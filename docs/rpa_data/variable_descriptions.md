# Variable Descriptions

The following variables are found in the county land use projections data files.

## RPA Scenario
- **File**: county_landuse_projections_RPA.*
- **Units**: Not applicable
- **Precision**: Not applicable

RPA Scenarios are defined by Global Climate Model (GCM), Representative Concentration Pathway (RCP), and Shared Socioeconomic Pathway (SSP).

### Climate Models:
- **CNRM_CM5**: "wet" climate model
- **HadGEM2_ES365**: "hot" climate model
- **IPSL_CM5A_MR**: "dry" climate model
- **MRI_CGCM3**: "least warm" climate model
- **NorESM1_M**: "middle" climate model

### RPA Scenario Combinations:
- **rcp45_ssp1**: Low emissions forcing, medium growth
- **rcp85_ssp2**: High emissions forcing, medium growth
- **rcp85_ssp3**: High emissions forcing, low growth
- **rcp85_ssp5**: High emissions forcing, high growth

## Time Step
- **File**: county_landuse_projections_RPA.*
- **Units**: Years
- **Precision**: Integer

Projections are made in 10-year time steps from 2020-2070. For completeness we have included an additional time step (2012-2020) that was used to calibrate the projections for use in subsequent modeling efforts as part of the 2020 RPA Assessment.

## U.S. County Identifier
- **File**: county_landuse_projections_RPA.*
- **Units**: Not applicable
- **Precision**: Integer

5 Digit FIPS (Federal Information Processing Standards) code.

## [6 x 6 transition table]
- **File**: county_landuse_projections_RPA.*
- **Units**: 100s of acres
- **Precision**: Double-Precision Floating-Point

Area of land transitioned between land use categories:
- **cr**: cropland
- **ps**: pasture land
- **rg**: rangeland
- **fr**: forest land
- **ur**: urban developed land
- **t1**: total area of land in use category at starting year
- **t2**: total area of land in use category at ending year 