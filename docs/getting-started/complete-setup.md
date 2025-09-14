# Complete Setup Guide

Get up and running with RPA Land Use Analytics from installation to your first query in 10 minutes!

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+** - The project requires Python 3.9 or higher
- **uv** - Python package installer and virtual environment manager
- **Git** - For cloning the repository

## Step 1: Clone and Install

### Clone the Repository

```bash
git clone https://github.com/yourusername/rpa-landuse.git
cd rpa-landuse
```

### Set Up Virtual Environment

We recommend using `uv` for managing the virtual environment:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Dependencies

Install the project and all dependencies using uv:

```bash
# Install project in development mode with all dependencies
uv sync

# Or install manually if needed
uv pip install -e .
```

This will install:

- **LangChain** (>=0.3.0) - Core framework for building LLM applications
- **LangGraph** (>=0.2.0) - Modern graph-based agent framework
- **LangChain Anthropic** (>=0.2.0) - Claude integration
- **LangChain OpenAI** (>=0.2.0) - OpenAI integration
- **DuckDB** (>=1.0.0) - High-performance analytical database
- **Pandas** (>=2.2.0) - Data manipulation and analysis
- **Streamlit** (>=1.46.0) - Web dashboard framework
- **Rich** (>=14.0.0) - Terminal formatting and progress bars
- **Pydantic** (>=2.0.0) - Data validation
- **Plotly** (>=5.17.0) - Interactive visualizations
- **GeoPandas** (>=1.0.0) - Geographic data processing
- And more...

## Step 2: Configure Environment Variables

### Create Environment File

```bash
# Copy the example configuration
cp .env.example .env
```

### Edit Configuration

Edit the `.env` file with your settings:

```bash
# Required API Keys (choose one based on your model preference)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Model Configuration
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=4000

# Database Configuration
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50

# Agent Execution Limits
LANDUSE_MAX_ITERATIONS=8
LANDUSE_MAX_EXECUTION_TIME=120

# Features
LANDUSE_ENABLE_MAPS=true
LANDUSE_ENABLE_MEMORY=true

# Performance
LANDUSE_RATE_LIMIT_CALLS=60
LANDUSE_RATE_LIMIT_WINDOW=60
```

!!! warning "API Key Security"
    Never commit your `.env` file to version control. The `.gitignore` file should already exclude it.

## Step 3: Prepare Land Use Data

If you have the RPA county land use projections data:

1. Place your JSON file in `data/raw/`
2. Run the DuckDB converter:

```bash
# Convert JSON to DuckDB star schema (recommended)
uv run python scripts/converters/convert_to_duckdb.py

# Or use the legacy SQLite converter
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

This creates the optimized DuckDB database in `data/processed/landuse_analytics.duckdb`.

## Step 4: Verify Installation

Test that everything is working:

```bash
# Test the main RPA analytics agent (requires API key setup)
uv run rpa-analytics

# Alternative entry points
uv run landuse-agent
uv run python -m landuse.agents.agent

# Test the Streamlit dashboard
uv run streamlit run landuse_app.py
```

If your API keys are configured correctly, you should see:

```
🌲 RPA Land Use Analytics Agent
USDA Forest Service RPA Assessment Data Analysis

RPA Land Use Analytics Database:
✓ Found 5 tables in database

Welcome to RPA Land Use Analytics!
Ask questions about land use projections and transitions.
Type 'exit' to quit, 'help' for examples, 'clear' to reset conversation.

[You] >
```

## Step 5: Your First Query

### Start the Agent

```bash
# Interactive command-line interface (recommended)
uv run rpa-analytics

# Or launch the web dashboard
uv run streamlit run landuse_app.py
```

### Explore RPA Scenarios

Start by understanding the available RPA scenarios:

```
You> What RPA scenarios are available in the database?
```

The agent will show you the 20 integrated climate-socioeconomic scenarios.

### Explore the Database Schema

```
You> Describe the database schema
```

Response:
```
RPA Land Use Analytics Database:
  • fact_landuse_transitions: 5.4M land use changes
  • dim_scenario: 20 RPA climate-socioeconomic scenarios
  • dim_geography_enhanced: 3,075 US counties
  • dim_landuse: 5 land use categories
  • dim_time: 6 time periods (2012-2100)
```

### Try Natural Language Queries

**Basic RPA Queries:**
```
You> How does agricultural land loss differ between the LM and HH scenarios?
You> Show me forest loss under the "hot" climate model
You> What's the projected urban area in 2070 under high growth scenarios?
```

**Advanced RPA Queries:**
```
You> Compare forest loss between RCP4.5 and RCP8.5 pathways
You> How does urban expansion differ between SSP1 (sustainability) and SSP5 (fossil-fueled)?
You> Show me agricultural transitions in the South region under the "dry" climate model
```

### Understanding Agent Responses

The agent will:

1. **Interpret your question** - Convert natural language to SQL
2. **Show the query** - Display the generated SQL for transparency
3. **Execute and format** - Run the query and present results clearly
4. **Provide context** - Add explanations when helpful

Example interaction:

```
You> What are the main land use types in the RPA Assessment?

Agent> I'll query the RPA database to show you the land use categories.

📊 Analysis Assumptions:
- Using USDA Forest Service 2020 RPA Assessment categories

Query: SELECT landuse_name, landuse_category FROM dim_landuse ORDER BY landuse_id

Results: 5 land use types
- Crop (Agriculture)
- Pasture (Agriculture)
- Rangeland (Natural)
- Forest (Natural)
- Urban (Developed)
```

## Complete Configuration Reference

### Core Configuration Variables

The system uses a modern dataclass-based configuration system (`LanduseConfig`) that provides type-safe, validated configuration with environment variable support.

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

### Model Selection

#### Available Models

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

#### Model Comparison

| Model | Provider | Pros | Cons | Best For |
|-------|----------|------|------|----------|
| gpt-4o-mini | OpenAI | Fast, cheap, good accuracy | Smaller context | Development, simple queries |
| gpt-4o | OpenAI | Best accuracy, large context | More expensive | Production, complex analysis |
| claude-3-5-sonnet | Anthropic | Latest model, excellent reasoning | Higher cost | Complex SQL, analysis |
| claude-3-sonnet | Anthropic | Good reasoning, reliable | Higher cost | Complex queries |
| claude-3-haiku | Anthropic | Very fast, economical | Less capable | Simple queries, high volume |

### Temperature Settings

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

### Using LanduseConfig

#### Basic Usage

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

#### Agent-Specific Configurations

```python
from landuse.config.landuse_config import get_basic_config, get_map_config, get_streamlit_config

# Basic agent (minimal features)
basic_config = get_basic_config()

# Map-enabled agent (includes visualization)
map_config = get_map_config(verbose=True)

# Streamlit application config
streamlit_config = get_streamlit_config(enable_memory=False)
```

#### Custom Configurations

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
)
```

### Environment-Specific Configurations

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

## Advanced Setup

### Documentation Deployment (GitHub Pages)

#### MkDocs Configuration

The documentation is configured for deployment to GitHub Pages using MkDocs with the Material theme.

```bash
# Build the documentation site
uv run mkdocs build

# Build with strict mode (catches all warnings)
uv run mkdocs build --strict

# Serve locally for development
uv run mkdocs serve
```

Documentation will be available at http://localhost:8000

#### Deployment Setup

**Initial Setup (One-time):**
1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: gh-pages / (root)
4. Save the settings

**Automatic Deployment:**
Documentation automatically deploys when:
- Documentation files are changed and pushed to main branch
- The deploy-docs workflow is manually triggered

**Manual Deployment:**
```bash
# Deploy to GitHub Pages
uv run mkdocs gh-deploy --force
```

### Map Generation Settings

Configure map output and visualization:

```bash
# Map generation
LANDUSE_MAP_OUTPUT_DIR=maps/agent_generated  # Output directory for maps
LANDUSE_ENABLE_MAPS=true                     # Enable/disable map generation
```

### Security Configuration

#### API Key Management

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

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the virtual environment and project is installed
uv run which python  # Should show .venv/bin/python
uv pip list | grep rpa-landuse  # Should show the project is installed
```

**OpenAI API Errors**
```bash
# Check your API key is set
echo $OPENAI_API_KEY  # Should show your key (be careful not to share!)
```

**Permission Errors**
```bash
# Ensure data directories exist and are writable
mkdir -p data/{raw,processed}
chmod 755 data data/raw data/processed
```

**Database Connection Issues**
```bash
# Test database connectivity
duckdb data/processed/landuse_analytics.duckdb "SELECT 1;"

# Check database integrity
duckdb data/processed/landuse_analytics.duckdb "PRAGMA integrity_check;"

# Verify table counts
duckdb data/processed/landuse_analytics.duckdb \
    "SELECT table_name, estimated_size FROM duckdb_tables();"
```

### Getting Help

If you encounter issues:

1. Check the [FAQ section](faq.md)
2. Search existing [GitHub issues](https://github.com/yourusername/langchain-landuse/issues)
3. Create a new issue with:
   - Your Python version (`python --version`)
   - Error messages
   - Steps to reproduce

## Query Tips and Examples

### Query Tips

1. **Be specific** - Include details like scenarios, years, or counties
2. **Use natural language** - No need to write SQL
3. **Ask follow-ups** - The agent maintains context
4. **Request visualizations** - Ask for charts or plots

### Common Task Examples

**Analyzing Transitions:**
```
# See all transitions from forest
You> Show all land use types that forest converts to

# Focus on specific transitions
You> How much pasture converts to crop in the High Crop Demand scenario?

# Exclude same-to-same
You> Show me only the changes, not areas that stayed the same
```

**Geographic Analysis:**
```
# County-specific queries
You> What are the land use changes in Los Angeles County (FIPS 06037)?

# Regional patterns
You> Which counties in California have the most urban growth?

# Top counties
You> List the top 20 counties by total agricultural land
```

**Time Series Analysis:**
```
# Trends over time
You> Show me how forest area changes from 2020 to 2100

# Specific periods
You> What happens between 2040 and 2050 in terms of urban expansion?

# Rate of change
You> Which decade has the fastest cropland growth?
```

### Export Results

Save query results in different formats:

```
You> Export the top 100 urban growth counties to a CSV file
You> Save forest transition data for California as Parquet
You> Export the fact_landuse_transitions table to JSON format
```

## Next Steps

Now that you have the system installed and configured:

1. **Learn more query techniques** → [Natural Language Queries](../queries/complete-guide.md)
2. **Understand the data** → [Complete Database Reference](../data/complete-reference.md)
3. **Explore the agent system** → [Agent Complete Guide](../agents/complete-guide.md)
4. **Try advanced examples** → [Complete Examples](../examples/complete-examples.md)

## Related Documentation

### Quick Links
- **[Complete Database Reference](../data/complete-reference.md)** - Database schema and tables
- **[Agent Guide](../agents/complete-guide.md)** - Natural language queries and configuration
- **[Query Examples](../queries/complete-guide.md)** - Query patterns and examples
- **[API Documentation](../api/agent.md)** - Python integration

### Deep Dives
- **[Tool System Architecture](../agents/TOOL_SYSTEM_ARCHITECTURE.md)** - How tools work internally
- **[Performance Monitoring](../agents/PERFORMANCE_MONITORING.md)** - Production optimization
- **[Error Handling](../agents/ERROR_HANDLING_RESILIENCE.md)** - Debugging and reliability

## See Also

### Related Documentation
- **[Complete Query Guide](../queries/complete-guide.md)** - Learn natural language query patterns and advanced syntax
- **[Complete Agent Guide](../agents/complete-guide.md)** - Understand agent configuration and advanced capabilities
- **[Complete Database Reference](../data/complete-reference.md)** - Explore database schema and data structures
- **[Complete Examples Guide](../examples/complete-examples.md)** - Real-world workflows and use cases
- **[RPA Assessment Complete](../rpa/rpa-assessment-complete.md)** - Background on data sources and methodology

### Quick Navigation for Next Steps
- **Query Patterns**: See [Complete Query Guide](../queries/complete-guide.md#getting-started-with-basic-queries) for your first queries
- **Agent Configuration**: Check [Complete Agent Guide](../agents/complete-guide.md#configuration) for customization options  
- **Database Understanding**: Reference [Complete Database Reference](../data/complete-reference.md#star-schema-design) for data structure
- **Practical Examples**: Follow [Complete Examples Guide](../examples/complete-examples.md#step-by-step-workflows) for detailed workflows
- **Data Context**: Learn about [RPA Assessment](../rpa/rpa-assessment-complete.md#overview) for background

> **Consolidation Note**: This guide consolidates information from installation.md, quickstart.md, configuration.md, and github-pages-setup.md into a single comprehensive setup resource. For the most current installation and configuration instructions, always refer to this complete guide rather than individual component files.