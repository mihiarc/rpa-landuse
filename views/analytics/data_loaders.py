"""Data loading functions for the Analytics Dashboard.

Provides cached data loading with generic query builders to reduce duplication.
"""

import os
import sys
from pathlib import Path
from typing import Literal, Optional

# Add src to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import pandas as pd
import streamlit as st

from landuse.connections import DuckDBConnection
from landuse.core.app_config import AppConfig
from landuse.utils.security import SQLSanitizer
from landuse.utils.state_mappings import StateMapper

from .constants import CACHE_TTL_SHORT, MIN_ACRES_THRESHOLD, MAX_SANKEY_FLOWS


@st.cache_resource
def get_database_connection():
    """Get cached database connection using st.connection."""
    try:
        config = AppConfig()
        conn = st.connection(
            name="landuse_db_analytics",
            type=DuckDBConnection,
            database=config.database.path,
            read_only=True,
        )
        return conn, None
    except Exception as e:
        return None, f"Database connection error: {e}"


def _add_state_mappings(df: pd.DataFrame) -> pd.DataFrame:
    """Add state abbreviations and names to a DataFrame with state_code."""
    if df is not None and "state_code" in df.columns:
        df["state_abbr"] = df["state_code"].map(StateMapper.FIPS_TO_ABBREV)
        df["state_name"] = df["state_code"].map(StateMapper.FIPS_TO_NAME)
    return df


def _round_percent_change(df: pd.DataFrame) -> pd.DataFrame:
    """Round percent_change column if present."""
    if df is not None and "percent_change" in df.columns:
        df["percent_change"] = df["percent_change"].round(1)
    return df


# =============================================================================
# Generic Query Builders
# =============================================================================

def _build_loss_query(landuse_type: Literal["forest", "agricultural"]) -> str:
    """Build query for landuse loss by destination."""
    if landuse_type == "forest":
        from_filter = "fl.landuse_name = 'Forest'"
        to_filter = "tl.landuse_name != 'Forest'"
    else:  # agricultural
        from_filter = "fl.landuse_category = 'Agriculture'"
        to_filter = "tl.landuse_category != 'Agriculture'"

    return f"""
    SELECT
        tl.landuse_name as to_landuse,
        s.rcp_scenario,
        SUM(f.acres) as total_acres,
        AVG(f.acres) as avg_acres_per_county,
        COUNT(DISTINCT g.state_code) as states_affected
    FROM fact_landuse_transitions f
    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
    JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
    JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
    JOIN dim_geography g ON f.geography_id = g.geography_id
    WHERE {from_filter}
      AND {to_filter}
      AND f.transition_type = 'change'
    GROUP BY tl.landuse_name, s.rcp_scenario
    ORDER BY total_acres DESC
    """


def _build_gain_query(landuse_type: Literal["forest", "agricultural"]) -> str:
    """Build query for landuse gain by source."""
    if landuse_type == "forest":
        from_filter = "fl.landuse_name != 'Forest'"
        to_filter = "tl.landuse_name = 'Forest'"
    else:  # agricultural
        from_filter = "fl.landuse_category != 'Agriculture'"
        to_filter = "tl.landuse_category = 'Agriculture'"

    return f"""
    SELECT
        fl.landuse_name as from_landuse,
        s.rcp_scenario,
        SUM(f.acres) as total_acres,
        AVG(f.acres) as avg_acres_per_county,
        COUNT(DISTINCT g.state_code) as states_affected
    FROM fact_landuse_transitions f
    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
    JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
    JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
    JOIN dim_geography g ON f.geography_id = g.geography_id
    WHERE {from_filter}
      AND {to_filter}
      AND f.transition_type = 'change'
    GROUP BY fl.landuse_name, s.rcp_scenario
    ORDER BY total_acres DESC
    """


def _build_state_analysis_query(landuse_type: Literal["forest", "agricultural"]) -> str:
    """Build query for state-level analysis with baseline/future comparison."""
    if landuse_type == "forest":
        name = "forest"
        filter_condition = "fl.landuse_name = 'Forest' OR tl.landuse_name = 'Forest'"
        loss_condition = "fl.landuse_name = 'Forest' AND tl.landuse_name != 'Forest'"
        gain_condition = "fl.landuse_name != 'Forest' AND tl.landuse_name = 'Forest'"
    else:  # agricultural
        name = "ag"
        filter_condition = "fl.landuse_category = 'Agriculture' OR tl.landuse_category = 'Agriculture'"
        loss_condition = "fl.landuse_category = 'Agriculture' AND tl.landuse_category != 'Agriculture'"
        gain_condition = "fl.landuse_category != 'Agriculture' AND tl.landuse_category = 'Agriculture'"

    return f"""
    WITH
    {name}_baseline_2025 AS (
        SELECT
            g.state_code,
            SUM(f.acres) as baseline_acres
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE t.year_range = '2020-2030'
          AND f.transition_type = 'change'
          AND ({filter_condition})
        GROUP BY g.state_code
    ),
    {name}_future_2070 AS (
        SELECT
            g.state_code,
            SUM(f.acres) as future_acres,
            SUM(CASE WHEN {loss_condition} THEN f.acres ELSE 0 END) as {name}_loss,
            SUM(CASE WHEN {gain_condition} THEN f.acres ELSE 0 END) as {name}_gain
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE t.year_range = '2060-2070'
          AND f.transition_type = 'change'
          AND ({filter_condition})
        GROUP BY g.state_code
    )
    SELECT
        COALESCE(b.state_code, f.state_code) as state_code,
        COALESCE(f.{name}_loss, 0) as {name}_loss,
        COALESCE(f.{name}_gain, 0) as {name}_gain,
        COALESCE(f.{name}_gain, 0) - COALESCE(f.{name}_loss, 0) as net_change,
        COALESCE(b.baseline_acres, 0) as baseline_{name},
        COALESCE(f.future_acres, 0) as future_{name},
        CASE
            WHEN COALESCE(b.baseline_acres, 0) > 0
            THEN ((COALESCE(f.future_acres, 0) - COALESCE(b.baseline_acres, 0)) / b.baseline_acres) * 100
            ELSE 0
        END as percent_change
    FROM {name}_baseline_2025 b
    FULL OUTER JOIN {name}_future_2070 f ON b.state_code = f.state_code
    ORDER BY net_change DESC
    """


# =============================================================================
# Public Data Loading Functions
# =============================================================================

@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_landuse_analysis_data(landuse_type: Literal["forest", "agricultural"]):
    """Load comprehensive landuse transition data (gains and losses).

    Args:
        landuse_type: Either "forest" or "agricultural"

    Returns:
        Tuple of (df_loss, df_gain, df_states, error)
    """
    conn, error = get_database_connection()
    if error:
        return None, None, None, error

    try:
        loss_query = _build_loss_query(landuse_type)
        gain_query = _build_gain_query(landuse_type)
        state_query = _build_state_analysis_query(landuse_type)

        df_loss = conn.query(loss_query, ttl=CACHE_TTL_SHORT)
        df_gain = conn.query(gain_query, ttl=CACHE_TTL_SHORT)
        df_states = conn.query(state_query, ttl=CACHE_TTL_SHORT)

        df_states = _add_state_mappings(df_states)
        df_states = _round_percent_change(df_states)

        return df_loss, df_gain, df_states, None
    except Exception as e:
        return None, None, None, f"Error loading {landuse_type} data: {e}"


# Backward-compatible aliases
@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_forest_analysis_data():
    """Load comprehensive forest transition data."""
    return load_landuse_analysis_data("forest")


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_agricultural_analysis_data():
    """Load comprehensive agricultural transition data."""
    return load_landuse_analysis_data("agricultural")


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_urbanization_data():
    """Load urbanization data by state."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            g.state_code,
            fl.landuse_name as from_landuse,
            SUM(f.acres) as total_acres_urbanized
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE tl.landuse_name = 'Urban'
          AND f.transition_type = 'change'
        GROUP BY g.state_code, fl.landuse_name
        ORDER BY total_acres_urbanized DESC
        LIMIT 50
        """
        df = conn.query(query, ttl=CACHE_TTL_SHORT)
        return df, None
    except Exception as e:
        return None, f"Error loading urbanization data: {e}"


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_climate_comparison_data():
    """Load data for climate scenario comparison."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            s.rcp_scenario,
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
        GROUP BY s.rcp_scenario, fl.landuse_name, tl.landuse_name
        ORDER BY total_acres DESC
        LIMIT 100
        """
        df = conn.query(query, ttl=CACHE_TTL_SHORT)
        return df, None
    except Exception as e:
        return None, f"Error loading climate comparison data: {e}"


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_state_transitions():
    """Load state-level transition data for choropleth map."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        WITH
        baseline_2025 AS (
            SELECT g.state_code, SUM(f.acres) as acres_2025
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2020-2030' AND f.transition_type = 'change'
            GROUP BY g.state_code
        ),
        future_2070 AS (
            SELECT g.state_code, SUM(f.acres) as acres_2070
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2060-2070' AND f.transition_type = 'change'
            GROUP BY g.state_code
        ),
        state_changes AS (
            SELECT
                COALESCE(b.state_code, f.state_code) as state_code,
                COALESCE(b.acres_2025, 0) as baseline,
                COALESCE(f.acres_2070, 0) as future,
                CASE
                    WHEN COALESCE(b.acres_2025, 0) > 0
                    THEN ((COALESCE(f.acres_2070, 0) - COALESCE(b.acres_2025, 0)) / b.acres_2025) * 100
                    ELSE 0
                END as percent_change
            FROM baseline_2025 b
            FULL OUTER JOIN future_2070 f ON b.state_code = f.state_code
        ),
        state_transitions AS (
            SELECT
                g.state_code,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
            GROUP BY g.state_code, fl.landuse_name, tl.landuse_name
        )
        SELECT
            sc.state_code,
            sc.percent_change,
            sc.baseline,
            sc.future,
            (SELECT CONCAT(from_landuse, ' -> ', to_landuse)
             FROM state_transitions st
             WHERE st.state_code = sc.state_code
             ORDER BY total_acres DESC
             LIMIT 1) as dominant_transition
        FROM state_changes sc
        WHERE sc.state_code IS NOT NULL
        """
        df = conn.query(query, ttl=CACHE_TTL_SHORT)
        df = _add_state_mappings(df)
        df = _round_percent_change(df)
        return df, None
    except Exception as e:
        return None, f"Error loading state transitions: {e}"


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_sankey_data(
    from_landuse: Optional[str] = None,
    to_landuse: Optional[str] = None,
    state_filter: Optional[str] = None,
):
    """Load data for Sankey diagram of land use flows."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        where_conditions = [
            "f.transition_type = 'change'",
            "fl.landuse_name != tl.landuse_name",  # Exclude self-loops
        ]

        if from_landuse and from_landuse != "All":
            try:
                SQLSanitizer.validate_landuse(from_landuse)
                where_conditions.append(f"fl.landuse_name = {SQLSanitizer.safe_string(from_landuse)}")
            except ValueError as e:
                return None, str(e)

        if to_landuse and to_landuse != "All":
            try:
                SQLSanitizer.validate_landuse(to_landuse)
                where_conditions.append(f"tl.landuse_name = {SQLSanitizer.safe_string(to_landuse)}")
            except ValueError as e:
                return None, str(e)

        if state_filter and state_filter != "All":
            state_fips = StateMapper.name_to_fips(state_filter)
            if state_fips:
                try:
                    SQLSanitizer.validate_state_code(state_fips)
                    where_conditions.append(f"g.state_code = {SQLSanitizer.safe_string(state_fips)}")
                except ValueError as e:
                    return None, str(e)
            else:
                return None, f"Invalid state: {state_filter}"

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT
            fl.landuse_name as source,
            tl.landuse_name as target,
            SUM(f.acres) as value,
            COUNT(DISTINCT s.scenario_id) as scenario_count,
            COUNT(DISTINCT g.county_name) as county_count
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        WHERE {where_clause}
        GROUP BY fl.landuse_name, tl.landuse_name
        HAVING SUM(f.acres) > {MIN_ACRES_THRESHOLD}
        ORDER BY value DESC
        LIMIT {MAX_SANKEY_FLOWS}
        """

        df = conn.query(query, ttl=CACHE_TTL_SHORT)

        if df.empty:
            return None, "No transitions found for selected filters."

        return df, None
    except Exception as e:
        return None, f"Error loading Sankey data: {e}"


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_animated_timeline_data():
    """Load timeline visualization data."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            t.start_year,
            t.year_range,
            s.rcp_scenario,
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
          AND fl.landuse_name != tl.landuse_name
        GROUP BY t.start_year, t.year_range, s.rcp_scenario, fl.landuse_name, tl.landuse_name
        HAVING SUM(f.acres) > 500000
        ORDER BY t.start_year, total_acres DESC
        """
        df = conn.query(query, ttl=CACHE_TTL_SHORT)
        return df, None
    except Exception as e:
        return None, f"Error loading timeline data: {e}"


@st.cache_data(ttl=CACHE_TTL_SHORT)
def load_scenario_comparison_data():
    """Load available scenarios for comparison."""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT DISTINCT
            s.scenario_name,
            s.climate_model,
            s.rcp_scenario
        FROM dim_scenario s
        ORDER BY s.scenario_name
        """
        df = conn.query(query, ttl=CACHE_TTL_SHORT)
        return df, None
    except Exception as e:
        return None, f"Error loading scenario data: {e}"
