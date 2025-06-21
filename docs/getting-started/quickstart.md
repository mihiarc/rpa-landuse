# Quick Start Guide

Get up and running with natural language queries in 5 minutes!

## Prerequisites

Make sure you've completed the [installation](installation.md) steps:

- ✅ Dependencies installed
- ✅ OpenAI API key configured
- ✅ Test agent runs successfully

## Your First Query

### 1. Start the Agent

```bash
uv run python scripts/agents/test_agent.py
```

### 2. List Available Data

Start by exploring what data is available:

```
You> List all files in the data directory
```

The agent will show you available CSV, JSON, Parquet, and database files.

### 3. Explore a Database

If you have the land use database, explore its structure:

```
You> Show me the tables in processed/landuse_transitions_with_ag.db
```

Response:
```
Database: processed/landuse_transitions_with_ag.db
Tables:
  • landuse_transitions: 1,234,567 rows
  • landuse_transitions_ag: 987,654 rows
  • landuse_changes_only: 543,210 rows
  • landuse_changes_only_ag: 432,109 rows
```

### 4. Understand the Schema

```
You> Describe the landuse_transitions table
```

The agent will show columns, data types, and sample data.

## Natural Language Query Examples

### Basic Queries

**Count records by scenario:**
```
You> How many transitions are there for each scenario?
```

**Find specific transitions:**
```
You> Show me forest to urban transitions in the Baseline scenario
```

**Aggregate data:**
```
You> What's the total agricultural land area in 2050?
```

### Advanced Queries

**Top counties by change:**
```
You> Which 10 counties had the most forest loss between 2020 and 2050?
```

**Scenario comparison:**
```
You> Compare total urban area between Baseline and High Crop Demand scenarios in 2050
```

**Trend analysis:**
```
You> Show me how cropland area changes over time for FIPS code 06037
```

## Working with the Agent

### Understanding Agent Responses

The agent will:

1. **Interpret your question** - Convert natural language to SQL
2. **Show the query** - Display the generated SQL for transparency
3. **Execute and format** - Run the query and present results clearly
4. **Provide context** - Add explanations when helpful

Example interaction:

```
You> What are the main land use types?

Agent> I'll query the database to show you the distinct land use types.

Query: SELECT DISTINCT from_land_use FROM landuse_transitions ORDER BY from_land_use

Results: 6 rows
- Crop
- Forest
- Pasture
- Range
- Total
- Urban
```

### Query Tips

1. **Be specific** - Include details like scenarios, years, or counties
2. **Use natural language** - No need to write SQL
3. **Ask follow-ups** - The agent maintains context
4. **Request visualizations** - Ask for charts or plots

### Common Tasks

<details>
<summary>📊 Analyzing Transitions</summary>

```
# See all transitions from forest
You> Show all land use types that forest converts to

# Focus on specific transitions
You> How much pasture converts to crop in the High Crop Demand scenario?

# Exclude same-to-same
You> Show me only the changes, not areas that stayed the same
```
</details>

<details>
<summary>🗺️ Geographic Analysis</summary>

```
# County-specific queries
You> What are the land use changes in Los Angeles County (FIPS 06037)?

# Regional patterns
You> Which counties in California have the most urban growth?

# Top counties
You> List the top 20 counties by total agricultural land
```
</details>

<details>
<summary>📈 Time Series Analysis</summary>

```
# Trends over time
You> Show me how forest area changes from 2020 to 2100

# Specific periods
You> What happens between 2040 and 2050 in terms of urban expansion?

# Rate of change
You> Which decade has the fastest cropland growth?
```
</details>

## Data Formats

The agent can work with multiple formats:

### Databases
```
You> Query processed/landuse_transitions.db: SELECT COUNT(*) FROM landuse_transitions WHERE scenario = 'Baseline'
```

### CSV Files
```
You> Analyze the sample_data.csv file
You> Query sample_data.csv: SELECT category, AVG(price) FROM data GROUP BY category
```

### JSON Files
```
You> Read the inventory.json file
You> Convert inventory.json to a Parquet file
```

### Parquet Files
```
You> Get statistics for sensor_data.parquet
You> Query sensor_data.parquet: SELECT sensor_id, AVG(temperature) FROM data GROUP BY sensor_id
```

## Export Results

Save query results in different formats:

```
You> Export the top 100 urban growth counties to a CSV file
You> Save forest transition data for California as Parquet
You> Export the landuse_transitions table to JSON format
```

## Next Steps

Now that you've run your first queries:

1. **Learn more query techniques** → [Natural Language Queries](../queries/overview.md)
2. **Understand the data** → [Data Schemas](../data/schema.md)
3. **See advanced examples** → [Query Examples](../queries/examples.md)
4. **Customize the agent** → [Configuration](configuration.md)

## Getting Help

- Type `help` in the agent for available commands
- Check [example queries](../queries/examples.md) for inspiration
- See [troubleshooting](../troubleshooting.md) for common issues