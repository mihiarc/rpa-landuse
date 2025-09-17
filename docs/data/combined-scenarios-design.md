# Combined Scenarios Database Design

## Overview

This document describes the redesigned database schema that aggregates multiple GCM (Global Climate Model) projections into combined RCP-SSP scenarios, aligned with the 2020 RPA Assessment methodology.

## Key Changes from Original Design

### Before: 20 Individual GCM Scenarios
- 5 GCMs × 4 RCP-SSP combinations = 20 scenarios
- Each GCM (CNRM, HadGEM2, IPSL, MRI, NorESM1) had separate records
- Users needed to manually aggregate or choose specific GCMs

### After: 5 Combined Scenarios
1. **OVERALL** (Default) - Mean across all GCMs and all RCP-SSP combinations
2. **RCP45_SSP1** - Sustainability pathway (low emissions, sustainable development)
3. **RCP85_SSP2** - Middle of the Road (high emissions, moderate development)
4. **RCP85_SSP3** - Regional Rivalry (high emissions, slow development)
5. **RCP85_SSP5** - Fossil-fueled Development (high emissions, rapid development)

## Database Structure

### dim_scenario Table
```sql
CREATE TABLE dim_scenario (
    scenario_id INTEGER PRIMARY KEY,
    scenario_name VARCHAR(100),      -- 'OVERALL', 'RCP45_SSP1', etc.
    rcp_scenario VARCHAR(20),        -- 'Combined', 'RCP4.5', 'RCP8.5'
    ssp_scenario VARCHAR(20),        -- 'Combined', 'SSP1', 'SSP2', etc.
    description TEXT,                -- Human-readable description
    narrative TEXT,                  -- Scenario narrative
    aggregation_method VARCHAR(50),  -- 'mean' for all scenarios
    gcm_count INTEGER,              -- Number of GCMs aggregated
    created_at TIMESTAMP
)
```

### fact_landuse_transitions Table
```sql
CREATE TABLE fact_landuse_transitions (
    transition_id BIGINT PRIMARY KEY,
    scenario_id INTEGER,
    time_id INTEGER,
    geography_id INTEGER,
    from_landuse_id INTEGER,
    to_landuse_id INTEGER,
    acres DECIMAL(15,4),           -- Mean acres across aggregated models
    acres_std_dev DECIMAL(15,4),   -- Standard deviation (for transparency)
    acres_min DECIMAL(15,4),        -- Minimum value across models
    acres_max DECIMAL(15,4),        -- Maximum value across models
    transition_type VARCHAR(20),
    created_at TIMESTAMP,
    -- Foreign keys...
)
```

## Default Behavior

### OVERALL Scenario as Default

The **OVERALL** scenario is the default for most queries and analyses. It represents:
- Mean across all 20 original GCM-RCP-SSP combinations
- Provides baseline "most likely" projections
- Reduces uncertainty from individual model biases
- Simplifies initial data exploration

### When to Use Specific Scenarios

Use individual RCP-SSP scenarios when:
- Comparing different climate/socioeconomic pathways
- Analyzing uncertainty ranges
- Conducting sensitivity analysis
- Creating scenario-based policy recommendations

## Key Views

### v_default_transitions
```sql
-- Uses OVERALL scenario by default
CREATE VIEW v_default_transitions AS
SELECT
    year_range, start_year, end_year,
    fips_code, county_name, state_name, region,
    from_landuse, to_landuse,
    acres, transition_type
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
WHERE s.scenario_name = 'OVERALL'
```

### v_scenario_comparisons
```sql
-- For comparing across scenarios
CREATE VIEW v_scenario_comparisons AS
SELECT
    s.scenario_name,
    s.rcp_scenario,
    s.ssp_scenario,
    -- aggregated metrics...
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
WHERE s.scenario_name != 'OVERALL'  -- Exclude overall for comparisons
```

## Query Examples

### Default Query (Using OVERALL)
```sql
-- Simple query automatically uses ensemble mean
SELECT state_name, SUM(acres) as urban_expansion
FROM v_default_transitions
WHERE to_landuse = 'Urban'
  AND transition_type = 'change'
  AND start_year >= 2020
GROUP BY state_name
ORDER BY urban_expansion DESC;
```

### Scenario Comparison Query
```sql
-- Compare outcomes across RCP-SSP scenarios
SELECT
    s.scenario_name,
    s.rcp_scenario,
    s.ssp_scenario,
    SUM(f.acres) as total_forest_loss
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
WHERE f.from_landuse_id = (SELECT landuse_id FROM dim_landuse WHERE landuse_name = 'Forest')
  AND f.transition_type = 'change'
  AND s.scenario_name != 'OVERALL'  -- Compare individual scenarios
GROUP BY s.scenario_name, s.rcp_scenario, s.ssp_scenario
ORDER BY total_forest_loss DESC;
```

### Uncertainty Analysis Query
```sql
-- Show uncertainty range using statistics
SELECT
    county_name,
    state_name,
    AVG(acres) as mean_urban_growth,
    AVG(acres_std_dev) as uncertainty,
    AVG(acres_min) as best_case,
    AVG(acres_max) as worst_case
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
WHERE s.scenario_name = 'OVERALL'
  AND to_landuse_id = (SELECT landuse_id FROM dim_landuse WHERE landuse_name = 'Urban')
GROUP BY county_name, state_name
HAVING mean_urban_growth > 100
ORDER BY uncertainty DESC;
```

## Benefits of This Design

1. **Simplicity**: Default OVERALL scenario for most use cases
2. **Scientific Rigor**: Ensemble averaging reduces model bias
3. **Flexibility**: Individual scenarios available for detailed analysis
4. **Transparency**: Statistics preserved (std_dev, min, max)
5. **Performance**: 5× fewer scenario records to process
6. **Alignment**: Matches 2020 RPA Assessment methodology

## Migration from Original Database

To convert existing queries:

### Original Query Pattern
```sql
-- Old: Needed to handle multiple GCMs
SELECT scenario_name, AVG(acres) as mean_acres
FROM transitions
WHERE scenario_name LIKE '%rcp45_ssp1%'
GROUP BY extract_rcp_ssp(scenario_name)
```

### New Query Pattern
```sql
-- New: Direct scenario access
SELECT acres
FROM v_default_transitions  -- Uses OVERALL by default
-- OR
SELECT acres
FROM transitions
WHERE scenario_name = 'RCP45_SSP1'  -- Specific scenario
```

## RPA Assessment Alignment

The combined scenarios align with the 2020 RPA Assessment's approach:

| Database Scenario | RPA Description | Climate | Socioeconomic |
|------------------|-----------------|----------|---------------|
| OVERALL | Ensemble Mean | All | All |
| RCP45_SSP1 | Sustainability | Lower warming | Sustainable development |
| RCP85_SSP2 | Middle Road | Higher warming | Moderate challenges |
| RCP85_SSP3 | Regional Rivalry | Higher warming | High challenges |
| RCP85_SSP5 | Fossil Development | Higher warming | Rapid fossil-based growth |

## Usage Guidelines

### For General Analysis
- Start with `v_default_transitions` or OVERALL scenario
- Provides robust, averaged projections
- Reduces noise from individual model variations

### For Scenario Planning
- Use individual RCP-SSP scenarios
- Compare across different pathways
- Analyze sensitivity to assumptions

### For Uncertainty Quantification
- Use statistics fields (std_dev, min, max)
- Understand projection confidence intervals
- Identify high-uncertainty regions/transitions

## Implementation

Run the combined scenario converter:
```bash
uv run python scripts/converters/convert_to_duckdb_combined.py \
  --input data/raw/county_landuse_projections_RPA.json \
  --output data/processed/landuse_analytics_combined.duckdb
```

This creates a database with:
- 5 scenarios (1 OVERALL + 4 RCP-SSP)
- Aggregated transitions (mean across GCMs)
- Preserved statistics for uncertainty analysis
- Optimized views for common queries