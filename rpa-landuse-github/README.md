# RPA Land Use Viewer

This repository contains a Streamlit application for visualizing land use transition projections from the USDA Forest Service's Resources Planning Act (RPA) Assessment.

## Overview

The RPA Land Use Viewer helps users explore how land use is expected to change across the United States from 2020 to 2070 under different climate and socioeconomic scenarios. The app visualizes key transitions such as:

- Urbanization trends
- Forest land conversion
- County-level land use changes
- Overall land use transitions across regions
- Interactive state-level maps showing land use change patterns

## Features

- **Data Explorer**: Browse and download the underlying datasets
- **Urbanization Trends**: Visualize how urban areas are projected to expand
- **Forest Transitions**: Explore how forest land is expected to change
- **Interactive Map**: View state-level land use changes with customizable filters for:
  - Transition type (all, to urban, from forest)
  - Climate and socioeconomic scenarios
  - Time periods (decades from 2020-2070)

## Data

This repository includes optimized data views created directly from the RPA Land Use database using DuckDB:

- `data/processed/gross_change_ensemble_all.parquet`: Region-level land use transitions
- `data/processed/urbanization_trends.parquet`: Key urbanization trends by decade and scenario
- `data/processed/to_urban_transitions.parquet`: Major transitions to urban land
- `data/processed/from_forest_transitions.parquet`: Major transitions from forest land
- `data/processed/county_transitions.parquet`: County-level land use transitions

The data has been processed to:
1. Aggregate county-level data to regions where appropriate
2. Focus on the most significant land use transitions
3. Provide optimal performance for web-based deployment

## Running the App

### Local Development

1. Clone this repository:
```bash
git clone https://github.com/your-username/rpa-landuse.git
cd rpa-landuse
```

2. Install dependencies:
```bash
pip install -r requirements-streamlit.txt
```

3. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

### Streamlit Cloud Deployment

This repository is configured for direct deployment on Streamlit Cloud:

1. Connect your GitHub repository to Streamlit Cloud
2. Select `streamlit_app.py` as the main file
3. Set Python version to 3.9+ in the requirements

## Data Processing

The optimized data views were created using DuckDB queries that:

- Aggregate data to appropriate levels
- Focus on the most significant transitions
- Reduce file sizes for GitHub and cloud deployment

For more details on the data processing approach, see:
- `docs/duckdb/data_views.md`: Documentation on the DuckDB data views
- `scripts/data_processor_duckdb.py`: Code that generates the processed data

## License

This project is licensed under the terms specified in the LICENSE file.

## Acknowledgments

Data source: USDA Forest Service's Resources Planning Act (RPA) Assessment 