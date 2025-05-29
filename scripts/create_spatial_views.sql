-- RPA Land Use Viewer - Spatial Aggregation Views
-- This script creates views for different spatial levels to support the Data Explorer functionality
-- Updated to work with existing materialized views and proper land use type names

-- =============================================================================
-- COUNTY LEVEL VIEW (Base view - using the main landuse_change table)
-- =============================================================================
CREATE OR REPLACE VIEW county_level_transitions AS
SELECT 
    s.scenario_name,
    d.decade_name,
    c.fips_code,
    c.county_name,
    c.state_name,
    c.region,
    c.subregion,
    lt_from.landuse_type_name as from_category,
    lt_to.landuse_type_name as to_category,
    lc.area_hundreds_acres * 100 as total_area  -- Convert to acres
FROM landuse_change lc
JOIN scenarios s ON lc.scenario_id = s.scenario_id
JOIN decades d ON lc.decade_id = d.decade_id
JOIN counties c ON lc.fips_code = c.fips_code
JOIN landuse_types lt_from ON lc.from_landuse = lt_from.landuse_type_code
JOIN landuse_types lt_to ON lc.to_landuse = lt_to.landuse_type_code;

-- =============================================================================
-- STATE LEVEL VIEW (Using existing materialized view)
-- =============================================================================
CREATE OR REPLACE VIEW state_level_transitions AS
SELECT 
    scenario_name,
    decade_name,
    state_name,
    region,
    subregion,
    lt_from.landuse_type_name as from_category,
    lt_to.landuse_type_name as to_category,
    total_area * 100 as total_area  -- Convert to acres
FROM mat_state_transitions mst
JOIN landuse_types lt_from ON mst.from_landuse = lt_from.landuse_type_code
JOIN landuse_types lt_to ON mst.to_landuse = lt_to.landuse_type_code;

-- =============================================================================
-- REGION LEVEL VIEW (Using existing materialized view)
-- =============================================================================
CREATE OR REPLACE VIEW region_level_transitions AS
SELECT 
    scenario_name,
    decade_name,
    region,
    lt_from.landuse_type_name as from_category,
    lt_to.landuse_type_name as to_category,
    SUM(total_area * 100) as total_area  -- Convert to acres and aggregate
FROM mat_region_transitions mrt
JOIN landuse_types lt_from ON mrt.from_landuse = lt_from.landuse_type_code
JOIN landuse_types lt_to ON mrt.to_landuse = lt_to.landuse_type_code
GROUP BY 
    scenario_name,
    decade_name,
    region,
    lt_from.landuse_type_name,
    lt_to.landuse_type_name;

-- =============================================================================
-- SUBREGION LEVEL VIEW (Using existing materialized view)
-- =============================================================================
CREATE OR REPLACE VIEW subregion_level_transitions AS
SELECT 
    scenario_name,
    decade_name,
    subregion,
    lt_from.landuse_type_name as from_category,
    lt_to.landuse_type_name as to_category,
    SUM(total_area * 100) as total_area  -- Convert to acres and aggregate
FROM mat_subregion_transitions msrt
JOIN landuse_types lt_from ON msrt.from_landuse = lt_from.landuse_type_code
JOIN landuse_types lt_to ON msrt.to_landuse = lt_to.landuse_type_code
GROUP BY 
    scenario_name,
    decade_name,
    subregion,
    lt_from.landuse_type_name,
    lt_to.landuse_type_name;

-- =============================================================================
-- NATIONAL LEVEL VIEW (Aggregate from state level)
-- =============================================================================
CREATE OR REPLACE VIEW national_level_transitions AS
SELECT 
    scenario_name,
    decade_name,
    'United States' as country,
    from_category,
    to_category,
    SUM(total_area) as total_area  -- Already in acres from state_level_transitions
FROM state_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    from_category,
    to_category;

-- =============================================================================
-- SUMMARY VIEWS FOR EACH SPATIAL LEVEL (for quick exploration)
-- =============================================================================

-- County level summary (total transitions by county)
CREATE OR REPLACE VIEW county_level_summary AS
SELECT 
    scenario_name,
    decade_name,
    fips_code,
    county_name,
    state_name,
    region,
    subregion,
    SUM(total_area) as total_area_changed
FROM county_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    fips_code,
    county_name,
    state_name,
    region,
    subregion;

-- State level summary (total transitions by state)
CREATE OR REPLACE VIEW state_level_summary AS
SELECT 
    scenario_name,
    decade_name,
    state_name,
    region,
    subregion,
    SUM(total_area) as total_area_changed
FROM state_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    state_name,
    region,
    subregion;

-- Region level summary (total transitions by region)
CREATE OR REPLACE VIEW region_level_summary AS
SELECT 
    scenario_name,
    decade_name,
    region,
    SUM(total_area) as total_area_changed
FROM region_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    region;

-- Subregion level summary (total transitions by subregion)
CREATE OR REPLACE VIEW subregion_level_summary AS
SELECT 
    scenario_name,
    decade_name,
    subregion,
    SUM(total_area) as total_area_changed
FROM subregion_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    subregion;

-- National level summary (total transitions nationally)
CREATE OR REPLACE VIEW national_level_summary AS
SELECT 
    scenario_name,
    decade_name,
    country,
    SUM(total_area) as total_area_changed
FROM national_level_transitions
GROUP BY 
    scenario_name,
    decade_name,
    country;

-- =============================================================================
-- SPECIALIZED VIEWS FOR COMMON ANALYSIS PATTERNS
-- =============================================================================

-- Urbanization trends by spatial level
CREATE OR REPLACE VIEW urbanization_by_county AS
SELECT * FROM county_level_transitions WHERE to_category = 'Urban';

CREATE OR REPLACE VIEW urbanization_by_state AS
SELECT * FROM state_level_transitions WHERE to_category = 'Urban';

CREATE OR REPLACE VIEW urbanization_by_region AS
SELECT * FROM region_level_transitions WHERE to_category = 'Urban';

CREATE OR REPLACE VIEW urbanization_by_subregion AS
SELECT * FROM subregion_level_transitions WHERE to_category = 'Urban';

CREATE OR REPLACE VIEW urbanization_by_national AS
SELECT * FROM national_level_transitions WHERE to_category = 'Urban';

-- Forest loss trends by spatial level
CREATE OR REPLACE VIEW forest_loss_by_county AS
SELECT * FROM county_level_transitions WHERE from_category = 'Forest';

CREATE OR REPLACE VIEW forest_loss_by_state AS
SELECT * FROM state_level_transitions WHERE from_category = 'Forest';

CREATE OR REPLACE VIEW forest_loss_by_region AS
SELECT * FROM region_level_transitions WHERE from_category = 'Forest';

CREATE OR REPLACE VIEW forest_loss_by_subregion AS
SELECT * FROM subregion_level_transitions WHERE from_category = 'Forest';

CREATE OR REPLACE VIEW forest_loss_by_national AS
SELECT * FROM national_level_transitions WHERE from_category = 'Forest';

-- Agricultural land transitions by spatial level
CREATE OR REPLACE VIEW agricultural_transitions_by_county AS
SELECT * FROM county_level_transitions WHERE from_category IN ('Cropland', 'Pasture');

CREATE OR REPLACE VIEW agricultural_transitions_by_state AS
SELECT * FROM state_level_transitions WHERE from_category IN ('Cropland', 'Pasture');

CREATE OR REPLACE VIEW agricultural_transitions_by_region AS
SELECT * FROM region_level_transitions WHERE from_category IN ('Cropland', 'Pasture');

CREATE OR REPLACE VIEW agricultural_transitions_by_subregion AS
SELECT * FROM subregion_level_transitions WHERE from_category IN ('Cropland', 'Pasture');

CREATE OR REPLACE VIEW agricultural_transitions_by_national AS
SELECT * FROM national_level_transitions WHERE from_category IN ('Cropland', 'Pasture');

-- =============================================================================
-- ENSEMBLE SCENARIO MAPPING (Create cleaner scenario names)
-- =============================================================================

-- Create a mapping of scenario patterns to ensemble names
CREATE OR REPLACE VIEW scenario_mapping AS
SELECT 
    scenario_name as original_scenario,
    CASE 
        WHEN scenario_name LIKE '%rcp45_ssp1%' THEN 'ensemble_LM'
        WHEN scenario_name LIKE '%rcp85_ssp3%' THEN 'ensemble_HL'  
        WHEN scenario_name LIKE '%rcp85_ssp2%' THEN 'ensemble_HM'
        WHEN scenario_name LIKE '%rcp85_ssp5%' THEN 'ensemble_HH'
        ELSE scenario_name
    END as ensemble_scenario
FROM scenarios;

-- =============================================================================
-- DATASET MAPPING FOR STREAMLIT APP
-- =============================================================================

-- Map the views to the datasets expected by the Streamlit app
CREATE OR REPLACE VIEW "County-Level Land Use Transitions" AS
SELECT * FROM county_level_transitions;

CREATE OR REPLACE VIEW "State-Level Land Use Transitions" AS  
SELECT * FROM state_level_transitions;

CREATE OR REPLACE VIEW "Region-Level Land Use Transitions" AS
SELECT * FROM region_level_transitions;

CREATE OR REPLACE VIEW "Subregion-Level Land Use Transitions" AS
SELECT * FROM subregion_level_transitions;

CREATE OR REPLACE VIEW "National-Level Land Use Transitions" AS
SELECT * FROM national_level_transitions;

-- Urbanization trends dataset
CREATE OR REPLACE VIEW "Urbanization Trends By Decade" AS
SELECT 
    scenario_name,
    decade_name,
    SUM(CASE WHEN from_category = 'Forest' AND to_category = 'Urban' THEN total_area ELSE 0 END) as forest_to_urban,
    SUM(CASE WHEN from_category = 'Cropland' AND to_category = 'Urban' THEN total_area ELSE 0 END) as cropland_to_urban,
    SUM(CASE WHEN from_category = 'Pasture' AND to_category = 'Urban' THEN total_area ELSE 0 END) as pasture_to_urban
FROM national_level_transitions
WHERE to_category = 'Urban'
GROUP BY scenario_name, decade_name;

-- =============================================================================
-- CREATE INDEXES ON BASE TABLE FOR BETTER PERFORMANCE
-- =============================================================================

-- Indexes for common query patterns (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_landuse_change_scenario_decade ON landuse_change (scenario_id, decade_id);
CREATE INDEX IF NOT EXISTS idx_landuse_change_fips ON landuse_change (fips_code);
CREATE INDEX IF NOT EXISTS idx_landuse_change_transitions ON landuse_change (from_landuse, to_landuse);
CREATE INDEX IF NOT EXISTS idx_counties_state ON counties (state_name);
CREATE INDEX IF NOT EXISTS idx_counties_region ON counties (region);
CREATE INDEX IF NOT EXISTS idx_counties_subregion ON counties (subregion); 