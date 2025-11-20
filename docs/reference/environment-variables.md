# Environment Variables Reference

Complete reference for all environment variables used in the RPA Land Use Analytics project.

## Quick Start

Create a `config/.env` file with your configuration:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults shown)
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini
LANDUSE_AGENT__MAX_ITERATIONS=8
LANDUSE_DATABASE__PATH=data/processed/landuse_analytics.duckdb
```

## Configuration System

The project uses **AppConfig** (Pydantic v2) for unified configuration with environment variable support.

### Environment Variable Naming Convention

All application settings use the `LANDUSE_` prefix with double underscores (`__`) to denote nested sections:

```
LANDUSE_{SECTION}__{SETTING_NAME}

Examples:
LANDUSE_LLM__MODEL_NAME          → config.llm.model_name
LANDUSE_AGENT__MAX_ITERATIONS    → config.agent.max_iterations
LANDUSE_DATABASE__PATH           → config.database.path
```

## Required Variables

### OpenAI API Key

```bash
# Required for LLM functionality
OPENAI_API_KEY=sk-proj-...
```

**Description**: API key for OpenAI GPT models
**Required**: Yes
**Default**: None
**Format**: String starting with `sk-`
**Where to get**: https://platform.openai.com/api-keys

## Optional Variables by Section

### LLM Configuration

Control the language model behavior and parameters.

```bash
# Model selection
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini
```
**Options**: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`
**Default**: `gpt-4o-mini`
**Recommendation**:
- `gpt-4o-mini`: Best cost/performance balance (recommended)
- `gpt-4o`: Highest quality responses
- `gpt-3.5-turbo`: Fastest, lowest cost

```bash
# Temperature for response randomness
LANDUSE_LLM__TEMPERATURE=0.1
```
**Range**: 0.0 to 2.0
**Default**: 0.1
**Recommendation**: Keep low (0.0-0.2) for consistent SQL generation

```bash
# Maximum tokens in response
LANDUSE_LLM__MAX_TOKENS=4000
```
**Range**: 100 to 128000 (model-dependent)
**Default**: 4000
**Recommendation**: 4000 is sufficient for most queries

```bash
# Request timeout in seconds
LANDUSE_LLM__TIMEOUT=60
```
**Range**: 10 to 300
**Default**: 60
**Recommendation**: Increase if experiencing timeout errors

### Agent Configuration

Control agent behavior, limits, and features.

```bash
# Maximum LLM calls per query
LANDUSE_AGENT__MAX_ITERATIONS=8
```
**Range**: 1 to 20
**Default**: 8
**Description**: Maximum tool invocations before stopping
**Recommendation**: 8 is usually sufficient; increase for complex multi-step queries

```bash
# Query execution timeout
LANDUSE_AGENT__MAX_EXECUTION_TIME=120
```
**Range**: 30 to 600 seconds
**Default**: 120
**Description**: Maximum seconds for query execution
**Recommendation**: 120 for large queries; reduce for faster timeouts

```bash
# Maximum rows returned from database
LANDUSE_AGENT__MAX_QUERY_ROWS=1000
```
**Range**: 1 to 100000
**Default**: 1000
**Description**: Hard limit on query results
**Recommendation**: Increase for data exports; keep low for interactive use

```bash
# Default rows to display
LANDUSE_AGENT__DEFAULT_DISPLAY_LIMIT=50
```
**Range**: 1 to 1000
**Default**: 50
**Description**: Default rows shown in output
**Recommendation**: 50 for readable output; adjust based on preference

```bash
# Enable conversation memory
LANDUSE_AGENT__ENABLE_MEMORY=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Remember conversation context across queries
**Recommendation**: Keep enabled for multi-turn conversations

```bash
# Conversation history size
LANDUSE_AGENT__CONVERSATION_HISTORY_LIMIT=20
```
**Range**: 5 to 100
**Default**: 20
**Description**: Number of messages to retain in sliding window
**Recommendation**: 20 is good balance; increase for longer context

### Database Configuration

Control database connection and behavior.

```bash
# Database file path
LANDUSE_DATABASE__PATH=data/processed/landuse_analytics.duckdb
```
**Default**: `data/processed/landuse_analytics.duckdb`
**Description**: Path to DuckDB database file
**Recommendation**: Use absolute path for production deployments

```bash
# Connection pool size
LANDUSE_DATABASE__MAX_CONNECTIONS=10
```
**Range**: 1 to 100
**Default**: 10
**Description**: Maximum concurrent database connections
**Recommendation**: 10 for single-user; increase for multi-user deployments

```bash
# Query result cache TTL
LANDUSE_DATABASE__CACHE_TTL=3600
```
**Range**: 0 to 86400 seconds
**Default**: 3600 (1 hour)
**Description**: How long to cache query results
**Recommendation**: 3600 for development; lower for real-time data

```bash
# Read-only mode
LANDUSE_DATABASE__READ_ONLY=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Open database in read-only mode
**Recommendation**: Keep true for safety in production

### Security Configuration

Control security features and validation.

```bash
# Enable SQL injection prevention
LANDUSE_SECURITY__ENABLE_SQL_VALIDATION=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Validate SQL queries for safety
**Recommendation**: Always keep enabled

```bash
# Strict table name validation
LANDUSE_SECURITY__STRICT_TABLE_VALIDATION=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Enforce allowlist of valid table names
**Recommendation**: Keep enabled to prevent unauthorized access

```bash
# Rate limit - calls per window
LANDUSE_SECURITY__RATE_LIMIT_CALLS=60
```
**Range**: 1 to 1000
**Default**: 60
**Description**: Maximum API calls in time window
**Recommendation**: 60 for development; adjust for production load

```bash
# Rate limit - time window
LANDUSE_SECURITY__RATE_LIMIT_WINDOW=60
```
**Range**: 10 to 3600 seconds
**Default**: 60
**Description**: Time window for rate limiting
**Recommendation**: 60 seconds is standard

### Logging Configuration

Control logging behavior and output.

```bash
# Logging level
LANDUSE_LOGGING__LEVEL=INFO
```
**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Default**: `INFO`
**Description**: Minimum log level to output
**Recommendation**:
- `INFO` for production
- `DEBUG` for development/troubleshooting

```bash
# Log file path
LANDUSE_LOGGING__LOG_FILE=logs/landuse.log
```
**Default**: `logs/landuse.log`
**Description**: Path to log file (None for console only)
**Recommendation**: Use file logging in production

```bash
# Enable performance logging
LANDUSE_LOGGING__ENABLE_PERFORMANCE_LOGGING=false
```
**Options**: `true`, `false`
**Default**: `false`
**Description**: Log detailed performance metrics
**Recommendation**: Enable for performance tuning; disable in production

```bash
# Enable JSON logging
LANDUSE_LOGGING__JSON_FORMAT=false
```
**Options**: `true`, `false`
**Default**: `false`
**Description**: Output logs in JSON format
**Recommendation**: Enable for log aggregation systems

### Feature Toggles

Enable or disable specific features.

```bash
# Enable map generation
LANDUSE_FEATURES__ENABLE_MAP_GENERATION=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Enable geographic visualization features
**Recommendation**: Keep enabled unless maps not needed

```bash
# Enable conversation memory
LANDUSE_FEATURES__ENABLE_CONVERSATION_MEMORY=true
```
**Options**: `true`, `false`
**Default**: `true`
**Description**: Remember conversation history
**Recommendation**: Keep enabled for better user experience

```bash
# Map output directory
LANDUSE_FEATURES__MAP_OUTPUT_DIR=maps/agent_generated
```
**Default**: `maps/agent_generated`
**Description**: Directory for generated map files
**Recommendation**: Use absolute path for predictable file locations

## Configuration Profiles

### Development Profile

Optimized for local development with verbose logging and lower limits:

```bash
# Development .env
OPENAI_API_KEY=your_key_here

# Development-friendly settings
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini
LANDUSE_AGENT__MAX_ITERATIONS=8
LANDUSE_AGENT__DEFAULT_DISPLAY_LIMIT=20
LANDUSE_DATABASE__CACHE_TTL=300
LANDUSE_LOGGING__LEVEL=DEBUG
LANDUSE_LOGGING__ENABLE_PERFORMANCE_LOGGING=true
```

### Production Profile

Optimized for production deployment with performance and security:

```bash
# Production .env
OPENAI_API_KEY=your_production_key_here

# Production-optimized settings
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini
LANDUSE_LLM__TIMEOUT=30
LANDUSE_AGENT__MAX_ITERATIONS=6
LANDUSE_AGENT__MAX_EXECUTION_TIME=60
LANDUSE_AGENT__MAX_QUERY_ROWS=500
LANDUSE_DATABASE__MAX_CONNECTIONS=50
LANDUSE_DATABASE__CACHE_TTL=3600
LANDUSE_DATABASE__READ_ONLY=true
LANDUSE_SECURITY__ENABLE_SQL_VALIDATION=true
LANDUSE_SECURITY__STRICT_TABLE_VALIDATION=true
LANDUSE_SECURITY__RATE_LIMIT_CALLS=30
LANDUSE_LOGGING__LEVEL=INFO
LANDUSE_LOGGING__LOG_FILE=logs/production.log
LANDUSE_LOGGING__JSON_FORMAT=true
```

### Testing Profile

Optimized for automated testing:

```bash
# Testing .env
OPENAI_API_KEY=your_test_key_here

# Test-friendly settings
LANDUSE_LLM__MODEL_NAME=gpt-3.5-turbo
LANDUSE_AGENT__MAX_ITERATIONS=4
LANDUSE_AGENT__MAX_EXECUTION_TIME=30
LANDUSE_DATABASE__PATH=data/test/test_landuse.duckdb
LANDUSE_DATABASE__CACHE_TTL=0
LANDUSE_LOGGING__LEVEL=WARNING
LANDUSE_SECURITY__RATE_LIMIT_CALLS=1000
```

## Programmatic Configuration

### Loading Configuration

```python
from landuse.core.app_config import AppConfig

# Load from environment variables
config = AppConfig()

# Access settings
print(f"Model: {config.llm.model_name}")
print(f"Database: {config.database.path}")
print(f"Max iterations: {config.agent.max_iterations}")
```

### Override at Runtime

```python
from landuse.core.app_config import AppConfig

# Create config with overrides
config = AppConfig.from_env(
    llm__model_name='gpt-4o',
    agent__max_iterations=12,
    logging__level='DEBUG'
)
```

### Validation

All configuration is validated on load using Pydantic:

```python
from landuse.core.app_config import AppConfig
from pydantic import ValidationError

try:
    config = AppConfig()
except ValidationError as e:
    print(f"Configuration error: {e}")
```

## Migration from Legacy Configuration

### Old Format (LanduseConfig)

```python
# Old style (deprecated but still supported)
from landuse.config.landuse_config import LanduseConfig

config = LanduseConfig(
    model_name="gpt-4o-mini",
    max_iterations=8,
    database_path="data/processed/landuse_analytics.duckdb"
)
```

### New Format (AppConfig)

```python
# New style (recommended)
from landuse.core.app_config import AppConfig

# Load from environment
config = AppConfig()

# Or create programmatically
config = AppConfig(
    llm=LLMConfig(model_name="gpt-4o-mini"),
    agent=AgentConfig(max_iterations=8),
    database=DatabaseConfig(path="data/processed/landuse_analytics.duckdb")
)
```

## Troubleshooting

### Configuration Not Loading

**Problem**: Environment variables not being read

**Solutions**:
1. Check file location: `config/.env` in project root
2. Verify variable naming: Must use `LANDUSE_` prefix
3. Check for typos in section names (use double underscore)
4. Restart application after changes

### Invalid Configuration Values

**Problem**: Pydantic validation errors

**Solutions**:
1. Check value types (e.g., numbers should not be quoted)
2. Verify boolean values are `true` or `false` (lowercase)
3. Check allowed values for enum fields
4. Review error messages for specific field issues

### OpenAI API Key Issues

**Problem**: API key not recognized or invalid

**Solutions**:
1. Verify key starts with `sk-`
2. Check key has no extra spaces or quotes
3. Confirm key is active in OpenAI dashboard
4. Try setting directly in environment: `export OPENAI_API_KEY=your_key`

## Related Documentation

- **[Configuration Guide](../getting-started/configuration.md)** - General configuration instructions
- **[AppConfig API](../development/architecture.md#configuration-system)** - Configuration system architecture
- **[Troubleshooting](../getting-started/troubleshooting.md)** - Common configuration issues

---

*For detailed configuration examples and best practices, see the [Complete Setup Guide](../getting-started/complete-setup.md).*
