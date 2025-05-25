import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import folium
from streamlit_folium import folium_static
import geopandas as gpd

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
@st.cache_data
def load_us_states():
    # Use a simplified US states GeoJSON from a public source
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
    return gpd.read_file(url)

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

# Create choropleth map
def create_state_map(state_data, title):
    """Create a folium choropleth map of states"""
    # Load GeoJSON of US states
    states_geojson = load_us_states()
    
    # Center the map on the continental US
    map_center = [39.8283, -98.5795]
    state_map = folium.Map(location=map_center, zoom_start=4, scrollWheelZoom=False)
    
    # Create choropleth layer
    choropleth = folium.Choropleth(
        geo_data=states_geojson,
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
    
    # Add title as a caption
    title_html = f'''
        <h3 align="center" style="font-size:16px"><b>{title}</b></h3>
    '''
    state_map.get_root().html.add_child(folium.Element(title_html))
    
    return state_map

# Main layout with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Data Explorer", "Urbanization Trends", "Forest Transitions", "State Map"])

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
    
    # Select dataset to explore
    dataset_options = list(data.keys())
    selected_dataset = st.selectbox("Select Dataset", options=dataset_options)
    
    # Show dataset
    st.subheader(f"Exploring: {selected_dataset}")
    selected_df = data[selected_dataset]
    
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
    csv = selected_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'{selected_dataset}.csv',
        mime='text/csv',
    )

# ---- URBANIZATION TRENDS TAB ----
with tab3:
    st.header("Urbanization Trends")
    
    # Filter controls
    st.subheader("Explore Urbanization Trends")
    
    urbanization_df = data["Urbanization Trends By Decade"]
    # Convert to string for display in selectbox
    scenarios = urbanization_df["scenario_name"].unique().tolist()
    scenarios = [str(s) for s in scenarios]
    selected_scenario = st.selectbox("Select Scenario", options=scenarios)
    
    # Filter data based on selection
    filtered_urban = urbanization_df[urbanization_df["scenario_name"] == selected_scenario]
    
    # Plot the data
    st.subheader(f"Land Conversion to Urban Areas: {selected_scenario}")
    
    fig, ax = plt.figure(figsize=(10, 6)), plt.subplot()
    ax.plot(filtered_urban["decade_name"], filtered_urban["forest_to_urban"], marker='o', label="Forest to Urban")
    ax.plot(filtered_urban["decade_name"], filtered_urban["cropland_to_urban"], marker='s', label="Cropland to Urban")
    ax.plot(filtered_urban["decade_name"], filtered_urban["pasture_to_urban"], marker='^', label="Pasture to Urban")
    ax.set_xlabel("Time Period")
    ax.set_ylabel("Acres")
    ax.set_title(f"Land Conversion to Urban Areas: {selected_scenario}")
    ax.legend()
    plt.tight_layout()
    
    st.pyplot(fig)
    
    with st.expander("Show Data Table"):
        # Convert object columns to string to avoid PyArrow conversion issues
        display_df = filtered_urban.copy()
        for col in display_df.select_dtypes(include=['object']).columns:
            display_df[col] = display_df[col].astype(str)
        st.dataframe(display_df)
    
    st.subheader("Top Counties Converting to Urban Land")
    
    # Get county transitions data 
    county_df = data["County-Level Land Use Transitions"]
    # Filter for urban transitions only (where to_category is 'Urban')
    urban_counties_df = county_df[county_df["to_category"] == "Urban"]
    
    # Group by county and sum total area
    urban_by_county = urban_counties_df.groupby(["county_name", "state_name"])["total_area"].sum().reset_index()
    urban_by_county = urban_by_county.sort_values("total_area", ascending=False).head(10)
    
    fig2, ax2 = plt.figure(figsize=(10, 6)), plt.subplot()
    ax2.bar(urban_by_county["county_name"] + ", " + urban_by_county["state_name"], urban_by_county["total_area"])
    ax2.set_xlabel("County")
    ax2.set_ylabel("Acres")
    ax2.set_title("Top 10 Counties by Urbanization")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    st.pyplot(fig2)

# ---- FOREST TRANSITIONS TAB ----
with tab4:
    st.header("Forest Land Transitions")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        from_forest_df = data["Transitions from Forest Land"]
        # Convert to string for display in selectbox
        forest_scenarios = from_forest_df["scenario_name"].unique().tolist()
        forest_scenarios = [str(s) for s in forest_scenarios]
        selected_scenario_forest = st.selectbox("Select Scenario", 
                                               options=forest_scenarios,
                                               key="forest_scenario")
    
    # Filter data
    filtered_forest = from_forest_df[from_forest_df["scenario_name"] == selected_scenario_forest]
    
    # Aggregate data by destination land use
    forest_to_use = filtered_forest.groupby(["to_category", "decade_name"])["total_area"].sum().reset_index()
    
    # Pivot table for plotting
    pivot_forest = forest_to_use.pivot(index="decade_name", columns="to_category", values="total_area")
    
    # Plot the data
    st.subheader(f"Forest Land Conversion: {selected_scenario_forest}")
    
    fig3, ax3 = plt.figure(figsize=(10, 6)), plt.subplot()
    pivot_forest.plot(kind="bar", ax=ax3)
    ax3.set_xlabel("Time Period")
    ax3.set_ylabel("Acres")
    ax3.set_title(f"Forest Land Conversion by Destination: {selected_scenario_forest}")
    plt.tight_layout()
    
    st.pyplot(fig3)
    
    with st.expander("Show Data Table"):
        st.dataframe(pivot_forest)

# ---- STATE MAP TAB ----
with tab5:
    st.header("State-Level Land Use Change Map")
    
    # Get county transitions data
    county_df = data["County-Level Land Use Transitions"]
    
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
        # Scenario selection
        map_scenarios = county_df["scenario_name"].unique().tolist()
        map_scenarios = [str(s) for s in map_scenarios]
        selected_map_scenario = st.selectbox(
            "Scenario", 
            options=map_scenarios,
            key="map_scenario"
        )
    
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
    folium_static(state_map, width=1000, height=600)
    
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