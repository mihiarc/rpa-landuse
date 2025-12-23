#!/usr/bin/env python3
"""Analytics Dashboard package for RPA Land Use Analysis.

This package provides pre-built visualizations and analytics for land use
transition data from the USDA Forest Service 2020 RPA Assessment.

The module has been refactored from a monolithic file into a modular package
with the following structure:

    views/analytics/
    ├── __init__.py          # Package exports (this file)
    ├── constants.py         # Colors, TTLs, thresholds
    ├── utilities.py         # Shared helper functions
    ├── data_loaders.py      # Database queries and data loading
    ├── dashboard.py         # Main UI orchestration
    └── charts/
        ├── __init__.py      # Chart exports
        ├── flow_charts.py   # Flow/waterfall charts
        ├── map_charts.py    # Choropleth, Sankey diagrams
        └── comparison.py    # Spider/radar charts

Usage:
    from views.analytics import main
    main()

Or import specific components:
    from views.analytics import RPA_COLORS, create_forest_flow_chart
"""

# Main entry points
from .dashboard import main, show_enhanced_visualizations

# Constants - backward compatibility
from .constants import (
    CACHE_TTL_LONG,
    CACHE_TTL_SHORT,
    CHART_HEIGHT_LARGE,
    CHART_HEIGHT_MEDIUM,
    CHART_HEIGHT_SMALL,
    CHART_HEIGHT_XLARGE,
    LANDUSE_TYPES,
    MAX_SANKEY_FLOWS,
    MIN_ACRES_THRESHOLD,
    RPA_BLUE_SCALE,
    RPA_BROWN_SCALE,
    RPA_COLOR_SEQUENCE,
    RPA_COLORS,
    RPA_DIVERGING_SCALE,
    RPA_GREEN_SCALE,
    SCENARIO_DISPLAY_NAMES,
    TOP_STATES_DISPLAY,
)

# Data loaders - backward compatibility
from .data_loaders import (
    get_database_connection,
    load_agricultural_analysis_data,
    load_animated_timeline_data,
    load_climate_comparison_data,
    load_forest_analysis_data,
    load_sankey_data,
    load_scenario_comparison_data,
    load_state_transitions,
    load_urbanization_data,
)

# Chart creators - backward compatibility
from .charts import (
    create_agricultural_flow_chart,
    create_agricultural_state_map,
    create_animated_timeline,
    create_choropleth_map,
    create_flow_chart,
    create_forest_flow_chart,
    create_forest_state_map,
    create_sankey_diagram,
    create_scenario_spider_chart,
    create_state_choropleth,
    create_urbanization_chart,
)

__all__ = [
    # Main entry points
    "main",
    "show_enhanced_visualizations",
    # Constants
    "RPA_COLORS",
    "RPA_COLOR_SEQUENCE",
    "RPA_GREEN_SCALE",
    "RPA_BLUE_SCALE",
    "RPA_BROWN_SCALE",
    "RPA_DIVERGING_SCALE",
    "CACHE_TTL_SHORT",
    "CACHE_TTL_LONG",
    "CHART_HEIGHT_SMALL",
    "CHART_HEIGHT_MEDIUM",
    "CHART_HEIGHT_LARGE",
    "CHART_HEIGHT_XLARGE",
    "MIN_ACRES_THRESHOLD",
    "MAX_SANKEY_FLOWS",
    "TOP_STATES_DISPLAY",
    "LANDUSE_TYPES",
    "SCENARIO_DISPLAY_NAMES",
    # Data loaders
    "get_database_connection",
    "load_agricultural_analysis_data",
    "load_forest_analysis_data",
    "load_urbanization_data",
    "load_climate_comparison_data",
    "load_state_transitions",
    "load_sankey_data",
    "load_animated_timeline_data",
    "load_scenario_comparison_data",
    # Chart creators
    "create_flow_chart",
    "create_forest_flow_chart",
    "create_agricultural_flow_chart",
    "create_animated_timeline",
    "create_state_choropleth",
    "create_forest_state_map",
    "create_agricultural_state_map",
    "create_choropleth_map",
    "create_sankey_diagram",
    "create_urbanization_chart",
    "create_scenario_spider_chart",
]

if __name__ == "__main__":
    main()
