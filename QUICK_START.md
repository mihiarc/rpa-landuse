# 🚀 Quick Start Guide

## 1. Setup (One-time)

```bash
# Clone and setup
git clone <repo>
cd langchain-landuse
uv sync

# Guided setup
uv run python setup_agents.py
```

## 2. Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Set it up (choose one):

   **Option A: Quick setup script**
   ```bash
   uv run python set_openai_key.py
   ```

   **Option B: Manual edit**
   ```bash
   # Edit config/.env
   OPENAI_API_KEY=your_key_here
   ```

## 3. Start Analyzing! 

```bash
# Natural language queries
uv run python scripts/agents/landuse_query_agent.py
```

## 4. Try These Questions

**Agricultural Analysis:**
- "Which scenarios show the most agricultural land loss?"
- "How much farmland is being converted to urban areas?"

**Climate Analysis:**
- "Compare forest loss between RCP45 and RCP85 scenarios"
- "Which states are seeing the most reforestation?"

**Geographic Patterns:**
- "Which states have the most urban expansion?"
- "Show me agricultural changes in California"

## 5. Alternative Interfaces

```bash
# DuckDB UI (browser-based)
duckdb data/processed/landuse_analytics.duckdb -ui
# → Open http://localhost:4213

# General SQL agent
uv run python scripts/agents/sql_query_agent.py

# Test script
uv run python scripts/agents/test_landuse_agent.py
```

## 6. Help & Documentation

- Type `help` in any agent for examples
- Type `schema` to see database structure
- Read full docs: `docs/api/landuse-query-agent.md`

---

## Troubleshooting

**"OpenAI API key not found"**
→ Set `OPENAI_API_KEY` in `config/.env` file

**"Database not found"**
→ Run `uv run python scripts/converters/convert_to_duckdb.py`

**"Import errors"**
→ Run `uv sync` to install dependencies

---

**🎉 You're ready to explore landuse data with natural language!** 