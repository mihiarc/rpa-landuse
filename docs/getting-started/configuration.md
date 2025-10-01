# Configuration

Learn how to customize the RPA Land Use Analytics system using the unified `AppConfig` system.

## Overview

The system uses a modern Pydantic-based configuration system (`AppConfig`) that provides type-safe, validated configuration with environment variable support and component-specific sections.

## Environment Variables

The system reads configuration from environment variables, typically stored in `config/.env`.

### Required Settings

```bash
# API Keys (choose one based on your model preference)
OPENAI_API_KEY=sk-...your-key-here...        # For GPT models
ANTHROPIC_API_KEY=sk-ant-...your-key...      # For Claude models
```

### Core Configuration Variables

```bash
# LLM Configuration (LANDUSE_LLM__ prefix)
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini    # Model name
LANDUSE_LLM__TEMPERATURE=0.1           # Model temperature (0.0-2.0)
LANDUSE_LLM__MAX_TOKENS=4000           # Maximum response tokens

# Agent Configuration (LANDUSE_AGENT__ prefix)
LANDUSE_AGENT__MAX_ITERATIONS=8              # Maximum agent iterations
LANDUSE_AGENT__MAX_EXECUTION_TIME=120        # Maximum execution time (seconds)
LANDUSE_AGENT__MAX_QUERY_ROWS=1000           # Maximum query result rows
LANDUSE_AGENT__DEFAULT_DISPLAY_LIMIT=50      # Default display limit
LANDUSE_AGENT__ENABLE_MEMORY=true            # Enable conversation memory
LANDUSE_AGENT__CONVERSATION_HISTORY_LIMIT=20 # Max conversation messages

# Database Configuration (LANDUSE_DATABASE__ prefix)
LANDUSE_DATABASE__PATH=data/processed/landuse_analytics.duckdb
LANDUSE_DATABASE__MAX_CONNECTIONS=10         # Connection pool size
LANDUSE_DATABASE__CACHE_TTL=3600            # Query cache TTL in seconds

# Security Configuration (LANDUSE_SECURITY__ prefix)
LANDUSE_SECURITY__ENABLE_SQL_VALIDATION=true
LANDUSE_SECURITY__STRICT_TABLE_VALIDATION=true
LANDUSE_SECURITY__RATE_LIMIT_CALLS=60        # Max calls per time window
LANDUSE_SECURITY__RATE_LIMIT_WINDOW=60       # Time window in seconds

# Logging Configuration (LANDUSE_LOGGING__ prefix)
LANDUSE_LOGGING__LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LANDUSE_LOGGING__LOG_FILE=logs/landuse.log   # File path (None for console only)
LANDUSE_LOGGING__ENABLE_PERFORMANCE_LOGGING=false

# Feature Toggles (LANDUSE_FEATURES__ prefix)
LANDUSE_FEATURES__ENABLE_MAP_GENERATION=true
LANDUSE_FEATURES__ENABLE_CONVERSATION_MEMORY=true
LANDUSE_FEATURES__MAP_OUTPUT_DIR=maps/agent_generated
```

## Using AppConfig

### Basic Usage

```python
from landuse.core.app_config import AppConfig

# Create default configuration
config = AppConfig()

# Create configuration with overrides
config = AppConfig.from_env(
    llm__model_name="claude-3-sonnet-20240229",
    llm__temperature=0.1,
    features__enable_map_generation=True
)
```

### Component-Specific Configurations

The system provides component-specific configuration sections:

```python
from landuse.core.app_config import AppConfig

# Basic agent configuration
config = AppConfig()
print(f"Using model: {config.llm.model_name}")
print(f"Database: {config.database.path}")
print(f"Max iterations: {config.agent.max_iterations}")

# Access specific components
print(f"Security enabled: {config.security.enable_sql_validation}")
print(f"Logging level: {config.logging.level}")
```

### Configuration Validation

The `AppConfig` system includes automatic Pydantic validation:

- **Type checking**: Ensures all config values match expected types
- **Range validation**: Validates temperature, token limits, etc.
- **Required fields**: Checks for required configuration values
- **Nested validation**: Validates all component-specific sections

## Model Selection

### Available Models

The system supports both OpenAI and Anthropic models:

```bash
# OpenAI Models (recommended)
LANDUSE_MODEL=gpt-4o-mini           # Default - fast, cost-effective
LANDUSE_MODEL=gpt-4o                # Best performance
LANDUSE_MODEL=gpt-4-turbo           # Good balance

# Anthropic Models
LANDUSE_MODEL=claude-3-5-sonnet-20241022  # Latest Claude Sonnet (recommended)
LANDUSE_MODEL=claude-3-sonnet-20240229    # Excellent reasoning
LANDUSE_MODEL=claude-3-haiku-20240307     # Fast, economical
```

### Model Comparison

| Model | Provider | Pros | Cons | Best For |
|-------|----------|------|------|----------|
| gpt-4o-mini | OpenAI | Fast, cheap, good accuracy | Smaller context | Development, simple queries |
| gpt-4o | OpenAI | Best accuracy, large context | More expensive | Production, complex analysis |
| claude-3-5-sonnet | Anthropic | Latest model, excellent reasoning | Higher cost | Complex SQL, analysis |
| claude-3-sonnet | Anthropic | Good reasoning, reliable | Higher cost | Complex queries |
| claude-3-haiku | Anthropic | Very fast, economical | Less capable | Simple queries, high volume |

## Temperature Settings

Temperature controls the randomness of responses:

```bash
# For consistent, deterministic results (recommended)
TEMPERATURE=0.0

# Default - slight variability
TEMPERATURE=0.1

# For more creative responses
TEMPERATURE=0.7
```

!!! tip "Best Practice"
    Use low temperature (0.0-0.2) for data analysis to ensure consistent, accurate SQL generation.

## Advanced Configuration Options

### Map Generation Settings

Configure map output and visualization:

```bash
# Map generation
LANDUSE_MAP_OUTPUT_DIR=maps/agent_generated  # Output directory for maps
LANDUSE_ENABLE_MAPS=true                     # Enable/disable map generation
```


### Streamlit Configuration

For web interface deployment:

```bash
# Streamlit-specific settings
STREAMLIT_CACHE_TTL=300                      # Cache time-to-live (seconds)
```

## Custom Agent Configuration

### Creating Custom Configurations

```python
from landuse.core.app_config import AppConfig

# Create a custom configuration
custom_config = AppConfig.from_env(
    llm__model_name="gpt-4o",
    llm__temperature=0.0,
    agent__max_iterations=10,
    features__enable_map_generation=True,
    logging__level="DEBUG",
    agent__max_query_rows=2000
)

# Use with an agent
from landuse.agents.landuse_agent import LanduseAgent
with LanduseAgent(config=custom_config) as agent:
    agent.chat()  # Start interactive session
    # or
    result = agent.query("Show me urban growth in California")
```

### Configuration for Different Use Cases

```python
# Development configuration - fast and cheap
dev_config = AppConfig.from_env(
    llm__model_name="gpt-4o-mini",
    llm__temperature=0.1,
    agent__max_iterations=5,
    logging__level="DEBUG"
)

# Production configuration - accurate and robust
prod_config = AppConfig.from_env(
    llm__model_name="gpt-4o",
    llm__temperature=0.0,
    agent__max_iterations=8,
    features__enable_map_generation=True,
    logging__level="WARNING"
)

# Analysis configuration - optimized for complex queries
analysis_config = AppConfig.from_env(
    llm__model_name="claude-3-sonnet-20240229",
    llm__temperature=0.0,
    agent__max_query_rows=5000,
    agent__max_execution_time=300
)
```

## Database Configuration

### Query Limits

Configure query result limits through `AppConfig`:

```python
config = AppConfig.from_env(
    agent__max_query_rows=2000,           # Maximum rows returned
    agent__default_display_limit=100      # Default display limit
)
```

### Connection Settings

Configure database path through environment variables:

```bash
# Database location
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb

# Or use absolute paths
LANDUSE_DB_PATH=/path/to/your/database.duckdb
```

## Visualization Settings

Configure plotting behavior:

```python
# Matplotlib settings
import matplotlib.pyplot as plt

plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 300
```

## Rich Terminal Configuration

Customize the terminal interface:

```python
from rich.console import Console

# Create custom console
console = Console(
    color_system="truecolor",  # or "256" or "standard"
    force_terminal=True,
    width=120
)
```

## Logging Configuration

Enable detailed logging for debugging:

```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
```

## Performance Tuning

### Batch Processing

Adjust chunk sizes for large data:

```bash
# For JSON to database conversion
CHUNK_SIZE=10000  # Default
CHUNK_SIZE=50000  # For better performance with RAM
CHUNK_SIZE=5000   # For limited memory
```

### Cache Settings

The agent includes a 15-minute cache for web fetches:

```python
# In WebFetch tool
# Cache automatically cleans after 15 minutes
```

## Security Configuration

### API Key Management

!!! danger "Security Best Practices"
    - Never commit `.env` files to version control
    - Use environment-specific `.env` files
    - Rotate API keys regularly
    - Use read-only database access when possible

```bash
# Development
cp config/.env.development config/.env

# Production
cp config/.env.production config/.env
```

### File Access Restrictions

Limit agent file access:

```python
# Restrict to specific directories
ALLOWED_PATHS = [
    "./data",
    "./output",
    "./temp"
]
```

## Advanced Configuration

### Custom Prompts

Modify the agent's system prompt:

```python
prompt = PromptTemplate.from_template("""
You are a specialized land use data analyst.
Focus on: {analysis_focus}
Current directory: {root_dir}

{tools}
...
""")
```

### Tool Timeouts

Set timeouts for long-running operations:

```python
# In tool definition
Tool(
    name="heavy_computation",
    func=self._heavy_computation,
    description="...",
    # Add timeout
    coroutine_timeout=300  # 5 minutes
)
```

## Environment-Specific Configs

Create different configurations for different environments:

```bash
# .env.development
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.2
MAX_TOKENS=2000
LANDUSE_MAX_ITERATIONS=5
VERBOSE=true
DEBUG=true
LANDUSE_ENABLE_MAPS=false

# .env.production  
LANDUSE_MODEL=gpt-4o
TEMPERATURE=0.0
MAX_TOKENS=4000
LANDUSE_MAX_ITERATIONS=8
VERBOSE=false
DEBUG=false
LANDUSE_ENABLE_MAPS=true
```

Load appropriate config:

```python
from dotenv import load_dotenv
from landuse.core.app_config import AppConfig

# Load environment-specific config
env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f"config/.env.{env}")

# Create configuration
config = AppConfig.from_env()
```

## Next Steps

- Learn about [natural language queries](../queries/overview.md)
- Explore [API reference](../api/agent.md) for detailed customization
- See [examples](../examples/workflows.md) of configured agents