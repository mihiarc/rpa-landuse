import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import plotly.graph_objects as go
import requests
import tempfile
import duckdb

# Set page configuration
st.set_page_config(
    page_title="RPA Land Use Viewer",
    page_icon="🌳",
    layout="wide"
)

# Title and description
st.title("2020 Resources Planning Act (RPA) Assessment")
st.subheader("Land-Use Change Viewer")
st.markdown("""
This application visualizes land use transition projections from the USDA Forest Service's Resources Planning Act (RPA) Assessment.
Explore how land use is expected to change across the United States from 2020 to 2070 under different climate and socioeconomic scenarios.
""")

# Load the parquet files
@st.cache_data
def load_parquet_data():
    # Use processed data for deployed app
    data_dir = "data/processed"
    
    try:
        # Define dataset files
        files = {
            "Average Gross Change Across All Scenarios (2020-2070)": "gross_change_ensemble_all.parquet",
            "Urbanization Trends By Decade": "urbanization_trends.parquet",
            "Transitions to Urban Land": "to_urban_transitions.parquet",
            "Transitions from Forest Land": "from_forest_transitions.parquet",
            "County-Level Land Use Transitions": "county_transitions.parquet"
        }
        
        # Load datasets
        raw_data = {}
        for key, filename in files.items():
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                raw_data[key] = pd.read_parquet(file_path)
            else:
                st.warning(f"File not found: {file_path}")
                
        st.sidebar.success("Using optimized datasets for better performance")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        raise e
    
    # Convert hundred acres to acres for all datasets
    data = {}
    for key, df in raw_data.items():
        df_copy = df.copy()
        
        # Convert total_area column if it exists
        if "total_area" in df_copy.columns:
            df_copy["total_area"] = df_copy["total_area"] * 100
            
        # Convert specific columns for urbanization trends dataset
        if key == "Urbanization Trends By Decade":
            area_columns = ["forest_to_urban", "cropland_to_urban", "pasture_to_urban"]
            for col in area_columns:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col] * 100
        
        data[key] = df_copy
    
    return data

# Load US states GeoJSON
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_us_states():
    """Load US states geographic data without any projection system dependencies"""
    
    # Method 1: Try to download remote GeoJSON and parse it directly
    try:
        st.info("Downloading US states geographic data...")
        
        url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
        
        # Download with SSL verification disabled
        response = requests.get(url, verify=False)
        response.raise_for_status()
        
        # Parse JSON directly - no GeoPandas needed for this step
        import json
        geojson_data = json.loads(response.text)
        
        st.success("✅ Downloaded US states data successfully.")
        return geojson_data  # Return raw GeoJSON for Folium
            
    except Exception as e:
        st.warning(f"Could not download remote states data: {e}")
    
    # Method 2: Try to read local counties and create states manually
    try:
        st.info("Creating states from local counties data...")
        
        counties_path = "data/counties.geojson"
        if os.path.exists(counties_path):
            # Read the file as plain JSON first
            import json
            with open(counties_path, 'r') as f:
                counties_geojson = json.load(f)
            
            # Create state FIPS to name mapping
            state_fips_to_name = {
                '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas', '06': 'California',
                '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware', '11': 'District of Columbia',
                '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho', '17': 'Illinois',
                '18': 'Indiana', '19': 'Iowa', '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana',
                '23': 'Maine', '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
                '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
                '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
                '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma',
                '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina',
                '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas', '49': 'Utah', '50': 'Vermont',
                '51': 'Virginia', '53': 'Washington', '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming'
            }
            
            # Group counties by state and create simplified state boundaries
            state_features = {}
            for feature in counties_geojson['features']:
                state_fips = feature['properties']['STATE']
                state_name = state_fips_to_name.get(state_fips)
                
                if state_name:
                    if state_name not in state_features:
                        state_features[state_name] = {
                            "type": "Feature",
                            "properties": {"name": state_name},
                            "geometry": {
                                "type": "MultiPolygon",
                                "coordinates": []
                            }
                        }
                    
                    # Add county geometry to state (simplified approach)
                    geom = feature['geometry']
                    if geom['type'] == 'Polygon':
                        state_features[state_name]['geometry']['coordinates'].append(geom['coordinates'])
                    elif geom['type'] == 'MultiPolygon':
                        state_features[state_name]['geometry']['coordinates'].extend(geom['coordinates'])
            
            # Create final GeoJSON
            states_geojson = {
                "type": "FeatureCollection",
                "features": list(state_features.values())
            }
            
            st.success("✅ Created states from local counties data.")
            return states_geojson
            
    except Exception as e:
        st.warning(f"Could not create states from counties: {e}")
    
    # Method 3: Create a minimal hardcoded states GeoJSON
    try:
        st.info("Using minimal hardcoded states data...")
        
        # Create basic rectangular boundaries for major states
        minimal_states = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "California"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-124.0, 42.0], [-114.0, 42.0], [-114.0, 32.0], [-124.0, 32.0], [-124.0, 42.0]]]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Texas"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-106.0, 36.0], [-94.0, 36.0], [-94.0, 25.0], [-106.0, 25.0], [-106.0, 36.0]]]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Florida"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-87.0, 31.0], [-80.0, 31.0], [-80.0, 24.0], [-87.0, 24.0], [-87.0, 31.0]]]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {"name": "New York"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-79.0, 45.0], [-71.0, 45.0], [-71.0, 40.0], [-79.0, 40.0], [-79.0, 45.0]]]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Illinois"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-91.0, 42.5], [-87.0, 42.5], [-87.0, 37.0], [-91.0, 37.0], [-91.0, 42.5]]]
                    }
                }
            ]
        }
        
        st.info("✅ Using minimal geographic data (5 major states).")
        st.warning("⚠️ Limited to 5 major states due to system issues.")
        return minimal_states
        
    except Exception as e:
        st.warning(f"Minimal approach failed: {e}")
    
    # Final fallback: return None to disable mapping
    st.error("❌ Geographic mapping is disabled - all methods failed.")
    st.info("The data table will still be available below.")
    return None

# Load RPA documentation if available
@st.cache_data
def load_rpa_docs():
    try:
        with open("docs/rpa_text/gtr_wo102_Chap4_chunks.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Aggregate county data to state level
def aggregate_to_state_level(county_df, transition_type, scenario, decade):
    """
    Aggregate county-level data to state level for mapping
    
    Args:
        county_df: The county-level transitions dataframe
        transition_type: 'to_urban', 'from_forest', or 'all'
        scenario: The scenario name to filter by
        decade: The decade name to filter by
    
    Returns:
        DataFrame aggregated at state level
    """
    # Filter by scenario and decade
    filtered_df = county_df[
        (county_df["scenario_name"] == scenario) & 
        (county_df["decade_name"] == decade)
    ].copy()
    
    # Apply transition type filter
    if transition_type == 'to_urban':
        filtered_df = filtered_df[filtered_df["to_category"] == "Urban"]
    elif transition_type == 'from_forest':
        filtered_df = filtered_df[filtered_df["from_category"] == "Forest"]
    
    # Aggregate to state level
    state_df = filtered_df.groupby("state_name")["total_area"].sum().reset_index()
    
    # Rename columns for clarity
    state_df.columns = ["name", "total_area"]
    
    return state_df

# Create Sankey diagram for land use transitions
def create_sankey_diagram(transitions_data, title, scenario_name):
    """
    Create a Sankey diagram showing land use transitions
    
    Args:
        transitions_data: DataFrame with from_category, to_category, and total_area columns
        title: Title for the diagram
        scenario_name: Scenario name for filtering
    
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
    
    # Define colors for different land use types
    color_map = {
        'Forest': '#228B22',      # Forest Green
        'Cropland': '#FFD700',    # Gold
        'Pasture': '#90EE90',     # Light Green
        'Urban': '#FF6347',       # Tomato Red
        'Other': '#D3D3D3',       # Light Gray
        'Range': '#DEB887',       # Burlywood
        'Water': '#4169E1',       # Royal Blue
        'Federal': '#8B4513'      # Saddle Brown
    }
    
    # Assign colors to nodes
    node_colors = [color_map.get(cat, '#D3D3D3') for cat in all_categories]
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
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
        height=700,
        margin=dict(l=20, r=20, t=80, b=50)
    )
    
    return fig

# Create choropleth map
def create_state_map(state_data, title):
    """Create a folium choropleth map of states using raw GeoJSON"""
    # Load GeoJSON of US states (now returns raw GeoJSON dict)
    states_geojson = load_us_states()
    
    # If states data couldn't be loaded, return None
    if states_geojson is None:
        return None
    
    # Center the map on the continental US
    map_center = [39.8283, -98.5795]
    state_map = folium.Map(location=map_center, zoom_start=4, scrollWheelZoom=False)
    
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

# Main layout with tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Overview", "Data Explorer", "Land Use Flow Diagrams", "Urbanization Trends", "Forest Transitions", "Agricultural Transitions", "State Map"])

# Load data
try:
    data = load_parquet_data()
    rpa_docs = load_rpa_docs()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ---- OVERVIEW TAB ----
with tab1:
    st.header("Land Use Projections Overview")
    
    st.markdown("""
        ### Key Findings
        - Developed land area is projected to increase under all scenarios, with most of the new developed land coming at the expense of forest land.
        - Higher projected population and income growth lead to relatively less forest land, while hotter projected future climates lead to relatively more forest land.
        - Projected future land use change is more sensitive to the variation in economic factors across RPA scenarios than to the variation among climate projections.
        """)
    
    st.subheader("RPA Integrated Scenarios")
    st.markdown("""
    This application focuses on the 5 most important RPA scenarios for policy analysis:
    
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
    
    # Add more informative overview
    st.subheader("Data Processing Information")
    st.markdown("""
    This viewer uses optimized datasets created directly from the RPA Land Use database using DuckDB.
    The data has been processed to:
    
    1. Aggregate county-level data to regions where appropriate
    2. Focus on the most significant land use transitions
    3. Provide optimal performance for web-based deployment
    
    All data values are shown in acres (converted from the original hundreds of acres).
    """)

# ---- DATA EXPLORER TAB ----
with tab2:
    st.header("Data Explorer")
    
    # Load data using database views for spatial levels
    @st.cache_data
    def load_spatial_data(spatial_level, scenario_filter=None, geographic_filter=None, filter_value=None):
        """Load data from database views based on spatial level, scenario, and optional geographic filter."""
        import duckdb
        
        db_path = "data/database/rpa.db"
        
        try:
            conn = duckdb.connect(db_path)
            
            # Map spatial levels to view names
            view_mapping = {
                "County": '"County-Level Land Use Transitions"',
                "State": '"State-Level Land Use Transitions"',
                "Region": '"Region-Level Land Use Transitions"',
                "Subregion": '"Subregion-Level Land Use Transitions"', 
                "National": '"National-Level Land Use Transitions"'
            }
            
            view_name = view_mapping.get(spatial_level)
            if view_name:
                # Build the query with optional filtering
                query = f'SELECT * FROM {view_name}'
                
                # Add filters
                conditions = []
                
                # Add scenario filter if specified
                if scenario_filter and scenario_filter != "Overall Mean":
                    conditions.append(f"scenario_name = '{scenario_filter}'")
                
                # Add geographic filter if specified
                if geographic_filter and filter_value and filter_value != "All":
                    if geographic_filter == "state":
                        conditions.append(f"state_name = '{filter_value}'")
                    elif geographic_filter == "region":
                        conditions.append(f"region = '{filter_value}'")
                    elif geographic_filter == "subregion":
                        conditions.append(f"subregion = '{filter_value}'")
                
                # Add WHERE clause if we have conditions
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                df = conn.execute(query).df()
                conn.close()
                return df
            else:
                conn.close()
                return None
                
        except Exception as e:
            st.error(f"Error loading {spatial_level} data: {e}")
            return None
    
    @st.cache_data
    def get_geographic_options():
        """Get available states, regions, and subregions for filtering."""
        import duckdb
        
        db_path = "data/database/rpa.db"
        
        try:
            conn = duckdb.connect(db_path)
            
            # Get unique values for filtering
            states = conn.execute('SELECT DISTINCT state_name FROM "County-Level Land Use Transitions" ORDER BY state_name').fetchall()
            regions = conn.execute('SELECT DISTINCT region FROM "County-Level Land Use Transitions" WHERE region IS NOT NULL ORDER BY region').fetchall()
            subregions = conn.execute('SELECT DISTINCT subregion FROM "County-Level Land Use Transitions" WHERE subregion IS NOT NULL ORDER BY subregion').fetchall()
            
            conn.close()
            
            return {
                'states': [row[0] for row in states],
                'regions': [row[0] for row in regions],
                'subregions': [row[0] for row in subregions]
            }
        except Exception as e:
            st.error(f"Error loading geographic options: {e}")
            return {'states': [], 'regions': [], 'subregions': []}
    
    # Select RPA scenario to explore
    scenario_descriptions = {
        'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
        'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
        'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
        'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
        'ensemble_HH': 'High Development (RCP8.5-SSP5)'
    }
    
    scenario_options = list(scenario_descriptions.keys())
    selected_scenario_display = st.selectbox("Select RPA Scenario", options=scenario_options)
    
    # Map display name back to database scenario name
    if selected_scenario_display == 'Overall Mean':
        selected_scenario = 'ensemble_overall'
    else:
        selected_scenario = selected_scenario_display
    
    # Add spatial level selector
    spatial_levels = ["County", "Subregion", "Region", "State", "National"]
    selected_spatial_level = st.selectbox("Select Spatial Level", options=spatial_levels)
    
    # Add geographic filtering for County level
    geographic_filter = None
    filter_value = None
    
    if selected_spatial_level == "County":
        st.subheader("🌍 Geographic Filter")
        
        # Get available options
        geo_options = get_geographic_options()
        
        # Filter type selection
        filter_options = ["All Counties", "Counties by State", "Counties by Region", "Counties by Subregion"]
        selected_filter = st.selectbox("Show:", options=filter_options)
        
        if selected_filter == "Counties by State":
            geographic_filter = "state"
            filter_value = st.selectbox("Select State:", options=["All"] + geo_options['states'])
        elif selected_filter == "Counties by Region":
            geographic_filter = "region"
            filter_value = st.selectbox("Select Region:", options=["All"] + geo_options['regions'])
        elif selected_filter == "Counties by Subregion":
            geographic_filter = "subregion"
            filter_value = st.selectbox("Select Subregion:", options=["All"] + geo_options['subregions'])
    
    # Load data from database views
    selected_df = load_spatial_data(selected_spatial_level, selected_scenario, geographic_filter, filter_value)
    
    if selected_df is not None:
        # Successfully loaded from database views
        scenario_text = scenario_descriptions[selected_scenario_display]
        
        if selected_spatial_level == "County" and geographic_filter and filter_value and filter_value != "All":
            st.subheader(f"Exploring: Counties in {filter_value} ({geographic_filter.title()})")
            st.info(f"📊 Showing {len(selected_df):,} rows | Scenario: {scenario_text}")
        else:
            st.subheader(f"Exploring: {selected_spatial_level} Level Land Use Transitions")
            st.info(f"📊 Scenario: {scenario_text} | Spatial Level: {selected_spatial_level}")
    
    else:
        # Fallback message
        st.error("Unable to load data from database views. Please check that the database is available.")
        st.stop()
    
    # Add info message about acres conversion
    st.info("Note: All area values are displayed in acres.")
    
    # Show basic stats
    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Number of Rows", selected_df.shape[0])
    with col2:
        st.metric("Number of Columns", selected_df.shape[1])
    
    # Show column info
    st.subheader("Column Information")
    # Convert object types to string to avoid PyArrow conversion issues
    col_df = pd.DataFrame({
        "Column": selected_df.columns,
        "Type": [str(dtype) for dtype in selected_df.dtypes],
        "Sample Values": [str(selected_df[col].iloc[0]) if len(selected_df) > 0 else "Empty" for col in selected_df.columns]
    })
    st.dataframe(col_df)
    
    # Show data
    st.subheader("Data Preview")
    # Convert object columns to string to avoid PyArrow conversion issues
    preview_df = selected_df.head(100).copy()
    for col in preview_df.select_dtypes(include=['object']).columns:
        preview_df[col] = preview_df[col].astype(str)
    st.dataframe(preview_df)
    
    # Allow download
    # Prepare download data with better column ordering
    download_df = selected_df.copy()
    
    # Reorder columns for better readability, putting identifiers first
    if selected_spatial_level == "County":
        # For county data, ensure FIPS code is first, followed by names
        id_columns = ["fips_code", "county_name", "state_name"]
        if "region" in download_df.columns:
            id_columns.append("region")
        if "subregion" in download_df.columns:
            id_columns.append("subregion")
    elif selected_spatial_level == "State":
        id_columns = ["state_name"]
    elif selected_spatial_level == "Region":
        id_columns = ["region"]
    elif selected_spatial_level == "Subregion":
        id_columns = ["subregion"]
    else:
        id_columns = []
    
    # Get data columns (metrics)
    data_columns = ["scenario_name", "decade_name", "from_category", "to_category", "total_area"]
    
    # Reorder all columns: IDs -> Data -> Remaining
    available_id_cols = [col for col in id_columns if col in download_df.columns]
    available_data_cols = [col for col in data_columns if col in download_df.columns]
    remaining_cols = [col for col in download_df.columns if col not in available_id_cols + available_data_cols]
    
    # Final column order
    final_column_order = available_id_cols + available_data_cols + remaining_cols
    download_df = download_df[final_column_order]
    
    # Show info about FIPS codes if included
    if "fips_code" in download_df.columns:
        st.info("💡 Downloads include FIPS codes for easy integration with mapping and other datasets")
    
    csv = download_df.to_csv(index=False).encode('utf-8')
    scenario_name = selected_scenario_display.replace(' ', '_').replace('(', '').replace(')', '')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'{scenario_name}_{selected_spatial_level}_level.csv',
        mime='text/csv',
    )

# ---- LAND USE FLOW DIAGRAMS TAB ----
with tab3:
    st.header("🌊 Land Use Transition Flow Diagrams")
    
    st.markdown("""
    Sankey diagrams show the flow of land from one use type to another. The width of each flow 
    represents the total acres converted between land use categories over the selected time period.
    """)
    
    # Get county transitions data 
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    county_df = county_df[county_df["scenario_name"].isin(key_scenarios)]
    
    # Controls for Sankey diagram
    st.subheader("Diagram Controls")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Scenario selection
        scenario_descriptions = {
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)',
            'ensemble_overall': 'Ensemble Projection (All Scenarios)'
        }
        
        sankey_scenarios = county_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in sankey_scenarios]
        selected_scenario_display = st.selectbox(
            "Climate & Economic Scenario", 
            options=scenario_options,
            index=4,  # Default to Ensemble Projection
            key="sankey_scenario"
        )
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_sankey_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col2:
        # Time period selection
        sankey_decades = county_df["decade_name"].unique().tolist()
        sankey_decades.sort()
        selected_time_period = st.selectbox(
            "Time Period", 
            options=["All Periods"] + sankey_decades,
            key="sankey_time"
        )
    
    with col3:
        # Geographic scope
        geographic_scope = st.selectbox(
            "Geographic Scope",
            options=["National", "By State"],
            key="sankey_scope"
        )
    
    # Advanced filters
    with st.expander("🔍 Advanced Filters"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # From land use filter
            all_from_categories = county_df["from_category"].unique().tolist()
            all_from_categories.sort()
            selected_from_categories = st.multiselect(
                "From Land Use Types (leave empty for all)",
                options=all_from_categories,
                key="sankey_from"
            )
        
        with col2:
            # To land use filter
            all_to_categories = county_df["to_category"].unique().tolist()
            all_to_categories.sort()
            selected_to_categories = st.multiselect(
                "To Land Use Types (leave empty for all)",
                options=all_to_categories,
                key="sankey_to"
            )
        
        # Minimum flow threshold
        min_threshold = st.slider(
            "Minimum Flow Threshold (acres)",
            min_value=0,
            max_value=100000,
            value=1000,
            step=1000,
            help="Hide flows smaller than this threshold to reduce clutter",
            key="sankey_threshold"
        )
    
    # Filter data based on selections
    filtered_sankey_data = county_df[county_df["scenario_name"] == selected_sankey_scenario]
    
    # Apply time period filter
    if selected_time_period != "All Periods":
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["decade_name"] == selected_time_period]
    
    # Apply land use filters
    if selected_from_categories:
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["from_category"].isin(selected_from_categories)]
    
    if selected_to_categories:
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["to_category"].isin(selected_to_categories)]
    
    # Create Sankey diagram(s)
    if geographic_scope == "National":
        # Single national diagram
        st.subheader(f"🌊 National Land Use Transitions")
        
        # Aggregate data
        sankey_data = filtered_sankey_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
        
        # Apply threshold filter
        sankey_data = sankey_data[sankey_data["total_area"] >= min_threshold]
        
        # Filter out transitions where land use stays the same
        sankey_data = sankey_data[sankey_data["from_category"] != sankey_data["to_category"]]
        
        if len(sankey_data) > 0:
            # Create title
            time_text = f" ({selected_time_period})" if selected_time_period != "All Periods" else " (2020-2070)"
            sankey_title = f"National Land Use Transitions - {selected_scenario_display}{time_text}"
            
            # Create Sankey diagram
            sankey_fig = create_sankey_diagram(
                filtered_sankey_data, 
                sankey_title,
                selected_sankey_scenario
            )
            
            st.plotly_chart(sankey_fig, use_container_width=True, key="national_sankey")
            
            # Show summary statistics
            with st.expander("📊 Flow Summary Statistics"):
                summary_stats = sankey_data.copy()
                summary_stats["total_area"] = summary_stats["total_area"].map(lambda x: f"{x:,.0f}")
                summary_stats.columns = ["From Land Use", "To Land Use", "Total Acres Converted"]
                summary_stats = summary_stats.sort_values("Total Acres Converted", ascending=False)
                st.dataframe(summary_stats, use_container_width=True)
                
                # Download option
                csv_data = sankey_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Flow Data (CSV)",
                    data=csv_data,
                    file_name=f"land_use_flows_{selected_sankey_scenario}_{selected_time_period}.csv",
                    mime="text/csv"
                )
        else:
            st.warning("No data available for the selected filters. Try adjusting your criteria.")
    
    else:
        # Multiple state diagrams
        st.subheader(f"🌊 Land Use Transitions by State")
        
        # Get available states
        available_states = filtered_sankey_data["state_name"].unique().tolist()
        available_states.sort()
        
        # State selection
        selected_states = st.multiselect(
            "Select States to Display (max 4 for readability)",
            options=available_states,
            default=available_states[:2] if len(available_states) >= 2 else available_states,
            max_selections=4,
            key="sankey_states"
        )
        
        if selected_states:
            # Create diagrams for each selected state
            for state in selected_states:
                state_data = filtered_sankey_data[filtered_sankey_data["state_name"] == state]
                
                # Aggregate data for this state
                state_sankey_data = state_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
                
                # Apply threshold filter
                state_sankey_data = state_sankey_data[state_sankey_data["total_area"] >= min_threshold]
                
                # Filter out transitions where land use stays the same
                state_sankey_data = state_sankey_data[state_sankey_data["from_category"] != state_sankey_data["to_category"]]
                
                if len(state_sankey_data) > 0:
                    # Create title
                    time_text = f" ({selected_time_period})" if selected_time_period != "All Periods" else " (2020-2070)"
                    state_title = f"{state} Land Use Transitions - {selected_scenario_display}{time_text}"
                    
                    # Create Sankey diagram
                    state_fig = create_sankey_diagram(
                        state_data, 
                        state_title,
                        selected_sankey_scenario
                    )
                    
                    st.plotly_chart(state_fig, use_container_width=True, key=f"sankey_{state}")
                    
                    # Show summary for this state
                    with st.expander(f"📊 {state} Flow Summary"):
                        state_summary = state_sankey_data.copy()
                        state_summary["total_area"] = state_summary["total_area"].map(lambda x: f"{x:,.0f}")
                        state_summary.columns = ["From Land Use", "To Land Use", "Total Acres Converted"]
                        state_summary = state_summary.sort_values("Total Acres Converted", ascending=False)
                        st.dataframe(state_summary, use_container_width=True)
                else:
                    st.info(f"No significant transitions found for {state} with current filters.")
        else:
            st.info("Please select at least one state to display diagrams.")

# ---- URBANIZATION TRENDS TAB ----
with tab4:
    st.header("🏙️ Where is Urban Development Rate Highest?")
    
    # Load data using database views for spatial levels (reuse function from Data Explorer)
    @st.cache_data
    def load_urbanization_data_enhanced(spatial_level, scenario_filter=None):
        """Load enhanced urbanization data with FIPS, regions, source breakdown, and proper urbanization rates."""
        import duckdb
        
        # Define scenario mapping inside the function
        scenario_descriptions = {
            'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)'
        }
        
        # Create reverse mapping for database queries
        scenario_reverse_mapping = {v: k for k, v in scenario_descriptions.items()}
        # Handle the special case for 'Overall Mean'
        scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
        
        db_path = "data/database/rpa.db"
        
        try:
            conn = duckdb.connect(db_path)
            
            if spatial_level == "County":
                # Enhanced county query with baseline urban area and proper rate calculations
                query = '''
                WITH baseline_urban AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        baseline_acres_2020 as baseline_urban_acres_2020
                    FROM baseline_county_land_stock
                    WHERE land_use_code = 'ur'
                ),
                new_urban_with_source AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        from_category,
                        SUM(total_area) as new_urban_acres,
                        region,
                        subregion
                    FROM "County-Level Land Use Transitions"
                    WHERE to_category = 'Urban' AND from_category != 'Urban'
                    GROUP BY fips_code, county_name, state_name, scenario_name, from_category, region, subregion
                ),
                total_new_urban AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        region,
                        subregion,
                        SUM(new_urban_acres) as total_new_urban_acres
                    FROM new_urban_with_source
                    GROUP BY fips_code, county_name, state_name, scenario_name, region, subregion
                )
                SELECT 
                    b.fips_code,
                    t.county_name,
                    t.state_name,
                    t.region,
                    t.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_urban_acres_2020, 0) as baseline_urban_acres_2020,
                    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
                    (COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
                    -- Proper urbanization rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
                        ELSE NULL
                    END as urbanization_rate_percent,
                    -- Absolute urban expansion rate (acres per decade)
                    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
                    -- Annualized growth rate
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (POWER((COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_urban_growth_rate_percent,
                    -- Source breakdown pivot (need to handle separately)
                    s.from_category,
                    COALESCE(s.new_urban_acres, 0) as source_acres
                FROM baseline_urban b
                FULL OUTER JOIN total_new_urban t ON b.fips_code = t.fips_code 
                    AND b.county_name = t.county_name 
                    AND b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                LEFT JOIN new_urban_with_source s ON b.fips_code = s.fips_code 
                    AND b.county_name = s.county_name 
                    AND b.state_name = s.state_name 
                    AND b.scenario_name = s.scenario_name
                WHERE 1=1
                '''
                
                if scenario_filter and scenario_filter != "All Scenarios":
                    scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                    query += f" AND b.scenario_name = '{scenario_key}'"
                
                query += " ORDER BY COALESCE(t.total_new_urban_acres, 0) DESC"
                
            elif spatial_level == "State":
                # Enhanced state query using baseline_state_land_stock
                query = '''
                WITH baseline_urban AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        baseline_acres_2020 as baseline_urban_acres_2020
                    FROM baseline_state_land_stock
                    WHERE land_use_code = 'ur'
                ),
                new_urban_development AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        SUM(total_area) as total_new_urban_acres
                    FROM "State-Level Land Use Transitions"
                    WHERE to_category = 'Urban' AND from_category != 'Urban'
                    GROUP BY state_name, region, subregion, scenario_name
                )
                SELECT 
                    b.state_name,
                    b.region,
                    b.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_urban_acres_2020, 0) as baseline_urban_acres_2020,
                    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
                    (COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
                    -- Proper urbanization rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
                        ELSE NULL
                    END as urbanization_rate_percent,
                    -- Absolute urban expansion rate (acres per decade)
                    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
                    -- Annualized growth rate
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (POWER((COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_urban_growth_rate_percent
                FROM baseline_urban b
                LEFT JOIN new_urban_development t ON b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                WHERE 1=1
                '''
                
                if scenario_filter and scenario_filter != "All Scenarios":
                    scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                    query += f" AND b.scenario_name = '{scenario_key}'"
                
                query += " ORDER BY COALESCE(t.total_new_urban_acres, 0) DESC"
            
            # Execute query and load data
            result_df = conn.execute(query).df()
            conn.close()
            
            if result_df.empty:
                st.warning(f"No data available for {spatial_level} level with the selected scenario.")
                return pd.DataFrame()
            
            return result_df
                
        except Exception as e:
            st.error(f"Error loading enhanced urbanization data: {str(e)}")
            return pd.DataFrame()
    
    # Analysis controls
    st.subheader("Analysis Controls")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Add scenario selector
        scenario_descriptions = {
            'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)'
        }
        
        # Create reverse mapping for database queries
        scenario_reverse_mapping = {v: k for k, v in scenario_descriptions.items()}
        # Handle the special case for 'Overall Mean'
        scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
        
        scenario_options = list(scenario_descriptions.keys())
        selected_scenario_display = st.selectbox("Select RPA Scenario", options=scenario_options, key="urban_scenario")
        
        # Map display name back to database scenario name
        if selected_scenario_display == 'Overall Mean':
            selected_scenario = 'ensemble_overall'
        else:
            selected_scenario = selected_scenario_display
    
    with col2:
        # Add spatial level selector for data extraction
        spatial_levels = ["County", "State", "Subregion", "Region", "National"]
        selected_spatial_level = st.selectbox("Data Extraction Level", options=spatial_levels, 
                                            index=1,  # Default to State
                                            key="urban_spatial",
                                            help="Choose spatial level for data download and detailed analysis")
    
    # Load data at selected spatial level
    spatial_data = load_urbanization_data_enhanced(selected_spatial_level, selected_scenario)
    
    if spatial_data is None:
        st.error("Unable to load urbanization data from database views.")
        st.stop()
    
    # For visualization, always use state-level aggregation for readability
    # Get county transitions data for visualization
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    county_df = county_df[county_df["scenario_name"].isin(key_scenarios)]
    
    # Filter for urban transitions only (where to_category is 'Urban')
    urban_counties_df = county_df[county_df["to_category"] == "Urban"]
    
    # Filter data for visualization (always use state level for charts)
    viz_data = urban_counties_df[urban_counties_df["scenario_name"] == selected_scenario]
    
    # Aggregate visualization data to state level for charts
    viz_analysis = viz_data.groupby(["state_name"]).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names for visualization
    viz_analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    viz_analysis = viz_analysis.reset_index()
    
    # Calculate urbanization rate for visualization
    viz_analysis["urbanization_rate"] = (viz_analysis["total_acres"] / 
                                       viz_analysis["num_decades"]).round(2)
    
    # Sort by total area for visualization
    viz_analysis = viz_analysis.sort_values("total_acres", ascending=False)
    
    # 1. TOP STATES TEMPORAL TRENDS (for visualization)
    st.subheader(f"📈 Urban Development Trends: Top States ({scenario_descriptions[selected_scenario_display]})")
    st.info(f"📊 Visualization shows state-level data | Data extraction/download uses {selected_spatial_level} level")
    
    # Get top locations for temporal analysis (always states for visualization)
    top_10_viz = viz_analysis.head(10).copy()
    top_10_viz["location"] = top_10_viz["state_name"]
    
    # Create temporal visualization for top states
    if len(top_10_viz) > 0:
        # Get temporal data for top states
        top_states = top_10_viz[["state_name"]].head(10)  # Top 10
        temporal_data = []
        for _, row in top_states.iterrows():
            state_data = viz_data[viz_data["state_name"] == row["state_name"]]
            if len(state_data) > 0:
                state_summary = state_data.groupby("decade_name")["total_area"].sum().reset_index()
                state_summary["location"] = row["state_name"]
                # Calculate percentage change from first period
                if len(state_summary) > 1:
                    baseline = state_summary["total_area"].iloc[0]
                    if baseline > 0:
                        state_summary["pct_change"] = ((state_summary["total_area"] - baseline) / baseline * 100).round(1)
                    else:
                        state_summary["pct_change"] = 0
                else:
                    state_summary["pct_change"] = 0
                temporal_data.append(state_summary)
        
        # Create publication-quality line chart
        if temporal_data:
            # Set dark mode style
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
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
            ax.set_ylabel("Percentage Change from Baseline (%)", fontsize=14, fontweight='bold', color='white')
            ax.set_title(f"Urban Development Trends: Top 10 States ({scenario_descriptions[selected_scenario_display]})", 
                        fontsize=16, fontweight='bold', pad=20, color='white')
            
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
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # 2. SUMMARY STATISTICS FOR SELECTED SPATIAL LEVEL
    st.subheader(f"📊 Summary Statistics ({selected_spatial_level} Level)")
    
    # Check what columns are available in the enhanced data and handle accordingly
    if spatial_data is not None and not spatial_data.empty:
        # For enhanced data structure with proper baseline rate calculations
        if "total_new_urban_acres" in spatial_data.columns and "baseline_urban_acres_2020" in spatial_data.columns:
            # Use enhanced data structure with proper columns
            if selected_spatial_level == "County":
                group_cols = ["county_name", "state_name"]
                location_col = "county_name"
                unit_name = "Counties"
            elif selected_spatial_level == "State":
                group_cols = ["state_name"]
                location_col = "state_name"
                unit_name = "States"
            elif selected_spatial_level == "Region":
                group_cols = ["region"]
                location_col = "region"
                unit_name = "Regions"
            elif selected_spatial_level == "Subregion":
                group_cols = ["subregion"]
                location_col = "subregion"
                unit_name = "Subregions"
            else:  # National
                group_cols = []
                location_col = None
                unit_name = "National"
            
            # Aggregate enhanced data for selected spatial level
            if group_cols:
                # Check which columns actually exist in the data
                available_group_cols = [col for col in group_cols if col in spatial_data.columns]
                
                if available_group_cols:
                    try:
                        # Aggregate using the enhanced columns
                        spatial_analysis = spatial_data.groupby(available_group_cols).agg({
                            "total_new_urban_acres": ["sum", "mean"],
                            "baseline_urban_acres_2020": "first",
                            "urbanization_rate_percent": "mean",
                            "urban_expansion_rate_acres_per_decade": "mean"
                        }).round(2)
                        
                        # Flatten column names
                        spatial_analysis.columns = ["total_new_urban_acres", "avg_new_urban_per_area", "baseline_urban_acres", "avg_urbanization_rate", "avg_expansion_rate"]
                        spatial_analysis = spatial_analysis.reset_index()
                        
                        # Sort by total new urban acres
                        spatial_analysis = spatial_analysis.sort_values("total_new_urban_acres", ascending=False)
                        
                        # Display summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(f"Total {unit_name}", len(spatial_analysis))
                        with col2:
                            st.metric("Total New Urban Acres", f"{spatial_analysis['total_new_urban_acres'].sum():,.0f}")
                        with col3:
                            st.metric(f"Average per {unit_name[:-1]}", f"{spatial_analysis['total_new_urban_acres'].mean():,.0f}")
                        with col4:
                            st.metric(f"Highest Single {unit_name[:-1]}", f"{spatial_analysis['total_new_urban_acres'].max():,.0f}")
                        
                        # Format data for display
                        display_data = spatial_analysis.copy()
                        display_data["total_new_urban_acres"] = display_data["total_new_urban_acres"].map(lambda x: f"{x:,.0f}")
                        display_data["baseline_urban_acres"] = display_data["baseline_urban_acres"].map(lambda x: f"{x:,.0f}")
                        display_data["avg_urbanization_rate"] = display_data["avg_urbanization_rate"].map(lambda x: f"{x:,.1f}%")
                        display_data["avg_expansion_rate"] = display_data["avg_expansion_rate"].map(lambda x: f"{x:,.1f}")
                        
                        # Rename columns for clarity
                        column_mapping = {
                            "total_new_urban_acres": "Total New Urban Acres",
                            "baseline_urban_acres": "2020 Baseline Urban Acres",
                            "avg_urbanization_rate": "Avg Urbanization Rate (%)",
                            "avg_expansion_rate": "Avg Expansion Rate (acres/decade)"
                        }
                        
                        if selected_spatial_level == "County":
                            column_mapping.update({
                                "county_name": "County",
                                "state_name": "State"
                            })
                        elif selected_spatial_level == "State":
                            column_mapping["state_name"] = "State"
                        elif selected_spatial_level == "Region":
                            column_mapping["region"] = "Region"
                        elif selected_spatial_level == "Subregion":
                            column_mapping["subregion"] = "Subregion"
                        
                        display_data = display_data.rename(columns=column_mapping)
                        
                    except Exception as e:
                        st.error(f"Error during groupby operation: {str(e)}")
                        st.info("Falling back to basic data display")
                        display_data = spatial_data.head(20).copy()
                else:
                    # No valid grouping columns found
                    st.warning(f"No valid grouping columns found for {selected_spatial_level} level in the enhanced data.")
                    st.info(f"Expected columns: {group_cols}")
                    st.info(f"Available columns: {list(spatial_data.columns)}")
                    display_data = spatial_data.head(20).copy()
            else:
                # National level - simple aggregation
                try:
                    spatial_analysis = spatial_data.agg({
                        "total_new_urban_acres": "sum",
                        "baseline_urban_acres_2020": "sum"
                    })
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total New Urban Acres", f"{spatial_analysis['total_new_urban_acres']:,.0f}")
                    with col2:
                        st.metric("Total Baseline Urban Acres (2020)", f"{spatial_analysis['baseline_urban_acres_2020']:,.0f}")
                    
                    display_data = pd.DataFrame({
                        "Metric": ["Total New Urban Acres", "Total Baseline Urban Acres (2020)"],
                        "Value": [f"{spatial_analysis['total_new_urban_acres']:,.0f}", f"{spatial_analysis['baseline_urban_acres_2020']:,.0f}"]
                    })
                except Exception as e:
                    st.error(f"Error during national aggregation: {str(e)}")
                    display_data = spatial_data.head(20).copy()
        else:
            # Fallback: no enhanced data structure, show basic info
            st.info("Enhanced urbanization data structure not available. Showing basic information.")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Records", len(spatial_data))
            with col2:
                st.metric("Data Columns", len(spatial_data.columns))
            
            display_data = spatial_data.head(10)  # Show first 10 rows
    else:
        st.warning("No spatial data available for analysis.")
        display_data = pd.DataFrame()
    
    # 3. DETAILED DATA TABLE FOR SELECTED SPATIAL LEVEL
    st.subheader(f"📋 Detailed Analysis Results ({selected_spatial_level} Level)")
    
    if not display_data.empty:
        # Show data with search/filter capability
        st.dataframe(display_data, use_container_width=True)
    else:
        st.info("No detailed data available to display.")
    
    # 4. ENHANCED DOWNLOAD FUNCTIONALITY FOR SELECTED SPATIAL LEVEL
    st.subheader(f"💾 Enhanced Download Analysis Results ({selected_spatial_level} Level)")
    
    # Prepare enhanced download data
    if selected_spatial_level == "County" and spatial_data is not None and not spatial_data.empty:
        
        # For county level, we need to process the source breakdown data
        # First, aggregate the main metrics without source breakdown
        main_metrics = spatial_data.groupby([
            "fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"
        ]).agg({
            "baseline_urban_acres_2020": "first",
            "total_new_urban_acres": "first", 
            "projected_urban_acres_2070": "first",
            "urbanization_rate_percent": "first",
            "urban_expansion_rate_acres_per_decade": "first",
            "annualized_urban_growth_rate_percent": "first"
        }).reset_index()
        
        # Get source breakdown if available
        if "from_category" in spatial_data.columns and "source_acres" in spatial_data.columns:
            source_breakdown = spatial_data[spatial_data["from_category"].notna()].copy()
            
            # Additional safety check: remove any urban-to-urban transitions that might exist
            source_breakdown = source_breakdown[source_breakdown["from_category"] != "Urban"]
            
            # Pivot to get source categories as columns
            if not source_breakdown.empty:
                source_pivot = source_breakdown.pivot_table(
                    index=["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"],
                    columns="from_category",
                    values="source_acres",
                    fill_value=0
                ).reset_index()
    
                # Flatten column names and add 'acres_from_' prefix
                source_pivot.columns = [
                    f"acres_from_{col.lower().replace(' ', '_').replace('-', '_')}" 
                    if col not in ["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"]
                    else col
                    for col in source_pivot.columns
                ]
                
                # Merge with main metrics
                download_data = main_metrics.merge(
                    source_pivot, 
                    on=["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"],
                    how="left"
                )
                
                # Get list of available source columns for info display
                available_source_cols = [col for col in download_data.columns if col.startswith("acres_from_")]
            else:
                download_data = main_metrics.copy()
                available_source_cols = []
        else:
            download_data = main_metrics.copy()
            available_source_cols = []
            
    elif selected_spatial_level == "State" and spatial_data is not None and not spatial_data.empty:
        # For state level, data is already aggregated properly
        download_data = spatial_data.copy()
        available_source_cols = []
        
    else:
        # Fallback for other spatial levels or empty data
        download_data = spatial_data.copy() if spatial_data is not None else pd.DataFrame()
        available_source_cols = []
    
    if download_data.empty:
        st.warning("No data available for download with the current selection.")
    else:
        # Reorder columns to put key identifiers first
        priority_cols = []
        if "fips_code" in download_data.columns:
            priority_cols.append("fips_code")
        if "county_name" in download_data.columns:
            priority_cols.append("county_name")
        if "state_name" in download_data.columns:
            priority_cols.append("state_name")
        if "region" in download_data.columns:
            priority_cols.append("region")
        if "subregion" in download_data.columns:
            priority_cols.append("subregion")
        
        # Add baseline and metrics columns
        metrics_cols = [
            "baseline_urban_acres_2020",
            "total_new_urban_acres", 
            "projected_urban_acres_2070",
            "urbanization_rate_percent",
            "urban_expansion_rate_acres_per_decade",
            "annualized_urban_growth_rate_percent"
        ]
        
        priority_cols.extend([col for col in metrics_cols if col in download_data.columns])
        priority_cols.extend(available_source_cols)
    
        # Add remaining columns
        remaining_cols = [col for col in download_data.columns if col not in priority_cols]
        final_col_order = priority_cols + remaining_cols
        
        download_data = download_data[final_col_order]
        
        # Round numeric columns for better readability
        numeric_columns = download_data.select_dtypes(include=[np.number]).columns
        download_data[numeric_columns] = download_data[numeric_columns].round(2)
    
        # Add metadata
        download_data["scenario"] = selected_scenario
        download_data["scenario_description"] = scenario_descriptions[selected_scenario_display]
        download_data["spatial_level"] = selected_spatial_level
        download_data["time_period"] = "All Periods (2020-2070)"
        download_data["analysis_type"] = "Enhanced Urbanization Analysis with Baseline Rates"
        download_data["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
        # Convert to CSV
        csv_data = download_data.to_csv(index=False)
        
        # Enhanced info about included features
        info_items = []
        if "fips_code" in download_data.columns:
            info_items.append("🗺️ FIPS codes for GIS integration")
        if "region" in download_data.columns:
            info_items.append("🌎 Regional classifications (Census regions)")
        if "subregion" in download_data.columns:
            info_items.append("📍 Subregional classifications (Census divisions)")
        if "baseline_urban_acres_2020" in download_data.columns:
            info_items.append("📊 2020 baseline urban area for proper rate calculations")
        if "urbanization_rate_percent" in download_data.columns:
            info_items.append("📈 True urbanization rate (% relative to 2020 baseline)")
        if available_source_cols:
            info_items.append(f"🔄 Source land breakdown ({len(available_source_cols)} non-urban categories)")
        
        if info_items:
            st.info("💡 Enhanced exports include: " + " | ".join(info_items))
        
        # Important clarification about urban exclusion and rate calculation
        if available_source_cols or "urbanization_rate_percent" in download_data.columns:
            st.success("""
            🎯 **Key Enhancements:**
            • **NEW urban development only** (excludes urban-to-urban transitions)
            • **Proper urbanization rate** calculated as percentage relative to 2020 baseline urban area
            • **Baseline urban area included** for transparency and validation
            • **Annualized growth rate** for comparing different time horizons
            """)
        
        # Display data preview
        st.subheader(f"📋 Data Preview ({len(download_data):,} records)")
        st.dataframe(download_data.head(20), use_container_width=True)
    
        col1, col2 = st.columns(2)
        with col1:
            scenario_name = selected_scenario_display.replace(' ', '_').replace('(', '').replace(')', '')
            st.download_button(
                label=f"📥 Enhanced Download ({selected_spatial_level} Level)",
                data=csv_data,
                file_name=f"enhanced_urbanization_analysis_{selected_spatial_level.lower()}_{scenario_name}_all_periods.csv",
                mime="text/csv",
                help=f"Download enhanced urbanization analysis with baseline rates, FIPS codes, regions, and source breakdown"
            )
        
        with col2:
            # Top 20 enhanced download (only for aggregated levels)
            if len(download_data) > 20:
                top_20_data = download_data.head(20).copy()
                top_20_csv = top_20_data.to_csv(index=False)
                st.download_button(
                    label=f"📥 Top 20 Download",
                    data=top_20_csv,
                    file_name=f"enhanced_urbanization_top20_{selected_spatial_level.lower()}_{scenario_name}.csv",
                    mime="text/csv",
                    help="Download top 20 records with highest total new urban acres"
                )

# ---- FOREST TRANSITIONS TAB ----
with tab5:
    st.header("🌲 Where is Forest Loss Rate Highest?")
    
    # Load data using database views for spatial levels (similar to urbanization tab)
    @st.cache_data
    def load_forest_data_enhanced(spatial_level, scenario_filter=None, destination_filter=None):
        """Load enhanced forest loss data with FIPS, regions, destination breakdown, and proper forest loss rates."""
        import duckdb
        
        # Define scenario mapping inside the function
        scenario_descriptions = {
            'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)'
        }
        
        # Create reverse mapping for database queries
        scenario_reverse_mapping = {v: k for k, v in scenario_descriptions.items()}
        # Handle the special case for 'Overall Mean'
        scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
        
        db_path = "data/database/rpa.db"
        
        try:
            conn = duckdb.connect(db_path)
            
            if spatial_level == "County":
                # Enhanced county query with baseline forest area and proper rate calculations
                query = '''
                WITH baseline_forest AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        baseline_acres_2020 as baseline_forest_acres_2020
                    FROM baseline_county_land_stock
                    WHERE land_use_code = 'fr'
                ),
                forest_loss_with_destination AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        to_category,
                        SUM(total_area) as forest_lost_acres,
                        region,
                        subregion
                    FROM "County-Level Land Use Transitions"
                    WHERE from_category = 'Forest' AND to_category != 'Forest'
                    GROUP BY fips_code, county_name, state_name, scenario_name, to_category, region, subregion
                ),
                total_forest_loss AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        region,
                        subregion,
                        SUM(forest_lost_acres) as total_forest_lost_acres
                    FROM forest_loss_with_destination
                    GROUP BY fips_code, county_name, state_name, scenario_name, region, subregion
                )
                SELECT 
                    b.fips_code,
                    t.county_name,
                    t.state_name,
                    t.region,
                    t.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_forest_acres_2020, 0) as baseline_forest_acres_2020,
                    COALESCE(t.total_forest_lost_acres, 0) as total_forest_lost_acres,
                    (COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) as projected_forest_acres_2070,
                    -- Proper forest loss rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_forest_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_forest_lost_acres, 0) / b.baseline_forest_acres_2020 * 100)
                        ELSE NULL
                    END as forest_loss_rate_percent,
                    -- Absolute forest loss rate (acres per decade)
                    COALESCE(t.total_forest_lost_acres, 0) / 5.0 as forest_loss_rate_acres_per_decade,
                    -- Annualized loss rate
                    CASE 
                        WHEN COALESCE(b.baseline_forest_acres_2020, 0) > 0 AND (COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) > 0 THEN 
                            (POWER((COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) / b.baseline_forest_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_forest_loss_rate_percent,
                    -- Destination breakdown pivot (need to handle separately)
                    d.to_category,
                    COALESCE(d.forest_lost_acres, 0) as destination_acres
                FROM baseline_forest b
                FULL OUTER JOIN total_forest_loss t ON b.fips_code = t.fips_code 
                    AND b.county_name = t.county_name 
                    AND b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                LEFT JOIN forest_loss_with_destination d ON b.fips_code = d.fips_code 
                    AND b.county_name = d.county_name 
                    AND b.state_name = d.state_name 
                    AND b.scenario_name = d.scenario_name
                WHERE 1=1
                '''
                
                if scenario_filter and scenario_filter != "All Scenarios":
                    scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                    query += f" AND b.scenario_name = '{scenario_key}'"
                
                if destination_filter and destination_filter != "All Destinations":
                    query += f" AND (d.to_category = '{destination_filter}' OR d.to_category IS NULL)"
                
                query += " ORDER BY COALESCE(t.total_forest_lost_acres, 0) DESC"
                
            elif spatial_level == "State":
                # Enhanced state query using baseline_state_land_stock
                query = '''
                WITH baseline_forest AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        baseline_acres_2020 as baseline_forest_acres_2020
                    FROM baseline_state_land_stock
                    WHERE land_use_code = 'fr'
                ),
                forest_loss_development AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        SUM(total_area) as total_forest_lost_acres
                    FROM "State-Level Land Use Transitions"
                    WHERE from_category = 'Forest' AND to_category != 'Forest'
                    GROUP BY state_name, region, subregion, scenario_name
                )
                SELECT 
                    b.state_name,
                    b.region,
                    b.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_forest_acres_2020, 0) as baseline_forest_acres_2020,
                    COALESCE(t.total_forest_lost_acres, 0) as total_forest_lost_acres,
                    (COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) as projected_forest_acres_2070,
                    -- Proper forest loss rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_forest_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_forest_lost_acres, 0) / b.baseline_forest_acres_2020 * 100)
                        ELSE NULL
                    END as forest_loss_rate_percent,
                    -- Absolute forest loss rate (acres per decade)
                    COALESCE(t.total_forest_lost_acres, 0) / 5.0 as forest_loss_rate_acres_per_decade,
                    -- Annualized loss rate
                    CASE 
                        WHEN COALESCE(b.baseline_forest_acres_2020, 0) > 0 AND (COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) > 0 THEN 
                            (POWER((COALESCE(b.baseline_forest_acres_2020, 0) - COALESCE(t.total_forest_lost_acres, 0)) / b.baseline_forest_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_forest_loss_rate_percent
                FROM baseline_forest b
                LEFT JOIN forest_loss_development t ON b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                WHERE 1=1
                '''
                
                if scenario_filter and scenario_filter != "All Scenarios":
                    scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                    query += f" AND b.scenario_name = '{scenario_key}'"
                
                query += " ORDER BY COALESCE(t.total_forest_lost_acres, 0) DESC"
            
            # Execute query and load data
            result_df = conn.execute(query).df()
            conn.close()
            
            if result_df.empty:
                st.warning(f"No data available for {spatial_level} level with the selected scenario.")
                return pd.DataFrame()
            
            return result_df
                
        except Exception as e:
            st.error(f"Error loading enhanced forest loss data: {str(e)}")
            return pd.DataFrame()
    
    # Analysis controls
    st.subheader("Analysis Controls")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Add scenario selector
        scenario_descriptions = {
            'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)'
        }
        
        # Create reverse mapping for database queries
        scenario_reverse_mapping = {v: k for k, v in scenario_descriptions.items()}
        # Handle the special case for 'Overall Mean'
        scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
        
        scenario_options = list(scenario_descriptions.keys())
        selected_scenario_display = st.selectbox("Select RPA Scenario", options=scenario_options, key="forest_scenario")
        
        # Map display name back to database scenario name
        if selected_scenario_display == 'Overall Mean':
            selected_scenario = 'ensemble_overall'
        else:
            selected_scenario = selected_scenario_display
    
    with col2:
        # Add spatial level selector for data extraction
        spatial_levels = ["County", "State", "Subregion", "Region", "National"]
        selected_spatial_level = st.selectbox("Data Extraction Level", options=spatial_levels, 
                                            index=1,  # Default to State
                                            key="forest_spatial",
                                            help="Choose spatial level for data download and detailed analysis")
    
    with col3:
        # Keep destination filter
        # Get destinations from county data for filter options
        county_df = data["County-Level Land Use Transitions"]
        forest_counties_df = county_df[county_df["from_category"] == "Forest"]
        destinations = forest_counties_df["to_category"].unique().tolist()
        destinations.sort()
        selected_destination = st.selectbox("Forest Converted To", 
                                          options=["All Destinations"] + destinations, 
                                          key="forest_destination")
    
    # Load data at selected spatial level
    spatial_data = load_forest_data_enhanced(selected_spatial_level, selected_scenario, selected_destination)
    
    if spatial_data is None:
        st.error("Unable to load forest loss data from database views.")
        st.stop()
    
    # For visualization, always use state-level aggregation for readability
    # Get county transitions data for visualization
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    county_df = county_df[county_df["scenario_name"].isin(key_scenarios)]
    
    # Filter for forest transitions only (where from_category is 'Forest')
    forest_counties_df = county_df[county_df["from_category"] == "Forest"]
    
    # Filter data for visualization (always use state level for charts)
    viz_data = forest_counties_df[forest_counties_df["scenario_name"] == selected_scenario]
    if selected_destination != "All Destinations":
        viz_data = viz_data[viz_data["to_category"] == selected_destination]
    
    # Aggregate visualization data to state level for charts
    viz_analysis = viz_data.groupby(["state_name"]).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names for visualization
    viz_analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    viz_analysis = viz_analysis.reset_index()
    
    # Calculate forest loss rate for visualization
    viz_analysis["forest_loss_rate"] = (viz_analysis["total_acres"] / 
                                       viz_analysis["num_decades"]).round(2)
    
    # Sort by total area for visualization
    viz_analysis = viz_analysis.sort_values("total_acres", ascending=False)
    
    # 1. TOP STATES TEMPORAL TRENDS (for visualization)
    destination_text = f" (converted to {selected_destination})" if selected_destination != "All Destinations" else ""
    st.subheader(f"📈 Forest Loss Trends: Top States ({scenario_descriptions[selected_scenario_display]}){destination_text}")
    st.info(f"📊 Visualization shows state-level data | Data extraction/download uses {selected_spatial_level} level")
    
    # Get top locations for temporal analysis (always states for visualization)
    top_10_viz = viz_analysis.head(10).copy()
    top_10_viz["location"] = top_10_viz["state_name"]
    
    # Create temporal visualization for top states
    if len(top_10_viz) > 0:
        # Get temporal data for top states
        top_states = top_10_viz[["state_name"]].head(10)  # Top 10
        temporal_data = []
        for _, row in top_states.iterrows():
            state_data = viz_data[viz_data["state_name"] == row["state_name"]]
            if len(state_data) > 0:
                state_summary = state_data.groupby("decade_name")["total_area"].sum().reset_index()
                state_summary["location"] = row["state_name"]
                # Calculate percentage change from first period
                if len(state_summary) > 1:
                    baseline = state_summary["total_area"].iloc[0]
                    if baseline > 0:
                        state_summary["pct_change"] = ((state_summary["total_area"] - baseline) / baseline * 100).round(1)
                    else:
                        state_summary["pct_change"] = 0
                else:
                    state_summary["pct_change"] = 0
                temporal_data.append(state_summary)
        
        # Create publication-quality line chart
        if temporal_data:
            # Set dark mode style
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
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
            ax.set_ylabel("Percentage Change from Baseline (%)", fontsize=14, fontweight='bold', color='white')
            ax.set_title(f"Forest Loss Trends: Top 10 States{destination_text} ({scenario_descriptions[selected_scenario_display]})", 
                        fontsize=16, fontweight='bold', pad=20, color='white')
            
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
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # 2. SUMMARY STATISTICS FOR SELECTED SPATIAL LEVEL
    st.subheader(f"📊 Summary Statistics ({selected_spatial_level} Level)")
    
    # Check what columns are available in the enhanced data and handle accordingly
    if spatial_data is not None and not spatial_data.empty:
        # For enhanced data structure with proper baseline rate calculations
        if "total_forest_lost_acres" in spatial_data.columns and "baseline_forest_acres_2020" in spatial_data.columns:
            # Use enhanced data structure with proper columns
            if selected_spatial_level == "County":
                group_cols = ["county_name", "state_name"]
                location_col = "county_name"
                unit_name = "Counties"
            elif selected_spatial_level == "State":
                group_cols = ["state_name"]
                location_col = "state_name"
                unit_name = "States"
            elif selected_spatial_level == "Region":
                group_cols = ["region"]
                location_col = "region"
                unit_name = "Regions"
            elif selected_spatial_level == "Subregion":
                group_cols = ["subregion"]
                location_col = "subregion"
                unit_name = "Subregions"
            else:  # National
                group_cols = []
                location_col = None
                unit_name = "National"
            
            # Aggregate enhanced data for selected spatial level
            if group_cols:
                # Check which columns actually exist in the data
                available_group_cols = [col for col in group_cols if col in spatial_data.columns]
                
                if available_group_cols:
                    try:
                        # Aggregate using the enhanced columns
                        spatial_analysis = spatial_data.groupby(available_group_cols).agg({
                            "total_forest_lost_acres": ["sum", "mean"],
                            "baseline_forest_acres_2020": "first",
                            "forest_loss_rate_percent": "mean",
                            "forest_loss_rate_acres_per_decade": "mean"
                        }).round(2)
                        
                        # Flatten column names
                        spatial_analysis.columns = ["total_forest_lost_acres", "avg_forest_lost_per_area", "baseline_forest_acres", "avg_forest_loss_rate", "avg_loss_rate_per_decade"]
                        spatial_analysis = spatial_analysis.reset_index()
                        
                        # Sort by total forest lost acres
                        spatial_analysis = spatial_analysis.sort_values("total_forest_lost_acres", ascending=False)
                        
                        # Display summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(f"Total {unit_name}", len(spatial_analysis))
                        with col2:
                            st.metric("Total Forest Acres Lost", f"{spatial_analysis['total_forest_lost_acres'].sum():,.0f}")
                        with col3:
                            st.metric(f"Average per {unit_name[:-1]}", f"{spatial_analysis['total_forest_lost_acres'].mean():,.0f}")
                        with col4:
                            st.metric(f"Highest Single {unit_name[:-1]}", f"{spatial_analysis['total_forest_lost_acres'].max():,.0f}")
                        
                        # Format data for display
                        display_data = spatial_analysis.copy()
                        display_data["total_forest_lost_acres"] = display_data["total_forest_lost_acres"].map(lambda x: f"{x:,.0f}")
                        display_data["baseline_forest_acres"] = display_data["baseline_forest_acres"].map(lambda x: f"{x:,.0f}")
                        display_data["avg_forest_loss_rate"] = display_data["avg_forest_loss_rate"].map(lambda x: f"{x:,.1f}%")
                        display_data["avg_loss_rate_per_decade"] = display_data["avg_loss_rate_per_decade"].map(lambda x: f"{x:,.1f}")
                        
                        # Rename columns for clarity
                        column_mapping = {
                            "total_forest_lost_acres": "Total Forest Acres Lost",
                            "baseline_forest_acres": "2020 Baseline Forest Acres",
                            "avg_forest_loss_rate": "Avg Forest Loss Rate (%)",
                            "avg_loss_rate_per_decade": "Avg Loss Rate (acres/decade)"
                        }
                        
                        if selected_spatial_level == "County":
                            column_mapping.update({
                                "county_name": "County",
                                "state_name": "State"
                            })
                        elif selected_spatial_level == "State":
                            column_mapping["state_name"] = "State"
                        elif selected_spatial_level == "Region":
                            column_mapping["region"] = "Region"
                        elif selected_spatial_level == "Subregion":
                            column_mapping["subregion"] = "Subregion"
                        
                        display_data = display_data.rename(columns=column_mapping)
                        
                    except Exception as e:
                        st.error(f"Error during groupby operation: {str(e)}")
                        st.info("Falling back to basic data display")
                        display_data = spatial_data.head(20).copy()
                else:
                    # No valid grouping columns found
                    st.warning(f"No valid grouping columns found for {selected_spatial_level} level in the enhanced data.")
                    st.info(f"Expected columns: {group_cols}")
                    st.info(f"Available columns: {list(spatial_data.columns)}")
                    display_data = spatial_data.head(20).copy()
            else:
                # National level - simple aggregation
                try:
                    spatial_analysis = spatial_data.agg({
                        "total_forest_lost_acres": "sum",
                        "baseline_forest_acres_2020": "sum"
                    })
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Forest Acres Lost", f"{spatial_analysis['total_forest_lost_acres']:,.0f}")
                    with col2:
                        st.metric("Total Baseline Forest Acres (2020)", f"{spatial_analysis['baseline_forest_acres_2020']:,.0f}")
                    
                    display_data = pd.DataFrame({
                        "Metric": ["Total Forest Acres Lost", "Total Baseline Forest Acres (2020)"],
                        "Value": [f"{spatial_analysis['total_forest_lost_acres']:,.0f}", f"{spatial_analysis['baseline_forest_acres_2020']:,.0f}"]
                    })
                except Exception as e:
                    st.error(f"Error during national aggregation: {str(e)}")
                    display_data = spatial_data.head(20).copy()
        else:
            # Fallback: no enhanced data structure, show basic info
            st.info("Enhanced forest loss data structure not available. Showing basic information.")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Records", len(spatial_data))
            with col2:
                st.metric("Data Columns", len(spatial_data.columns))
            
            display_data = spatial_data.head(10)  # Show first 10 rows
    else:
        st.warning("No spatial data available for analysis.")
        display_data = pd.DataFrame()
    
    # 3. DETAILED DATA TABLE FOR SELECTED SPATIAL LEVEL
    st.subheader(f"📋 Detailed Analysis Results ({selected_spatial_level} Level)")
    
    if not display_data.empty:
        # Show data with search/filter capability
        st.dataframe(display_data, use_container_width=True)
    else:
        st.info("No detailed data available to display.")
    
    # 4. ENHANCED DOWNLOAD FUNCTIONALITY FOR SELECTED SPATIAL LEVEL
    st.subheader(f"💾 Enhanced Download Analysis Results ({selected_spatial_level} Level)")
    
    # Prepare enhanced download data
    if selected_spatial_level == "County" and spatial_data is not None and not spatial_data.empty:
        
        # For county level, we need to process the destination breakdown data
        # First, aggregate the main metrics without destination breakdown
        main_metrics = spatial_data.groupby([
            "fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"
        ]).agg({
            "baseline_forest_acres_2020": "first",
            "total_forest_lost_acres": "first", 
            "projected_forest_acres_2070": "first",
            "forest_loss_rate_percent": "first",
            "forest_loss_rate_acres_per_decade": "first",
            "annualized_forest_loss_rate_percent": "first"
        }).reset_index()
        
        # Get destination breakdown if available
        if "to_category" in spatial_data.columns and "destination_acres" in spatial_data.columns:
            destination_breakdown = spatial_data[spatial_data["to_category"].notna()].copy()
            
            # Additional safety check: remove any forest-to-forest transitions that might exist
            destination_breakdown = destination_breakdown[destination_breakdown["to_category"] != "Forest"]
            
            # Pivot to get destination categories as columns
            if not destination_breakdown.empty:
                destination_pivot = destination_breakdown.pivot_table(
                    index=["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"],
                    columns="to_category",
                    values="destination_acres",
                    fill_value=0
                ).reset_index()
    
                # Flatten column names and add 'acres_to_' prefix
                destination_pivot.columns = [
                    f"acres_to_{col.lower().replace(' ', '_').replace('-', '_')}" 
                    if col not in ["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"]
                    else col
                    for col in destination_pivot.columns
                ]
                
                # Merge with main metrics
                download_data = main_metrics.merge(
                    destination_pivot, 
                    on=["fips_code", "county_name", "state_name", "region", "subregion", "scenario_name"],
                    how="left"
                )
                
                # Get list of available destination columns for info display
                available_destination_cols = [col for col in download_data.columns if col.startswith("acres_to_")]
            else:
                download_data = main_metrics.copy()
                available_destination_cols = []
        else:
            download_data = main_metrics.copy()
            available_destination_cols = []
            
    elif selected_spatial_level == "State" and spatial_data is not None and not spatial_data.empty:
        # For state level, data is already aggregated properly
        download_data = spatial_data.copy()
        available_destination_cols = []
        
    else:
        # Fallback for other spatial levels or empty data
        download_data = spatial_data.copy() if spatial_data is not None else pd.DataFrame()
        available_destination_cols = []
    
    if download_data.empty:
        st.warning("No data available for download with the current selection.")
    else:
        # Reorder columns to put key identifiers first
        priority_cols = []
        if "fips_code" in download_data.columns:
            priority_cols.append("fips_code")
        if "county_name" in download_data.columns:
            priority_cols.append("county_name")
        if "state_name" in download_data.columns:
            priority_cols.append("state_name")
        if "region" in download_data.columns:
            priority_cols.append("region")
        if "subregion" in download_data.columns:
            priority_cols.append("subregion")
        
        # Add baseline and metrics columns
        metrics_cols = [
            "baseline_forest_acres_2020",
            "total_forest_lost_acres", 
            "projected_forest_acres_2070",
            "forest_loss_rate_percent",
            "forest_loss_rate_acres_per_decade",
            "annualized_forest_loss_rate_percent"
        ]
        
        priority_cols.extend([col for col in metrics_cols if col in download_data.columns])
        priority_cols.extend(available_destination_cols)
    
        # Add remaining columns
        remaining_cols = [col for col in download_data.columns if col not in priority_cols]
        final_col_order = priority_cols + remaining_cols
        
        download_data = download_data[final_col_order]
        
        # Round numeric columns for better readability
        numeric_columns = download_data.select_dtypes(include=[np.number]).columns
        download_data[numeric_columns] = download_data[numeric_columns].round(2)
    
        # Add metadata
        download_data["scenario"] = selected_scenario
        download_data["scenario_description"] = scenario_descriptions[selected_scenario_display]
        download_data["spatial_level"] = selected_spatial_level
        download_data["destination_filter"] = selected_destination
        download_data["time_period"] = "All Periods (2020-2070)"
        download_data["analysis_type"] = "Enhanced Forest Loss Analysis with Baseline Rates"
        download_data["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
        # Convert to CSV
        csv_data = download_data.to_csv(index=False)
        
        # Enhanced info about included features
        info_items = []
        if "fips_code" in download_data.columns:
            info_items.append("🗺️ FIPS codes for GIS integration")
        if "region" in download_data.columns:
            info_items.append("🌎 Regional classifications (Census regions)")
        if "subregion" in download_data.columns:
            info_items.append("📍 Subregional classifications (Census divisions)")
        if "baseline_forest_acres_2020" in download_data.columns:
            info_items.append("📊 2020 baseline forest area for proper rate calculations")
        if "forest_loss_rate_percent" in download_data.columns:
            info_items.append("📈 True forest loss rate (% relative to 2020 baseline)")
        if available_destination_cols:
            info_items.append(f"🔄 Destination land breakdown ({len(available_destination_cols)} non-forest categories)")
        
        if info_items:
            st.info("💡 Enhanced exports include: " + " | ".join(info_items))
        
        # Important clarification about forest exclusion and rate calculation
        if available_destination_cols or "forest_loss_rate_percent" in download_data.columns:
            st.success("""
            🎯 **Key Enhancements:**
            • **Forest LOSS only** (excludes forest-to-forest transitions)
            • **Proper forest loss rate** calculated as percentage relative to 2020 baseline forest area
            • **Baseline forest area included** for transparency and validation
            • **Annualized loss rate** for comparing different time horizons
            """)
        
        # Display data preview
        st.subheader(f"📋 Data Preview ({len(download_data):,} records)")
        st.dataframe(download_data.head(20), use_container_width=True)
    
        col1, col2 = st.columns(2)
        with col1:
            scenario_name = selected_scenario_display.replace(' ', '_').replace('(', '').replace(')', '')
            destination_name = selected_destination.replace(' ', '_').replace('(', '').replace(')', '')
            st.download_button(
                label=f"📥 Enhanced Download ({selected_spatial_level} Level)",
                data=csv_data,
                file_name=f"enhanced_forest_loss_analysis_{selected_spatial_level.lower()}_{scenario_name}_{destination_name}_all_periods.csv",
                mime="text/csv",
                help=f"Download enhanced forest loss analysis with baseline rates, FIPS codes, regions, and destination breakdown"
            )
        
        with col2:
            # Top 20 enhanced download (only for aggregated levels)
            if len(download_data) > 20:
                top_20_data = download_data.head(20).copy()
                top_20_csv = top_20_data.to_csv(index=False)
                st.download_button(
                    label=f"📥 Top 20 Download",
                    data=top_20_csv,
                    file_name=f"enhanced_forest_loss_top20_{selected_spatial_level.lower()}_{scenario_name}_{destination_name}.csv",
                    mime="text/csv",
                    help="Download top 20 records with highest total forest acres lost"
                )

# ---- AGRICULTURAL TRANSITIONS TAB ----
with tab6:
    st.header("🌾 Where is Agricultural Land Loss Rate Highest?")
    
    # Get county transitions data 
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    county_df = county_df[county_df["scenario_name"].isin(key_scenarios)]
    
    # Filter for agricultural transitions only (where from_category is 'Cropland' or 'Pasture')
    ag_counties_df = county_df[county_df["from_category"].isin(["Cropland", "Pasture"])]
    
    # Analysis controls
    st.subheader("Analysis Controls")
    
    # Fixed settings - no user controls for scenario and analysis level
    selected_scenario = 'ensemble_overall'  # Ensemble Projection
    selected_scenario_display = 'Ensemble Projection'
    analysis_level = "State"
    
    # Keep the source and destination filters
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Source filter
        sources = ["Both Cropland & Pasture"] + ag_counties_df["from_category"].unique().tolist()
        selected_source = st.selectbox("Agricultural Land Type", 
                                     options=sources, 
                                     key="ag_source")
    
    with col2:
        destinations = ag_counties_df["to_category"].unique().tolist()
        destinations.sort()
        selected_destination = st.selectbox("Agricultural Land Converted To", 
                                          options=["All Destinations"] + destinations, 
                                          key="ag_destination")
    
    # Filter data based on selections
    filtered_data = ag_counties_df[ag_counties_df["scenario_name"] == selected_scenario]
    if selected_source != "Both Cropland & Pasture":
        filtered_data = filtered_data[filtered_data["from_category"] == selected_source]
    if selected_destination != "All Destinations":
        filtered_data = filtered_data[filtered_data["to_category"] == selected_destination]
    
    # Aggregate data based on analysis level
    if analysis_level == "County":
        # Check if fips_code column exists, if not use only county and state
        if "fips_code" in filtered_data.columns:
            group_cols = ["county_name", "state_name", "fips_code"]
        else:
            group_cols = ["county_name", "state_name"]
        location_col = "county_name"
    else:  # State
        group_cols = ["state_name"]
        location_col = "state_name"
    
    # Calculate agricultural loss metrics
    ag_analysis = filtered_data.groupby(group_cols).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names
    ag_analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    ag_analysis = ag_analysis.reset_index()
    
    # Calculate agricultural loss rate (acres per decade)
    ag_analysis["ag_loss_rate"] = (ag_analysis["total_acres"] / 
                                 ag_analysis["num_decades"]).round(2)
    
    # Sort by total area
    ag_analysis = ag_analysis.sort_values("total_acres", ascending=False)
    
    # 1. TOP COUNTIES/STATES TEMPORAL TRENDS
    source_text = f" ({selected_source})" if selected_source != "Both Cropland & Pasture" else " (Cropland + Pasture)"
    destination_text = f" (converted to {selected_destination})" if selected_destination != "All Destinations" else ""
    st.subheader(f"📈 Agricultural Land Loss Trends: Top {analysis_level}s ({selected_scenario_display}){source_text}{destination_text}")
    
    # Top 10 visualization
    top_10 = ag_analysis.head(10).copy()
    
    # Create location labels for display
    if analysis_level == "County":
        top_10["location"] = top_10.apply(lambda row: f"{row['county_name']}, {row['state_name']}", axis=1)
    else:
        top_10["location"] = top_10[location_col]
    
    # Create temporal visualization for top counties/states
    if len(top_10) > 0:
        # Get temporal data for top locations
        if analysis_level == "County":
            top_locations = top_10[["county_name", "state_name"]].head(10)  # Top 10
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[
                    (filtered_data["county_name"] == row["county_name"]) & 
                    (filtered_data["state_name"] == row["state_name"])
                ]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = f"{row['county_name']}, {row['state_name']}"
                    # Calculate percentage change from first period
                    if len(location_summary) > 1:
                        baseline = location_summary["total_area"].iloc[0]
                        if baseline > 0:
                            location_summary["pct_change"] = ((location_summary["total_area"] - baseline) / baseline * 100).round(1)
                        else:
                            location_summary["pct_change"] = 0
                    else:
                        location_summary["pct_change"] = 0
                    temporal_data.append(location_summary)
        else:  # State level
            top_locations = top_10[["state_name"]].head(10)  # Top 10
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[filtered_data["state_name"] == row["state_name"]]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = row["state_name"]
                    # Calculate percentage change from first period
                    if len(location_summary) > 1:
                        baseline = location_summary["total_area"].iloc[0]
                        if baseline > 0:
                            location_summary["pct_change"] = ((location_summary["total_area"] - baseline) / baseline * 100).round(1)
                        else:
                            location_summary["pct_change"] = 0
                    else:
                        location_summary["pct_change"] = 0
                    temporal_data.append(location_summary)
        
        # Create publication-quality line chart
        if temporal_data:
            # Set dark mode style
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
            fig.patch.set_facecolor('#0E1117')  # Streamlit dark background
            ax.set_facecolor('#0E1117')
            
            # Sort temporal_data by percentage change (highest to lowest)
            # Calculate final percentage change for each location to sort properly
            location_pct_changes = []
            for location_data in temporal_data:
                # Get the final percentage change value (last time period)
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
            ax.set_ylabel("Percentage Change from Baseline (%)", fontsize=14, fontweight='bold', color='white')
            source_text = f" ({selected_source})" if selected_source != "Both Cropland & Pasture" else " (Cropland + Pasture)"
            destination_text = f" to {selected_destination}" if selected_destination != "All Destinations" else ""
            ax.set_title(f"Agricultural Land Loss Trends: Top 10 {analysis_level}s{source_text}{destination_text} ({selected_scenario_display})", 
                        fontsize=16, fontweight='bold', pad=20, color='white')
            
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
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # 2. SUMMARY STATISTICS AND DATA TABLE
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total States", len(ag_analysis))
    with col2:
        st.metric("Total Agricultural Acres Transitioned", f"{ag_analysis['total_acres'].sum():,.0f}")
    with col3:
        st.metric("Average per State", f"{ag_analysis['total_acres'].mean():,.0f}")
    with col4:
        st.metric("Highest Single State", f"{ag_analysis['total_acres'].max():,.0f}")
    
    # Detailed data table
    st.subheader("📋 Detailed Analysis Results")
    
    # Format data for display
    display_data = ag_analysis.copy()
    display_data["total_acres"] = display_data["total_acres"].map(lambda x: f"{x:,.0f}")
    display_data["avg_acres_per_decade"] = display_data["avg_acres_per_decade"].map(lambda x: f"{x:,.1f}")
    display_data["ag_loss_rate"] = display_data["ag_loss_rate"].map(lambda x: f"{x:,.1f}")
    
    # Rename columns for clarity
    column_mapping = {
        "total_acres": "Total Agricultural Acres Transitioned",
        "avg_acres_per_decade": "Average Acres per Decade",
        "num_decades": "Decades Covered",
        "ag_loss_rate": "Agricultural Transition Rate (acres/decade)"
    }
    
    if analysis_level == "County":
        column_mapping.update({
            "county_name": "County",
            "state_name": "State"
        })
        if "fips_code" in display_data.columns:
            column_mapping["fips_code"] = "FIPS Code"
    else:
        column_mapping["state_name"] = "State"
    
    display_data = display_data.rename(columns=column_mapping)
    
    # Show data with search/filter capability
    st.dataframe(display_data, use_container_width=True)
    
    # 3. DOWNLOAD FUNCTIONALITY
    st.subheader("💾 Download Analysis Results")
    
    # Prepare download data (with original numeric values)
    download_data = ag_analysis.copy()
    
    # Add metadata
    download_data["scenario"] = selected_scenario
    download_data["time_period"] = "All Periods"
    download_data["source_category"] = selected_source
    download_data["destination"] = selected_destination
    download_data["analysis_level"] = analysis_level
    download_data["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Reorder columns for better readability, putting identifiers first
    if analysis_level == "County":
        # For county data, ensure FIPS code is first, followed by names
        id_columns = ["fips_code", "county_name", "state_name"]
        if "region" in download_data.columns:
            id_columns.append("region")
        if "subregion" in download_data.columns:
            id_columns.append("subregion")
    else:  # State
        id_columns = ["state_name"]
    
    # Get data columns (metrics)
    data_columns = ["total_acres", "avg_acres_per_decade", "num_decades", "ag_loss_rate"]
    
    # Get metadata columns
    metadata_columns = ["scenario", "time_period", "source_category", "destination", "analysis_level", "generated_date"]
    
    # Reorder all columns: IDs -> Data -> Metadata
    available_id_cols = [col for col in id_columns if col in download_data.columns]
    available_data_cols = [col for col in data_columns if col in download_data.columns]
    available_meta_cols = [col for col in metadata_columns if col in download_data.columns]
    
    # Add any remaining columns that weren't categorized
    remaining_cols = [col for col in download_data.columns if col not in available_id_cols + available_data_cols + available_meta_cols]
    
    # Final column order
    final_column_order = available_id_cols + available_data_cols + remaining_cols + available_meta_cols
    download_data = download_data[final_column_order]
    
    # Show info about FIPS codes if included
    if "fips_code" in download_data.columns:
        st.info("💡 Downloads include FIPS codes for easy integration with mapping and other datasets")
    
    # Convert to CSV
    csv_data = download_data.to_csv(index=False).encode('utf-8')
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Full Analysis (CSV)",
            data=csv_data,
            file_name=f"ag_loss_analysis_{analysis_level.lower()}_{selected_scenario}_all_periods_{selected_source}_{selected_destination}.csv",
            mime="text/csv",
            help="Download complete analysis results with all metrics"
        )
    
    with col2:
        # Top 20 download
        top_20_data = download_data.head(20).copy()
        
        # Reorder columns for top 20 as well
        if analysis_level == "County":
            id_columns = ["fips_code", "county_name", "state_name"]
            if "region" in top_20_data.columns:
                id_columns.append("region")
            if "subregion" in top_20_data.columns:
                id_columns.append("subregion")
        else:
            id_columns = ["state_name"]
        
        data_columns = ["total_acres", "avg_acres_per_decade", "num_decades", "ag_loss_rate"]
        metadata_columns = ["scenario", "time_period", "source_category", "destination", "analysis_level", "generated_date"]
        
        available_id_cols = [col for col in id_columns if col in top_20_data.columns]
        available_data_cols = [col for col in data_columns if col in top_20_data.columns]
        available_meta_cols = [col for col in metadata_columns if col in top_20_data.columns]
        remaining_cols = [col for col in top_20_data.columns if col not in available_id_cols + available_data_cols + available_meta_cols]
        
        final_column_order = available_id_cols + available_data_cols + remaining_cols + available_meta_cols
        top_20_data = top_20_data[final_column_order]
        
        top_20_csv = top_20_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🏆 Download Top 20 (CSV)",
            data=top_20_csv,
            file_name=f"top_20_ag_loss_{analysis_level.lower()}_{selected_scenario}.csv",
            mime="text/csv",
            help="Download top 20 areas by agricultural land loss"
        )

# ---- STATE MAP TAB ----
with tab7:
    st.header("State-Level Land Use Change Map")
    
    # Get county transitions data
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    county_df = county_df[county_df["scenario_name"].isin(key_scenarios)]
    
    # Controls for map
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Transition type selection
        transition_options = [
            "All Transitions", 
            "To Urban Land", 
            "From Forest Land"
        ]
        selected_transition = st.selectbox(
            "Transition Type", 
            options=transition_options,
            key="map_transition"
        )
        
        # Map transition selection to filter values
        transition_mapping = {
            "All Transitions": "all",
            "To Urban Land": "to_urban",
            "From Forest Land": "from_forest"
        }
        transition_filter = transition_mapping[selected_transition]
    
    with col2:
        # Scenario selection with descriptions
        scenario_descriptions = {
            'ensemble_LM': 'Lower Warming, Moderate Growth',
            'ensemble_HL': 'High Warming, Low Growth', 
            'ensemble_HM': 'High Warming, Moderate Growth',
            'ensemble_HH': 'High Warming, High Growth',
            'ensemble_overall': 'Overall Mean Projection'
        }
        
        map_scenarios = county_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in map_scenarios]
        selected_scenario_display = st.selectbox(
            "Scenario", 
            options=scenario_options,
            key="map_scenario"
        )
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_map_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col3:
        # Decade selection
        map_decades = county_df["decade_name"].unique().tolist()
        map_decades.sort() # Sort chronologically
        selected_map_decade = st.selectbox(
            "Time Period", 
            options=map_decades,
            key="map_decade"
        )
    
    # Aggregate data to state level
    state_data = aggregate_to_state_level(
        county_df,
        transition_filter,
        selected_map_scenario,
        selected_map_decade
    )
    
    # Create map title
    map_title = f"{selected_transition} ({selected_map_scenario}, {selected_map_decade})"
    
    # Create folium map
    state_map = create_state_map(state_data, map_title)
    
    # Display the map
    st.subheader("Land Use Change by State")
    if state_map is not None:
        folium_static(state_map, width=1000, height=600)
    else:
        st.error("Geographic mapping is currently unavailable due to data loading issues.")
        st.info("You can still view the data in the table below.")
    
    # Add data table below the map
    with st.expander("Show State Data Table"):
        # Sort by total area for better readability
        sorted_state_data = state_data.sort_values("total_area", ascending=False)
        
        # Format for display
        sorted_state_data["total_area"] = sorted_state_data["total_area"].map(lambda x: f"{x:,.0f} acres")
        sorted_state_data.columns = ["State", "Area Changed"]
        
        st.dataframe(sorted_state_data)

# Add footer
st.markdown("---")
st.markdown("""
**Data Source**: USDA Forest Service's Resources Planning Act (RPA) Assessment

This app uses optimized data views created with DuckDB. For more information, see the [GitHub repository](https://github.com/your-username/rpa-landuse).
""")

# Add sidebar info
st.sidebar.header("About")
st.sidebar.info("""
This app visualizes land use change projections from the USDA Forest Service's 2020 RPA Assessment.

The data has been optimized for web deployment using DuckDB for data processing.
""") 