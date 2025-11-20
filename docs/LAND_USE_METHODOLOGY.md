# Land Use Methodology

This document provides an overview of the USDA Forest Service's RPA Assessment land use projection methodology.

> **📚 For Complete Methodology Documentation**: See the [Complete RPA Assessment Reference](rpa/rpa-assessment-complete.md) which includes comprehensive details about the econometric model, assumptions, and data sources.

## Quick Reference

### Econometric Model Foundation

The RPA land use projections are based on a sophisticated econometric model that projects county-level land use transitions from 2020 to 2100.

**Core Characteristics**:
- **Spatial Resolution**: 3,075 US counties
- **Temporal Coverage**: Decadal projections 2020-2100
- **Land Ownership Focus**: Private land only (public lands assumed static)
- **Scenario Integration**: 20 integrated climate-socioeconomic futures
- **Policy Approach**: Policy-neutral projections based on historical relationships

### Key Assumptions

#### 1. Development Irreversibility
Once land converts to developed (urban) use, it does not revert to other uses. This reflects the high cost and practical difficulty of converting developed areas back to agricultural or natural uses.

**Implications**:
- Urban areas can only increase or remain stable
- All urbanization comes from conversion of agricultural or natural lands
- Development pressure is a one-way driver of change

#### 2. Private Land Focus
All land use transitions occur on privately owned land. Public lands are managed under different objectives and constraints.

**Implications**:
- Model excludes approximately 30% of total U.S. land area
- Focus on lands most subject to economic development pressures

#### 3. Historical Calibration
Model is calibrated to observed transitions from 2001-2012 using National Resources Inventory (NRI) data.

**Implications**:
- Projects future based on historical relationships
- Assumes continuation of observed patterns
- Does not incorporate major policy changes

### Primary Land Use Pattern

**~46% of new developed land comes from forest conversion**

This is the dominant land use transition pattern observed historically and projected into the future across most scenarios.

## Land Use Categories

| Code | Category | Description |
|------|----------|-------------|
| **cr** | Crop | Agricultural cropland for food, feed, and fiber |
| **ps** | Pasture | Livestock grazing land and hay production |
| **fr** | Forest | Forested areas including timberland and woodland |
| **ur** | Urban | Built and developed areas (residential, commercial, infrastructure) |
| **rg** | Rangeland | Natural grasslands and shrublands |

## Data Sources

### Primary Sources
- **National Resources Inventory (NRI)**: Historical land use observations 2001-2012
- **Global Climate Models**: Temperature and precipitation projections from 5 selected GCMs
- **Socioeconomic Projections**: Population and economic growth scenarios from SSPs
- **Geographic Data**: County boundaries and land ownership patterns

### Model Outputs
- **Transition matrices**: Detailed acre-by-acre changes between land use categories
- **Scenario variations**: Results for all 20 integrated climate-socioeconomic scenarios
- **Temporal resolution**: Decadal projections enabling trend analysis
- **Spatial detail**: County-level granularity for local and regional analysis

## Related Documentation

- **[Complete RPA Assessment Reference](rpa/rpa-assessment-complete.md)** - Comprehensive methodology, scenarios, and analysis guidelines
- **[Climate Models](rpa/climate-models.md)** - Detailed climate model specifications
- **[Scenarios](rpa/scenarios.md)** - Integrated scenario framework and naming
- **[Data Dictionary](data/data-dictionary.md)** - Complete database schema and variable definitions

---

*For the most comprehensive and up-to-date methodology information, always refer to the [Complete RPA Assessment Reference](rpa/rpa-assessment-complete.md).*
