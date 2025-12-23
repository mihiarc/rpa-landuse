"""Scenario comparison chart visualizations.

Spider/radar charts and other comparison visualizations.
"""

from typing import List, Optional, Tuple

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..constants import CHART_HEIGHT_MEDIUM


def create_scenario_spider_chart(
    selected_scenarios: List[str],
) -> Tuple[Optional[go.Figure], Optional[str]]:
    """Create spider/radar chart comparing scenarios.

    Args:
        selected_scenarios: List of scenario names to compare

    Returns:
        Tuple of (figure, error_message). Figure is None if error occurred.
    """
    if not selected_scenarios:
        return None, "No scenarios selected"

    # Import here to avoid circular imports
    from ..data_loaders import get_database_connection

    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Import SQLSanitizer for safe query building
        from landuse.utils.security import SQLSanitizer

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
        pivot_df = df.pivot(
            index="scenario_name",
            columns="to_landuse",
            values="total_acres_gained"
        ).fillna(0)

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
            height=CHART_HEIGHT_MEDIUM,
        )

        return fig, None

    except Exception as e:
        return None, f"Error creating comparison: {e}"
