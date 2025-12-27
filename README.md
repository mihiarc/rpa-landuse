<div align="center">

# RPA Land Use Analytics

### Ask questions about America's changing landscape. Get instant, data-driven answers.

<br/>

[![Launch App](https://img.shields.io/badge/Launch%20App-rpalanduse.org-0066cc?style=for-the-badge&logo=rocket&logoColor=white)](https://rpalanduse.org)

<br/>

![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=flat-square)
![AI Powered](https://img.shields.io/badge/AI-Powered-blueviolet?style=flat-square)
![Data](https://img.shields.io/badge/Counties-3%2C075-forestgreen?style=flat-square)
![Projections](https://img.shields.io/badge/Projections-2020--2070-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

<br/>

*Powered by official USDA Forest Service RPA Assessment data*

</div>

---

## What You Can Discover

Ask questions in plain English and get immediate answers from millions of land use records:

<table>
<tr>
<td width="50%">

**Urbanization & Development**
> "Which states have the most urban expansion?"

> "What's converting to urban land in California?"

**Forest & Agriculture**
> "How much forest will be lost by 2070?"

> "Compare agricultural land changes across scenarios"

</td>
<td width="50%">

**Climate Scenarios**
> "How do RCP 4.5 and RCP 8.5 differ for my region?"

> "Which scenario shows the highest forest loss?"

**Regional Analysis**
> "Show me land use trends in the Pacific Northwest"

> "Which counties have the most farmland conversion?"

</td>
</tr>
</table>

---

## How It Works

<table>
<tr>
<td align="center" width="33%">
<h3>1. Ask</h3>
Type your question in plain English—no technical queries needed
</td>
<td align="center" width="33%">
<h3>2. Analyze</h3>
AI searches 5.4 million records from official USDA projections
</td>
<td align="center" width="33%">
<h3>3. Discover</h3>
Get formatted answers with supporting data and visualizations
</td>
</tr>
</table>

---

## Features

| Feature | Description |
|:--------|:------------|
| **AI Chat** | Ask complex questions about land use trends, climate impacts, and regional comparisons in natural language |
| **Analytics Dashboard** | Interactive visualizations for land use distribution, climate scenarios, and urbanization patterns |
| **Data Explorer** | SQL query interface with schema browser for custom analysis |
| **Data Export** | Download filtered datasets in CSV, JSON, or Excel format |

---

## Data Coverage

Our analytics are powered by the **USDA Forest Service 2020 RPA Assessment**—the authoritative source for long-term land use projections in the United States.

| Dimension | Coverage |
|:----------|:---------|
| **Geographic** | 3,075 U.S. counties |
| **Temporal** | 2020 – 2070 (50-year projections) |
| **Climate Scenarios** | 5 integrated RCP-SSP scenarios |
| **Land Use Types** | Cropland, Pasture, Forest, Urban, Rangeland |
| **Records** | 5.4+ million land use transitions |

---

## Key Insights from the Data

The RPA Assessment projections reveal important trends for America's landscape:

- **Urban expansion is accelerating** — Developed land is projected to increase under all scenarios, primarily converting from forest
- **Forest loss is widespread** — Overall forest land losses projected between 1.9% and 3.7% by 2070
- **The South faces the greatest change** — Highest increases in developed land and forest loss are projected for the RPA South Region
- **Economic factors drive change** — Land use projections are more sensitive to economic factors than climate variation

---

## About the RPA Assessment

The [Resources Planning Act (RPA) Assessment](https://www.fs.usda.gov/research/rpa) is prepared by the USDA Forest Service in response to the 1974 Forest and Rangeland Renewable Resources Planning Act. The 2020 Assessment provides comprehensive analysis of U.S. forests, rangelands, and the effects of socioeconomic and climate change through 2070.

**Data Citation:** Mihiar, A.J.; Lewis, D.J.; Coulston, J.W. 2023. *Land use projections for the 2020 RPA Assessment.* Fort Collins, CO: Forest Service Research Data Archive. [https://doi.org/10.2737/RDS-2023-0026](https://doi.org/10.2737/RDS-2023-0026)

---

<div align="center">

### Ready to explore?

[![Start Analyzing](https://img.shields.io/badge/Start%20Analyzing-rpalanduse.org-0066cc?style=for-the-badge&logo=rocket&logoColor=white)](https://rpalanduse.org)

</div>

---

<details>
<summary><strong>For Developers</strong></summary>

### Architecture

The platform consists of three components:

| Component | Technology | Repository |
|-----------|------------|------------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS | [rpa-landuse-frontend](https://github.com/mihiarc/rpa-landuse-frontend) |
| **Backend API** | FastAPI, Python 3.11 | [rpa-landuse-backend](https://github.com/mihiarc/rpa-landuse-backend) |
| **Analytics Core** | LangChain, Claude, DuckDB | This repository |

### AI Agent Design

The system uses a **tool-calling pattern** where Claude Sonnet 4.5 selects from 11 domain-specific tools. Each tool encapsulates SQL queries—the LLM never generates SQL directly, preventing injection attacks.

**Tools available:**
- `query_land_use_area` — Land use by state/type/year
- `query_land_use_transitions` — What converts to what
- `query_urban_expansion` — Urban development patterns
- `query_forest_change` — Forest gain/loss analysis
- `compare_scenarios` — RCP/SSP comparisons
- `query_time_series` — Trends 2020-2070
- And 5 more specialized tools

### Quick Start

```bash
# Install dependencies
uv sync

# Configure API key
cp .env.example config/.env
# Edit config/.env with your ANTHROPIC_API_KEY

# Run command-line agent
uv run rpa-analytics
```

### Database

The analytics database uses a **DuckDB star schema**:

- `fact_landuse_transitions` — 5.4M records
- `dim_scenario` — Climate scenarios
- `dim_geography` — 3,075 counties
- `dim_landuse` — 5 land use types
- `dim_time` — Time periods

### Testing

```bash
# Run all tests
uv run pytest tests/ --cov=src/landuse

# Run specific test categories
uv run pytest tests/unit/          # Unit tests
uv run pytest tests/integration/   # Integration tests
```

### Python API

```python
from landuse.agents.landuse_agent import LandUseAgent

with LandUseAgent() as agent:
    response = agent.query("How much forest is in California?")
    print(response)
```

</details>

---

<div align="center">

**[rpalanduse.org](https://rpalanduse.org)** | [GitHub](https://github.com/mihiarc/rpa-landuse) | [USDA RPA Assessment](https://www.fs.usda.gov/research/rpa)

MIT License

</div>
