#!/usr/bin/env python3
"""
Shared constants for landuse agents
Contains common schema information, mappings, and query examples
"""

import os

# Import state mappings from centralized module
from landuse.utils.state_mappings import STATE_NAMES

# Database schema template
SCHEMA_INFO_TEMPLATE = """
# RPA Land Use Transitions Database Schema

## Overview
This database contains USDA Forest Service 2020 RPA Assessment land use projections across 20 integrated climate-socioeconomic scenarios through 2070.

## RPA Scenarios Quick Reference
- **LM (RCP4.5-SSP1)**: Lower warming, moderate growth, sustainability focus
- **HL (RCP8.5-SSP3)**: High warming, low growth, regional rivalry
- **HM (RCP8.5-SSP2)**: High warming, moderate growth, middle of the road
- **HH (RCP8.5-SSP5)**: High warming, high growth, fossil-fueled development

## Tables and Relationships

### Fact Table
- **fact_landuse_transitions**: Main table with transition data
  - transition_id (BIGINT): Unique identifier
  - scenario_id (INTEGER): Links to dim_scenario
  - time_id (INTEGER): Links to dim_time
  - geography_id (INTEGER): Links to dim_geography
  - from_landuse_id (INTEGER): Source land use type
  - to_landuse_id (INTEGER): Destination land use type
  - acres (DECIMAL): Area in acres for this transition
  - transition_type (VARCHAR): 'same' or 'change'

### Dimension Tables
- **dim_scenario**: 20 RPA climate-socioeconomic scenarios
  - scenario_id (INTEGER): Primary key
  - scenario_name (VARCHAR): Full scenario name (e.g., "CNRM_CM5_rcp45_ssp1")
  - climate_model (VARCHAR): 5 models - CNRM_CM5 (wet), HadGEM2_ES365 (hot), IPSL_CM5A_MR (dry), MRI_CGCM3 (least warm), NorESM1_M (middle)
  - rcp_scenario (VARCHAR): "rcp45" (lower warming ~2.5°C) or "rcp85" (high warming ~4.5°C)
  - ssp_scenario (VARCHAR): "ssp1" (sustainability), "ssp2" (middle), "ssp3" (rivalry), "ssp5" (fossil-fueled)

- **dim_time**: Time periods
  - time_id (INTEGER): Primary key
  - year_range (VARCHAR): Range like "2012-2020"
  - start_year (INTEGER): Starting year
  - end_year (INTEGER): Ending year
  - period_length (INTEGER): Duration in years

- **dim_geography**: Geographic locations
  - geography_id (INTEGER): Primary key
  - fips_code (VARCHAR): 5-digit FIPS county code
  - state_code (VARCHAR): 2-digit FIPS state code (e.g., '06' for California, NOT 'CA')
  - state_name (VARCHAR): Full state name (e.g., 'California')
  - state_abbrev (VARCHAR): Also FIPS code (same as state_code)

- **dim_landuse**: Land use types
  - landuse_id (INTEGER): Primary key
  - landuse_code (VARCHAR): Short code (cr, ps, rg, fr, ur)
  - landuse_name (VARCHAR): Full name (Crop, Pasture, Rangeland, Forest, Urban)
  - landuse_category (VARCHAR): Category (Agriculture, Natural, Developed)
"""

# Default assumptions for queries
DEFAULT_ASSUMPTIONS = {
    "scenarios": "Averaged across all 20 RPA scenarios (5 climate models × 4 scenario combinations)",
    "time_period": "Full projection period 2012-2070 (RPA Assessment timeframe)",
    "geographic_scope": "All 3,075 U.S. counties in the conterminous United States",
    "transition_type": "Only 'change' transitions (excluding same-to-same land use)",
    "rpa_context": "Based on USDA Forest Service 2020 Resources Planning Act Assessment",
    "methodology": "Econometric model calibrated on 2001-2012 observed transitions, private land only",
}

# Common query examples
QUERY_EXAMPLES = {
    "agricultural_loss": """
-- Agricultural land loss (averaged across scenarios, full time period)
SELECT
    AVG(f.acres) as avg_acres_lost_per_scenario,
    COUNT(DISTINCT s.scenario_id) as scenarios_included
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE fl.landuse_category = 'Agriculture'
  AND tl.landuse_category != 'Agriculture'
  AND f.transition_type = 'change'
LIMIT 100;
""",
    "urbanization": """
-- Urbanization patterns (averaged across scenarios)
SELECT
    g.state_code,
    fl.landuse_name as from_landuse,
    AVG(f.acres) as avg_acres_urbanized
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE tl.landuse_name = 'Urban'
  AND f.transition_type = 'change'
GROUP BY g.state_code, fl.landuse_name
ORDER BY avg_acres_urbanized DESC
LIMIT 20;
""",
    "climate_comparison": """
-- Compare RCP scenarios
SELECT
    s.rcp_scenario,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY s.rcp_scenario, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC;
""",
    "time_series": """
-- Time series of land use changes
SELECT
    t.start_year,
    t.end_year,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY t.start_year, t.end_year, fl.landuse_name, tl.landuse_name
ORDER BY t.start_year, total_acres DESC;
""",
}

# Interactive chat examples
CHAT_EXAMPLES = [
    "How much agricultural land is projected to be lost by 2070?",
    "Which states have the most urban expansion under high growth scenarios?",
    "Compare forest loss between RCP4.5 and RCP8.5 climate pathways",
    "Show me land use changes under the sustainability scenario (SSP1)",
    "What's the difference between the 'hot' and 'dry' climate models?",
    "How does land use change differ between high growth (SSP5) and low growth (SSP3)?",
]

# Response formatting sections
RESPONSE_SECTIONS = {
    "assumptions": "📊 **Analysis Assumptions:**",
    "findings": "🔍 **Key Findings:**",
    "interpretation": "💡 **Interpretation:**",
    "followup": "📈 **Suggested Follow-up Analyses:**",
}

# Database configuration defaults
DB_CONFIG = {
    "default_path": "data/processed/landuse_analytics.duckdb",
    "max_query_limit": int(os.getenv("LANDUSE_MAX_QUERY_ROWS", "1000")),
    "default_display_limit": int(os.getenv("LANDUSE_DEFAULT_DISPLAY_LIMIT", "50")),
    "read_only": True,
}

# Model configuration defaults
MODEL_CONFIG = {
    "default_temperature": 0.1,
    "default_max_tokens": 4000,
    "max_iterations": int(os.getenv("LANDUSE_MAX_ITERATIONS", "5")),  # Increased from 3 to 5
    "max_execution_time": int(os.getenv("LANDUSE_MAX_EXECUTION_TIME", "120")),  # 2 minutes default
    "default_openai_model": "gpt-4o-mini",
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "max_calls": int(os.getenv("LANDUSE_RATE_LIMIT_CALLS", "60")),
    "time_window": int(os.getenv("LANDUSE_RATE_LIMIT_WINDOW", "60")),  # seconds
}

# RPA Scenario definitions
RPA_SCENARIOS = {
    "LM": {
        "name": "Lower-Moderate",
        "rcp": "rcp45",
        "ssp": "ssp1",
        "description": "Lower warming (~2.5°C), moderate U.S. growth, sustainable development",
        "theme": "Taking the Green Road",
    },
    "HL": {
        "name": "High-Low",
        "rcp": "rcp85",
        "ssp": "ssp3",
        "description": "High warming (~4.5°C), low U.S. growth, regional rivalry",
        "theme": "A Rocky Road",
    },
    "HM": {
        "name": "High-Moderate",
        "rcp": "rcp85",
        "ssp": "ssp2",
        "description": "High warming (~4.5°C), moderate U.S. growth, middle of the road",
        "theme": "Middle of the Road",
    },
    "HH": {
        "name": "High-High",
        "rcp": "rcp85",
        "ssp": "ssp5",
        "description": "High warming (~4.5°C), high U.S. growth, fossil-fueled development",
        "theme": "Taking the Highway",
    },
}

# Climate model characteristics
CLIMATE_MODELS = {
    "CNRM_CM5": {"type": "Wet", "description": "Increased precipitation scenario"},
    "HadGEM2_ES365": {"type": "Hot", "description": "Upper bound of warming"},
    "IPSL_CM5A_MR": {"type": "Dry", "description": "Reduced precipitation scenario"},
    "MRI_CGCM3": {"type": "Least warm", "description": "Lower bound of warming"},
    "NorESM1_M": {"type": "Middle", "description": "Central tendency projection"},
}
