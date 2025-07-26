# Table Reference Guide

## Overview

This document provides detailed specifications for all 8 tables in the RPA Land Use Analytics database, including column definitions, data types, constraints, and usage examples.

## Fact Tables

### fact_landuse_transitions

**Purpose**: Core table containing all land use transitions between categories across scenarios, time periods, and counties.

**Records**: 5,432,198 | **Size**: 5.18 MB | **Type**: Fact Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `transition_id` | BIGINT | | Unique identifier for each transition record |
| `scenario_id` | INTEGER | NOT NULL, FK | Reference to dim_scenario table |
| `time_id` | INTEGER | NOT NULL, FK | Reference to dim_time table |
| `geography_id` | INTEGER | NOT NULL, FK | Reference to dim_geography table |
| `from_landuse_id` | INTEGER | NOT NULL, FK | Reference to dim_landuse (source land use) |
| `to_landuse_id` | INTEGER | NOT NULL, FK | Reference to dim_landuse (destination land use) |
| `acres` | DECIMAL(15,4) | | Area in acres for this transition |
| `transition_type` | VARCHAR | | 'change' or 'same' |
| `created_at` | TIMESTAMP | | Record creation timestamp |

#### Sample Data

```sql
SELECT * FROM fact_landuse_transitions LIMIT 5;
```

| transition_id | scenario_id | time_id | geography_id | from_landuse_id | to_landuse_id | acres | transition_type |
|---------------|-------------|---------|--------------|-----------------|---------------|-------|-----------------|
| 737281 | 3 | 4 | 459 | 4 | 3 | 3.7577 | change |
| 737282 | 3 | 4 | 459 | 4 | 4 | 265.0467 | same |
| 737283 | 3 | 4 | 459 | 4 | 5 | 0.1956 | change |
| 737284 | 3 | 4 | 459 | 5 | 1 | 0.0000 | change |
| 737285 | 3 | 4 | 459 | 5 | 2 | 0.0000 | change |

#### Data Distribution

| Transition Type | Count | Percentage | Avg Acres |
|----------------|-------|------------|-----------|
| change | 3,887,318 | 71.5% | 13.3 |
| same | 1,544,880 | 28.5% | 1,045.6 |

#### Performance Notes

- Primary composite index on `(scenario_id, time_id, geography_id)`
- Secondary indexes on `from_landuse_id`, `to_landuse_id`, `acres`, `transition_type`
- Optimized for analytical queries with dimensional filtering

---

### fact_socioeconomic_projections

**Purpose**: Population and income projections by county and SSP scenario.

**Records**: 291,936 | **Size**: 0.28 MB | **Type**: Fact Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `projection_id` | BIGINT | NOT NULL, PK | Unique identifier for each projection |
| `geography_id` | INTEGER | NOT NULL, FK | Reference to dim_geography table |
| `socioeconomic_id` | INTEGER | NOT NULL, FK | Reference to dim_socioeconomic table |
| `indicator_id` | INTEGER | NOT NULL, FK | Reference to dim_indicators table |
| `year` | INTEGER | NOT NULL | Projection year |
| `value` | DECIMAL(15,4) | NOT NULL | Indicator value (population in thousands, income in 2009 USD thousands) |
| `is_historical` | BOOLEAN | DEFAULT FALSE | Whether this is historical (TRUE) or projected (FALSE) data |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

#### Sample Data

```sql
SELECT * FROM fact_socioeconomic_projections LIMIT 5;
```

| projection_id | geography_id | socioeconomic_id | indicator_id | year | value | is_historical |
|---------------|--------------|------------------|--------------|------|-------|---------------|
| 1 | 1 | 1 | 1 | 2010 | 54.4210 | TRUE |
| 2 | 1 | 1 | 1 | 2020 | 55.3690 | FALSE |
| 3 | 1 | 1 | 1 | 2030 | 56.2520 | FALSE |
| 4 | 1 | 1 | 1 | 2040 | 56.9500 | FALSE |
| 5 | 1 | 1 | 1 | 2050 | 57.4030 | FALSE |

#### Performance Notes

- Composite index on `(geography_id, socioeconomic_id, indicator_id, year)`
- Optimized for time-series analysis and demographic queries

---

## Dimension Tables

### dim_geography

**Purpose**: Geographic reference data for all US counties with enhanced metadata.

**Records**: 3,075 | **Size**: 0.003 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `geography_id` | INTEGER | PK | Unique identifier for each county |
| `fips_code` | VARCHAR | UNIQUE | 5-digit FIPS county code |
| `county_name` | VARCHAR | | County name |
| `state_code` | VARCHAR | | 2-character state code |
| `state_name` | VARCHAR | | Full state name |
| `state_abbrev` | VARCHAR | | 2-character state abbreviation |
| `region` | VARCHAR | | US Census region (Northeast, Midwest, South, West) |
| `geometry` | GEOMETRY | | County boundary geometry (spatial data) |
| `area_sqmi` | DOUBLE | | County area in square miles |
| `centroid_lat` | DOUBLE | | County centroid latitude |
| `centroid_lon` | DOUBLE | | County centroid longitude |
| `created_at` | TIMESTAMP | | Record creation timestamp |
| `updated_at` | TIMESTAMP | | Last update timestamp |

#### Sample Data

```sql
SELECT fips_code, county_name, state_name, region, area_sqmi 
FROM dim_geography LIMIT 5;
```

| fips_code | county_name | state_name | region | area_sqmi |
|-----------|-------------|------------|--------|-----------|
| 01001 | Autauga County | Alabama | South | 594.44 |
| 01003 | Baldwin County | Alabama | South | 1589.78 |
| 01005 | Barbour County | Alabama | South | 884.88 |
| 01007 | Bibb County | Alabama | South | 622.58 |
| 01009 | Blount County | Alabama | South | 644.78 |

#### Regional Distribution

| Region | Counties | Avg Size (sq mi) | Percentage |
|--------|----------|------------------|------------|
| South | 1,389 | 624 | 45.2% |
| Midwest | 1,055 | 711 | 34.3% |
| West | 414 | 2,836 | 13.5% |
| Northeast | 217 | 746 | 7.1% |

#### Performance Notes

- Primary index on `geography_id`
- Secondary indexes on `fips_code` and `state_name` for fast lookups
- Spatial index on `geometry` for geographic queries

---

### dim_scenario

**Purpose**: Climate and socioeconomic scenario definitions combining climate models with RCP/SSP pathways.

**Records**: 20 | **Size**: 0.00002 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `scenario_id` | INTEGER | NOT NULL, PK | Unique identifier for each scenario |
| `scenario_name` | VARCHAR | NOT NULL, UNIQUE | Full scenario name (e.g., "CNRM_CM5_rcp45_ssp1") |
| `climate_model` | VARCHAR | | Climate model used |
| `rcp_scenario` | VARCHAR | | Representative Concentration Pathway |
| `ssp_scenario` | VARCHAR | | Shared Socioeconomic Pathway |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

#### Climate Models

| Model | Description | Characteristics |
|-------|-------------|-----------------|
| CNRM_CM5 | "Wet" climate model | Higher precipitation scenarios |
| HadGEM2_ES365 | "Hot" climate model | Higher temperature scenarios |
| IPSL_CM5A_MR | "Dry" climate model | Lower precipitation scenarios |
| MRI_CGCM3 | "Least warm" climate model | More moderate temperature increases |
| NorESM1_M | "Middle" climate model | Balanced temperature/precipitation |

#### RCP/SSP Combinations

| Combination | Emissions | Growth | Description |
|-------------|-----------|--------|-------------|
| rcp45_ssp1 | Low | Medium | Sustainability pathway |
| rcp85_ssp2 | High | Medium | Middle of the road |
| rcp85_ssp3 | High | Low | Regional rivalry |
| rcp85_ssp5 | High | High | Fossil-fueled development |

#### Sample Data

```sql
SELECT * FROM dim_scenario LIMIT 5;
```

| scenario_id | scenario_name | climate_model | rcp_scenario | ssp_scenario |
|-------------|---------------|---------------|--------------|--------------|
| 1 | CNRM_CM5_rcp45_ssp1 | CNRM_CM5 | rcp45 | ssp1 |
| 2 | CNRM_CM5_rcp85_ssp2 | CNRM_CM5 | rcp85 | ssp2 |
| 3 | CNRM_CM5_rcp85_ssp3 | CNRM_CM5 | rcp85 | ssp3 |
| 4 | CNRM_CM5_rcp85_ssp5 | CNRM_CM5 | rcp85 | ssp5 |
| 5 | HadGEM2_ES365_rcp45_ssp1 | HadGEM2_ES365 | rcp45 | ssp1 |

---

### dim_time

**Purpose**: Time period definitions for land use projection intervals.

**Records**: 6 | **Size**: 0.000006 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `time_id` | INTEGER | NOT NULL, PK | Unique identifier for each time period |
| `year_range` | VARCHAR | NOT NULL, UNIQUE | Year range string (e.g., "2012-2020") |
| `start_year` | INTEGER | | Starting year of the period |
| `end_year` | INTEGER | | Ending year of the period |
| `period_length` | INTEGER | | Duration in years |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

#### Time Periods

| time_id | year_range | start_year | end_year | period_length | Purpose |
|---------|------------|------------|----------|---------------|---------|
| 1 | 2012-2020 | 2012 | 2020 | 8 | Historical calibration |
| 2 | 2020-2030 | 2020 | 2030 | 10 | Near-term projections |
| 3 | 2030-2040 | 2030 | 2040 | 10 | Medium-term projections |
| 4 | 2040-2050 | 2040 | 2050 | 10 | Mid-century projections |
| 5 | 2050-2060 | 2050 | 2060 | 10 | Extended projections |
| 6 | 2060-2070 | 2060 | 2070 | 10 | Long-term projections |

---

### dim_landuse

**Purpose**: Land use category definitions with business descriptions.

**Records**: 5 | **Size**: 0.000005 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `landuse_id` | INTEGER | NOT NULL, PK | Unique identifier for each land use type |
| `landuse_code` | VARCHAR | UNIQUE | Short code (cr, ps, rg, fr, ur) |
| `landuse_name` | VARCHAR | | Full descriptive name |
| `landuse_category` | VARCHAR | | High-level category (Agriculture, Natural, Developed) |
| `description` | VARCHAR | | Detailed description of land use type |
| `created_at` | TIMESTAMP | | Record creation timestamp |

#### Land Use Types

| landuse_id | landuse_code | landuse_name | landuse_category | Description |
|------------|--------------|--------------|------------------|-------------|
| 1 | cr | Crop | Agriculture | Agricultural cropland for food production |
| 2 | ps | Pasture | Agriculture | Grazing land for livestock |
| 3 | rg | Rangeland | Natural | Natural grasslands and shrublands |
| 4 | fr | Forest | Natural | Forested areas including managed timber |
| 5 | ur | Urban | Developed | Developed areas with infrastructure |

---

### dim_socioeconomic

**Purpose**: Shared Socioeconomic Pathway (SSP) scenario definitions with narrative descriptions.

**Records**: 5 | **Size**: 0.000005 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `socioeconomic_id` | INTEGER | NOT NULL, PK | Unique identifier for each SSP scenario |
| `ssp_scenario` | VARCHAR | NOT NULL, UNIQUE | SSP identifier (ssp1, ssp2, etc.) |
| `scenario_name` | VARCHAR | NOT NULL | Descriptive scenario name |
| `narrative_description` | VARCHAR | | Detailed scenario narrative |
| `population_growth_trend` | VARCHAR | | Population growth characterization |
| `economic_growth_trend` | VARCHAR | | Economic growth characterization |
| `urbanization_level` | VARCHAR | | Urbanization trend description |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

#### SSP Scenarios

| ssp_scenario | scenario_name | Population Growth | Economic Growth | Urbanization |
|--------------|---------------|-------------------|-----------------|--------------|
| ssp1 | Sustainability | Low | Medium | Moderate |
| ssp2 | Middle of the Road | Medium | Medium | Moderate |
| ssp3 | Regional Rivalry | High | Low | Slow |
| ssp4 | Inequality | Medium | High | Fast |
| ssp5 | Fossil-fueled Development | Low | High | Fast |

---

### dim_indicators

**Purpose**: Socioeconomic indicator definitions for measurement units and descriptions.

**Records**: 2 | **Size**: 0.000002 MB | **Type**: Dimension Table

#### Schema Definition

| Column | Data Type | Constraints | Description |
|--------|-----------|-------------|-------------|
| `indicator_id` | INTEGER | NOT NULL, PK | Unique identifier for each indicator |
| `indicator_name` | VARCHAR | NOT NULL, UNIQUE | Indicator name |
| `indicator_type` | VARCHAR | NOT NULL | Type category (demographic, economic) |
| `unit_of_measure` | VARCHAR | NOT NULL | Measurement units |
| `description` | VARCHAR | | Detailed indicator description |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

#### Available Indicators

| indicator_id | indicator_name | indicator_type | unit_of_measure | Description |
|--------------|----------------|----------------|-----------------|-------------|
| 1 | Population | Demographic | Thousands | County population in thousands |
| 2 | Income Per Capita | Economic | 2009 USD Thousands | Per capita income in thousands of 2009 USD |

## Common Query Patterns

### Basic Table Queries

```sql
-- Get all scenarios with their climate models
SELECT scenario_name, climate_model, rcp_scenario, ssp_scenario 
FROM dim_scenario;

-- Find counties in a specific state
SELECT fips_code, county_name, area_sqmi 
FROM dim_geography 
WHERE state_name = 'California';

-- Get all time periods
SELECT year_range, start_year, end_year, period_length 
FROM dim_time 
ORDER BY start_year;
```

### Join Patterns

```sql
-- Land use transitions with readable names
SELECT 
    g.county_name,
    g.state_name,
    s.scenario_name,
    t.year_range,
    lu_from.landuse_name as from_landuse,
    lu_to.landuse_name as to_landuse,
    f.acres
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse lu_from ON f.from_landuse_id = lu_from.landuse_id
JOIN dim_landuse lu_to ON f.to_landuse_id = lu_to.landuse_id
WHERE f.transition_type = 'change'
LIMIT 10;
```

### Aggregation Patterns

```sql
-- Total acres by land use category and region
SELECT 
    g.region,
    lu.landuse_category,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse lu ON f.to_landuse_id = lu.landuse_id
WHERE f.transition_type = 'same'  -- Only current land use
GROUP BY g.region, lu.landuse_category
ORDER BY g.region, total_acres DESC;
```

## Data Relationships

### Foreign Key Constraints

- `fact_landuse_transitions.scenario_id` → `dim_scenario.scenario_id`
- `fact_landuse_transitions.time_id` → `dim_time.time_id`
- `fact_landuse_transitions.geography_id` → `dim_geography.geography_id`
- `fact_landuse_transitions.from_landuse_id` → `dim_landuse.landuse_id`
- `fact_landuse_transitions.to_landuse_id` → `dim_landuse.landuse_id`
- `fact_socioeconomic_projections.geography_id` → `dim_geography.geography_id`
- `fact_socioeconomic_projections.socioeconomic_id` → `dim_socioeconomic.socioeconomic_id`
- `fact_socioeconomic_projections.indicator_id` → `dim_indicators.indicator_id`

### Data Integrity

All foreign key relationships are enforced at the application level and validated during data loading. The star schema design ensures referential integrity and optimal query performance.

## Usage Guidelines

1. **Always filter dimension tables first** to reduce the size of fact table joins
2. **Use appropriate indexes** by including indexed columns in WHERE clauses
3. **Exclude validation rows** with `WHERE transition_type != 'Total'` when applicable
4. **Consider using views** for complex, frequently-used join patterns
5. **Aggregate before filtering** when possible for better performance

## Next Steps

- **View Documentation**: See [View Definitions](view-definitions.md) for pre-built analytical views
- **Query Examples**: See [Advanced Queries](../queries/advanced-queries.md) for complex analysis patterns
- **Performance Guide**: See [DuckDB Optimization](../performance/duckdb-copy-optimization.md) for performance tuning