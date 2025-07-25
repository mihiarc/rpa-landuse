# RPA Land Use Change Methodology

## Overview

The land use projections in the RPA Assessment database are based on a sophisticated econometric model that projects county-level land use transitions from 2020 to 2070. This document explains the methodology, key assumptions, and how to interpret the data.

## Model Characteristics

### Core Features
- **Spatial Resolution**: County-level (3,075 counties in conterminous U.S.)
- **Temporal Coverage**: 2020-2070 projections
- **Land Ownership**: Private land only
- **Scenarios**: 20 integrated climate-socioeconomic futures
- **Policy Approach**: Policy-neutral projections

### Key Assumptions
1. **Development is Irreversible**: Once land converts to developed use, it doesn't revert
2. **Private Land Focus**: All transitions occur on privately owned land
3. **Historical Basis**: Model calibrated on observed transitions from 2001-2012
4. **Policy Neutral**: No assumptions about future conservation policies

## Land Use Classes

The model tracks five major land use categories:

| Code | Land Use | Category | Description |
|------|----------|----------|-------------|
| **cr** | Crop | Agriculture | Agricultural cropland |
| **ps** | Pasture | Agriculture | Livestock grazing land |
| **fr** | Forest | Natural | Forested areas |
| **ur** | Urban | Developed | Built/developed areas |
| **rg** | Rangeland | Natural | Natural grasslands |

## Historical Context

### Development Trends
The model was calibrated during a period of changing development patterns:
- **1980s**: ~1.2 million acres/year converted to developed
- **1992-1997**: Peak at ~2.0 million acres/year
- **After 2000**: Declining rate (reflected in projections)

### Observed Transitions (2001-2012)
- Most active transitions between **crop ↔ pasture** (agricultural rotation)
- **Forest → Developed**: Primary urbanization pathway
- **Agricultural → Developed**: Secondary urbanization pathway

## Projection Methodology

### Model Structure
1. **Econometric Foundation**: Based on empirical analysis of NRI data
2. **Climate Integration**: Incorporates temperature and precipitation projections
3. **Socioeconomic Drivers**: Population and GDP growth from SSPs
4. **Spatial Constraints**: Respects county boundaries and land availability

### Scenario Integration
Each of the 20 scenarios combines:
- **Climate Model** (5 options): Hot, Wet, Dry, Least warm, Middle
- **RCP Pathway** (2 options): RCP 4.5 or RCP 8.5
- **SSP Pathway** (4 options): SSP1, SSP2, SSP3, or SSP5

### Projection Process
1. Calculate transition probabilities based on:
   - Historical land use patterns
   - Projected climate conditions
   - Socioeconomic growth rates
   - Land quality factors

2. Apply constraints:
   - Total county area must be conserved
   - Development cannot revert
   - Transitions follow observed patterns

3. Generate projections for six time periods:
   - 2012-2020, 2020-2030, 2030-2040, 2040-2050, 2050-2070, 2070-2100

## Key Projections (2020-2070)

### National Level
- **Developed Land**: +41.3 to +57.0 million acres
- **Forest Land**: -7.6 to -15.0 million acres
- **Agricultural Land**: Variable by scenario
- **Primary Conversion**: ~46% of new developed land from forest

### Regional Patterns
**Highest Development Pressure**:
1. South Region: 18.4-25.0 million acres
2. North Region: 10.6-14.0 million acres
3. Rocky Mountain: 6.4-8.9 million acres
4. Pacific Coast: 5.9-9.9 million acres

**Forest Loss Patterns**:
- Largest losses: South Region (4.6-9.2 million acres)
- Moderate losses: Pacific Coast, North
- Smallest losses: Rocky Mountain Region

## Scenario Effects

### Climate Impact (RCP 4.5 vs RCP 8.5)
Higher warming (RCP 8.5) results in:
- **2.4% less** developed land expansion
- **1.2 million acres more** forest retention
- Climate stress reduces development attractiveness

### Socioeconomic Impact (Low vs High Growth)
Higher growth (SSP5 vs SSP3) results in:
- **9.4% more** developed land expansion
- **3.5 million acres less** forest
- Economic pressure drives conversion

## Data Structure in Database

### Fact Table: `fact_landuse_transitions`
Each record represents a land use transition for a specific:
- County (geography_id)
- Time period (time_id)
- Scenario (scenario_id)
- Transition type (from_landuse_id → to_landuse_id)

### Key Fields
- **acres**: Area undergoing this specific transition
- **transition_type**: 'change' (actual transition) or 'same' (no change)

### Aggregation Patterns
Common aggregations in analysis:
- **By Scenario**: Compare climate/socioeconomic pathways
- **By Time**: Track temporal trends
- **By Geography**: State or regional patterns
- **By Transition**: Focus on specific conversions (e.g., forest loss)

## Important Considerations

### When Analyzing Data

1. **Default to Averages**: When not comparing scenarios, average across all 20
2. **Focus on Changes**: Use transition_type = 'change' for actual transitions
3. **Consider Scale**: National patterns may differ from local trends
4. **Remember Constraints**: Development is irreversible in projections

### Common Analysis Patterns

```sql
-- Total agricultural loss (averaged across scenarios)
SELECT AVG(acres) as avg_loss_per_scenario
FROM fact_landuse_transitions
WHERE from_landuse_id IN (SELECT landuse_id FROM dim_landuse WHERE landuse_category = 'Agriculture')
  AND to_landuse_id NOT IN (SELECT landuse_id FROM dim_landuse WHERE landuse_category = 'Agriculture')
  AND transition_type = 'change';

-- Urbanization by source
SELECT fl.landuse_name as source, SUM(acres) as total_converted
FROM fact_landuse_transitions f
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE tl.landuse_code = 'ur' AND f.transition_type = 'change'
GROUP BY fl.landuse_name;
```

### Limitations

1. **Private Land Only**: Public lands assumed static
2. **Policy Neutral**: Doesn't account for future conservation efforts
3. **County Level**: Sub-county patterns not captured
4. **Historical Basis**: Assumes past relationships continue

## References

- Mihiar, C.J.; Lewis, D.J.; Coulston, J.W. 2023. Land use projections for the 2020 RPA Assessment. https://doi.org/10.2737/RDS-2023-0026
- Chapter 4: Land Resources. In: Future of America's Forest and Rangelands: Forest Service 2020 Resources Planning Act Assessment. Gen. Tech. Rep. WO-102.