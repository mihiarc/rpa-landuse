# Data Directory

## Structure

```
data/
├── raw/              # Original source data files
│   └── *.json       # Raw RPA Assessment data files
└── processed/        # Converted databases and processed files
    └── landuse_analytics.duckdb  # Primary DuckDB database
```

## Main Database

**File**: `processed/landuse_analytics.duckdb`
**Format**: DuckDB database (optimized columnar format)
**Size**: ~1.2 GB
**Records**: 5.4M+ land use transition records

### Database Features

- **Star Schema Design**: Optimized for analytics with dimension and fact tables
- **Bulk Loading**: Uses DuckDB COPY optimization for 5-10x faster data loading
- **Indexed**: Strategic indexes on key columns for query performance
- **Views**: Pre-built views for common query patterns

## Database Schema Overview

### Fact Table
- **fact_landuse_transitions**: 5.4M records of land use changes across scenarios

### Dimension Tables
- **dim_scenario**: 20 climate scenarios (RCP45/85, SSP1/5)
- **dim_geography**: 3,075 US counties with state/region metadata
- **dim_landuse**: 5 land use types (Crop, Pasture, Forest, Urban, Rangeland)
- **dim_time**: 6 time periods (2012-2100)

### Pre-Built Views

```sql
-- Common analysis views
- transition_summary          -- Aggregated transitions by scenario/period
- county_landuse_totals       -- Total land use by county
- scenario_comparisons        -- Cross-scenario comparisons
- agriculture_transitions     -- Agricultural land changes
- urbanization_patterns       -- Urban development trends
```

## Data Sources

### Primary Source
- **USDA Forest Service 2020 RPA Assessment**
- County-level land use projections
- 20 integrated climate-socioeconomic scenarios
- Temporal coverage: 2012-2100

### Raw Data Format
- **Format**: JSON (nested structure)
- **Size**: 20M+ lines
- **Processing**: Converted to normalized star schema in DuckDB

## Accessing the Database

### Using DuckDB CLI
```bash
# Interactive CLI
duckdb data/processed/landuse_analytics.duckdb

# Browser-based UI
duckdb data/processed/landuse_analytics.duckdb -ui
```

### Using Python
```python
import duckdb

# Read-only connection (recommended for analysis)
conn = duckdb.connect('data/processed/landuse_analytics.duckdb', read_only=True)

# Query the database
result = conn.execute("""
    SELECT county_name, state,
           SUM(acres) as total_acres
    FROM fact_landuse_transitions
    JOIN dim_geography USING (geography_id)
    WHERE landuse_to = 'Urban'
    GROUP BY county_name, state
    ORDER BY total_acres DESC
    LIMIT 10
""").fetchdf()

print(result)
```

### Using the Natural Language Agent
```bash
# Command line agent
uv run python -m landuse.agents.agent

# Streamlit dashboard
uv run streamlit run landuse_app.py
```

## Data Conversion

### Converting Raw JSON to DuckDB

```bash
# Standard conversion (optimized bulk loading)
uv run python scripts/converters/convert_to_duckdb.py

# Traditional insert method (for comparison/debugging)
uv run python scripts/converters/convert_to_duckdb.py --no-bulk-copy
```

### Performance
- **Bulk COPY method**: ~10-15 minutes for full dataset
- **Traditional inserts**: ~60-90 minutes for full dataset
- **Recommendation**: Always use bulk COPY (default)

## Data Quality

### Validation
- All records validated during ETL process
- Foreign key relationships enforced
- Data types validated with Pydantic models
- Completeness checks on required fields

### Coverage
- **Geographic**: All 3,075 counties in conterminous US
- **Temporal**: 6 projection periods (2012-2100)
- **Scenarios**: 20 climate-socioeconomic combinations
- **Land Uses**: 5 major categories tracked

## Related Documentation

- **[Database Schema](../docs/data/duckdb-schema.md)** - Complete schema documentation
- **[Data Dictionary](../docs/data/data-dictionary.md)** - Field definitions and descriptions
- **[Query Guide](../docs/queries/complete-guide.md)** - How to query the database
- **[Converter API](../docs/api/converters.md)** - Data conversion tools

---

*For detailed information about the database structure, schema design, and query patterns, see the [Complete Database Reference](../docs/data/complete-reference.md).*
