# Quick Start Guide

Get up and running with RPA Land Use Analytics in 5 minutes!

## Prerequisites

Make sure you've completed the [installation](installation.md) steps:

- ✅ Dependencies installed
- ✅ OpenAI API key configured
- ✅ Test agent runs successfully

## Your First Query

### 1. Start the RPA Analytics Agent

```bash
# Interactive command-line interface
uv run rpa-analytics

# Or launch the web dashboard
uv run streamlit run streamlit_app.py
```

### 2. Explore RPA Scenarios

Start by understanding the available RPA scenarios:

```
You> What RPA scenarios are available in the database?
```

The agent will show you the 20 integrated climate-socioeconomic scenarios.

### 3. Explore the RPA Database

Explore the star schema structure:

```
You> Describe the database schema
```

Response:
```
RPA Land Use Analytics Database:
  • fact_landuse_transitions: 5.4M land use changes
  • dim_scenario: 20 RPA climate-socioeconomic scenarios
  • dim_geography_enhanced: 3,075 US counties
  • dim_landuse: 5 land use categories
  • dim_time: 6 time periods (2012-2100)
```

### 4. Understand the Schema

```
You> Describe the landuse_transitions table
```

The agent will show columns, data types, and sample data.

## Natural Language Query Examples

### Basic RPA Queries

**Compare RPA scenarios:**
```
You> How does agricultural land loss differ between the LM and HH scenarios?
```

**Analyze climate models:**
```
You> Show me forest loss under the "hot" climate model
```

**Project future land use:**
```
You> What's the projected urban area in 2070 under high growth scenarios?
```

### Advanced RPA Queries

**Climate pathway comparison:**
```
You> Compare forest loss between RCP4.5 and RCP8.5 pathways
```

**Socioeconomic analysis:**
```
You> How does urban expansion differ between SSP1 (sustainability) and SSP5 (fossil-fueled)?
```

**Regional patterns:**
```
You> Show me agricultural transitions in the South region under the "dry" climate model
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
You> What are the main land use types in the RPA Assessment?

Agent> I'll query the RPA database to show you the land use categories.

📊 Analysis Assumptions:
- Using USDA Forest Service 2020 RPA Assessment categories

Query: SELECT landuse_name, landuse_category FROM dim_landuse ORDER BY landuse_id

Results: 5 land use types
- Crop (Agriculture)
- Pasture (Agriculture)
- Rangeland (Natural)
- Forest (Natural)
- Urban (Developed)
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