# Installation

This guide will help you set up the RPA Land Use Analytics project on your system.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+** - The project requires Python 3.9 or higher
- **uv** - Python package installer and virtual environment manager
- **Git** - For cloning the repository

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/rpa-landuse.git
cd rpa-landuse
```

## Step 2: Set Up Virtual Environment

We recommend using `uv` for managing the virtual environment:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Step 3: Install Dependencies

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

## Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example configuration
cp .env.example .env
```

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
LANDUSE_ENABLE_KNOWLEDGE_BASE=false

# Performance
LANDUSE_RATE_LIMIT_CALLS=60
LANDUSE_RATE_LIMIT_WINDOW=60
```

!!! warning "API Key Security"
    Never commit your `.env` file to version control. The `.gitignore` file should already exclude it.

## Step 5: Verify Installation

Test that everything is working:

```bash
# Test the main RPA analytics agent (requires API key setup)
uv run rpa-analytics

# Alternative entry points
uv run landuse-agent
uv run python -m landuse.agents.agent

# Test the Streamlit dashboard
uv run streamlit run streamlit_app.py
```

If your API keys are configured correctly, you should see:

```
🌲 RPA Land Use Analytics Agent
USDA Forest Service RPA Assessment Data Analysis

RPA Land Use Analytics Database:
✓ Found 5 tables in database
✓ Knowledge base ready (if enabled)

Welcome to RPA Land Use Analytics!
Ask questions about land use projections and transitions.
Type 'exit' to quit, 'help' for examples, 'clear' to reset conversation.

[You] >
```

## Step 6: Prepare Land Use Data

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

### Getting Help

If you encounter issues:

1. Check the [FAQ section](../faq.md)
2. Search existing [GitHub issues](https://github.com/yourusername/langchain-landuse/issues)
3. Create a new issue with:
   - Your Python version (`python --version`)
   - Error messages
   - Steps to reproduce

## Next Steps

Now that you have the project installed, proceed to:

- [Quick Start Guide](quickstart.md) - Run your first natural language query
- [Configuration](configuration.md) - Customize agent behavior
- [Natural Language Queries](../queries/overview.md) - Learn query techniques