# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPA Land Use Analytics is an AI-powered analytics tool for USDA Forest Service RPA Assessment data. Built with a modern data stack (DuckDB, LangChain, GPT-4), it processes county-level land use projections and enables users to ask questions in plain English about land use changes across different climate scenarios from the 2020 RPA Assessment.

## Production Deployment

### Architecture
The application is deployed as a modern full-stack system:

| Component | Platform | URL |
|-----------|----------|-----|
| **Frontend** | Netlify | https://rpa-landuse-frontend.netlify.app |
| **Backend API** | Render | https://rpa-landuse-backend.onrender.com |

### Frontend (Netlify)
- **Dashboard**: https://app.netlify.com/projects/rpa-landuse-frontend
- **Framework**: Next.js 16 + React 19
- **Auto-deploy**: Enabled (from main branch)
- **Features**: Chat, Analytics, SQL Explorer, Data Extraction

### Backend (Render)
- **Dashboard**: https://dashboard.render.com/web/srv-d547o675r7bs73e8oocg
- **Repository**: https://github.com/mihiarc/rpa-landuse-backend
- **Runtime**: Python (FastAPI + Uvicorn)
- **Region**: Oregon
- **Plan**: Starter
- **Auto-deploy**: Enabled (from main branch)

### Environment Variables
Frontend requires `NEXT_PUBLIC_API_URL` pointing to the backend.
Backend requires `OPENAI_API_KEY` and database configuration.

## Key Commands

### Installation & Setup
```bash
# Install dependencies
uv sync

# Guided setup (creates .env file and tests everything)
uv run python setup_agents.py
```

### Running the Applications

#### Next.js Frontend (Production)
```bash
# Navigate to frontend directory
cd ../rpa-landuse-frontend

# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build
```

#### FastAPI Backend (Production)
```bash
# Navigate to backend directory
cd ../rpa-landuse-backend

# Install dependencies
uv sync

# Run development server (http://localhost:8000)
uvicorn app.main:app --reload --port 8000

# API documentation available at http://localhost:8000/docs
```

#### Streamlit Dashboard (Legacy/Development)
```bash
# Local development dashboard with chat interface and visualizations
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
# Convert JSON to DuckDB star schema (optimized bulk loading)
uv run python scripts/converters/convert_to_duckdb.py

# With traditional insert method (for comparison/debugging)
uv run python scripts/converters/convert_to_duckdb.py --no-bulk-copy
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

### Full-Stack Architecture (Production)
```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Next.js Frontend  │────▶│   FastAPI Backend   │────▶│   DuckDB Database   │
│      (Netlify)      │     │      (Render)       │     │    (1.2GB Star)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │  LangChain/LangGraph│
                            │   + OpenAI GPT-4    │
                            └─────────────────────┘
```

### Repository Structure (Monorepo)
- **rpa-landuse-core/**: Python analytics engine, agents, and Streamlit (legacy)
- **rpa-landuse-backend/**: FastAPI REST API (deployed on Render)
- **rpa-landuse-frontend/**: Next.js web frontend (deployed on Netlify)

### Data Stack
1. **Raw Data**: 20M+ line JSON file in `data/raw/` with county landuse projections
2. **DuckDB Processing**: `convert_to_duckdb.py` creates optimized star schema
3. **Analytics Database**: `data/processed/landuse_analytics.duckdb` (1.2GB)
4. **Natural Language Agent**: LangGraph agent converts questions to SQL

### Star Schema Design
- **fact_landuse_transitions**: 5.4M records of land use changes
- **dim_scenario**: 20 climate scenarios (RCP45/85, SSP1/5)
- **dim_geography**: 3,075 US counties with metadata
- **dim_landuse**: 5 land use types with descriptive names
- **dim_time**: 6 time periods (2012-2100)

### Key Components

**Next.js Frontend** (`rpa-landuse-frontend/`):
- Modern React 19 application with Next.js 16 App Router
- **Tech Stack**: Tailwind CSS, shadcn/ui, Zustand, TanStack Query, Plotly.js
- **Pages**:
  - `/login` - Password authentication
  - `/chat` - Natural language AI chat with SSE streaming
  - `/analytics` - Interactive dashboard with Plotly visualizations
  - `/explorer` - SQL query editor with schema browser
  - `/extraction` - Data export (CSV/JSON)
- Session-based authentication with cookies
- Responsive design with dark/light theme support

**FastAPI Backend** (`rpa-landuse-backend/`):
- REST API with OpenAPI documentation at `/docs`
- **Endpoints**: `/api/v1/auth`, `/api/v1/chat`, `/api/v1/analytics`, `/api/v1/explorer`, `/api/v1/extraction`
- SSE streaming for real-time chat responses
- JWT token-based authentication
- Integrates with LangGraph agent for natural language processing

**Streamlit Dashboard** (`landuse_app.py`) - *Legacy/Development*:
- Local development interface with multipage navigation using st.Page and st.navigation
- Chat Interface: Natural language queries with conversation history
- Analytics Dashboard: Pre-built visualizations with Plotly
- Data Explorer: Interactive SQL query interface with schema browser
- Data Extraction: Export query results in multiple formats (CSV, JSON, Parquet)
- Settings Page: System status, configuration, and troubleshooting
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

## Modern Infrastructure & Core Architecture

### Core Architecture Components (`src/landuse/core/`)

**Unified Configuration System** (`app_config.py`):
- **Pydantic-Based Validation**: Type-safe configuration with comprehensive validation
- **Component-Specific Sections**: Organized into database, llm, agent, security, logging, and features
- **Environment Variable Integration**: Native support for LANDUSE_ prefixed env vars with nested delimiters
- **Configuration Inheritance**: Supports configuration overrides and environment-specific settings
- **Backward Compatibility**: Seamless conversion to/from legacy LanduseConfig format

```python
from landuse.core.app_config import AppConfig

# Unified configuration with validation
config = AppConfig()
print(f"Database: {config.database.path}")
print(f"LLM Model: {config.llm.model_name}")
print(f"Max Iterations: {config.agent.max_iterations}")
```

**Dependency Injection Container** (`container.py`):
- **Singleton Pattern**: Thread-safe singleton services with proper lifecycle management
- **Auto-Resolution**: Automatic resolution of common interfaces (DatabaseInterface, LLMInterface, etc.)
- **Factory Registration**: Support for complex object creation with custom factories
- **Configuration Injection**: Automatic configuration injection throughout the application
- **Resource Management**: Proper cleanup and resource disposal

```python
from landuse.core.container import DependencyContainer
from landuse.core.interfaces import DatabaseInterface

# Create and configure DI container
container = DependencyContainer(config)
container.register_singleton(DatabaseInterface, DatabaseManager)

# Resolve services automatically
db_service = container.resolve(DatabaseInterface)
```

**Abstract Interfaces** (`interfaces.py`):
- **Clean Dependency Boundaries**: Abstract interfaces for all major components
- **Testing Support**: Easy mocking and testing with clear interface contracts
- **Loose Coupling**: Components depend on abstractions, not concrete implementations
- **Interface Types**: DatabaseInterface, LLMInterface, ConversationInterface, CacheInterface, LoggerInterface, MetricsInterface

### Infrastructure Layer (`src/landuse/infrastructure/`)

**Thread-Safe Caching** (`cache.py`):
- **InMemoryCache**: High-performance in-memory cache with TTL and LRU eviction
- **Thread Safety**: All operations are thread-safe with RLock protection
- **TTL Support**: Configurable time-to-live for automatic cache expiration
- **LRU Eviction**: Least Recently Used eviction when max size is reached
- **Statistics**: Built-in cache statistics and health monitoring

```python
from landuse.infrastructure import InMemoryCache

# Create cache with TTL and size limits
cache = InMemoryCache(default_ttl=300, max_size=1000)
cache.set('query_results', data, ttl=600)
cached_data = cache.get('query_results')
print(f"Cache stats: {cache.stats()}")
```

**Structured Logging** (`logging.py`):
- **JSON Logging**: Structured JSON logs for production environments
- **Rich Console Output**: Beautiful console logging for development with Rich integration
- **Specialized Loggers**: Separate loggers for security events and performance metrics
- **Performance Logging**: Automatic performance event tracking with timing
- **Security Logging**: Dedicated security event logging with context

```python
from landuse.infrastructure import StructuredLogger
from landuse.core.app_config import LoggingConfig

# Create structured logger
logger_config = LoggingConfig(level='INFO', log_file='logs/app.log')
logger = StructuredLogger(logger_config)

# Log different event types
logger.info("Application started", component="main")
logger.security_event("login_attempt", "User authentication", user_id="123")
logger.performance_event("database_query", 0.45, query_type="select")
```

**Metrics Collection** (`metrics.py`):
- **InMemoryMetrics**: Counter, gauge, and timer metrics with tag-based filtering
- **Thread Safety**: All metric operations are thread-safe
- **Tag-Based Filtering**: Rich tagging system for metric aggregation and filtering
- **Retention Management**: Automatic cleanup of old metrics based on retention policies
- **Statistics**: Built-in statistical analysis (min, max, mean, count, total)

```python
from landuse.infrastructure import InMemoryMetrics

# Create metrics collector
metrics = InMemoryMetrics(retention_seconds=3600)

# Record different metric types
metrics.increment_counter('api_calls', {'endpoint': '/query', 'status': 'success'})
metrics.record_gauge('active_connections', 15, {'pool': 'database'})
metrics.record_timer('query_duration', 0.234, {'type': 'select'})

# Get statistics
stats = metrics.get_timer_stats('query_duration')
print(f"Query stats: {stats}")
```

**Performance Monitoring** (`performance.py`):
- **PerformanceMonitor**: Decorator-based performance tracking with automatic metrics
- **Specialized Decorators**: Database and LLM operation decorators with domain-specific metrics
- **Context Managers**: Timing context managers for code block measurement
- **Exception Tracking**: Automatic exception tracking in performance metrics
- **Integration**: Seamless integration with logging and metrics systems

```python
from landuse.infrastructure import PerformanceMonitor, create_performance_decorator

# Create performance monitor with logging and metrics
perf_monitor = create_performance_decorator(logger, metrics)

# Use as decorator
@perf_monitor.time_execution('critical_operation', tags={'component': 'agent'})
def important_function():
    # Function implementation
    pass

# Use as context manager
with perf_monitor.time_context('batch_processing', {'batch_size': 100}):
    # Process batch
    pass
```

## Configuration System

### Modern AppConfig System (2025)
The application now uses a unified Pydantic-based configuration system with component-specific sections and environment variable integration.

#### Environment Variables
Create `config/.env` with LANDUSE_ prefixed variables:
```bash
# Required API Key
OPENAI_API_KEY=your_openai_key

# LLM Configuration (LANDUSE_LLM__ prefix)
LANDUSE_LLM__MODEL_NAME=gpt-4o-mini        # or gpt-4o, gpt-3.5-turbo
LANDUSE_LLM__TEMPERATURE=0.1
LANDUSE_LLM__MAX_TOKENS=4000

# Agent Configuration (LANDUSE_AGENT__ prefix)
LANDUSE_AGENT__MAX_ITERATIONS=8            # Max tool calls before stopping
LANDUSE_AGENT__MAX_EXECUTION_TIME=120      # Max seconds for query execution
LANDUSE_AGENT__MAX_QUERY_ROWS=1000         # Max rows returned by queries
LANDUSE_AGENT__DEFAULT_DISPLAY_LIMIT=50    # Default rows to display
LANDUSE_AGENT__ENABLE_MEMORY=true          # Enable conversation memory
LANDUSE_AGENT__CONVERSATION_HISTORY_LIMIT=20  # Max conversation messages

# Database Configuration (LANDUSE_DATABASE__ prefix)
LANDUSE_DATABASE__PATH=data/processed/landuse_analytics.duckdb
LANDUSE_DATABASE__MAX_CONNECTIONS=10       # Connection pool size
LANDUSE_DATABASE__CACHE_TTL=3600          # Query cache TTL in seconds

# Security Configuration (LANDUSE_SECURITY__ prefix)
LANDUSE_SECURITY__ENABLE_SQL_VALIDATION=true
LANDUSE_SECURITY__STRICT_TABLE_VALIDATION=true
LANDUSE_SECURITY__RATE_LIMIT_CALLS=60      # Max calls per time window
LANDUSE_SECURITY__RATE_LIMIT_WINDOW=60     # Time window in seconds

# Logging Configuration (LANDUSE_LOGGING__ prefix)
LANDUSE_LOGGING__LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR, CRITICAL
LANDUSE_LOGGING__LOG_FILE=logs/landuse.log # File path (None for console only)
LANDUSE_LOGGING__ENABLE_PERFORMANCE_LOGGING=false

# Feature Toggles (LANDUSE_FEATURES__ prefix)
LANDUSE_FEATURES__ENABLE_MAP_GENERATION=true
LANDUSE_FEATURES__ENABLE_CONVERSATION_MEMORY=true
LANDUSE_FEATURES__MAP_OUTPUT_DIR=maps/agent_generated
```

#### Programmatic Configuration
```python
from landuse.core.app_config import AppConfig

# Load from environment variables
config = AppConfig()

# Or create with overrides
config = AppConfig.from_env(
    llm__model_name='gpt-4o',
    agent__max_iterations=12,
    logging__level='DEBUG'
)

# Access component-specific settings
print(f"Using model: {config.llm.model_name}")
print(f"Database: {config.database.path}")
print(f"Max iterations: {config.agent.max_iterations}")
```

### Legacy Configuration Support
The system maintains backward compatibility with the original LanduseConfig for existing code:

```python
from landuse.config.landuse_config import LanduseConfig

# Legacy configuration still works
legacy_config = LanduseConfig()

# All manager classes support both config types
from landuse.agents.database_manager import DatabaseManager
db_manager = DatabaseManager(config)        # New AppConfig
db_manager = DatabaseManager(legacy_config) # Legacy config
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

### Streamlit Development Guidelines

**IMPORTANT: Use Streamlit Built-in Features**
- Always prefer Streamlit's built-in functionality over custom solutions
- Do NOT over-engineer custom implementations when Streamlit provides native support
- Examples:
  - Use Streamlit's built-in theme system (Settings menu) instead of custom theme toggles
  - Use st.connection for database connections instead of custom connection managers
  - Use st.cache_data and st.cache_resource instead of custom caching solutions
  - Use st.session_state for state management instead of custom state handlers
  - Use Streamlit's native widgets and layouts instead of custom HTML/CSS when possible
- Only create custom solutions when Streamlit genuinely lacks the required functionality
- This approach ensures better maintainability, compatibility, and performance

### Modern Architecture Development (2025)

#### Unified Configuration Pattern
Use the new AppConfig system for type-safe, validated configuration:

```python
from landuse.core.app_config import AppConfig
from landuse.core.container import DependencyContainer

# Create unified configuration
config = AppConfig()

# Set up dependency injection
container = DependencyContainer(config)
container.register_instance(AppConfig, config)

# Use throughout application
print(f"Using {config.llm.model_name} with {config.agent.max_iterations} max iterations")
```

#### Agent Architecture with Modern Components
The landuse agent now uses modular architecture with dependency injection:

```python
# Modern agent initialization
from landuse.agents.landuse_agent import LanduseAgent
from landuse.core.app_config import AppConfig

# Clean dependency injection pattern with new config
config = AppConfig()
with LanduseAgent(config) as agent:
    response = agent.query("Which scenarios show the most agricultural land loss?")

# Or use legacy config (backward compatible)
from landuse.config.landuse_config import LanduseConfig
legacy_config = LanduseConfig()
with LanduseAgent(legacy_config) as agent:
    response = agent.query("Compare forest loss between scenarios")
```

#### Component-Based Development with Modern Architecture
Working with individual managers using the new infrastructure:

```python
# Direct component usage with AppConfig
from landuse.core.app_config import AppConfig
from landuse.agents.llm_manager import LLMManager
from landuse.agents.database_manager import DatabaseManager
from landuse.agents.conversation_manager import ConversationManager
from landuse.infrastructure import InMemoryCache, InMemoryMetrics, StructuredLogger

# Create unified configuration
config = AppConfig()

# Set up infrastructure components
cache = InMemoryCache(max_size=1000, default_ttl=3600)
metrics = InMemoryMetrics(retention_seconds=7200)
logger = StructuredLogger(config.logging)

# LLM management with performance monitoring
llm_manager = LLMManager(config)
llm = llm_manager.create_llm()  # Factory pattern with performance tracking

# Database operations with caching and monitoring
with DatabaseManager(config) as db_manager:
    connection = db_manager.get_connection()
    schema = db_manager.get_schema()  # Automatically performance monitored

# Conversation handling with configurable sliding window
conversation = ConversationManager(config)  # Uses config.agent.conversation_history_limit
conversation.add_conversation("question", "response")
messages = conversation.get_conversation_messages()

# Access metrics and cache
cache.set('schema', schema, ttl=1800)
query_stats = metrics.get_timer_stats('database.get_schema.duration')
```

#### Dependency Injection Pattern
Use dependency injection for clean, testable code:

```python
from landuse.core.container import DependencyContainer
from landuse.core.interfaces import DatabaseInterface, LLMInterface, CacheInterface

# Set up dependency injection container
container = DependencyContainer(config)

# Register services
container.register_singleton(DatabaseInterface, DatabaseManager)
container.register_singleton(LLMInterface, LLMManager) 
container.register_instance(CacheInterface, cache)

# Resolve services automatically
db_service = container.resolve(DatabaseInterface)
llm_service = container.resolve(LLMInterface)
cache_service = container.resolve(CacheInterface)

# Services are properly configured and ready to use
schema = db_service.get_schema()
model = llm_service.create_llm()
cache_service.set('model_info', {'name': model.__class__.__name__})
```

#### Performance Monitoring Integration
Integrate performance monitoring throughout your application:

```python
from landuse.infrastructure.performance import create_performance_decorator, time_database_operation

# Create performance monitor with infrastructure
perf_monitor = create_performance_decorator(logger, metrics)

# Use decorators for automatic performance tracking
@perf_monitor.time_execution('custom_analysis', tags={'type': 'landuse'})
def analyze_land_use_patterns(data):
    # Analysis logic with automatic timing
    return processed_data

# Use specialized decorators for database operations
@time_database_operation('complex_query')
def execute_complex_query(connection, query):
    return connection.execute(query).fetchall()

# Context manager for ad-hoc timing
with perf_monitor.time_context('data_processing', {'batch_size': 1000}):
    # Process large dataset
    results = process_large_dataset(data)
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

### Testing Patterns with Modern Architecture
The new modular architecture with dependency injection enables comprehensive testing:

```python
# Unit testing with dependency injection and mocking
from unittest.mock import Mock
from landuse.core.app_config import AppConfig
from landuse.core.container import DependencyContainer
from landuse.core.interfaces import DatabaseInterface, LLMInterface
from landuse.agents.query_executor import QueryExecutor

def test_query_executor_with_di():
    # Create test configuration
    config = AppConfig()
    
    # Set up DI container with mocked dependencies
    container = DependencyContainer(config)
    mock_db = Mock(spec=DatabaseInterface)
    container.register_instance(DatabaseInterface, mock_db)
    
    # Test with clean dependencies
    db_service = container.resolve(DatabaseInterface)
    assert db_service is mock_db

# Integration testing with real infrastructure components
def test_full_stack_integration():
    from landuse.infrastructure import InMemoryCache, InMemoryMetrics
    
    config = AppConfig()
    cache = InMemoryCache(max_size=100)
    metrics = InMemoryMetrics()
    
    # Test infrastructure integration
    cache.set('test_key', 'test_value')
    metrics.increment_counter('test_counter')
    
    assert cache.get('test_key') == 'test_value'
    assert metrics.get_counter_total('test_counter') == 1.0

# Performance monitoring testing
def test_performance_monitoring():
    from landuse.infrastructure.performance import PerformanceMonitor
    from landuse.infrastructure import InMemoryMetrics, StructuredLogger
    
    config = AppConfig()
    metrics = InMemoryMetrics()
    logger = StructuredLogger(config.logging)
    perf_monitor = PerformanceMonitor(logger, metrics)
    
    @perf_monitor.time_execution('test_operation')
    def test_function():
        return "success"
    
    result = test_function()
    assert result == "success"
    
    # Check metrics were recorded
    timer_stats = metrics.get_timer_stats('test_operation.duration')
    assert timer_stats['count'] == 1

# Agent testing with both config types
def test_agent_backward_compatibility():
    from landuse.agents.landuse_agent import LanduseAgent
    from landuse.config.landuse_config import LanduseConfig
    
    # Test with new AppConfig
    app_config = AppConfig()
    with LanduseAgent(app_config) as agent:
        assert agent is not None
    
    # Test with legacy config (backward compatibility)
    legacy_config = LanduseConfig()
    with LanduseAgent(legacy_config) as agent:
        assert agent is not None
```

## Documentation Guidelines

### Docstring Style
This project uses **Google Style** docstrings for consistency and readability. Google style is preferred over NumPy style for general code due to its space efficiency and clarity.

#### Function/Method Documentation
```python
def process_land_use_data(
    input_file: Path,
    scenario: str,
    validate: bool = True
) -> pd.DataFrame:
    """Process land use transition data for a specific scenario.

    Converts raw JSON data into normalized DataFrame format with proper
    indexing and validation. Handles missing values and data type conversions.

    Args:
        input_file: Path to the input JSON file containing land use data.
        scenario: Climate scenario identifier (e.g., 'RCP45_SSP2').
        validate: Whether to validate data integrity. Defaults to True.

    Returns:
        DataFrame with normalized land use transitions indexed by county.

    Raises:
        ValueError: If scenario is not found in the input data.
        IOError: If input file cannot be read.

    Example:
        >>> df = process_land_use_data(Path('data.json'), 'RCP45_SSP2')
        >>> print(df.shape)
        (3075, 15)
    """
```

#### Class Documentation
```python
class LanduseDataConverter:
    """Convert nested landuse JSON to normalized DuckDB database.

    This converter handles the ETL process for transforming deeply nested
    JSON land use projections into a star schema optimized for analytics.
    Uses bulk loading techniques for optimal performance on large datasets.

    Attributes:
        input_file: Path to source JSON file.
        output_file: Path to target DuckDB database.
        use_bulk_copy: Whether to use optimized bulk COPY (5-10x faster).

    Example:
        >>> converter = LanduseDataConverter('input.json', 'output.db')
        >>> converter.create_schema()
        >>> converter.load_data()
        >>> converter.close()
    """
```

### Documentation Best Practices

1. **Consistency**: Use Google style throughout the codebase. Don't mix styles.

2. **Conciseness**: Keep line length to 72 characters for docstrings. Be clear but brief.

3. **Type Hints**: Always include type hints in function signatures - they're part of the documentation.

4. **Examples**: Include short examples for complex functions, especially those in public APIs.

5. **Private Methods**: Document private methods with a single line unless complexity demands more.

6. **Module Level**: Start each module with a brief description of its purpose.

7. **Avoid Redundancy**: Don't repeat what's obvious from the code or type hints.

### What to Document

- **Public APIs**: All public functions, classes, and methods need comprehensive docstrings
- **Complex Logic**: Any non-obvious algorithm or business logic
- **Data Structures**: Expected formats, schemas, and transformations
- **Side Effects**: File I/O, database changes, external API calls
- **Error Conditions**: What exceptions are raised and when
- **Performance Notes**: For optimized code paths or known bottlenecks

### What NOT to Document

- **Obvious Code**: Don't document getters/setters unless they have side effects
- **Implementation Details**: Focus on *what* not *how* in public APIs
- **TODO Comments**: Use issue tracking instead of TODO comments
- **Commented-Out Code**: Remove it, don't document why it's there

### Tools & Automation

- **IDE Support**: VSCode/PyCharm can auto-generate Google style docstring templates
- **Documentation Generation**: Use `mkdocs` with `mkdocstrings` for auto-generated API docs
- **Validation**: Consider using `pydocstyle` with Google style configuration

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
   - Model selection (GPT-4o-mini, GPT-4o, GPT-3.5 Turbo)
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
- **Core**: langchain, langchain-openai, langchain-community, langgraph
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

### Configuration Centralization & Dependency Injection (2025)
- **Unified AppConfig System**: Replaced scattered configuration with single Pydantic-based AppConfig
- **Component-Specific Sections**: Organized configuration into database, llm, agent, security, logging, and features sections
- **Environment Variable Integration**: Native support for LANDUSE_ prefixed env vars with nested delimiters
- **Backward Compatibility**: All manager classes support both new AppConfig and legacy LanduseConfig
- **Dependency Injection Container**: 
  - Singleton pattern with thread-safety for shared resources
  - Auto-resolution of common interfaces (DatabaseInterface, LLMInterface, etc.)
  - Factory registration for complex object creation
  - Configuration injection throughout the application
- **Infrastructure Components**:
  - `InMemoryCache`: Thread-safe caching with TTL and LRU eviction
  - `StructuredLogger`: JSON logging with security and performance event tracking
  - `InMemoryMetrics`: Counter, gauge, and timer metrics with tag-based filtering
- **Configuration Migration**: Seamless conversion between AppConfig and legacy formats
- **Interface Abstractions**: Clean dependency boundaries with abstract interfaces for all major components

### Performance Monitoring & Observability (2025)
- **Decorator-Based Performance Tracking**: Automatic timing and metrics collection for critical operations
- **Specialized Operation Decorators**: Database and LLM operation decorators with domain-specific metrics
- **Context Manager Timing**: Ad-hoc timing support for code blocks and batch operations
- **Exception Tracking**: Automatic exception tracking in performance metrics with error categorization
- **Infrastructure Integration**: Seamless integration with structured logging and metrics collection
- **Performance Components**:
  - `PerformanceMonitor`: Central performance tracking with decorator and context manager support
  - `@time_database_operation`: Specialized decorator for database operations with row count tracking
  - `@time_llm_operation`: LLM-specific decorator with token usage tracking
  - Thread-safe metrics collection with tag-based filtering and aggregation
- **Real-Time Observability**: Live performance metrics with statistical analysis (min, max, mean, count)
- **Production Ready**: Performance monitoring with configurable retention and automatic cleanup

### Modern Infrastructure Enhancements
- **Pydantic v2 Models**: Type-safe data structures with validation for all components
- **DuckDB COPY Optimization**: 5-10x performance improvement using bulk loading with Parquet
- **Retry Logic with Tenacity**: Robust error handling with exponential backoff strategies
- **CI/CD Pipeline**: Comprehensive GitHub Actions for testing, security, and releases
- **Streamlit Fragments**: Performance optimization with @st.fragment decorators