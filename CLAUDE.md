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
uv run streamlit run landuse_app.py

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

**Streamlit Dashboard** (`landuse_app.py`):
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

**Refactored LangGraph Agent** (`src/landuse/agents/landuse_agent.py`) - **RECOMMENDED**:
- **Modern Modular Architecture**: Follows SOLID principles with separated concerns
- **Component-Based Design**: Uses dependency injection with specialized managers
- **Enhanced Security**: Comprehensive SQL injection prevention and input validation
- **LangGraph Integration**: State-based workflows with conversation memory and checkpointing
- **Streaming Support**: Real-time responses with graceful error handling
- **Robust Error Handling**: Custom exception hierarchy with contextual error messages
- **Backward Compatible**: Maintains all existing public APIs while improving internal structure

**Agent Architecture Components**:
- **LLMManager** (`src/landuse/agents/llm_manager.py`): LLM creation, API key handling, model selection
- **DatabaseManager** (`src/landuse/agents/database_manager.py`): Connection management, schema retrieval, resource cleanup
- **ConversationManager** (`src/landuse/agents/conversation_manager.py`): Sliding window memory, message formatting
- **QueryExecutor** (`src/landuse/agents/query_executor.py`): SQL execution with security validation and error handling
- **GraphBuilder** (`src/landuse/agents/graph_builder.py`): LangGraph workflow construction and node management
- **DatabaseSecurity** (`src/landuse/security/database_security.py`): Allowlist-based validation, SQL injection prevention

**Data Converter** (`src/landuse/converters/convert_to_duckdb.py`):
- Processes nested JSON to normalized star schema
- Creates dimension and fact tables
- Adds indexes and views for performance
- Handles 20M+ lines efficiently with progress tracking

**DuckDB Connection** (`src/landuse/connections/duckdb_connection.py`):
- **Custom st.connection Implementation**: Extends Streamlit's BaseConnection pattern
- **Automatic Caching**: Query results cached with configurable TTL (default: 3600s)
- **Database Retry Logic**: Robust connection handling with exponential backoff
- **Thread Safety**: Read-only mode by default with concurrent access support
- **Connection Features**:
  - Supports both file-based and in-memory databases
  - Automatic path resolution with environment variable fallback
  - Query validation and parameterization support
  - Health check and monitoring capabilities
  - Compatible with testing environments (graceful Streamlit import fallback)

**Agent Tools** (`src/landuse/tools/`):
- **Common Tools** (`common_tools.py`):
  - `execute_landuse_query`: SQL execution with error handling and suggestions
  - `analyze_landuse_results`: Business insights and interpretation
  - `explore_landuse_schema`: Database schema exploration
  - Integrated retry logic and result formatting
- **Map Generation Tool** (`map_generation_tool.py`):
  - LangGraph-compatible tool with `response_format="content_and_artifact"`
  - Creates county-level, regional, and transition maps
  - Supports state-specific visualizations (Texas, California, Florida)
  - Uses GeoPandas for spatial data and Plotly for interactive maps
  - Automatic filename generation with timestamps
  - Output formats: PNG (matplotlib) and HTML (plotly)

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

## Pydantic v2 Data Models

**Core Models** (`src/landuse/models.py`):
- **Configuration Models**: 
  - `AgentConfig`: Comprehensive agent configuration with validation
  - `QueryInput`: Natural language query validation and cleaning
  - `SQLQuery`: SQL validation preventing destructive operations
- **Data Models**:
  - `QueryResult`: Query execution results with metadata and DataFrame handling
  - `LandUseTransition`: Fact table records with business logic validation
  - Dimension models: `ScenarioDimension`, `TimeDimension`, `GeographyDimension`, `LandUseDimension`
- **Analysis Models**:
  - `AnalysisRequest`: Structured analysis requests with parameter validation
  - `ChatMessage`: Chat interface data structure with timestamp and metadata
  - `SystemStatus`: System health and configuration monitoring
- **Enums**: Controlled vocabularies for land use types, scenarios, and transitions
- **Features**: Field validation, model validation, protected namespaces, extra field control

**Conversion Models** (`src/landuse/converter_models.py`):
- **ETL Configuration**: `ConversionConfig` with bulk loading optimization
- **Processing Models**:
  - `RawLandUseData`: Input validation for JSON data
  - `ProcessedTransition`: Validated database-ready records
  - `ConversionStats`: Performance metrics and success rates
- **Quality Control**:
  - `ValidationResult`: Data quality validation with errors and warnings
  - `CheckpointData`: Recovery and progress tracking
- **Conversion Modes**: Streaming, batch, parallel, and optimized bulk copy operations

## Development Patterns

### Refactored Agent Architecture (2025)
The landuse agent now uses modern modular architecture with dependency injection:

```python
# Agent initialization with component managers
from landuse.agents.landuse_agent import LanduseAgent
from landuse.config.landuse_config import LanduseConfig

# Clean dependency injection pattern
config = LanduseConfig()
with LanduseAgent(config) as agent:
    response = agent.query("Which scenarios show the most agricultural land loss?")
```

### Component-Based Development
Working with individual managers for focused functionality:

```python
# Direct component usage for specialized tasks
from landuse.agents.llm_manager import LLMManager
from landuse.agents.database_manager import DatabaseManager
from landuse.agents.conversation_manager import ConversationManager

# LLM management
llm_manager = LLMManager(config)
llm = llm_manager.create_llm()  # Factory pattern

# Database operations
with DatabaseManager(config) as db_manager:
    connection = db_manager.get_connection()
    schema = db_manager.get_schema()

# Conversation handling with sliding window memory
conversation = ConversationManager(max_history_length=20)
conversation.add_conversation("question", "response")
messages = conversation.get_conversation_messages()
```

### Security-First Development
Comprehensive SQL injection prevention and validation:

```python
from landuse.security.database_security import DatabaseSecurity, QueryValidator

# Validate queries before execution
DatabaseSecurity.validate_query_safety(query)
DatabaseSecurity.validate_table_name(table_name)

# Advanced validation with detailed results
validator = QueryValidator(strict_mode=True)
result = validator.validate_query(query)
if not result.is_valid:
    print(f"Validation errors: {result.validation_errors}")
```

### Error Handling with Custom Exceptions
Structured error handling with specific exception types:

```python
from landuse.exceptions import DatabaseError, LLMError, ToolExecutionError

try:
    result = agent.query("complex query")
except DatabaseError as e:
    # Handle database-specific errors
    print(f"Database error: {e.message}")
except LLMError as e:
    # Handle LLM-related errors
    print(f"LLM error with model {e.model_name}: {e.message}")
except ToolExecutionError as e:
    # Handle tool execution failures
    print(f"Tool '{e.tool_name}' failed: {e.message}")
```

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
- All queries automatically validated for security

### Testing Patterns
The modular architecture enables comprehensive testing:

```python
# Unit testing with mocked components
def test_query_executor():
    mock_connection = Mock(spec=duckdb.DuckDBPyConnection)
    mock_config = Mock(spec=LanduseConfig)
    executor = QueryExecutor(mock_config, mock_connection)
    
# Integration testing with real components
def test_agent_integration():
    config = LanduseConfig()
    with LanduseAgent(config) as agent:
        result = agent.query("test query")
        assert result is not None
```

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
**Modern Multipage Architecture** (`landuse_app.py`):
- **Navigation**: Uses modern `st.navigation()` API with organized page groups
- **Responsive Design**: Optimized CSS for wide layouts and mobile compatibility
- **Error Handling**: Comprehensive error catching with helpful diagnostics

**Dashboard Pages**:
1. **Home Page**: Feature overview with dataset statistics and navigation cards
2. **Natural Language Chat** (`views/chat.py`): 
   - Real-time streaming responses with agent conversation
   - Model selection (GPT-4o-mini, Claude 3.5 Sonnet)
   - Conversation history with agent reasoning display
   - Error handling with rate limit detection
3. **Analytics Dashboard** (`views/analytics.py`):
   - Pre-built visualizations using Plotly
   - Agricultural impact analysis
   - Climate scenario comparisons
   - Geographic trend maps with choropleth visualization
4. **Data Explorer** (`views/explorer.py`):
   - Interactive SQL query interface
   - Schema browser with table information
   - Example queries and documentation
   - Export capabilities (CSV, JSON, Parquet)
5. **Data Extraction** (`views/extraction.py`):
   - Custom query builder
   - Bulk data export functionality
   - Format selection and download
6. **Settings & Help** (`views/settings.py`):
   - System status monitoring
   - Configuration management
   - Troubleshooting tools and diagnostics

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

### Agent Architecture Refactoring (2025)
- **Monolithic Breakdown**: Refactored 900-line agent class into 5 specialized managers (37% size reduction)
- **SOLID Principles**: Implemented Single Responsibility, Dependency Injection, and Clean Architecture patterns
- **Component Separation**: 
  - `LLMManager`: API key handling and model creation with factory pattern
  - `DatabaseManager`: Connection pooling, schema caching, and resource cleanup  
  - `ConversationManager`: Sliding window memory management (prevents memory leaks)
  - `QueryExecutor`: SQL execution with comprehensive security validation
  - `GraphBuilder`: LangGraph workflow construction and state management
- **Security Enhancements**: 
  - Allowlist-based SQL injection prevention with comprehensive validation
  - Custom exception hierarchy with 10+ specific exception types
  - Secure API key masking and environment variable management
- **Error Handling Overhaul**: Replaced 25+ broad exception handlers with specific, contextual error handling
- **Backward Compatibility**: Maintained all existing public APIs while improving internal architecture
- **Production Quality**: Achieved A+ architecture rating (92/100) and B+ security rating (83/100)

### Modern Infrastructure Enhancements
- **Pydantic v2 Models**: Type-safe data structures with validation for all components
- **DuckDB COPY Optimization**: 5-10x performance improvement using bulk loading with Parquet
- **Retry Logic with Tenacity**: Robust error handling with exponential backoff strategies
- **CI/CD Pipeline**: Comprehensive GitHub Actions for testing, security, and releases
- **Streamlit Fragments**: Performance optimization with @st.fragment decorators