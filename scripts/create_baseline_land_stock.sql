-- =============================================================================
-- CREATE BASELINE LAND STOCK VIEWS
-- =============================================================================
-- 
-- This script creates views that capture the starting land use stocks for 2020
-- by summing up all the 'from_landuse' areas in the first decade.
-- 
-- These baseline stocks are essential for calculating proper urbanization rates
-- as percentages relative to the initial urban area in each county.
--
-- Author: RPA Land Use Analysis System
-- Created: 2024-06-02
-- =============================================================================

-- Create baseline land stock by county (2020 starting conditions)
CREATE OR REPLACE VIEW baseline_county_land_stock AS
SELECT 
    co.fips_code,
    co.county_name,
    co.state_name,
    co.region,
    co.subregion,
    s.scenario_name,
    lt.landuse_type_name as land_use_type,
    lc.from_landuse as land_use_code,
    SUM(lc.area_hundreds_acres * 100) as baseline_acres_2020
FROM landuse_change lc
JOIN counties co ON lc.fips_code = co.fips_code
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN landuse_types lt ON lc.from_landuse = lt.landuse_type_code
WHERE lc.decade_id = 1  -- First decade (2020-2030) represents 2020 starting conditions
GROUP BY 
    co.fips_code, co.county_name, co.state_name, co.region, co.subregion,
    s.scenario_name, lt.landuse_type_name, lc.from_landuse
ORDER BY co.state_name, co.county_name, s.scenario_name, lt.landuse_type_name;

-- Create baseline land stock by state (2020 starting conditions)
CREATE OR REPLACE VIEW baseline_state_land_stock AS
SELECT 
    co.state_name,
    co.region,
    co.subregion,
    s.scenario_name,
    lt.landuse_type_name as land_use_type,
    lc.from_landuse as land_use_code,
    SUM(lc.area_hundreds_acres * 100) as baseline_acres_2020
FROM landuse_change lc
JOIN counties co ON lc.fips_code = co.fips_code
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN landuse_types lt ON lc.from_landuse = lt.landuse_type_code
WHERE lc.decade_id = 1  -- First decade (2020-2030) represents 2020 starting conditions
GROUP BY 
    co.state_name, co.region, co.subregion,
    s.scenario_name, lt.landuse_type_name, lc.from_landuse
ORDER BY co.state_name, s.scenario_name, lt.landuse_type_name;

-- Create baseline land stock by region (2020 starting conditions)
CREATE OR REPLACE VIEW baseline_region_land_stock AS
SELECT 
    co.region,
    s.scenario_name,
    lt.landuse_type_name as land_use_type,
    lc.from_landuse as land_use_code,
    SUM(lc.area_hundreds_acres * 100) as baseline_acres_2020
FROM landuse_change lc
JOIN counties co ON lc.fips_code = co.fips_code
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN landuse_types lt ON lc.from_landuse = lt.landuse_type_code
WHERE lc.decade_id = 1  -- First decade (2020-2030) represents 2020 starting conditions
GROUP BY 
    co.region, s.scenario_name, lt.landuse_type_name, lc.from_landuse
ORDER BY co.region, s.scenario_name, lt.landuse_type_name;

-- Create baseline land stock by subregion (2020 starting conditions)
CREATE OR REPLACE VIEW baseline_subregion_land_stock AS
SELECT 
    co.subregion,
    co.region,
    s.scenario_name,
    lt.landuse_type_name as land_use_type,
    lc.from_landuse as land_use_code,
    SUM(lc.area_hundreds_acres * 100) as baseline_acres_2020
FROM landuse_change lc
JOIN counties co ON lc.fips_code = co.fips_code
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN landuse_types lt ON lc.from_landuse = lt.landuse_type_code
WHERE lc.decade_id = 1  -- First decade (2020-2030) represents 2020 starting conditions
GROUP BY 
    co.subregion, co.region, s.scenario_name, lt.landuse_type_name, lc.from_landuse
ORDER BY co.subregion, s.scenario_name, lt.landuse_type_name;

-- Create baseline land stock national (2020 starting conditions)
CREATE OR REPLACE VIEW baseline_national_land_stock AS
SELECT 
    s.scenario_name,
    lt.landuse_type_name as land_use_type,
    lc.from_landuse as land_use_code,
    SUM(lc.area_hundreds_acres * 100) as baseline_acres_2020
FROM landuse_change lc
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN landuse_types lt ON lc.from_landuse = lt.landuse_type_code
WHERE lc.decade_id = 1  -- First decade (2020-2030) represents 2020 starting conditions
GROUP BY 
    s.scenario_name, lt.landuse_type_name, lc.from_landuse
ORDER BY s.scenario_name, lt.landuse_type_name;

-- =============================================================================
-- ENHANCED URBANIZATION ANALYSIS WITH BASELINE RATES
-- =============================================================================

-- Enhanced county urbanization analysis with baseline urban area and true percentage rates
CREATE OR REPLACE VIEW enhanced_county_urbanization_analysis AS
WITH baseline_urban AS (
    SELECT 
        fips_code,
        county_name,
        state_name,
        region,
        subregion,
        scenario_name,
        baseline_acres_2020 as baseline_urban_acres_2020
    FROM baseline_county_land_stock
    WHERE land_use_code = 'ur'  -- Urban land use
),
new_urban_development AS (
    SELECT 
        fips_code,
        county_name,
        state_name,
        region,
        subregion,
        scenario_name,
        from_category,
        SUM(total_area) as new_urban_acres
    FROM "County-Level Land Use Transitions"
    WHERE to_category = 'Urban' AND from_category != 'Urban'  -- Only NEW urban development
    GROUP BY fips_code, county_name, state_name, region, subregion, scenario_name, from_category
),
total_new_urban AS (
    SELECT 
        fips_code,
        county_name,
        state_name,
        region,
        subregion,
        scenario_name,
        SUM(new_urban_acres) as total_new_urban_acres
    FROM new_urban_development
    GROUP BY fips_code, county_name, state_name, region, subregion, scenario_name
)
SELECT 
    b.fips_code,
    b.county_name,
    b.state_name,
    b.region,
    b.subregion,
    b.scenario_name,
    b.baseline_urban_acres_2020,
    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
    (b.baseline_urban_acres_2020 + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
    -- Calculate proper urbanization rate as percentage relative to 2020 baseline
    CASE 
        WHEN b.baseline_urban_acres_2020 > 0 THEN 
            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
        ELSE NULL
    END as urbanization_rate_percent,
    -- Calculate absolute rate (acres per decade)
    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
    -- Calculate annualized percentage growth rate
    CASE 
        WHEN b.baseline_urban_acres_2020 > 0 THEN 
            (POWER((b.baseline_urban_acres_2020 + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
        ELSE NULL
    END as annualized_urban_growth_rate_percent
FROM baseline_urban b
LEFT JOIN total_new_urban t ON b.fips_code = t.fips_code 
    AND b.county_name = t.county_name 
    AND b.state_name = t.state_name 
    AND b.scenario_name = t.scenario_name
ORDER BY COALESCE(t.total_new_urban_acres, 0) DESC;

-- Enhanced state urbanization analysis with baseline urban area and true percentage rates
CREATE OR REPLACE VIEW enhanced_state_urbanization_analysis AS
WITH baseline_urban AS (
    SELECT 
        state_name,
        region,
        subregion,
        scenario_name,
        baseline_acres_2020 as baseline_urban_acres_2020
    FROM baseline_state_land_stock
    WHERE land_use_code = 'ur'  -- Urban land use
),
new_urban_development AS (
    SELECT 
        state_name,
        region,
        subregion,
        scenario_name,
        SUM(total_area) as total_new_urban_acres
    FROM "State-Level Land Use Transitions"
    WHERE to_category = 'Urban' AND from_category != 'Urban'  -- Only NEW urban development
    GROUP BY state_name, region, subregion, scenario_name
)
SELECT 
    b.state_name,
    b.region,
    b.subregion,
    b.scenario_name,
    b.baseline_urban_acres_2020,
    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
    (b.baseline_urban_acres_2020 + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
    -- Calculate proper urbanization rate as percentage relative to 2020 baseline
    CASE 
        WHEN b.baseline_urban_acres_2020 > 0 THEN 
            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
        ELSE NULL
    END as urbanization_rate_percent,
    -- Calculate absolute rate (acres per decade)
    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
    -- Calculate annualized percentage growth rate
    CASE 
        WHEN b.baseline_urban_acres_2020 > 0 THEN 
            (POWER((b.baseline_urban_acres_2020 + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
        ELSE NULL
    END as annualized_urban_growth_rate_percent
FROM baseline_urban b
LEFT JOIN new_urban_development t ON b.state_name = t.state_name 
    AND b.scenario_name = t.scenario_name
ORDER BY COALESCE(t.total_new_urban_acres, 0) DESC;

-- =============================================================================
-- CREATE INDEXES FOR OPTIMAL PERFORMANCE
-- =============================================================================

-- Create indexes on baseline views for better query performance
CREATE INDEX IF NOT EXISTS idx_baseline_county_fips_scenario ON baseline_county_land_stock (fips_code, scenario_name, land_use_code);
CREATE INDEX IF NOT EXISTS idx_baseline_state_scenario ON baseline_state_land_stock (state_name, scenario_name, land_use_code);
CREATE INDEX IF NOT EXISTS idx_baseline_region_scenario ON baseline_region_land_stock (region, scenario_name, land_use_code);

-- =============================================================================
-- VALIDATION QUERIES
-- =============================================================================

-- Query to validate baseline urban acres by state (example)
-- SELECT state_name, scenario_name, baseline_acres_2020 
-- FROM baseline_state_land_stock 
-- WHERE land_use_code = 'ur' AND scenario_name = 'ensemble_overall'
-- ORDER BY baseline_acres_2020 DESC LIMIT 10;

-- Query to validate enhanced urbanization analysis (example)
-- SELECT county_name, state_name, baseline_urban_acres_2020, total_new_urban_acres, 
--        urbanization_rate_percent, annualized_urban_growth_rate_percent
-- FROM enhanced_county_urbanization_analysis 
-- WHERE scenario_name = 'ensemble_overall' 
-- ORDER BY urbanization_rate_percent DESC LIMIT 10; 