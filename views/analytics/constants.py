"""Constants for the Analytics Dashboard.

RPA Assessment Official Color Palette and configuration values.
"""

# RPA Assessment Official Color Palette
RPA_COLORS = {
    "dark_green": "#496f4a",
    "medium_green": "#85b18b",
    "medium_blue": "#a3cad4",
    "light_brown": "#cec597",
    "pink": "#edaa97",
    "dark_blue": "#61a4b5",
    "lighter_dark_green": "#89b18b",
    "lighter_medium_green": "#b8d0b9",
    "lighter_medium_blue": "#c8dfe5",
    "lighter_light_brown": "#e2dcc1",
}

# RPA color sequences for Plotly charts
RPA_COLOR_SEQUENCE = [
    RPA_COLORS["dark_green"],
    RPA_COLORS["medium_blue"],
    RPA_COLORS["medium_green"],
    RPA_COLORS["light_brown"],
    RPA_COLORS["pink"],
    RPA_COLORS["dark_blue"],
]

# RPA gradient scales for choropleth maps
RPA_GREEN_SCALE = [
    [0, RPA_COLORS["lighter_medium_green"]],
    [0.5, RPA_COLORS["medium_green"]],
    [1, RPA_COLORS["dark_green"]],
]

RPA_BLUE_SCALE = [
    [0, RPA_COLORS["lighter_medium_blue"]],
    [0.5, RPA_COLORS["medium_blue"]],
    [1, RPA_COLORS["dark_blue"]],
]

RPA_BROWN_SCALE = [
    [0, RPA_COLORS["lighter_light_brown"]],
    [0.5, RPA_COLORS["light_brown"]],
    [1, "#9f6b25"],
]

# Diverging scale for gain/loss visualizations
RPA_DIVERGING_SCALE = [
    [0, "#d73027"],      # Red (loss)
    [0.5, "#ffffbf"],    # Yellow (neutral)
    [1, "#1a9850"],      # Green (gain)
]

# Cache TTL values (in seconds)
CACHE_TTL_SHORT = 300   # 5 minutes for frequently changing data
CACHE_TTL_LONG = 3600   # 1 hour for stable data

# Chart dimensions
CHART_HEIGHT_SMALL = 400
CHART_HEIGHT_MEDIUM = 500
CHART_HEIGHT_LARGE = 600
CHART_HEIGHT_XLARGE = 700

# Data thresholds
MIN_ACRES_THRESHOLD = 100000  # Minimum acres for Sankey diagram display
MAX_SANKEY_FLOWS = 15         # Maximum flows in Sankey diagram
TOP_STATES_DISPLAY = 5        # Number of top states to display in rankings

# Land use type mappings
LANDUSE_TYPES = {
    "forest": {"code": "fr", "name": "Forest", "color": RPA_COLORS["dark_green"]},
    "agricultural": {"code": "cr", "name": "Cropland", "color": RPA_COLORS["light_brown"]},
    "pasture": {"code": "ps", "name": "Pasture", "color": RPA_COLORS["medium_green"]},
    "urban": {"code": "ur", "name": "Urban", "color": RPA_COLORS["pink"]},
    "rangeland": {"code": "rg", "name": "Rangeland", "color": RPA_COLORS["medium_blue"]},
}

# Scenario display names
SCENARIO_DISPLAY_NAMES = {
    "RCP45_SSP1": "Low Warming/Slow Growth (LM)",
    "RCP45_SSP2": "Low Warming/Rapid Growth (HM)",
    "RCP85_SSP1": "High Warming/Slow Growth (HL)",
    "RCP85_SSP2": "High Warming/Rapid Growth (HH)",
}
