# Tools API Reference

Detailed documentation of all tools available to the LangChain Data Engineering Agent.

## Overview

The agent uses a collection of specialized tools for file operations, data analysis, and database queries. Each tool is designed to handle specific tasks while maintaining consistency and error handling.

## Tool Categories

### 📁 File Management Tools

Tools inherited from LangChain's `FileManagementToolkit`:

| Tool | Function | Parameters | Example |
|------|----------|------------|---------|
| `list_directory` | List files in directory | `dir_path: str` | "List files in data/" |
| `read_file` | Read file contents | `file_path: str` | "Read config.json" |
| `write_file` | Write to file | `file_path: str, text: str` | "Save results to output.txt" |
| `copy_file` | Copy file | `source: str, destination: str` | "Copy data.csv to backup/" |
| `move_file` | Move/rename file | `source: str, destination: str` | "Move temp.csv to processed/" |
| `delete_file` | Delete file | `file_path: str` | "Delete temporary.txt" |

### 📊 Data Reading Tools

Specialized tools for reading different data formats:

#### read_csv

```python
def _read_csv(self, file_path: str) -> str
```

**Purpose:** Read CSV files and return basic information

**Returns:**
- Shape, columns, data types
- Missing values summary
- Memory usage
- First 5 rows
- Basic statistics

**Example:**
```python
agent.run("Read the sample_data.csv file")
```

#### read_parquet

```python
def _read_parquet(self, file_path: str) -> str
```

**Purpose:** Read Parquet files efficiently

**Features:**
- Columnar format support
- Compression handling
- Metadata extraction

#### read_json

```python
def _read_json(self, file_path: str) -> str
```

**Purpose:** Read JSON files with large file support

**Special Handling:**
- Files > MAX_FILE_SIZE_MB use streaming
- Automatic structure detection
- Sample extraction for large files

### 🔍 Data Analysis Tools

#### analyze_dataframe

```python
def _analyze_dataframe(self, file_path: str) -> str
```

**Purpose:** Perform detailed analysis on any supported file format

**Analysis Includes:**
- Shape and memory usage
- Duplicate row detection
- Column-wise analysis:
  - Data types
  - Null counts and percentages
  - Unique values
  - Cardinality
  - Numeric statistics

**Output Format:**
```json
{
  "shape": [rows, cols],
  "memory_usage_mb": 12.5,
  "duplicate_rows": 0,
  "column_analysis": {
    "column_name": {
      "dtype": "float64",
      "null_count": 5,
      "null_percentage": 0.5,
      "unique_values": 100,
      "mean": 50.2,
      "std": 10.5
    }
  }
}
```

#### query_data

```python
def _query_data(self, params: Union[Dict[str, str], str]) -> str
```

**Purpose:** Execute SQL queries on any file format using DuckDB

**Parameters:**
```python
{
  "file_path": "data.csv",
  "query": "SELECT * FROM data WHERE value > 100"
}
```

**Features:**
- Automatic table creation
- SQL syntax support
- Cross-format queries
- Spatial support for GeoParquet

### 🔄 Data Transformation Tools

#### transform_data

```python
def _transform_data(self, params: Union[Dict[str, str], str]) -> str
```

**Purpose:** Convert between data formats

**Parameters:**
```python
{
  "input_path": "data.json",
  "output_path": "data.parquet",
  "output_format": "parquet",
  "compression": "snappy"  # optional
}
```

**Supported Formats:**
- CSV ↔ Parquet
- JSON ↔ Parquet
- Excel ↔ CSV
- Any format to GeoParquet (if geometry present)

#### optimize_storage

```python
def _optimize_storage(self, file_path: str) -> str
```

**Purpose:** Analyze data and suggest optimal storage format

**Analysis Factors:**
- Current format and size
- Data characteristics
- Column types distribution
- Compression potential

**Recommendations Include:**
- Suggested format
- Reason for recommendation
- Estimated size reduction

### 🗄️ Database Tools

#### list_database_tables

```python
def _list_database_tables(self, db_path: str) -> str
```

**Purpose:** List all tables in a SQLite database

**Output:**
```
Database: landuse.db
Tables:
  • landuse_transitions: 1,234,567 rows
  • landuse_changes: 543,210 rows
```

#### describe_database_table

```python
def _describe_database_table(self, params: Dict[str, str]) -> str
```

**Purpose:** Get detailed table information

**Parameters:**
```python
{
  "db_path": "database.db",
  "table_name": "landuse_transitions"
}
```

**Returns:**
- Row count
- Column schema
- Data types
- Constraints
- Indexes
- Sample data

#### query_database

```python
def _query_database(self, params: Dict[str, str]) -> str
```

**Purpose:** Execute SQL queries on SQLite databases

**Parameters:**
```python
{
  "db_path": "database.db",
  "query": "SELECT COUNT(*) FROM table",
  "limit": 1000  # optional, default 1000
}
```

**Features:**
- Automatic LIMIT addition
- Result formatting
- Error handling
- Performance optimization

#### export_database_table

```python
def _export_database_table(self, params: Dict[str, str]) -> str
```

**Purpose:** Export database tables to files

**Parameters:**
```python
{
  "db_path": "database.db",
  "table_name": "results",
  "output_path": "export.csv",
  "output_format": "csv",  # csv, json, parquet
  "where_clause": "year > 2020",  # optional
  "limit": 10000  # optional
}
```

### 📈 Visualization Tools

#### data_visualization

```python
def _create_visualization(self, params: Dict[str, str]) -> str
```

**Purpose:** Create data visualizations

**Parameters:**
```python
{
  "file_path": "data.csv",
  "plot_type": "scatter",  # scatter, line, histogram, correlation
  "x": "column1",  # optional
  "y": "column2"   # optional
}
```

**Plot Types:**
- Scatter plots
- Line charts
- Histograms
- Correlation heatmaps

**Output:** Saves plot as PNG file

### 🚀 Advanced Tools

#### json_to_database

```python
def _json_to_database(self, params: Dict[str, Any]) -> str
```

**Purpose:** Convert large JSON files to SQLite efficiently

**Parameters:**
```python
{
  "json_path": "large_data.json",
  "db_path": "output.db",
  "table_name": "data",
  "chunk_size": 10000
}
```

**Features:**
- Streaming processing
- Automatic schema detection
- Progress tracking
- Index creation
- Batch insertion

#### database_statistics

```python
def _database_statistics(self, db_path: str) -> str
```

**Purpose:** Get comprehensive database statistics

**Returns:**
- File size
- Table count
- Row counts per table
- Index information
- Schema version

## Tool Integration

### Creating Custom Tools

```python
from langchain_core.tools import Tool

def create_custom_tool():
    return Tool(
        name="custom_analysis",
        func=custom_analysis_function,
        description="Perform custom analysis on data"
    )
```

### Tool Parameters

Tools accept parameters in multiple formats:

1. **String parameters:**
```python
agent.run("Read file.csv")
```

2. **Dictionary parameters:**
```python
params = {"file_path": "data.csv", "query": "SELECT * FROM data"}
agent.run(f"Query data with parameters: {json.dumps(params)}")
```

3. **Structured parameters:**
```python
from pydantic import BaseModel

class QueryParams(BaseModel):
    file_path: str
    query: str
    limit: Optional[int] = 1000
```

## Error Handling

All tools implement consistent error handling:

```python
try:
    # Tool operation
    result = perform_operation()
    return format_success(result)
except FileNotFoundError:
    return f"Error: File not found: {file_path}"
except ValueError as e:
    return f"Error: Invalid value: {str(e)}"
except Exception as e:
    return f"Error: {str(e)}"
```

## Performance Considerations

### File Size Handling

- Files > MAX_FILE_SIZE_MB trigger special handling
- Large files use streaming/sampling
- Progress indicators for long operations

### Query Optimization

- Automatic LIMIT clauses
- Index usage
- Batch processing
- Connection pooling

### Memory Management

- Chunked processing for large datasets
- Explicit garbage collection when needed
- Streaming for JSON/CSV processing

## Usage Examples

### Basic File Analysis

```python
# Analyze a CSV file
result = agent.run("Analyze the sales_data.csv file")

# Get specific statistics
result = agent.run("Show me statistics for the revenue column in sales_data.csv")
```

### Complex Queries

```python
# Multi-step analysis
agent.run("""
1. Read the customer_data.csv file
2. Query it to find top customers by revenue
3. Export results to top_customers.parquet
""")
```

### Database Operations

```python
# Explore database
agent.run("Show all tables in analytics.db")

# Complex query
agent.run("""
Query analytics.db: 
SELECT category, SUM(sales) as total_sales 
FROM transactions 
WHERE date >= '2024-01-01' 
GROUP BY category 
ORDER BY total_sales DESC
""")
```

## Best Practices

1. **Use appropriate tools for the task**
   - File reading for exploration
   - Query tools for analysis
   - Export tools for results

2. **Handle errors gracefully**
   - Check file existence
   - Validate parameters
   - Provide helpful error messages

3. **Optimize for performance**
   - Use appropriate chunk sizes
   - Leverage indexes
   - Stream large files

4. **Maintain data integrity**
   - Validate transformations
   - Preserve data types
   - Handle nulls appropriately

## Next Steps

- See [Agent API](agent.md) for using tools programmatically
- Review [Query Examples](../queries/examples.md) for tool usage patterns
- Check [Data Processing](../data/processing.md) for data pipeline tools