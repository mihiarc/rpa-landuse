# LangChain Land Use Analysis Project

Analyzes county-level land use transitions using LangChain agents and SQLite.

## Quick Start:

1. Install dependencies:
   ```bash
   uv pip install -r config/requirements.txt
   ```

2. Set OpenAI API key in `config/.env`

3. Run the agent:
   ```bash
   uv run python scripts/agents/test_agent.py
   ```

## Project Structure:
- `scripts/` - Python scripts
  - `converters/` - Data conversion tools
  - `agents/` - LangChain agents
- `data/` - Data files
  - `raw/` - Source data
  - `processed/` - Converted databases
  - `samples/` - Test data
- `config/` - Configuration files
- `docs/` - Documentation

## Main Database:
`data/processed/landuse_transitions_with_ag.db` contains land use transitions with views for:
- Individual land uses (crop/pasture separate)
- Agriculture aggregated (crop+pasture combined)
- Change-only views (excluding same-to-same transitions)
