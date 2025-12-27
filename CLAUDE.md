# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPA Land Use Analytics is an AI-powered analytics tool for USDA Forest Service RPA Assessment data. Built with a modern data stack (DuckDB, LangChain, Claude), it processes county-level land use projections and enables users to ask questions in plain English about land use changes across different climate scenarios from the 2020 RPA Assessment.

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
Backend requires `ANTHROPIC_API_KEY` and database configuration.

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

#### Command Line Agents
```bash
# Primary: RPA Analytics Natural Language Agent (command line)
uv run python -m landuse.agents.agent

# Or use the shortcut
uv run rpa-analytics
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
                            │  LangChain + Claude │
                            │   Sonnet 4.5        │
                            └─────────────────────┘
```

### Repository Structure (Monorepo)
- **rpa-landuse-core/**: Python analytics engine and tool-calling agent
- **rpa-landuse-backend/**: FastAPI REST API (deployed on Render)
- **rpa-landuse-frontend/**: Next.js web frontend (deployed on Netlify)

### Data Stack
1. **Raw Data**: 20M+ line JSON file in `data/raw/` with county landuse projections
2. **DuckDB Processing**: `convert_to_duckdb.py` creates optimized star schema
3. **Analytics Database**: `data/processed/landuse_analytics.duckdb` (1.2GB)
4. **Natural Language Agent**: Tool-calling agent with encapsulated SQL queries

### Star Schema Design
- **fact_landuse_transitions**: 5.4M records of land use changes
- **dim_scenario**: Climate scenarios (LM, HM, HL, HH)
- **dim_geography**: 3,075 US counties with metadata
- **dim_landuse**: 5 land use types with descriptive names
- **dim_time**: 6 time periods (2012-2070)

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
- Integrates with tool-calling agent for natural language processing

**Tool-Calling Agent** (`src/landuse/agents/landuse_agent.py`):
- **Simple Architecture**: Claude Sonnet 4.5 with domain-specific tools
- **No SQL Generation**: The LLM never generates SQL - it picks the right tool with parameters
- **11 Specialized Tools**: Each tool encapsulates specific query patterns
- **Streaming Support**: Real-time responses with multi-turn tool calling
- **Conversation Memory**: Sliding window history for context

**Agent Tools** (`src/landuse/agents/tools.py`):
All SQL is encapsulated in tools - the LLM never generates SQL directly:
- `query_land_use_area`: Land use area by state/type/year
- `query_land_use_transitions`: What converts to what
- `query_urban_expansion`: Urban development patterns
- `query_forest_change`: Forest gain/loss
- `query_agricultural_change`: Crop/pasture changes
- `compare_scenarios`: LM vs HM vs HL vs HH
- `compare_states`: State-by-state rankings
- `query_time_series`: Trends 2012-2070
- `query_by_county`: County-level analysis
- `query_top_counties`: Top counties by metric
- `get_data_summary`: Data coverage info

**LandUse Service** (`src/landuse/services/landuse_service.py`):
- Handles all database queries with proper SQL
- Returns formatted results for tools
- Manages DuckDB connections

**Data Converter** (`src/landuse/converters/convert_to_duckdb.py`):
- Processes nested JSON to normalized star schema
- Creates dimension and fact tables
- Adds indexes and views for performance
- Handles 20M+ lines efficiently with progress tracking

**DuckDB Connection** (`src/landuse/connections/duckdb_connection.py`):
- Thread-safe connection management
- Read-only mode by default
- Query caching with TTL

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

## Configuration System

### Environment Variables
Create `config/.env` with these variables:
```bash
# Required API Key
ANTHROPIC_API_KEY=your_anthropic_key

# Database Configuration
LANDUSE_DATABASE__PATH=data/processed/landuse_analytics.duckdb
```

### Agent Usage
```python
from landuse.agents.landuse_agent import LandUseAgent

# Simple usage
with LandUseAgent() as agent:
    response = agent.query("How much forest is in California?")
    print(response)

# Interactive chat
agent = LandUseAgent()
agent.chat()  # Starts interactive CLI
```

## Development Patterns

### Security-First Development
SQL is encapsulated in tools - the LLM never generates SQL directly. This prevents SQL injection and ensures consistent query patterns.

### Error Handling with Custom Exceptions
```python
from landuse.exceptions import DatabaseError, LLMError, ToolExecutionError

try:
    result = agent.query("complex query")
except DatabaseError as e:
    print(f"Database error: {e.message}")
except LLMError as e:
    print(f"LLM error: {e.message}")
```

### Natural Language Queries
The agent understands business context:
```python
agent.query("Which scenarios show the most agricultural land loss?")
agent.query("Compare forest loss between LM and HH scenarios")
agent.query("Show me urbanization patterns in California")
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

### DuckDB Direct Access
```bash
# Browser-based UI
duckdb data/processed/landuse_analytics.duckdb -ui

# Command line
duckdb data/processed/landuse_analytics.duckdb
```

## Dependencies

Key packages (managed via `uv`):
- **AI/LLM**: langchain, langchain-anthropic
- **Data**: pandas, duckdb (1.1.0+), pyarrow, ijson
- **Visualization**: plotly, matplotlib, geopandas
- **Terminal UI**: rich
- **Retry Logic**: tenacity
- **Validation**: pydantic v2
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Docs**: mkdocs, mkdocs-material

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

## Recent Updates (2025)

### AI Stack Migration
- **Switched from OpenAI to Anthropic**: Now uses Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Eliminated LangGraph**: Replaced with simple tool-calling loop
- **Encapsulated SQL**: All SQL is in tools - LLM never generates SQL directly
- **Simplified Architecture**: Removed 5+ manager classes in favor of direct tool-calling pattern

### Current Agent Architecture
```
User Question
     │
     ▼
┌─────────────────────────────────────────┐
│         LandUseAgent                    │
│  (ChatAnthropic + bind_tools)           │
├─────────────────────────────────────────┤
│  1. Convert to LangChain messages       │
│  2. Call LLM with tools                 │
│  3. Execute tool calls                  │
│  4. Return tool results to LLM          │
│  5. Get final response                  │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│         11 Domain Tools                 │
│  (Each encapsulates SQL queries)        │
├─────────────────────────────────────────┤
│  query_land_use_area                    │
│  query_land_use_transitions             │
│  query_urban_expansion                  │
│  query_forest_change                    │
│  query_agricultural_change              │
│  compare_scenarios                      │
│  compare_states                         │
│  query_time_series                      │
│  query_by_county                        │
│  query_top_counties                     │
│  get_data_summary                       │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│         LandUseService                  │
│  (DuckDB queries + formatting)          │
└─────────────────────────────────────────┘
```

### Key Files
- `src/landuse/agents/landuse_agent.py` - Main agent with Claude integration
- `src/landuse/agents/tools.py` - 11 domain-specific tools with Pydantic schemas
- `src/landuse/agents/prompts.py` - System prompt with RPA context
- `src/landuse/services/landuse_service.py` - Database queries and formatting
