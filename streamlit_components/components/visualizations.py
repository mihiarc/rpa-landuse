"""
Visualization components for the RPA Land Use Viewer application.

This module contains reusable visualization functions for charts, maps,
and other data displays.
"""
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import folium
import streamlit as st
from typing import Dict, List, Optional, Tuple
import numpy as np


def create_land_use_sankey(df: pd.DataFrame, title: str = "Land Use Transitions") -> go.Figure:
    """
    Create a Sankey diagram for land use transitions.
    
    Args:
        df: DataFrame with from_category, to_category, and total_area columns
        title: Title for the diagram
        
    Returns:
        go.Figure: Plotly Sankey diagram
    """
    # Prepare data for Sankey diagram
    df_filtered = df[df['from_category'] != df['to_category']]
    
    # Create node labels
    from_categories = df_filtered['from_category'].unique()
    to_categories = df_filtered['to_category'].unique()
    all_categories = list(set(list(from_categories) + list(to_categories)))
    
    # Create source and target indices
    source_indices = []
    target_indices = []
    values = []
    
    for _, row in df_filtered.iterrows():
        source_idx = all_categories.index(row['from_category'])
        target_idx = all_categories.index(row['to_category'])
        source_indices.append(source_idx)
        target_indices.append(target_idx)
        values.append(row['total_area'])
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_categories,
            color="blue"
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=values
        )
    )])
    
    fig.update_layout(
        title_text=title,
        font_size=12,
        height=600
    )
    
    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, 
                    title: str = "", xlabel: str = "", ylabel: str = "",
                    color: str = "#4472C4", figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
    """
    Create a styled bar chart using matplotlib.
    
    Args:
        df: DataFrame with data to plot
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        color: Bar color
        figsize: Figure size tuple
        
    Returns:
        plt.Figure: Matplotlib figure
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=figsize, dpi=300)
    
    bars = ax.bar(df[x_col], df[y_col], color=color, edgecolor='white', linewidth=0.5)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}',
                ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Style improvements
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)
    
    # Rotate x-axis labels if needed
    if len(df[x_col].astype(str).str.len().max()) > 10:
        plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    return fig


def create_time_series_plot(df: pd.DataFrame, x_col: str, y_cols: List[str],
                           title: str = "", xlabel: str = "", ylabel: str = "",
                           colors: Optional[List[str]] = None) -> plt.Figure:
    """
    Create a time series plot with multiple lines.
    
    Args:
        df: DataFrame with time series data
        x_col: Column name for x-axis (time)
        y_cols: List of column names for y-axis values
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        colors: Optional list of colors for each line
        
    Returns:
        plt.Figure: Matplotlib figure
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    if colors is None:
        colors = plt.cm.tab10(range(len(y_cols)))
    
    for i, col in enumerate(y_cols):
        ax.plot(df[x_col], df[col], marker='o', linewidth=2,
                label=col, color=colors[i])
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def create_state_choropleth(state_data: pd.DataFrame, value_col: str,
                           title: str = "", geojson_data: dict = None) -> folium.Map:
    """
    Create a choropleth map for state-level data.
    
    Args:
        state_data: DataFrame with state_name and value columns
        value_col: Column name containing values to visualize
        title: Map title
        geojson_data: GeoJSON data for state boundaries
        
    Returns:
        folium.Map: Folium choropleth map
    """
    # Create base map
    m = folium.Map(
        location=[39.50, -98.35],  # Center of US
        zoom_start=4,
        tiles='OpenStreetMap'
    )
    
    if geojson_data and not state_data.empty:
        # Create choropleth
        folium.Choropleth(
            geo_data=geojson_data,
            name='choropleth',
            data=state_data,
            columns=['state_name', value_col],
            key_on='feature.properties.name',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=title,
            nan_fill_color='white'
        ).add_to(m)
        
        # Add tooltips
        folium.features.GeoJsonTooltip(
            fields=['name'],
            labels=True,
            sticky=True
        ).add_to(m)
    
    return m


def display_metrics_row(metrics: Dict[str, Tuple[str, str]], cols_per_row: int = 4):
    """
    Display a row of metric cards.
    
    Args:
        metrics: Dictionary of {label: (value, delta)} 
        cols_per_row: Number of columns per row
    """
    cols = st.columns(cols_per_row)
    for i, (label, (value, delta)) in enumerate(metrics.items()):
        col_idx = i % cols_per_row
        with cols[col_idx]:
            st.metric(label=label, value=value, delta=delta)


def create_summary_table(df: pd.DataFrame, group_cols: List[str], 
                        value_col: str, agg_func: str = 'sum') -> pd.DataFrame:
    """
    Create a summary table with aggregated values.
    
    Args:
        df: Input DataFrame
        group_cols: Columns to group by
        value_col: Column to aggregate
        agg_func: Aggregation function ('sum', 'mean', 'count', etc.)
        
    Returns:
        pd.DataFrame: Aggregated summary table
    """
    summary = df.groupby(group_cols)[value_col].agg(agg_func).reset_index()
    
    # Format numbers for display
    if agg_func in ['sum', 'mean']:
        summary[value_col] = summary[value_col].apply(lambda x: f"{x:,.0f}")
    
    return summary


def plot_comparison_chart(data_dict: Dict[str, pd.DataFrame], 
                         value_col: str, category_col: str,
                         title: str = "Comparison Chart") -> go.Figure:
    """
    Create a grouped bar chart comparing multiple datasets.
    
    Args:
        data_dict: Dictionary of {dataset_name: DataFrame}
        value_col: Column containing values to plot
        category_col: Column for grouping
        title: Chart title
        
    Returns:
        go.Figure: Plotly grouped bar chart
    """
    fig = go.Figure()
    
    for name, df in data_dict.items():
        fig.add_trace(go.Bar(
            name=name,
            x=df[category_col],
            y=df[value_col]
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=category_col,
        yaxis_title=value_col,
        barmode='group',
        height=500
    )
    
    return fig


def create_pie_chart(df: pd.DataFrame, labels_col: str, values_col: str,
                    title: str = "") -> go.Figure:
    """
    Create a pie chart.
    
    Args:
        df: DataFrame with data
        labels_col: Column for pie slice labels
        values_col: Column for pie slice values
        title: Chart title
        
    Returns:
        go.Figure: Plotly pie chart
    """
    fig = go.Figure(data=[go.Pie(
        labels=df[labels_col],
        values=df[values_col],
        hole=0.3  # Creates a donut chart
    )])
    
    fig.update_layout(
        title=title,
        height=500
    )
    
    return fig