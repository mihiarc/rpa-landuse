"""
Overview tab implementation.
"""

import streamlit as st
from .base_tab import BaseTab


class OverviewTab(BaseTab):
    """Overview tab showing key findings and RPA scenario information."""
    
    def render(self) -> None:
        """Render the overview tab content."""
        st.header("Land Use Projections Overview")
        
        self._render_key_findings()
        self._render_rpa_scenarios()
        self._render_data_info()
    
    def _render_key_findings(self) -> None:
        """Render the key findings section."""
        st.markdown("""
            ### Key Findings
            - Developed land area is projected to increase under all scenarios, with most of the new developed land coming at the expense of forest land.
            - Higher projected population and income growth lead to relatively less forest land, while hotter projected future climates lead to relatively more forest land.
            - Projected future land use change is more sensitive to the variation in economic factors across RPA scenarios than to the variation among climate projections.
            """)
    
    def _render_rpa_scenarios(self) -> None:
        """Render the RPA scenarios section."""
        st.subheader("RPA Integrated Scenarios")
        st.markdown("""
        This application focuses on the 4 Integrated RPA scenarios and an Ensemble Projection combining all 4:
        
        **🌡️ Climate & Economic Scenarios:**
        - **Sustainable Development Pathway** (RCP4.5-SSP1) - *Most optimistic scenario*
        - **Climate Challenge Scenario** (RCP8.5-SSP3) - *Climate stress with economic challenges*
        - **Moderate Growth Scenario** (RCP8.5-SSP2) - *Middle-of-the-road scenario*
        - **High Development Scenario** (RCP8.5-SSP5) - *High development pressure*
        - **Ensemble Projection** - *Average across all 20 scenarios*
        
        Each scenario represents different combinations of:
        - **Climate projections** (RCP4.5 = lower warming, RCP8.5 = higher warming)
        - **Socioeconomic pathways** (SSP1-5 = different population and economic growth patterns)
        """)
    
    def _render_data_info(self) -> None:
        """Render the data processing information section."""
        st.subheader("Data Processing Information")
        st.markdown("""
        This viewer uses optimized datasets created directly from the RPA Land Use change database.
        The data has been processed to:
        
        1. Aggregate county-level data to regions where appropriate
        2. Focus on the most significant land use transitions
        3. Provide optimal performance for web-based deployment
        
        All data values are shown in acres (converted from the original hundreds of acres).
        """) 