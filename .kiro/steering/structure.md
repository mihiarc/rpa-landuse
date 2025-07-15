# Project Structure & Organization

## Source Layout (src/ pattern)
```
src/landuse/                    # Main package following src layout
├── agents/                     # AI agent implementations
│   ├── landuse_agent.py       # Main consolidated agent with LangGraph
│   ├── constants.py           # Shared constants and schema info
│   ├── formatting.py          # Output formatting utilities
│   └── prompts.py             # Centralized prompt management
├── config/                     # Configuration management
│   └── landuse_config.py      # Unified dataclass-based configuration
├── tools/                      # LangChain tools for agents
│   ├── common_tools.py        # Database query and analysis tools
│   └── map_tools.py           # Geographic visualization tools
├── utilities/                  # Runtime utilities
│   ├── security.py            # Input validation and rate limiting
│   └── state_mappings.py      # FIPS code to state name mappings
├── connections/                # Database connection management
│   └── duckdb_connection.py   # DuckDB connection with retry logic
└── models.py                   # Pydantic data models
```

## Supporting Directories
```
scripts/                        # Setup and maintenance scripts
├── converters/                 # Data transformation tools
├── setup/                      # Database setup utilities
└── maintenance/                # Ongoing maintenance scripts

tests/                          # Comprehensive test suite (91% coverage)
├── unit/                       # Unit tests for individual modules
├── integration/                # Integration tests with real database
├── fixtures/                   # Test data and utilities
└── conftest.py                 # Shared pytest configuration

docs/                           # MkDocs documentation
├── getting-started/            # Installation and quickstart guides
├── queries/                    # Query examples and patterns
├── data/                       # Database schema documentation
└── development/                # Architecture and testing guides

data/                           # Data storage
├── raw/                        # Source JSON data (not in repo)
├── processed/                  # Optimized DuckDB database
└── chroma_db/                  # Vector database for knowledge base

config/                         # Configuration files
├── .env                        # Environment variables (not in repo)
└── requirements.txt            # Compiled dependencies
```

## Architecture Patterns

### Agent Architecture
- **Memory-first**: LangGraph with MemorySaver for conversation state
- **Tool-based**: Modular tools for database queries, analysis, and visualization
- **Configuration-driven**: Centralized `LanduseConfig` dataclass
- **Error handling**: Retry decorators and graceful degradation

### Database Design
- **Star schema**: Fact table with dimension tables for analytics
- **Connection management**: Singleton pattern with retry logic
- **Query optimization**: Automatic LIMIT clauses and result formatting

### Code Organization
- **Separation of concerns**: Agents, tools, utilities, and configuration separated
- **Factory patterns**: LLM creation based on configuration
- **Context managers**: Resource cleanup for database connections
- **Type safety**: Modern Python with type hints and dataclasses

## File Naming Conventions
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_*.py`

## Import Patterns
```python
# Standard library first
import os
from typing import Any, Optional

# Third-party libraries
import duckdb
from langchain_core.tools import BaseTool
from rich.console import Console

# Local imports (relative within package)
from landuse.config.landuse_config import LanduseConfig
from landuse.utilities.security import validate_input
```

## Configuration Management
- **Environment-first**: Configuration from environment variables
- **Dataclass-based**: Type-safe configuration with validation
- **Agent-specific**: Different configs for different agent types
- **Override support**: Runtime configuration overrides

## Testing Structure
- **Fixtures**: Shared test data and database setup in `conftest.py`
- **Mocking**: Database and API mocking for unit tests
- **Integration**: Real database tests with temporary databases
- **Coverage**: Aim for >90% test coverage with meaningful tests

## Documentation Standards
- **Docstrings**: Google-style docstrings for all public functions
- **Type hints**: Full type annotations for better IDE support
- **README**: Comprehensive project documentation
- **API docs**: Auto-generated from docstrings using MkDocs