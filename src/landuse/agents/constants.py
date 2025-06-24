#!/usr/bin/env python3
"""
Shared constants for landuse agents
Contains common schema information, mappings, and query examples
"""

# State code to name mapping
STATE_NAMES = {
    '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
    '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
    '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho',
    '17': 'Illinois', '18': 'Indiana', '19': 'Iowa', '20': 'Kansas',
    '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine', '24': 'Maryland',
    '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota', '28': 'Mississippi',
    '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
    '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
    '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma',
    '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina',
    '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas', '49': 'Utah',
    '50': 'Vermont', '51': 'Virginia', '53': 'Washington', '54': 'West Virginia',
    '55': 'Wisconsin', '56': 'Wyoming'
}

# Database schema template
SCHEMA_INFO_TEMPLATE = """
# Landuse Transitions Database Schema

## Overview
This database contains land use transition data across different climate scenarios, time periods, and geographic locations using a star schema design.

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
- **dim_scenario**: Climate and socioeconomic scenarios
  - scenario_id (INTEGER): Primary key
  - scenario_name (VARCHAR): Full scenario name (e.g., "CNRM_CM5_rcp45_ssp1")
  - climate_model (VARCHAR): Climate model (e.g., "CNRM_CM5")
  - rcp_scenario (VARCHAR): RCP pathway (e.g., "rcp45", "rcp85") - NOTE: values are "rcp45", "rcp85"
  - ssp_scenario (VARCHAR): SSP pathway (e.g., "ssp1", "ssp5") - NOTE: values are "ssp1", "ssp2", "ssp3", "ssp5"

- **dim_time**: Time periods
  - time_id (INTEGER): Primary key
  - year_range (VARCHAR): Range like "2012-2020"
  - start_year (INTEGER): Starting year
  - end_year (INTEGER): Ending year
  - period_length (INTEGER): Duration in years

- **dim_geography**: Geographic locations
  - geography_id (INTEGER): Primary key
  - fips_code (VARCHAR): 5-digit FIPS county code
  - state_code (VARCHAR): 2-digit state code
  - state_name (VARCHAR): Full state name (if available)

- **dim_landuse**: Land use types
  - landuse_id (INTEGER): Primary key
  - landuse_code (VARCHAR): Short code (cr, ps, rg, fr, ur)
  - landuse_name (VARCHAR): Full name (Crop, Pasture, Rangeland, Forest, Urban)
  - landuse_category (VARCHAR): Category (Agriculture, Natural, Developed)
"""

# Default assumptions for queries
DEFAULT_ASSUMPTIONS = {
    "scenarios": "Averaged across all 20 climate scenarios (mean outcome)",
    "time_period": "Full range 2012-2100 (all available years)",
    "geographic_scope": "All US counties",
    "transition_type": "Only 'change' transitions (excluding same-to-same)"
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
"""
}

# Interactive chat examples  
CHAT_EXAMPLES = [
    "How much agricultural land is being lost?",
    "Which states have the most urban expansion?",
    "Compare forest loss between RCP45 and RCP85 scenarios",
    "Show me crop to pasture transitions by state",
    "What's the rate of forest loss?",
    "Show me agricultural changes in California"
]

# Response formatting sections
RESPONSE_SECTIONS = {
    "assumptions": "📊 **Analysis Assumptions:**",
    "findings": "🔍 **Key Findings:**",
    "interpretation": "💡 **Interpretation:**",
    "followup": "📈 **Suggested Follow-up Analyses:**"
}

# Database configuration defaults
DB_CONFIG = {
    "default_path": "data/processed/landuse_analytics.duckdb",
    "max_query_limit": 1000,
    "default_display_limit": 50,
    "read_only": True
}

# Model configuration defaults
MODEL_CONFIG = {
    "default_temperature": 0.1,
    "default_max_tokens": 4000,
    "max_iterations": 3,
    "default_openai_model": "gpt-4o-mini",
    "default_anthropic_model": "claude-3-5-sonnet-20241022"
}
