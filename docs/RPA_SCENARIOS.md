# RPA Assessment Scenarios Reference Guide

## Overview

The 2020 RPA Assessment uses four integrated scenarios to explore alternative futures and provide a framework for evaluating a plausible range of natural resource outcomes through 2070. These scenarios combine climate pathways (RCPs) with socioeconomic pathways (SSPs) to create comprehensive projections.

## The Four RPA Scenarios

### Quick Reference Table

| Scenario | Code | Climate | Socioeconomic | Description |
|----------|------|---------|---------------|-------------|
| **Lower-Moderate** | LM | RCP 4.5 | SSP1 | Lower warming, moderate U.S. growth, sustainable development |
| **High-Low** | HL | RCP 8.5 | SSP3 | High warming, low U.S. growth, regional rivalry |
| **High-Moderate** | HM | RCP 8.5 | SSP2 | High warming, moderate U.S. growth, middle of the road |
| **High-High** | HH | RCP 8.5 | SSP5 | High warming, high U.S. growth, fossil-fueled development |

### Detailed Scenario Descriptions

#### Scenario LM: Lower warming-moderate U.S. growth (RCP 4.5-SSP1)
- **Theme**: "Taking the Green Road"
- **Climate**: Lower emissions with moderate warming (~2.5°C by 2100)
- **Society**: Strong international cooperation, sustainable practices
- **U.S. Economy**: 3.0X GDP growth by 2070
- **U.S. Population**: 1.5X growth to ~470 million by 2070
- **Key Features**: Environmental protection prioritized, renewable energy transition

#### Scenario HL: High warming-low U.S. growth (RCP 8.5-SSP3)
- **Theme**: "A Rocky Road"
- **Climate**: High emissions with significant warming (~4.5°C by 2100)
- **Society**: Nationalism, regional conflicts, security concerns
- **U.S. Economy**: 1.9X GDP growth by 2070 (slowest)
- **U.S. Population**: 1.0X (no net growth, ~330 million by 2070)
- **Key Features**: Trade barriers, resource competition, adaptation challenges

#### Scenario HM: High warming-moderate U.S. growth (RCP 8.5-SSP2)
- **Theme**: "Middle of the Road"
- **Climate**: High emissions with significant warming (~4.5°C by 2100)
- **Society**: Historical trends continue, slow progress
- **U.S. Economy**: 2.8X GDP growth by 2070
- **U.S. Population**: 1.4X growth to ~450 million by 2070
- **Key Features**: Uneven development, moderate challenges and progress

#### Scenario HH: High warming-high U.S. growth (RCP 8.5-SSP5)
- **Theme**: "Taking the Highway"
- **Climate**: High emissions with significant warming (~4.5°C by 2100)
- **Society**: Rapid development, technology-focused, fossil fuel reliant
- **U.S. Economy**: 4.7X GDP growth by 2070 (highest)
- **U.S. Population**: 1.9X growth to ~580 million by 2070
- **Key Features**: High consumption, technological solutions, urbanization

## Climate Models Used

The RPA Assessment uses five climate models to capture different aspects of climate change:

### The Five Core Climate Projections

| Model Type | Climate Model | Institution | Key Characteristic |
|------------|---------------|-------------|-------------------|
| **Least warm** | MRI-CGCM3 | Meteorological Research Institute, Japan | Lower bound of warming |
| **Hot** | HadGEM2-ES | Met Office Hadley Centre, UK | Upper bound of warming |
| **Dry** | IPSL-CM5A-MR | Institut Pierre Simon Laplace, France | Reduced precipitation |
| **Wet** | CNRM-CM5 | National Centre of Meteorological Research, France | Increased precipitation |
| **Middle** | NorESM1-M | Norwegian Climate Center, Norway | Central tendency |

## Understanding RCPs and SSPs

### Representative Concentration Pathways (RCPs)
- **RCP 4.5**: Medium forcing scenario with emissions peaking around 2040
  - Assumes implementation of climate policies
  - ~2.5°C global warming by 2100
  - Used in scenario LM

- **RCP 8.5**: High forcing scenario with continued emissions growth
  - Assumes limited climate action
  - ~4.5°C global warming by 2100
  - Used in scenarios HL, HM, and HH

### Shared Socioeconomic Pathways (SSPs)
- **SSP1 - Sustainability**: Green growth, reduced inequality, international cooperation
- **SSP2 - Middle of the Road**: Historical trends continue, slow progress
- **SSP3 - Regional Rivalry**: Nationalism, security concerns, material-intensive consumption
- **SSP5 - Fossil-fueled Development**: Rapid growth, technological solutions, high energy use

## Land Use Implications by Scenario

### Development Pressure
- **Highest**: Scenario HH (high growth, urbanization)
- **Moderate**: Scenarios LM and HM (balanced growth)
- **Lowest**: Scenario HL (low growth, limited expansion)

### Agricultural Land Loss
- **Most Severe**: Scenarios with high population/economic growth (HH)
- **Moderate**: Middle scenarios (LM, HM)
- **Least Severe**: Low growth scenario (HL)

### Forest Conservation
- **Best Outcomes**: Scenario LM (sustainability focus)
- **Worst Outcomes**: Scenario HH (development pressure)
- **Variable**: Scenarios HL and HM (depends on regional factors)

## Using Scenarios in Analysis

### Time Horizons
- **Near-term (2020-2030)**: Limited divergence between scenarios
- **Mid-term (2030-2050)**: Increasing differentiation
- **Long-term (2050-2070)**: Maximum scenario divergence

### Best Practices
1. **Always specify the scenario** when presenting results
2. **Compare across scenarios** to show uncertainty range
3. **Use scenario names consistently** (LM, HL, HM, HH)
4. **Include climate model** when relevant (e.g., "HH-Hot" or "LM-Wet")
5. **Consider averaging** across all scenarios for general trends

### Common Analysis Patterns

#### For Climate Impact Studies
- Compare RCP 4.5 (scenario LM) vs RCP 8.5 (scenarios HL, HM, HH)
- Use all five climate models to capture precipitation uncertainty

#### For Socioeconomic Analysis
- Compare high growth (HH) vs low growth (HL) scenarios
- Use middle scenarios (LM, HM) for moderate projections

#### For Integrated Assessment
- Present all four scenarios to show full uncertainty range
- Highlight scenario LM as "best case" and HL as "challenging case"

## Data Structure in Database

In our DuckDB database, scenarios are structured as:

```sql
-- Scenario naming convention
-- Format: {ClimateModel}_{RCP}_ssp{SSP}
-- Example: CNRM_CM5_rcp45_ssp1 (Wet climate, lower warming, sustainability)

-- The 20 scenarios in our database combine:
-- 5 climate models × 2 RCPs × variable SSPs = 20 total scenarios

-- Scenario components:
-- Climate models: CNRM_CM5, HadGEM2_ES365, IPSL_CM5A_MR, MRI_CGCM3, NorESM1_M
-- RCPs: rcp45, rcp85
-- SSPs: ssp1, ssp2, ssp3, ssp5
```

## References

- U.S. Department of Agriculture, Forest Service. 2023. Future Scenarios. Chapter 3 in: Future of America's Forest and Rangelands: Forest Service 2020 Resources Planning Act Assessment. Gen. Tech. Rep. WO-102. Washington, DC.
- O'Dea, C.B.; Langner, L.L.; Joyce, L.A.; Prestemon, J.P.; Wear, D.N. 2023. Future Scenarios. https://doi.org/10.2737/WO-GTR-102-Chap3