# Climate Models in the RPA Assessment

## Overview

The 2020 RPA Assessment uses 5 carefully selected Global Climate Models (GCMs) to capture the range of possible future climate conditions across the United States. These models were chosen to represent different combinations of temperature and precipitation patterns.

## The Five Climate Models

### CNRM_CM5 - "Wet" Model
- **Full Name**: Centre National de Recherches Météorologiques Climate Model 5
- **Origin**: France
- **Key Characteristic**: Projects increased precipitation across most of the US
- **Temperature Pattern**: Moderate warming
- **Best For**: Analyzing scenarios with higher water availability

### HadGEM2_ES365 - "Hot" Model
- **Full Name**: Hadley Centre Global Environmental Model 2 - Earth System
- **Origin**: United Kingdom
- **Key Characteristic**: Represents the upper bound of temperature increases
- **Temperature Pattern**: Highest warming projections
- **Best For**: Stress-testing under extreme heat scenarios

### IPSL_CM5A_MR - "Dry" Model
- **Full Name**: Institut Pierre Simon Laplace Climate Model 5A - Medium Resolution
- **Origin**: France
- **Key Characteristic**: Projects reduced precipitation in many regions
- **Temperature Pattern**: Moderate to high warming
- **Best For**: Analyzing drought and water scarcity impacts

### MRI_CGCM3 - "Least Warm" Model
- **Full Name**: Meteorological Research Institute Coupled Global Climate Model 3
- **Origin**: Japan
- **Key Characteristic**: Most conservative temperature projections
- **Temperature Pattern**: Lower bound of warming
- **Best For**: Best-case climate scenarios

### NorESM1_M - "Middle" Model
- **Full Name**: Norwegian Earth System Model 1 - Medium Resolution
- **Origin**: Norway
- **Key Characteristic**: Represents central tendency of climate projections
- **Temperature Pattern**: Median warming and precipitation
- **Best For**: Most likely/average climate outcomes

## Model Selection Rationale

The RPA Assessment team selected these models to:
1. **Capture uncertainty** - Range from wet to dry, hot to least warm
2. **Represent extremes** - Include both upper and lower bounds
3. **Include central tendency** - Middle model for most likely outcomes
4. **Geographic coverage** - Models perform well across US regions

## Using Climate Models in Analysis

### Comparing Models
When analyzing RPA data, you can:
- Compare outcomes across all 5 models to see the full range
- Focus on extremes (Hot vs Least Warm, Wet vs Dry)
- Use the Middle model for typical projections

### Example Queries
```
"Compare forest loss between the wet and dry climate models"
"Which climate model shows the most agricultural stress?"
"Show urban expansion under the hot climate model"
```

### Interpreting Results
- **Wet model** results suggest impacts under increased precipitation
- **Dry model** results indicate drought stress responses
- **Hot model** shows maximum temperature stress
- **Least warm** provides conservative estimates
- **Middle model** offers balanced projections

## Climate Pathways (RCPs)

Each climate model runs under two Representative Concentration Pathways:

### RCP4.5 - Lower Emissions
- Global warming of approximately 2.5°C by 2100
- Assumes significant emissions reductions
- More optimistic climate future

### RCP8.5 - Higher Emissions
- Global warming of approximately 4.5°C by 2100
- Assumes continued high emissions
- More pessimistic climate future

## Model × Scenario Matrix

Each of the 5 climate models is combined with 4 RPA scenarios:
- 5 climate models × 4 scenarios = 20 total projections
- Allows analysis of climate-socioeconomic interactions
- Captures full range of plausible futures

## Technical Notes

- Models downscaled to county-level resolution
- Bias-corrected for regional accuracy
- Validated against historical observations
- Updated from CMIP5 ensemble