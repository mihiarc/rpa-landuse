# Technology Stack & Build System

## Core Technologies
- **Python 3.9+**: Primary language with modern type hints and dataclasses
- **DuckDB**: High-performance analytical database with columnar storage
- **LangChain**: AI framework for natural language to SQL translation
- **LangGraph**: State-based agent workflows with memory management
- **Rich**: Terminal UI with colors, tables, and formatting
- **Streamlit**: Web interface (optional)

## AI/ML Stack
- **LLMs**: OpenAI GPT-4o-mini (default) or Anthropic Claude models
- **Agent Architecture**: Memory-first LangGraph workflows with tool integration
- **Vector Store**: ChromaDB for knowledge base retrieval (optional)
- **Prompt Engineering**: Centralized prompt system with configurable styles

## Data & Analytics
- **Database**: DuckDB with star schema design
- **Geospatial**: GeoPandas for geographic analysis and mapping
- **Visualization**: Matplotlib, Plotly for charts and maps
- **Data Processing**: Pandas, NumPy, PyArrow for data manipulation

## Build System & Package Management
- **Package Manager**: `uv` (modern Python package manager)
- **Build System**: Hatchling (pyproject.toml-based)
- **Dependencies**: Managed via pyproject.toml with optional dependency groups

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Install with development tools
uv sync --extra dev

# Run quickstart verification
uv run python quickstart.py
```

### Running the Application
```bash
# Main natural language agent
uv run python src/landuse/agents/landuse_natural_language_agent.py

# Or use the shortcut
uv run rpa-analytics

# Interactive chat interface
uv run python -m landuse
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/landuse --cov-report=html

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Code Quality
```bash
# Linting and formatting
uv run ruff check
uv run ruff format

# Type checking
uv run mypy src/

# Security scanning
uv run safety check
uv run pip-audit
```

### Documentation
```bash
# Serve documentation locally
uv run python scripts/serve_docs.py

# Build documentation
uv run mkdocs build

# Deploy to GitHub Pages
uv run python scripts/deploy_docs.py
```

### Database Operations
```bash
# Convert raw JSON to DuckDB
uv run python scripts/converters/convert_to_duckdb.py

# Enhance database with state mappings
uv run python scripts/setup/enhance_database.py

# Open DuckDB UI in browser
duckdb data/processed/landuse_analytics.duckdb -ui
```

## Configuration
- **Environment**: `.env` files in `config/` directory (recommended) or root
- **Settings**: Centralized configuration via `LanduseConfig` dataclass
- **API Keys**: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` required
- **Database**: `LANDUSE_DB_PATH` environment variable for custom database location