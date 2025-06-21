# SQL Query Agents API

Complete API reference for our specialized SQL agents and their natural language interfaces.

## Overview

We provide two specialized agents for different data analysis needs:

### 🌾 **Landuse Natural Language Query Agent**
Specialized for landuse transition analysis - converts natural language questions into optimized DuckDB SQL queries.

**[📖 Complete Documentation →](landuse-query-agent.md)**

```python
from scripts.agents.landuse_query_agent import LanduseQueryAgent

# Initialize the specialized landuse agent
agent = LanduseQueryAgent()

# Ask natural language questions
result = agent.query("Which scenarios show the most agricultural land loss?")
```

### 🔍 **General SQL Query Agent**
Multi-database support for SQLite, DuckDB, CSV, JSON, and Parquet files.

```python
from scripts.agents.sql_query_agent import SQLQueryAgent

# Initialize the general SQL agent
agent = SQLQueryAgent(root_dir="./data")

# Run SQL queries on various data sources
result = agent.run("Show me the tables in landuse_transitions.db")
```

---

## General SQL Query Agent (Legacy)

The `SQLQueryAgent` is the original component that interprets natural language queries and performs data operations on various databases and files.

```python
from scripts.agents.data_engineering_agent import DataEngineeringAgent

# Initialize the agent
agent = DataEngineeringAgent(root_dir="./data")

# Run a query
result = agent.run("Show me the tables in landuse_transitions.db")
```

## Class: DataEngineeringAgent

### Constructor

```python
DataEngineeringAgent(root_dir: str = None)
```

**Parameters:**
- `root_dir` (str, optional): Root directory for file operations. Defaults to `PROJECT_ROOT_DIR` from environment or `"./data"`

**Example:**
```python
# Use default directory
agent = DataEngineeringAgent()

# Specify custom directory
agent = DataEngineeringAgent(root_dir="/path/to/data")
```

### Methods

#### run(query: str) -> str

Execute a natural language query and return results.

**Parameters:**
- `query` (str): Natural language query to execute

**Returns:**
- `str`: Query results formatted as text

**Example:**
```python
result = agent.run("What are the top 5 counties by urban growth?")
print(result)
```

#### chat()

Start an interactive chat session with rich terminal formatting.

**Example:**
```python
# Start interactive mode
agent.chat()
# Type 'exit' to quit
```

## Available Tools

The agent has access to numerous tools for data operations:

### File Management Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `list_files` | List files in directory | "Show me all files in the data folder" |
| `read_file` | Read file contents | "Read the README file" |
| `write_file` | Create/update files | "Save these results to output.txt" |
| `copy_file` | Copy files | "Copy the database to backup folder" |

### Data Analysis Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `read_csv` | Load CSV files | "Analyze the sample_data.csv file" |
| `read_parquet` | Load Parquet files | "Show me the sensor_data.parquet contents" |
| `analyze_dataframe` | Get detailed statistics | "Analyze the land use data in detail" |
| `query_data` | SQL queries on files | "Query the CSV: SELECT * FROM data WHERE value > 100" |

### Database Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `list_database_tables` | Show all tables | "What tables are in the database?" |
| `describe_database_table` | Get schema info | "Describe the landuse_transitions table" |
| `query_database` | Execute SQL | "Query the database: SELECT COUNT(*) FROM transitions" |
| `export_database_table` | Export to file | "Export the results to CSV" |

### Transformation Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `transform_data` | Convert formats | "Convert the JSON file to Parquet" |
| `optimize_storage` | Suggest optimal format | "What's the best format for this data?" |
| `json_to_database` | Convert large JSON | "Convert the JSON to a SQLite database" |

## Query Patterns

### Basic Information Queries

```python
# List available data
agent.run("Show me all data files")

# Get table information  
agent.run("What tables are in landuse_transitions.db?")

# View sample data
agent.run("Show me 5 rows from the landuse_transitions table")
```

### Analysis Queries

```python
# Aggregations
agent.run("What's the total urban area in 2050?")

# Comparisons
agent.run("Compare forest area between scenarios")

# Trends
agent.run("Show me urban growth trends by decade")
```

### Complex Queries

```python
# Multi-step analysis
agent.run("""
Find counties with the most forest loss, 
then show what that forest is converting to
""")

# Custom calculations
agent.run("""
Calculate the percentage of land that changes use 
vs stays the same for each scenario
""")
```

## Response Format

The agent returns responses in a structured format:

```
Query: [Generated SQL or operation]
Results: [Number of rows]

[Formatted data table or results]

[Additional context or explanations]
```

## Error Handling

The agent handles various error conditions gracefully:

```python
# File not found
result = agent.run("Read nonexistent.csv")
# Returns: "Error reading CSV: [Errno 2] No such file or directory"

# Invalid SQL
result = agent.run("Query with invalid SQL syntax")
# Returns: "Error executing query: [SQL error details]"

# Type mismatches
result = agent.run("Calculate the average of text columns")
# Returns: "No numeric columns found for calculation"
```

## Memory and Context

The agent maintains conversation context:

```python
# First query establishes context
agent.run("Show me counties in California")

# Follow-up query uses context
agent.run("Now show me just the ones with high urban growth")
# Agent remembers we're looking at California counties
```

## Performance Considerations

### Query Optimization

The agent automatically optimizes queries:
- Adds appropriate LIMIT clauses
- Uses indexes when available
- Filters early in query execution

### Large File Handling

For files over `MAX_FILE_SIZE_MB`:
- Automatic sampling for preview
- Streaming processing for conversions
- Progress indicators for long operations

## Configuration

The agent respects environment variables:

```python
import os

# Set configuration
os.environ['AGENT_MODEL'] = 'gpt-4-turbo-preview'
os.environ['TEMPERATURE'] = '0.1'
os.environ['MAX_TOKENS'] = '4000'

# Initialize with configuration
agent = DataEngineeringAgent()
```

## Integration Examples

### Programmatic Usage

```python
# Batch processing
queries = [
    "List all tables",
    "Count total records",
    "Show summary statistics"
]

results = {}
for query in queries:
    results[query] = agent.run(query)
```

### Pipeline Integration

```python
# Data processing pipeline
def analyze_county(fips_code):
    agent = DataEngineeringAgent()
    
    # Get county profile
    profile = agent.run(f"Show land use for FIPS {fips_code}")
    
    # Calculate changes
    changes = agent.run(f"Calculate land use changes for FIPS {fips_code}")
    
    # Export results
    agent.run(f"Export analysis for FIPS {fips_code} to CSV")
    
    return profile, changes
```

### Web Service Integration

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
agent = DataEngineeringAgent()

@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query')
    result = agent.run(user_query)
    return jsonify({'result': result})
```

## Advanced Features

### Custom Tools

Add custom analysis tools:

```python
class CustomAgent(DataEngineeringAgent):
    def _create_tools(self):
        tools = super()._create_tools()
        
        # Add custom tool
        tools.append(Tool(
            name="custom_metric",
            func=self._calculate_custom_metric,
            description="Calculate custom sustainability metric"
        ))
        
        return tools
    
    def _calculate_custom_metric(self, params):
        # Custom implementation
        pass
```

### Extending Functionality

```python
# Add visualization capabilities
agent.run("Create a chart showing urban growth trends")

# Add geographic analysis
agent.run("Show me a map of land use changes")

# Add statistical modeling
agent.run("Predict future land use based on trends")
```

## Best Practices

1. **Clear Queries**: Be specific about what you want
2. **Iterative Refinement**: Start broad, then narrow down
3. **Use Context**: Leverage the agent's memory for complex analyses
4. **Error Recovery**: Check for errors and refine queries as needed
5. **Performance**: Use appropriate limits and filters for large datasets

## Next Steps

- See [Query Examples](../queries/examples.md) for more patterns
- Review [Converters API](converters.md) for data processing
- Check [Tools Reference](tools.md) for detailed tool documentation