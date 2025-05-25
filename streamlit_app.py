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
@st.cache_data(ttl=3600)  # Cache for 1 hour, helps with SSL issues
def load_us_states():
    # Skip remote download due to SSL issues on macOS, use local fallback directly
    try:
        # Create states boundary from counties data
        counties_path = "data/counties.geojson"
        if os.path.exists(counties_path):
            counties = gpd.read_file(counties_path)
            # Create a simple state FIPS to name mapping
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
            
            # Add state names to counties
            counties['state_name'] = counties['STATE'].map(state_fips_to_name)
            
            # Dissolve counties by state to create state boundaries
            if 'state_name' in counties.columns:
                states = counties.dissolve(by='state_name').reset_index()
                states = states.rename(columns={'state_name': 'name'})
                st.info("Using local geographic data for state boundaries.")
                return states
    except Exception as e:
        st.warning(f"Could not load local states data: {e}")
    
    # If local fallback fails, try remote as last resort
    try:
        st.info("Attempting to download remote geographic data...")
        url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
        return gpd.read_file(url)
    except Exception as e:
        st.warning(f"Could not load remote states data: {e}")
        
        # Final fallback: return None and disable mapping
        st.warning("Geographic mapping is disabled due to data loading issues.")
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

# Create choropleth map
def create_state_map(state_data, title):
    """Create a folium choropleth map of states"""
    # Load GeoJSON of US states
    states_geojson = load_us_states()
    
    # If states data couldn't be loaded, return None
    if states_geojson is None:
        return None
    
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Overview", "Data Explorer", "Urbanization Trends", "Forest Transitions", "Agricultural Transitions", "State Map"])

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
    st.header("🏙️ Where is Urban Development Rate Highest?")
    
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
    
    # Filter for urban transitions only (where to_category is 'Urban')
    urban_counties_df = county_df[county_df["to_category"] == "Urban"]
    
    # Analysis controls
    st.subheader("Analysis Controls")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Scenario selection with descriptions
        scenario_descriptions = {
            'ensemble_LM': 'Sustainable Development Pathway',
            'ensemble_HL': 'Climate Challenge Scenario', 
            'ensemble_HM': 'Moderate Growth Scenario',
            'ensemble_HH': 'High Development Scenario',
            'ensemble_overall': 'Ensemble Projection'
        }
        
        scenarios = urban_counties_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in scenarios]
        selected_scenario_display = st.selectbox("Select Scenario", options=scenario_options, key="urban_scenario")
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col2:
        # Analysis level
        analysis_level = st.selectbox("Analysis Level", 
                                    options=["County", "State"], 
                                    key="urban_level")
    
    # Filter data based on selections
    filtered_data = urban_counties_df[urban_counties_df["scenario_name"] == selected_scenario]
    
    # Aggregate data based on analysis level
    if analysis_level == "County":
        # Check if fips_code column exists, if not use only county and state
        if "fips_code" in filtered_data.columns:
            group_cols = ["county_name", "state_name", "fips_code"]
        else:
            group_cols = ["county_name", "state_name"]
        location_col = "county_name"
        location_display = lambda row: f"{row['county_name']}, {row['state_name']}"
    elif analysis_level == "State":
        group_cols = ["state_name"]
        location_col = "state_name"
        location_display = lambda row: row['state_name']
    else:  # Region - fallback to state since region_name doesn't exist
        group_cols = ["state_name"]
        location_col = "state_name"
        location_display = lambda row: row['state_name']
    
    # Calculate urbanization metrics
    urban_analysis = filtered_data.groupby(group_cols).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names
    urban_analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    urban_analysis = urban_analysis.reset_index()
    
    # Calculate urbanization rate (acres per decade)
    urban_analysis["urbanization_rate"] = (urban_analysis["total_acres"] / 
                                         urban_analysis["num_decades"]).round(2)
    
    # Sort by total area
    urban_analysis = urban_analysis.sort_values("total_acres", ascending=False)
    
    # Display results
    st.subheader(f"📈 Urban Development Trends ({selected_scenario_display})")
    
    # Get top locations for temporal analysis
    top_10 = urban_analysis.head(10).copy()
    
    # Create location labels for display
    if analysis_level == "County":
        top_10["location"] = top_10.apply(lambda row: f"{row['county_name']}, {row['state_name']}", axis=1)
    else:
        top_10["location"] = top_10[location_col]
    
    # Create temporal visualization for top counties/states
    if len(top_10) > 0:
        # Get temporal data for top locations
        if analysis_level == "County":
            top_locations = top_10[["county_name", "state_name"]].head(5)  # Top 5 for readability
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[
                    (filtered_data["county_name"] == row["county_name"]) & 
                    (filtered_data["state_name"] == row["state_name"])
                ]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = f"{row['county_name']}, {row['state_name']}"
                    temporal_data.append(location_summary)
        else:  # State level
            top_locations = top_10[["state_name"]].head(5)
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[filtered_data["state_name"] == row["state_name"]]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = row["state_name"]
                    temporal_data.append(location_summary)
        
        # Create line chart
        if temporal_data:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            for location_data in temporal_data:
                ax.plot(location_data["decade_name"], location_data["total_area"], 
                       marker='o', linewidth=2.5, markersize=6, label=location_data["location"].iloc[0])
            
            ax.set_xlabel("Time Period", fontsize=12)
            ax.set_ylabel("Acres Converted to Urban", fontsize=12)
            ax.set_title(f"Urban Development Trends: Top 5 {analysis_level}s ({selected_scenario_display})", fontsize=14)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Areas Analyzed", len(urban_analysis))
    with col2:
        st.metric("Total Acres Urbanized", f"{urban_analysis['total_acres'].sum():,.0f}")
    with col3:
        st.metric("Average per Area", f"{urban_analysis['total_acres'].mean():,.0f}")
    with col4:
        st.metric("Highest Single Area", f"{urban_analysis['total_acres'].max():,.0f}")
    
    # Detailed data table
    st.subheader("📋 Detailed Analysis Results")
    
    # Format data for display
    display_data = urban_analysis.copy()
    display_data["total_acres"] = display_data["total_acres"].map(lambda x: f"{x:,.0f}")
    display_data["avg_acres_per_decade"] = display_data["avg_acres_per_decade"].map(lambda x: f"{x:,.1f}")
    display_data["urbanization_rate"] = display_data["urbanization_rate"].map(lambda x: f"{x:,.1f}")
    
    # Rename columns for clarity
    column_mapping = {
        "total_acres": "Total Acres Urbanized",
        "avg_acres_per_decade": "Average Acres per Decade",
        "num_decades": "Decades Covered",
        "urbanization_rate": "Urbanization Rate (acres/decade)"
    }
    
    if analysis_level == "County":
        column_mapping.update({
            "county_name": "County",
            "state_name": "State"
        })
        if "fips_code" in display_data.columns:
            column_mapping["fips_code"] = "FIPS Code"
    elif analysis_level == "State":
        column_mapping["state_name"] = "State"
    else:
        column_mapping[location_col] = "Region"
    
    display_data = display_data.rename(columns=column_mapping)
    
    # Show data with search/filter capability
    st.dataframe(display_data, use_container_width=True)
    
    # Download functionality
    st.subheader("💾 Download Analysis Results")
    
    # Prepare download data (with original numeric values)
    download_data = urban_analysis.copy()
    
    # Add metadata
    download_data["scenario"] = selected_scenario
    download_data["time_period"] = "All Periods"
    download_data["analysis_level"] = analysis_level
    download_data["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Convert to CSV
    csv_data = download_data.to_csv(index=False).encode('utf-8')
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Full Analysis (CSV)",
            data=csv_data,
            file_name=f"urban_development_analysis_{analysis_level.lower()}_{selected_scenario}_all_periods.csv",
            mime="text/csv",
            help="Download complete analysis results with all metrics"
        )
    
    with col2:
        # Top 20 download
        top_20_data = download_data.head(20).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🏆 Download Top 20 (CSV)",
            data=top_20_data,
            file_name=f"top_20_urban_development_{analysis_level.lower()}_{selected_scenario}.csv",
            mime="text/csv",
            help="Download top 20 areas by urban development"
        )
    
    # National trends visualization
    st.subheader("📈 National Urbanization Trends")
    
    urbanization_df = data["Urbanization Trends By Decade"]
    filtered_urban = urbanization_df[urbanization_df["scenario_name"] == selected_scenario]
    
    # Plot the data
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    ax3.plot(filtered_urban["decade_name"], filtered_urban["forest_to_urban"], 
             marker='o', linewidth=2, label="Forest to Urban")
    ax3.plot(filtered_urban["decade_name"], filtered_urban["cropland_to_urban"], 
             marker='s', linewidth=2, label="Cropland to Urban")
    ax3.plot(filtered_urban["decade_name"], filtered_urban["pasture_to_urban"], 
             marker='^', linewidth=2, label="Pasture to Urban")
    
    ax3.set_xlabel("Time Period")
    ax3.set_ylabel("Acres Converted")
    ax3.set_title(f"National Land Conversion to Urban Areas: {selected_scenario}")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    st.pyplot(fig3)
    
    with st.expander("📊 Show National Trends Data"):
        display_trends = filtered_urban.copy()
        for col in display_trends.select_dtypes(include=['object']).columns:
            display_trends[col] = display_trends[col].astype(str)
        st.dataframe(display_trends)

# ---- FOREST TRANSITIONS TAB ----
with tab4:
    st.header("🌲 Where is Forest Loss Rate Highest?")
    
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
    
    # Filter for forest transitions only (where from_category is 'Forest')
    forest_counties_df = county_df[county_df["from_category"] == "Forest"]
    
    # Analysis controls
    st.subheader("Analysis Controls")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Scenario selection with descriptions
        scenario_descriptions = {
            'ensemble_LM': 'Sustainable Development Pathway',
            'ensemble_HL': 'Climate Challenge Scenario', 
            'ensemble_HM': 'Moderate Growth Scenario',
            'ensemble_HH': 'High Development Scenario',
            'ensemble_overall': 'Ensemble Projection'
        }
        
        scenarios = forest_counties_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in scenarios]
        selected_scenario_display = st.selectbox("Select Scenario", options=scenario_options, key="forest_scenario")
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col2:
        # Analysis level
        analysis_level = st.selectbox("Analysis Level", 
                                    options=["County", "State"], 
                                    key="forest_level")
    
    with col3:
        # Destination filter
        destinations = forest_counties_df["to_category"].unique().tolist()
        destinations.sort()
        selected_destination = st.selectbox("Forest Converted To", 
                                          options=["All Destinations"] + destinations, 
                                          key="forest_destination")
    
    # Filter data based on selections
    filtered_data = forest_counties_df[forest_counties_df["scenario_name"] == selected_scenario]
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
    
    # Calculate forest loss metrics
    forest_analysis = filtered_data.groupby(group_cols).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names
    forest_analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    forest_analysis = forest_analysis.reset_index()
    
    # Calculate forest loss rate (acres per decade)
    forest_analysis["forest_loss_rate"] = (forest_analysis["total_acres"] / 
                                         forest_analysis["num_decades"]).round(2)
    
    # Sort by total area
    forest_analysis = forest_analysis.sort_values("total_acres", ascending=False)
    
    # Display results
    destination_text = f" (converted to {selected_destination})" if selected_destination != "All Destinations" else ""
    st.subheader(f"📈 Forest Loss Trends ({selected_scenario_display}){destination_text}")
    
    # Get top locations for temporal analysis
    top_10 = forest_analysis.head(10).copy()
    
    # Create location labels for display
    if analysis_level == "County":
        top_10["location"] = top_10.apply(lambda row: f"{row['county_name']}, {row['state_name']}", axis=1)
    else:
        top_10["location"] = top_10[location_col]
    
    # Create temporal visualization for top counties/states
    if len(top_10) > 0:
        # Get temporal data for top locations
        if analysis_level == "County":
            top_locations = top_10[["county_name", "state_name"]].head(5)  # Top 5 for readability
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[
                    (filtered_data["county_name"] == row["county_name"]) & 
                    (filtered_data["state_name"] == row["state_name"])
                ]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = f"{row['county_name']}, {row['state_name']}"
                    temporal_data.append(location_summary)
        else:  # State level
            top_locations = top_10[["state_name"]].head(5)
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[filtered_data["state_name"] == row["state_name"]]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = row["state_name"]
                    temporal_data.append(location_summary)
        
        # Create line chart
        if temporal_data:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            for location_data in temporal_data:
                ax.plot(location_data["decade_name"], location_data["total_area"], 
                       marker='o', linewidth=2.5, markersize=6, label=location_data["location"].iloc[0])
            
            ax.set_xlabel("Time Period", fontsize=12)
            ax.set_ylabel("Acres of Forest Lost", fontsize=12)
            destination_text = f" (to {selected_destination})" if selected_destination != "All Destinations" else ""
            ax.set_title(f"Forest Loss Trends: Top 5 {analysis_level}s{destination_text} ({selected_scenario_display})", fontsize=14)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Areas Analyzed", len(forest_analysis))
    with col2:
        st.metric("Total Forest Acres Lost", f"{forest_analysis['total_acres'].sum():,.0f}")
    with col3:
        st.metric("Average per Area", f"{forest_analysis['total_acres'].mean():,.0f}")
    with col4:
        st.metric("Highest Single Area", f"{forest_analysis['total_acres'].max():,.0f}")
    
    # Detailed data table
    st.subheader("📋 Detailed Analysis Results")
    
    # Format data for display
    display_data = forest_analysis.copy()
    display_data["total_acres"] = display_data["total_acres"].map(lambda x: f"{x:,.0f}")
    display_data["avg_acres_per_decade"] = display_data["avg_acres_per_decade"].map(lambda x: f"{x:,.1f}")
    display_data["forest_loss_rate"] = display_data["forest_loss_rate"].map(lambda x: f"{x:,.1f}")
    
    # Rename columns for clarity
    column_mapping = {
        "total_acres": "Total Forest Acres Lost",
        "avg_acres_per_decade": "Average Acres per Decade",
        "num_decades": "Decades Covered",
        "forest_loss_rate": "Forest Loss Rate (acres/decade)"
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
    
    # Download functionality
    st.subheader("💾 Download Analysis Results")
    
    # Prepare download data (with original numeric values)
    download_data = forest_analysis.copy()
    
    # Add metadata
    download_data["scenario"] = selected_scenario
    download_data["time_period"] = "All Periods"
    download_data["destination"] = selected_destination
    download_data["analysis_level"] = analysis_level
    download_data["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Convert to CSV
    csv_data = download_data.to_csv(index=False).encode('utf-8')
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Full Analysis (CSV)",
            data=csv_data,
            file_name=f"forest_loss_analysis_{analysis_level.lower()}_{selected_scenario}_all_periods_{selected_destination}.csv",
            mime="text/csv",
            help="Download complete analysis results with all metrics"
        )
    
    with col2:
        # Top 20 download
        top_20_data = download_data.head(20).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🏆 Download Top 20 (CSV)",
            data=top_20_data,
            file_name=f"top_20_forest_loss_{analysis_level.lower()}_{selected_scenario}.csv",
            mime="text/csv",
            help="Download top 20 areas by forest loss"
        )
    
    # National trends visualization
    st.subheader("📈 National Forest Loss Trends by Destination")
    
    from_forest_df = data["Transitions from Forest Land"]
    filtered_forest = from_forest_df[from_forest_df["scenario_name"] == selected_scenario]
    
    # Aggregate data by destination land use
    forest_to_use = filtered_forest.groupby(["to_category", "decade_name"])["total_area"].sum().reset_index()
    
    # Pivot table for plotting
    pivot_forest = forest_to_use.pivot(index="decade_name", columns="to_category", values="total_area")
    
    # Plot the data
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    pivot_forest.plot(kind="bar", ax=ax3, width=0.8)
    ax3.set_xlabel("Time Period")
    ax3.set_ylabel("Acres of Forest Lost")
    ax3.set_title(f"National Forest Land Conversion by Destination: {selected_scenario}")
    ax3.legend(title="Converted To", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    st.pyplot(fig3)
    
    with st.expander("📊 Show National Trends Data"):
        st.dataframe(pivot_forest)

# ---- AGRICULTURAL TRANSITIONS TAB ----
with tab5:
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
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Scenario selection with descriptions
        scenario_descriptions = {
            'ensemble_LM': 'Sustainable Development Pathway',
            'ensemble_HL': 'Climate Challenge Scenario', 
            'ensemble_HM': 'Moderate Growth Scenario',
            'ensemble_HH': 'High Development Scenario',
            'ensemble_overall': 'Ensemble Projection'
        }
        
        scenarios = ag_counties_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in scenarios]
        selected_scenario_display = st.selectbox("Select Scenario", options=scenario_options, key="ag_scenario")
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col2:
        # Analysis level
        analysis_level = st.selectbox("Analysis Level", 
                                    options=["County", "State"], 
                                    key="ag_level")
    
    with col3:
        # Source filter
        sources = ["Both Cropland & Pasture"] + ag_counties_df["from_category"].unique().tolist()
        selected_source = st.selectbox("Agricultural Land Type", 
                                     options=sources, 
                                     key="ag_source")
    
    # Additional filter for destination
    col4, col5 = st.columns([1, 1])
    with col4:
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
    
    # Display results
    source_text = f" ({selected_source})" if selected_source != "Both Cropland & Pasture" else " (Cropland + Pasture)"
    destination_text = f" (converted to {selected_destination})" if selected_destination != "All Destinations" else ""
    st.subheader(f"📈 Agricultural Land Loss Trends ({selected_scenario_display}){source_text}{destination_text}")
    
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
            top_locations = top_10[["county_name", "state_name"]].head(5)  # Top 5 for readability
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[
                    (filtered_data["county_name"] == row["county_name"]) & 
                    (filtered_data["state_name"] == row["state_name"])
                ]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = f"{row['county_name']}, {row['state_name']}"
                    temporal_data.append(location_summary)
        else:  # State level
            top_locations = top_10[["state_name"]].head(5)
            temporal_data = []
            for _, row in top_locations.iterrows():
                location_data = filtered_data[filtered_data["state_name"] == row["state_name"]]
                if len(location_data) > 0:
                    location_summary = location_data.groupby("decade_name")["total_area"].sum().reset_index()
                    location_summary["location"] = row["state_name"]
                    temporal_data.append(location_summary)
        
        # Create line chart
        if temporal_data:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            for location_data in temporal_data:
                ax.plot(location_data["decade_name"], location_data["total_area"], 
                       marker='o', linewidth=2.5, markersize=6, label=location_data["location"].iloc[0])
            
            ax.set_xlabel("Time Period", fontsize=12)
            ax.set_ylabel("Acres of Agricultural Land Lost", fontsize=12)
            source_text = f" ({selected_source})" if selected_source != "Both Cropland & Pasture" else " (Cropland + Pasture)"
            destination_text = f" to {selected_destination}" if selected_destination != "All Destinations" else ""
            ax.set_title(f"Agricultural Land Loss Trends: Top 5 {analysis_level}s{source_text}{destination_text} ({selected_scenario_display})", fontsize=14)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No temporal data available for visualization.")
    else:
        st.warning("No data available for the selected criteria.")
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Areas Analyzed", len(ag_analysis))
    with col2:
        st.metric("Total Agricultural Acres Lost", f"{ag_analysis['total_acres'].sum():,.0f}")
    with col3:
        st.metric("Average per Area", f"{ag_analysis['total_acres'].mean():,.0f}")
    with col4:
        st.metric("Highest Single Area", f"{ag_analysis['total_acres'].max():,.0f}")
    
    # Detailed data table
    st.subheader("📋 Detailed Analysis Results")
    
    # Format data for display
    display_data = ag_analysis.copy()
    display_data["total_acres"] = display_data["total_acres"].map(lambda x: f"{x:,.0f}")
    display_data["avg_acres_per_decade"] = display_data["avg_acres_per_decade"].map(lambda x: f"{x:,.1f}")
    display_data["ag_loss_rate"] = display_data["ag_loss_rate"].map(lambda x: f"{x:,.1f}")
    
    # Rename columns for clarity
    column_mapping = {
        "total_acres": "Total Agricultural Acres Lost",
        "avg_acres_per_decade": "Average Acres per Decade",
        "num_decades": "Decades Covered",
        "ag_loss_rate": "Agricultural Loss Rate (acres/decade)"
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
    
    # Download functionality
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
        top_20_data = download_data.head(20).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🏆 Download Top 20 (CSV)",
            data=top_20_data,
            file_name=f"top_20_ag_loss_{analysis_level.lower()}_{selected_scenario}.csv",
            mime="text/csv",
            help="Download top 20 areas by agricultural land loss"
        )
    
    # National trends visualization
    st.subheader("📈 National Agricultural Land Loss Trends by Source")
    
    # Create trends data by aggregating cropland and pasture separately
    ag_trends = ag_counties_df[ag_counties_df["scenario_name"] == selected_scenario]
    
    # Aggregate data by source land use
    ag_to_use = ag_trends.groupby(["from_category", "decade_name"])["total_area"].sum().reset_index()
    
    # Pivot table for plotting
    pivot_ag = ag_to_use.pivot(index="decade_name", columns="from_category", values="total_area")
    
    # Plot the data
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    pivot_ag.plot(kind="bar", ax=ax3, width=0.8)
    ax3.set_xlabel("Time Period")
    ax3.set_ylabel("Acres of Agricultural Land Lost")
    ax3.set_title(f"National Agricultural Land Loss by Source: {selected_scenario}")
    ax3.legend(title="Source Land Use", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    st.pyplot(fig3)
    
    with st.expander("📊 Show National Trends Data"):
        st.dataframe(pivot_ag)

# ---- STATE MAP TAB ----
with tab6:
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