# RPA Scenarios Quick Reference

This document provides a quick reference to the RPA Assessment scenarios.

> **📚 For Complete Scenario Documentation**: See the [Scenarios Guide](rpa/scenarios.md) which includes comprehensive details about all scenarios, climate models, and analysis patterns.

## The Four RPA Scenarios

| Scenario | Code | Climate | Socioeconomic | U.S. Growth | Theme |
|----------|------|---------|---------------|-------------|-------|
| **Lower-Moderate** | **LM** | RCP 4.5 | SSP1 | 3.0X GDP, 1.5X Pop | "Taking the Green Road" |
| **High-Low** | **HL** | RCP 8.5 | SSP3 | 1.9X GDP, 1.0X Pop | "A Rocky Road" |
| **High-Moderate** | **HM** | RCP 8.5 | SSP2 | 2.8X GDP, 1.4X Pop | "Middle of the Road" |
| **High-High** | **HH** | RCP 8.5 | SSP5 | 4.7X GDP, 1.9X Pop | "Taking the Highway" |

## Quick Comparison

### Climate Impact
- **Lower Warming**: LM (~2.5°C by 2100)
- **Higher Warming**: HL, HM, HH (~4.5°C by 2100)

### Development Pressure
- **Highest**: HH (rapid development, urbanization)
- **Moderate**: LM, HM (balanced growth)
- **Lowest**: HL (regional rivalry, slow growth)

### Agricultural Land Loss
- **Most Severe**: HH (high population and economic growth)
- **Moderate**: LM, HM (middle scenarios)
- **Least Severe**: HL (low growth scenario)

## Climate Models

The RPA Assessment uses **5 climate models** to capture uncertainty:

| Model | Type | Institution | Characteristic |
|-------|------|-------------|----------------|
| **MRI-CGCM3** | Least Warm | Japan Meteorological Research Institute | Lower warming bound |
| **HadGEM2-ES** | Hot | UK Met Office Hadley Centre | Upper warming bound |
| **IPSL-CM5A-MR** | Dry | Institut Pierre Simon Laplace, France | Reduced precipitation |
| **CNRM-CM5** | Wet | Centre National de Recherches Météorologiques, France | Increased precipitation |
| **NorESM1-M** | Middle | Norwegian Climate Center | Central tendency |

## Database Scenario Names

In the DuckDB database, scenarios follow this naming convention:

```
Format: {ClimateModel}_{RCP}_ssp{SSP}

Examples:
- CNRM_CM5_rcp45_ssp1 → LM scenario, Wet climate model
- HadGEM2_ES365_rcp85_ssp5 → HH scenario, Hot climate model
- MRI_CGCM3_rcp85_ssp3 → HL scenario, Least Warm climate model
```

**Total Scenarios**: 20 (5 climate models × 4 RPA scenarios)

## Using Scenarios in Queries

### Natural Language Examples
```
"Show forest loss in the High-High scenario"
"Compare agricultural land loss between LM and HH"
"What happens to urban development in the Low scenario?"
"Show all climate model variations for HM"
```

### SQL Examples
```sql
-- Query specific RPA scenario (all climate models)
SELECT * FROM fact_landuse_transitions
WHERE scenario_name LIKE '%_rcp85_ssp5'  -- HH scenario

-- Query specific climate model
SELECT * FROM fact_landuse_transitions
WHERE scenario_name LIKE 'HadGEM2_ES365_%'  -- Hot model

-- Query both RPA code and climate model
SELECT * FROM fact_landuse_transitions
WHERE scenario_name = 'CNRM_CM5_rcp45_ssp1'  -- LM Wet
```

## Scenario Mapping Reference

### RPA Code to Technical Name

| RPA Code | RCP | SSP | Technical Pattern |
|----------|-----|-----|-------------------|
| **LM** | 4.5 | 1 | `*_rcp45_ssp1` |
| **HL** | 8.5 | 3 | `*_rcp85_ssp3` |
| **HM** | 8.5 | 2 | `*_rcp85_ssp2` |
| **HH** | 8.5 | 5 | `*_rcp85_ssp5` |

### Climate Model Codes

| Database Code | Short Name | Description |
|---------------|------------|-------------|
| **CNRM_CM5** | Wet | Increased precipitation |
| **HadGEM2_ES365** | Hot | Upper warming bound |
| **IPSL_CM5A_MR** | Dry | Reduced precipitation |
| **MRI_CGCM3** | Least Warm | Lower warming bound |
| **NorESM1_M** | Middle | Central tendency |

## Related Documentation

- **[Complete Scenarios Guide](rpa/scenarios.md)** - Comprehensive scenario documentation with analysis patterns
- **[Climate Models](rpa/climate-models.md)** - Detailed climate model specifications
- **[Complete RPA Assessment Reference](rpa/rpa-assessment-complete.md)** - Full RPA methodology and framework
- **[Data Dictionary](data/data-dictionary.md)** - Database schema and scenario fields

---

*For detailed analysis guidelines and land use implications, refer to the [Complete Scenarios Guide](rpa/scenarios.md).*
