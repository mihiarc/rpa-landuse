"""
Configuration constants for the RPA Land Use Viewer application.
"""

# Page configuration
PAGE_CONFIG = {
    "page_title": "RPA Land Use Viewer",
    "page_icon": "🌳",
    "layout": "wide"
}

# Application metadata
APP_TITLE = "2020 Resources Planning Act (RPA) Assessment"
APP_SUBTITLE = "Land-Use Change Viewer"
APP_DESCRIPTION = """
This application visualizes land use transition projections from the USDA Forest Service's Resources Planning Act (RPA) Assessment.
Explore how land use is expected to change across the United States from 2020 to 2070 under different climate and socioeconomic scenarios.
"""

# Data file mappings
DATA_FILES = {
    "Average Gross Change Across All Scenarios (2020-2070)": "gross_change_ensemble_all.parquet",
    "Urbanization Trends By Decade": "urbanization_trends.parquet", 
    "Transitions to Urban Land": "to_urban_transitions.parquet",
    "Transitions from Forest Land": "from_forest_transitions.parquet",
    "County-Level Land Use Transitions": "county_transitions.parquet"
}

# Scenario names
SCENARIOS = ["LM", "ML", "HM", "HL", "HH"]
SCENARIO_NAMES = ["All Scenarios", "LM", "ML", "HM", "HL", "HH"]

# Land use categories
LAND_USE_CATEGORIES = {
    "Forest": "fr",
    "Urban": "ur", 
    "Cropland": "cr",
    "Pasture": "pa",
    "Range": "ra",
    "Other": "ot"
}

# Color schemes for visualizations
COLOR_SCHEMES = {
    "forest": "#228B22",
    "urban": "#DC143C",
    "cropland": "#FFD700",
    "pasture": "#32CD32",
    "range": "#DEB887",
    "other": "#708090"
}

# Map configuration
MAP_CONFIG = {
    "center_lat": 39.50,
    "center_lon": -98.35,
    "zoom_start": 4,
    "tiles": "OpenStreetMap"
}

# Tab names
TAB_NAMES = [
    "Overview",
    "Data Explorer", 
    "Land Use Flow Diagrams",
    "Urbanization Trends",
    "Forest Transitions",
    "Agricultural Transitions",
    "State Map",
    "Natural Language Query"
]

# Natural Language Query examples
NLQ_EXAMPLES = [
    "What are the top 10 counties with the highest forest loss?",
    "Show me urban growth trends by state",
    "Which regions will see the most agricultural land conversion?",
    "Compare land use changes across different climate scenarios",
    "What is the total projected urban expansion by 2070?",
    "Show counties with the highest cropland to urban transitions",
    "Which states will lose the most pasture land?",
    "Create a chart showing forest loss trends over time"
]

# Database paths
DB_PATH = "data/database/rpa.db"
PROCESSED_DATA_DIR = "data/processed"

# Cache TTL settings (in seconds)
CACHE_TTL = {
    "geographic_data": 3600,  # 1 hour
    "query_results": 300,     # 5 minutes
    "static_data": None       # No expiration
}