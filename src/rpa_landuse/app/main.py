"""
Main application controller for the RPA Land Use Viewer.
"""

import logging
import streamlit as st
from typing import Dict
import pandas as pd

from .config import APP_TITLE, APP_SUBTITLE, APP_ICON, APP_LAYOUT, TAB_NAMES
from .services import DataService
from .tabs import (
    OverviewTab,
    DataExplorerTab,
    LandUseFlowsTab,
    UrbanizationTab,
    ForestTransitionsTab,
    AgriculturalTransitionsTab,
    StateMapTab
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RPALandUseApp:
    """Main application controller."""
    
    def __init__(self):
        """Initialize the application."""
        self.data = None
        self.tabs = {}
        
        # Configure Streamlit
        st.set_page_config(
            page_title=APP_TITLE,
            page_icon=APP_ICON,
            layout=APP_LAYOUT
        )
    
    def run(self) -> None:
        """Run the Streamlit application."""
        try:
            self._render_header()
            self._load_data()
            self._initialize_tabs()
            self._render_tabs()
            self._render_footer()
            
        except Exception as e:
            st.error(f"Application error: {e}")
            logger.error(f"Application error: {e}", exc_info=True)
    
    def _render_header(self) -> None:
        """Render the application header."""
        st.title(APP_TITLE)
        st.subheader(APP_SUBTITLE)
        st.markdown("""
        This application visualizes land use transition projections from the USDA Forest Service's 2020 Resources Planning Act (RPA) Assessment.
        Explore how land use may change across the United States from 2020 to 2070 under different climate and socioeconomic scenarios.
        """)
    
    def _load_data(self) -> None:
        """Load application data."""
        try:
            logger.info("Loading application data...")
            self.data = DataService.load_parquet_data()
            logger.info("Data loaded successfully")
        except Exception as e:
            st.error(f"Error loading data: {e}")
            logger.error(f"Error loading data: {e}", exc_info=True)
            st.stop()
    
    def _initialize_tabs(self) -> None:
        """Initialize all tab instances."""
        try:
            logger.info("Initializing tabs...")
            self.tabs = {
                "Overview": OverviewTab(self.data),
                "Data Explorer": DataExplorerTab(self.data),
                "Land Use Flow Diagrams": LandUseFlowsTab(self.data),
                "Urbanization Trends": UrbanizationTab(self.data),
                "Forest Trends": ForestTransitionsTab(self.data),
                "Agricultural Trends": AgriculturalTransitionsTab(self.data),
                "State Map": StateMapTab(self.data)
            }
            logger.info("Tabs initialized successfully")
        except Exception as e:
            st.error(f"Error initializing tabs: {e}")
            logger.error(f"Error initializing tabs: {e}", exc_info=True)
            st.stop()
    
    def _render_tabs(self) -> None:
        """Render the tab interface."""
        # Create tabs
        tab_objects = st.tabs(TAB_NAMES)
        
        # Render each tab
        for i, (tab_name, tab_instance) in enumerate(self.tabs.items()):
            with tab_objects[i]:
                try:
                    tab_instance.render()
                except Exception as e:
                    st.error(f"Error rendering {tab_name} tab: {e}")
                    logger.error(f"Error rendering {tab_name} tab: {e}", exc_info=True)
    
    def _render_footer(self) -> None:
        """Render the application footer."""
        st.markdown("---")
        st.markdown("""
        **Data Source**: USDA Forest Service's Resources Planning Act (RPA) Assessment

        For more information, see the [2020 RPA Assessment](https://research.fs.usda.gov/inventory/rpaa/2020).
        """)
        
        # Add sidebar info
        st.sidebar.header("About")
        st.sidebar.info("""
        This app visualizes land use change projections from the USDA Forest Service's 2020 RPA Assessment.

        For more information, see the [2020 RPA Assessment](https://research.fs.usda.gov/inventory/rpaa/2020).
        """)


def main():
    """Main entry point for the application."""
    app = RPALandUseApp()
    app.run()


if __name__ == "__main__":
    main() 