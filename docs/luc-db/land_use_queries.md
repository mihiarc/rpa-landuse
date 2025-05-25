# Land Use Analysis Query Examples

This document contains example SQL queries for analyzing land use transitions in the RPA Land Use database using DuckDB.

## Basic Transition Analysis

### Total Acreage by Land Use Type (Initial)

```sql
SELECT 
    t.from_land_use,
    l.category_name,
    SUM(t.area_hundreds_acres * 100) as total_acres
FROM 
    land_use_transitions t
JOIN
    land_use_categories l ON t.from_land_use = l.category_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
GROUP BY 
    t.from_land_use, l.category_name
ORDER BY 
    total_acres DESC;
```

### Total Acreage by Land Use Type (Final)

```sql
SELECT 
    t.to_land_use,
    l.category_name,
    SUM(t.area_hundreds_acres * 100) as total_acres
FROM 
    land_use_transitions t
JOIN
    land_use_categories l ON t.to_land_use = l.category_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
GROUP BY 
    t.to_land_use, l.category_name
ORDER BY 
    total_acres DESC;
```

### Net Change by Land Use Type

```sql
WITH initial_acres AS (
    SELECT 
        from_land_use as land_use,
        SUM(area_hundreds_acres * 100) as acres
    FROM 
        land_use_transitions
    WHERE 
        scenario_id = 1 
        AND time_step_id = 2
    GROUP BY 
        from_land_use
),
final_acres AS (
    SELECT 
        to_land_use as land_use,
        SUM(area_hundreds_acres * 100) as acres
    FROM 
        land_use_transitions
    WHERE 
        scenario_id = 1 
        AND time_step_id = 2
    GROUP BY 
        to_land_use
)
SELECT 
    l.category_code,
    l.category_name,
    COALESCE(fa.acres, 0) - COALESCE(ia.acres, 0) as net_change_acres
FROM 
    land_use_categories l
LEFT JOIN
    initial_acres ia ON l.category_code = ia.land_use
LEFT JOIN
    final_acres fa ON l.category_code = fa.land_use
WHERE 
    l.category_code NOT IN ('t1', 't2')
ORDER BY 
    net_change_acres DESC;
```

## Regional Analysis

### Transitions by Region

```sql
SELECT 
    c.region,
    t.from_land_use,
    lf.category_name as from_category,
    t.to_land_use,
    lt.category_name as to_category,
    SUM(t.area_hundreds_acres * 100) as acres_changed
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
JOIN
    land_use_categories lf ON t.from_land_use = lf.category_code
JOIN
    land_use_categories lt ON t.to_land_use = lt.category_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use != t.to_land_use
GROUP BY 
    c.region, t.from_land_use, lf.category_name, t.to_land_use, lt.category_name
ORDER BY 
    c.region, acres_changed DESC;
```

### Forest to Urban Conversion by State

```sql
SELECT 
    c.state_name,
    SUM(t.area_hundreds_acres * 100) as acres_converted
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use = 'fr'
    AND t.to_land_use = 'ur'
GROUP BY 
    c.state_name
ORDER BY 
    acres_converted DESC;
```

### Top Counties for Agricultural Expansion

```sql
SELECT 
    c.county_name,
    c.state_name,
    SUM(t.area_hundreds_acres * 100) as acres_gained
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.to_land_use = 'cr'
    AND t.from_land_use != 'cr'
GROUP BY 
    c.county_name, c.state_name
ORDER BY 
    acres_gained DESC
LIMIT 20;
```

## Scenario Comparison

### Compare Forest Loss Across Scenarios

```sql
WITH forest_loss AS (
    SELECT 
        s.scenario_id,
        s.scenario_name,
        s.gcm,
        s.rcp,
        s.ssp,
        SUM(CASE WHEN t.from_land_use = 'fr' AND t.to_land_use != 'fr' 
            THEN t.area_hundreds_acres * 100 ELSE 0 END) as acres_lost
    FROM 
        land_use_transitions t
    JOIN
        scenarios s ON t.scenario_id = s.scenario_id
    WHERE 
        t.time_step_id = 2
    GROUP BY 
        s.scenario_id, s.scenario_name, s.gcm, s.rcp, s.ssp
)
SELECT 
    scenario_name,
    gcm,
    rcp,
    ssp,
    acres_lost,
    RANK() OVER (ORDER BY acres_lost DESC) as loss_rank
FROM 
    forest_loss
ORDER BY 
    acres_lost DESC;
```

### Compare Urban Growth by Climate Model

```sql
SELECT 
    s.gcm as climate_model,
    t.time_step_id,
    ts.start_year,
    ts.end_year,
    SUM(CASE WHEN t.to_land_use = 'ur' AND t.from_land_use != 'ur' 
        THEN t.area_hundreds_acres * 100 ELSE 0 END) as urban_growth_acres
FROM 
    land_use_transitions t
JOIN
    scenarios s ON t.scenario_id = s.scenario_id
JOIN
    time_steps ts ON t.time_step_id = ts.time_step_id
WHERE 
    s.ssp = 'ssp2'  -- Keep socioeconomic pathway constant
GROUP BY 
    s.gcm, t.time_step_id, ts.start_year, ts.end_year
ORDER BY 
    s.gcm, t.time_step_id;
```

## Temporal Analysis

### Land Use Change Over Time (All Periods)

```sql
SELECT 
    t.time_step_id,
    ts.start_year,
    ts.end_year,
    t.from_land_use,
    t.to_land_use,
    SUM(t.area_hundreds_acres * 100) as acres_changed
FROM 
    land_use_transitions t
JOIN
    time_steps ts ON t.time_step_id = ts.time_step_id
WHERE 
    t.scenario_id = 1
    AND t.from_land_use != t.to_land_use
GROUP BY 
    t.time_step_id, ts.start_year, ts.end_year, t.from_land_use, t.to_land_use
ORDER BY 
    t.time_step_id, acres_changed DESC;
```

### Forest to Urban Conversion Rate Over Time

```sql
SELECT 
    ts.time_step_id,
    ts.start_year,
    ts.end_year,
    SUM(t.area_hundreds_acres * 100) as acres_converted,
    SUM(t.area_hundreds_acres * 100) / (ts.end_year - ts.start_year) as acres_per_year
FROM 
    land_use_transitions t
JOIN
    time_steps ts ON t.time_step_id = ts.time_step_id
WHERE 
    t.scenario_id = 1
    AND t.from_land_use = 'fr'
    AND t.to_land_use = 'ur'
GROUP BY 
    ts.time_step_id, ts.start_year, ts.end_year
ORDER BY 
    ts.time_step_id;
```

## Specialized Analyses

### Land Use Diversity by State

```sql
WITH state_land_use AS (
    SELECT 
        c.state_name,
        t.to_land_use,
        SUM(t.area_hundreds_acres * 100) as land_area
    FROM 
        land_use_transitions t
    JOIN 
        counties c ON t.fips_code = c.fips_code
    WHERE 
        t.scenario_id = 1 
        AND t.time_step_id = 2
        AND t.to_land_use NOT IN ('t1', 't2')
    GROUP BY 
        c.state_name, t.to_land_use
)
SELECT 
    state_name,
    COUNT(DISTINCT to_land_use) as land_use_count,
    SUM(land_area) as total_area,
    MIN(land_area) as min_land_use_area,
    MAX(land_area) as max_land_use_area,
    MAX(land_area) / NULLIF(MIN(land_area), 0) as max_min_ratio
FROM 
    state_land_use
GROUP BY 
    state_name
ORDER BY 
    land_use_count DESC, total_area DESC;
```

### Top Counties for Land Use Change Intensity

```sql
SELECT 
    c.county_name,
    c.state_name,
    SUM(CASE WHEN t.from_land_use != t.to_land_use 
        THEN t.area_hundreds_acres * 100 ELSE 0 END) as acres_changing,
    SUM(t.area_hundreds_acres * 100) as total_acres,
    (SUM(CASE WHEN t.from_land_use != t.to_land_use 
        THEN t.area_hundreds_acres * 100 ELSE 0 END) / 
        NULLIF(SUM(t.area_hundreds_acres * 100), 0)) * 100 as percent_changing
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
GROUP BY 
    c.county_name, c.state_name
HAVING 
    SUM(t.area_hundreds_acres * 100) > 10000  -- Minimum area threshold
ORDER BY 
    percent_changing DESC
LIMIT 20;
``` 