# DuckDB Data Views for RPA Land Use Viewer

This document describes the approach for creating smaller, optimized data views directly from the DuckDB database for GitHub and Streamlit Cloud deployment.

## Advantages of Direct DuckDB Approach

Rather than creating existing parquet files and then reducing them, we create the smaller views directly from the source database:

1. **Data Integrity**: Direct SQL aggregation preserves the exact relationships in the data
2. **Performance**: DuckDB's query engine efficiently handles the aggregation operations
3. **Maintainability**: Changes to reduction logic can be implemented by modifying SQL queries
4. **Simplicity**: Single-step process from raw data to deployment-ready files

## Implementation

The implementation is in `scripts/data_processor_duckdb.py` which:

1. Connects to the DuckDB database (`data/database/rpa.db`)
2. Runs optimized SQL queries to create aggregated datasets
3. Saves the results as parquet files in `data/processed/`

## Generated Datasets

The script creates five reduced datasets:

1. **Gross Change Ensemble**: Aggregated at region level instead of county level
2. **Urbanization Trends**: Focused on key transitions from various land types to urban areas
3. **To-Urban Transitions**: Highlights largest transitions to urban land 
4. **From-Forest Transitions**: Shows major transitions from forest land to other types
5. **County Transitions**: Includes top 200 counties plus aggregated "Other counties" by state

## Size Reduction Techniques

Each dataset uses specific reduction strategies:

- **Region Aggregation**: Group by region instead of county
- **Limiting Results**: Focus on largest transitions by area
- **Data Consolidation**: Aggregate smaller transitions into "Other" categories
- **Selective Columns**: Include only necessary information in each view

## Usage

Run the processor to generate the reduced datasets:

```bash
python scripts/data_processor_duckdb.py
```

The app will automatically use the smaller datasets if they're found in `data/processed/`.

## Modifying Reduction Logic

To change how data is reduced:

1. Edit the SQL query in the appropriate function in `scripts/data_processor_duckdb.py`
2. Run the script again to regenerate the datasets
3. No changes to the app code are needed as long as the output file names remain the same 