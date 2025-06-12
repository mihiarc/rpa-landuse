#!/usr/bin/env python3
"""
RPA Land Use Viewer - Modular Streamlit Application

This is the main entry point for the RPA Land Use Viewer application.
It uses a modular structure with separate pages and components.
"""
import streamlit as st
from streamlit_components.config.constants import (
    PAGE_CONFIG, APP_TITLE, APP_SUBTITLE, TAB_NAMES
)
from streamlit_components.utils.data_loader import load_parquet_data, load_us_states
from streamlit_components.pages.overview import render_overview_page
from streamlit_components.pages.data_explorer import render_data_explorer_page
from streamlit_components.pages.urbanization_trends import render_urbanization_trends_page
from streamlit_components.pages.natural_language_query import render_natural_language_query_page

# Import additional pages as they are created
# from streamlit_components.pages.land_use_flow import render_land_use_flow_page
# from streamlit_components.pages.forest_transitions import render_forest_transitions_page
# from streamlit_components.pages.agricultural_transitions import render_agricultural_transitions_page
# from streamlit_components.pages.state_map import render_state_map_page


def main():
    """Main application function."""
    
    # Set page configuration
    st.set_page_config(**PAGE_CONFIG)
    
    # Title and description
    st.title(APP_TITLE)
    st.subheader(APP_SUBTITLE)
    
    # Initialize session state
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.data = None
        st.session_state.geojson_data = None
    
    # Load data if not already loaded
    if not st.session_state.data_loaded:
        try:
            with st.spinner("Loading data..."):
                st.session_state.data = load_parquet_data()
                st.session_state.geojson_data = load_us_states()
                st.session_state.data_loaded = True
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.stop()
    
    # Create tabs for different pages
    tabs = st.tabs(TAB_NAMES)
    
    # Render each tab based on selection
    with tabs[0]:  # Overview
        render_overview_page()
    
    with tabs[1]:  # Data Explorer
        render_data_explorer_page(st.session_state.data)
    
    with tabs[2]:  # Land Use Flow Diagrams
        st.info("Land Use Flow Diagrams page - Coming soon!")
        st.markdown("This page will display Sankey diagrams showing land use transitions.")
        # render_land_use_flow_page(st.session_state.data)
    
    with tabs[3]:  # Urbanization Trends
        render_urbanization_trends_page(st.session_state.data)
    
    with tabs[4]:  # Forest Transitions
        st.info("Forest Transitions page - Coming soon!")
        st.markdown("This page will analyze forest loss and gain patterns.")
        # render_forest_transitions_page(st.session_state.data)
    
    with tabs[5]:  # Agricultural Transitions
        st.info("Agricultural Transitions page - Coming soon!")
        st.markdown("This page will track changes in cropland and pasture.")
        # render_agricultural_transitions_page(st.session_state.data)
    
    with tabs[6]:  # State Map
        st.info("State Map page - Coming soon!")
        st.markdown("This page will show geographic visualizations of state-level data.")
        # render_state_map_page(st.session_state.data, st.session_state.geojson_data)
    
    with tabs[7]:  # Natural Language Query
        render_natural_language_query_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>Data Source: USDA Forest Service 2020 RPA Assessment | 
            Built with Streamlit | 
            <a href='https://www.fs.usda.gov/research/rpa' target='_blank'>Learn More</a></p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()