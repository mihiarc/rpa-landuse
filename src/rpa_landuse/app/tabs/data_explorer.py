"""
Data Explorer tab implementation.

This tab provides a data explorer for the RPA Land Use Viewer application.

It allows users to explore the datasets at different spatial levels providing an interface for extracting the data in raw formats.
"""

import streamlit as st
import pandas as pd
from .base_tab import BaseTab
from ..config import SCENARIO_DESCRIPTIONS, SPATIAL_LEVELS


class DataExplorerTab(BaseTab):
    """Data Explorer tab for exploring datasets at different spatial levels."""
    
    def render(self) -> None:
        """Render the data explorer tab content."""
        st.header("Data Explorer")
        
        try:
            self._render_controls()
            self._render_data_info()
            self._render_data_preview()
            
        except Exception as e:
            self.show_error("Error rendering data explorer", e)
    
    def _render_controls(self) -> None:
        """Render the control panel for data exploration."""
        # Select RPA scenario to explore
        scenario_options = list(SCENARIO_DESCRIPTIONS.keys())
        selected_scenario_display = st.selectbox("Select RPA Scenario", options=scenario_options)
        
        # Add spatial level selector
        selected_spatial_level = st.selectbox("Select Spatial Level", options=SPATIAL_LEVELS)
        
        # Store selections in session state for use in other methods
        st.session_state['explorer_scenario'] = selected_scenario_display
        st.session_state['explorer_spatial_level'] = selected_spatial_level
    
    def _render_data_info(self) -> None:
        """Render data information and metrics."""
        if 'County-Level Land Use Transitions' in self.data:
            df = self.data['County-Level Land Use Transitions']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Number of Rows", f"{df.shape[0]:,}")
            with col2:
                st.metric("Number of Columns", df.shape[1])
    
    def _render_data_preview(self) -> None:
        """Render data preview and download options."""
        if 'County-Level Land Use Transitions' in self.data:
            df = self.data['County-Level Land Use Transitions']
            
            st.subheader("Data Preview")
            st.dataframe(df.head(100))
            
            # Download option
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f'county_level_data.csv',
                mime='text/csv',
            ) 