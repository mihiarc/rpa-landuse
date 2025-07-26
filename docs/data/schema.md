# Database Schema

This page documents the structure of the RPA land use analytics database, including all tables, columns, and relationships.

## Database Overview

The DuckDB database (`landuse_analytics.duckdb`) uses a modern star schema design optimized for analytical queries. For comprehensive details, see the [Database Overview](database-overview.md) and [Table Reference](table-reference.md).

### Current Star Schema
The system uses a normalized star schema with:
- `fact_landuse_transitions` - Central fact table with all transitions
- `fact_socioeconomic_projections` - Population and income projections
- `dim_scenario` - Climate and socioeconomic scenarios  
- `dim_geography` - County geography with enhanced metadata
- `dim_landuse` - Land use type definitions
- `dim_time` - Time period dimensions
- `dim_socioeconomic` - SSP scenario descriptions
- `dim_indicators` - Socioeconomic indicator definitions

## Current Database Structure

**Note**: This page contains legacy information. For complete current database documentation, see:
- [Database Overview](database-overview.md) - Executive summary and architecture
- [Table Reference](table-reference.md) - Detailed table specifications  
- [View Definitions](view-definitions.md) - Analytical views and usage
- [Data Dictionary](data-dictionary.md) - Business definitions and guidelines

## Key Concepts

### Climate Scenarios
The database contains 20 climate scenarios combining:
- 5 Climate models (CNRM_CM5, HadGEM2_ES365, IPSL_CM5A_MR, MRI_CGCM3, NorESM1_M)  
- 4 RCP/SSP combinations (rcp45_ssp1, rcp85_ssp2, rcp85_ssp3, rcp85_ssp5)

### Land Use Categories
- **Crop (cr)**: Agricultural cropland
- **Pasture (ps)**: Livestock grazing land  
- **Rangeland (rg)**: Natural grasslands/shrublands
- **Forest (fr)**: Forested areas
- **Urban (ur)**: Developed/built areas

### Time Coverage
6 time periods from 2012-2070:
- 2012-2020 (calibration period)
- 2020-2030, 2030-2040, 2040-2050, 2050-2060, 2060-2070

### Geographic Coverage  
- 3,075 US counties across all 50 states
- Organized by US Census regions (Northeast, Midwest, South, West)

## Basic Query Examples

For detailed query patterns and examples, see [Basic Queries](../queries/basic-queries.md) and [Advanced Queries](../queries/advanced-queries.md).

```sql
-- Get all scenarios
SELECT * FROM dim_scenario;

-- Find counties in California
SELECT * FROM dim_geography WHERE state_name = 'California';

-- Basic land use transition query
SELECT 
    g.county_name,
    s.scenario_name,
    lu_from.landuse_name as from_landuse,
    lu_to.landuse_name as to_landuse,
    f.acres
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse lu_from ON f.from_landuse_id = lu_from.landuse_id
JOIN dim_landuse lu_to ON f.to_landuse_id = lu_to.landuse_id
WHERE f.transition_type = 'change'
LIMIT 10;
```

## Next Steps

- Explore [Land Use Categories](categories.md) in detail
- See [Data Sources](sources.md) for data provenance
- Review [Processing Steps](processing.md) for data pipeline