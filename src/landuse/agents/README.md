# Agent Scripts

LangChain-based agents for data analysis:

- `data_engineering_agent.py` - Main data engineering agent with file operations
- `test_agent.py` - Test script with sample data generation

# SQL Query Agents

This directory contains specialized AI agents for natural language database querying and analysis.

## 🌾 Landuse Natural Language Agent

**Specialized for landuse transition analysis** - The most advanced agent for converting natural language questions into optimized DuckDB SQL queries for landuse data.

### Features
- 🤖 **Natural Language Processing**: Converts English questions to SQL
- 🦆 **DuckDB Optimization**: Generates efficient star schema joins
- 📊 **Rich Analytics**: Automatic summary statistics and business context
- 🎨 **Beautiful Interface**: Rich terminal interface with colors and markdown

### Quick Start
```bash
# Interactive chat mode
uv run python scripts/agents/landuse_natural_language_agent.py

# Test with sample queries
uv run python scripts/agents/test_landuse_agent.py
```

### Example Questions
- "Which scenarios show the most agricultural land loss?"
- "Compare forest loss between RCP45 and RCP85 scenarios"
- "Which states have the most urban expansion?"
- "Show me crop to pasture transitions by state"

**[📖 Complete Documentation →](../../docs/api/landuse-query-agent.md)**

---

## 🔍 General Data Agent

**Multi-database and file format support** - Versatile agent that works with SQLite, DuckDB, CSV, JSON, and Parquet files for general data operations.

### Features
- 🗃️ **Multi-Database**: SQLite, DuckDB, CSV, JSON, Parquet support
- 🔧 **Data Transformation**: Convert between formats
- 📈 **Analysis Tools**: Statistical analysis and visualization
- 🛠️ **Database Operations**: Schema exploration, query execution

### Quick Start
```bash
# Interactive chat mode
```

**[📖 Complete Documentation →](../../docs/api/agent.md)**

---

## Choosing the Right Agent

### Use **Landuse Natural Language Agent** when:
- ✅ Analyzing landuse transition data specifically
- ✅ Want natural language to SQL conversion
- ✅ Need business context and interpretations
- ✅ Working with the DuckDB landuse database

### Use **General Data Agent** when:
- ✅ Working with multiple database types
- ✅ Need data transformation capabilities
- ✅ Analyzing various data formats (CSV, JSON, etc.)
- ✅ Performing general database operations

---

## Architecture

Both agents use:
- **LangChain**: Agent framework and tool orchestration
- **OpenAI GPT-4**: Natural language understanding
- **Rich**: Beautiful terminal interfaces
- **Pydantic**: Data validation and parsing

### Landuse Agent Architecture
```
Natural Language Query
        ↓
    GPT-4 Processing
        ↓
    Star Schema SQL Generation
        ↓
    DuckDB Execution
        ↓
    Rich Formatted Results + Business Context
```

### General Agent Architecture
```
Natural Language Query
        ↓
    GPT-4 Processing
        ↓
    Multi-Database Tool Selection
        ↓
    Query Execution (SQLite/DuckDB/Files)
        ↓
    Formatted Results
```

---

## Performance Comparison

| Feature | Landuse Agent | General Agent |
|---------|---------------|---------------|
| **Landuse Queries** | 🟢 Optimized | 🟡 Basic |
| **Multi-Database** | 🔴 DuckDB Only | 🟢 Full Support |
| **Natural Language** | 🟢 Domain-Specific | 🟡 General |
| **Business Context** | 🟢 Rich Insights | 🔴 Limited |
| **Performance** | 🟢 Star Schema Optimized | 🟡 Standard |
| **Ease of Use** | 🟢 Specialized | 🟡 General Purpose |

---

## Future Enhancements

### Planned Features
- **Visualization Generation**: Automatic chart creation from queries
- **Export Capabilities**: Direct CSV/Excel export of analysis results
- **Saved Query Library**: Store and reuse common analyses
- **Multi-Database Landuse**: Extend landuse agent to multiple databases
- **Real-time Collaboration**: Share queries and results with teams

### Contributing
1. Add new query patterns to the landuse agent examples
2. Improve business context explanations
3. Enhance error handling and recovery
4. Optimize SQL generation patterns
5. Add new data source connectors to the general agent

---

## Getting Started

1. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Try the landuse agent:**
   ```bash
   uv run python scripts/agents/landuse_natural_language_agent.py
   ```

4. **Ask natural language questions:**
   ```
   🌾 Ask> Which scenarios show the most agricultural land loss?
   ```

Both agents represent the cutting edge of natural language data analysis, making complex database queries accessible through simple English questions!
