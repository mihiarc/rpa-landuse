"""
Configuration settings for the RPA Land Use Viewer application.
"""

import os
from pathlib import Path
from typing import Dict, List

# Application settings
APP_TITLE = "2020 Resources Planning Act (RPA) Assessment"
APP_SUBTITLE = "Land-Use Change Viewer"
APP_ICON = "🌳"
APP_LAYOUT = "wide"

# Data paths
DATA_DIR = Path("data")
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATABASE_PATH = DATA_DIR / "database" / "rpa.db"
COUNTIES_GEOJSON_PATH = DATA_DIR / "counties.geojson"

# Dataset configuration
DATASET_FILES = {
    "Average Gross Change Across All Scenarios (2020-2070)": "gross_change_ensemble_all.parquet",
    "Urbanization Trends By Decade": "urbanization_trends.parquet", 
    "Transitions to Urban Land": "to_urban_transitions.parquet",
    "Transitions from Forest Land": "from_forest_transitions.parquet",
    "County-Level Land Use Transitions": "county_transitions.parquet"
}

# Scenario descriptions
SCENARIO_DESCRIPTIONS = {
    'Overall Mean': 'Ensemble Projection (Average of All Scenarios)',
    'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
    'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
    'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
    'ensemble_HH': 'High Development (RCP8.5-SSP5)'
}

# Key RPA scenarios for filtering
KEY_SCENARIOS = [
    'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
    'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
    'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
    'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
    'ensemble_overall' # Overall mean projection
]

# Map configuration
US_STATES_GEOJSON_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
MAP_CENTER = [39.8283, -98.5795]  # Continental US center
MAP_ZOOM_START = 4

# State FIPS to name mapping
STATE_FIPS_TO_NAME = {
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

# Land use color mapping for visualizations
LAND_USE_COLORS = {
    'Forest': '#228B22',      # Forest Green
    'Cropland': '#FFD700',    # Gold
    'Pasture': '#90EE90',     # Light Green
    'Urban': '#FF6347',       # Tomato Red
    'Other': '#D3D3D3',       # Light Gray
    'Range': '#DEB887',       # Burlywood
    'Water': '#4169E1',       # Royal Blue
    'Federal': '#8B4513'      # Saddle Brown
}

# Cache settings
CACHE_TTL_HOURS = 3600  # 1 hour in seconds

# UI Configuration
TAB_NAMES = [
    "Overview", 
    "Data Explorer", 
    "Land Use Flow Diagrams", 
    "Urbanization Trends", 
    "Forest Transitions", 
    "Agricultural Transitions", 
    "State Map"
]

# Spatial analysis levels
SPATIAL_LEVELS = ["County", "State", "Subregion", "Region", "National"]

# Urbanization analysis specific columns that need unit conversion
URBANIZATION_AREA_COLUMNS = ["forest_to_urban", "cropland_to_urban", "pasture_to_urban"]

# Unit conversion factor (hundred acres to acres)
HUNDRED_ACRES_TO_ACRES = 100

# Visualization settings
SANKEY_CHART_HEIGHT = 800
SANKEY_CHART_MARGINS = dict(l=20, r=20, t=80, b=100)
SANKEY_NODE_PAD = 20
SANKEY_NODE_THICKNESS = 25
TEMPORAL_CHART_SIZE = (12, 8)
TEMPORAL_CHART_DPI = 300 