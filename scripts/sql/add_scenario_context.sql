-- RPA Scenario Context Views
-- Adds descriptive information about RPA scenarios to the database

-- Create a view that enriches scenario information with RPA context
CREATE OR REPLACE VIEW v_scenario_details AS
WITH scenario_mapping AS (
    SELECT 
        scenario_id,
        scenario_name,
        climate_model,
        rcp_scenario,
        ssp_scenario,
        -- Map to RPA scenario codes
        CASE 
            WHEN rcp_scenario = 'rcp45' AND ssp_scenario = 'ssp1' THEN 'LM'
            WHEN rcp_scenario = 'rcp85' AND ssp_scenario = 'ssp3' THEN 'HL'
            WHEN rcp_scenario = 'rcp85' AND ssp_scenario = 'ssp2' THEN 'HM'
            WHEN rcp_scenario = 'rcp85' AND ssp_scenario = 'ssp5' THEN 'HH'
        END as rpa_code,
        -- Climate model characteristics
        CASE climate_model
            WHEN 'CNRM_CM5' THEN 'Wet - Increased precipitation'
            WHEN 'HadGEM2_ES365' THEN 'Hot - Upper bound warming'
            WHEN 'IPSL_CM5A_MR' THEN 'Dry - Reduced precipitation'
            WHEN 'MRI_CGCM3' THEN 'Least warm - Lower bound warming'
            WHEN 'NorESM1_M' THEN 'Middle - Central tendency'
        END as climate_characteristic,
        -- RCP descriptions
        CASE rcp_scenario
            WHEN 'rcp45' THEN 'Lower emissions (~2.5°C warming by 2100)'
            WHEN 'rcp85' THEN 'High emissions (~4.5°C warming by 2100)'
        END as rcp_description,
        -- SSP descriptions
        CASE ssp_scenario
            WHEN 'ssp1' THEN 'Sustainability - Green growth, cooperation'
            WHEN 'ssp2' THEN 'Middle of the road - Historical trends'
            WHEN 'ssp3' THEN 'Regional rivalry - Nationalism, conflicts'
            WHEN 'ssp5' THEN 'Fossil-fueled - Rapid growth, high consumption'
        END as ssp_description
    FROM dim_scenario
)
SELECT 
    s.*,
    -- Add RPA scenario descriptions
    CASE rpa_code
        WHEN 'LM' THEN 'Lower-Moderate: Sustainable development with climate action'
        WHEN 'HL' THEN 'High-Low: Climate challenges with economic struggles'
        WHEN 'HM' THEN 'High-Moderate: Business as usual with climate impacts'
        WHEN 'HH' THEN 'High-High: Rapid growth despite climate change'
    END as rpa_description,
    -- Growth projections
    CASE rpa_code
        WHEN 'LM' THEN 'U.S. GDP: 3.0x, Population: 1.5x by 2070'
        WHEN 'HL' THEN 'U.S. GDP: 1.9x, Population: 1.0x by 2070'
        WHEN 'HM' THEN 'U.S. GDP: 2.8x, Population: 1.4x by 2070'
        WHEN 'HH' THEN 'U.S. GDP: 4.7x, Population: 1.9x by 2070'
    END as growth_projection
FROM scenario_mapping s;

-- Create a summary view of scenarios grouped by RPA code
CREATE OR REPLACE VIEW v_rpa_scenario_summary AS
SELECT 
    rpa_code,
    rpa_description,
    rcp_scenario,
    ssp_scenario,
    COUNT(*) as model_count,
    STRING_AGG(climate_model || ' (' || SPLIT_PART(climate_characteristic, ' - ', 1) || ')', ', ') as climate_models,
    growth_projection
FROM v_scenario_details
WHERE rpa_code IS NOT NULL
GROUP BY rpa_code, rpa_description, rcp_scenario, ssp_scenario, growth_projection
ORDER BY rpa_code;

-- Create a view for comparing scenarios by their characteristics
CREATE OR REPLACE VIEW v_scenario_comparison AS
SELECT 
    sd.rpa_code,
    sd.climate_model,
    sd.climate_characteristic,
    SUM(CASE WHEN tl.landuse_code = 'ur' AND fl.landuse_code != 'ur' THEN f.acres ELSE 0 END) as urban_expansion_acres,
    SUM(CASE WHEN fl.landuse_category = 'Agriculture' AND tl.landuse_category != 'Agriculture' THEN f.acres ELSE 0 END) as agricultural_loss_acres,
    SUM(CASE WHEN fl.landuse_code = 'fr' AND tl.landuse_code != 'fr' THEN f.acres ELSE 0 END) as forest_loss_acres
FROM fact_landuse_transitions f
JOIN v_scenario_details sd ON f.scenario_id = sd.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY sd.rpa_code, sd.climate_model, sd.climate_characteristic;

-- Add comments to help users understand the views
COMMENT ON VIEW v_scenario_details IS 'Detailed information about each RPA scenario including climate and socioeconomic characteristics';
COMMENT ON VIEW v_rpa_scenario_summary IS 'Summary of the four main RPA scenarios (LM, HL, HM, HH) with their key characteristics';
COMMENT ON VIEW v_scenario_comparison IS 'Comparison of land use changes across different scenarios and climate models';