# LanduseAgent API Reference

Complete API reference for the unified RPA Land Use Analytics agent.

## Overview

The **LanduseAgent** is the primary and only agent for RPA Land Use Analytics. It provides a unified interface for natural language queries about USDA Forest Service RPA Assessment data with both simple and advanced execution modes.

### 🌾 **Unified Architecture**
Single agent class that combines:
- **Natural Language Processing**: Converts questions to optimized DuckDB SQL
- **LangGraph Integration**: Graph-based workflows for complex analysis
- **Memory Management**: Conversation history and state persistence
- **Rich Formatting**: Beautiful terminal output with Rich library
- **RPA Expertise**: Specialized knowledge of 2020 RPA Assessment data

```python
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig

# Initialize with default configuration
agent = LanduseAgent()

# Ask natural language questions
result = agent.query("Which scenarios show the most agricultural land loss?")
print(result)
```

---

```python
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig

# Initialize with default configuration
agent = LanduseAgent()

# Initialize with custom configuration
config = LanduseConfig(
    model_name="claude-3-5-sonnet-20241022", 
    enable_map_generation=True,
    enable_memory=True,
    debug=True
)
agent = LanduseAgent(config=config)

# Run a query
result = agent.query("Show me the tables in the database")
```

## Class: LanduseAgent

### Constructor

```python
LanduseAgent(config: LanduseConfig = None)
```

**Parameters:**
- `config` (LanduseConfig, optional): Configuration object. If None, uses default configuration from environment variables.

**Example:**
```python
# Use default configuration
agent = LanduseAgent()

# Use agent-specific configuration
config = LanduseConfig.for_agent_type('map', verbose=True)
agent = LanduseAgent(config=config)
```

### Methods

#### query(question: str, use_graph: bool = False, thread_id: Optional[str] = None) -> str

Execute a natural language query and return results.

**Parameters:**
- `question` (str): Natural language question about RPA data
- `use_graph` (bool): Whether to use LangGraph workflow (default: False)
- `thread_id` (Optional[str]): Thread ID for conversation memory

**Returns:**
- `str`: Query results formatted as text with business context

**Example:**
```python
result = agent.query("What are the top 5 counties by urban growth?")
print(result)

# With graph workflow and memory
result = agent.query(
    "Compare this to agricultural land loss", 
    use_graph=True, 
    thread_id="analysis_session"
)
```

#### simple_query(question: str) -> str

Direct LLM interaction without LangGraph (recommended for production).

**Parameters:**
- `question` (str): Natural language question

**Returns:**
- `str`: Formatted response with query results and analysis

**Example:**
```python
result = agent.simple_query("Show me forest transition patterns")
print(result)
```

#### stream_query(question: str, thread_id: Optional[str] = None) -> Iterator[Any]

Streaming query execution for real-time responses.

**Parameters:**
- `question` (str): Natural language question
- `thread_id` (Optional[str]): Thread ID for memory

**Yields:**
- Response chunks for real-time display

**Example:**
```python
for chunk in agent.stream_query("Analyze urbanization trends"):
    print(chunk, end="")
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

The LanduseAgent has access to specialized tools for RPA data analysis:

### Core RPA Analysis Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `execute_landuse_query` | Execute DuckDB SQL on RPA data | "Which scenarios show most forest loss?" |
| `analyze_landuse_results` | Interpret results in RPA context | "Explain these urbanization patterns" |
| `get_schema_info` | Show RPA database schema | "What tables are available?" |
| `get_state_code` | Convert state names to FIPS codes | "Show me data for California" |

### Optional Enhancement Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `rpa_knowledge_retriever` | Access RPA methodology docs | "What is the forest projection methodology?" |
| `create_choropleth_map` | Generate geographic visualizations | "Map agricultural losses by county" |
| `create_heatmap` | Create data heatmaps | "Show urbanization hotspots" |

**Note**: Map generation and knowledge base tools are optional and controlled by configuration.

## Query Patterns

### RPA Scenario Analysis

```python
# Climate scenario comparisons
agent.query("Compare forest loss between RCP45 and RCP85 scenarios")

# Socioeconomic scenario analysis
agent.query("Which SSP scenarios show the most urban expansion?")

# Model ensemble analysis
agent.query("Show variation across different climate models")
```

### Geographic Analysis

```python
# State-level analysis
agent.query("Which states have the most agricultural land loss?")

# Regional comparisons
agent.query("Compare urbanization between the South and Midwest")

# County-level patterns
agent.query("Show me the top 10 counties for forest to urban conversion")
```

### Land Use Transition Analysis

```python
# Transition matrices
agent.query("What land use types are converting to urban?")

# Agricultural analysis
agent.query("How much cropland is being lost to development?")

# Forest analysis
agent.query("Show me forest conversion patterns by scenario")
```

### Temporal Analysis

```python
# Time series trends
agent.query("Show urbanization trends from 2020 to 2070")

# Acceleration patterns
agent.query("When does urban expansion accelerate the most?")

# Cumulative changes
agent.query("Total land use change by 2100 under high warming")
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

The LanduseAgent maintains conversation context across queries:

```python
# Initialize conversation context
agent.query("Show me counties in California")

# Follow-up queries use conversation history
agent.query("Now show me just the ones with high urban growth")
# Agent remembers we're analyzing California counties

# Context persists across multiple queries
agent.query("What scenarios show the biggest changes?")
# Still in California context

# Clear context when needed
agent.clear_history()
agent.query("Now analyze Texas counties")  # Fresh context
```

### Memory Configuration

```python
# Enable persistent memory with thread IDs
config = LanduseConfig(enable_memory=True)
agent = LanduseAgent(config=config)

# Use graph mode for advanced memory features
result = agent.query(
    "Analyze forest trends", 
    use_graph=True, 
    thread_id="forest_analysis_session"
)

# Continue conversation in same thread
result = agent.query(
    "Now compare to agricultural trends", 
    use_graph=True, 
    thread_id="forest_analysis_session"
)
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

# Set configuration via environment variables
os.environ['LANDUSE_MODEL'] = 'gpt-4o'
os.environ['TEMPERATURE'] = '0.1'
os.environ['MAX_TOKENS'] = '4000'

# Initialize with configuration
config = LanduseConfig.from_env()
agent = LanduseAgent(config=config)
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

### RPA Analysis Pipeline

```python
# RPA scenario analysis pipeline
def analyze_scenario(scenario_name):
    config = LanduseConfig(enable_memory=True)
    agent = LanduseAgent(config=config)
    
    # Get scenario overview
    overview = agent.query(f"Analyze {scenario_name} scenario overview")
    
    # Agricultural impacts
    ag_impacts = agent.query(f"Show agricultural impacts in {scenario_name}")
    
    # Forest transitions
    forest_changes = agent.query(f"Analyze forest changes in {scenario_name}")
    
    # Geographic patterns
    geo_patterns = agent.query(f"Show geographic patterns for {scenario_name}")
    
    return {
        'overview': overview,
        'agriculture': ag_impacts,
        'forest': forest_changes,
        'geography': geo_patterns
    }

# Batch scenario comparison
def compare_scenarios(scenarios):
    agent = LanduseAgent()
    results = {}
    
    for scenario in scenarios:
        agent.clear_history()  # Fresh context for each scenario
        results[scenario] = analyze_scenario(scenario)
    
    return results
```

### Web Service Integration

```python
from flask import Flask, request, jsonify
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig

app = Flask(__name__)
# Disable memory for stateless web service
config = LanduseConfig(enable_memory=False, debug=False)
agent = LanduseAgent(config=config)

@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query')
    thread_id = request.json.get('thread_id')  # Optional
    
    # Use simple_query for web service stability
    result = agent.simple_query(user_query)
    
    return jsonify({
        'result': result,
        'thread_id': thread_id,
        'model': agent.model_name
    })

@app.route('/stream', methods=['POST'])
def stream_query():
    user_query = request.json.get('query')
    thread_id = request.json.get('thread_id')
    
    def generate():
        for chunk in agent.stream_query(user_query, thread_id):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')
```

## Advanced Features

### Custom Tools and Subgraphs

Extend the LanduseAgent with specialized capabilities:

```python
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig
from langchain_core.tools import Tool

class CustomRPAAgent(LanduseAgent):
    def __init__(self, config: LanduseConfig = None):
        super().__init__(config)
        # Add custom RPA-specific tools
        self.custom_tools = self._create_custom_tools()
    
    def _create_custom_tools(self):
        return [
            Tool(
                name="calculate_carbon_impact",
                func=self._calculate_carbon_impact,
                description="Calculate carbon impact of land use changes"
            ),
            Tool(
                name="assess_water_resources",
                func=self._assess_water_impact,
                description="Assess water resource implications"
            )
        ]
    
    def create_sustainability_subgraph(self):
        """Create specialized subgraph for sustainability analysis."""
        sustainability_tools = self.tools + self.custom_tools
        return self.create_subgraph("sustainability", sustainability_tools)
    
    def _calculate_carbon_impact(self, params: str) -> str:
        # Custom carbon analysis implementation
        return "Carbon impact analysis results"
    
    def _assess_water_impact(self, params: str) -> str:
        # Custom water resource analysis
        return "Water resource impact assessment"
```

### Extending Functionality

```python
# Enable map generation in configuration
config = LanduseConfig(enable_map_generation=True)
agent = LanduseAgent(config=config)

# Generate geographic visualizations
agent.query("Create a map showing urban growth by county")

# Use map subgraph for complex geographic analysis
map_subgraph = agent.create_map_subgraph()

# Access RPA methodology documentation
config = LanduseConfig(enable_knowledge_base=True)
agent = LanduseAgent(config=config)
agent.query("What assumptions are used in the forest projection model?")

# Advanced analysis with custom prompts
from landuse.agents.prompts import create_custom_prompt
custom_prompt = create_custom_prompt(
    analysis_style="detailed",
    domain_focus="forest_economics"
)
```

## Best Practices

1. **Use RPA Terminology**: Reference scenarios (LM, HL, HM, HH), models (RCP45/85, SSP1/5), and land use types correctly
2. **Start with Simple Queries**: Use `simple_query()` or `query(use_graph=False)` for production
3. **Leverage Context**: Build up analysis through conversation history
4. **Geographic Specificity**: Specify states, regions, or counties for focused analysis
5. **Scenario Comparisons**: Compare multiple scenarios to understand uncertainty
6. **Error Recovery**: Agent provides helpful suggestions when queries fail
7. **Performance**: Agent automatically optimizes queries with appropriate limits

## Next Steps

- See [Query Examples](../queries/examples.md) for more patterns
- Review [Converters API](converters.md) for data processing
- Check [Tools Reference](tools.md) for detailed tool documentation