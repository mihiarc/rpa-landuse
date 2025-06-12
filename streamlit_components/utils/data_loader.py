"""
Data loading utilities for the RPA Land Use Viewer application.

This module handles all data loading operations including parquet files,
geographic data, and database connections with proper caching.
"""
import os
import pandas as pd
import streamlit as st
import json
import requests
import geopandas as gpd
import tempfile
from typing import Dict, Optional


@st.cache_data
def load_parquet_data() -> Dict[str, pd.DataFrame]:
    """
    Load preprocessed parquet files for the application.
    
    Returns:
        Dict[str, pd.DataFrame]: Dictionary of dataset names to DataFrames
    """
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_us_states() -> dict:
    """
    Load US states geographic data without any projection system dependencies.
    
    Returns:
        dict: GeoJSON data for US states
    """
    # Method 1: Try to download remote GeoJSON and parse it directly
    try:
        st.info("Downloading US states geographic data...")
        
        url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
        
        # Download with SSL verification disabled
        response = requests.get(url, verify=False)
        response.raise_for_status()
        
        # Parse JSON directly - no GeoPandas needed for this step
        geojson_data = json.loads(response.text)
        
        # Clear the info message
        st.empty()
        
        return geojson_data
        
    except Exception as e:
        st.warning(f"Failed to download remote data: {e}")
    
    # Method 2: Try local file - check if it exists first
    local_path = "data/us-states.geojson"
    if os.path.exists(local_path):
        try:
            st.info("Loading local US states geographic data...")
            
            # Load file directly as JSON
            with open(local_path, 'r') as f:
                geojson_data = json.load(f)
            
            st.empty()
            return geojson_data
            
        except Exception as e:
            st.warning(f"Failed to load local file: {e}")
    
    # Method 3: Create a minimal dataset as fallback
    st.warning("Using minimal fallback data for demonstration")
    
    # Minimal GeoJSON structure with simplified state boundaries
    fallback_data = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Add a few example states with very simplified boundaries
    example_states = {
        "California": [[-124, 42], [-124, 32], [-114, 32], [-114, 42], [-124, 42]],
        "Texas": [[-106, 36], [-106, 25], [-93, 25], [-93, 36], [-106, 36]],
        "Florida": [[-87, 31], [-87, 24], [-80, 24], [-80, 31], [-87, 31]]
    }
    
    for state_name, coords in example_states.items():
        feature = {
            "type": "Feature",
            "properties": {"name": state_name},
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        fallback_data["features"].append(feature)
    
    return fallback_data


@st.cache_data
def load_rpa_docs() -> str:
    """
    Load RPA documentation for the overview tab.
    
    Returns:
        str: RPA documentation content
    """
    return """
## Scenarios

The RPA scenarios represent different assumptions about future conditions:

### Socioeconomic Scenarios:
- **SSP1**: Sustainability - Taking the Green Road
- **SSP2**: Middle of the Road  
- **SSP3**: Regional Rivalry - A Rocky Road
- **SSP5**: Fossil-fueled Development

### Climate Scenarios:
- **RCP 4.5**: Moderate climate change scenario
- **RCP 8.5**: High climate change scenario

### Combined Scenarios:
- **LM (Low-Moderate)**: SSP1 + RCP 4.5
- **ML (Moderate-Low)**: SSP2 + RCP 4.5  
- **HM (High-Moderate)**: SSP3 + RCP 4.5
- **HL (High-Low)**: SSP5 + RCP 4.5
- **HH (High-High)**: SSP5 + RCP 8.5

## Data Sources

The data comes from the USDA Forest Service's 2020 Resources Planning Act (RPA) Assessment. The projections use econometric models that consider:
- Population growth
- Economic development
- Climate change impacts
- Historical land use patterns
- Policy scenarios

For more information, visit the [USDA Forest Service RPA website](https://www.fs.usda.gov/research/rpa).
"""


def aggregate_by_region(df: pd.DataFrame, value_col: str, region_type: str = 'state') -> pd.DataFrame:
    """
    Aggregate data by geographic region.
    
    Args:
        df: Input DataFrame
        value_col: Column to aggregate
        region_type: Type of region ('state' or 'county')
        
    Returns:
        pd.DataFrame: Aggregated data
    """
    if region_type == 'state':
        return df.groupby(['state_name', 'scenario_name'])[value_col].sum().reset_index()
    else:
        return df.groupby(['state_name', 'county_name', 'scenario_name'])[value_col].sum().reset_index()


def filter_by_scenario(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """
    Filter DataFrame by scenario name.
    
    Args:
        df: Input DataFrame
        scenario: Scenario name to filter by
        
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    if scenario == "All Scenarios":
        return df
    return df[df['scenario_name'] == scenario]