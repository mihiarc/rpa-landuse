# Pydantic Models Implementation

## Overview

This guide documents the comprehensive Pydantic v2 models implementation for the landuse project. These models provide type safety, automatic validation, and clear data contracts throughout the application.

## Benefits of Pydantic Models

1. **Type Safety**: Compile-time type checking with mypy
2. **Runtime Validation**: Automatic input validation with helpful error messages
3. **Documentation**: Self-documenting data structures
4. **Serialization**: Easy conversion to/from JSON, dict, etc.
5. **IDE Support**: Excellent autocomplete and type hints

## Core Models

### Agent Configuration

```python
from landuse import AgentConfig

# Create config with validation
config = AgentConfig(
    db_path="data/processed/landuse_analytics.duckdb",
    model_name="claude-3-5-sonnet-20241022",
    temperature=0.1,
    max_tokens=4000,
    max_iterations=5,
    max_execution_time=120
)

# Access validated attributes
print(config.db_path)  # Path object, verified to exist
print(config.temperature)  # Float between 0-2
```

### Query Models

```python
from landuse import QueryInput, SQLQuery, QueryResult

# Natural language query validation
query_input = QueryInput(
    query="Show me agricultural land loss",
    include_assumptions=True
)

# SQL query validation
sql_query = SQLQuery(
    sql="SELECT * FROM dim_landuse",
    description="List all land use types"
)
# Automatically validates:
# - Only SELECT/WITH queries allowed
# - No destructive operations

# Query results with metadata
result = QueryResult(
    success=True,
    data=df,  # pandas DataFrame
    execution_time=1.23,
    query="SELECT COUNT(*) FROM fact_landuse_transitions"
)
print(f"Processed {result.row_count:,} rows in {result.execution_time:.2f}s")
```

### Data Models

```python
from landuse import (
    LandUseType, LandUseCategory, 
    RCPScenario, SSPScenario,
    TransitionType
)

# Enums provide controlled vocabularies
land_use = LandUseType.CROP  # "cr"
category = LandUseCategory.AGRICULTURE
rcp = RCPScenario.RCP45  # "4.5"
ssp = SSPScenario.SSP1
transition = TransitionType.CHANGE

# Dimension models with validation
from landuse.models import GeographyDimension

geography = GeographyDimension(
    geography_id=1,
    fips_code="12345",  # Validated as 5 digits
    county_name="Example County",
    state_code="CA",
    state_name="California"
)
```

### Tool Input Models

```python
from landuse.models import (
    ExecuteQueryInput,
    SchemaInfoInput,
    StateCodeInput
)

# Tool inputs are validated before execution
execute_input = ExecuteQueryInput(
    sql_query="SELECT COUNT(*) FROM dim_scenario"
)

state_input = StateCodeInput(
    state_name="California"
)
```

## Converter Models

### Conversion Configuration

```python
from landuse import ConversionConfig, ConversionMode

config = ConversionConfig(
    input_file="data/raw/landuse.json",
    output_file="data/processed/landuse.duckdb",
    mode=ConversionMode.STREAMING,
    batch_size=100000,
    parallel_workers=8,
    memory_limit="16GB",
    show_progress=True
)

# Validates:
# - Input file exists and is JSON
# - Memory limit format (e.g., "8GB", "512MB")
# - Reasonable batch sizes and worker counts
```

### Processing Models

```python
from landuse import ProcessedTransition, ConversionStats

# Validated transition record
transition = ProcessedTransition(
    scenario_name="GCAM_RCP45_SSP1",
    climate_model="GCAM",
    rcp_scenario="4.5",
    ssp_scenario="SSP1",
    time_period="2020-2030",
    start_year=2020,
    end_year=2030,
    fips_code="06037",  # Validated FIPS
    county_name="Los Angeles",
    state_code="06",
    from_landuse="Crop",
    to_landuse="Urban",
    acres=1234.56,
    transition_type="change"  # Validated as change/stable
)

# Conversion statistics
stats = ConversionStats(
    total_records=5_400_000,
    processed_records=5_399_950,
    failed_records=50,
    processing_time=123.45
)
print(f"Success rate: {stats.success_rate():.2f}%")
print(f"Speed: {stats.records_per_second():.0f} records/sec")
```

## Integration Examples

### Agent Usage

```python
from landuse.agents import LanduseAgent
from landuse import AgentConfig, QueryInput

# Initialize with Pydantic config
config = AgentConfig(
    model_name="gpt-4o-mini",
    temperature=0.1,
    max_iterations=10
)

agent = LanduseAgent(config=config)

# Query with validation
query_input = QueryInput(
    query="Which states have the most urban expansion?"
)
response = agent.query(query_input.query)
```

### Database Connection

```python
from landuse.connections import DuckDBConnection
from landuse import QueryResult

conn = DuckDBConnection("landuse_db")

# Get validated query results
result: QueryResult = conn.query_with_result(
    "SELECT COUNT(*) as total FROM fact_landuse_transitions"
)

if result.success:
    print(f"Total transitions: {result.data['total'][0]:,}")
    print(f"Query took {result.execution_time:.3f}s")
else:
    print(f"Error: {result.error}")
```

### Streamlit Integration

```python
import streamlit as st
from landuse import ChatMessage, SystemStatus

# Track chat messages with validation
message = ChatMessage(
    role="user",
    content="Show me forest loss trends"
)
st.session_state.messages.append(message)

# System status monitoring
status = SystemStatus(
    database_connected=True,
    agent_initialized=True,
    model_name="claude-3-5-sonnet",
    database_path="/path/to/db",
    table_count=5,
    total_records=5_400_000
)
```

## Error Handling

Pydantic provides detailed validation errors:

```python
from landuse import AgentConfig
from pydantic import ValidationError

try:
    config = AgentConfig(
        temperature=3.0,  # Too high!
        max_tokens=-100   # Negative!
    )
except ValidationError as e:
    print(e.json(indent=2))
    # {
    #   "errors": [
    #     {
    #       "loc": ["temperature"],
    #       "msg": "ensure this value is less than or equal to 2",
    #       "type": "value_error.number.not_le"
    #     },
    #     {
    #       "loc": ["max_tokens"],
    #       "msg": "ensure this value is greater than 0",
    #       "type": "value_error.number.not_gt"
    #     }
    #   ]
    # }
```

## Best Practices

1. **Use Models at Boundaries**: Validate data at API endpoints, user inputs, and external data sources
2. **Leverage Validators**: Add custom validators for business logic
3. **Export Common Models**: Make models easily importable from package root
4. **Document Fields**: Use Field descriptions for self-documenting APIs
5. **Handle Validation Errors**: Catch ValidationError and provide user-friendly messages

## Migration Guide

To migrate existing code to use Pydantic models:

1. **Replace dict parameters with model instances**:
   ```python
   # Before
   agent.query({"query": "...", "limit": 50})
   
   # After
   agent.query(QueryInput(query="...", limit=50))
   ```

2. **Use enums instead of strings**:
   ```python
   # Before
   if landuse_type == "cr":
   
   # After
   if landuse_type == LandUseType.CROP:
   ```

3. **Return structured results**:
   ```python
   # Before
   return {"success": True, "data": df, "error": None}
   
   # After
   return QueryResult(success=True, data=df)
   ```

## Performance Considerations

- Pydantic v2 is 5-50x faster than v1
- Use `model_config = ConfigDict(extra="forbid")` to catch typos
- Leverage `.model_dump()` for efficient serialization
- Use `exclude=True` on fields that shouldn't be serialized

## Testing with Models

```python
import pytest
from landuse import QueryInput
from pydantic import ValidationError

def test_query_validation():
    # Valid query
    query = QueryInput(query="Show me data")
    assert query.include_assumptions is True  # Default
    
    # Invalid query (empty)
    with pytest.raises(ValidationError):
        QueryInput(query="")
    
    # Invalid query (too long)
    with pytest.raises(ValidationError):
        QueryInput(query="x" * 1001)
```

## Future Enhancements

1. **JSON Schema Generation**: Auto-generate API documentation
2. **OpenAPI Integration**: Use models for API spec generation
3. **Settings Management**: Use pydantic-settings for configuration
4. **Async Support**: Add async validators for I/O operations