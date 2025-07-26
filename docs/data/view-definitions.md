# View Definitions

## Overview

The RPA Land Use Analytics database includes 5 pre-built analytical views that simplify common query patterns and provide optimized access to integrated data across multiple tables.

| View | Records | Purpose |
|------|---------|---------|
| `v_scenarios_combined` | 20 | Climate + socioeconomic scenario integration |
| `v_landuse_socioeconomic` | 5.4M | Complete land use transitions with demographics |
| `v_population_trends` | 291,936 | County population projections by scenario |
| `v_income_trends` | 291,936 | County income projections by scenario |
| `v_full_projection_period` | 1.3M | Long-term trends and cumulative changes 2020-2070 |

## Scenario Integration Views

### v_scenarios_combined

**Purpose**: Combines climate scenarios with socioeconomic scenarios to provide complete scenario context in a single view.

**Records**: 20

#### View Definition

```sql
CREATE VIEW v_scenarios_combined AS 
SELECT 
    s.scenario_id, 
    s.scenario_name AS climate_scenario, 
    s.climate_model, 
    s.rcp_scenario, 
    s.ssp_scenario, 
    se.scenario_name AS ssp_name, 
    se.narrative_description, 
    se.population_growth_trend, 
    se.economic_growth_trend, 
    se.urbanization_level 
FROM dim_scenario AS s 
LEFT JOIN dim_socioeconomic AS se ON (s.ssp_scenario = se.ssp_scenario);
```

#### Sample Output

```sql
SELECT * FROM v_scenarios_combined LIMIT 5;
```

| scenario_id | climate_scenario | climate_model | rcp_scenario | ssp_scenario | ssp_name | population_growth_trend | economic_growth_trend | urbanization_level |
|-------------|------------------|---------------|--------------|--------------|----------|------------------------|----------------------|-------------------|
| 1 | CNRM_CM5_rcp45_ssp1 | CNRM_CM5 | rcp45 | ssp1 | Sustainability | Low | Medium | Moderate |
| 2 | CNRM_CM5_rcp85_ssp2 | CNRM_CM5 | rcp85 | ssp2 | Middle of the Road | Medium | Medium | Moderate |
| 3 | CNRM_CM5_rcp85_ssp3 | CNRM_CM5 | rcp85 | ssp3 | Regional Rivalry | High | Low | Slow |
| 4 | CNRM_CM5_rcp85_ssp5 | CNRM_CM5 | rcp85 | ssp5 | Fossil-fueled Development | Low | High | Fast |
| 5 | HadGEM2_ES365_rcp45_ssp1 | HadGEM2_ES365 | rcp45 | ssp1 | Sustainability | Low | Medium | Moderate |

#### Use Cases

- **Scenario Selection**: Choose scenarios based on combined climate/socioeconomic characteristics
- **Narrative Analysis**: Understand the storyline behind each projection scenario
- **Comparative Studies**: Group scenarios by climate model or socioeconomic pathway

#### Example Queries

```sql
-- Find all "hot" climate scenarios with high economic growth
SELECT climate_scenario, ssp_name, economic_growth_trend
FROM v_scenarios_combined
WHERE climate_model = 'HadGEM2_ES365' 
  AND economic_growth_trend = 'High';

-- Group scenarios by urbanization trend
SELECT urbanization_level, 
       COUNT(*) as scenario_count,
       STRING_AGG(climate_scenario, ', ') as scenarios
FROM v_scenarios_combined
GROUP BY urbanization_level;
```

---

## Comprehensive Analysis Views

### v_landuse_socioeconomic

**Purpose**: Comprehensive view combining land use transitions with full demographic and geographic context for integrated analysis.

**Records**: 5,432,198 (all land use transitions)

#### View Definition

```sql
CREATE VIEW v_landuse_socioeconomic AS 
SELECT 
    f.transition_id, 
    g.fips_code, 
    g.county_name, 
    g.state_name, 
    g.region, 
    s.scenario_name AS climate_scenario, 
    s.rcp_scenario, 
    s.ssp_scenario, 
    t.start_year, 
    t.end_year, 
    lu_from.landuse_name AS from_landuse, 
    lu_to.landuse_name AS to_landuse, 
    f.acres, 
    f.transition_type, 
    pop.population_thousands AS population_start, 
    inc.income_per_capita_2009usd AS income_start 
FROM fact_landuse_transitions AS f 
INNER JOIN dim_scenario AS s ON (f.scenario_id = s.scenario_id) 
INNER JOIN dim_time AS t ON (f.time_id = t.time_id) 
INNER JOIN dim_geography AS g ON (f.geography_id = g.geography_id) 
INNER JOIN dim_landuse AS lu_from ON (f.from_landuse_id = lu_from.landuse_id) 
INNER JOIN dim_landuse AS lu_to ON (f.to_landuse_id = lu_to.landuse_id) 
LEFT JOIN v_population_trends AS pop ON ((g.fips_code = pop.fips_code) 
    AND (s.ssp_scenario = pop.ssp_scenario) 
    AND (t.start_year = pop.year)) 
LEFT JOIN v_income_trends AS inc ON ((g.fips_code = inc.fips_code) 
    AND (s.ssp_scenario = inc.ssp_scenario) 
    AND (t.start_year = inc.year));
```

#### Sample Output

```sql
SELECT fips_code, county_name, state_name, climate_scenario, 
       from_landuse, to_landuse, acres, population_start, income_start
FROM v_landuse_socioeconomic 
WHERE transition_type = 'change' 
LIMIT 5;
```

| fips_code | county_name | state_name | climate_scenario | from_landuse | to_landuse | acres | population_start | income_start |
|-----------|-------------|------------|------------------|---------------|-------------|-------|------------------|--------------|
| 06037 | Los Angeles County | California | CNRM_CM5_rcp45_ssp1 | Forest | Urban | 125.32 | 9818.5 | 42.6 |
| 48201 | Harris County | Texas | CNRM_CM5_rcp45_ssp1 | Crop | Urban | 89.45 | 4092.4 | 41.2 |
| 12086 | Miami-Dade County | Florida | CNRM_CM5_rcp45_ssp1 | Pasture | Urban | 156.78 | 2496.4 | 35.8 |

#### Use Cases

- **Integrated Analysis**: Analyze land use changes in context of population and economic trends
- **Policy Impact Studies**: Understand how demographic pressures affect land use transitions
- **Regional Comparisons**: Compare land use patterns across different socioeconomic contexts

#### Example Queries

```sql
-- Counties with highest population growth and urban expansion
SELECT county_name, state_name, 
       SUM(acres) as urban_expansion,
       AVG(population_start) as avg_population
FROM v_landuse_socioeconomic
WHERE to_landuse = 'Urban' 
  AND transition_type = 'change'
  AND start_year = 2020
GROUP BY county_name, state_name
ORDER BY urban_expansion DESC
LIMIT 10;

-- Correlation between income and agricultural land conversion
SELECT 
    CASE WHEN income_start < 30 THEN 'Low Income'
         WHEN income_start < 50 THEN 'Medium Income'
         ELSE 'High Income' END as income_bracket,
    SUM(CASE WHEN from_landuse IN ('Crop', 'Pasture') 
             AND to_landuse = 'Urban' THEN acres ELSE 0 END) as ag_to_urban
FROM v_landuse_socioeconomic
WHERE transition_type = 'change'
GROUP BY income_bracket;
```

---

## Demographic Trend Views

### v_population_trends

**Purpose**: County-level population projections across all SSP scenarios for demographic analysis.

**Records**: 291,936

#### View Definition

```sql
CREATE VIEW v_population_trends AS 
SELECT 
    g.fips_code, 
    g.county_name, 
    g.state_name, 
    g.region, 
    se.ssp_scenario, 
    se.scenario_name, 
    sp.year, 
    sp.value AS population_thousands, 
    sp.is_historical 
FROM fact_socioeconomic_projections AS sp 
INNER JOIN dim_geography AS g ON (sp.geography_id = g.geography_id) 
INNER JOIN dim_socioeconomic AS se ON (sp.socioeconomic_id = se.socioeconomic_id) 
INNER JOIN dim_indicators AS i ON (sp.indicator_id = i.indicator_id) 
WHERE (i.indicator_name = 'Population');
```

#### Sample Output

```sql
SELECT * FROM v_population_trends 
WHERE fips_code = '06037' AND ssp_scenario = 'ssp1'
ORDER BY year;
```

| fips_code | county_name | state_name | region | ssp_scenario | scenario_name | year | population_thousands | is_historical |
|-----------|-------------|------------|--------|--------------|---------------|------|---------------------|---------------|
| 06037 | Los Angeles County | California | West | ssp1 | Sustainability | 2010 | 9818.5 | TRUE |
| 06037 | Los Angeles County | California | West | ssp1 | Sustainability | 2020 | 10014.2 | FALSE |
| 06037 | Los Angeles County | California | West | ssp1 | Sustainability | 2030 | 10156.8 | FALSE |
| 06037 | Los Angeles County | California | West | ssp1 | Sustainability | 2040 | 10234.1 | FALSE |
| 06037 | Los Angeles County | California | West | ssp1 | Sustainability | 2050 | 10267.9 | FALSE |

#### Use Cases

- **Demographic Planning**: Understand population growth patterns by scenario
- **Urban Planning**: Project infrastructure needs based on population trends
- **Regional Analysis**: Compare population trajectories across different regions

#### Example Queries

```sql
-- Fastest growing counties by scenario
SELECT county_name, state_name, ssp_scenario,
       MAX(population_thousands) - MIN(population_thousands) as growth
FROM v_population_trends
WHERE year BETWEEN 2020 AND 2050
GROUP BY county_name, state_name, ssp_scenario
ORDER BY growth DESC
LIMIT 10;

-- Regional population distribution by scenario
SELECT region, ssp_scenario, year,
       SUM(population_thousands) as total_population
FROM v_population_trends
WHERE year IN (2020, 2030, 2040, 2050)
GROUP BY region, ssp_scenario, year
ORDER BY region, ssp_scenario, year;
```

---

### v_income_trends

**Purpose**: County-level income per capita projections across all SSP scenarios for economic analysis.

**Records**: 291,936

#### View Definition

```sql
CREATE VIEW v_income_trends AS 
SELECT 
    g.fips_code, 
    g.county_name, 
    g.state_name, 
    g.region, 
    se.ssp_scenario, 
    se.scenario_name, 
    sp.year, 
    sp.value AS income_per_capita_2009usd, 
    sp.is_historical 
FROM fact_socioeconomic_projections AS sp 
INNER JOIN dim_geography AS g ON (sp.geography_id = g.geography_id) 
INNER JOIN dim_socioeconomic AS se ON (sp.socioeconomic_id = se.socioeconomic_id) 
INNER JOIN dim_indicators AS i ON (sp.indicator_id = i.indicator_id) 
WHERE (i.indicator_name = 'Income Per Capita');
```

#### Sample Output

```sql
SELECT * FROM v_income_trends 
WHERE fips_code = '06037' AND ssp_scenario = 'ssp5'
ORDER BY year;
```

| fips_code | county_name | state_name | region | ssp_scenario | scenario_name | year | income_per_capita_2009usd | is_historical |
|-----------|-------------|------------|--------|--------------|---------------|------|---------------------------|---------------|
| 06037 | Los Angeles County | California | West | ssp5 | Fossil-fueled Development | 2010 | 42.6 | TRUE |
| 06037 | Los Angeles County | California | West | ssp5 | Fossil-fueled Development | 2020 | 48.2 | FALSE |
| 06037 | Los Angeles County | California | West | ssp5 | Fossil-fueled Development | 2030 | 55.8 | FALSE |
| 06037 | Los Angeles County | California | West | ssp5 | Fossil-fueled Development | 2040 | 64.1 | FALSE |
| 06037 | Los Angeles County | California | West | ssp5 | Fossil-fueled Development | 2050 | 73.9 | FALSE |

#### Use Cases

- **Economic Planning**: Understand income growth patterns across scenarios
- **Development Analysis**: Correlate economic growth with land use changes
- **Regional Economics**: Compare economic trajectories across regions

#### Example Queries

```sql
-- Income inequality across scenarios
SELECT ssp_scenario, year,
       MAX(income_per_capita_2009usd) as max_income,
       MIN(income_per_capita_2009usd) as min_income,
       MAX(income_per_capita_2009usd) - MIN(income_per_capita_2009usd) as income_gap
FROM v_income_trends
WHERE year IN (2020, 2030, 2040, 2050)
GROUP BY ssp_scenario, year
ORDER BY ssp_scenario, year;

-- Economic growth rates by region
SELECT region, ssp_scenario,
       (MAX(income_per_capita_2009usd) - MIN(income_per_capita_2009usd)) / 
       MIN(income_per_capita_2009usd) * 100 as growth_rate_pct
FROM v_income_trends
WHERE year BETWEEN 2020 AND 2050
GROUP BY region, ssp_scenario
ORDER BY region, growth_rate_pct DESC;
```

## Performance Considerations

### Query Optimization

All views are optimized for analytical queries with the following characteristics:

- **Indexed Joins**: All joins use indexed columns for optimal performance
- **Minimal Computation**: Complex calculations are performed at query time, not in views
- **Selective Filtering**: Views include the most commonly filtered columns

### Best Practices

1. **Filter Early**: Apply WHERE clauses on geographic or scenario columns first
2. **Use Appropriate Views**: Choose the most specific view for your analysis needs
3. **Aggregate Wisely**: Group by dimensions before calculating complex metrics
4. **Limit Results**: Use LIMIT clauses for exploratory queries

### Example Optimized Query Pattern

```sql
-- Efficient pattern: filter on indexed columns first, then aggregate
SELECT 
    region,
    ssp_scenario,
    AVG(population_thousands) as avg_population,
    SUM(acres) as total_urban_expansion
FROM v_landuse_socioeconomic
WHERE 
    region = 'West'                    -- Geographic filter (indexed)
    AND ssp_scenario = 'ssp1'          -- Scenario filter (indexed)  
    AND to_landuse = 'Urban'           -- Land use filter
    AND transition_type = 'change'     -- Transition filter
    AND start_year >= 2020             -- Time filter
GROUP BY region, ssp_scenario;
```

## Cross-View Analysis

### Combining Multiple Views

Views can be combined for complex analytical queries:

```sql
-- Population growth vs. agricultural land loss
WITH pop_growth AS (
    SELECT fips_code, ssp_scenario,
           MAX(population_thousands) - MIN(population_thousands) as growth
    FROM v_population_trends
    WHERE year BETWEEN 2020 AND 2050
    GROUP BY fips_code, ssp_scenario
),
ag_loss AS (
    SELECT fips_code, ssp_scenario,
           SUM(acres) as agricultural_loss
    FROM v_landuse_socioeconomic
    WHERE from_landuse IN ('Crop', 'Pasture')
      AND to_landuse = 'Urban'
      AND transition_type = 'change'
    GROUP BY fips_code, ssp_scenario
)
SELECT p.fips_code, p.ssp_scenario, p.growth, a.agricultural_loss,
       a.agricultural_loss / p.growth as loss_per_capita
FROM pop_growth p
JOIN ag_loss a ON p.fips_code = a.fips_code AND p.ssp_scenario = a.ssp_scenario
WHERE p.growth > 0
ORDER BY loss_per_capita DESC;
```

## Maintenance and Updates

### View Dependencies

Views are automatically updated when underlying tables change. The dependency chain is:

1. **Base Tables**: fact and dimension tables
2. **Simple Views**: v_population_trends, v_income_trends, v_scenarios_combined  
3. **Complex Views**: v_landuse_socioeconomic (depends on simple views)

### Performance Monitoring

Monitor view performance using DuckDB's query profiling:

```sql
-- Profile a view query
PRAGMA enable_profiling;
SELECT * FROM v_landuse_socioeconomic WHERE region = 'West' LIMIT 1000;
PRAGMA disable_profiling;
```

---

## Long-Term Trend Analysis Views

### v_full_projection_period

**Purpose**: Comprehensive long-term land use trend analysis with cumulative change tracking across the complete projection period (2020-2070).

**Records**: 1,285,387

#### View Definition

```sql
CREATE VIEW v_full_projection_period AS 
WITH projection_periods AS (
    -- Get only projection periods (exclude calibration 2012-2020)
    SELECT 
        f.transition_id,
        f.scenario_id,
        f.time_id, 
        f.geography_id,
        f.from_landuse_id,
        f.to_landuse_id,
        f.acres,
        f.transition_type,
        s.scenario_name,
        s.climate_model,
        s.rcp_scenario,
        s.ssp_scenario,
        t.year_range,
        t.start_year,
        t.end_year,
        g.fips_code,
        g.county_name,
        g.state_name,
        g.region,
        lu.landuse_name,
        lu.landuse_category
    FROM fact_landuse_transitions f
    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_geography g ON f.geography_id = g.geography_id
    JOIN dim_landuse lu ON f.to_landuse_id = lu.landuse_id
    WHERE t.start_year >= 2020  -- Only projection periods
      AND f.transition_type = 'same'  -- Current land use amounts
),
net_changes AS (
    -- Calculate net changes by comparing consecutive periods
    SELECT *,
        acres - LAG(acres) OVER (
            PARTITION BY scenario_id, geography_id, landuse_name 
            ORDER BY start_year
        ) as net_period_change,
        2020 as baseline_year,
        start_year - 2020 as years_from_baseline
    FROM projection_periods
),
cumulative_changes AS (
    -- Calculate cumulative changes from baseline
    SELECT *,
        SUM(COALESCE(net_period_change, 0)) OVER (
            PARTITION BY scenario_id, geography_id, landuse_name 
            ORDER BY start_year 
            ROWS UNBOUNDED PRECEDING
        ) as cumulative_net_change,
        net_period_change / (end_year - start_year) as avg_annual_change_rate
    FROM net_changes
)
SELECT 
    transition_id,
    scenario_id,
    scenario_name,
    climate_model,
    rcp_scenario,
    ssp_scenario,
    geography_id,
    fips_code,
    county_name,
    state_name,
    region,
    landuse_name,
    landuse_category,
    year_range,
    start_year,
    end_year,
    years_from_baseline,
    acres as current_acres,
    COALESCE(net_period_change, 0) as net_period_change,
    cumulative_net_change,
    avg_annual_change_rate,
    CASE 
        WHEN ABS(cumulative_net_change) >= 100 THEN 
            CASE WHEN cumulative_net_change > 0 THEN 'Significant Gain' ELSE 'Significant Loss' END
        WHEN ABS(cumulative_net_change) >= 10 THEN 
            CASE WHEN cumulative_net_change > 0 THEN 'Moderate Gain' ELSE 'Moderate Loss' END
        ELSE 'Stable'
    END as trend_category
FROM cumulative_changes
WHERE ABS(COALESCE(net_period_change, 0)) >= 0.01  -- Filter out negligible changes
ORDER BY scenario_id, geography_id, landuse_name, start_year;
```

#### Key Features

- **Complete Projection Coverage**: 2020-2070 (50 years of projections)
- **Cumulative Tracking**: Running totals from 2020 baseline
- **Trend Classification**: Automatic categorization of change magnitude
- **Performance Optimized**: Filters negligible changes for better query speed
- **Time-Series Ready**: Window functions for period-over-period analysis

#### Sample Output

```sql
SELECT * FROM v_full_projection_period 
WHERE state_name = 'California' AND county_name = 'Los Angeles'
  AND landuse_name = 'Urban' AND scenario_name = 'CNRM_CM5_rcp45_ssp1'
ORDER BY start_year;
```

| county_name | landuse_name | year_range | net_period_change | cumulative_net_change | trend_category |
|-------------|--------------|------------|-------------------|----------------------|----------------|
| Los Angeles | Urban | 2020-2030 | 45.2 | 45.2 | Moderate Gain |
| Los Angeles | Urban | 2030-2040 | 52.8 | 98.0 | Moderate Gain |
| Los Angeles | Urban | 2040-2050 | 48.1 | 146.1 | Significant Gain |
| Los Angeles | Urban | 2050-2060 | 44.3 | 190.4 | Significant Gain |
| Los Angeles | Urban | 2060-2070 | 41.7 | 232.1 | Significant Gain |

#### Use Cases

- **Long-term Planning**: 50-year trend analysis for infrastructure and policy planning
- **Climate Impact Assessment**: Compare outcomes across different climate scenarios
- **Cumulative Impact Analysis**: Track total changes from baseline through 2070
- **Trend Identification**: Identify counties with significant land use changes
- **Time-Series Analysis**: Detailed year-over-year progression analysis

#### Example Queries

```sql
-- Top 10 counties with highest urban expansion by 2070
SELECT county_name, state_name, scenario_name,
       cumulative_net_change as total_urban_growth
FROM v_full_projection_period
WHERE landuse_name = 'Urban' 
  AND end_year = 2070
  AND cumulative_net_change > 0
ORDER BY cumulative_net_change DESC
LIMIT 10;

-- Agricultural land loss by climate scenario
SELECT rcp_scenario, ssp_scenario,
       SUM(CASE WHEN end_year = 2070 THEN cumulative_net_change ELSE 0 END) as total_ag_change
FROM v_full_projection_period
WHERE landuse_category = 'Agriculture'
  AND cumulative_net_change < 0
GROUP BY rcp_scenario, ssp_scenario
ORDER BY total_ag_change;

-- Time series for specific region and land use
SELECT year_range, 
       SUM(net_period_change) as period_change,
       SUM(cumulative_net_change) as total_cumulative_change
FROM v_full_projection_period
WHERE region = 'West' 
  AND landuse_name = 'Forest'
  AND scenario_name = 'CNRM_CM5_rcp45_ssp1'
GROUP BY year_range, start_year
ORDER BY start_year;
```

#### Performance Notes

- **Optimized Filtering**: Pre-filters negligible changes to improve query speed
- **Window Functions**: Efficient cumulative calculations using SQL window functions
- **Index Support**: Benefits from existing indexes on scenario_id, geography_id, time_id
- **Query Time**: ~0.76 seconds for complex aggregation queries over full dataset

---

## Next Steps

- **Advanced Analysis**: See [Advanced Queries](../queries/advanced-queries.md) for complex analytical patterns
- **Table Details**: See [Table Reference](table-reference.md) for underlying table specifications
- **Performance Tuning**: See [DuckDB Optimization](../performance/duckdb-copy-optimization.md) for query optimization techniques