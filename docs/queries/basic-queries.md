# Basic Natural Language Queries

This guide covers fundamental query patterns to help you get started with natural language data analysis.

## Exploring the Database

### List Tables

```
You> What tables are in the landuse_transitions database?
```

**Agent Response:**
```
Database: processed/landuse_transitions_with_ag.db
Tables:
  • landuse_transitions: 1,234,567 rows
  • landuse_transitions_ag: 987,654 rows  
  • landuse_changes_only: 543,210 rows
  • landuse_changes_only_ag: 432,109 rows
```

### Understand Table Structure

```
You> Describe the schema of the landuse_transitions table
```

**Agent Response:**
```
Table: landuse_transitions
Rows: 1,234,567

Schema:
  scenario (TEXT) NOT NULL
  year (INTEGER) NOT NULL
  year_range (TEXT) NOT NULL
  fips (TEXT) NOT NULL
  from_land_use (TEXT) NOT NULL
  to_land_use (TEXT) NOT NULL
  area_1000_acres (REAL)

Indexes:
  • idx_scenario
  • idx_year
  • idx_fips
```

### See Sample Data

```
You> Show me 5 sample rows from the landuse_transitions table
```

## Simple Filtering Queries

### Filter by Scenario

```
You> Show me data from the Baseline scenario
```

The agent generates:
```sql
SELECT * FROM landuse_transitions 
WHERE scenario = 'Baseline' 
LIMIT 10
```

### Filter by Year

```
You> What land use transitions happened in 2050?
```

### Filter by Location

```
You> Show me land use changes in California
```

The agent knows California FIPS codes start with '06':
```sql
SELECT * FROM landuse_transitions 
WHERE fips LIKE '06%' 
LIMIT 100
```

### Filter by Land Use Type

```
You> Show me all transitions from forest
```

## Basic Aggregations

### Count Records

```
You> How many land use transitions are in the database?
```

### Sum Areas

```
You> What's the total forest area in 2020?
```

**Generated SQL:**
```sql
SELECT SUM(area_1000_acres) as total_forest_acres
FROM landuse_transitions
WHERE from_land_use = 'Forest' 
  AND to_land_use = 'Forest'
  AND year = 2020
```

### Group By Queries

```
You> Show me total area by land use type
```

### Calculate Averages

```
You> What's the average urban area per county?
```

## Finding Unique Values

### List Scenarios

```
You> What scenarios are available in the data?
```

**Response:**
```
Unique scenarios:
- Baseline
- High Crop Demand  
- High Forest
- High Urban
```

### List Land Use Types

```
You> What are all the land use categories?
```

### List Years

```
You> What years does the data cover?
```

## Simple Transition Queries

### Specific Transitions

```
You> Show me forest to urban transitions
```

**Generated SQL:**
```sql
SELECT * FROM landuse_transitions
WHERE from_land_use = 'Forest' 
  AND to_land_use = 'Urban'
LIMIT 100
```

### All Transitions From a Type

```
You> What does cropland convert to?
```

### All Transitions To a Type

```
You> What converts to urban land?
```

## Basic Sorting

### Order by Area

```
You> Show the largest land use transitions by area
```

### Order by Year

```
You> Show forest area over time, sorted by year
```

### Top N Results

```
You> What are the top 10 counties by total land area?
```

## Simple Comparisons

### Compare Two Values

```
You> Is there more forest or cropland in 2050?
```

### Year-over-Year Changes

```
You> How much did urban area change from 2020 to 2030?
```

### Scenario Differences

```
You> Compare forest area between Baseline and High Forest scenarios
```

## Working with Results

### Export Data

```
You> Export the forest transitions to a CSV file
```

### Get Statistics

```
You> Show me statistics for the area_1000_acres column
```

### Count Distinct Values

```
You> How many unique counties are in the data?
```

## Common Query Patterns

### Pattern 1: Filter + Aggregate
```
"Total [land use] area in [location] for [scenario]"
"Sum of [metric] where [condition]"
"Average [value] by [grouping]"
```

### Pattern 2: Find Specific Records
```
"Show me [land use] in [year]"
"List [top N] [items] by [metric]"
"Find all [transitions] from [type] to [type]"
```

### Pattern 3: Compare Values
```
"Compare [metric] between [A] and [B]"
"What's the difference in [value] from [time1] to [time2]"
"Which [item] has more [metric]?"
```

## Tips for Success

### 1. Start Simple

Begin with basic queries and add complexity:
- First: "Show forest data"
- Then: "Show forest data in 2050"  
- Finally: "Show forest to urban transitions in California in 2050"

### 2. Use Natural Language

Don't try to write SQL-like queries:
- ❌ "SELECT * FROM landuse WHERE..."
- ✅ "Show me land use data where..."

### 3. Ask for Clarification

If unsure about data:
```
You> What does the 'area_1000_acres' column represent?
You> What's the difference between the regular and _ag tables?
```

### 4. Build on Previous Queries

The agent remembers context:
```
You> Show me total forest area by year
[Agent shows results]
You> Now just show me the years where it decreases
```

## Practice Exercises

Try these queries to build familiarity:

1. **Basic Exploration**
   - List all tables in the database
   - Show the first 10 rows of landuse_transitions
   - Count total records in each table

2. **Filtering Practice**
   - Find all High Urban scenario data
   - Show transitions in the year 2100
   - List data for FIPS code 06037

3. **Simple Analysis**
   - Calculate total urban area
   - Find the most common land use transition
   - Show which scenario has the most forest

4. **Basic Comparisons**
   - Compare cropland between 2020 and 2050
   - Find the county with the most urban growth
   - Show the difference between scenarios

## Next Steps

Once comfortable with basic queries:
- Learn [Advanced Queries](advanced-queries.md) for complex analysis
- See [Query Examples](examples.md) for real-world scenarios
- Understand [Data Schemas](../data/schema.md) for available fields