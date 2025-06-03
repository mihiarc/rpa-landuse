"""
State Map tab implementation.
"""

import streamlit as st
from .base_tab import BaseTab
from ..utils.visualizations import MapUtils


class StateMapTab(BaseTab):
    """State Map tab showing geographic visualizations."""
    
    def render(self) -> None:
        """Render the state map tab content."""
        st.header("State-Level Land Use Change Map")
        
        st.info("Geographic mapping implementation will be added here - using MapUtils.create_state_map()")
        
        # Load geographic data
        states_geojson = self.geo_service.load_us_states()
        
        if states_geojson:
            st.success("Geographic data loaded successfully")
            st.write(f"Found {len(states_geojson.get('features', []))} geographic features")
        else:
            st.warning("Geographic data could not be loaded")
        
        if 'County-Level Land Use Transitions' in self.data:
            df = self.data['County-Level Land Use Transitions']
            st.write(f"Transition data available for mapping: {len(df):,} rows") 