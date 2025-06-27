# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPA Land Use Analytics is an AI-powered analytics tool for USDA Forest Service RPA Assessment data. Built with a modern data stack (DuckDB, LangChain, Claude/GPT-4), it processes county-level land use projections and enables users to ask questions in plain English about land use changes across different climate scenarios from the 2020 RPA Assessment.

## Key Commands

### Installation & Setup
```bash
# Install dependencies
uv sync

# Guided setup (creates .env file and tests everything)
uv run python setup_agents.py
```

### Running the Applications

#### Streamlit Dashboard (Recommended)
```bash
# Modern web dashboard with chat interface and visualizations
uv run streamlit run streamlit_app.py

# Features:
# - Natural language chat interface
# - Interactive analytics dashboard with 6 visualization types
# - Data explorer with SQL query interface
# - Data extraction tool for custom analysis
# - System settings and configuration
```

#### Command Line Agents
```bash
# Primary: RPA Analytics Natural Language Agent (command line)
uv run python -m landuse.agents.agent

# Or use the shortcut
uv run rpa-analytics

# Test with sample queries
uv run python -m landuse.agents.test_landuse_agent
```

### Data Processing
```bash
# Convert JSON to DuckDB star schema (modern approach)
uv run python scripts/converters/convert_to_duckdb.py

# Legacy SQLite converters
uv run python scripts/converters/convert_landuse_to_db.py
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

### Documentation
```bash
# Build documentation
mkdocs build

# Serve documentation locally (http://localhost:8000)
mkdocs serve
```

### Direct Database Access
```bash
# Browser-based DuckDB UI
duckdb data/processed/landuse_analytics.duckdb -ui

# DuckDB command line
duckdb data/processed/landuse_analytics.duckdb
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

**Streamlit Dashboard** (`streamlit_app.py`):
- Modern web interface with multipage navigation using st.Page and st.navigation
- 💬 **Chat Interface**: Natural language queries with conversation history
- 📊 **Analytics Dashboard**: 
  - Overview metrics and KPIs
  - Agricultural impact analysis
  - Forest transition analysis
  - Climate scenario comparisons
  - Geographic visualizations (choropleth maps)
  - Land use flow diagrams (Sankey charts)
- 🔍 **Data Explorer**: Interactive SQL query interface with schema browser
- 📥 **Data Extraction**: Export query results in multiple formats (CSV, JSON, Parquet)
- ⚙️ **Settings Page**: System status, configuration, and troubleshooting
- Mobile-responsive design with modern UI patterns
- Custom DuckDB connection using st.connection pattern

**LangGraph Natural Language Agent** (`src/landuse/agents/langgraph_agent.py`) - **RECOMMENDED**:
- Modern graph-based agent architecture using LangGraph
- Enhanced state management with conversation memory
- Built-in checkpointing for conversation continuity
- Streaming support for real-time responses
- Advanced error handling and recovery
- Tool composition and orchestration
- Uses Claude 3.5 Sonnet by default (configurable via LANDUSE_MODEL env var)
- Specialized for land use analysis with business context
- Beautiful Rich terminal UI with markdown support

**Traditional LangChain Agent** (`src/landuse/agents/landuse_natural_language_agent.py`) - **LEGACY**:
- Built with LangChain REACT agent framework
- Linear execution with basic tool calling
- Limited state management
- Schema-aware query generation

**Data Converter** (`src/landuse/converters/convert_to_duckdb.py`):
- Processes nested JSON to normalized star schema
- Creates dimension and fact tables
- Adds indexes and views for performance
- Handles 20M+ lines efficiently with progress tracking

**DuckDB Connection** (`src/landuse/connections/duckdb_connection.py`):
- Custom connection class implementing st.connection pattern
- Automatic result caching with configurable TTL
- Support for both file-based and in-memory databases
- Thread-safe operations with read-only mode by default
- Compatible with testing environments

### Land Use Categories
- **Crop**: Agricultural cropland (cr)
- **Pasture**: Livestock grazing land (ps)
- **Forest**: Forested areas (fr)
- **Urban**: Developed/built areas (ur)
- **Rangeland**: Natural grasslands (rg)

### Land Use Projection Methodology
The projections are based on an econometric model with these characteristics:
- **Historical Calibration**: Based on observed transitions 2001-2012 from NRI data
- **Spatial Resolution**: County-level projections for 3,075 counties
- **Land Ownership**: Private land only (public lands assumed static)
- **Key Assumption**: Development is irreversible - once urban, always urban
- **Model Type**: Policy-neutral projections based on historical relationships
- **Primary Pattern**: ~46% of new developed land comes from forest

For detailed methodology, see `docs/LAND_USE_METHODOLOGY.md`

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

# Query Execution Limits (optional, defaults shown)
LANDUSE_MAX_ITERATIONS=5        # Max tool calls before stopping
LANDUSE_MAX_EXECUTION_TIME=120  # Max seconds for query execution
LANDUSE_MAX_QUERY_ROWS=1000     # Max rows returned by queries
LANDUSE_DEFAULT_DISPLAY_LIMIT=50 # Default rows to display

# Rate Limiting (optional, defaults shown)
LANDUSE_RATE_LIMIT_CALLS=60     # Max calls per time window
LANDUSE_RATE_LIMIT_WINDOW=60    # Time window in seconds
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
uv run python -m landuse.agents.test_landuse_agent

# Interactive exploration
uv run python -m landuse.agents.landuse_natural_language_agent
```

### DuckDB Direct Access
```bash
# Browser-based UI
duckdb data/processed/landuse_analytics.duckdb -ui

# Command line
duckdb data/processed/landuse_analytics.duckdb
```

## Key Features

### Web Dashboard (Streamlit)
1. **Modern Web Interface**: Responsive design with multipage navigation
2. **Interactive Chat**: Real-time natural language queries with streaming responses
3. **Rich Visualizations**: Plotly charts for agricultural loss, urbanization, climate scenarios
4. **Data Exploration**: SQL query interface with schema browser and example queries
5. **System Management**: Configuration, status monitoring, and troubleshooting tools

### Command Line Interface
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

## Testing

### Test Framework
```bash
# Run all tests
uv run python -m pytest tests/

# Run with coverage report
uv run python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test categories
uv run python -m pytest tests/unit/          # Unit tests
uv run python -m pytest tests/integration/   # Integration tests
```

### Test Coverage
- **Current Coverage**: 89.75% (exceeding 70% requirement)
- **Total Tests**: 142+ tests across unit and integration
- **Test Categories**:
  - Agent functionality tests
  - Natural language processing tests
  - Database connection tests (with real DuckDB)
  - Security and validation tests
  - Streamlit component tests (with mocked decorators)
  - Data conversion tests

### Testing Philosophy
- All tests use real functionality (no mocking of core logic)
- Real API calls for agent tests
- Real database connections for data tests
- Comprehensive error handling coverage

## Dependencies

Key packages (managed via `uv`):
- **Core**: langchain, langchain-anthropic, langchain-community, langgraph
- **Modern Agent Framework**: langgraph (for state-based agents)
- **Data**: pandas, duckdb (0.11.0+), pyarrow, ijson
- **Web UI**: streamlit (1.40.0+), plotly  
- **Terminal UI**: rich
- **Retry Logic**: tenacity
- **Validation**: pydantic v2
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Docs**: mkdocs, mkdocs-material

## Recent Updates (2024-2025)

### Streamlit Dashboard
- Added comprehensive multipage dashboard with 5 main sections
- Implemented custom DuckDB connection with st.connection pattern
- Created rich analytics visualizations using Plotly
- Added data extraction functionality with multiple export formats
- Mobile-responsive design with modern UI patterns

### Testing Infrastructure
- Achieved 89.75% test coverage with 142+ tests
- Added comprehensive unit tests for all core components
- Created mock Streamlit module for testing without full installation
- All tests use real functionality (no mocking of business logic)

### Data Processing
- Optimized star schema design for 5.4M+ records
- Added specialized views for common query patterns
- Improved query performance with strategic indexing

### Modern Agent Architecture (LangGraph Migration)
- **LangGraph Implementation**: New state-based agent using LangGraph for enhanced workflow control
- **Conversation Memory**: Built-in checkpointing for conversation continuity across sessions
- **Streaming Support**: Real-time response streaming for better user experience
- **Enhanced State Management**: TypedDict-based state with rich context tracking
- **Tool Orchestration**: Improved tool composition and execution flow
- **Error Recovery**: Advanced error handling with graceful fallbacks
- **Performance Improvements**: Graph-based execution with optimized iteration patterns
- **Production Ready**: Memory management, thread safety, and scalability features

### Modern Infrastructure Enhancements
- **Pydantic v2 Models**: Type-safe data structures with validation for all components
- **DuckDB COPY Optimization**: 5-10x performance improvement using bulk loading with Parquet
- **Retry Logic with Tenacity**: Robust error handling with exponential backoff strategies
- **CI/CD Pipeline**: Comprehensive GitHub Actions for testing, security, and releases
- **Streamlit Fragments**: Performance optimization with @st.fragment decorators