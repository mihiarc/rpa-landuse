# Configuration

Learn how to customize the LangChain Land Use Analysis system to fit your needs.

## Environment Variables

The system uses environment variables stored in `config/.env` for configuration.

### Required Settings

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-...your-key-here...
```

### Optional Settings

```bash
# Project Settings
PROJECT_ROOT_DIR=./data           # Root directory for data files
MAX_FILE_SIZE_MB=100             # Maximum file size for processing

# Agent Model Settings
AGENT_MODEL=gpt-4-turbo-preview  # OpenAI model to use
TEMPERATURE=0.1                   # Model temperature (0.0-1.0)
MAX_TOKENS=4000                  # Maximum response tokens

# Database Settings
DEFAULT_QUERY_LIMIT=1000         # Default row limit for queries
CHUNK_SIZE=10000                 # Batch size for data processing
```

## Model Selection

### Available Models

The agent supports different OpenAI models:

```bash
# Recommended for best results
AGENT_MODEL=gpt-4-turbo-preview

# Alternatives
AGENT_MODEL=gpt-4               # More expensive, similar quality
AGENT_MODEL=gpt-3.5-turbo      # Faster, cheaper, less accurate
```

### Model Comparison

| Model | Pros | Cons | Best For |
|-------|------|------|----------|
| gpt-4-turbo-preview | Best accuracy, large context | More expensive | Complex queries, production use |
| gpt-4 | Very accurate | Most expensive, smaller context | High-stakes analysis |
| gpt-3.5-turbo | Fast, cheap | Less accurate SQL | Simple queries, development |

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

## Memory and Context

The agent uses LangGraph's MemorySaver for conversation context:

```python
# In data_engineering_agent.py
self.memory = MemorySaver()
```

This enables:
- Follow-up questions
- Contextual understanding
- Multi-step analysis

## File Size Limits

Control how large files are handled:

```bash
# Maximum file size for full processing
MAX_FILE_SIZE_MB=100

# For larger files, sampling is used
# First 1000 rows are read for preview
```

## Custom Agent Configuration

### Modifying Agent Behavior

Edit `scripts/agents/data_engineering_agent.py`:

```python
class DataEngineeringAgent:
    def __init__(self, root_dir: str = None):
        # Customize initialization
        self.llm = ChatOpenAI(
            model=os.getenv("AGENT_MODEL", "gpt-4-turbo-preview"),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
            # Add custom parameters
            request_timeout=60,
            max_retries=3
        )
```

### Adding Custom Tools

Extend agent capabilities by adding new tools:

```python
def _create_tools(self) -> List[Tool]:
    tools = []
    
    # Add your custom tool
    tools.append(
        Tool(
            name="custom_analysis",
            func=self._custom_analysis,
            description="Perform custom analysis on data"
        )
    )
    
    return tools

def _custom_analysis(self, params: str) -> str:
    """Your custom analysis logic"""
    # Implementation here
    pass
```

## Database Configuration

### Query Limits

Prevent accidental large result sets:

```python
# In DatabaseQueryParams
class DatabaseQueryParams(BaseModel):
    limit: Optional[int] = Field(1000, description="Maximum rows")
```

### Connection Settings

For different database locations:

```bash
# Use absolute paths for databases outside data directory
DATABASE_PATH=/path/to/your/database.db

# Or modify in code
db_path = os.getenv("DATABASE_PATH", "processed/landuse_transitions.db")
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
# config/.env.development
AGENT_MODEL=gpt-3.5-turbo
TEMPERATURE=0.2
MAX_TOKENS=2000

# config/.env.production  
AGENT_MODEL=gpt-4-turbo-preview
TEMPERATURE=0.0
MAX_TOKENS=4000
```

Load appropriate config:

```python
from dotenv import load_dotenv

env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f"config/.env.{env}")
```

## Next Steps

- Learn about [natural language queries](../queries/overview.md)
- Explore [API reference](../api/agent.md) for detailed customization
- See [examples](../examples/workflows.md) of configured agents