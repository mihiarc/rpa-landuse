# DuckDB CLI User Guide

This guide provides basic instructions for using the DuckDB Command Line Interface (CLI) to interact with the RPA Land Use database.

## Installation

If you haven't installed DuckDB CLI yet:

```bash
# macOS (using Homebrew)
brew install duckdb

# Ubuntu/Debian
sudo apt-get install duckdb

# Using Python (already available if you've installed the Python duckdb package)
pip install duckdb
```

## Basic Usage

### Starting the CLI

To start the DuckDB CLI with the RPA Land Use database:

```bash
# Navigate to the project directory
cd /path/to/rpa-landuse-viewer

# Start DuckDB with the database file
duckdb data/database/rpa.db
```

You should see a prompt like:
```
v0.9.2 3c695d4ba9
Enter ".help" for usage hints.
D 
```

### Basic Commands

Here are some essential DuckDB CLI commands:

| Command | Description |
|---------|-------------|
| `.help` | Display help information |
| `.tables` | List all tables in the database |
| `.schema TABLE_NAME` | Show the schema of a specific table |
| `.exit` or `.quit` | Exit the CLI |
| `.timer on/off` | Turn query timing on or off |
| `.mode FORMAT` | Set output mode (csv, column, line, etc.) |
| `.headers on/off` | Turn column headers on or off |
| `.read FILENAME` | Execute SQL from a file |
| `.output FILENAME` | Direct output to a file |
| `.output stdout` | Direct output back to console |

## Querying the RPA Land Use Database

### List Available Tables

```sql
.tables
```

This should display:
```
counties land_use_categories land_use_transitions scenarios time_steps
```

### Examine Table Structure

```sql
.schema counties
```

```sql
.schema land_use_transitions
```

### Basic Query Examples

#### View Scenarios

```sql
SELECT * FROM scenarios;
```

#### View Time Steps

```sql
SELECT * FROM time_steps;
```

#### View Land Use Categories

```sql
SELECT * FROM land_use_categories;
```

#### View Counties (Limited)

```sql
SELECT * FROM counties LIMIT 10;
```

### Advanced Query Examples

#### Land Use Transitions

View top transitions by acres changed:

```sql
SELECT 
    c.county_name, 
    c.state_name, 
    t.from_land_use, 
    t.to_land_use, 
    t.area_hundreds_acres * 100 as acres_changed
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use != t.to_land_use
ORDER BY 
    acres_changed DESC
LIMIT 10;
```

#### Transitions by Region

Count transitions by region:

```sql
SELECT 
    c.region, 
    t.from_land_use, 
    t.to_land_use, 
    COUNT(*) as transition_count,
    SUM(t.area_hundreds_acres * 100) as total_acres_changed
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use != t.to_land_use
GROUP BY 
    c.region, t.from_land_use, t.to_land_use
ORDER BY 
    c.region, total_acres_changed DESC;
```

#### State Statistics

Get total land transitions by state:

```sql
SELECT 
    c.state_name, 
    SUM(t.area_hundreds_acres * 100) as total_acres_changing
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
    AND t.from_land_use != t.to_land_use
GROUP BY 
    c.state_name
ORDER BY 
    total_acres_changing DESC
LIMIT 15;
```

## Exporting Data

### Export Query Results to CSV

```sql
.mode csv
.headers on
.output results.csv
SELECT 
    c.county_name, 
    c.state_name, 
    t.from_land_use, 
    t.to_land_use, 
    t.area_hundreds_acres * 100 as acres_changed
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
WHERE 
    t.scenario_id = 1 
    AND t.time_step_id = 2
LIMIT 100;
.output stdout
```

### Export to Parquet

```sql
COPY (
    SELECT 
        c.county_name, 
        c.state_name, 
        t.from_land_use, 
        t.to_land_use, 
        t.area_hundreds_acres * 100 as acres_changed
    FROM 
        land_use_transitions t
    JOIN 
        counties c ON t.fips_code = c.fips_code
    WHERE 
        t.scenario_id = 1 
        AND t.time_step_id = 2
) TO 'output.parquet' (FORMAT PARQUET);
```

## Advanced Features

### Run SQL from a File

Create a file `query.sql` containing your SQL query, then:

```sql
.read query.sql
```

### Timing Queries

```sql
.timer on
SELECT COUNT(*) FROM land_use_transitions;
```

### Creating Views for Complex Queries

```sql
CREATE VIEW state_transitions AS
SELECT 
    c.state_name, 
    t.from_land_use, 
    t.to_land_use, 
    SUM(t.area_hundreds_acres * 100) as total_acres
FROM 
    land_use_transitions t
JOIN 
    counties c ON t.fips_code = c.fips_code
GROUP BY 
    c.state_name, t.from_land_use, t.to_land_use;

-- Now query from the view
SELECT * FROM state_transitions 
WHERE from_land_use = 'fr' AND to_land_use = 'ur'
ORDER BY total_acres DESC;
```

## Tips and Tricks

1. Use UP arrow key to recall previous commands
2. Use `.timer on` to measure query performance
3. For large result sets, use `.mode csv` and `.output filename.csv` to export results
4. Use LIMIT clause in queries to preview results before running on full dataset
5. Create VIEWS for frequently used complex queries
6. Use indexes for better performance on large tables
7. The `EXPLAIN` keyword before a query shows the execution plan

## Conclusion

This guide covers the basics of using DuckDB CLI with the RPA Land Use database. For more advanced features, refer to the [official DuckDB documentation](https://duckdb.org/docs/api/cli.html). 