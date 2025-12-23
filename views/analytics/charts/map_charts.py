"""Map and geographic chart visualizations.

Choropleth maps, Sankey diagrams, and state-level visualizations.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ..constants import (
    CHART_HEIGHT_LARGE,
    CHART_HEIGHT_MEDIUM,
    RPA_BROWN_SCALE,
    RPA_COLORS,
)
from ..utilities import calculate_symmetric_color_range


def create_state_choropleth(
    df: pd.DataFrame,
    value_column: str,
    title: str,
    hover_data: dict,
    labels: dict,
    color_scale: str = "Viridis",
    max_cap: float = 100.0,
) -> Optional[go.Figure]:
    """Create a generic state choropleth map.

    Args:
        df: DataFrame with state data
        value_column: Column to visualize
        title: Chart title
        hover_data: Hover data configuration
        labels: Label mappings for columns
        color_scale: Plotly color scale name
        max_cap: Maximum absolute value for color range

    Returns:
        Plotly figure or None if data is invalid
    """
    if df is None or df.empty:
        return None

    # Calculate symmetric color range
    color_range = calculate_symmetric_color_range(df, value_column, max_cap=max_cap)

    fig = px.choropleth(
        df,
        locations="state_abbr",
        locationmode="USA-states",
        color=value_column,
        color_continuous_scale=color_scale,
        color_continuous_midpoint=0,
        range_color=color_range,
        hover_name="state_name",
        hover_data=hover_data,
        labels=labels,
        title=title,
    )

    fig.update_layout(
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showlakes": True,
            "lakecolor": "rgba(255, 255, 255, 0.3)",
            "bgcolor": "rgba(0,0,0,0)",
        },
        height=CHART_HEIGHT_LARGE,
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


def create_forest_state_map(df_states: pd.DataFrame) -> Optional[go.Figure]:
    """Create choropleth map showing percentage forest change by state.

    Args:
        df_states: DataFrame with state-level forest data

    Returns:
        Plotly figure or None if data is invalid
    """
    hover_data = {
        "state_abbr": False,
        "percent_change": ":.1f",
        "forest_loss": ":,.0f",
        "forest_gain": ":,.0f",
        "net_change": ":,.0f",
        "baseline_forest": ":,.0f",
        "state_name": False,
    }
    labels = {
        "percent_change": "Change (%)",
        "forest_loss": "2070 Forest Loss (acres)",
        "forest_gain": "2070 Forest Gain (acres)",
        "net_change": "Net Change (acres)",
        "baseline_forest": "2025 Baseline (acres)",
        "future_forest": "2070 Activity (acres)",
    }

    return create_state_choropleth(
        df=df_states,
        value_column="percent_change",
        title="Forest Transition Activity: % Change from 2025 to 2070",
        hover_data=hover_data,
        labels=labels,
    )


def create_agricultural_state_map(df_states: pd.DataFrame) -> Optional[go.Figure]:
    """Create choropleth map showing percentage agricultural change by state.

    Args:
        df_states: DataFrame with state-level agricultural data

    Returns:
        Plotly figure or None if data is invalid
    """
    hover_data = {
        "state_abbr": False,
        "percent_change": ":.1f",
        "ag_loss": ":,.0f",
        "ag_gain": ":,.0f",
        "net_change": ":,.0f",
        "baseline_ag": ":,.0f",
        "state_name": False,
    }
    labels = {
        "percent_change": "Change (%)",
        "ag_loss": "2070 Agricultural Loss (acres)",
        "ag_gain": "2070 Agricultural Gain (acres)",
        "net_change": "Net Change (acres)",
        "baseline_ag": "2025 Baseline (acres)",
        "future_ag": "2070 Activity (acres)",
    }

    return create_state_choropleth(
        df=df_states,
        value_column="percent_change",
        title="Agricultural Transition Activity: % Change from 2025 to 2070",
        hover_data=hover_data,
        labels=labels,
    )


def create_choropleth_map(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create interactive choropleth map showing percentage change between 2025-2070.

    Args:
        df: DataFrame with state transition data

    Returns:
        Plotly figure or None if data is invalid
    """
    if df is None or df.empty:
        return None

    fig = px.choropleth(
        df,
        locations="state_abbr",
        locationmode="USA-states",
        color="percent_change",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        range_color=[-50, 50],
        hover_name="state_name",
        hover_data={
            "state_abbr": False,
            "percent_change": ":.1f",
            "baseline": ":,.0f",
            "future": ":,.0f",
            "dominant_transition": True,
            "state_name": False,
        },
        labels={
            "percent_change": "Change (%)",
            "baseline": "2020-2030 Period (acres)",
            "future": "2060-2070 Period (acres)",
            "dominant_transition": "Most Common Transition",
        },
        title="Change in Land Use Transition Activity: 2020-2030 vs 2060-2070 (%)",
    )

    fig.update_layout(
        geo={
            "scope": "usa",
            "projection_type": "albers usa",
            "showlakes": True,
            "lakecolor": "rgba(255, 255, 255, 0.3)",
            "bgcolor": "rgba(0,0,0,0)",
        },
        height=CHART_HEIGHT_LARGE,
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


def create_sankey_diagram(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create Sankey diagram for land use flows.

    Args:
        df: DataFrame with source, target, value, and optional metadata columns

    Returns:
        Plotly figure or None if data is invalid
    """
    if df is None or df.empty:
        return None

    # Sort by value to ensure most significant flows are visible
    df = df.sort_values("value", ascending=False)

    # Create unique node labels
    source_nodes = df["source"].unique().tolist()
    target_nodes = df["target"].unique().tolist()
    all_nodes = list(dict.fromkeys(source_nodes + target_nodes))
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    # RPA color palette for land use types
    node_colors = {
        "Crop": RPA_COLORS["light_brown"],
        "Pasture": RPA_COLORS["medium_green"],
        "Forest": RPA_COLORS["dark_green"],
        "Urban": RPA_COLORS["dark_blue"],
        "Rangeland": RPA_COLORS["pink"],
    }

    # Prepare hover labels
    hover_labels = []
    for _, row in df.iterrows():
        acres_millions = row["value"] / 1_000_000
        label_text = f"<b>{row['source']} → {row['target']}</b><br>Total: {acres_millions:.2f}M acres<br>"
        if "county_count" in row:
            label_text += f"Counties: {row['county_count']}<br>"
        if "scenario_count" in row:
            label_text += f"Scenarios: {row['scenario_count']}"
        hover_labels.append(label_text)

    # Generate link colors with transparency
    link_colors = []
    for i in range(len(df)):
        source_color = node_colors.get(df.iloc[i]["source"], "#999999")
        if source_color.startswith("#"):
            hex_color = source_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            link_colors.append(f"rgba({r},{g},{b},0.3)")
        else:
            link_colors.append("rgba(150,150,150,0.3)")

    # Create Sankey diagram
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
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
        height=CHART_HEIGHT_LARGE,
        margin={"l": 10, "r": 10, "t": 60, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel={"bgcolor": "white", "font_size": 12},
    )

    return fig


def create_urbanization_chart(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create urbanization analysis visualization.

    Args:
        df: DataFrame with state_code and total_acres_urbanized columns

    Returns:
        Plotly figure or None if data is invalid
    """
    if df is None or df.empty:
        return None

    # Aggregate by state and get top 15
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
        height=CHART_HEIGHT_MEDIUM,
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Acres Urbanized (millions)",
        xaxis_tickformat=".1s",
        font={"size": 12},
    )

    return fig
