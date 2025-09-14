# Configuration

Learn how to customize the RPA Land Use Analytics system using the unified `LanduseConfig` system.

## Overview

The system uses a modern dataclass-based configuration system (`LanduseConfig`) that provides type-safe, validated configuration with environment variable support and agent-specific presets.

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
# Database Configuration
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb

# Model Configuration  
LANDUSE_MODEL=gpt-4o-mini        # Model name (gpt-4o-mini, claude-3-sonnet-20240229, etc.)
TEMPERATURE=0.2                  # Model temperature (0.0-2.0)
MAX_TOKENS=4000                  # Maximum response tokens

# Agent Behavior
LANDUSE_MAX_ITERATIONS=8         # Maximum agent iterations
LANDUSE_MAX_EXECUTION_TIME=120   # Maximum execution time (seconds)
LANDUSE_MAX_QUERY_ROWS=1000      # Maximum query result rows
LANDUSE_DEFAULT_DISPLAY_LIMIT=50 # Default display limit

# Features
LANDUSE_ENABLE_MEMORY=true       # Enable conversation memory
LANDUSE_ENABLE_MAPS=true         # Enable map generation

# Performance
LANDUSE_RATE_LIMIT_CALLS=60      # API calls per window
LANDUSE_RATE_LIMIT_WINDOW=60     # Rate limit window (seconds)

# Debugging
VERBOSE=false                    # Enable verbose output
DEBUG=false                      # Enable debug mode

# Map Generation Settings
LANDUSE_MAP_OUTPUT_DIR=maps/agent_generated  # Output directory for maps


# Streamlit Settings
STREAMLIT_CACHE_TTL=300          # Cache time-to-live (seconds)

# Domain Configuration
LANDUSE_ANALYSIS_STYLE=standard  # Analysis style (standard, detailed, brief)
LANDUSE_DOMAIN_FOCUS=none        # Domain focus (agriculture, forest, urban, none)
```

## Using LanduseConfig

### Basic Usage

```python
from landuse.config.landuse_config import LanduseConfig

# Create default configuration
config = LanduseConfig()

# Create configuration with overrides
config = LanduseConfig.from_env(
    model_name="claude-3-sonnet-20240229",
    temperature=0.1,
    enable_map_generation=True
)
```

### Agent-Specific Configurations

The system provides pre-configured setups for different agent types:

```python
from landuse.config.landuse_config import get_basic_config, get_map_config, get_streamlit_config

# Basic agent (minimal features)
basic_config = get_basic_config()

# Map-enabled agent (includes visualization)
map_config = get_map_config(verbose=True)

# Streamlit application config
streamlit_config = get_streamlit_config(enable_memory=False)
```

### Configuration Validation

The `LanduseConfig` system includes automatic validation:

- **Database path validation**: Ensures the database file exists
- **API key validation**: Checks for required API keys based on model
- **Numeric range validation**: Validates temperature, token limits, etc.
- **Directory creation**: Automatically creates output directories

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
from landuse.config.landuse_config import LanduseConfig

# Create a custom configuration
custom_config = LanduseConfig.from_env(
    model_name="gpt-4o",
    temperature=0.0,
    max_iterations=10,
    enable_map_generation=True,
    verbose=True,
    max_query_rows=2000
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
dev_config = LanduseConfig.for_agent_type('basic',
    model_name="gpt-4o-mini",
    temperature=0.1,
    max_iterations=5,
    verbose=True
)

# Production configuration - accurate and robust
prod_config = LanduseConfig.for_agent_type('map',
    model_name="gpt-4o",
    temperature=0.0,
    max_iterations=8,
    enable_map_generation=True,
    verbose=False
)

# Analysis configuration - optimized for complex queries
analysis_config = LanduseConfig.from_env(
    model_name="claude-3-sonnet-20240229",
    temperature=0.0,
    max_query_rows=5000,
    max_execution_time=300,
    enable_knowledge_base=True
)
```

## Database Configuration

### Query Limits

Configure query result limits through `LanduseConfig`:

```python
config = LanduseConfig.from_env(
    max_query_rows=2000,           # Maximum rows returned
    default_display_limit=100      # Default display limit
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
from landuse.config.landuse_config import LanduseConfig

# Load environment-specific config
env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f"config/.env.{env}")

# Create configuration
config = LanduseConfig.from_env()
```

## Next Steps

- Learn about [natural language queries](../queries/overview.md)
- Explore [API reference](../api/agent.md) for detailed customization
- See [examples](../examples/workflows.md) of configured agents