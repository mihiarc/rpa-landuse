# LangGraph Migration Guide

This guide provides detailed information about the migration from traditional LangChain REACT agents to the modern LangGraph architecture.

## Overview

The RPA Land Use Analytics project has been migrated to use LangGraph, which provides:
- **Graph-based control flow**: More explicit and debuggable agent behavior
- **State management**: Clear state transitions and checkpointing support
- **Better error handling**: Structured error states and recovery
- **Extensibility**: Easy to add new nodes and transitions

## Migration Status

### ✅ Completed
- Created new `BaseLangGraphAgent` abstract base class
- Migrated `LanduseNaturalLanguageAgent` to LangGraph architecture
- Created unified `LangGraphMapAgent` that properly extends natural language agent
- Added migration wrappers for backward compatibility
- Updated package imports and exports
- Created migration scripts and documentation

### 🚧 In Progress
- Streamlit integration updates
- Test suite migration
- Documentation updates

## Using the New Agents

### Command Line Usage

Both old and new agents are available during the migration period:

```bash
# Use the original agent (still works)
uv run landuse-agent

# Use the new LangGraph agent
uv run landuse-agent-v2
```

### Python API Usage

```python
# Option 1: Use migration wrappers (recommended)
from landuse.agents import create_natural_language_agent

# This will create a LangGraph agent by default
agent = create_natural_language_agent(
    db_path="data/processed/landuse_analytics.duckdb",
    use_langgraph=True  # Default is True
)

# Use the agent
result = agent.query("Which scenarios show the most agricultural land loss?")

# Option 2: Direct import of new agent
from landuse.agents.landuse_natural_language_agent_v2 import LanduseNaturalLanguageAgent

agent = LanduseNaturalLanguageAgent()
result = agent.query("Compare forest loss between RCP45 and RCP85")
```

### Backward Compatibility

To use the old agent during migration:

```python
from landuse.agents import create_natural_language_agent

# Explicitly request the old agent
agent = create_natural_language_agent(use_langgraph=False)
```

## Architecture Changes

### Old Architecture (LangChain REACT)
```
BaseLanduseAgent
├── LanduseNaturalLanguageAgent
├── LangGraphMapAgent (incorrectly inherits from base)
└── (other agents)
```

### New Architecture (LangGraph)
```
BaseLangGraphAgent (abstract)
├── LanduseNaturalLanguageAgent (v2)
│   └── LangGraphMapAgent (v2) - properly extends NL agent
└── (future agents)
```

## Key Differences

### State Management
The new agents use explicit state management:

```python
class BaseLanduseState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_query: Optional[str]
    sql_queries: list[str]
    query_results: list[dict[str, Any]]
    analysis_context: dict[str, Any]
    iteration_count: int
    max_iterations: int
```

### Graph-Based Control Flow
Instead of implicit REACT loops, we now have explicit graph nodes:

```python
workflow = StateGraph(state_schema=self.state_schema)

# Add nodes
workflow.add_node("process_query", self._process_query_node)
workflow.add_node("execute_sql", self._execute_sql_node)
workflow.add_node("analyze_results", self._analyze_results_node)

# Add edges
workflow.add_edge("process_query", "execute_sql")
workflow.add_edge("execute_sql", "analyze_results")
```

### Tool Integration
Tools are now integrated as graph nodes with the `@tool` decorator:

```python
@tool
def execute_landuse_query(sql_query: str) -> dict:
    """Execute SQL query on landuse database"""
    # Implementation
```

## Migration Checklist

- [x] Create new base agent class
- [x] Migrate natural language agent
- [x] Create unified map agent
- [x] Add migration wrappers
- [x] Update package exports
- [x] Create migration scripts
- [ ] Update Streamlit app
- [ ] Migrate test suite
- [ ] Update all documentation
- [ ] Remove old agents (after deprecation period)

## Running the Migration Script

To automatically update imports in your codebase:

```bash
uv run python scripts/migrate_to_langgraph.py --update
```

## Testing

Run the basic test script to verify the new agents work:

```bash
uv run python scripts/test_langgraph_basic.py
```

## Support

If you encounter issues during migration:
1. Check the migration report: `LANGGRAPH_MIGRATION.md`
2. Review the comprehensive summary: `LANGGRAPH_MIGRATION_SUMMARY.md`
3. Use `use_langgraph=False` to temporarily use old agents
4. Report issues to the development team

## Future Plans

1. **Phase 1** (Current): Dual support for old and new agents
2. **Phase 2**: Update all integrations to use new agents
3. **Phase 3**: Deprecate old agents with warnings
4. **Phase 4**: Remove old agent code

The migration is designed to be seamless with zero breaking changes for existing users.