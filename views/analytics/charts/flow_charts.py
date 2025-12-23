"""Flow and waterfall chart visualizations.

Charts for visualizing land use transition flows, gains, and losses.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_flow_chart(
    df_loss: pd.DataFrame,
    df_gain: pd.DataFrame,
    title: str,
    loss_column: str = "to_landuse",
    gain_column: str = "from_landuse",
    value_column: str = "total_acres",
) -> Optional[go.Figure]:
    """Create a generic flow chart showing gains and losses.

    Args:
        df_loss: DataFrame with loss data
        df_gain: DataFrame with gain data
        title: Chart title
        loss_column: Column name for loss categories
        gain_column: Column name for gain categories
        value_column: Column containing acre values

    Returns:
        Plotly figure or None if data is invalid
    """
    if df_loss is None or df_gain is None:
        return None

    fig = go.Figure()

    # Aggregate data
    loss_by_type = df_loss.groupby(loss_column)[value_column].sum().sort_values(ascending=False)
    gain_by_type = df_gain.groupby(gain_column)[value_column].sum().sort_values(ascending=False)

    # Build chart data
    x_labels = []
    y_values = []
    colors = []

    # Add losses (negative values) - Blue for colorblind safety
    for landuse, acres in loss_by_type.items():
        x_labels.append(f"To {landuse}")
        y_values.append(-acres)
        colors.append("rgba(33, 102, 172, 0.7)")

    # Add gains (positive values) - Orange for colorblind safety
    for landuse, acres in gain_by_type.items():
        x_labels.append(f"From {landuse}")
        y_values.append(acres)
        colors.append("rgba(217, 95, 2, 0.7)")

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
            "text": f"{title}: Net Change = {net_change / 1e6:+.1f}M acres",
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


def create_forest_flow_chart(
    df_loss: pd.DataFrame,
    df_gain: pd.DataFrame,
) -> Optional[go.Figure]:
    """Create forest transition flow chart.

    Args:
        df_loss: DataFrame with forest loss data
        df_gain: DataFrame with forest gain data

    Returns:
        Plotly figure or None if data is invalid
    """
    return create_flow_chart(
        df_loss=df_loss,
        df_gain=df_gain,
        title="Forest Transitions",
        loss_column="to_landuse",
        gain_column="from_landuse",
    )


def create_agricultural_flow_chart(
    df_loss: pd.DataFrame,
    df_gain: pd.DataFrame,
) -> Optional[go.Figure]:
    """Create agricultural transition flow chart.

    Args:
        df_loss: DataFrame with agricultural loss data
        df_gain: DataFrame with agricultural gain data

    Returns:
        Plotly figure or None if data is invalid
    """
    if df_loss is None or df_gain is None:
        return None

    # Aggregate data
    loss_by_type = df_loss.groupby("to_landuse")["total_acres"].sum().to_dict()
    gain_by_type = df_gain.groupby("from_landuse")["total_acres"].sum().to_dict()

    # Build chart data
    x_labels = []
    y_values = []
    colors = []

    # Add losses (negative values) - Blue for colorblind safety
    for landuse, acres in loss_by_type.items():
        x_labels.append(f"To {landuse}")
        y_values.append(-acres)
        colors.append("rgba(33, 102, 172, 0.7)")

    # Add gains (positive values) - Orange for colorblind safety
    for landuse, acres in gain_by_type.items():
        x_labels.append(f"From {landuse}")
        y_values.append(acres)
        colors.append("rgba(217, 95, 2, 0.7)")

    # Create figure with subplots compatibility
    fig = go.Figure()

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


def create_animated_timeline(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create animated timeline of land use transitions.

    Args:
        df: DataFrame with timeline data including start_year, rcp_scenario,
            from_landuse, to_landuse, and total_acres columns

    Returns:
        Plotly figure with animation or None if data is invalid
    """
    if df is None or df.empty:
        return None

    # Create transition labels
    df = df.copy()
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
