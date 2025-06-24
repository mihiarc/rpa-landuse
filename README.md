# 🌾 LangChain Landuse Analysis Project

Advanced natural language analysis of county-level land use transitions using AI agents and modern data stack (DuckDB, LangChain, GPT-4).

## ✨ Features

- **🤖 Natural Language Queries**: Ask questions like "Which scenarios show the most agricultural land loss?"
- **🦆 Modern Data Stack**: DuckDB star schema optimized for analytics
- **📊 Rich Analytics**: Automatic summary statistics and business insights
- **🎨 Beautiful Interface**: Rich terminal UI with colors and markdown
- **🌍 Climate Analysis**: Compare RCP/SSP scenarios and geographic patterns

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Install dependencies
uv sync

# Guided setup (creates .env file and tests everything)
uv run python setup_agents.py
```

### 2. Configure API Access
```bash
# Copy example environment file to config directory (recommended)
cp .env.example config/.env

# Edit config/.env and add your OpenAI API key:
# OPENAI_API_KEY=your_api_key_here
```

### 3. Try the Natural Language Query Agent
```bash
# Interactive landuse analysis with natural language
uv run python scripts/agents/landuse_natural_language_agent.py

# Test with sample queries
uv run python scripts/agents/test_landuse_agent.py

# Alternative: DuckDB UI in browser
duckdb data/processed/landuse_analytics.duckdb -ui
```

### 4. Example Questions to Try
- "Which scenarios show the most agricultural land loss?"
- "Compare forest loss between RCP45 and RCP85 scenarios"
- "Which states have the most urban expansion?"
- "Show me crop to pasture transitions by state"

## 📁 Project Structure

```
langchain-landuse/
├── 🤖 scripts/agents/          # AI-powered query agents
│   ├── landuse_natural_language_agent.py  # Natural language → DuckDB SQL
│   └── test_landuse_agent.py   # Sample queries & testing
├── 🔄 scripts/converters/      # Data transformation tools
│   └── convert_to_duckdb.py    # JSON → DuckDB star schema
├── 📊 data/
│   ├── raw/                    # Source JSON data (20M+ lines)
│   └── processed/              # Optimized DuckDB database
│       └── landuse_analytics.duckdb  # Star schema (1.2GB)
├── 📚 docs/                    # Comprehensive documentation
│   ├── api/landuse-query-agent.md
│   └── data/duckdb-schema.md
├── ⚙️ config/requirements.txt   # Python dependencies
├── 🌍 .env.example             # Environment configuration
└── 🚀 setup_agents.py          # Guided setup script
```

## 🗄️ Database Schema

**Modern DuckDB Star Schema** optimized for analytics:

- **`fact_landuse_transitions`**: 5.4M records of land use changes
- **`dim_scenario`**: 20 climate scenarios (RCP45/85, SSP1/5)
- **`dim_geography`**: 3,075 US counties with FIPS codes
- **`dim_landuse`**: 5 land use types (Crop, Pasture, Forest, etc.)
- **`dim_time`**: 6 time periods (2012-2100)

**Pre-built Views:**
- `v_agriculture_transitions`: Agricultural land changes
- `v_scenario_summary`: Aggregated scenario comparisons

## 🎯 Key Capabilities

### Natural Language Analysis
```
🌾 Ask> "Which scenarios show the most agricultural land loss?"

🦆 DuckDB Query Results (20 rows)
SQL: SELECT s.scenario_name, SUM(f.acres) as acres_lost 
     FROM fact_landuse_transitions f 
     JOIN dim_scenario s ON f.scenario_id = s.scenario_id...

Results:
scenario_name                    acres_lost
CNRM_CM5_rcp85_ssp5             2,648,344
MRI_CGCM3_rcp85_ssp5            2,643,261
...
```

### Business Intelligence
- **Agricultural Impact**: Track farmland loss and conversion patterns
- **Climate Scenarios**: Compare emission pathways (RCP45 vs RCP85)
- **Geographic Analysis**: State and county-level trends
- **Urbanization Pressure**: Development vs conservation patterns
