# RPA Land Use Analytics

AI-powered analytics tool for USDA Forest Service RPA Assessment land use data. This project enables natural language exploration of county-level land use projections from the 2020 Resources Planning Act Assessment through 2070.

## Core Purpose
- Analyze land use transitions across 20 climate-socioeconomic scenarios
- Provide natural language interface to complex geospatial datasets
- Support policy analysis and land use planning decisions
- Enable comparison of climate pathways (RCP4.5 vs RCP8.5) and socioeconomic scenarios (SSP1-5)

## Key Features
- **Natural Language Queries**: Ask questions like "Which scenarios show the most agricultural land loss?"
- **Modern Data Stack**: DuckDB star schema optimized for analytics
- **AI Agents**: LangChain + GPT-4/Claude for SQL generation and analysis
- **Rich Analytics**: Automatic summary statistics and business insights
- **Geographic Analysis**: County-level data for 3,075 US counties

## Data Context
Based on USDA Forest Service 2020 RPA Assessment with econometric model projections covering:
- **Time Range**: 2012-2070 in 10-year intervals
- **Geographic Scope**: Conterminous United States (3,075 counties)
- **Land Use Types**: Crop, Pasture, Rangeland, Forest, Urban
- **Scenarios**: 20 combinations of climate models and socioeconomic pathways
- **Focus**: Private land transitions only (public lands assumed unchanged)