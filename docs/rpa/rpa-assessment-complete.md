# Complete RPA Assessment Reference

Welcome to the comprehensive guide for understanding the USDA Forest Service's 2020 Resources Planning Act (RPA) Assessment. This guide provides complete documentation of the methodology, scenarios, climate models, and data structure that underlies the RPA land use projections from 2020 to 2100.

## Table of Contents

1. [RPA Assessment Overview](#rpa-assessment-overview)
2. [Land Use Change Methodology](#land-use-change-methodology)
3. [Climate Models and Projections](#climate-models-and-projections)
4. [Integrated Scenarios Framework](#integrated-scenarios-framework)
5. [Data Structure and Usage](#data-structure-and-usage)
6. [Analysis Guidelines](#analysis-guidelines)

## RPA Assessment Overview

### About the 2020 Resources Planning Act Assessment

The USDA Forest Service's 2020 Resources Planning Act (RPA) Assessment provides comprehensive projections of land use change across the United States through 2100. This assessment is mandated by the Forest and Rangeland Renewable Resources Planning Act of 1974, which requires periodic evaluations of the Nation's renewable resources.

### Assessment Scope and Coverage

#### Geographic Coverage
- **3,075 US counties** - Complete coverage of the conterminous United States
- **County-level resolution** - Maintains local geographic detail for analysis
- **Private land focus** - Public lands are assumed to remain static

#### Temporal Coverage
- **Base period**: 2012-2020 (calibration period)
- **Projection periods**: 2020-2030, 2030-2040, 2040-2050, 2050-2070, 2070-2090, 2090-2100
- **Total timespan**: Nearly 90 years of land use evolution

#### Land Use Categories
The assessment tracks **5 major land use categories**:

| Code | Land Use | Category | Description |
|------|----------|----------|-------------|
| **cr** | Crop | Agriculture | Agricultural cropland for food, feed, and fiber |
| **ps** | Pasture | Agriculture | Livestock grazing land and hay production |
| **fr** | Forest | Natural | Forested areas including timberland and woodland |
| **ur** | Urban | Developed | Built and developed areas including residential, commercial, and infrastructure |
| **rg** | Rangeland | Natural | Natural grasslands and shrublands |

### Integrated Scenario Framework

The assessment employs **20 integrated climate-socioeconomic scenarios** to capture uncertainty:

- **4 scenario combinations** (LM, HL, HM, HH) representing different development pathways
- **5 climate models** representing diverse precipitation and temperature patterns
- **2 climate pathways** (RCP4.5 lower emissions, RCP8.5 higher emissions)
- **4 socioeconomic pathways** (SSP1, SSP2, SSP3, SSP5) representing different growth patterns

### Key Data Sources

#### Primary Data Sources
- **National Resources Inventory (NRI)** - Historical land use observations from 2001-2012
- **Global Climate Models** - Temperature and precipitation projections from 5 selected GCMs
- **Socioeconomic Projections** - Population and economic growth scenarios from SSPs
- **Geographic Data** - County boundaries and land ownership patterns

#### Model Outputs
- **Transition matrices** - Detailed acre-by-acre changes between land use categories
- **Scenario variations** - Results for all 20 integrated climate-socioeconomic scenarios
- **Temporal resolution** - Decadal projections enabling trend analysis
- **Spatial detail** - County-level granularity for local and regional analysis

## Land Use Change Methodology

### Econometric Model Foundation

The RPA land use projections are based on a sophisticated econometric model that projects county-level land use transitions from 2020 to 2100. The model represents a significant advance in land use change modeling, incorporating climate, socioeconomic, and historical factors.

#### Core Model Characteristics
- **Spatial Resolution**: County-level analysis for 3,075 counties in the conterminous United States
- **Temporal Coverage**: Decadal projections from 2020 to 2100
- **Land Ownership Focus**: Private land only (public lands assumed static)
- **Scenario Integration**: 20 integrated climate-socioeconomic futures
- **Policy Approach**: Policy-neutral projections based on historical relationships

### Fundamental Model Assumptions

#### 1. Development Irreversibility
**Key Principle**: Once land converts to developed (urban) use, it does not revert to other uses.

**Rationale**: Based on observed patterns where urban development represents a permanent change in land use. This reflects the high cost and practical difficulty of converting developed areas back to agricultural or natural uses.

**Implications**: 
- Urban areas can only increase or remain stable over time
- All urbanization comes from conversion of agricultural or natural lands
- Development pressure is a one-way driver of land use change

#### 2. Private Land Focus
**Key Principle**: All land use transitions occur on privately owned land.

**Rationale**: Public lands (federal, state, local) are managed under different objectives and constraints, making them less responsive to market-driven land use pressures.

**Implications**:
- Model excludes approximately 30% of total U.S. land area
- Focus on lands most subject to economic development pressures
- Results represent the subset of land where transitions are most likely

#### 3. Historical Calibration
**Key Principle**: Model calibrated using observed transitions from 2001-2012 National Resources Inventory data.

**Rationale**: Past land use change patterns provide the best available evidence for understanding drivers and rates of future change.

**Implications**:
- Future transitions follow historically observed relationships
- Model captures regional variations in transition propensities
- Assumes basic economic and social drivers remain consistent

#### 4. Policy Neutrality
**Key Principle**: No assumptions about future conservation policies or land use regulations.

**Rationale**: Policy-neutral projections provide a baseline against which policy alternatives can be evaluated.

**Implications**:
- Results show market-driven outcomes without policy intervention
- Useful for assessing potential policy impacts
- May overestimate conversion pressures where policies provide protection

### Historical Context and Calibration

#### Development Trends Over Time
The model calibration period (2001-2012) captured important trends:

- **1980s baseline**: ~1.2 million acres per year converted to developed uses
- **1990s expansion**: Peak development around 1992-1997 at ~2.0 million acres per year
- **2000s moderation**: Declining development rates reflected in model calibration
- **Post-recession patterns**: Model captures more moderate growth expectations

#### Observed Transition Patterns (2001-2012)
**Most Active Transitions**:
- **Crop ↔ Pasture**: Frequent conversions representing agricultural land management decisions
- **Forest → Urban**: Primary pathway for urbanization and development
- **Agricultural → Urban**: Secondary pathway, especially near existing developed areas

**Regional Variations**:
- **South**: Highest absolute forest-to-urban conversion
- **West**: Rangeland-to-urban conversions in arid regions  
- **Midwest**: Agricultural-to-urban conversions near metropolitan areas
- **Northeast**: Forest-to-urban in suburban expansion areas

### Projection Methodology

#### Econometric Model Structure

**1. Transition Probability Modeling**
The model calculates the probability of each land use transition based on:
- **Historical transition rates** by county and land use type
- **Climate variables** (temperature and precipitation changes)
- **Socioeconomic factors** (population growth, economic development)
- **Land quality indicators** (soil productivity, terrain characteristics)
- **Spatial factors** (proximity to existing development, transportation access)

**2. Constraint Application**
Physical and logical constraints ensure realistic projections:
- **Area conservation**: Total county land area remains constant
- **Development irreversibility**: Urban land cannot convert to other uses
- **Transition realism**: Changes follow observed historical patterns
- **Capacity limits**: Maximum feasible transition rates based on historical data

**3. Temporal Projection Process**
For each time period (decade), the model:
1. Calculates transition probabilities based on projected conditions
2. Applies constraints to ensure realistic outcomes
3. Generates land use areas for each category
4. Feeds results forward as initial conditions for next period

#### Climate Integration Process

**Temperature Effects**:
- Higher temperatures can reduce agricultural productivity
- Extreme heat may limit development attractiveness in some regions
- Temperature stress affects forest growth and survival

**Precipitation Effects**:
- Drought conditions increase pressure for agricultural land conversion
- Excessive precipitation can limit development in flood-prone areas
- Water availability affects regional growth patterns

**Regional Climate Impacts**:
Different climate models project varying regional effects:
- **Southwest**: Increased drought stress on agriculture and forests
- **Southeast**: Higher temperature stress on all land uses
- **Great Plains**: Variable precipitation affects agricultural viability
- **Pacific Northwest**: Temperature increases affect forest composition

#### Socioeconomic Driver Integration

**Population Growth Effects**:
- Higher population creates demand for housing and urban services
- Regional population shifts drive spatial patterns of development
- Demographic changes affect agricultural labor availability

**Economic Growth Effects**:
- GDP growth increases demand for commercial and industrial land
- Economic prosperity enables development in previously marginal areas
- Income growth affects housing preferences and suburban expansion

**Technology and Development Patterns**:
- Different SSP scenarios assume different development technologies
- Infrastructure investments affect development feasibility
- Transportation patterns influence spatial development

### Key National Projections (2020-2100)

#### Developed Land Expansion
**Range Across Scenarios**: +41.3 to +57.0 million acres (2020-2070)
- **Scenario HL** (Low Growth): +41.3 million acres - most conservative expansion
- **Scenario HH** (High Growth): +57.0 million acres - maximum development pressure
- **Rate of Change**: 0.8 to 1.1 million acres per year nationally

#### Forest Land Changes
**Range Across Scenarios**: -7.6 to -15.0 million acres (2020-2070)
- **Primary Driver**: ~46% of new developed land comes from forest conversion
- **Regional Concentration**: Largest losses in South and Pacific Coast regions
- **Conservation Potential**: Scenario LM shows smallest forest losses

#### Agricultural Land Dynamics
**Variable Outcomes by Scenario**:
- **Crop vs. Pasture**: Significant shifts between cropping systems
- **Regional Specialization**: Some areas intensify agriculture, others convert
- **Climate Sensitivity**: Drought and temperature stress drive conversions

### Regional Development Patterns

#### Highest Development Pressure Regions
**1. South Region**: 18.4-25.0 million acres of new development
- States: Texas, Florida, North Carolina, Georgia, Virginia
- Drivers: Population growth, economic expansion, favorable climate

**2. North Region**: 10.6-14.0 million acres of new development  
- States: Ohio, Michigan, Pennsylvania, New York, Illinois
- Drivers: Urban expansion around major metropolitan areas

**3. Rocky Mountain Region**: 6.4-8.9 million acres of new development
- States: Colorado, Utah, Idaho, Montana, Wyoming
- Drivers: Amenity migration, energy development, population growth

**4. Pacific Coast Region**: 5.9-9.9 million acres of new development
- States: California, Oregon, Washington
- Drivers: Continued urbanization, economic growth, climate migration

#### Forest Loss Concentration
**Largest Losses**: South Region (4.6-9.2 million acres)
- High development pressure combined with extensive private forests
- Conversion for both urban development and agricultural expansion

**Moderate Losses**: Pacific Coast and North regions
- Urban expansion pressures on forested suburban areas
- Climate stress contributing to conversion decisions

**Smallest Losses**: Rocky Mountain Region
- Lower development pressure and more public land

### Scenario-Specific Impacts

#### Climate Pathway Effects (RCP 4.5 vs RCP 8.5)
**Higher Warming (RCP 8.5) Results**:
- **2.4% less developed land expansion** - Climate stress reduces development attractiveness
- **1.2 million acres more forest retention** - Reduced conversion pressure
- **Regional variations** - Stronger effects in already hot/dry regions

#### Socioeconomic Pathway Effects
**Higher Growth (SSP5 vs SSP3) Results**:
- **9.4% more developed land expansion** - Economic pressure drives conversion
- **3.5 million acres less forest** - Development pressure overcomes conservation
- **Accelerated urbanization** - Faster rates of land use change

## Climate Models and Projections

### Overview of Climate Model Selection

The 2020 RPA Assessment uses 5 carefully selected Global Climate Models (GCMs) to capture the range of possible future climate conditions across the United States. These models were chosen through a rigorous selection process to represent different combinations of temperature and precipitation patterns while ensuring good performance across U.S. regions.

### The Five Core Climate Models

#### CNRM_CM5 - "Wet" Climate Model
**Full Name**: Centre National de Recherches Météorologiques Climate Model 5
- **Origin**: Météo-France, Centre National de Recherches Météorologiques, France
- **Key Characteristic**: Projects increased precipitation across most of the United States
- **Temperature Pattern**: Moderate warming trajectory with regional variations
- **Precipitation Pattern**: Above-average precipitation in most regions
- **Best Used For**: 
  - Analyzing scenarios with higher water availability
  - Assessing land use under reduced drought stress
  - Evaluating agricultural productivity under favorable moisture conditions

#### HadGEM2_ES365 - "Hot" Climate Model
**Full Name**: Hadley Centre Global Environmental Model 2 - Earth System (365-day calendar)
- **Origin**: Met Office Hadley Centre, United Kingdom
- **Key Characteristic**: Represents the upper bound of temperature increases
- **Temperature Pattern**: Highest warming projections among the five models
- **Precipitation Pattern**: Variable, with some regions experiencing reduced precipitation
- **Best Used For**:
  - Stress-testing land use systems under extreme heat scenarios
  - Analyzing agricultural vulnerability to temperature extremes
  - Assessing maximum development pressure under climate stress

#### IPSL_CM5A_MR - "Dry" Climate Model
**Full Name**: Institut Pierre Simon Laplace Climate Model 5A - Medium Resolution
- **Origin**: Institut Pierre Simon Laplace, France
- **Key Characteristic**: Projects reduced precipitation in many U.S. regions
- **Temperature Pattern**: Moderate to high warming with regional variations
- **Precipitation Pattern**: Below-average precipitation, increased drought risk
- **Best Used For**:
  - Analyzing drought and water scarcity impacts on land use
  - Assessing agricultural stress and potential abandonment
  - Evaluating forest vulnerability to moisture stress

#### MRI_CGCM3 - "Least Warm" Climate Model
**Full Name**: Meteorological Research Institute Coupled Global Climate Model 3
- **Origin**: Meteorological Research Institute, Japan
- **Key Characteristic**: Most conservative temperature projections
- **Temperature Pattern**: Lower bound of warming among the five models
- **Precipitation Pattern**: Moderate changes with regional variations
- **Best Used For**:
  - Best-case climate scenarios and conservative projections
  - Minimum climate stress assessments
  - Baseline comparisons for climate impact analysis

#### NorESM1_M - "Middle" Climate Model
**Full Name**: Norwegian Earth System Model 1 - Medium Resolution
- **Origin**: Norwegian Climate Centre, Norway
- **Key Characteristic**: Represents central tendency of climate projections
- **Temperature Pattern**: Median warming and precipitation changes
- **Precipitation Pattern**: Balanced regional increases and decreases
- **Best Used For**:
  - Most likely/average climate outcomes
  - Central estimates for planning purposes
  - Balanced projections across regions

### Climate Model Selection Rationale

#### Scientific Criteria
The RPA Assessment team selected these models based on:

**1. Uncertainty Representation**
- **Temperature range**: From conservative (Least Warm) to extreme (Hot)
- **Precipitation range**: From dry conditions (Dry) to wet conditions (Wet)
- **Central tendency**: Middle model represents most likely outcomes

**2. Geographic Performance**
- Models evaluated for accuracy across U.S. climate regions
- Regional biases corrected through statistical downscaling
- Performance validated against historical observations

**3. Complementary Characteristics**
- Each model captures different aspects of climate uncertainty
- Combined ensemble provides comprehensive range of possibilities
- Models selected to avoid redundancy while maximizing coverage

#### Model Ensemble Benefits
Using five diverse climate models provides:
- **Robust uncertainty quantification** - Full range of plausible climate futures
- **Regional specificity** - Different models perform better in different regions
- **Extreme scenario coverage** - Both optimistic and pessimistic climate futures
- **Policy-relevant ranges** - Bounded estimates for decision-making

### Climate Pathways (Representative Concentration Pathways)

Each climate model runs under two Representative Concentration Pathways (RCPs) representing different greenhouse gas emission trajectories:

#### RCP4.5 - Lower Emissions Pathway
**Emission Trajectory**: Emissions peak around 2040, then decline
- **Global warming**: Approximately 2.5°C increase by 2100
- **Policy assumptions**: Significant global emissions reductions implemented
- **Radiative forcing**: Moderate forcing scenario with stabilization
- **Climate outcomes**: More optimistic climate future with managed warming
- **Land use implications**: Reduced climate stress on agriculture and forests

#### RCP8.5 - Higher Emissions Pathway  
**Emission Trajectory**: Continued high emissions growth through 2100
- **Global warming**: Approximately 4.5°C increase by 2100
- **Policy assumptions**: Limited climate action, continued fossil fuel dependence
- **Radiative forcing**: High forcing scenario with continued acceleration
- **Climate outcomes**: More pessimistic climate future with severe warming
- **Land use implications**: Increased climate stress, potential land abandonment

### Using Climate Models in RPA Analysis

#### Comparative Analysis Strategies

**1. Cross-Model Comparisons**
```
"Compare forest loss between the wet and dry climate models"
"Which climate model shows the most agricultural stress?"
"Show urban expansion differences across all five climate models"
```

**2. Extreme Scenario Analysis**
```
"Contrast outcomes between the hot and least warm models"
"Show maximum climate impact using the dry-hot combination"
"What's the best-case scenario using the wet-least warm combination?"
```

**3. Central Tendency Analysis**
```
"Use the middle climate model for typical projections"
"Show average outcomes across all climate models"
"What does the middle model suggest for forest conservation?"
```

#### Interpreting Climate Model Results

**Wet Model Results** suggest:
- Impacts under increased precipitation and water availability
- Reduced drought stress on agriculture and forests
- Potential for increased agricultural productivity
- Lower wildfire risk in many regions

**Dry Model Results** indicate:
- Drought stress responses and water scarcity impacts
- Agricultural vulnerability and potential abandonment
- Increased pressure for land use conversion
- Higher wildfire risk and forest stress

**Hot Model Results** show:
- Maximum temperature stress on all land use systems
- Agricultural heat stress and reduced productivity
- Urban heat island effects limiting development appeal
- Forest mortality and composition changes

**Least Warm Model Results** provide:
- Conservative estimates with minimal climate stress
- Best-case agricultural and forest outcomes
- Reduced pressure for climate-driven land conversion
- Baseline for comparing climate impacts

**Middle Model Results** offer:
- Balanced projections representing most likely outcomes
- Central estimates for planning and policy analysis
- Moderate climate stress across land use systems
- Representative outcomes for typical conditions

### Technical Implementation

#### Downscaling and Bias Correction
**Spatial Downscaling**: Global climate model outputs downscaled to county-level resolution using:
- Statistical downscaling methods
- Regional climate model integration  
- Topographic and local climate factor adjustment

**Bias Correction**: Model outputs adjusted for:
- Historical bias relative to observations
- Regional systematic errors
- Seasonal and temporal bias patterns

#### Validation and Quality Control
**Historical Validation**: Models validated against:
- 20th century temperature and precipitation observations
- Regional climate patterns and variability
- Extreme event frequency and intensity

**Cross-Model Consistency**: Ensemble checked for:
- Reasonable spread across models
- Consistent regional patterns
- Physical plausibility of projections

## Integrated Scenarios Framework

### Overview of the Four RPA Scenarios

The 2020 RPA Assessment employs four integrated scenarios that combine climate pathways (RCPs) with socioeconomic pathways (SSPs) to explore alternative futures and provide a comprehensive framework for evaluating natural resource outcomes through 2100.

#### Quick Reference: The Four Core Scenarios

| Scenario | Full Name | Climate | Socioeconomic | Development Theme |
|----------|-----------|---------|---------------|-------------------|
| **LM** | Lower warming-Moderate growth | RCP 4.5 | SSP1 | "Taking the Green Road" |
| **HL** | High warming-Low growth | RCP 8.5 | SSP3 | "A Rocky Road" |
| **HM** | High warming-Moderate growth | RCP 8.5 | SSP2 | "Middle of the Road" |
| **HH** | High warming-High growth | RCP 8.5 | SSP5 | "Taking the Highway" |

### Detailed Scenario Descriptions

#### Scenario LM: Lower Warming-Moderate U.S. Growth (RCP 4.5-SSP1)
**Development Theme**: "Taking the Green Road"

**Climate Characteristics**:
- **Emission pathway**: Lower emissions with peak around 2040
- **Global warming**: Moderate warming (~2.5°C by 2100)
- **Policy context**: Strong international cooperation on climate action
- **Environmental impacts**: Managed climate change with adaptation measures

**Socioeconomic Characteristics**:
- **U.S. Economic Growth**: 3.0X GDP expansion by 2070
- **U.S. Population Growth**: 1.5X increase to ~470 million by 2070
- **Development pattern**: Sustainable development prioritized
- **Technology focus**: Renewable energy transition and efficiency
- **International relations**: Strong global cooperation and coordination

**Key Features**:
- Environmental protection prioritized in development decisions
- Sustainable intensification of agriculture
- Green infrastructure and smart growth policies
- Reduced material consumption per capita
- Strong institutions and environmental governance

**Land Use Implications**:
- Moderate development pressure with environmental constraints
- Sustainable agricultural practices and productivity improvements
- Forest conservation prioritized
- Compact urban development patterns

#### Scenario HL: High Warming-Low U.S. Growth (RCP 8.5-SSP3)
**Development Theme**: "A Rocky Road"

**Climate Characteristics**:
- **Emission pathway**: High emissions with continued growth
- **Global warming**: Significant warming (~4.5°C by 2100)
- **Policy context**: Limited international cooperation, regional conflicts
- **Environmental impacts**: Severe climate impacts with limited adaptation

**Socioeconomic Characteristics**:
- **U.S. Economic Growth**: 1.9X GDP expansion by 2070 (slowest growth)
- **U.S. Population Growth**: 1.0X (essentially no net growth, ~330 million by 2070)
- **Development pattern**: Nationalism and regional rivalry
- **Technology focus**: Slow technological progress and adoption
- **International relations**: Trade barriers and security concerns

**Key Features**:
- Material-intensive consumption patterns
- Slow economic development and technological progress
- Resource competition and security concerns
- Adaptation challenges due to limited cooperation
- Unequal development with significant disparities

**Land Use Implications**:
- Lowest development pressure due to slow growth
- Agricultural stress from climate impacts
- Limited conservation resources
- Regional conflicts over land and water resources

#### Scenario HM: High Warming-Moderate U.S. Growth (RCP 8.5-SSP2)
**Development Theme**: "Middle of the Road"

**Climate Characteristics**:
- **Emission pathway**: High emissions with continued growth
- **Global warming**: Significant warming (~4.5°C by 2100)
- **Policy context**: Slow progress on climate action
- **Environmental impacts**: Substantial climate impacts with moderate adaptation

**Socioeconomic Characteristics**:
- **U.S. Economic Growth**: 2.8X GDP expansion by 2070
- **U.S. Population Growth**: 1.4X increase to ~450 million by 2070
- **Development pattern**: Historical trends continue
- **Technology focus**: Moderate technological advancement
- **International relations**: Mixed cooperation and competition

**Key Features**:
- Uneven development across regions and sectors
- Moderate progress on sustainability goals
- Mixed technological adoption and innovation
- Some environmental improvements, some degradation
- Persistent inequality and development challenges

**Land Use Implications**:
- Moderate development pressure
- Mixed agricultural and forest outcomes
- Uneven conservation efforts
- Regional variation in land use stress

#### Scenario HH: High Warming-High U.S. Growth (RCP 8.5-SSP5)
**Development Theme**: "Taking the Highway"

**Climate Characteristics**:
- **Emission pathway**: High emissions with fossil fuel dependence
- **Global warming**: Significant warming (~4.5°C by 2100)
- **Policy context**: Technology-focused but continued high emissions
- **Environmental impacts**: Severe climate impacts with technological solutions

**Socioeconomic Characteristics**:
- **U.S. Economic Growth**: 4.7X GDP expansion by 2070 (highest growth)
- **U.S. Population Growth**: 1.9X increase to ~580 million by 2070
- **Development pattern**: Rapid development and urbanization
- **Technology focus**: High technology adoption and innovation
- **International relations**: Globalization with convergence

**Key Features**:
- Rapid economic growth and technological development
- High energy demand and fossil fuel consumption
- Lifestyle convergence and high consumption
- Urban living and technological solutions
- Energy-intensive adaptation to climate change

**Land Use Implications**:
- Highest development pressure
- Maximum urban expansion
- Agricultural intensification and efficiency
- Technology-driven land management
- Highest competition for land resources

### Understanding RCPs and SSPs Integration

#### Representative Concentration Pathways (RCPs)

**RCP 4.5 - Lower Emissions Pathway**:
- **Radiative forcing**: Medium forcing scenario
- **Emission trajectory**: Peak emissions around 2040, then decline
- **Policy assumptions**: Implementation of climate policies globally
- **Temperature outcome**: ~2.5°C global warming by 2100
- **Used in**: Scenario LM only

**RCP 8.5 - Higher Emissions Pathway**:
- **Radiative forcing**: High forcing scenario
- **Emission trajectory**: Continued high emissions growth through 2100
- **Policy assumptions**: Limited climate action globally
- **Temperature outcome**: ~4.5°C global warming by 2100  
- **Used in**: Scenarios HL, HM, and HH

#### Shared Socioeconomic Pathways (SSPs)

**SSP1 - Sustainability Path**:
- **Theme**: Strong international cooperation and environmental focus
- **Development**: Sustainable development and green growth
- **Population**: Lower population growth and demographic transition
- **Used in**: Scenario LM

**SSP2 - Middle of the Road Path**:
- **Theme**: Uneven progress and mixed development patterns
- **Development**: Historical trends continue with slow progress
- **Population**: Moderate demographic and economic trends
- **Used in**: Scenario HM

**SSP3 - Regional Rivalry Path**:
- **Theme**: Nationalism, security concerns, and regional competition
- **Development**: Slow economic growth and material-intensive consumption
- **Population**: High population growth in some regions, slow economic development
- **Used in**: Scenario HL

**SSP5 - Fossil-fueled Development Path**:
- **Theme**: Rapid economic growth with high energy use
- **Development**: Technological solutions and convergence
- **Population**: Lower population growth but high consumption
- **Used in**: Scenario HH

### Climate Model Integration

Each scenario is implemented with all five climate models (Wet, Hot, Dry, Least Warm, Middle), creating the full matrix of **20 total projections**:

- **5 climate models** × **4 scenarios** = **20 integrated projections**
- Each projection represents a unique combination of climate and socioeconomic futures
- Full ensemble captures range of climate-socioeconomic interactions

#### Example Climate-Scenario Combinations
- **LM-Wet**: Sustainable development with increased precipitation
- **HH-Hot**: High growth development under extreme warming
- **HL-Dry**: Low growth with drought stress
- **HM-Middle**: Moderate development under typical climate change

### Land Use Implications by Scenario

#### Development Pressure Ranking
**1. Highest Pressure - Scenario HH** (High Growth):
- Maximum population and economic growth
- Highest demand for urban and infrastructure development
- Greatest competition for land resources
- Technology-enabled development in marginal areas

**2. Moderate Pressure - Scenarios LM and HM**:
- **LM**: Sustainable development approaches moderate pressure
- **HM**: Historical trend continuation with moderate growth
- Balanced development with some environmental consideration

**3. Lowest Pressure - Scenario HL** (Low Growth):
- Slow economic growth limits development demand
- Regional conflicts constrain large-scale development
- Limited resources for major land conversion projects
- Climate stress without adaptation resources

#### Agricultural Land Dynamics

**Most Severe Agricultural Pressure**:
- **Scenario HH**: High development pressure competes with agriculture
- **Climate stress**: All RCP 8.5 scenarios face significant agricultural challenges
- **Technology response**: HH assumes technological solutions to agricultural stress

**Moderate Agricultural Outcomes**:
- **Scenario LM**: Sustainable intensification maintains agricultural productivity
- **Scenario HM**: Mixed outcomes with some regions improving, others declining

**Challenging Agricultural Conditions**:
- **Scenario HL**: Climate stress without adequate adaptation resources
- Limited technological and economic capacity for agricultural adaptation

#### Forest Conservation Outcomes

**Best Forest Conservation**:
- **Scenario LM**: Environmental priorities and sustainable development
- Lower development pressure combined with conservation focus
- Climate change impacts managed through adaptation

**Variable Forest Outcomes**:
- **Scenarios HL and HM**: Depend heavily on regional factors and climate model
- HL: Low pressure but limited conservation resources
- HM: Moderate pressure with mixed conservation efforts

**Highest Forest Pressure**:
- **Scenario HH**: Maximum development pressure on forest lands
- High population and economic growth drive conversion
- Technology may enable development in previously protected areas

### Using Scenarios in Analysis

#### Time Horizon Considerations

**Near-term (2020-2030)**:
- **Limited divergence**: All scenarios show similar patterns
- **Initial conditions dominate**: Historical trends continue
- **Policy lag effects**: New policies haven't yet influenced outcomes

**Mid-term (2030-2050)**:
- **Increasing differentiation**: Scenario effects become apparent
- **Climate impacts emerge**: Regional climate differences become significant
- **Development patterns diverge**: Different growth trajectories evident

**Long-term (2050-2100)**:
- **Maximum scenario divergence**: Full range of uncertainty apparent
- **Cumulative impacts**: Long-term trends dominate outcomes
- **System interactions**: Complex feedbacks between climate and development

#### Analysis Best Practices

**1. Always Specify Scenario Context**
- Include scenario name (LM, HL, HM, HH) in all presentations
- Specify climate model when relevant (e.g., "HH-Hot", "LM-Wet")
- Provide scenario context for non-technical audiences

**2. Use Appropriate Scenario Comparisons**
- **Climate impact studies**: Compare RCP 4.5 (LM) vs RCP 8.5 (HL, HM, HH)
- **Socioeconomic analysis**: Compare high growth (HH) vs low growth (HL)
- **Uncertainty assessment**: Present all four scenarios

**3. Consider Averaging Strategies**
- **General trends**: Average across all scenarios for overall patterns
- **Robust findings**: Identify results consistent across scenarios
- **Uncertainty ranges**: Present minimum and maximum across scenarios

**4. Scenario-Specific Applications**
- **Planning applications**: Use scenario most relevant to planning context
- **Risk assessment**: Focus on challenging scenarios (HL, HH under extreme climate)
- **Opportunity assessment**: Highlight beneficial scenarios (LM under favorable climate)

### Common Analysis Patterns

#### For Climate Impact Studies
```
"Compare RCP 4.5 vs RCP 8.5 scenarios across all socioeconomic pathways"
"Show climate model sensitivity within the HH scenario"
"Assess forest vulnerability under the Hot-Dry climate combination"
```

#### For Socioeconomic Analysis
```
"Compare high growth (HH) vs low growth (HL) under the same climate conditions"
"Show development pressure differences between sustainability (LM) and rivalry (HL) scenarios"
"Analyze agricultural outcomes under different economic growth patterns"
```

#### For Integrated Assessment
```
"Present land use outcomes for all four scenarios to show full uncertainty range"
"Identify robust findings that appear across all scenarios"
"Highlight scenario-dependent outcomes that require adaptive management"
```

## Data Structure and Usage

### Database Architecture

The RPA land use data is stored in a modern DuckDB database using a **star schema design** optimized for analytical queries and natural language processing.

#### Fact Table: `fact_landuse_transitions`
**Purpose**: Core table containing all land use transition records
**Records**: 5.4+ million transition records
**Structure**: Each record represents a specific transition for a unique combination of:

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | INTEGER | Links to scenario dimension table |
| `time_id` | INTEGER | Links to time period dimension table |
| `geography_id` | INTEGER | Links to county geography dimension table |
| `from_landuse_id` | INTEGER | Source land use type |
| `to_landuse_id` | INTEGER | Destination land use type |
| `acres` | REAL | Area (in acres) undergoing this transition |

#### Dimension Tables

**`dim_scenario`** - Scenario definitions (20 records)
- Scenario names, descriptions, RCP/SSP combinations
- Climate model information and scenario themes

**`dim_geography`** - County information (3,075 records)  
- County names, FIPS codes, state information
- Geographic metadata and regional classifications

**`dim_landuse`** - Land use categories (5 records)
- Land use codes, names, descriptions, and categories
- Hierarchical groupings (Agricultural, Natural, Developed)

**`dim_time`** - Time periods (6 records)
- Time period definitions and year ranges
- Start/end years for each projection period

#### Pre-built Views for Analysis

**`v_landuse_with_metadata`** - Complete denormalized view
- Joins all dimension tables with fact table
- Includes human-readable names for all dimensions
- Primary view for most natural language queries

**`v_landuse_summary`** - Pre-aggregated summaries
- Common aggregations by scenario, time, and geography
- Optimized for dashboard and summary statistics

**`v_scenario_comparison`** - Cross-scenario analysis
- Structured for comparing outcomes across scenarios
- Includes variance and range calculations

### Scenario Naming Convention in Database

The database uses a systematic naming convention for the 20 scenarios:

#### Format: `{ClimateModel}_{RCP}_ssp{SSP}`

**Examples**:
- `CNRM_CM5_rcp45_ssp1` - Wet climate, lower warming, sustainability path (LM scenario)
- `HadGEM2_ES365_rcp85_ssp5` - Hot climate, higher warming, fossil-fueled development (HH scenario)
- `IPSL_CM5A_MR_rcp85_ssp3` - Dry climate, higher warming, regional rivalry (HL scenario)

#### Climate Model Components
- **CNRM_CM5** - Wet climate projections
- **HadGEM2_ES365** - Hot climate projections  
- **IPSL_CM5A_MR** - Dry climate projections
- **MRI_CGCM3** - Least warm climate projections
- **NorESM1_M** - Middle climate projections

#### RCP Components
- **rcp45** - Lower emissions pathway (2.5°C warming)
- **rcp85** - Higher emissions pathway (4.5°C warming)

#### SSP Components
- **ssp1** - Sustainability pathway (green growth)
- **ssp2** - Middle of the road pathway (historical trends)
- **ssp3** - Regional rivalry pathway (nationalism, slow growth)
- **ssp5** - Fossil-fueled development pathway (rapid growth)

### Data Analysis Patterns

#### Common Aggregation Strategies

**By Scenario** - Compare climate/socioeconomic pathways:
```sql
SELECT scenario_name, SUM(acres) as total_forest_loss
FROM v_landuse_with_metadata  
WHERE from_landuse_name = 'Forest' AND to_landuse_name != 'Forest'
GROUP BY scenario_name;
```

**By Time Period** - Track temporal trends:
```sql
SELECT time_period, SUM(acres) as urban_expansion  
FROM v_landuse_with_metadata
WHERE to_landuse_name = 'Urban' 
GROUP BY time_period ORDER BY time_period;
```

**By Geography** - State or regional patterns:
```sql
SELECT state_name, AVG(acres) as avg_agricultural_loss
FROM v_landuse_with_metadata
WHERE from_landuse_category = 'Agriculture' AND to_landuse_category != 'Agriculture'
GROUP BY state_name;
```

**By Transition Type** - Focus on specific conversions:
```sql
SELECT from_landuse_name, to_landuse_name, SUM(acres) as total_conversion
FROM v_landuse_with_metadata
WHERE from_landuse_name != to_landuse_name  -- Actual transitions only
GROUP BY from_landuse_name, to_landuse_name
ORDER BY total_conversion DESC;
```

#### Key Analysis Considerations

**1. Transition vs. Same Records**
- **Transition records**: `from_landuse_id != to_landuse_id` (actual land use changes)
- **Same records**: `from_landuse_id = to_landuse_id` (land remaining in same use)
- **Focus on transitions** for most change analyses

**2. Scenario Averaging**
When not comparing scenarios specifically:
```sql
-- Average across all scenarios for general trends
SELECT geography_name, AVG(acres) as avg_forest_loss
FROM v_landuse_with_metadata  
WHERE from_landuse_name = 'Forest' AND to_landuse_name != 'Forest'
GROUP BY geography_name;
```

**3. Scale Considerations**
- **National patterns** may obscure important regional variations
- **County-level detail** provides local specificity but can be noisy
- **State/regional aggregation** often provides appropriate balance

### Important Analysis Guidelines

#### When Analyzing RPA Data

**1. Default to Appropriate Averages**
- When not specifically comparing scenarios, average across relevant scenarios
- Consider whether climate model variation or socioeconomic variation is of interest
- Use all 20 scenarios for maximum uncertainty assessment

**2. Focus on Meaningful Changes**
- Use transition records (`from_landuse_id != to_landuse_id`) for change analysis
- Same-to-same records useful for understanding land use stability
- Consider both absolute changes (acres) and relative changes (percentages)

**3. Understand Temporal Patterns**
- Early periods (2020-2030) show less scenario divergence
- Later periods (2070-2100) show maximum scenario effects
- Cumulative changes often more meaningful than period-by-period changes

**4. Remember Model Constraints**
- Development is irreversible in projections
- Only private land undergoes transitions
- Historical relationships assumed to continue

#### Common Query Patterns for Natural Language Interface

**Exploring Available Data**:
```
"What scenarios are available in the database?"
"Show me the land use categories and their descriptions"
"Which time periods does the data cover?"
```

**Basic Transition Analysis**:
```
"Show forest to urban transitions by scenario"
"What land uses convert to agricultural land?"
"Calculate total urban expansion across all scenarios"
```

**Scenario Comparisons**:
```
"Compare agricultural land loss between high growth and low growth scenarios"
"Show forest conservation differences between RCP 4.5 and RCP 8.5"
"Which scenario preserves the most natural land?"
```

**Geographic Analysis**:
```
"Show urban expansion by state"
"Which counties have the most forest loss?"
"Compare land use changes between regions"
```

**Temporal Analysis**:
```
"Track forest area changes over time"
"When does urban area expansion peak?"
"Show agricultural trends by decade"
```

### Data Quality and Validation

#### Built-in Data Checks
The database includes several validation mechanisms:

**Area Conservation**: Total county area remains constant across time periods
```sql
-- Verify area conservation by county and time
SELECT geography_id, time_id, SUM(acres) as total_area
FROM fact_landuse_transitions  
GROUP BY geography_id, time_id;
```

**Transition Completeness**: All land accounted for in transitions
```sql  
-- Check that from_landuse totals match to_landuse totals
SELECT time_id, scenario_id,
       SUM(CASE WHEN from_landuse_id = 1 THEN acres ELSE 0 END) as from_crop,
       SUM(CASE WHEN to_landuse_id = 1 THEN acres ELSE 0 END) as to_crop
FROM fact_landuse_transitions
GROUP BY time_id, scenario_id;
```

**Scenario Consistency**: All scenarios include same geographic and temporal coverage
```sql
-- Verify consistent coverage across scenarios  
SELECT scenario_id, COUNT(DISTINCT geography_id) as counties,
       COUNT(DISTINCT time_id) as time_periods
FROM fact_landuse_transitions
GROUP BY scenario_id;
```

## Analysis Guidelines

### Choosing Appropriate Analysis Approaches

#### For Climate Impact Studies

**Recommended Approach**: Compare RCP 4.5 vs RCP 8.5 across relevant socioeconomic contexts
```
"Compare forest loss between RCP 4.5 and RCP 8.5 scenarios"
"Show agricultural vulnerability under high warming (RCP 8.5) scenarios"
"Assess urban development under different climate pathways"
```

**Climate Model Sensitivity**: Use all five climate models to capture uncertainty
```
"Show forest loss under wet vs dry climate conditions"
"Compare agricultural outcomes across all five climate models"
"Identify regions most sensitive to climate model choice"
```

#### For Socioeconomic Impact Studies

**Growth Scenario Comparisons**: Focus on SSP differences
```
"Compare land use outcomes between high growth (SSP5) and low growth (SSP3)"
"Show development pressure differences between sustainability (SSP1) and fossil-fueled (SSP5) paths"
"Analyze agricultural intensification under different economic scenarios"
```

**Population and Economic Drivers**:
```
"Which scenario shows highest urban expansion?"
"Compare agricultural land pressure under different demographic scenarios"
"Show relationship between economic growth and forest conversion"
```

#### For Integrated Assessment

**Full Uncertainty Assessment**: Present all scenarios to show complete range
```
"Show land use outcomes for all four scenarios to demonstrate uncertainty"
"Present minimum and maximum forest loss across all scenarios"
"Identify robust findings that appear regardless of scenario choice"
```

**Policy-Relevant Analysis**: Focus on scenario contrasts relevant to policy decisions
```
"Compare outcomes under current trends (HM) vs sustainable development (LM)"
"Show benefits of international cooperation (LM) vs regional rivalry (HL)"
"Assess land use outcomes under different climate policy effectiveness"
```

### Best Practices for Temporal Analysis

#### Understanding Scenario Divergence Over Time

**Near-term (2020-2030)**: 
- **Limited scenario effects** - All scenarios show similar patterns
- **Historical momentum** - Past trends dominate near-term outcomes
- **Useful for**: Short-term planning and policy implementation

**Mid-term (2030-2050)**:
- **Moderate divergence** - Scenario effects become apparent  
- **Policy impacts emerge** - Different pathways start to show effects
- **Useful for**: Strategic planning and infrastructure decisions

**Long-term (2050-2100)**:
- **Maximum divergence** - Full scenario uncertainty apparent
- **Cumulative impacts** - Long-term trends dominate outcomes
- **Useful for**: Long-range planning and climate adaptation

#### Recommended Temporal Analysis Approaches

**Trend Analysis**:
```
"Show forest area trends over time by scenario"
"When do scenarios begin to diverge significantly?"
"Track cumulative urban expansion through 2100"
```

**Rate of Change Analysis**:
```
"Compare rates of agricultural land loss across decades"
"Show acceleration or deceleration of urban expansion"
"Identify periods of most rapid land use change"
```

**Threshold Analysis**:
```
"When does urban area exceed 20% in major metropolitan counties?"
"Identify when forest cover drops below critical thresholds"
"Show when agricultural land loss reaches concerning levels"
```

### Geographic Analysis Guidelines

#### Multi-Scale Analysis Strategies

**National Level**: For broad policy questions and overall trends
```
"Show total U.S. land use changes by scenario"
"Compare national forest conservation across scenarios"
"Calculate total agricultural land at risk"
```

**Regional Level**: For understanding geographic patterns and climate interactions
```
"Compare land use changes between South and Northeast regions"
"Show regional differences in development pressure"
"Analyze climate impacts by major geographic regions"
```

**State Level**: For state policy and planning applications
```
"Rank states by forest loss across scenarios"
"Show agricultural land changes by state"
"Compare development pressure in Western states"
```

**County Level**: For local analysis and detailed spatial patterns
```
"Identify counties with highest urban expansion"
"Show forest loss hotspots at county level"
"Find counties with unusual land use transition patterns"
```

#### Regional Considerations

**South Region**: 
- Highest development pressure
- Most forest-to-urban conversion
- Climate stress on agriculture

**West Region**:
- Water availability constraints
- Rangeland-to-urban transitions
- Climate model sensitivity

**Midwest Region**:
- Agricultural transitions dominate
- Urban expansion around metros
- Less forest conversion

**Northeast Region**:
- Moderate development pressure
- Forest-to-urban in suburban areas
- Climate adaptation challenges

### Validation and Quality Assurance

#### Recommended Validation Checks

**Data Consistency Checks**:
```
"Verify that total county area remains constant over time"
"Check that land use transitions balance (from totals = to totals)"
"Confirm all scenarios have complete geographic coverage"
```

**Reasonableness Checks**:
```
"Identify any counties with unrealistic land use change rates"
"Check for negative land areas or impossible transitions"
"Verify that urban development is irreversible as assumed"
```

**Comparative Validation**:
```
"Compare early projection periods (2020-2030) with recent trends"
"Check scenario outcomes against other national projections"
"Validate regional patterns against known development pressures"
```

#### Interpreting Results

**Understanding Model Limitations**:
- **Private land only**: Results exclude ~30% of total U.S. land area
- **Policy neutral**: No future conservation policies assumed
- **County resolution**: Sub-county patterns not captured
- **Historical basis**: Assumes past relationships continue

**Appropriate Uses**:
- ✅ Scenario comparison and uncertainty assessment
- ✅ Regional and temporal trend analysis  
- ✅ Policy baseline for conservation planning
- ✅ Climate impact assessment

**Inappropriate Uses**:
- ❌ Precise predictions for specific locations
- ❌ Short-term forecasting (use other models)
- ❌ Public land management planning
- ❌ Policy prescriptions without additional analysis

### Integration with RPA Land Use Analytics Tools

#### Using Natural Language Queries

The RPA Land Use Analytics system provides natural language access to this data through:

**Conversational Interface**: Ask questions in plain English
```
"Which scenarios show the most agricultural land loss?"
"Compare forest conservation between climate pathways"
"Show me urbanization patterns in California counties"
```

**Agent Capabilities**: The system automatically:
- Selects appropriate scenarios for your question
- Handles temporal aggregations correctly
- Provides business insights and interpretation
- Generates visualizations when helpful

**Best Practices for Queries**:
- Be specific about scenarios, time periods, and geographic scope
- Ask follow-up questions to explore interesting findings
- Request explanations when results are unexpected
- Use the agent's memory to build complex multi-step analyses

#### Integration with Analysis Workflows

**Dashboard Applications**: Use for summary statistics and KPI monitoring
**Research Projects**: Extract data for detailed academic analysis
**Policy Analysis**: Generate scenarios for policy impact assessment
**Planning Applications**: Inform long-range regional and state planning

## References and Further Reading

### Official RPA Assessment Resources

- **Primary Report**: U.S. Department of Agriculture, Forest Service. 2023. Future of America's Forest and Rangelands: Forest Service 2020 Resources Planning Act Assessment. Gen. Tech. Rep. WO-102. Washington, DC.

- **Land Use Projections**: Mihiar, C.J.; Lewis, D.J.; Coulston, J.W. 2023. Land use projections for the 2020 RPA Assessment. https://doi.org/10.2737/RDS-2023-0026

- **Scenarios Documentation**: O'Dea, C.B.; Langner, L.L.; Joyce, L.A.; Prestemon, J.P.; Wear, D.N. 2023. Future Scenarios. Chapter 3 in: Future of America's Forest and Rangelands: Forest Service 2020 Resources Planning Act Assessment. https://doi.org/10.2737/WO-GTR-102-Chap3

### Online Resources

- **Official RPA Website**: [https://www.fs.usda.gov/research/rpa](https://www.fs.usda.gov/research/rpa)
- **2020 RPA Assessment Report**: [https://www.fs.usda.gov/research/rpa/assessment](https://www.fs.usda.gov/research/rpa/assessment)  
- **Technical Documentation**: [https://www.fs.usda.gov/research/rpa/docs](https://www.fs.usda.gov/research/rpa/docs)

### Related Documentation

#### Within RPA Land Use Analytics System
- **[Complete Agent System Guide](../agents/complete-guide.md)** - Natural language agent configuration and capabilities
- **[Complete Database Reference](../data/complete-reference.md)** - Detailed database schema and technical specifications
- **[Complete Query Guide](../queries/complete-guide.md)** - Natural language query patterns and examples
- **[Complete Setup Guide](../getting-started/complete-setup.md)** - Installation and configuration instructions

#### Cross-References
- **Methodology Details**: See [Complete Database Reference](../data/complete-reference.md) for technical implementation of RPA methodology
- **Query Examples**: See [Complete Query Guide](../queries/complete-guide.md) for examples of analyzing RPA scenarios
- **Agent Configuration**: See [Complete Agent System Guide](../agents/complete-guide.md) for customizing analysis approaches
- **System Architecture**: See [Complete Database Reference](../data/complete-reference.md) for database design and optimization

The 2020 RPA Assessment represents a comprehensive, scientifically rigorous approach to projecting land use change across the United States. By understanding the methodology, scenarios, and data structure described in this guide, users can effectively leverage the RPA Land Use Analytics system to generate insights about future land use patterns and their implications for natural resource management.

## See Also

### Related Documentation
- **[Complete Examples Guide](../examples/complete-examples.md)** - Real-world use cases and workflows demonstrating RPA scenario analysis
- **[Complete Query Guide](../queries/complete-guide.md)** - Natural language query patterns for exploring RPA data and scenarios
- **[Complete Agent Guide](../agents/complete-guide.md)** - Agent configuration for RPA data analysis and interpretation
- **[Complete Database Reference](../data/complete-reference.md)** - Technical implementation of RPA methodology in the database schema
- **[Complete Setup Guide](../getting-started/complete-setup.md)** - Installation and configuration for accessing RPA data

### Quick Navigation by Application
- **Policy Analysis**: See [Complete Examples Guide](../examples/complete-examples.md#policy-analysis-and-government-applications) for government use cases
- **Query Scenarios**: Check [Complete Query Guide](../queries/complete-guide.md#scenario-comparison-queries) for scenario analysis patterns
- **Conservation Planning**: Reference [Complete Examples Guide](../examples/complete-examples.md#conservation-planning-and-biodiversity) for conservation workflows
- **Data Structure**: Learn about [Database Schema](../data/complete-reference.md#star-schema-design) for technical understanding
- **Agent Setup**: Follow [Agent Configuration](../agents/complete-guide.md#configuration) for RPA-specific analysis

> **Consolidation Note**: This guide consolidates information from overview.md, methodology.md, climate-models.md, and scenarios.md into a single comprehensive RPA Assessment reference. For the most current information about RPA methodology and scenarios, always refer to this complete guide rather than individual component files.