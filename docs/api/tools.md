# Tools API Reference

Detailed documentation of all tools available to the unified **LanduseAgent** for RPA land use analytics.

## Overview

The LanduseAgent uses a collection of specialized tools for RPA data analysis, geographic processing, and natural language interaction. Each tool is designed to handle specific RPA analytical tasks while maintaining consistency and error handling.

## Tool Categories

### 🌾 Core RPA Analysis Tools

Specialized tools for RPA land use data analysis:

| Tool | Function | Parameters | Example |
|------|----------|------------|---------|
| `execute_landuse_query` | Execute DuckDB SQL on RPA data | `query: str` | "Which scenarios show most forest loss?" |
| `analyze_landuse_results` | Interpret results in RPA context | `results: str` | "Explain these urbanization patterns" |
| `get_schema_info` | Show RPA database schema | `table_name: str` | "What tables are available?" |
| `get_state_code` | Convert state names to FIPS codes | `state_name: str` | "Show me data for California" |

### 🗺️ Optional Geographic Tools

Enhanced tools available when map generation is enabled:

| Tool | Function | Parameters | Example |
|------|----------|------------|---------|
| `create_choropleth_map` | Generate county-level maps | `data_query: str` | "Map agricultural losses by county" |
| `create_heatmap` | Create data heatmaps | `data: str` | "Show urbanization hotspots" |

### 📚 Optional Knowledge Tools

RPA methodology and documentation tools:

| Tool | Function | Parameters | Example |
|------|----------|------------|---------|
| `rpa_knowledge_retriever` | Access RPA methodology docs | `question: str` | "What is the forest projection methodology?" |

## Core Tool Details

### execute_landuse_query

```python
def execute_landuse_query(query: str) -> str
```

**Purpose:** Execute optimized SQL queries on the RPA DuckDB database

**Features:**
- Star schema-aware query execution
- Automatic performance optimization
- Error handling with helpful suggestions
- Result formatting for terminal display
- Query safety with row limits

**Returns:**
- Formatted query results with business context
- Summary statistics when appropriate
- Error messages with suggestions for fixes

**Example:**
```python
agent.query("Which scenarios show the most agricultural land loss?")
# Internally calls execute_landuse_query with optimized SQL
```

### analyze_landuse_results

```python
def analyze_landuse_results(results: str, context: str = "") -> str
```

**Purpose:** Provide business interpretation of RPA query results

**Features:**
- RPA scenario expertise and context
- Climate and socioeconomic impact analysis
- Geographic pattern recognition
- Policy and planning implications
- Cross-scenario comparisons

**Returns:**
- Business interpretation of numerical results
- Key insights and implications
- Recommendations for further analysis
- Context about RPA methodology

**Example:**
```python
# After executing a query about forest loss
results = "RCP85/SSP5 scenarios show 15M acres of forest loss..."
analysis = analyze_landuse_results(results)
# Returns: "This represents the highest warming scenario combined with..."
```

### get_schema_info

```python
def get_schema_info(table_name: str = None) -> str
```

**Purpose:** Provide RPA database schema information and guidance

**Features:**
- Complete star schema documentation
- Business-friendly column descriptions
- Common query patterns and examples
- Relationship mapping between tables
- Data quality and coverage notes

**Parameters:**
- `table_name` (optional): Specific table to describe, or None for full schema

**Example:**
```python
agent.query("What tables are available?")
# Shows: fact_landuse_transitions, dim_scenario, dim_geography_enhanced, etc.

agent.query("Describe the scenario table")
# Shows: scenario_id, scenario_name, rcp_scenario, ssp_scenario, etc.
```

### get_state_code

```python
def get_state_code(state_name: str) -> str
```

**Purpose:** Convert state names to FIPS codes for geographic filtering

**Features:**
- Fuzzy matching for state names
- Abbreviation support (CA, TX, FL, etc.)
- Full state name support (California, Texas, Florida)
- Error handling for invalid states
- Returns both FIPS codes and state names

**Example:**
```python
agent.query("Show me data for California")
# Internally converts "California" to FIPS code "06"

agent.query("Compare Texas and Florida urbanization")
# Converts "Texas" -> "48" and "Florida" -> "12"
```

## Enhanced Tool Configuration

### Map Generation Tools

Enable map generation in your configuration:

```python
from landuse.config import LanduseConfig

config = LanduseConfig(enable_map_generation=True)
agent = LanduseAgent(config=config)

# Now you can ask for maps
agent.query("Create a map showing urban growth by county")
```

#### create_choropleth_map

```python
def create_choropleth_map(data_query: str, map_type: str = "county") -> str
```

**Purpose:** Generate geographic visualizations of RPA data

**Features:**
- County-level choropleth maps
- Automatic data aggregation
- Professional styling and legends
- Multiple map types (forest, urban, agricultural)
- Saves maps to `maps/agent_generated/` directory

**Example:**
```python
agent.query("Map forest loss by county in California")
# Creates: maps/agent_generated/county_map_forest_california_YYYYMMDD_HHMMSS.png
```

### Knowledge Base Tools

Enable RPA methodology access:

```python
config = LanduseConfig(enable_knowledge_base=True)
agent = LanduseAgent(config=config)

# Now you can ask methodology questions
agent.query("What assumptions are used in the forest projection model?")
```

#### rpa_knowledge_retriever

```python
def rpa_knowledge_retriever(question: str) -> str
```

**Purpose:** Access RPA Assessment methodology documentation

**Features:**
- Vector search across RPA technical documents
- Contextual retrieval of methodology details
- References to specific chapters and sections
- Integration with query results for deeper analysis

**Example:**
```python
agent.query("What is the economic model used for land use projections?")
# Retrieves relevant sections from RPA technical documentation
```

## Tool Error Handling

### Database Connection Errors

```python
# Automatic retry logic
def execute_landuse_query(query: str) -> str:
    try:
        return execute_query_with_retry(query)
    except DatabaseError as e:
        return f"Database error: {e}. Try rephrasing your question."
```

### SQL Generation Errors

```python
# Helpful error recovery
def handle_sql_error(error: str, original_query: str) -> str:
    suggestions = [
        "Try using specific scenario names (like 'RCP45' or 'SSP1')",
        "Specify state names or FIPS codes for geographic queries",
        "Check table and column names with 'What tables are available?'"
    ]
    return f"SQL Error: {error}\n\nSuggestions:\n" + "\n".join(suggestions)
```

### Geographic Query Errors

```python
# State name validation
def validate_geography(location: str) -> str:
    if location not in valid_states:
        suggestions = find_similar_states(location)
        return f"Unknown location: {location}. Did you mean: {suggestions}?"
```

## Tool Integration Patterns

### Sequential Tool Usage

```python
# Common pattern: Query -> Analyze -> Map
1. execute_landuse_query("Agricultural losses by county in Texas")
2. analyze_landuse_results(results, "Focus on policy implications")
3. create_choropleth_map("Texas agricultural losses")  # If maps enabled
```

### Cross-Tool Validation

```python
# Schema validation before queries
1. get_schema_info("dim_scenario")  # Check available scenarios
2. execute_landuse_query("SELECT * FROM dim_scenario LIMIT 5")
3. analyze_landuse_results(results, "Explain scenario differences")
```

### Geographic Tool Chain

```python
# Geographic analysis workflow
1. get_state_code("California")  # Convert to FIPS: "06"
2. execute_landuse_query("Query for state_code = '06'")
3. create_choropleth_map("California county analysis")
```

## Performance Considerations

### Query Optimization

- **Automatic LIMIT clauses**: Tools add appropriate row limits
- **Star schema awareness**: Optimized joins across dimension tables
- **Column selection**: Only retrieve necessary columns
- **Filter pushdown**: Apply filters early in query execution

### Caching

- **Schema information**: Cached to avoid repeated database calls
- **State code mappings**: Pre-loaded for instant lookup
- **Common queries**: Results cached for conversation continuity

### Resource Management

- **Connection pooling**: Efficient database connection management
- **Memory limits**: Large result sets are automatically sampled
- **Timeout handling**: Prevents runaway queries

## Best Practices

### Tool Selection

1. **Start with schema**: Use `get_schema_info` to understand available data
2. **Geography first**: Use `get_state_code` for location-based queries
3. **Query execution**: Use `execute_landuse_query` for data retrieval
4. **Business analysis**: Use `analyze_landuse_results` for interpretation
5. **Visualization**: Use map tools for geographic insights (if enabled)

### Error Recovery

1. **Read error messages**: Tools provide specific guidance
2. **Check schema**: Verify table and column names
3. **Simplify queries**: Start with basic queries and build complexity
4. **Use examples**: Reference help system for query patterns

### Performance Optimization

1. **Be specific**: Use filters to reduce data scope
2. **Geographic focus**: Specify states or regions when possible
3. **Scenario selection**: Filter to relevant RCP/SSP combinations
4. **Time periods**: Specify relevant years for analysis

## Tool Development

### Adding Custom Tools

```python
from landuse.agents import LanduseAgent
from langchain_core.tools import Tool

class CustomRPAAgent(LanduseAgent):
    def __init__(self, config=None):
        super().__init__(config)
        self.tools.extend(self._create_custom_tools())
    
    def _create_custom_tools(self):
        return [
            Tool(
                name="calculate_carbon_impact",
                func=self._calculate_carbon_impact,
                description="Calculate carbon impact of land use changes"
            )
        ]
    
    def _calculate_carbon_impact(self, params: str) -> str:
        # Custom carbon analysis implementation
        return "Carbon impact analysis results"
```

### Tool Testing

```python
import pytest
from landuse.tools.common_tools import execute_landuse_query

def test_execute_landuse_query():
    result = execute_landuse_query("SELECT COUNT(*) FROM dim_scenario")
    assert "scenarios" in result.lower()
    assert "error" not in result.lower()
```

## Next Steps

- See [Agent API](agent.md) for complete LanduseAgent documentation
- Review [Query Examples](../queries/examples.md) for tool usage patterns
- Check [Configuration Guide](../getting-started/configuration.md) for enabling optional tools
- See [Development Guide](../development/architecture.md) for extending tools