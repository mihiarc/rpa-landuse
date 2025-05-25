# DuckDB CLI Cheatsheet

## Getting Started

```bash
# Start the CLI with a database
duckdb data/database/rpa.db

# Exit the CLI
.exit or .quit
```

## Basic Commands

| Command | Description |
|---------|-------------|
| `.help` | Display help information |
| `.tables` | List all tables in the database |
| `.schema TABLE` | Show table structure |
| `.mode csv/column/line` | Change output format |
| `.headers on/off` | Toggle column headers |
| `.timer on/off` | Toggle query timing |
| `.output FILE` | Send output to file |
| `.output stdout` | Reset output to console |
| `.read FILE.sql` | Run SQL from file |

## Essential SQL

```sql
-- Basic SELECT
SELECT * FROM table_name LIMIT 10;

-- Filter with WHERE
SELECT * FROM counties WHERE state_name = 'California';

-- JOIN tables
SELECT 
    c.county_name, 
    t.from_land_use, 
    t.to_land_use 
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
LIMIT 10;

-- Aggregations
SELECT 
    state_name, 
    COUNT(*) as county_count 
FROM 
    counties 
GROUP BY 
    state_name
ORDER BY 
    county_count DESC;
```

## Data Modification

```sql
-- Delete rows based on a condition
DELETE FROM table_name WHERE condition;

-- Example: Delete all rows with state_name 'Alaska'
DELETE FROM counties WHERE state_name = 'Alaska';

-- Delete rows with multiple conditions
DELETE FROM land_use_transitions 
WHERE scenario_id = 5 
AND area_hundreds_acres < 1.0;

-- Delete all rows in a table (keeps the table structure)
DELETE FROM table_name;

-- Drop (delete) an entire table
DROP TABLE table_name;

-- Drop a table only if it exists
DROP TABLE IF EXISTS table_name;

-- Rename a table
ALTER TABLE current_table_name RENAME TO new_table_name;

-- Example: Rename a temporary table
ALTER TABLE temp_counties RENAME TO counties;

-- Rename a column in a table
ALTER TABLE table_name RENAME COLUMN old_column_name TO new_column_name;
```

## Table Constraints

```sql
-- Creating a table with a UNIQUE constraint
CREATE TABLE scenarios (
    scenario_id INTEGER PRIMARY KEY,
    scenario_name VARCHAR UNIQUE,  -- Single column unique constraint
    gcm VARCHAR,
    rcp VARCHAR,
    ssp VARCHAR
);

-- Creating a table with a multi-column UNIQUE constraint
CREATE TABLE counties (
    fips_code VARCHAR PRIMARY KEY,
    county_name VARCHAR,
    state_name VARCHAR,
    state_fips VARCHAR,
    region VARCHAR,
    UNIQUE(county_name, state_name)  -- Composite unique constraint
);

-- Adding a UNIQUE constraint to an existing table
ALTER TABLE scenarios ADD CONSTRAINT unique_scenario_name UNIQUE(scenario_name);

-- Adding a composite UNIQUE constraint
ALTER TABLE time_steps ADD CONSTRAINT unique_year_range UNIQUE(start_year, end_year);

-- Checking what would violate a UNIQUE constraint
SELECT scenario_name, COUNT(*) 
FROM scenarios 
GROUP BY scenario_name 
HAVING COUNT(*) > 1;

-- Removing duplicate rows before adding a UNIQUE constraint
WITH numbered_rows AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY scenario_name ORDER BY scenario_id) as rn
  FROM scenarios
)
DELETE FROM scenarios 
WHERE scenario_id IN (
  SELECT scenario_id FROM numbered_rows WHERE rn > 1
);
```

## Exporting Data

```sql
-- Export to CSV
.mode csv
.headers on
.output results.csv
SELECT * FROM counties LIMIT 100;
.output stdout

-- Export to Parquet
COPY (SELECT * FROM counties) TO 'counties.parquet' (FORMAT PARQUET);
```

## Land Use Database Quick Queries

```sql
-- All scenarios
SELECT * FROM scenarios;

-- Time periods
SELECT * FROM time_steps;

-- Land use categories
SELECT * FROM land_use_categories;

-- Top transitions for scenario 1 and time step 2
SELECT 
    c.county_name, 
    c.state_name, 
    t.from_land_use, 
    t.to_land_use, 
    t.area_hundreds_acres * 100 as acres
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use != t.to_land_use
ORDER BY 
    acres DESC
LIMIT 10;
``` 