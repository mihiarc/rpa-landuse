# RPA Land Use Analytics Agent

## Overview

The RPA Land Use Analytics project uses a unified AI agent built with LangGraph to enable natural language analysis of land use data. The agent converts questions in plain English to optimized SQL queries and provides business insights.

## Architecture

### Single Unified Agent: `LanduseAgent`

The project uses a single, configurable agent class that provides all functionality:

```python
from landuse.agents import LanduseAgent

# Create an agent
agent = LanduseAgent()

# Query the data
response = agent.query("Which scenarios show the most agricultural land loss?")

# Interactive chat mode
agent.chat()
```

### Key Features

- **Natural Language Processing**: Converts questions to SQL queries
- **Business Intelligence**: Provides insights and summary statistics
- **Map Generation**: Optional choropleth map creation
- **Conversation Memory**: Optional conversation history
- **Multi-Model Support**: Works with GPT-4, Claude, and other LLMs

## Configuration

### Basic Usage

```python
# Default configuration
agent = LanduseAgent()
```

### Advanced Configuration

```python
from landuse.agents import LanduseAgent
from landuse.models import AgentConfig

# Using configuration object
config = AgentConfig(
    model_name="gpt-4",
    temperature=0.1,
    max_tokens=4000
)
agent = LanduseAgent(config=config)

# Or using parameters
agent = LanduseAgent(
    model_name="claude-3-5-sonnet-20241022",
    temperature=0.0,
    enable_maps=True,
    enable_memory=True
)
```

### Configuration Options

- `db_path`: Path to DuckDB database (default: `data/processed/landuse_analytics.duckdb`)
- `model_name`: LLM model to use (default: `claude-3-5-sonnet-20241022`)
- `temperature`: Model temperature 0.0-2.0 (default: `0.1`)
- `max_tokens`: Maximum response tokens (default: `4000`)
- `enable_memory`: Enable conversation memory (default: `False`)
- `enable_maps`: Enable map generation tools (default: `False`)
- `verbose`: Enable verbose logging (default: `False`)

## Tools

The agent has access to these tools:

### Core Tools (Always Available)
- `execute_landuse_query`: Execute SQL queries on the database
- `get_schema_info`: Get database schema information
- `suggest_query_examples`: Get example queries
- `get_state_code`: Convert state names to codes
- `get_default_assumptions`: Get default analysis assumptions

### Optional Tools
- `create_choropleth_map`: Generate maps (when `enable_maps=True`)

## Usage Examples

### Basic Queries

```python
agent = LanduseAgent()

# Agricultural analysis
response = agent.query("How much agricultural land is being lost?")

# Climate scenarios
response = agent.query("Compare forest loss between RCP45 and RCP85")

# Geographic patterns
response = agent.query("Which states have the most urban expansion?")
```

### Map Generation

```python
# Enable maps
agent = LanduseAgent(enable_maps=True)

# Generate visualizations
response = agent.query("Show me a map of forest coverage by state")
```

### Interactive Chat

```python
agent = LanduseAgent()
agent.chat()  # Starts interactive mode
```

## Implementation Details

### LangGraph Architecture

The agent uses LangGraph's StateGraph for control flow:

1. **State Management**: Tracks messages, queries, results, and context
2. **Graph Nodes**: Agent reasoning and tool execution nodes
3. **Conditional Edges**: Dynamic routing based on tool calls
4. **Memory Support**: Optional checkpointing for conversation history

### Query Processing Flow

1. User asks a natural language question
2. Agent analyzes the question and database schema
3. Agent generates appropriate SQL query
4. Query is executed with safety limits
5. Results are formatted and analyzed
6. Business insights are provided

## Environment Variables

Configure via environment variables:

```bash
# Required
OPENAI_API_KEY=your_key       # For GPT models
ANTHROPIC_API_KEY=your_key    # For Claude models

# Optional
LANDUSE_MODEL=gpt-4          # Model choice
TEMPERATURE=0.1              # Model temperature
MAX_TOKENS=4000              # Response limit
LANDUSE_DB_PATH=path/to/db   # Database location
```

## Best Practices

1. **Start Simple**: Use default configuration for most cases
2. **Enable Features as Needed**: Add maps/memory only when required
3. **Use Appropriate Models**: GPT-4 for complex reasoning, GPT-3.5 for speed
4. **Set Reasonable Limits**: Configure max_tokens based on expected response size

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure environment variables are set
2. **Database Not Found**: Check LANDUSE_DB_PATH or use setup script
3. **Timeout Errors**: Simplify queries or increase limits
4. **Memory Errors**: Disable memory for one-off queries

### Debug Mode

Enable verbose logging for troubleshooting:

```python
agent = LanduseAgent(verbose=True)
```

## API Reference

### LanduseAgent

```python
class LanduseAgent:
    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        verbose: bool = False,
        config: Optional[AgentConfig] = None,
        enable_memory: bool = False,
        enable_maps: bool = False
    )
    
    def query(self, natural_language_query: str) -> str:
        """Process a natural language query"""
        
    def chat(self):
        """Start interactive chat mode"""
```

## Summary

The RPA Land Use Analytics agent provides a simple yet powerful interface for analyzing land use data through natural language. The unified architecture makes it easy to use while remaining flexible enough for advanced use cases.