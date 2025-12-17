#!/usr/bin/env python3
"""
Analytics Dashboard for Landuse Data
Pre-built visualizations and insights for land use transition analysis
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from landuse.connections import DuckDBConnection  # noqa: E402
from landuse.core.app_config import AppConfig  # noqa: E402
from landuse.utils.security import SQLSanitizer  # noqa: E402

# Import state mappings and connection
from landuse.utils.state_mappings import StateMapper  # noqa: E402

# RPA Assessment Official Color Palette
RPA_COLORS = {
    "dark_green": "#496f4a",
    "medium_green": "#85b18b",
    "medium_blue": "#a3cad4",
    "light_brown": "#cec597",
    "pink": "#edaa97",
    "dark_blue": "#61a4b5",
    "lighter_dark_green": "#89b18b",
    "lighter_medium_green": "#b8d0b9",
    "lighter_medium_blue": "#c8dfe5",
    "lighter_light_brown": "#e2dcc1",
}

# RPA color sequences for Plotly
RPA_COLOR_SEQUENCE = [
    RPA_COLORS["dark_green"],
    RPA_COLORS["medium_blue"],
    RPA_COLORS["medium_green"],
    RPA_COLORS["light_brown"],
    RPA_COLORS["pink"],
    RPA_COLORS["dark_blue"],
]

# RPA gradient scales
RPA_GREEN_SCALE = [
    [0, RPA_COLORS["lighter_medium_green"]],
    [0.5, RPA_COLORS["medium_green"]],
    [1, RPA_COLORS["dark_green"]],
]
RPA_BLUE_SCALE = [
    [0, RPA_COLORS["lighter_medium_blue"]],
    [0.5, RPA_COLORS["medium_blue"]],
    [1, RPA_COLORS["dark_blue"]],
]
RPA_BROWN_SCALE = [[0, RPA_COLORS["lighter_light_brown"]], [0.5, RPA_COLORS["light_brown"]], [1, "#9f6b25"]]


@st.cache_resource
def get_database_connection():
    """Get cached database connection using st.connection"""
    try:
        # Use unified config system
        config = AppConfig()

        conn = st.connection(
            name="landuse_db_analytics", type=DuckDBConnection, database=config.database.path, read_only=True
        )
        return conn, None
    except Exception as e:
        return None, f"Database connection error: {e}"


@st.cache_data
def load_agricultural_analysis_data():
    """Load comprehensive agricultural transition data (gains and losses)"""
    conn, error = get_database_connection()
    if error:
        return None, None, None, error

    try:
        # Query 1: Agricultural loss by destination (what agriculture becomes)
        ag_loss_query = """
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
        WHERE fl.landuse_category = 'Agriculture'
          AND tl.landuse_category != 'Agriculture'
          AND f.transition_type = 'change'
        GROUP BY tl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 2: Agricultural gain by source (what becomes agriculture)
        ag_gain_query = """
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
        WHERE fl.landuse_category != 'Agriculture'
          AND tl.landuse_category = 'Agriculture'
          AND f.transition_type = 'change'
        GROUP BY fl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 3: State-level agricultural changes with temporal percentage change (2025 baseline to 2070)
        state_ag_query = """
        WITH
        ag_baseline_2025 AS (
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
              AND (fl.landuse_category = 'Agriculture' OR tl.landuse_category = 'Agriculture')
            GROUP BY g.state_code
        ),
        ag_future_2070 AS (
            SELECT
                g.state_code,
                SUM(f.acres) as future_acres,
                SUM(CASE
                    WHEN fl.landuse_category = 'Agriculture' AND tl.landuse_category != 'Agriculture' THEN f.acres
                    ELSE 0
                END) as ag_loss,
                SUM(CASE
                    WHEN fl.landuse_category != 'Agriculture' AND tl.landuse_category = 'Agriculture' THEN f.acres
                    ELSE 0
                END) as ag_gain
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2060-2070'
              AND f.transition_type = 'change'
              AND (fl.landuse_category = 'Agriculture' OR tl.landuse_category = 'Agriculture')
            GROUP BY g.state_code
        )
        SELECT
            COALESCE(b.state_code, f.state_code) as state_code,
            COALESCE(f.ag_loss, 0) as ag_loss,
            COALESCE(f.ag_gain, 0) as ag_gain,
            COALESCE(f.ag_gain, 0) - COALESCE(f.ag_loss, 0) as net_change,
            COALESCE(b.baseline_acres, 0) as baseline_ag,
            COALESCE(f.future_acres, 0) as future_ag,
            CASE
                WHEN COALESCE(b.baseline_acres, 0) > 0
                THEN ((COALESCE(f.future_acres, 0) - COALESCE(b.baseline_acres, 0)) / b.baseline_acres) * 100
                ELSE 0
            END as percent_change
        FROM ag_baseline_2025 b
        FULL OUTER JOIN ag_future_2070 f ON b.state_code = f.state_code
        ORDER BY net_change DESC
        """

        df_loss = conn.query(ag_loss_query, ttl=300)
        df_gain = conn.query(ag_gain_query, ttl=300)
        df_states = conn.query(state_ag_query, ttl=300)

        # Add state names and abbreviations
        df_states["state_abbr"] = df_states["state_code"].map(StateMapper.FIPS_TO_ABBREV)
        df_states["state_name"] = df_states["state_code"].map(StateMapper.FIPS_TO_NAME)

        # Add baseline_forest column for compatibility (same as total_transitions)
        if "total_transitions" in df_states.columns:
            df_states["baseline_ag"] = df_states["total_transitions"]

        # Round percentage for display
        if "percent_change" in df_states.columns:
            df_states["percent_change"] = df_states["percent_change"].round(1)

        return df_loss, df_gain, df_states, None
    except Exception as e:
        return None, None, None, f"Error loading agricultural data: {e}"


@st.cache_data
def load_urbanization_data():
    """Load urbanization data by state"""
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

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading urbanization data: {e}"


@st.cache_data
def load_forest_analysis_data():
    """Load comprehensive forest transition data"""
    conn, error = get_database_connection()
    if error:
        return None, None, None, error

    try:
        # Query 1: Forest loss by destination
        forest_loss_query = """
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
        WHERE fl.landuse_name = 'Forest'
          AND tl.landuse_name != 'Forest'
          AND f.transition_type = 'change'
        GROUP BY tl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 2: Forest gain by source
        forest_gain_query = """
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
        WHERE tl.landuse_name = 'Forest'
          AND fl.landuse_name != 'Forest'
          AND f.transition_type = 'change'
        GROUP BY fl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 3: State-level forest changes with temporal percentage change (2025 baseline to 2070)
        state_forest_query = """
        WITH
        forest_baseline_2025 AS (
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
              AND (fl.landuse_name = 'Forest' OR tl.landuse_name = 'Forest')
            GROUP BY g.state_code
        ),
        forest_future_2070 AS (
            SELECT
                g.state_code,
                SUM(f.acres) as future_acres,
                SUM(CASE
                    WHEN fl.landuse_name = 'Forest' AND tl.landuse_name != 'Forest' THEN f.acres
                    ELSE 0
                END) as forest_loss,
                SUM(CASE
                    WHEN fl.landuse_name != 'Forest' AND tl.landuse_name = 'Forest' THEN f.acres
                    ELSE 0
                END) as forest_gain
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2060-2070'
              AND f.transition_type = 'change'
              AND (fl.landuse_name = 'Forest' OR tl.landuse_name = 'Forest')
            GROUP BY g.state_code
        )
        SELECT
            COALESCE(b.state_code, f.state_code) as state_code,
            COALESCE(f.forest_loss, 0) as forest_loss,
            COALESCE(f.forest_gain, 0) as forest_gain,
            COALESCE(f.forest_gain, 0) - COALESCE(f.forest_loss, 0) as net_change,
            COALESCE(b.baseline_acres, 0) as baseline_forest,
            COALESCE(f.future_acres, 0) as future_forest,
            CASE
                WHEN COALESCE(b.baseline_acres, 0) > 0
                THEN ((COALESCE(f.future_acres, 0) - COALESCE(b.baseline_acres, 0)) / b.baseline_acres) * 100
                ELSE 0
            END as percent_change
        FROM forest_baseline_2025 b
        FULL OUTER JOIN forest_future_2070 f ON b.state_code = f.state_code
        ORDER BY net_change DESC
        """

        df_loss = conn.query(forest_loss_query, ttl=300)
        df_gain = conn.query(forest_gain_query, ttl=300)
        df_states = conn.query(state_forest_query, ttl=300)

        # Add state names and abbreviations
        df_states["state_abbr"] = df_states["state_code"].map(StateMapper.FIPS_TO_ABBREV)
        df_states["state_name"] = df_states["state_code"].map(StateMapper.FIPS_TO_NAME)

        # Add baseline_forest column for compatibility (same as total_transitions)
        if "total_transitions" in df_states.columns:
            df_states["baseline_forest"] = df_states["total_transitions"]

        # Round percentage for display
        if "percent_change" in df_states.columns:
            df_states["percent_change"] = df_states["percent_change"].round(1)

        return df_loss, df_gain, df_states, None
    except Exception as e:
        return None, None, None, f"Error loading forest data: {e}"


@st.cache_data
def load_climate_comparison_data():
    """Load data for climate scenario comparison"""
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

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading climate comparison data: {e}"


def create_urbanization_chart(df):
    """Create urbanization analysis visualization"""
    if df is None or df.empty:
        return None

    # Aggregate by state
    state_totals = df.groupby("state_code")["total_acres_urbanized"].sum().reset_index()
    state_totals = state_totals.sort_values("total_acres_urbanized", ascending=True).tail(15)

    fig = px.bar(
        state_totals,
        x="total_acres_urbanized",
        y="state_code",
        title="Top 15 States by Urban Expansion (Total Acres)",
        labels={"total_acres_urbanized": "Total Acres Urbanized", "state_code": "State"},
        color="total_acres_urbanized",
        color_continuous_scale=RPA_BROWN_SCALE,
    )

    fig.update_layout(
        height=500,
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Acres Urbanized (millions)",
        xaxis_tickformat=".1s",  # Format x-axis to show millions
        font={"size": 12},
    )

    return fig


def create_agricultural_flow_chart(df_loss, df_gain):
    """Create agricultural transition flow chart (similar to forest flow chart)"""
    if df_loss is None or df_gain is None:
        return None

    # Create waterfall-style chart showing gains and losses
    fig = make_subplots(rows=1, cols=1)

    # Aggregate data
    loss_by_type = df_loss.groupby("to_landuse")["total_acres"].sum().to_dict()
    gain_by_type = df_gain.groupby("from_landuse")["total_acres"].sum().to_dict()

    # Create waterfall chart
    x_labels = []
    y_values = []
    colors = []

    # Add losses (negative values)
    # Colorblind-safe: blue for losses
    for landuse, acres in loss_by_type.items():
        x_labels.append(f"To {landuse}")
        y_values.append(-acres)
        colors.append("rgba(33, 102, 172, 0.7)")  # Blue - colorblind safe for losses

    # Add gains (positive values)
    # Colorblind-safe: orange for gains
    for landuse, acres in gain_by_type.items():
        x_labels.append(f"From {landuse}")
        y_values.append(acres)
        colors.append("rgba(217, 95, 2, 0.7)")  # Orange - colorblind safe for gains

    # Create bar chart
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=y_values,
            marker_color=colors,
            text=[f"{abs(v / 1e6):.1f}M" for v in y_values],
            textposition="auto",
            name="Agricultural Transitions",
        )
    )

    # Update layout
    fig.update_layout(
        title={"text": "Agricultural Land Transitions: Gains vs Losses", "x": 0.5, "xanchor": "center"},
        xaxis_title="Transition Type",
        yaxis_title="Acres (Millions)",
        yaxis_tickformat=".1s",
        showlegend=False,
        height=450,
        hovermode="x unified",
        xaxis_tickangle=-45,
        yaxis_zeroline=True,
        yaxis_zerolinewidth=2,
        yaxis_zerolinecolor="black",
    )

    return fig


def create_forest_flow_chart(df_loss, df_gain):
    """Create a combined flow chart showing forest gains and losses"""
    if df_loss is None or df_gain is None:
        return None

    # Prepare data for waterfall chart
    fig = go.Figure()

    # Group by land use type for cleaner visualization
    loss_by_type = df_loss.groupby("to_landuse")["total_acres"].sum().sort_values(ascending=False)
    gain_by_type = df_gain.groupby("from_landuse")["total_acres"].sum().sort_values(ascending=False)

    # Create waterfall chart
    x_labels = []
    y_values = []
    colors = []

    # Add losses (negative values)
    # Colorblind-safe: blue for losses
    for landuse, acres in loss_by_type.items():
        x_labels.append(f"To {landuse}")
        y_values.append(-acres)
        colors.append("rgba(33, 102, 172, 0.7)")  # Blue - colorblind safe for losses

    # Add gains (positive values)
    # Colorblind-safe: orange for gains
    for landuse, acres in gain_by_type.items():
        x_labels.append(f"From {landuse}")
        y_values.append(acres)
        colors.append("rgba(217, 95, 2, 0.7)")  # Orange - colorblind safe for gains

    # Create bar chart
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=y_values,
            marker_color=colors,
            text=[f"{abs(v / 1e6):.1f}M" for v in y_values],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:,.0f} acres<extra></extra>",
        )
    )

    # Calculate net change
    total_loss = sum(v for v in y_values if v < 0)
    total_gain = sum(v for v in y_values if v > 0)
    net_change = total_gain + total_loss

    # Update layout
    fig.update_layout(
        title={
            "text": f"Forest Transitions: Net Change = {net_change / 1e6:+.1f}M acres",
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis_title="Transition Type",
        yaxis_title="Acres",
        yaxis_tickformat=".2s",
        height=500,
        showlegend=False,
        yaxis_zeroline=True,
        yaxis_zerolinewidth=2,
        yaxis_zerolinecolor="black",
    )

    return fig


def create_agricultural_state_map(df_states):
    """Create choropleth map showing percentage agricultural change by state"""
    if df_states is None or df_states.empty:
        return None

    # Calculate dynamic range based on actual data, capped at ±100%
    if "percent_change" in df_states.columns:
        # Get the 95th percentile to handle outliers
        lower_bound = df_states["percent_change"].quantile(0.05)
        upper_bound = df_states["percent_change"].quantile(0.95)
        # Make symmetric around 0 for better visual balance
        max_abs = max(abs(lower_bound), abs(upper_bound))
        # Cap at 100% since that's the theoretical maximum
        max_abs = min(max_abs, 100)
        color_range = [-max_abs, max_abs]
    else:
        color_range = [-100, 100]  # Fallback range

    # Use Viridis color scale for percentage changes
    fig = px.choropleth(
        df_states,
        locations="state_abbr",
        locationmode="USA-states",
        color="percent_change",
        color_continuous_scale="Viridis",  # Viridis color scale
        color_continuous_midpoint=0,  # Center at 0% change
        range_color=color_range,  # Dynamic range based on data
        hover_name="state_name",
        hover_data={
            "state_abbr": False,
            "percent_change": ":.1f",
            "ag_loss": ":,.0f",
            "ag_gain": ":,.0f",
            "net_change": ":,.0f",
            "baseline_ag": ":,.0f",
            "state_name": False,
        },
        labels={
            "percent_change": "Change (%)",
            "ag_loss": "2070 Agricultural Loss (acres)",
            "ag_gain": "2070 Agricultural Gain (acres)",
            "net_change": "Net Change (acres)",
            "baseline_ag": "2025 Baseline (acres)",
            "future_ag": "2070 Activity (acres)",
        },
        title="Agricultural Transition Activity: % Change from 2025 to 2070",
    )

    # Update layout
    fig.update_layout(
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showlakes": True,
            "lakecolor": "rgba(255, 255, 255, 0.3)",
            "bgcolor": "rgba(0,0,0,0)",
        },
        height=600,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        coloraxis_colorbar={
            "title": "Change<br>(%)",
            "thicknessmode": "pixels",
            "thickness": 15,
            "lenmode": "pixels",
            "len": 300,
            "yanchor": "middle",
            "y": 0.5,
            "ticksuffix": "%",
        },
    )

    return fig


def create_forest_state_map(df_states):
    """Create choropleth map showing percentage forest change by state"""
    if df_states is None or df_states.empty:
        return None

    # Calculate dynamic range based on actual data, capped at ±100%
    if "percent_change" in df_states.columns:
        # Get the 95th percentile to handle outliers
        lower_bound = df_states["percent_change"].quantile(0.05)
        upper_bound = df_states["percent_change"].quantile(0.95)
        # Make symmetric around 0 for better visual balance
        max_abs = max(abs(lower_bound), abs(upper_bound))
        # Cap at 100% since that's the theoretical maximum
        max_abs = min(max_abs, 100)
        color_range = [-max_abs, max_abs]
    else:
        color_range = [-100, 100]  # Fallback range

    # Use Viridis color scale for percentage changes
    fig = px.choropleth(
        df_states,
        locations="state_abbr",
        locationmode="USA-states",
        color="percent_change",
        color_continuous_scale="Viridis",  # Viridis color scale
        color_continuous_midpoint=0,  # Center at 0% change
        range_color=color_range,  # Dynamic range based on data
        hover_name="state_name",
        hover_data={
            "state_abbr": False,
            "percent_change": ":.1f",
            "forest_loss": ":,.0f",
            "forest_gain": ":,.0f",
            "net_change": ":,.0f",
            "baseline_forest": ":,.0f",
            "state_name": False,
        },
        labels={
            "percent_change": "Change (%)",
            "forest_loss": "2070 Forest Loss (acres)",
            "forest_gain": "2070 Forest Gain (acres)",
            "net_change": "Net Change (acres)",
            "baseline_forest": "2025 Baseline (acres)",
            "future_forest": "2070 Activity (acres)",
        },
        title="Forest Transition Activity: % Change from 2025 to 2070",
    )

    # Update layout
    fig.update_layout(
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showlakes": True,
            "lakecolor": "rgba(255, 255, 255, 0.3)",
            "bgcolor": "rgba(0,0,0,0)",
        },
        height=600,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        coloraxis_colorbar={
            "title": "Change<br>(%)",
            "thicknessmode": "pixels",
            "thickness": 15,
            "lenmode": "pixels",
            "len": 300,
            "yanchor": "middle",
            "y": 0.5,
            "ticksuffix": "%",
        },
    )

    return fig


def create_forest_scenario_comparison(df_loss, df_gain):
    """Create comparison of forest changes across climate scenarios"""
    if df_loss is None or df_gain is None:
        return None

    # Aggregate by scenario
    loss_by_scenario = df_loss.groupby("rcp_scenario")["total_acres"].sum()
    gain_by_scenario = df_gain.groupby("rcp_scenario")["total_acres"].sum()

    # Create grouped bar chart
    fig = go.Figure()

    scenarios = ["rcp45", "rcp85"]

    # Colorblind-safe palette: blue (#2166ac) for loss, orange (#d95f02) for gain
    # These colors are distinguishable for deuteranopia, protanopia, and tritanopia
    fig.add_trace(
        go.Bar(
            name="Forest Loss",
            x=scenarios,
            y=[-loss_by_scenario.get(s, 0) for s in scenarios],
            marker_color="rgba(33, 102, 172, 0.8)",  # Blue - colorblind safe
            marker_pattern_shape="/",  # Add pattern for additional encoding
            text=[f"{abs(loss_by_scenario.get(s, 0) / 1e6):.1f}M" for s in scenarios],
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Forest Gain",
            x=scenarios,
            y=[gain_by_scenario.get(s, 0) for s in scenarios],
            marker_color="rgba(217, 95, 2, 0.8)",  # Orange - colorblind safe
            marker_pattern_shape="",  # Solid fill for contrast with hatched pattern
            text=[f"{gain_by_scenario.get(s, 0) / 1e6:.1f}M" for s in scenarios],
            textposition="outside",
        )
    )

    # Calculate net change line
    net_changes = [gain_by_scenario.get(s, 0) - loss_by_scenario.get(s, 0) for s in scenarios]

    fig.add_trace(
        go.Scatter(
            name="Net Change",
            x=scenarios,
            y=net_changes,
            mode="lines+markers+text",
            line={"color": "black", "width": 3},
            marker={"size": 10},
            text=[f"{v / 1e6:+.1f}M" for v in net_changes],
            textposition="top center",
            yaxis="y2",
        )
    )

    # Update layout with dual y-axes
    fig.update_layout(
        title="Forest Changes by Climate Scenario",
        xaxis_title="Climate Scenario",
        yaxis_title="Forest Loss/Gain (acres)",
        yaxis2={"title": "Net Change (acres)", "overlaying": "y", "side": "right", "showgrid": False},
        yaxis_tickformat=".2s",
        yaxis2_tickformat=".2s",
        height=500,
        hovermode="x unified",
        barmode="relative",
        legend={"x": 0.02, "y": 0.98, "xanchor": "left", "yanchor": "top"},
    )

    return fig


def create_climate_comparison_chart(df):
    """Create climate scenario comparison visualization"""
    if df is None or df.empty:
        return None

    # Focus on major transitions
    major_transitions = df[df["total_acres"] > df["total_acres"].quantile(0.8)]

    fig = px.sunburst(
        major_transitions,
        path=["rcp_scenario", "from_landuse", "to_landuse"],
        values="total_acres",
        title="Land Use Transitions by Climate Scenario",
        color="total_acres",
        color_continuous_scale=RPA_BLUE_SCALE,
    )

    fig.update_layout(height=600, font={"size": 12})

    return fig


@st.cache_data
def load_state_transitions():
    """Load state-level transition data for choropleth map showing percentage change between 2025-2070"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        WITH
        baseline_2025 AS (
            SELECT
                g.state_code,
                SUM(f.acres) as acres_2025
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2020-2030'
              AND f.transition_type = 'change'
            GROUP BY g.state_code
        ),
        future_2070 AS (
            SELECT
                g.state_code,
                SUM(f.acres) as acres_2070
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.year_range = '2060-2070'
              AND f.transition_type = 'change'
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
            (SELECT CONCAT(from_landuse, ' → ', to_landuse)
             FROM state_transitions st
             WHERE st.state_code = sc.state_code
             ORDER BY total_acres DESC
             LIMIT 1) as dominant_transition
        FROM state_changes sc
        WHERE sc.state_code IS NOT NULL
        """

        df = conn.query(query, ttl=300)

        # Add state abbreviations and names
        df["state_abbr"] = df["state_code"].map(StateMapper.FIPS_TO_ABBREV)
        df["state_name"] = df["state_code"].map(StateMapper.FIPS_TO_NAME)

        # Round percentage for display
        df["percent_change"] = df["percent_change"].round(1)

        return df, None
    except Exception as e:
        return None, f"Error loading state transitions: {e}"


@st.cache_data
def load_sankey_data(from_landuse=None, to_landuse=None, state_filter=None):
    """Load data for Sankey diagram of land use flows"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Build dynamic WHERE clause with safe SQL construction
        where_conditions = ["f.transition_type = 'change'"]
        # Exclude self-loops where source equals target
        where_conditions.append("fl.landuse_name != tl.landuse_name")

        # Use SQLSanitizer for safe value handling
        if from_landuse and from_landuse != "All":
            try:
                # Validate and sanitize the land use type
                SQLSanitizer.validate_landuse(from_landuse)
                where_conditions.append(f"fl.landuse_name = {SQLSanitizer.safe_string(from_landuse)}")
            except ValueError as e:
                return None, str(e)

        if to_landuse and to_landuse != "All":
            try:
                # Validate and sanitize the land use type
                SQLSanitizer.validate_landuse(to_landuse)
                where_conditions.append(f"tl.landuse_name = {SQLSanitizer.safe_string(to_landuse)}")
            except ValueError as e:
                return None, str(e)

        if state_filter and state_filter != "All":
            # Convert state name to FIPS code for database query
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
        HAVING SUM(f.acres) > 100000
        ORDER BY value DESC
        LIMIT 15
        """

        df = conn.query(query, ttl=300)

        # Additional validation: ensure we have data
        if df.empty:
            return (
                None,
                "No transitions found for selected filters. Try adjusting the filter criteria or selecting 'All' for broader results.",
            )

        return df, None
    except Exception as e:
        return None, f"Error loading Sankey data: {e}"


def create_choropleth_map(df):
    """Create interactive choropleth map showing percentage change between 2025-2070"""
    if df is None or df.empty:
        return None

    # Use diverging color scale for percentage changes (red for decrease, green for increase)
    fig = px.choropleth(
        df,
        locations="state_abbr",
        locationmode="USA-states",
        color="percent_change",
        color_continuous_scale="RdYlGn",  # Red-Yellow-Green diverging scale
        color_continuous_midpoint=0,  # Center at 0% change
        range_color=[-50, 50],  # Cap display range at ±50% for better visualization
        hover_name="state_name",
        hover_data={
            "state_abbr": False,  # Hide from hover
            "percent_change": ":.1f",
            "baseline": ":,.0f",
            "future": ":,.0f",
            "dominant_transition": True,
            "state_name": False,  # Already shown as hover_name
        },
        labels={
            "percent_change": "Change (%)",
            "baseline": "2020-2030 Period (acres)",
            "future": "2060-2070 Period (acres)",
            "dominant_transition": "Most Common Transition",
        },
        title="Change in Land Use Transition Activity: 2020-2030 vs 2060-2070 (%)",
    )

    # Update layout for better visualization
    fig.update_layout(
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showlakes": True,
            "lakecolor": "rgba(255, 255, 255, 0.3)",
            "bgcolor": "rgba(0,0,0,0)",
        },
        height=600,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        coloraxis_colorbar={
            "title": "Transition<br>Activity<br>Change (%)",
            "thicknessmode": "pixels",
            "thickness": 15,
            "lenmode": "pixels",
            "len": 300,
            "yanchor": "middle",
            "y": 0.5,
            "ticksuffix": "%",
        },
    )

    return fig


def create_sankey_diagram(df):
    """Create Sankey diagram for land use flows with modern Plotly features"""
    if df is None or df.empty:
        return None

    # Sort by value to ensure most significant flows are visible
    df = df.sort_values("value", ascending=False)

    # Create node labels - ensure unique nodes
    source_nodes = df["source"].unique().tolist()
    target_nodes = df["target"].unique().tolist()
    all_nodes = list(dict.fromkeys(source_nodes + target_nodes))  # Preserve order, remove duplicates
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    # Define modern color palette for land use types with RPA colors
    node_colors = {
        "Crop": RPA_COLORS["light_brown"],  # Light brown for agricultural
        "Pasture": RPA_COLORS["medium_green"],  # Medium green for pasture
        "Forest": RPA_COLORS["dark_green"],  # Dark green for forest
        "Urban": RPA_COLORS["dark_blue"],  # Dark blue for urban
        "Rangeland": RPA_COLORS["pink"],  # Pink for rangeland
    }

    # Prepare hover data with better formatting
    hover_labels = []
    for _, row in df.iterrows():
        acres_millions = row["value"] / 1_000_000
        label_text = f"<b>{row['source']} → {row['target']}</b><br>" + f"Total: {acres_millions:.2f}M acres<br>"
        if "county_count" in row:
            label_text += f"Counties: {row['county_count']}<br>"
        label_text += f"Scenarios: {row['scenario_count']}"
        hover_labels.append(label_text)

    # Generate link colors with proper transparency
    link_colors = []
    for i in range(len(df)):
        source_color = node_colors.get(df.iloc[i]["source"], "#999999")
        # Convert hex to rgba with transparency
        if source_color.startswith("#"):
            # Parse hex color and convert to rgba
            hex_color = source_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            link_colors.append(f"rgba({r},{g},{b},0.3)")
        else:
            link_colors.append("rgba(150,150,150,0.3)")

    # Create Sankey diagram with enhanced features
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",  # Better node positioning
                node={
                    "pad": 20,
                    "thickness": 30,
                    "line": {"color": "white", "width": 1},
                    "label": all_nodes,
                    "color": [node_colors.get(node, "#999999") for node in all_nodes],
                    "customdata": all_nodes,
                    "hovertemplate": "<b>%{customdata}</b><br>Total: %{value:,.0f} acres<extra></extra>",
                },
                link={
                    "source": [node_dict.get(src) for src in df["source"]],
                    "target": [node_dict.get(tgt) for tgt in df["target"]],
                    "value": df["value"].tolist(),
                    "customdata": hover_labels,
                    "hovertemplate": "%{customdata}<extra></extra>",
                    "color": link_colors,
                    "line": {"width": 0},
                },
                textfont={"size": 14, "color": "black", "family": "Arial, sans-serif"},
            )
        ]
    )

    fig.update_layout(
        title={"text": "Land Use Transition Flows", "x": 0.5, "xanchor": "center", "font": {"size": 18}},
        font={"size": 12, "family": "Arial, sans-serif"},
        height=600,
        margin={"l": 10, "r": 10, "t": 60, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel={"bgcolor": "white", "font_size": 12},
    )

    return fig


@st.cache_data
def load_animated_timeline_data():
    """Load data for animated timeline visualization"""
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
            SUM(f.acres) as total_acres,
            COUNT(DISTINCT g.state_code) as states_affected
        FROM fact_landuse_transitions f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
          AND fl.landuse_name != tl.landuse_name
        GROUP BY t.start_year, t.year_range, s.rcp_scenario,
                 fl.landuse_name, tl.landuse_name
        HAVING SUM(f.acres) > 500000
        ORDER BY t.start_year, total_acres DESC
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading timeline data: {e}"


@st.cache_data
def load_scenario_comparison_data():
    """Load scenario list for comparison"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT DISTINCT
            s.scenario_name,
            s.climate_model,
            s.rcp_scenario,
            s.ssp_scenario
        FROM dim_scenario s
        ORDER BY s.scenario_name
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading scenarios: {e}"


def create_animated_timeline(df):
    """Create animated timeline of transitions"""
    if df is None or df.empty:
        return None

    # Create transition labels
    df["transition"] = df["from_landuse"] + " → " + df["to_landuse"]

    # Aggregate by year and scenario type
    timeline_data = df.groupby(["start_year", "rcp_scenario", "transition"])["total_acres"].sum().reset_index()

    # Create animated bar chart
    fig = px.bar(
        timeline_data,
        x="transition",
        y="total_acres",
        color="rcp_scenario",
        animation_frame="start_year",
        animation_group="transition",
        title="Land Use Transitions Over Time - Press Play to Animate",
        labels={
            "total_acres": "Total Acres",
            "transition": "Land Use Transition",
            "rcp_scenario": "Climate Scenario",
            "start_year": "Year",
        },
        color_discrete_map={"rcp45": "#2E86AB", "rcp85": "#F24236"},
        range_y=[0, timeline_data["total_acres"].max() * 1.1],
        height=600,
    )

    # Update layout for better readability
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=True,
        xaxis_title="Land Use Transition",
        yaxis_title="Total Acres",
        yaxis_tickformat=".2s",
        updatemenus=[
            {"type": "buttons", "showactive": False, "x": 0.1, "y": 1.15, "xanchor": "left", "yanchor": "top"}
        ],
    )

    # Slow down animation for better viewing
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1500
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 750

    return fig


def create_scenario_spider_chart(selected_scenarios):
    """Create spider/radar chart comparing scenarios"""
    conn, error = get_database_connection()
    if error:
        return None, error

    if not selected_scenarios:
        return None, "No scenarios selected"

    try:
        # Build query with safe scenario list
        try:
            safe_scenario_clause = SQLSanitizer.safe_scenario_list(selected_scenarios)
        except ValueError as e:
            return None, f"Invalid scenario name: {e}"

        query = f"""
        WITH scenario_summary AS (
            SELECT
                s.scenario_name,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres_gained
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
              AND s.scenario_name IN {safe_scenario_clause}
            GROUP BY s.scenario_name, tl.landuse_name
        )
        SELECT * FROM scenario_summary
        ORDER BY scenario_name, to_landuse
        """

        df = conn.query(query, ttl=300)

        if df.empty:
            return None, "No data for selected scenarios"

        # Pivot data for radar chart
        pivot_df = df.pivot(index="scenario_name", columns="to_landuse", values="total_acres_gained").fillna(0)

        # Create radar chart
        fig = go.Figure()

        colors = px.colors.qualitative.Set2

        for i, scenario in enumerate(pivot_df.index):
            values = pivot_df.loc[scenario].values.tolist()
            # Normalize values to make comparison easier
            max_val = max(values) if max(values) > 0 else 1
            normalized_values = [v / max_val * 100 for v in values]

            fig.add_trace(
                go.Scatterpolar(
                    r=normalized_values,
                    theta=pivot_df.columns.tolist(),
                    fill="toself",
                    name=scenario.split("_")[0],  # Show just model name
                    line_color=colors[i % len(colors)],
                    opacity=0.6,
                )
            )

        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 100], "ticksuffix": "%"}},
            showlegend=True,
            title="Scenario Comparison: Relative Land Gains by Type",
            height=500,
        )

        return fig, None

    except Exception as e:
        return None, f"Error creating comparison: {e}"


def show_enhanced_visualizations():
    """Show enhanced visualization section"""
    st.markdown("### 🎨 Enhanced Visualizations")
    st.markdown("**Interactive maps, flow diagrams, and advanced analytics**")

    # Create sub-tabs for enhanced visualizations
    viz_tab1, viz_tab2 = st.tabs(["🗺️ Geographic Analysis", "🔀 Transition Flows"])

    with viz_tab1:
        st.markdown("#### State-Level Land Use Changes")
        st.markdown(
            "**Interactive map showing the percentage change in land use transition activity between 2020-2030 and 2060-2070 periods**"
        )
        st.info(
            "📊 **What this shows:** The percentage increase or decrease in the total amount of land changing from one use to another. Green = more transition activity, Red = less transition activity."
        )

        state_data, state_error = load_state_transitions()
        if state_error:
            st.error(f"❌ {state_error}")
        elif state_data is not None and not state_data.empty:
            # Create choropleth map
            fig = create_choropleth_map(state_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

            # Show state details
            st.markdown("##### 🏆 Top 10 States by Percentage Change (2025-2070)")

            # Sort by absolute percentage change to show biggest changes (positive or negative)
            df_sorted = state_data.copy()
            df_sorted["abs_change"] = df_sorted["percent_change"].abs()
            top_states = df_sorted.nlargest(10, "abs_change")[
                ["state_name", "percent_change", "baseline", "future", "dominant_transition"]
            ]

            # Format the display
            top_states["Change (%)"] = top_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
            top_states["2025 Baseline"] = top_states["baseline"].apply(lambda x: f"{x:,.0f}")
            top_states["2070 Projection"] = top_states["future"].apply(lambda x: f"{x:,.0f}")

            display_df = top_states[
                ["state_name", "Change (%)", "2025 Baseline", "2070 Projection", "dominant_transition"]
            ]
            display_df.columns = ["State", "Change (%)", "2025 (acres)", "2070 (acres)", "Dominant Transition"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    with viz_tab2:
        st.markdown("#### Land Use Transition Flows")
        st.markdown("**Sankey diagram showing flows between land use types**")

        # Add informative help text
        with st.expander("ℹ️ How to read this diagram", expanded=False):
            st.markdown("""
            - **Width of flows** represents the total acres transitioning
            - **Node size** shows the total volume of land involved
            - **Colors** distinguish different land use types
            - **Hover** over flows or nodes for detailed information
            - Use filters below to explore specific transitions
            """)

        # Add filters with better layout
        st.markdown("##### 🔍 Filter Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            from_filter = st.selectbox(
                "From Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_from",
                help="Filter by source land use type",
            )

        with col2:
            to_filter = st.selectbox(
                "To Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_to",
                help="Filter by destination land use type",
            )

        with col3:
            # Create list of states for dropdown
            state_options = ["All"] + sorted(StateMapper.get_all_names())
            state_filter = st.selectbox(
                "State", state_options, key="sankey_state", help="Filter by state to see regional land use transitions"
            )

        # Load and display Sankey diagram with loading indicator
        with st.spinner("Loading transition flows..."):
            sankey_data, sankey_error = load_sankey_data(from_filter, to_filter, state_filter)

        if sankey_error:
            if "No transitions found" in sankey_error:
                st.warning(f"⚠️ {sankey_error}")
            else:
                st.error(f"❌ {sankey_error}")
        elif sankey_data is not None and not sankey_data.empty:
            # Display the Sankey diagram
            fig = create_sankey_diagram(sankey_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Enhanced statistics section
            st.markdown("---")
            st.markdown("##### 📊 Transition Statistics")

            # Create metrics row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_flow = sankey_data["value"].sum()
                st.metric("Total Acres", f"{total_flow / 1e6:.1f}M", help="Total acres transitioning between land uses")

            with col2:
                num_transitions = len(sankey_data)
                st.metric("Transitions Shown", num_transitions, help="Number of transition pathways displayed")

            with col3:
                avg_flow = sankey_data["value"].mean()
                st.metric("Average Flow", f"{avg_flow / 1e6:.1f}M", help="Average acres per transition")

            with col4:
                if "county_count" in sankey_data.columns:
                    total_counties = sankey_data["county_count"].sum()
                    st.metric("Counties Affected", total_counties, help="Number of counties with transitions")
                else:
                    max_scenarios = sankey_data["scenario_count"].max()
                    st.metric("Max Scenarios", max_scenarios, help="Maximum scenarios for any transition")

            # Show detailed transition table
            st.markdown("##### 📋 Detailed Transition Data")

            # Prepare display dataframe with better formatting
            display_df = sankey_data.copy()
            display_df["Transition"] = display_df["source"] + " → " + display_df["target"]
            display_df["Acres (M)"] = (display_df["value"] / 1e6).round(2)
            display_df["Scenarios"] = display_df["scenario_count"]

            # Select and reorder columns for display
            display_df = display_df[["Transition", "Acres (M)", "Scenarios"]]

            # Display with custom styling
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Transition": st.column_config.TextColumn(
                        "Land Use Transition",
                        width="medium",
                    ),
                    "Acres (M)": st.column_config.NumberColumn(
                        "Acres (Millions)",
                        format="%.2f",
                        width="small",
                    ),
                    "Scenarios": st.column_config.NumberColumn(
                        "Scenario Count",
                        width="small",
                    ),
                },
            )

            # Add insights
            if num_transitions > 0:
                top_transition = display_df.iloc[0]
                if state_filter and state_filter != "All":
                    st.info(
                        f"💡 **Key Insight for {state_filter}:** The largest transition is {top_transition['Transition']} with {top_transition['Acres (M)']}M acres"
                    )
                else:
                    st.info(
                        f"💡 **Key Insight:** The largest transition is {top_transition['Transition']} with {top_transition['Acres (M)']}M acres"
                    )
        else:
            st.info(
                "📊 No transition data available for the selected filters. Try selecting 'All' for broader results."
            )


def main():
    """Main analytics dashboard"""
    st.title("📊 RPA Assessment Analytics Dashboard")
    st.markdown("**Visualizations and insights from the USDA Forest Service 2020 RPA Assessment**")

    st.markdown("---")

    # Create tabs for different analysis areas
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🌲 Forest Analysis", "🌾 Agricultural Analysis", "🏙️ Urbanization Trends", "🎨 Enhanced Visualizations"]
    )

    with tab1:
        st.markdown("### 🌲 Forest Analysis")
        st.markdown("**Comprehensive analysis of forest gains, losses, and transitions**")

        # Load forest data
        df_loss, df_gain, df_states, forest_error = load_forest_analysis_data()
        if forest_error:
            st.error(f"❌ {forest_error}")
        else:
            # Create sub-tabs for forest analysis
            forest_tab1, forest_tab2 = st.tabs(["📊 Overview", "🗺️ Geographic Distribution"])

            with forest_tab1:
                st.markdown("#### 🌲 Forest Transition Overview")

                if df_loss is not None and df_gain is not None:
                    # Wide layout with main visualization and side metrics
                    main_col, metrics_col = st.columns([4, 2])

                    with main_col:
                        # Show flow chart
                        fig = create_forest_flow_chart(df_loss, df_gain)
                        if fig:
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)

                    with metrics_col:
                        # Key metrics in vertical layout
                        total_loss = df_loss["total_acres"].sum()
                        total_gain = df_gain["total_acres"].sum()
                        net_change = total_gain - total_loss

                        st.markdown("#### 📊 Forest Metrics")

                        st.metric(
                            "🔻 Total Forest Loss",
                            f"{total_loss / 1e6:.1f}M acres",
                            help="Total forest converted to other land uses",
                        )

                        st.metric(
                            "🔺 Total Forest Gain",
                            f"{total_gain / 1e6:.1f}M acres",
                            help="Total land converted to forest",
                        )

                        st.metric(
                            "📊 Net Change",
                            f"{net_change / 1e6:+.1f}M acres",
                            delta=f"{(net_change / total_loss) * 100:+.1f}%",
                            help="Net forest change across all scenarios",
                        )

                        # Quick insight box
                        if net_change < 0:
                            st.error(f"⚠️ Net forest loss of {abs(net_change / 1e6):.1f}M acres projected")
                        else:
                            st.success(f"✅ Net forest gain of {net_change / 1e6:.1f}M acres projected")

                    # Detailed breakdowns in full width
                    st.markdown("---")

                    # Use three columns for detailed analysis
                    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

                    with detail_col1:
                        st.markdown("##### 🔻 Forest Loss Destinations")
                        loss_summary = df_loss.groupby("to_landuse")["total_acres"].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_loss = px.bar(
                            x=loss_summary.values,
                            y=loss_summary.index,
                            orientation="h",
                            title="Where Forests Convert To",
                            labels={"x": "Acres", "y": "Land Use Type"},
                            color=loss_summary.values,
                            color_continuous_scale=RPA_BROWN_SCALE,
                        )
                        fig_loss.update_layout(height=300, showlegend=False)
                        st.plotly_chart(fig_loss, use_container_width=True)

                    with detail_col2:
                        st.markdown("##### 🔺 Forest Gain Sources")
                        gain_summary = df_gain.groupby("from_landuse")["total_acres"].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_gain = px.bar(
                            x=gain_summary.values,
                            y=gain_summary.index,
                            orientation="h",
                            title="Where Forest Gains Come From",
                            labels={"x": "Acres", "y": "Land Use Type"},
                            color=gain_summary.values,
                            color_continuous_scale=RPA_GREEN_SCALE,
                        )
                        fig_gain.update_layout(height=300, showlegend=False)
                        st.plotly_chart(fig_gain, use_container_width=True)

                    with detail_col3:
                        st.markdown("##### 📊 Transition Summary")

                        # Combined summary table
                        loss_pct = loss_summary / loss_summary.sum() * 100
                        gain_pct = gain_summary / gain_summary.sum() * 100

                        summary_data = []
                        for landuse in set(loss_summary.index) | set(gain_summary.index):
                            summary_data.append(
                                {
                                    "Land Use": landuse,
                                    "Loss %": f"{loss_pct.get(landuse, 0):.1f}%" if landuse in loss_pct else "-",
                                    "Gain %": f"{gain_pct.get(landuse, 0):.1f}%" if landuse in gain_pct else "-",
                                }
                            )

                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No forest transition data available")

            with forest_tab2:
                st.markdown("#### Geographic Distribution of Forest Changes")

                if df_states is not None and not df_states.empty:
                    # Explanation of the metric
                    with st.expander("💡 Understanding the Map Metric", expanded=False):
                        st.info("""
                        **How to interpret the percentage change:**

                        This map shows the **change in forest transition activity between 2020-2030 and 2060-2070**:
                        - **Negative % (purple)**: Decreasing forest transition activity over time
                        - **Near 0% (teal)**: Stable forest transition activity
                        - **Positive % (yellow)**: Increasing forest transition activity over time

                        **Formula:** ((2070 Activity - 2025 Activity) / 2025 Activity) × 100

                        This metric reveals whether forest-related land use changes are accelerating or
                        decelerating in each state over the projection period.
                        """)

                    # Show map
                    fig = create_forest_state_map(df_states)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

                    # State rankings
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("##### 🌲 Top States - Forest Gain (%)")
                        top_gain_states = df_states.nlargest(10, "percent_change")[
                            ["state_name", "percent_change", "net_change", "forest_gain"]
                        ]
                        top_gain_states["Percent Change"] = top_gain_states["percent_change"].apply(
                            lambda x: f"{x:+.1f}%"
                        )
                        top_gain_states["Net Change"] = top_gain_states["net_change"].apply(
                            lambda x: f"{x / 1e6:+.2f}M"
                        )
                        top_gain_states["Total Gain"] = top_gain_states["forest_gain"].apply(
                            lambda x: f"{x / 1e6:.2f}M"
                        )
                        display_df = top_gain_states[
                            ["state_name", "Percent Change", "Net Change", "Total Gain"]
                        ].copy()
                        st.dataframe(
                            display_df.rename(columns={"state_name": "State"}),
                            use_container_width=True,
                            hide_index=True,
                        )

                    with col2:
                        st.markdown("##### 🔥 Top States - Forest Loss (%)")
                        top_loss_states = df_states.nsmallest(10, "percent_change")[
                            ["state_name", "percent_change", "net_change", "forest_loss"]
                        ]
                        top_loss_states["Percent Change"] = top_loss_states["percent_change"].apply(
                            lambda x: f"{x:+.1f}%"
                        )
                        top_loss_states["Net Change"] = top_loss_states["net_change"].apply(
                            lambda x: f"{x / 1e6:+.2f}M"
                        )
                        top_loss_states["Total Loss"] = top_loss_states["forest_loss"].apply(
                            lambda x: f"{x / 1e6:.2f}M"
                        )
                        display_df = top_loss_states[
                            ["state_name", "Percent Change", "Net Change", "Total Loss"]
                        ].copy()
                        st.dataframe(
                            display_df.rename(columns={"state_name": "State"}),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # Summary insights
                    st.markdown("##### 🔍 Geographic Insights")
                    gaining_states = len(df_states[df_states["net_change"] > 0])
                    losing_states = len(df_states[df_states["net_change"] < 0])

                    st.info(f"""
                    **Key Findings:**
                    - {gaining_states} states show net forest gain
                    - {losing_states} states show net forest loss
                    - Regional patterns suggest climate and development pressures vary significantly by location
                    """)
                else:
                    st.info("No geographic data available")

    with tab2:
        st.markdown("### 🌾 Agricultural Analysis")
        st.markdown("**Comprehensive analysis of agricultural gains, losses, and transitions**")

        # Load agricultural data
        df_loss, df_gain, df_states, ag_error = load_agricultural_analysis_data()

        if ag_error:
            st.error(f"❌ {ag_error}")
        else:
            # Create sub-tabs for agricultural analysis
            ag_tab1, ag_tab2 = st.tabs(["📊 Overview", "🗺️ Geographic Distribution"])

            with ag_tab1:
                st.markdown("#### 🌾 Agricultural Transition Overview")

                if df_loss is not None and df_gain is not None:
                    # Wide layout with main visualization and side metrics
                    main_col, metrics_col = st.columns([4, 2])

                    with main_col:
                        # Show agricultural flow chart
                        fig = create_agricultural_flow_chart(df_loss, df_gain)
                        if fig:
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)

                    with metrics_col:
                        # Key metrics in vertical layout
                        total_loss = df_loss["total_acres"].sum()
                        total_gain = df_gain["total_acres"].sum()
                        net_change = total_gain - total_loss

                        st.markdown("#### 📊 Agricultural Metrics")

                        st.metric(
                            "🔻 Total Agricultural Loss",
                            f"{total_loss / 1e6:.1f}M acres",
                            help="Total agricultural land converted to other uses",
                        )

                        st.metric(
                            "🔺 Total Agricultural Gain",
                            f"{total_gain / 1e6:.1f}M acres",
                            help="Total land converted to agriculture",
                        )

                        st.metric(
                            "📊 Net Change",
                            f"{net_change / 1e6:+.1f}M acres",
                            delta=f"{(net_change / total_loss) * 100:+.1f}%" if total_loss > 0 else "N/A",
                            help="Net agricultural change across all scenarios",
                        )

                        # Quick insight box
                        if net_change < 0:
                            st.error(f"⚠️ Net agricultural loss of {abs(net_change / 1e6):.1f}M acres projected")
                        else:
                            st.success(f"✅ Net agricultural gain of {net_change / 1e6:.1f}M acres projected")

                    # Detailed breakdowns in full width
                    st.markdown("---")

                    # Use three columns for detailed analysis
                    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

                    with detail_col1:
                        st.markdown("##### 🔻 Agricultural Loss Destinations")
                        loss_summary = df_loss.groupby("to_landuse")["total_acres"].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_loss = px.bar(
                            x=loss_summary.values[:5],
                            y=loss_summary.index[:5],
                            orientation="h",
                            title="Where Agricultural Land Goes",
                            labels={"x": "Acres", "y": "Land Use Type"},
                            color_discrete_sequence=[RPA_COLORS["pink"]],
                        )
                        fig_loss.update_layout(
                            height=250, showlegend=False, xaxis_tickformat=".2s", margin=dict(t=30, b=0)
                        )
                        st.plotly_chart(fig_loss, use_container_width=True)

                    with detail_col2:
                        st.markdown("##### 🔺 Agricultural Gain Sources")
                        gain_summary = df_gain.groupby("from_landuse")["total_acres"].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_gain = px.bar(
                            x=gain_summary.values[:5],
                            y=gain_summary.index[:5],
                            orientation="h",
                            title="What Becomes Agricultural Land",
                            labels={"x": "Acres", "y": "Land Use Type"},
                            color_discrete_sequence=[RPA_COLORS["medium_green"]],
                        )
                        fig_gain.update_layout(
                            height=250, showlegend=False, xaxis_tickformat=".2s", margin=dict(t=30, b=0)
                        )
                        st.plotly_chart(fig_gain, use_container_width=True)

                    with detail_col3:
                        st.markdown("##### 📈 Scenario Comparison")
                        # Show RCP comparison
                        rcp_loss = df_loss.groupby("rcp_scenario")["total_acres"].sum()
                        rcp_gain = df_gain.groupby("rcp_scenario")["total_acres"].sum()

                        comparison_df = pd.DataFrame(
                            {
                                "Scenario": ["RCP4.5", "RCP8.5"],
                                "Loss (M acres)": [rcp_loss.get("rcp45", 0) / 1e6, rcp_loss.get("rcp85", 0) / 1e6],
                                "Gain (M acres)": [rcp_gain.get("rcp45", 0) / 1e6, rcp_gain.get("rcp85", 0) / 1e6],
                            }
                        )
                        comparison_df["Net (M acres)"] = (
                            comparison_df["Gain (M acres)"] - comparison_df["Loss (M acres)"]
                        )

                        st.dataframe(comparison_df.round(1), use_container_width=True, hide_index=True)
                else:
                    st.info("📊 No data available for agricultural transitions")

            with ag_tab2:
                st.markdown("#### Geographic Distribution of Agricultural Changes")

                if df_states is not None and not df_states.empty:
                    # Explanation of the metric
                    with st.expander("💡 Understanding the Map Metric", expanded=False):
                        st.info("""
                        **How to interpret the percentage change:**

                        This map shows the **change in agricultural transition activity between 2020-2030 and 2060-2070**:
                        - **Negative % (purple)**: Decreasing agricultural transition activity over time
                        - **Near 0% (teal)**: Stable agricultural transition activity
                        - **Positive % (yellow)**: Increasing agricultural transition activity over time

                        **Formula:** ((2070 Activity - 2025 Activity) / 2025 Activity) × 100

                        This metric reveals whether agriculture-related land use changes are accelerating or
                        decelerating in each state over the projection period.
                        """)

                    # Show map
                    fig = create_agricultural_state_map(df_states)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

                    # State rankings
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("##### 🌾 Top States - Agricultural Gain (%)")
                        top_gain_states = df_states.nlargest(10, "percent_change")[
                            ["state_name", "percent_change", "net_change", "ag_gain"]
                        ]
                        top_gain_states["Percent Change"] = top_gain_states["percent_change"].apply(
                            lambda x: f"{x:+.1f}%"
                        )
                        top_gain_states["Net Change"] = top_gain_states["net_change"].apply(
                            lambda x: f"{x / 1e6:+.2f}M"
                        )
                        top_gain_states["Total Gain"] = top_gain_states["ag_gain"].apply(lambda x: f"{x / 1e6:.2f}M")
                        display_df = top_gain_states[
                            ["state_name", "Percent Change", "Net Change", "Total Gain"]
                        ].copy()
                        st.dataframe(
                            display_df.rename(columns={"state_name": "State"}),
                            use_container_width=True,
                            hide_index=True,
                        )

                    with col2:
                        st.markdown("##### 🍂 Top States - Agricultural Loss (%)")
                        top_loss_states = df_states.nsmallest(10, "percent_change")[
                            ["state_name", "percent_change", "net_change", "ag_loss"]
                        ]
                        top_loss_states["Percent Change"] = top_loss_states["percent_change"].apply(
                            lambda x: f"{x:+.1f}%"
                        )
                        top_loss_states["Net Change"] = top_loss_states["net_change"].apply(
                            lambda x: f"{x / 1e6:+.2f}M"
                        )
                        top_loss_states["Total Loss"] = top_loss_states["ag_loss"].apply(lambda x: f"{x / 1e6:.2f}M")
                        display_df = top_loss_states[
                            ["state_name", "Percent Change", "Net Change", "Total Loss"]
                        ].copy()
                        st.dataframe(
                            display_df.rename(columns={"state_name": "State"}),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # Summary insights
                    st.markdown("##### 🔍 Geographic Insights")
                    gaining_states = len(df_states[df_states["net_change"] > 0])
                    losing_states = len(df_states[df_states["net_change"] < 0])

                    st.info(f"""
                    **Key Findings:**
                    - {gaining_states} states show net agricultural gain
                    - {losing_states} states show net agricultural loss
                    - Regional patterns suggest varying development and conservation pressures
                    """)
                else:
                    st.info("No geographic data available")

    with tab3:
        st.markdown("### 🏙️ Urbanization Patterns")
        st.markdown("**Comprehensive analysis of urban expansion across states and land use sources**")

        urban_data, urban_error = load_urbanization_data()
        if urban_error:
            st.error(f"❌ {urban_error}")
        elif urban_data is not None and not urban_data.empty:
            # Create two-column layout for urbanization analysis
            viz_col1, viz_col2 = st.columns(2)

            with viz_col1:
                # Sources of urbanization
                st.markdown("#### 🏘️ Urbanization Sources")
                source_breakdown = (
                    urban_data.groupby("from_landuse")["total_acres_urbanized"].sum().sort_values(ascending=False)
                )

                fig_pie = px.pie(
                    values=source_breakdown.values,
                    names=source_breakdown.index,
                    title="Land Converted to Urban",
                    color_discrete_sequence=RPA_COLOR_SEQUENCE,
                    hole=0.4,  # Donut chart
                )
                fig_pie.update_traces(textinfo="percent+label")
                fig_pie.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            with viz_col2:
                # Top converting states map preview
                st.markdown("#### 📍 Geographic Distribution")
                state_totals = urban_data.groupby("state_code")["total_acres_urbanized"].sum().reset_index()
                state_totals["state_abbr"] = state_totals["state_code"].map(StateMapper.FIPS_TO_ABBREV)

                # Mini choropleth
                fig_map = px.choropleth(
                    state_totals.head(20),
                    locations="state_abbr",
                    locationmode="USA-states",
                    color="total_acres_urbanized",
                    color_continuous_scale=RPA_BROWN_SCALE,
                    title="Urban Expansion Hotspots",
                )
                fig_map.update_layout(geo={"scope": "usa"}, height=350, margin={"r": 0, "t": 30, "l": 0, "b": 0})
                st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": False})

            # Detailed insights in full width
            st.markdown("---")

            # Create expandable sections for detailed analysis
            with st.container():
                detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

                with detail_col1:
                    st.markdown("#### 🔍 Key Insights")
                    if not urban_data.empty:
                        top_state_data = (
                            urban_data.groupby("state_code")["total_acres_urbanized"].sum().sort_values(ascending=False)
                        )
                        top_state = top_state_data.index[0]
                        top_state_acres = top_state_data.iloc[0]

                        st.success(f"""
                        **Urban Development Patterns:**
                        - **Top State:** {StateMapper.FIPS_TO_NAME.get(top_state, top_state)} ({top_state_acres / 1e6:.1f}M acres)
                        - **Primary Source:** {source_breakdown.index[0]} → Urban
                        - **Total Urbanized:** {source_breakdown.sum() / 1e6:.1f}M acres nationwide
                        """)

                with detail_col2:
                    st.markdown("#### 📊 Source Breakdown")
                    source_df = pd.DataFrame(
                        {
                            "Land Type": source_breakdown.index,
                            "Acres": source_breakdown.apply(lambda x: f"{x / 1e6:.2f}M"),
                            "Percent": source_breakdown.apply(lambda x: f"{x / source_breakdown.sum() * 100:.1f}%"),
                        }
                    )
                    st.dataframe(source_df, use_container_width=True, hide_index=True)

                with detail_col3:
                    st.markdown("#### 🏆 Top 10 States")
                    top_states_df = top_state_data.head(10).reset_index()
                    top_states_df["state_name"] = top_states_df["state_code"].map(StateMapper.FIPS_TO_NAME)
                    top_states_df["acres"] = top_states_df["total_acres_urbanized"].apply(lambda x: f"{x / 1e6:.2f}M")
                    display_df = top_states_df[["state_name", "acres"]].copy()
                    display_df.columns = ["State", "Urban Expansion"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("📊 No urbanization data available")

    with tab4:
        show_enhanced_visualizations()

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 Want to explore further?**
    - Use the **Chat** interface for custom natural language queries
    - Visit the **Data Explorer** for advanced SQL analysis
    - Check **Settings** for configuration options
    """)


if __name__ == "__main__":
    main()
