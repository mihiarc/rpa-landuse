#!/usr/bin/env python3
"""
Map Visualization Page for Landuse Analytics Dashboard
Interactive interface for generating and exploring land use maps
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

# Import map generation functionality
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from landuse.tools.map_generation_tool import MapGenerationTool, MapRequest  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="🗺️ Map Visualizations - Landuse Analytics",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS for map display
st.markdown("""
<style>
    .map-container {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    .map-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }

    .map-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .map-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    .map-type-selector {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .map-type-selector:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .example-query {
        background: #e8f4f8;
        border-left: 4px solid #0066cc;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        font-style: italic;
    }

    .map-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        margin-left: 0.5rem;
    }

    .status-success {
        background: #d4edda;
        color: #155724;
    }

    .status-error {
        background: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state for map page"""
    if 'map_history' not in st.session_state:
        st.session_state.map_history = []
    if 'selected_map_type' not in st.session_state:
        st.session_state.selected_map_type = None
    if 'current_map' not in st.session_state:
        st.session_state.current_map = None
    if 'map_agent' not in st.session_state:
        # Map agent disabled for now due to recursion issues
        st.session_state.map_agent = None

def get_available_options():
    """Get available options from the database"""
    try:
        db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        conn = duckdb.connect(str(db_path), read_only=True)

        # Get states
        states = conn.execute("""
            SELECT DISTINCT state_name
            FROM dim_geography_enhanced
            WHERE state_name IS NOT NULL
            ORDER BY state_name
        """).fetchall()

        # Get scenarios
        scenarios = conn.execute("""
            SELECT scenario_name, rcp, ssp, gcm
            FROM dim_scenario
            ORDER BY scenario_name
        """).fetchall()

        # Get time periods
        time_periods = conn.execute("""
            SELECT year_range, start_year, end_year
            FROM dim_time
            ORDER BY start_year
        """).fetchall()

        # Get landuse types
        landuse_types = conn.execute("""
            SELECT landuse_name, landuse_code, landuse_category
            FROM dim_landuse
            ORDER BY landuse_name
        """).fetchall()

        conn.close()

        return {
            'states': [s[0] for s in states],
            'scenarios': scenarios,
            'time_periods': time_periods,
            'landuse_types': landuse_types
        }

    except Exception as e:
        st.error(f"Error loading options: {e}")
        return None

def create_map_interface():
    """Create the interactive map generation interface"""
    st.title("🗺️ Interactive Map Visualizations")
    st.markdown("""
    Generate beautiful, data-driven maps showing land use patterns and transitions across the United States.
    Choose from various map types and customize parameters to explore the data visually.
    """)

    # Initialize session state
    init_session_state()

    # Get available options
    options = get_available_options()
    if not options:
        st.error("Could not load database options. Please check your database connection.")
        return

    # Map type selection
    st.markdown("## 🎨 Choose Map Type")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏛️ State County Maps", use_container_width=True, help="Detailed county-level maps for individual states"):
            st.session_state.selected_map_type = "state_counties"

        st.markdown("""
        <div class="example-query">
        "Show me forest coverage in Texas counties"
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if st.button("🌎 Regional Maps", use_container_width=True, help="State-level overview maps showing regional patterns"):
            st.session_state.selected_map_type = "regional"

        st.markdown("""
        <div class="example-query">
        "Display urban land use across all states"
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if st.button("🔄 Transition Maps", use_container_width=True, help="Maps showing land use conversions"):
            st.session_state.selected_map_type = "transitions"

        st.markdown("""
        <div class="example-query">
        "Map forest to urban transitions"
        </div>
        """, unsafe_allow_html=True)

    # Show map generation form based on selection
    if st.session_state.selected_map_type:
        st.markdown("---")
        generate_map_form(st.session_state.selected_map_type, options)

    # Natural language interface
    st.markdown("---")
    st.markdown("## 💬 Natural Language Map Generation")
    st.markdown("Ask for maps using natural language! The AI agent will understand your request and generate appropriate visualizations.")

    # Create two columns for input and examples
    col1, col2 = st.columns([2, 1])

    with col1:
        user_query = st.text_area(
            "Describe the map you want to see:",
            placeholder="Example: 'Create a map showing agricultural land in California counties' or 'Show me where forests are converting to urban areas'",
            height=100
        )

        if st.button("🚀 Generate Map from Query", type="primary", disabled=st.session_state.map_agent is None):
            if user_query:
                generate_map_from_query(user_query)

    with col2:
        st.markdown("### 💡 Example Queries")
        example_queries = [
            "Show me a map of forest coverage in Texas",
            "Create a county map of California showing urban areas",
            "Visualize agricultural land distribution across regions",
            "Map forest to urban transitions nationally",
            "Display crop land changes in the Midwest",
            "Show urbanization patterns in Florida"
        ]

        for query in example_queries:
            if st.button(f"📝 {query}", key=f"example_{query}", use_container_width=True):
                st.session_state.query_text = query
                st.rerun()

    # Display current map
    if st.session_state.current_map:
        display_current_map()

    # Map history gallery
    if st.session_state.map_history:
        display_map_history()

def generate_map_form(map_type: str, options: dict):
    """Generate form for specific map type"""
    st.markdown(f"### 🎯 Configure {map_type.replace('_', ' ').title()} Map")

    with st.form(f"map_form_{map_type}"):
        col1, col2 = st.columns(2)

        # Common parameters
        with col1:
            if map_type == "state_counties":
                state = st.selectbox("Select State", options['states'])
                landuse_type = st.selectbox(
                    "Land Use Type",
                    [lt[0] for lt in options['landuse_types']],
                    help="Choose which land use type to visualize"
                )
            elif map_type == "regional":
                landuse_type = st.selectbox(
                    "Land Use Type",
                    [lt[0] for lt in options['landuse_types']],
                    help="Choose which land use type to visualize"
                )
                state = None
            elif map_type == "transitions":
                from_landuse = st.selectbox(
                    "From Land Use",
                    [lt[0] for lt in options['landuse_types']],
                    help="Source land use type"
                )
                to_landuse = st.selectbox(
                    "To Land Use",
                    [lt[0] for lt in options['landuse_types']],
                    index=1,
                    help="Target land use type"
                )
                state = st.selectbox(
                    "State (Optional)",
                    ["All States"] + options['states'],
                    help="Leave as 'All States' for national view"
                )
                if state == "All States":
                    state = None
                landuse_type = None

        with col2:
            # Scenario selection
            scenario_names = [s[0] for s in options['scenarios']]
            scenario = st.selectbox(
                "Climate Scenario",
                ["Default (First Available)"] + scenario_names,
                help="Select a specific climate scenario or use default"
            )
            if scenario == "Default (First Available)":
                scenario = None

            # Time period selection
            time_periods = [tp[0] for tp in options['time_periods']]
            time_period = st.selectbox(
                "Time Period",
                ["Latest Available"] + time_periods,
                help="Select time period for the data"
            )
            if time_period == "Latest Available":
                time_period = None

        # Generate button
        submitted = st.form_submit_button("🗺️ Generate Map", type="primary", use_container_width=True)

        if submitted:
            # Create map request
            if map_type == "state_counties":
                generate_state_county_map(state, landuse_type, scenario, time_period)
            elif map_type == "regional":
                generate_regional_map(landuse_type, scenario, time_period)
            elif map_type == "transitions":
                generate_transition_map(from_landuse, to_landuse, state, scenario, time_period)

def generate_state_county_map(state: str, landuse_type: str, scenario: Optional[str], time_period: Optional[str]):
    """Generate a state county map"""
    with st.spinner(f"🎨 Creating county map for {state}..."):
        try:
            db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
            output_dir = Path("maps/streamlit_generated")
            output_dir.mkdir(exist_ok=True, parents=True)

            tool = MapGenerationTool(str(db_path), str(output_dir))
            result = tool.create_state_county_map(state, landuse_type, scenario, time_period)

            if result['success']:
                st.session_state.current_map = result
                st.session_state.map_history.append({
                    **result,
                    'timestamp': datetime.now().isoformat(),
                    'query_type': 'form'
                })
                st.success("✅ Map generated successfully!")
                st.rerun()
            else:
                st.error(f"❌ Error: {result['error']}")

        except Exception as e:
            st.error(f"❌ Failed to generate map: {str(e)}")

def generate_regional_map(landuse_type: str, scenario: Optional[str], time_period: Optional[str]):
    """Generate a regional map"""
    with st.spinner(f"🎨 Creating regional {landuse_type} map..."):
        try:
            db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
            output_dir = Path("maps/streamlit_generated")
            output_dir.mkdir(exist_ok=True, parents=True)

            tool = MapGenerationTool(str(db_path), str(output_dir))
            result = tool.create_regional_map(landuse_type)

            if result['success']:
                st.session_state.current_map = result
                st.session_state.map_history.append({
                    **result,
                    'timestamp': datetime.now().isoformat(),
                    'query_type': 'form'
                })
                st.success("✅ Map generated successfully!")
                st.rerun()
            else:
                st.error(f"❌ Error: {result['error']}")

        except Exception as e:
            st.error(f"❌ Failed to generate map: {str(e)}")

def generate_transition_map(from_landuse: str, to_landuse: str, state: Optional[str],
                          scenario: Optional[str], time_period: Optional[str]):
    """Generate a transition map"""
    with st.spinner(f"🎨 Creating {from_landuse} to {to_landuse} transition map..."):
        try:
            db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
            output_dir = Path("maps/streamlit_generated")
            output_dir.mkdir(exist_ok=True, parents=True)

            tool = MapGenerationTool(str(db_path), str(output_dir))
            result = tool.create_transition_map(from_landuse, to_landuse, state)

            if result['success']:
                st.session_state.current_map = result
                st.session_state.map_history.append({
                    **result,
                    'timestamp': datetime.now().isoformat(),
                    'query_type': 'form'
                })
                st.success("✅ Map generated successfully!")
                st.rerun()
            else:
                st.error(f"❌ Error: {result['error']}")

        except Exception as e:
            st.error(f"❌ Failed to generate map: {str(e)}")

def generate_map_from_query(query: str):
    """Generate map using natural language query"""
    if not st.session_state.map_agent:
        st.error("Natural language map generation is temporarily disabled. Please use the form-based interface above to create maps.")
        return

    with st.spinner("🤖 Understanding your request and generating map..."):
        try:
            # Use the map agent to process the query
            response = st.session_state.map_agent.query(query)

            # Parse response to extract map information
            if "Generated Visualizations:" in response:
                # Extract map path from response
                lines = response.split('\n')
                for line in lines:
                    if '.png' in line and '`' in line:
                        # Extract path between backticks
                        import re
                        match = re.search(r'`([^`]+\.png)`', line)
                        if match:
                            map_path = match.group(1)
                            if Path(map_path).exists():
                                # Create result object
                                result = {
                                    'success': True,
                                    'map_path': map_path,
                                    'description': query,
                                    'response': response
                                }
                                st.session_state.current_map = result
                                st.session_state.map_history.append({
                                    **result,
                                    'timestamp': datetime.now().isoformat(),
                                    'query_type': 'natural_language',
                                    'original_query': query
                                })
                                st.success("✅ Map generated successfully!")
                                st.rerun()
                                return

            # If no map was generated, show the response
            st.info(response)

        except Exception as e:
            st.error(f"❌ Error processing query: {str(e)}")

def display_current_map():
    """Display the currently generated map"""
    map_info = st.session_state.current_map

    st.markdown("---")
    st.markdown("## 🖼️ Generated Map")

    # Create container for map display
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            # Display the map image
            if 'map_path' in map_info and Path(map_info['map_path']).exists():
                st.image(map_info['map_path'], use_column_width=True)
            else:
                st.error("Map file not found!")

        with col2:
            # Map information
            st.markdown("### 📋 Map Details")

            if map_info.get('success'):
                st.markdown('<span class="map-status status-success">✓ Success</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="map-status status-error">✗ Failed</span>', unsafe_allow_html=True)

            # Display map metadata
            st.markdown("**Type:** " + map_info.get('map_type', 'Unknown').replace('_', ' ').title())

            if 'state' in map_info and map_info['state']:
                st.markdown(f"**State:** {map_info['state']}")

            if 'landuse_type' in map_info and map_info['landuse_type']:
                st.markdown(f"**Land Use:** {map_info['landuse_type']}")

            if 'from_landuse' in map_info and map_info['from_landuse']:
                st.markdown(f"**From:** {map_info['from_landuse']}")
                st.markdown(f"**To:** {map_info['to_landuse']}")

            if 'scenario' in map_info and map_info['scenario']:
                st.markdown(f"**Scenario:** {map_info['scenario']}")

            if 'time_period' in map_info and map_info['time_period']:
                st.markdown(f"**Period:** {map_info['time_period']}")

            # Download button
            if 'map_path' in map_info and Path(map_info['map_path']).exists():
                with open(map_info['map_path'], 'rb') as f:
                    st.download_button(
                        label="📥 Download Map",
                        data=f.read(),
                        file_name=Path(map_info['map_path']).name,
                        mime="image/png",
                        use_container_width=True
                    )

            # Clear button
            if st.button("🗑️ Clear Map", use_container_width=True):
                st.session_state.current_map = None
                st.rerun()

    # Show agent response if from natural language
    if 'response' in map_info:
        with st.expander("🤖 AI Agent Response", expanded=False):
            st.markdown(map_info['response'])

def display_map_history():
    """Display history of generated maps"""
    st.markdown("---")
    st.markdown("## 📚 Map History")

    # Sort history by timestamp (newest first)
    history = sorted(st.session_state.map_history,
                    key=lambda x: x.get('timestamp', ''),
                    reverse=True)

    # Create gallery
    cols = st.columns(3)
    for idx, map_info in enumerate(history[:9]):  # Show last 9 maps
        col = cols[idx % 3]

        with col:
            with st.container():
                # Create clickable card
                if st.button(
                    f"🗺️ {map_info.get('description', 'Map')}",
                    key=f"history_{idx}",
                    use_container_width=True
                ):
                    st.session_state.current_map = map_info
                    st.rerun()

                # Show thumbnail if available
                if 'map_path' in map_info and Path(map_info['map_path']).exists():
                    st.image(map_info['map_path'], use_column_width=True)

                # Show metadata
                st.caption(f"Type: {map_info.get('map_type', 'Unknown')}")
                if 'timestamp' in map_info:
                    from datetime import datetime
                    ts = datetime.fromisoformat(map_info['timestamp'])
                    st.caption(f"Created: {ts.strftime('%Y-%m-%d %H:%M')}")

# Initialize query text if passed from example
if 'query_text' in st.session_state:
    st.query_params['query'] = st.session_state.query_text
    del st.session_state.query_text

# Main execution
if __name__ == "__main__":
    create_map_interface()
