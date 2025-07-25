# Converters API Reference

Documentation for the data conversion scripts that transform raw JSON data into queryable SQLite databases.

## Overview

The converters module contains scripts for processing land use projection data:

```
scripts/converters/
├── convert_json_to_parquet.py
├── convert_landuse_to_db.py
├── convert_landuse_transitions.py
├── convert_landuse_with_agriculture.py
├── convert_landuse_nested.py
└── add_change_views.py
```

## Core Converters

### convert_landuse_to_db.py

Converts raw JSON land use projections to SQLite database format.

```python
# Basic usage
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
- Creates `landuse_transitions.db`
- Table: `landuse_transitions`
- ~1.2 million transition records

### convert_landuse_with_agriculture.py

Enhanced converter that includes agricultural aggregation views.

```python
# Usage with agricultural aggregation
uv run python scripts/converters/convert_landuse_with_agriculture.py
```

**Features:**
- Creates base transition table
- Adds agricultural aggregation (Crop + Pasture)
- Creates filtered views (changes only)
- Adds performance indexes

**Output Tables:**
1. `landuse_transitions` - All transitions
2. `landuse_transitions_ag` - With agricultural aggregation
3. `landuse_changes_only` - Excluding same-to-same
4. `landuse_changes_only_ag` - Changes with ag aggregation

### add_change_views.py

Adds filtered views to existing database.

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

### Streaming JSON Processing

For large JSON files, use streaming:

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

### Main Table

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

```sql
-- Performance indexes
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

### Basic Conversion

```bash
# Convert JSON to database
uv run python scripts/converters/convert_landuse_to_db.py

# Output
Processing county_landuse_projections_RPA.json...
Created 1,234,567 transition records
Database saved to: landuse_transitions.db
```

### Full Pipeline

```bash
# Complete processing pipeline
# 1. Basic conversion
uv run python scripts/converters/convert_landuse_to_db.py

# 2. Add agricultural aggregation
uv run python scripts/converters/convert_landuse_with_agriculture.py

# 3. Add filtered views
uv run python scripts/converters/add_change_views.py
```

### Custom Processing

```python
from scripts.converters.convert_landuse_to_db import process_matrix_data

# Custom processing example
def process_custom_scenario(json_data, scenario_name):
    """Process only specific scenario."""
    transitions = []
    
    for county in json_data:
        if scenario_name in county['scenarios']:
            scenario_data = county['scenarios'][scenario_name]
            # Process this scenario
            
    return transitions
```

## Next Steps

- See [Data Processing](../data/processing.md) for detailed pipeline
- Check [Database Schema](../data/schema.md) for table structure
- Review [Agent API](agent.md) for querying converted data