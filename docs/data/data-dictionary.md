# Data Dictionary

## Overview

This data dictionary provides comprehensive business definitions, technical specifications, and usage guidelines for all data elements in the RPA Land Use Analytics database.

## Business Context

The database contains land use transition projections from the **2020 USDA Forest Service RPA Assessment**, covering 3,075 US counties across 20 climate scenarios from 2012-2070. All projections focus on **private land only** (public lands assumed static) and include integrated socioeconomic data.

---

## Core Business Concepts

### Land Use Transitions

**Definition**: Changes in land use from one category to another over a specified time period, measured in acres.

**Business Rules**:
- **Irreversible Development**: Once land becomes Urban, it never converts back
- **Private Land Only**: Public lands (national forests, parks) excluded from projections
- **County Aggregation**: Sub-county variations are aggregated to county level
- **Decade Intervals**: Transitions measured over 10-year periods (except 2012-2020: 8 years)

**Key Insights**:
- ~46% of new urban development comes from forest conversion
- Agricultural land conversion varies significantly by economic scenario
- Range to pasture conversions often occur with livestock expansion

### Climate Scenarios

**Definition**: Combinations of climate models with Representative Concentration Pathways (RCP) and Shared Socioeconomic Pathways (SSP).

**Business Context**:
- **Climate Models**: Different climate sensitivities (wet, hot, dry, moderate)
- **RCP Pathways**: Greenhouse gas concentration trajectories
- **SSP Pathways**: Socioeconomic development narratives

---

## Data Elements by Category

### Geographic Identifiers

#### FIPS Code
- **Field Name**: `fips_code`
- **Type**: VARCHAR(5)
- **Definition**: Federal Information Processing Standards county identifier
- **Format**: 5-digit string (SSFFF where SS=state, FFF=county)
- **Business Use**: Unique county identification for data joining and mapping
- **Example**: "06037" = Los Angeles County, California
- **Data Quality**: All 3,075 US counties represented

#### County Name
- **Field Name**: `county_name`
- **Type**: VARCHAR
- **Definition**: Official county name as recognized by US Census
- **Business Use**: Human-readable geographic identification
- **Example**: "Los Angeles County"
- **Note**: Includes "County", "Parish", "Borough" suffixes as appropriate

#### State Information
- **Field Names**: `state_code`, `state_name`, `state_abbrev`
- **Types**: VARCHAR(2), VARCHAR, VARCHAR(2)
- **Definition**: State identification in multiple formats
- **Business Use**: State-level aggregation and filtering
- **Examples**: "06", "California", "CA"

#### Region
- **Field Name**: `region`
- **Type**: VARCHAR
- **Definition**: US Census region classification
- **Values**: Northeast, Midwest, South, West
- **Business Use**: Large-scale regional analysis and comparison
- **Distribution**: South (45.2%), Midwest (34.3%), West (13.5%), Northeast (7.1%)

### Land Use Categories

#### Land Use Code
- **Field Name**: `landuse_code`
- **Type**: VARCHAR(2)
- **Definition**: Standardized 2-character land use identifier
- **Values**:
  - **cr**: Cropland
  - **ps**: Pasture
  - **rg**: Rangeland
  - **fr**: Forest
  - **ur**: Urban
- **Business Use**: Compact representation for analysis and storage

#### Land Use Name
- **Field Name**: `landuse_name`
- **Type**: VARCHAR
- **Definition**: Full descriptive name for land use category
- **Business Use**: Human-readable reports and visualizations
- **Values**: Crop, Pasture, Rangeland, Forest, Urban

#### Land Use Category
- **Field Name**: `landuse_category`
- **Type**: VARCHAR
- **Definition**: High-level grouping for policy analysis
- **Values**:
  - **Agriculture**: Crop, Pasture
  - **Natural**: Rangeland, Forest
  - **Developed**: Urban
- **Business Use**: Simplified analysis focusing on broad land use types

### Scenario Definitions

#### Climate Model
- **Field Name**: `climate_model`
- **Type**: VARCHAR
- **Definition**: Global Climate Model used for projections
- **Business Context**:
  - **CNRM_CM5**: "Wet" climate model (higher precipitation)
  - **HadGEM2_ES365**: "Hot" climate model (higher temperatures)
  - **IPSL_CM5A_MR**: "Dry" climate model (lower precipitation)
  - **MRI_CGCM3**: "Least warm" climate model (moderate temperature increase)
  - **NorESM1_M**: "Middle" climate model (balanced)

#### RCP Scenario
- **Field Name**: `rcp_scenario`
- **Type**: VARCHAR
- **Definition**: Representative Concentration Pathway - greenhouse gas trajectory
- **Values**:
  - **rcp45**: Lower emissions scenario (+2.4°C by 2100)
  - **rcp85**: Higher emissions scenario (+4.3°C by 2100)
- **Business Use**: Climate impact analysis and mitigation planning

#### SSP Scenario
- **Field Name**: `ssp_scenario`
- **Type**: VARCHAR
- **Definition**: Shared Socioeconomic Pathway - development narrative
- **Values & Narratives**:
  - **ssp1**: Sustainability (low population growth, medium economic growth)
  - **ssp2**: Middle of the Road (medium population/economic growth)
  - **ssp3**: Regional Rivalry (high population growth, low economic growth)
  - **ssp4**: Inequality (medium population growth, high economic growth)
  - **ssp5**: Fossil-fueled Development (low population growth, high economic growth)

### Temporal Elements

#### Time Period
- **Field Name**: `year_range`
- **Type**: VARCHAR
- **Definition**: Decade-long transition period
- **Format**: "YYYY-YYYY"
- **Business Context**:
  - **2012-2020**: Historical calibration period (8 years)
  - **2020-2070**: 10-year projection intervals
- **Example**: "2040-2050"

#### Start Year / End Year
- **Field Names**: `start_year`, `end_year`
- **Type**: INTEGER
- **Definition**: Numeric year boundaries for calculations
- **Business Use**: Time-series analysis and trend calculations

### Measurement Units

#### Acres
- **Field Name**: `acres`
- **Type**: DECIMAL(15,4)
- **Definition**: Area measurement for land use transitions
- **Unit**: US acres (1 acre = 0.404686 hectares)
- **Business Context**: 
  - **Small Values**: Precision for urban development (typical: 1-50 acres)
  - **Large Values**: Agricultural and forest areas (typical: 100-10,000+ acres)
- **Conversion Factors**:
  - 1 acre = 4,047 square meters
  - 640 acres = 1 square mile
  - 1 acre = 0.404686 hectares

#### Population (Thousands)
- **Field Name**: `population_thousands`, `value` (in socioeconomic data)
- **Type**: DECIMAL(15,4)
- **Definition**: County population in thousands of persons
- **Business Use**: Demographic pressure analysis and development planning
- **Example**: 9,818.5 = 9,818,500 people

#### Income Per Capita
- **Field Name**: `income_per_capita_2009usd`, `value` (in socioeconomic data)
- **Type**: DECIMAL(15,4)
- **Definition**: Per capita income in thousands of 2009 US dollars
- **Business Context**: 
  - **Inflation Adjusted**: Constant 2009 dollars for temporal comparison
  - **Economic Indicator**: Purchasing power and development pressure
- **Example**: 42.6 = $42,600 per person per year

### Transition Characteristics

#### Transition Type
- **Field Name**: `transition_type`
- **Type**: VARCHAR
- **Definition**: Whether land use changed or remained the same
- **Values**:
  - **change**: Land converted from one use to another
  - **same**: Land remained in the same use category
- **Business Context**:
  - **Change Transitions**: Focus of policy and environmental analysis
  - **Same Transitions**: Baseline for calculating conversion rates

#### From/To Land Use
- **Field Names**: `from_landuse_id`, `to_landuse_id`
- **Type**: INTEGER (foreign keys)
- **Definition**: Source and destination land use categories
- **Business Use**: Transition matrix analysis and conversion pattern identification
- **Common Patterns**:
  - Forest → Urban (suburban development)
  - Crop ↔ Pasture (agricultural intensification/extensification)
  - Range → Pasture (livestock expansion)

---

## Socioeconomic Indicators

### Population Projections
- **Definition**: County-level population forecasts by SSP scenario
- **Data Source**: Integrated from SSP scenario narratives
- **Business Use**: 
  - Development pressure assessment
  - Infrastructure planning
  - Environmental impact analysis
- **Coverage**: 2010-2050 (historical + projections)

### Income Projections
- **Definition**: Per capita income forecasts by SSP scenario
- **Data Source**: Economic growth assumptions from SSP narratives
- **Business Use**:
  - Economic development planning
  - Land value and conversion pressure analysis
  - Environmental justice considerations
- **Unit**: Constant 2009 US dollars (inflation-adjusted)

---

## Data Quality and Validation

### Completeness
- **Geographic Coverage**: All 3,075 US counties included
- **Temporal Coverage**: Complete time series 2012-2070
- **Scenario Coverage**: All 20 climate/socioeconomic combinations
- **Land Use Coverage**: All major land use categories tracked

### Accuracy Considerations
- **Model Calibration**: 2012-2020 period used for historical validation
- **County Aggregation**: Sub-county variations smoothed to county level
- **Private Land Focus**: Public lands excluded (may underestimate total change)
- **Edge Effects**: County boundary effects not captured

### Business Rules Validation
- **Total Area Conservation**: County total land area remains constant
- **Urban Irreversibility**: No urban-to-other transitions (verified)
- **Logical Transitions**: Unrealistic transitions flagged during processing

---

## Usage Guidelines

### Query Patterns

#### Basic Land Use Analysis
```sql
-- Focus on actual changes
WHERE transition_type = 'change'

-- Exclude validation/total rows  
WHERE from_landuse != 'Total' AND to_landuse != 'Total'

-- Current land use (unchanged areas)
WHERE from_landuse_id = to_landuse_id
```

#### Scenario Comparison
```sql
-- Compare emission scenarios
WHERE rcp_scenario IN ('rcp45', 'rcp85')

-- Focus on specific socioeconomic narrative
WHERE ssp_scenario = 'ssp1'  -- Sustainability

-- Climate model sensitivity analysis
WHERE climate_model IN ('HadGEM2_ES365', 'IPSL_CM5A_MR')  -- Hot vs Dry
```

#### Geographic Analysis
```sql
-- Regional analysis
WHERE region = 'West'

-- State-level analysis
WHERE state_name = 'California'

-- Large counties (development pressure)
WHERE area_sqmi > 1000
```

#### Temporal Analysis
```sql
-- Near-term projections
WHERE start_year >= 2020 AND end_year <= 2040

-- Long-term trends
WHERE end_year = 2070

-- Historical calibration period
WHERE year_range = '2012-2020'
```

### Common Business Questions

#### Development Pressure
- **Question**: "Which counties face the highest urban development pressure?"
- **Data Elements**: Urban transitions, population growth, income trends
- **Key Metrics**: Acres converted to urban, population density, economic growth

#### Agricultural Impact
- **Question**: "How much agricultural land is lost under different scenarios?"
- **Data Elements**: Crop/Pasture to other transitions, scenario comparisons
- **Key Metrics**: Total agricultural acres lost, conversion rates by scenario

#### Climate Sensitivity
- **Question**: "How do land use outcomes vary between climate models?"
- **Data Elements**: Climate model comparisons, transition patterns
- **Key Metrics**: Forest loss rates, agricultural adaptation patterns

#### Regional Planning
- **Question**: "What are the regional patterns of land use change?"
- **Data Elements**: Regional aggregations, state-level comparisons
- **Key Metrics**: Land use change by region, cross-state patterns

---

## Integration Considerations

### External Data Sources
- **Census Data**: Population and economic statistics for validation
- **Agricultural Statistics**: USDA NASS for agricultural trends
- **Land Cover Data**: Remote sensing for land use verification
- **Climate Data**: Temperature and precipitation for model validation

### Data Relationships
- **Hierarchical Geography**: County → State → Region → Nation
- **Temporal Sequences**: Historical → Near-term → Long-term projections
- **Scenario Families**: Climate Model × RCP × SSP combinations
- **Land Use Transitions**: Source → Destination patterns

### Business Intelligence Applications
- **Dashboards**: County-level land use dashboards for planners
- **Reports**: Scenario comparison reports for policy makers
- **APIs**: Programmatic access for research applications
- **Visualizations**: Maps and charts for public communication

---

## Technical Notes

### Data Types and Precision
- **Spatial Precision**: County-level aggregation (~3,000 units)
- **Temporal Precision**: Decade-level intervals
- **Measurement Precision**: 4 decimal places for acres (0.1 square meter accuracy)
- **Scenario Precision**: 20 distinct scenario combinations

### Performance Characteristics
- **Query Performance**: Star schema optimized for analytical queries
- **Storage Efficiency**: 98.99% database block utilization
- **Index Strategy**: Composite indexes on frequently joined columns
- **View Performance**: Pre-computed views for common query patterns

### Maintenance and Updates
- **Static Data**: Historical and projection data (no ongoing updates)
- **Schema Stability**: Core structure stable for analytical consistency
- **Data Lineage**: Clear transformation pipeline from raw to analytical data
- **Quality Monitoring**: Automated validation checks during data loading

---

## Glossary

**RPA Assessment**: Resources Planning Act - periodic assessment of US forest and rangeland resources mandated by Congress

**County FIPS**: Federal Information Processing Standard codes uniquely identifying US counties

**Star Schema**: Data warehouse design with central fact table surrounded by dimension tables

**Land Use Transition**: Change (or lack of change) in land use category over a time period

**Private Land**: Non-government owned land subject to market forces and development pressure

**Climate Model**: Mathematical representation of Earth's climate system for future projections

**Socioeconomic Pathway**: Narrative describing potential societal development trajectories

**Representative Concentration Pathway**: Greenhouse gas concentration trajectory used in climate models

## Next Steps

- **Technical Implementation**: See [Table Reference](table-reference.md) for technical specifications
- **Query Examples**: See [Basic Queries](../queries/basic-queries.md) for practical usage
- **Business Context**: See [Land Use Categories](categories.md) for detailed category definitions
- **Methodology**: See [Land Use Methodology](../LAND_USE_METHODOLOGY.md) for projection methods