# Converters API Reference

Documentation for the data conversion scripts that transform raw JSON data into queryable DuckDB databases.

## Overview

The converters module contains scripts for processing land use projection data:

```
scripts/converters/
├── convert_to_duckdb.py          # Modern DuckDB converter (RECOMMENDED)
├── convert_json_to_parquet.py    # JSON to Parquet conversion
├── convert_landuse_to_db.py      # Legacy SQLite converter
├── convert_landuse_transitions.py # Legacy transition converter
├── convert_landuse_with_agriculture.py # Legacy SQLite with agriculture
├── convert_landuse_nested.py     # Legacy nested converter
├── add_change_views.py           # Add views to existing database
└── add_land_area_view.py         # Add land area calculations
```

## Core Converters

### convert_to_duckdb.py (RECOMMENDED)

Modern converter that transforms raw JSON land use projections into a well-structured DuckDB database using star schema design and bulk loading optimization.

```python
# Basic usage
uv run python scripts/converters/convert_to_duckdb.py
```

**Key Features:**
- **Star Schema Design**: Normalized dimension and fact tables
- **Bulk Loading**: 5-10x faster using DuckDB COPY with Parquet
- **Rich Progress Tracking**: Beautiful terminal progress bars
- **Data Validation**: Comprehensive integrity checks
- **Modern Architecture**: Optimized for analytics workloads

**Output:**
- Creates `data/processed/landuse_analytics.duckdb` (1.2GB)
- **Tables**: `fact_landuse_transitions`, `dim_scenario`, `dim_geography_enhanced`, `dim_landuse`, `dim_time`
- **Views**: Pre-built analytical views for common queries
- **Indexes**: Optimized for query performance

### convert_landuse_to_db.py (LEGACY)

Legacy converter for SQLite database format. Use `convert_to_duckdb.py` for new projects.

```python
# Legacy usage (not recommended)
uv run python scripts/converters/convert_landuse_to_db.py
```

**Key Functions:**

```python
def process_matrix_data(matrix_data, scenario, year, year_range, fips):
    """Convert transition matrix to normalized records.
    
    Args:
        matrix_data: List of transition matrix rows
        scenario: Scenario name (e.g., 'Baseline')
        year: End year of transition period
        year_range: Period string (e.g., '2020-2030')
        fips: County FIPS code
        
    Returns:
        List of transition dictionaries
    """
```

**Output:**
- Creates `landuse_transitions.db` (SQLite)
- Table: `landuse_transitions`
- ~1.2 million transition records

### convert_landuse_with_agriculture.py (LEGACY)

Legacy enhanced converter that includes agricultural aggregation views for SQLite.

```python
# Legacy usage with agricultural aggregation
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

**Features:**
- Creates base transition table (SQLite)
- Adds agricultural aggregation (Crop + Pasture)
- Creates filtered views (changes only)
- Adds performance indexes

**Output Tables:**
1. `landuse_transitions` - All transitions
2. `landuse_transitions_ag` - With agricultural aggregation
3. `landuse_changes_only` - Excluding same-to-same
4. `landuse_changes_only_ag` - Changes with ag aggregation

### add_change_views.py

Adds filtered views to existing database (works with both SQLite and DuckDB).

```python
# Add views to existing database
uv run python scripts/converters/add_change_views.py
```

**Creates Views:**
```sql
-- Changes only view
CREATE VIEW landuse_changes_only AS
SELECT * FROM landuse_transitions
WHERE from_land_use != to_land_use
  AND from_land_use != 'Total'
  AND to_land_use != 'Total';
```

### convert_json_to_parquet.py

Utility converter for creating Parquet files from JSON data.

```python
# Convert JSON to Parquet for analysis
uv run python scripts/converters/convert_json_to_parquet.py
```

**Features:**
- Efficient Parquet format for analytics
- Preserves nested data structure
- Compatible with pandas and DuckDB
- Smaller file sizes and faster I/O

## Utility Functions

### Land Use Mapping

```python
LAND_USE_MAP = {
    'cr': 'Crop',
    'ps': 'Pasture',
    'rg': 'Range',
    'fr': 'Forest',
    'ur': 'Urban',
    't1': 'Total',  # Row sum
    't2': 'Total'   # Column sum
}
```

### Year Extraction

```python
def extract_end_year(year_range):
    """Extract end year from range string.
    
    Args:
        year_range: String like '2020-2030'
        
    Returns:
        int: End year (2030)
    """
    return int(year_range.split('-')[1])
```

### Value Conversion

```python
def convert_value(value):
    """Convert Decimal/numeric to float.
    
    Handles various numeric types safely.
    """
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0
```

## Processing Large Files

### Modern Bulk Loading (DuckDB)

The modern converter uses DuckDB's COPY command with Parquet for optimal performance:

```python
class LanduseDataConverter:
    def bulk_load_fact_table(self, fact_data):
        """Use DuckDB COPY for 5-10x performance improvement."""
        parquet_path = self.temp_dir / "fact_transitions.parquet"
        
        # Write to Parquet first
        fact_df.to_parquet(parquet_path, index=False)
        
        # Bulk load with COPY
        self.conn.execute(f"""
            COPY fact_landuse_transitions 
            FROM '{parquet_path}'
            (FORMAT PARQUET)
        """)
```

### Legacy Streaming JSON Processing

For legacy converters, use streaming:

```python
import ijson

def process_large_json(json_path):
    """Stream process large JSON files."""
    with open(json_path, 'rb') as file:
        parser = ijson.items(file, 'item')
        
        batch = []
        for item in parser:
            batch.append(process_item(item))
            
            if len(batch) >= 10000:
                insert_batch(batch)
                batch = []
```

### Progress Tracking

Using Rich for progress display:

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Converting...", total=county_count)
    
    for county in counties:
        process_county(county)
        progress.update(task, advance=1)
```

## Database Schema Creation

### Modern DuckDB Star Schema (convert_to_duckdb.py)

```sql
-- Fact table
CREATE TABLE fact_landuse_transitions (
    scenario_id INTEGER,
    geography_id INTEGER,
    time_id INTEGER,
    from_landuse_id INTEGER,
    to_landuse_id INTEGER,
    acres DOUBLE,
    transition_type VARCHAR  -- 'change' or 'same'
);

-- Dimension tables
CREATE TABLE dim_scenario (
    scenario_id INTEGER PRIMARY KEY,
    scenario_name VARCHAR,
    rcp_scenario VARCHAR,
    ssp_scenario VARCHAR,
    description VARCHAR
);

CREATE TABLE dim_geography_enhanced (
    geography_id INTEGER PRIMARY KEY,
    county_fips VARCHAR,
    county_name VARCHAR,
    state_code VARCHAR,
    state_name VARCHAR,
    region_name VARCHAR,
    land_area_sq_miles DOUBLE
);
```

### Legacy SQLite Schema (convert_landuse_to_db.py)

```sql
CREATE TABLE landuse_transitions (
    scenario TEXT NOT NULL,
    year INTEGER NOT NULL,
    year_range TEXT NOT NULL,
    fips TEXT NOT NULL,
    from_land_use TEXT NOT NULL,
    to_land_use TEXT NOT NULL,
    area_1000_acres REAL
);
```

### Indexes

**DuckDB Indexes (Modern):**
```sql
-- Automatically optimized columnar storage
-- Additional indexes for star schema joins
CREATE INDEX idx_fact_scenario ON fact_landuse_transitions(scenario_id);
CREATE INDEX idx_fact_geography ON fact_landuse_transitions(geography_id);
CREATE INDEX idx_fact_time ON fact_landuse_transitions(time_id);
```

**SQLite Indexes (Legacy):**
```sql
-- Performance indexes for flat table
CREATE INDEX idx_scenario ON landuse_transitions(scenario);
CREATE INDEX idx_year ON landuse_transitions(year);
CREATE INDEX idx_fips ON landuse_transitions(fips);
CREATE INDEX idx_from_to ON landuse_transitions(from_land_use, to_land_use);
```

## Error Handling

### Validation

```python
def validate_transitions(transitions, fips, year):
    """Validate data integrity."""
    # Check total area consistency
    total_from = sum(t['area'] for t in transitions if t['from'] != 'Total')
    total_to = sum(t['area'] for t in transitions if t['to'] != 'Total')
    
    if abs(total_from - total_to) > 0.01:
        raise ValueError(f"Area mismatch for {fips} in {year}")
```

### Error Recovery

```python
try:
    process_county(county_data)
except Exception as e:
    logger.error(f"Error processing {county_id}: {e}")
    failed_counties.append(county_id)
    continue
```

## Custom Converters

### Creating Custom Aggregations

```python
def create_custom_aggregation(db_path, aggregation_map):
    """Create custom land use aggregations.
    
    Args:
        db_path: Database file path
        aggregation_map: Dict mapping original to new categories
    """
    conn = sqlite3.connect(db_path)
    
    # Example: Urban + Infrastructure
    aggregation_map = {
        'Urban': 'Developed',
        'Infrastructure': 'Developed',
        'Forest': 'Natural',
        'Range': 'Natural'
    }
```

### Adding Calculated Fields

```python
def add_calculated_fields(db_path):
    """Add derived columns to database."""
    conn = sqlite3.connect(db_path)
    
    # Add percentage column
    conn.execute("""
        ALTER TABLE landuse_transitions 
        ADD COLUMN percent_of_county REAL
    """)
    
    # Calculate percentages
    conn.execute("""
        UPDATE landuse_transitions
        SET percent_of_county = 
            area_1000_acres / (
                SELECT SUM(area_1000_acres) 
                FROM landuse_transitions t2 
                WHERE t2.fips = landuse_transitions.fips
                  AND t2.year = landuse_transitions.year
            ) * 100
    """)
```

## Performance Optimization

### Batch Operations

```python
# Batch inserts
conn.executemany(
    "INSERT INTO landuse_transitions VALUES (?,?,?,?,?,?,?)",
    batch_data
)

# Transaction wrapping
conn.execute("BEGIN TRANSACTION")
# ... bulk operations ...
conn.execute("COMMIT")
```

### Memory Management

```python
# Process in chunks
CHUNK_SIZE = 50000

for i in range(0, len(data), CHUNK_SIZE):
    chunk = data[i:i + CHUNK_SIZE]
    process_chunk(chunk)
    
    # Explicit garbage collection if needed
    if i % (CHUNK_SIZE * 10) == 0:
        import gc
        gc.collect()
```

## Usage Examples

### Modern DuckDB Conversion (RECOMMENDED)

```bash
# Convert JSON to DuckDB with star schema
uv run python scripts/converters/convert_to_duckdb.py

# Output
🚀 Using bulk COPY loading method
📊 Processing county_landuse_projections_RPA.json...
✅ Created 5,400,000+ transition records in star schema
🗄️ Database saved to: data/processed/landuse_analytics.duckdb (1.2GB)
```

### Legacy SQLite Pipeline

```bash
# Legacy complete processing pipeline
# 1. Basic conversion
uv run python scripts/converters/convert_landuse_to_db.py

# 2. Add agricultural aggregation
uv run python scripts/converters/convert_landuse_with_agriculture.py

# 3. Add filtered views
uv run python scripts/converters/add_change_views.py
```

### Performance Comparison

| Method | Time | Output Size | Query Performance |
|--------|------|-------------|------------------|
| DuckDB (Modern) | 2-5 minutes | 1.2GB | Excellent (columnar) |
| SQLite (Legacy) | 15-30 minutes | 800MB | Good (row-based) |

### Custom Processing

**Modern DuckDB Approach:**
```python
from landuse.converters.base_converter import LanduseDataConverter

# Custom processing with DuckDB
def process_custom_scenario(json_data, scenario_name):
    """Process only specific scenario with DuckDB."""
    converter = LanduseDataConverter(
        input_file="data.json", 
        output_file="custom.duckdb"
    )
    
    # Process with filtering
    converter.process_scenarios(filter_scenarios=[scenario_name])
    return converter
```

**Legacy SQLite Approach:**
```python
from scripts.converters.convert_landuse_to_db import process_matrix_data

# Legacy custom processing
def process_custom_scenario(json_data, scenario_name):
    """Process only specific scenario."""
    transitions = []
    
    for county in json_data:
        if scenario_name in county['scenarios']:
            scenario_data = county['scenarios'][scenario_name]
            # Process this scenario
            
    return transitions
```

## Migration Guide

### From SQLite to DuckDB

To migrate from legacy SQLite to modern DuckDB:

1. **Run Modern Converter**: Use `convert_to_duckdb.py` instead of legacy converters
2. **Update Agent Configuration**: Point to new DuckDB file in config
3. **Benefit from Performance**: Enjoy 5-10x faster queries with star schema
4. **Use Enhanced Features**: Access new analytical views and geographic data

## Recommendation

**For new projects**: Use `convert_to_duckdb.py` for modern star schema design and optimal performance.

**For existing projects**: Consider migrating to DuckDB for better analytics performance.

## Next Steps

- See [Data Processing](../data/processing.md) for detailed pipeline
- Check [DuckDB Schema](../data/duckdb-schema.md) for modern table structure
- Review [Agent API](agent.md) for querying converted data
- See [Performance Guide](../performance/duckdb-copy-optimization.md) for optimization details