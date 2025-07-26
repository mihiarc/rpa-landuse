# LanduseAgent API Reference

## Overview

The **LanduseAgent** is the unified, modern natural language agent for RPA Land Use Analytics. It combines graph-based LangGraph architecture with traditional query capabilities, providing enhanced state management, conversation memory, and streaming capabilities.

## Key Features

- **Unified Architecture**: Single agent class with both simple and graph-based execution modes
- **LangGraph Integration**: Graph-based workflow orchestration for complex queries
- **Conversation Memory**: Built-in conversation history and checkpointing
- **Streaming Support**: Real-time response streaming capabilities
- **Enhanced Error Handling**: Graceful recovery from failures with helpful suggestions
- **RPA Context Aware**: Specialized for 2020 RPA Assessment data analysis
- **Memory-First Design**: Modern 2025 architecture with persistent state

## Usage

### Command Line Interface

```bash
# Start the interactive agent
uv run python -m landuse.agents.landuse_agent

# Or use the package shortcut
uv run python -m landuse

# Or use the CLI shortcut if configured
uv run rpa-analytics
```

### Python API

```python
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig

# Initialize with default configuration
agent = LanduseAgent()

# Initialize with custom configuration
config = LanduseConfig(
    model_name="claude-3-5-sonnet-20241022",  # or "gpt-4o-mini"
    temperature=0.1,
    enable_memory=True,
    enable_map_generation=True
)
agent = LanduseAgent(config=config)

# Simple query (recommended for stability)
result = agent.query("Which RPA scenarios show the most forest loss?")
print(result)

# Graph-based query with memory
result = agent.query(
    "Compare urban expansion between scenarios", 
    use_graph=True, 
    thread_id="analysis_session_1"
)
print(result)

# Streaming query for real-time responses
for chunk in agent.stream_query("Show me agricultural trends", thread_id="stream_1"):
    print(chunk)
```

## Configuration

### Environment Variables

```bash
# Model selection (optional)
LANDUSE_MODEL=claude-3-5-sonnet-20241022  # Default

# API Keys (one required)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Database path (optional)
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb

# Execution limits (optional)
LANDUSE_MAX_ITERATIONS=5
LANDUSE_MAX_EXECUTION_TIME=120
LANDUSE_MAX_QUERY_ROWS=1000
```

### Agent State

The agent maintains state using TypedDict for LangGraph operations:

```python
class AgentState(TypedDict):
    """State definition for the landuse agent."""
    messages: list[BaseMessage]
    context: dict[str, Any]
    iteration_count: int
    max_iterations: int
```

### Configuration

The agent uses `LanduseConfig` for all configuration:

```python
from landuse.config import LanduseConfig

# Load from environment variables
config = LanduseConfig()

# Custom configuration
config = LanduseConfig(
    model_name="claude-3-5-sonnet-20241022",
    temperature=0.1,
    max_tokens=4000,
    enable_memory=True,
    enable_map_generation=False,
    debug=True
)
```

## Available Tools

The LanduseAgent uses a comprehensive set of tools for RPA data analysis:

### execute_landuse_query
Executes optimized DuckDB SQL queries on the RPA database.

```python
# The agent automatically converts natural language to SQL
"Which scenarios show the most agricultural land loss?"
# Generates and executes: SELECT s.scenario_name, SUM(f.acres) as acres_lost ...
```

### analyze_landuse_results
Provides business context and insights for query results.

```python
# Automatically interprets results in RPA context
"Explain the implications of this forest loss data"
```

### get_schema_info
Returns detailed schema information about the RPA star schema.

```python
# Shows table structure and relationships
"What tables are available in the database?"
```

### get_state_code
Converts state names to FIPS codes for geographic queries.

```python
# Handles state name variations
"Show me data for California"  # Automatically converts to state code
```

### Knowledge Base Integration (Optional)
If enabled, provides access to RPA methodology documentation.

```python
# When knowledge base is enabled
"What is the methodology behind forest transition projections?"
```

## Example Queries

### Basic RPA Analysis
```python
# Agricultural land loss
result = agent.query("How much agricultural land is projected to be lost by 2070?")

# Climate model comparison
result = agent.query("Compare forest loss between wet and dry climate models")

# Scenario analysis
result = agent.query("Which RPA scenario has the most urban expansion?")
```

### Advanced Analysis
```python
# Time series with specific scenario
result = agent.query("""
    Show me annual forest loss rates under the HH scenario 
    (high warming, high growth) from 2020 to 2070
""")

# Regional comparison
result = agent.query("""
    Compare agricultural transitions between the South and 
    Midwest regions under the sustainability scenario (LM)
""")

# Climate pathway analysis
result = agent.query("""
    What's the difference in total land use change between 
    RCP4.5 and RCP8.5 pathways across all socioeconomic scenarios?
""")
```

## Error Handling

The agent includes comprehensive error handling:

```python
try:
    result = agent.query("Invalid query")
except Exception as e:
    print(f"Query failed: {e}")
    # Agent provides helpful error messages and suggestions
```

## Performance Considerations

- **Query Optimization**: Agent automatically adds appropriate filters and limits
- **Memory Management**: Conversation history is pruned to maintain performance
- **Concurrent Queries**: Thread-safe for multiple simultaneous queries
- **Response Streaming**: Use async methods for real-time updates

## Integration with Streamlit

The LanduseAgent powers the Streamlit chat interface:

```python
# In Streamlit app
import streamlit as st
from landuse.agents import LanduseAgent
from landuse.config import LanduseConfig

# Initialize agent with Streamlit-optimized config
config = LanduseConfig(enable_memory=False, debug=False)
agent = LanduseAgent(config=config)

# Simple query for Streamlit (most stable)
response = agent.query(user_query)
st.write(response)

# Or streaming for real-time updates
for chunk in agent.stream_query(user_query, thread_id=st.session_state.get('thread_id')):
    st.write(chunk)
```

## Execution Modes

The LanduseAgent supports multiple execution modes:

| Mode | Description | Use Case | Stability |
|------|-------------|----------|----------|
| Simple Query | Direct LLM interaction | Most queries, production use | High |
| Graph Workflow | LangGraph state management | Complex analysis, development | Medium |
| Streaming | Real-time response chunks | UI applications | Medium |
| Chat Interface | Interactive terminal mode | Development, testing | High |

**Recommendation**: Use `simple_query()` or `query(use_graph=False)` for production applications.

## API Methods

### query(question: str, use_graph: bool = False, thread_id: Optional[str] = None) -> str
Main query method with flexible execution modes.

**Parameters:**
- `question`: Natural language question about RPA data
- `use_graph`: Whether to use LangGraph workflow (default: False for stability)
- `thread_id`: Optional thread ID for conversation memory

### simple_query(question: str) -> str
Direct LLM interaction without LangGraph state management (recommended).

### stream_query(question: str, thread_id: Optional[str] = None) -> Iterator[Any]
Streaming method for real-time responses using LangGraph.

### chat()
Interactive chat interface with rich terminal formatting.

### clear_history()
Clears conversation history and resets state.

### create_subgraph(name: str, specialized_tools: list[BaseTool]) -> StateGraph
Creates specialized subgraphs for complex workflows.

### create_map_subgraph() -> StateGraph
Creates a specialized subgraph for map-based analysis.

## Best Practices

1. **Use specific RPA terminology**: Reference scenarios (LM, HL, HM, HH) and models by name
2. **Leverage defaults**: Agent uses intelligent defaults when parameters aren't specified
3. **Ask follow-up questions**: Agent maintains context across queries
4. **Handle streaming**: Use async methods for better user experience
5. **Monitor iterations**: Set appropriate limits for complex queries