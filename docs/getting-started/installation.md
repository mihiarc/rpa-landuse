# Installation

This guide will help you set up the LangChain Land Use Analysis project on your system.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** - The project requires Python 3.8 or higher
- **uv** - Python package installer and virtual environment manager
- **Git** - For cloning the repository

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/langchain-landuse.git
cd langchain-landuse
```

## Step 2: Set Up Virtual Environment

We recommend using `uv` for managing the virtual environment:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Step 3: Install Dependencies

Install all required packages using uv:

```bash
uv pip install -r config/requirements.txt
```

This will install:

- **LangChain** (>=0.3.0) - Core framework for building LLM applications
- **LangChain OpenAI** (>=0.2.0) - OpenAI integration
- **LangChain Community** (>=0.3.0) - Community tools and integrations
- **Pandas** (>=2.2.0) - Data manipulation and analysis
- **SQLAlchemy** (>=2.0.0) - SQL toolkit and ORM
- **Rich** (>=14.0.0) - Terminal formatting and progress bars
- **Pydantic** (>=2.0.0) - Data validation
- And more...

## Step 4: Configure Environment Variables

Create a `.env` file in the `config` directory:

```bash
cd config
cp .env.example .env  # Or create a new file
```

Edit the `.env` file with your settings:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults shown)
PROJECT_ROOT_DIR=./data
AGENT_MODEL=gpt-4-turbo-preview
TEMPERATURE=0.1
MAX_TOKENS=4000
MAX_FILE_SIZE_MB=100
```

!!! warning "API Key Security"
    Never commit your `.env` file to version control. The `.gitignore` file should already exclude it.

## Step 5: Verify Installation

Test that everything is working:

```bash
# Go back to project root
cd ..

# Run the test agent
uv run python scripts/agents/test_agent.py
```

You should see:

```
🚀 Creating Sample Data Files
✅ sample_data.csv created
✅ inventory.json created
✅ sensor_data.parquet created

Data Engineering Agent
🤖 Agent initialized. Working directory: ./data
Type 'exit' to quit, 'help' for available commands

You>
```

## Step 6: Prepare Land Use Data

If you have the county land use projections data:

1. Place your JSON file in `data/raw/`
2. Run the converter:

```bash
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

This creates the SQLite database in `data/processed/`.

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the virtual environment
which python  # Should show .venv/bin/python
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