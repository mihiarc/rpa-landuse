# DuckDB to PandasAI Implementation Guide

This guide outlines the process for using DuckDB data with PandasAI through the creation of optimized Parquet file subsets with semantic layer enhancements.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Extracting Data from DuckDB](#extracting-data-from-duckdb)
4. [Creating Semantic Layers](#creating-semantic-layers)
5. [Querying with Natural Language](#querying-with-natural-language)
6. [Advanced Customization](#advanced-customization)
7. [Understanding Semantic Layers in PandasAI](#understanding-semantic-layers-in-pandasai)

## Overview

The DuckDB database (`rpa.db`) contains land use transition data across multiple scenarios and time periods. While PandasAI does not directly expose a DuckDB file connector, we can extract relevant data subsets into Parquet files and enhance them with semantic information to enable powerful natural language querying.

## Prerequisites

```bash
# Create a Python virtual environment with pip
python3 -m venv .venv

# Install required packages
pip install duckdb pandas pyarrow pandasai
```

## Extracting Data from DuckDB

First, we'll extract relevant subsets from the DuckDB database and save them as Parquet files:

```python
import os
import duckdb
import pandas as pd

# Create directory for parquet files if it doesn't exist
os.makedirs("land_use_parquet", exist_ok=True)

# Connect to DuckDB
conn = duckdb.connect('rpa.db')

# Extract reference tables
conn.sql("SELECT * FROM scenarios").write_parquet('land_use_parquet/scenarios.parquet')
conn.sql("SELECT * FROM land_use_categories").write_parquet('land_use_parquet/land_use_categories.parquet')
conn.sql("SELECT * FROM time_steps").write_parquet('land_use_parquet/time_steps.parquet')
conn.sql("SELECT * FROM counties").write_parquet('land_use_parquet/counties.parquet')

# Create an aggregated transitions view
conn.sql("""
    SELECT 
        s.scenario_name,
        s.gcm, 
        s.rcp,
        s.ssp,
        ts.time_step_name,
        ts.start_year,
        ts.end_year,
        c1.category_name as from_category,
        c2.category_name as to_category,
        SUM(t.area_hundreds_acres) as total_area
    FROM land_use_transitions t
    JOIN scenarios s ON t.scenario_id = s.scenario_id
    JOIN time_steps ts ON t.time_step_id = ts.time_step_id
    JOIN land_use_categories c1 ON t.from_land_use = c1.category_code
    JOIN land_use_categories c2 ON t.to_land_use = c2.category_code
    GROUP BY s.scenario_name, s.gcm, s.rcp, s.ssp, 
             ts.time_step_name, ts.start_year, ts.end_year, 
             c1.category_name, c2.category_name
""").write_parquet('land_use_parquet/transitions_summary.parquet')

# Create a county-level aggregation
conn.sql("""
    SELECT 
        co.fips_code,
        co.county_name,
        co.state_name,
        s.scenario_name,
        ts.time_step_name,
        c1.category_name as from_category,
        c2.category_name as to_category,
        SUM(t.area_hundreds_acres) as total_area
    FROM land_use_transitions t
    JOIN counties co ON t.fips_code = co.fips_code
    JOIN scenarios s ON t.scenario_id = s.scenario_id
    JOIN time_steps ts ON t.time_step_id = ts.time_step_id
    JOIN land_use_categories c1 ON t.from_land_use = c1.category_code
    JOIN land_use_categories c2 ON t.to_land_use = c2.category_code
    GROUP BY co.fips_code, co.county_name, co.state_name,
             s.scenario_name, ts.time_step_name, 
             c1.category_name, c2.category_name
""").write_parquet('land_use_parquet/county_transitions.parquet')

# Close the connection
conn.close()
```

## Creating Semantic Layers

Now, we'll add semantic layer information to our Parquet files using PandasAI:

```python
import pandasai as pai

# Set your API key if needed
pai.api_key.set("your-pai-api-key")

# Load the transitions summary dataset
transitions_df = pai.read_parquet('land_use_parquet/transitions_summary.parquet')

# Create dataset with semantic information
transitions_dataset = pai.create(
    path="my-org/land-use-transitions",
    df=transitions_df,
    name="Land Use Transitions",
    description="Aggregated land use transition data across scenarios and time periods",
    columns=[
        {"name": "scenario_name", "type": "string", "description": "Name of the climate scenario"},
        {"name": "gcm", "type": "string", "description": "Global Climate Model used in the scenario"},
        {"name": "rcp", "type": "string", "description": "Representative Concentration Pathway - emissions scenario"},
        {"name": "ssp", "type": "string", "description": "Shared Socioeconomic Pathway - socioeconomic scenario"},
        {"name": "time_step_name", "type": "string", "description": "Time period of the transition"},
        {"name": "start_year", "type": "integer", "description": "Starting year of the time period"},
        {"name": "end_year", "type": "integer", "description": "Ending year of the time period"},
        {"name": "from_category", "type": "string", "description": "Original land use category"},
        {"name": "to_category", "type": "string", "description": "Resulting land use category"},
        {"name": "total_area", "type": "float", "description": "Total area in hundreds of acres"}
    ]
)

# For county-level transitions
county_df = pai.read_parquet('land_use_parquet/county_transitions.parquet')

county_dataset = pai.create(
    path="my-org/county-transitions",
    df=county_df,
    name="County Land Use Transitions",
    description="County-level land use transition data across scenarios and time periods",
    columns=[
        {"name": "fips_code", "type": "string", "description": "FIPS code identifying the county"},
        {"name": "county_name", "type": "string", "description": "Name of the county"},
        {"name": "state_name", "type": "string", "description": "Name of the state"},
        {"name": "scenario_name", "type": "string", "description": "Name of the climate scenario"},
        {"name": "time_step_name", "type": "string", "description": "Time period of the transition"},
        {"name": "from_category", "type": "string", "description": "Original land use category"},
        {"name": "to_category", "type": "string", "description": "Resulting land use category"},
        {"name": "total_area", "type": "float", "description": "Total area in hundreds of acres"}
    ]
)
```

## Querying with Natural Language

Once the semantic layers are set up, you can use natural language to query the datasets:

```python
import pandasai as pai

# Load saved datasets
transitions_dataset = pai.load("my-org/land-use-transitions")
county_dataset = pai.load("my-org/county-transitions")

# Examples of natural language queries
transitions_dataset.chat("Which scenario shows the most conversion from Forest to Urban land?")

transitions_dataset.chat("Create a bar chart showing the top 5 land use transitions by total area")

county_dataset.chat("Which counties show the most agricultural land conversion to urban areas?")

# To use multiple datasets together
pai.chat("Compare Forest to Urban conversion across different time periods and scenarios", 
         transitions_dataset, county_dataset)
```

## Advanced Customization

### Creating Custom Views for Specific Analysis

You can create additional derived views for specific analysis needs:

```python
import duckdb
import pandasai as pai

# Connect to DuckDB
conn = duckdb.connect('rpa.db')

# Create a time series view for analyzing trends
conn.sql("""
    SELECT 
        s.scenario_name,
        ts.time_step_name,
        ts.start_year,
        SUM(CASE WHEN t.from_land_use = 'fr' AND t.to_land_use = 'ur' 
            THEN t.area_hundreds_acres ELSE 0 END) as forest_to_urban,
        SUM(CASE WHEN t.from_land_use = 'cr' AND t.to_land_use = 'ur' 
            THEN t.area_hundreds_acres ELSE 0 END) as cropland_to_urban,
        SUM(CASE WHEN t.from_land_use = 'ps' AND t.to_land_use = 'ur' 
            THEN t.area_hundreds_acres ELSE 0 END) as pasture_to_urban
    FROM land_use_transitions t
    JOIN scenarios s ON t.scenario_id = s.scenario_id
    JOIN time_steps ts ON t.time_step_id = ts.time_step_id
    GROUP BY s.scenario_name, ts.time_step_name, ts.start_year
    ORDER BY s.scenario_name, ts.start_year
""").write_parquet('land_use_parquet/urbanization_trends.parquet')

# Create semantic layer for the time series
urbanization_df = pai.read_parquet('land_use_parquet/urbanization_trends.parquet')

urbanization_dataset = pai.create(
    path="my-org/urbanization-trends",
    df=urbanization_df,
    name="Urbanization Trends",
    description="Time series of land conversion to urban areas across scenarios",
    columns=[
        {"name": "scenario_name", "type": "string", "description": "Name of the climate scenario"},
        {"name": "time_step_name", "type": "string", "description": "Time period of the transition"},
        {"name": "start_year", "type": "integer", "description": "Starting year of the time period"},
        {"name": "forest_to_urban", "type": "float", "description": "Forest area (hundreds of acres) converted to urban"},
        {"name": "cropland_to_urban", "type": "float", "description": "Cropland area (hundreds of acres) converted to urban"},
        {"name": "pasture_to_urban", "type": "float", "description": "Pasture area (hundreds of acres) converted to urban"}
    ]
)
```

## Understanding Semantic Layers in PandasAI

PandasAI's semantic layer feature works with various data formats, not just Parquet files. The key aspects of the semantic layer are:

### 1. How Semantic Layers Work with Different Data Sources

PandasAI's semantic layer can be applied to data from various sources:

- **Local files** (CSV, Parquet) - As demonstrated in this guide
- **SQL databases** - PandasAI supports MySQL, PostgreSQL, CockroachDB, and Oracle
- **Cloud data warehouses** - Snowflake, BigQuery, and Databricks are supported via enterprise extensions
- **Views** - Logical views that combine multiple data sources

The semantic layer works as a translation layer between your raw data and the natural language interface. Regardless of the original data source, once data is loaded into PandasAI, the semantic layer provides:

1. **Context for columns** - Describes what each column represents
2. **Data types** - Indicates how to interpret values (string, number, date)
3. **Relationships** - Can define relationships between datasets
4. **Transformations** - Can define data transformations

### 2. Workflow with Databases

When working with database sources like SQL databases, the workflow is similar:

1. **Connection Setup** - PandasAI connects to the database using appropriate connectors
2. **Schema Definition** - You define the semantic layer for the database tables
3. **Query Generation** - PandasAI translates natural language to appropriate SQL queries
4. **Result Processing** - Results are processed and returned in the requested format

The key difference is that with SQL databases, PandasAI can generate and execute queries directly against the database rather than loading all data into memory.

### 3. Benefits of Semantic Layer with Databases

- **Consistent Interface** - Same natural language interface regardless of data source
- **Reduced Data Movement** - Queries execute in the database when possible
- **Rich Context** - LLMs understand your data better with semantic information
- **Improved Accuracy** - Semantic information helps generate more accurate code
- **Domain-Specific Knowledge** - Incorporate business logic and domain knowledge

For DuckDB specifically, while there's no direct integration exposed in the API, PandasAI uses DuckDB internally as its SQL engine for local data processing, which is why the Parquet approach works well as a bridge. 