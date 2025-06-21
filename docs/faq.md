# Frequently Asked Questions

Common questions about the LangChain Land Use Analysis system.

## General Questions

### What is this project?

The LangChain Land Use Analysis system allows you to query and analyze county-level land use projections using natural language. Instead of writing SQL, you can ask questions like "Show me forest loss in California" and get meaningful results.

### What data does it analyze?

The system analyzes USDA Forest Service RPA (Resources Planning Act) land use projections:
- **Coverage**: All US counties
- **Time Period**: 2020-2100
- **Scenarios**: Baseline, High Crop Demand, High Forest, High Urban
- **Land Types**: Crop, Pasture, Forest, Urban, Range

### Do I need to know SQL?

No! The agent converts your natural language questions into SQL automatically. You can ask questions in plain English like:
- "What counties have the most urban growth?"
- "Show me forest to cropland transitions"
- "Compare scenarios for agricultural land"

## Setup Questions

### What are the system requirements?

- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Disk Space**: 2GB for data and dependencies
- **OS**: Windows, macOS, or Linux
- **API Key**: OpenAI API key required

### How do I get an OpenAI API key?

1. Visit https://platform.openai.com/signup
2. Create an account
3. Go to API keys section
4. Create new secret key
5. Add to your `.env` file

### Which OpenAI model should I use?

```bash
# Recommended (best accuracy)
AGENT_MODEL=gpt-4-turbo-preview

# Budget option (faster, less accurate)
AGENT_MODEL=gpt-3.5-turbo

# High accuracy (more expensive)
AGENT_MODEL=gpt-4
```

### Can I use it offline?

The data processing and queries work offline, but the natural language interpretation requires an internet connection to reach OpenAI's API.

## Data Questions

### What do the land use categories mean?

- **Crop**: Agricultural land for growing crops
- **Pasture**: Land for livestock grazing
- **Forest**: Wooded areas (natural and managed)
- **Urban**: Developed areas (cities, towns, infrastructure)
- **Range**: Natural grasslands and shrublands

### What's the difference between the tables?

| Table | Description | Use Case |
|-------|-------------|----------|
| `landuse_transitions` | All transitions including same-to-same | Complete analysis |
| `landuse_transitions_ag` | Crop+Pasture combined as Agriculture | Simplified agricultural analysis |
| `landuse_changes_only` | Excludes unchanged land | Focus on actual changes |
| `landuse_changes_only_ag` | Changes with agricultural aggregation | Simplified change analysis |

### What scenarios are available?

1. **Baseline**: Most likely future based on current trends
2. **High Crop Demand**: Increased agricultural pressure
3. **High Forest**: Strong forest conservation
4. **High Urban**: Accelerated urbanization

### Why are areas in "1000 acres"?

This unit makes large numbers more manageable. To convert:
- Acres: multiply by 1,000
- Square miles: multiply by 1.5625
- Hectares: multiply by 404.686

## Usage Questions

### How do I start a query?

Simply run the agent and type your question:
```bash
uv run python scripts/agents/test_agent.py

You> Show me urban growth in Texas counties
```

### Can I export results?

Yes! Ask the agent to export:
```
You> Export the results to urban_growth_texas.csv
```

Supported formats: CSV, JSON, Parquet

### How do I query specific years?

Include the year in your question:
```
You> Show me forest area in 2050
You> Compare urban growth between 2030 and 2080
You> What changes happen in the 2040-2050 decade?
```

### Can I compare scenarios?

Yes! Ask comparison questions:
```
You> Compare forest area between all scenarios in 2100
You> Which scenario has the most agricultural land?
You> Show the difference between Baseline and High Urban
```

### How do I focus on specific counties?

Use FIPS codes or descriptions:
```
You> Show data for FIPS 06037 (Los Angeles)
You> Analyze California counties (FIPS starting with 06)
You> Focus on Midwest agricultural counties
```

## Technical Questions

### How does the natural language processing work?

1. Your question → LangChain agent
2. Agent uses GPT model to understand intent
3. Generates appropriate SQL query
4. Executes query on database
5. Formats results in natural language

### Can I see the generated SQL?

Yes, the agent shows the SQL it generates:
```
Query: SELECT * FROM landuse_transitions WHERE ...
Results: 123 rows
[Table of results]
```

### How accurate is the SQL generation?

The GPT-4 models are very accurate for:
- Basic queries (>95% accuracy)
- Complex queries (>85% accuracy)
- Domain-specific terms (understands "forest loss", "urban growth", etc.)

### Can I write SQL directly?

Yes! Use this format:
```
You> Query database.db: SELECT * FROM table WHERE condition
```

### Is the data real-time?

No, this is projection data created by USDA models. It represents scenarios of possible futures, not real-time monitoring.

## Performance Questions

### Why is my query slow?

Common causes:
1. Large result sets - add limits
2. Complex aggregations - simplify query
3. Missing indexes - use indexed columns (scenario, year, fips)

### How can I make queries faster?

1. Use filtered tables (`_changes_only`)
2. Add LIMIT clauses
3. Filter by indexed columns first
4. Query specific years instead of all years

### What's the maximum file size I can process?

Default limit is 100MB (configurable):
```bash
MAX_FILE_SIZE_MB=200  # Increase limit
```

Large files are automatically sampled for preview.

## Troubleshooting Questions

### Why does it say "Database not found"?

Run the data conversion first:
```bash
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

### Why am I getting API key errors?

1. Check `.env` file exists in `config/`
2. Verify key starts with `sk-`
3. Ensure no extra quotes or spaces
4. Check API key is active on OpenAI

### Can I use a different LLM provider?

Currently supports OpenAI. The architecture allows for other providers (Claude, local models) with code modifications.

### How do I update the data?

Place new JSON data in `data/raw/` and run:
```bash
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

## Advanced Questions

### Can I add custom tools?

Yes! See the [Contributing Guide](development/contributing.md) for instructions on adding tools to the agent.

### Can I modify the land use categories?

Yes, edit the `LAND_USE_MAP` in the converter scripts:
```python
LAND_USE_MAP = {
    'cr': 'Cropland',  # Change naming
    'new': 'NewCategory'  # Add categories
}
```

### Can I integrate this with other systems?

Yes! Options include:
- Python API for programmatic access
- Export functions for data pipelines
- Web service wrapper possible
- Jupyter notebook integration

### Can I use my own projections?

Yes, if your data follows the same JSON structure. See [Data Processing](data/processing.md) for format requirements.

## Best Practices Questions

### What makes a good query?

**Good queries are:**
- Specific: "Show forest loss in California between 2020-2050"
- Clear: Use standard terms (urban, forest, crop)
- Focused: One question at a time

**Avoid:**
- Vague: "Show me some data"
- Complex: Multiple unrelated questions
- Ambiguous: "What changes?" (which changes?)

### How should I explore the data?

1. Start broad: "What tables are available?"
2. Understand structure: "Describe the main table"
3. Look at samples: "Show me 10 example rows"
4. Focus analysis: "Now show me specific patterns"

### When should I use each table?

- **Full analysis**: Use base `landuse_transitions`
- **Change focus**: Use `landuse_changes_only`
- **Agricultural studies**: Use `_ag` tables
- **Performance critical**: Use filtered views

## Getting More Help

### Where can I find more examples?

- [Query Examples](queries/examples.md) - Extensive query patterns
- [Workflows](examples/workflows.md) - Step-by-step guides
- [Notebooks](examples/notebooks.md) - Interactive examples

### How do I report issues?

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Search existing GitHub issues
3. Create new issue with:
   - Error message
   - Steps to reproduce
   - System information

### Can I contribute?

Yes! See [Contributing Guide](development/contributing.md) for:
- Code contributions
- Documentation improvements
- Bug reports
- Feature requests

### Where can I learn more?

- **LangChain**: https://python.langchain.com/
- **OpenAI API**: https://platform.openai.com/docs
- **SQLite**: https://www.sqlite.org/docs.html
- **Project GitHub**: Link to your repository