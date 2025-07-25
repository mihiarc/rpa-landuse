# Modern DuckDB Tools & Database Redesign

## 🎯 Project Transformation

We've successfully redesigned your landuse data from a **single denormalized table** (8.6M rows) into a **modern star schema** optimized for analytics. This follows 2025 best practices for data warehousing and analytics.

### Before vs After

| Aspect | Before (SQLite) | After (DuckDB) |
|--------|----------------|----------------|
| **Schema** | Single table with repeated data | Star schema with 5 normalized tables |
| **Storage** | String repetition, inefficient | Integer foreign keys, columnar storage |
| **Performance** | Slow aggregations | Fast analytical queries |
| **Scalability** | Limited | Optimized for large datasets |
| **Analytics** | Manual SQL only | Built-in views + modern tooling |
| **Data Quality** | No constraints | Referential integrity |

## 🦆 Our New DuckDB Schema

```
📊 Fact Table: fact_landuse_transitions (main data)
├── 🌍 dim_geography (counties, states, regions)
├── ⏰ dim_time (year ranges, periods)
├── 🏞️ dim_landuse (crop, forest, urban, etc.)
└── 🌡️ dim_scenario (climate models, RCP/SSP scenarios)
```

## 🔧 Modern DuckDB Tools (2025)

### 1. **DuckDB Native UI** (Official, 2025)
```bash
# Launch built-in web UI (DuckDB v1.2.1+)
duckdb data/processed/landuse_analytics.duckdb -ui
```

**Features:**
- ✅ Notebook-style interface (like Jupyter)
- ✅ Interactive SQL editor with syntax highlighting
- ✅ Data explorer with schema browsing
- ✅ Query history and results visualization
- ✅ No installation required - runs in browser
- ✅ Completely local (data never leaves your computer)

### 2. **Duck-UI** (Community)
```bash
# Web-based DuckDB interface
docker run -p 5522:5522 ghcr.io/caioricciuti/duck-ui:latest
```

**Features:**
- ✅ Modern React-based interface
- ✅ File import/export (CSV, JSON, Parquet)
- ✅ Data visualization capabilities
- ✅ Query management and history
- ✅ WebAssembly-powered (runs in browser)

### 3. **Our Enhanced SQL Query Agent**
```bash
# Run our custom agent with DuckDB support
uv run python scripts/agents/sql_query_agent.py
```

**Features:**
- ✅ DuckDB-optimized queries with `query_duckdb` tool
- ✅ Rich terminal interface with progress bars
- ✅ Automatic summary statistics for numeric columns
- ✅ Integration with LangChain for AI-powered analysis
- ✅ Smart query suggestions and error handling

## 📈 Analytics Capabilities

### Pre-built Views
```sql
-- Agricultural transitions analysis
SELECT * FROM v_agriculture_transitions 
WHERE scenario_name = 'CNRM_CM5_rcp45_ssp1';

-- Scenario summary with aggregations
SELECT * FROM v_scenario_summary 
ORDER BY total_acres DESC;
```

### Advanced Analytics Examples
```sql
-- Agricultural land loss by state
SELECT 
    s.scenario_name,
    g.state_code,
    SUM(f.acres) as acres_lost
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE fl.landuse_category = 'Agriculture' 
  AND tl.landuse_category != 'Agriculture'
  AND f.transition_type = 'change'
GROUP BY s.scenario_name, g.state_code
ORDER BY acres_lost DESC;

-- Time series analysis
SELECT 
    t.start_year,
    t.end_year,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY t.start_year, t.end_year, fl.landuse_name, tl.landuse_name
ORDER BY t.start_year, total_acres DESC;
```

## 🚀 Performance Benefits

### Query Speed Improvements
- **Aggregations**: 10-100x faster with columnar storage
- **Filtering**: Instant filtering on any dimension
- **Joins**: Optimized star schema joins
- **Memory Usage**: Reduced through integer foreign keys

### Storage Efficiency
- **Before**: Repeated strings in 8.6M rows
- **After**: Normalized dimensions + integer references
- **Compression**: DuckDB's columnar compression
- **Indexing**: Strategic indexes on common query patterns

## 🛠️ Development Workflow

### 1. Data Exploration
```bash
# Use DuckDB UI for interactive exploration
duckdb data/processed/landuse_analytics.duckdb -ui

# Or use our SQL Query Agent
uv run python scripts/agents/sql_query_agent.py
```

### 2. Advanced Analytics
```python
# Python integration
import duckdb
conn = duckdb.connect('data/processed/landuse_analytics.duckdb')
df = conn.execute("SELECT * FROM v_scenario_summary").df()
```

### 3. Visualization
```python
# Direct pandas integration for plotting
import matplotlib.pyplot as plt
import seaborn as sns

# Query and visualize
df = conn.execute("""
    SELECT s.scenario_name, SUM(f.acres) as total_acres
    FROM fact_landuse_transitions f
    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
    GROUP BY s.scenario_name
""").df()

sns.barplot(data=df, x='scenario_name', y='total_acres')
plt.xticks(rotation=45)
plt.show()
```

## 🔮 Next Steps & Modern Practices

### 1. **Data Quality & Testing**
```sql
-- Add data quality checks
SELECT COUNT(*) as null_acres 
FROM fact_landuse_transitions 
WHERE acres IS NULL;

-- Referential integrity checks
SELECT COUNT(*) as orphaned_records
FROM fact_landuse_transitions f
LEFT JOIN dim_scenario s ON f.scenario_id = s.scenario_id
WHERE s.scenario_id IS NULL;
```

### 2. **Performance Monitoring**
```sql
-- Query performance analysis
EXPLAIN ANALYZE SELECT ...;

-- Table statistics
SELECT table_name, estimated_size 
FROM duckdb_tables();
```

### 3. **Integration with Modern Stack**
- **dbt**: Data transformation and testing
- **Great Expectations**: Data quality validation
- **Streamlit**: Interactive dashboards
- **Observable**: Collaborative analytics notebooks
- **Evidence**: BI reporting from SQL

### 4. **Advanced DuckDB Features**
```sql
-- Spatial analysis (if geographic data available)
INSTALL spatial;
LOAD spatial;

-- Time series analysis
INSTALL icu;
LOAD icu;

-- Machine learning
INSTALL ml;
LOAD ml;
```

## 📚 Learning Resources

### Official Documentation
- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB UI Guide](https://duckdb.org/docs/stable/core_extensions/ui.html)
- [SQL Reference](https://duckdb.org/docs/stable/sql/introduction.html)

### Community Tools
- [Awesome DuckDB](https://github.com/davidgasquez/awesome-duckdb)
- [DuckDB Extensions](https://duckdb.org/docs/stable/extensions/overview.html)
- [DuckDB Cookbook](https://duckdb.org/docs/stable/guides/overview.html)

### Books & Courses
- "DuckDB: Up and Running" by Wei-Meng Lee (2024)
- Modern data stack courses focusing on DuckDB
- Analytics engineering best practices

## 🎯 Your Learning Path

1. **Explore the new schema** using DuckDB UI
2. **Write analytical queries** using our SQL Query Agent
3. **Build visualizations** with Python integration
4. **Learn modern analytics patterns** with star schema
5. **Experiment with DuckDB extensions** for advanced features

This redesign positions your project at the **cutting edge of 2025 data analytics**, using modern tools and practices that are becoming industry standard! 