# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangChain-based project for analyzing county-level land use transitions using AI agents and SQLite databases. The project processes land use projection data from JSON sources and converts it into queryable databases, then uses LangChain agents to analyze and interact with this data.

## Key Commands

### Installation
```bash
uv pip install -r config/requirements.txt
```

### Running the Agent
```bash
uv run python scripts/agents/test_agent.py
```

### Running Data Converters
```bash
# Convert JSON to SQLite database
uv run python scripts/converters/convert_landuse_to_db.py

# Convert with agriculture aggregation
uv run python scripts/converters/convert_landuse_with_agriculture.py

# Add change views to existing database
uv run python scripts/converters/add_change_views.py
```

## Architecture

### Data Flow
1. **Raw Data**: JSON files in `data/raw/` containing county landuse projections
2. **Converters**: Scripts in `scripts/converters/` transform JSON to SQLite databases
3. **Processed Data**: SQLite databases in `data/processed/` with structured land use transitions
4. **Agent Layer**: LangChain agents in `scripts/agents/` provide natural language interface to query data

### Key Components

**Data Engineering Agent** (`scripts/agents/data_engineering_agent.py`):
- Core agent providing file analysis, SQL queries, format conversion
- Supports CSV, Excel, JSON, Parquet, GeoParquet, and SQLite
- Memory-enabled for context retention
- Rich terminal UI with progress indicators

**Database Schema**:
- Main table: `landuse_transitions` 
- Columns: scenario, year, year_range, fips, from_land_use, to_land_use, area_1000_acres
- Views for aggregated agriculture (crop+pasture) and change-only transitions

### Land Use Categories
- **cr**: Crop
- **ps**: Pasture  
- **rg**: Range
- **fr**: Forest
- **ur**: Urban
- **ag**: Agriculture (aggregated crop + pasture)

## Environment Configuration

Create `config/.env` with:
```
OPENAI_API_KEY=your_api_key
PROJECT_ROOT_DIR=./data
AGENT_MODEL=gpt-4-turbo-preview
TEMPERATURE=0.1
MAX_TOKENS=4000
MAX_FILE_SIZE_MB=100
```

## Development Patterns

### Agent Tool Creation
Tools follow the pattern in `data_engineering_agent.py`:
- Pydantic models for parameter validation
- Rich console output for user feedback
- Error handling with descriptive messages
- Support for both dict and string inputs

### Database Queries
Use the agent's SQL capabilities:
```python
agent.run("Query processed/landuse_transitions.db: SELECT scenario, COUNT(*) FROM landuse_transitions GROUP BY scenario")
```

### Data Conversion
Large JSON files are processed using streaming (ijson) to handle memory efficiently. Progress tracking uses Rich library.

## Testing Approach

The `test_agent.py` script:
1. Creates sample data files (CSV, JSON, Parquet)
2. Launches interactive agent with example queries
3. No formal test framework - testing is interactive through the agent interface

To test new functionality, modify `test_agent.py` to create appropriate sample data and queries.