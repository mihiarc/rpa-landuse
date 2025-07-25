# LangGraph Agent API Reference

## Overview

The LangGraph Agent is the modern, graph-based natural language agent for RPA Land Use Analytics. It provides enhanced state management, conversation memory, and streaming capabilities compared to the traditional LangChain agent.

## Key Features

- **Graph-based Architecture**: Uses LangGraph for complex workflow orchestration
- **Conversation Memory**: Built-in checkpointing for session continuity
- **Streaming Support**: Real-time response streaming
- **Enhanced Error Handling**: Graceful recovery from failures
- **RPA Context Aware**: Specialized for 2020 RPA Assessment data

## Usage

### Command Line Interface

```bash
# Start the interactive agent
uv run python -m landuse.agents.langgraph_agent

# Or use the CLI shortcut
uv run rpa-analytics
```

### Python API

```python
from landuse.agents.langgraph_agent import LanduseLangGraphAgent

# Initialize the agent
agent = LanduseLangGraphAgent(
    db_path="data/processed/landuse_analytics.duckdb",
    model_name="claude-3-5-sonnet-20241022",  # or "gpt-4o-mini"
    temperature=0.1
)

# Query the agent
result = await agent.aquery("Which RPA scenarios show the most forest loss?")
print(result)

# Or use synchronous API
result = agent.query("Compare urban expansion between LM and HH scenarios")
print(result)
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

The agent maintains state using TypedDict:

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    results: Optional[str]
    error: Optional[str]
    iterations: int
    max_iterations: int
```

## Available Tools

### execute_landuse_query
Executes DuckDB SQL queries on the RPA database.

```python
# Example usage
"Execute SQL: SELECT * FROM dim_scenario WHERE rcp_scenario = 'rcp85'"
```

### get_schema_info
Returns detailed schema information about the RPA database.

```python
# Returns star schema structure with RPA context
"Get database schema information"
```

### suggest_query_examples
Provides example queries for common RPA analysis patterns.

```python
# Categories: agricultural_loss, urbanization, climate_comparison, time_series
"Suggest query examples for climate_comparison"
```

### explain_query_results
Interprets query results in RPA business context.

```python
"Explain these results: [query results]"
```

### get_default_assumptions
Shows default assumptions for scenarios, time periods, and geography.

```python
"What are the default analysis assumptions?"
```

### get_state_code
Converts state names to FIPS codes.

```python
"Get state code for California"
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

The LangGraph agent powers the Streamlit chat interface:

```python
# In Streamlit app
import streamlit as st
from landuse.agents.langgraph_agent import LanduseLangGraphAgent

agent = LanduseLangGraphAgent()

# Stream responses
for chunk in agent.stream(user_query):
    st.write(chunk)
```

## Comparison with Traditional Agent

| Feature | LangGraph Agent | Traditional Agent |
|---------|----------------|-------------------|
| Architecture | Graph-based | Linear REACT |
| State Management | Built-in checkpointing | Session-based |
| Streaming | Native support | Not supported |
| Error Recovery | Advanced retry logic | Basic error handling |
| Memory | Conversation history | Single query |
| Performance | Optimized iteration | Standard execution |

## API Methods

### query(question: str) -> str
Synchronous query method for simple interactions.

### aquery(question: str) -> str
Asynchronous query method for better performance.

### stream(question: str) -> Iterator[str]
Streaming method for real-time responses.

### astream(question: str) -> AsyncIterator[str]
Asynchronous streaming for web applications.

### clear_memory()
Clears conversation history and resets state.

## Best Practices

1. **Use specific RPA terminology**: Reference scenarios (LM, HL, HM, HH) and models by name
2. **Leverage defaults**: Agent uses intelligent defaults when parameters aren't specified
3. **Ask follow-up questions**: Agent maintains context across queries
4. **Handle streaming**: Use async methods for better user experience
5. **Monitor iterations**: Set appropriate limits for complex queries