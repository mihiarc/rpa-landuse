"""
Overview page for the RPA Land Use Viewer application.

Displays general information about the RPA assessment and available data.
"""
import streamlit as st
from ..utils.data_loader import load_rpa_docs
from ..config.constants import APP_DESCRIPTION


def render_overview_page():
    """Render the overview page content."""
    
    st.markdown("### About this Application")
    st.markdown(APP_DESCRIPTION)
    
    st.markdown("### Key Features")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📊 Data Explorer**
        - Query and filter land use transition data
        - Export results for further analysis
        - Interactive data tables with sorting and filtering
        """)
        
        st.markdown("""
        **🌆 Urbanization Analysis**
        - Track urban expansion patterns
        - Identify fastest-growing regions
        - Analyze sources of new urban land
        """)
        
        st.markdown("""
        **🌲 Forest Transitions**
        - Monitor forest loss and gain
        - Understand conversion patterns
        - Regional forest change analysis
        """)
    
    with col2:
        st.markdown("""
        **📈 Flow Diagrams**
        - Visualize land use transitions
        - Sankey diagrams showing conversion flows
        - Scenario comparisons
        """)
        
        st.markdown("""
        **🌾 Agricultural Changes**
        - Track cropland and pasture changes
        - Identify agricultural land loss hotspots
        - Conversion to urban and other uses
        """)
        
        st.markdown("""
        **🗺️ Geographic Analysis**
        - State-level aggregated views
        - Interactive choropleth maps
        - Regional comparisons
        """)
    
    # Load and display RPA documentation
    st.markdown("---")
    docs = load_rpa_docs()
    st.markdown(docs)
    
    # Add data notes
    st.markdown("---")
    st.markdown("### Data Notes")
    st.info("""
    - All area measurements are in acres
    - Projections cover 2020-2070 in 10-year increments
    - Data aggregated at county level with state summaries available
    - Scenarios represent different climate and socioeconomic pathways
    """)
    
    # Add citation
    st.markdown("### Citation")
    st.code("""
    USDA Forest Service. (2023). 2020 Resources Planning Act (RPA) Assessment.
    Land Use Projections Dataset. Washington, DC: U.S. Department of Agriculture,
    Forest Service. https://www.fs.usda.gov/research/rpa
    """, language="text")