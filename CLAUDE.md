# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an advanced natural language analysis system for county-level land use transitions using AI agents and modern data stack (DuckDB, LangChain, GPT-4). The project processes USDA RPA land use projection data and enables users to ask questions in plain English about land use changes across different climate scenarios.

## Key Commands

### Installation & Setup
```bash
# Install dependencies
uv sync

# Guided setup (creates .env file and tests everything)
uv run python setup_agents.py
```

### Running the Agents
```bash
# Primary: Landuse Natural Language Query Agent (recommended)
uv run python scripts/agents/landuse_query_agent.py

# Test with sample queries
uv run python scripts/agents/test_landuse_agent.py

# Alternative: General SQL Query Agent (legacy)
uv run python scripts/agents/sql_query_agent.py
```

### Data Processing
```bash
# Convert JSON to DuckDB star schema (modern approach)
uv run python scripts/converters/convert_to_duckdb.py

# Legacy SQLite converters
uv run python scripts/converters/convert_landuse_to_db.py
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

## Architecture

### Modern Data Stack (Current)
1. **Raw Data**: 20M+ line JSON file in `data/raw/` with county landuse projections
2. **DuckDB Processing**: `convert_to_duckdb.py` creates optimized star schema
3. **Analytics Database**: `data/processed/landuse_analytics.duckdb` (1.2GB)
4. **Natural Language Agent**: `landuse_query_agent.py` converts questions to SQL

### Star Schema Design
- **fact_landuse_transitions**: 5.4M records of land use changes
- **dim_scenario**: 20 climate scenarios (RCP45/85, SSP1/5)
- **dim_geography**: 3,075 US counties with metadata
- **dim_landuse**: 5 land use types with descriptive names
- **dim_time**: 6 time periods (2012-2100)

### Key Components

**Landuse Query Agent** (`scripts/agents/landuse_query_agent.py`):
- Specialized for land use analysis with business context
- Automatic summary statistics and insights
- Beautiful Rich terminal UI with markdown support
- Schema-aware query generation

**SQL Query Agent** (`scripts/agents/sql_query_agent.py`):
- General-purpose SQL agent for multiple databases
- Supports SQLite, DuckDB, CSV, JSON, Parquet
- File management and data transformation tools

### Land Use Categories
- **Crop**: Agricultural cropland
- **Pasture**: Livestock grazing land
- **Forest**: Forested areas
- **Urban**: Developed/built areas
- **Range**: Natural grasslands

## Environment Configuration

Create `config/.env` with:
```
# Required
OPENAI_API_KEY=your_api_key

# Optional (defaults shown)
ANTHROPIC_API_KEY=your_anthropic_key  # For Claude models
LANDUSE_MODEL=gpt-4o-mini            # or claude-3-haiku-20240307
TEMPERATURE=0.1
MAX_TOKENS=4000
```

## Development Patterns

### Natural Language Queries
The landuse agent understands business context:
```python
# Ask questions naturally
agent.query("Which scenarios show the most agricultural land loss?")
agent.query("Compare forest loss between RCP45 and RCP85")
agent.query("Show me urbanization patterns in California")
```

### DuckDB Best Practices
- Use CTEs for complex queries
- Leverage star schema joins
- Utilize pre-built views for common patterns
- Apply filters early for performance

### Error Handling
All agents provide helpful error messages and suggestions:
- Schema hints when columns are misspelled
- Query optimization suggestions
- Data quality warnings

## Testing Approach

### Interactive Testing
```bash
# Test landuse agent with sample queries
uv run python scripts/agents/test_landuse_agent.py

# Interactive exploration
uv run python scripts/agents/landuse_query_agent.py
```

### DuckDB Direct Access
```bash
# Browser-based UI
duckdb data/processed/landuse_analytics.duckdb -ui

# Command line
duckdb data/processed/landuse_analytics.duckdb
```

## Key Features

1. **Natural Language Understanding**: Converts questions to optimized SQL
2. **Business Intelligence**: Automatic insights and summary statistics
3. **Climate Analysis**: Compare RCP/SSP scenarios
4. **Geographic Patterns**: State and county-level analysis
5. **Beautiful Output**: Rich terminal UI with colors and formatting

## Common Query Patterns

```
# Scenario comparisons
"Which scenarios show the most agricultural land loss?"

# Geographic analysis
"Which states have the most urban expansion?"

# Temporal patterns
"Show me forest loss trends over time"

# Transition analysis
"What's converting to urban land in California?"
```