"""
Visualization utilities for charts and maps.
"""

import logging
from typing import Optional, Dict, Any, List
import pandas as pd
import plotly.graph_objects as go
import folium
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from ..config import (
    LAND_USE_COLORS, MAP_CENTER, MAP_ZOOM_START, 
    SANKEY_CHART_HEIGHT, SANKEY_CHART_MARGINS,
    SANKEY_NODE_PAD, SANKEY_NODE_THICKNESS
)

logger = logging.getLogger(__name__)


class ChartUtils:
    """Utility class for creating charts and visualizations."""
    
    @staticmethod
    def create_sankey_diagram(
        transitions_data: pd.DataFrame, 
        title: str, 
        scenario_name: str,
        height: Optional[int] = None
    ) -> go.Figure:
        """
        Create a Sankey diagram showing land use transitions.
        
        Args:
            transitions_data: DataFrame with from_category, to_category, and total_area columns
            title: Title for the diagram
            scenario_name: Scenario name for filtering
            height: Optional height for the diagram (defaults to config value)
        
        Returns:
            Plotly figure object
        """
        # Filter data for the specific scenario
        filtered_data = transitions_data[transitions_data["scenario_name"] == scenario_name]
        
        # Aggregate data across all time periods
        sankey_data = filtered_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
        
        # Filter out transitions where land use stays the same (e.g., Urban to Urban)
        sankey_data = sankey_data[sankey_data["from_category"] != sankey_data["to_category"]]
        
        # Get unique land use categories
        all_categories = list(set(sankey_data["from_category"].unique()) | set(sankey_data["to_category"].unique()))
        
        # Create node indices
        node_indices = {category: i for i, category in enumerate(all_categories)}
        
        # Prepare data for Sankey
        source = [node_indices[cat] for cat in sankey_data["from_category"]]
        target = [node_indices[cat] for cat in sankey_data["to_category"]]
        value = sankey_data["total_area"].tolist()
        
        # Assign colors to nodes
        node_colors = [LAND_USE_COLORS.get(cat, '#D3D3D3') for cat in all_categories]
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=SANKEY_NODE_PAD,
                thickness=SANKEY_NODE_THICKNESS,
                line=dict(color="black", width=0.5),
                label=all_categories,
                color=node_colors
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color='rgba(255, 0, 255, 0.4)'  # Semi-transparent links
            )
        )])
        
        fig.update_layout(
            title_text=title,
            font_size=12,
            height=height or SANKEY_CHART_HEIGHT,
            margin=SANKEY_CHART_MARGINS
        )
        
        return fig
    
    @staticmethod
    def create_temporal_line_chart(
        temporal_data: List[pd.DataFrame],
        title: str,
        ylabel: str = "Percentage Change from Baseline (%)",
        figsize: tuple = (12, 8)
    ) -> plt.Figure:
        """
        Create a temporal line chart with dark mode styling.
        
        Args:
            temporal_data: List of DataFrames with temporal data
            title: Chart title
            ylabel: Y-axis label
            figsize: Figure size
            
        Returns:
            Matplotlib figure
        """
        # Set dark mode style
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=figsize, dpi=300)
        fig.patch.set_facecolor('#0E1117')  # Streamlit dark background
        ax.set_facecolor('#0E1117')
        
        # Sort temporal_data by percentage change (highest to lowest)
        location_pct_changes = []
        for location_data in temporal_data:
            final_pct_change = location_data["pct_change"].iloc[-1] if len(location_data) > 0 else 0
            location_pct_changes.append((final_pct_change, location_data))
        
        # Sort by final percentage change (descending) and extract sorted data
        location_pct_changes.sort(key=lambda x: x[0], reverse=True)
        temporal_data_sorted = [item[1] for item in location_pct_changes]
        
        # Use viridis color palette for better distinction in dark mode
        colors = plt.cm.viridis(np.linspace(0, 1, len(temporal_data_sorted)))
        
        for i, location_data in enumerate(temporal_data_sorted):
            # Extract end years from decade names (e.g., "2020-2030" -> "2030")
            end_years = [decade.split('-')[1] for decade in location_data["decade_name"]]
            
            ax.plot(end_years, location_data["pct_change"], 
                   marker='o', linewidth=2.5, markersize=8, 
                   label=location_data["location"].iloc[0],
                   color=colors[i], markerfacecolor='#0E1117', 
                   markeredgewidth=2, markeredgecolor=colors[i])
        
        # Styling for dark mode
        ax.set_xlabel("Year", fontsize=14, fontweight='bold', color='white')
        ax.set_ylabel(ylabel, fontsize=14, fontweight='bold', color='white')
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='white')
        
        # Legend at bottom, horizontal
        ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', 
                 ncol=2, frameon=False, fontsize=11, labelcolor='white')
        
        # Grid and styling for dark mode
        ax.grid(True, alpha=0.3, linestyle='--', color='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_linewidth(0.5)
        ax.spines['bottom'].set_color('white')
        
        # Tick styling for dark mode
        ax.tick_params(axis='both', which='major', labelsize=12, colors='white')
        plt.xticks(rotation=0)  # Keep x-axis labels horizontal
        
        # Add horizontal line at 0%
        ax.axhline(y=0, color='white', linestyle='-', alpha=0.5, linewidth=0.8)
        
        plt.tight_layout()
        return fig


class MapUtils:
    """Utility class for creating maps and geographic visualizations."""
    
    @staticmethod
    def create_state_map(state_data: pd.DataFrame, title: str, states_geojson: Optional[Dict[str, Any]] = None) -> Optional[folium.Map]:
        """
        Create a folium choropleth map of states using raw GeoJSON.
        
        Args:
            state_data: DataFrame with state data for visualization
            title: Map title
            states_geojson: Optional GeoJSON data for states
            
        Returns:
            Folium map object or None if creation fails
        """
        # If states data couldn't be loaded, return None
        if states_geojson is None:
            return None
        
        # Center the map on the continental US
        state_map = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM_START, scrollWheelZoom=False)
        
        try:
            # Create choropleth layer using raw GeoJSON
            choropleth = folium.Choropleth(
                geo_data=states_geojson,  # Raw GeoJSON dict
                name="choropleth",
                data=state_data,
                columns=["name", "total_area"],
                key_on="feature.properties.name",
                fill_color="YlOrRd",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name="Acres Changed",
                highlight=True
            ).add_to(state_map)
            
            # Add tooltips
            choropleth.geojson.add_child(
                folium.features.GeoJsonTooltip(
                    fields=["name"],
                    aliases=["State:"],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
                )
            )
            
        except Exception as e:
            st.warning(f"Could not create choropleth layer: {e}")
            logger.warning(f"Failed to create choropleth layer: {e}")
            # Add basic GeoJSON layer without data binding
            folium.GeoJson(
                states_geojson,
                style_function=lambda feature: {
                    'fillColor': '#ffff00',
                    'color': 'black',
                    'weight': 2,
                    'fillOpacity': 0.7,
                }
            ).add_to(state_map)
        
        # Add title as a caption
        title_html = f'''
            <h3 align="center" style="font-size:16px"><b>{title}</b></h3>
        '''
        state_map.get_root().html.add_child(folium.Element(title_html))
        
        return state_map 