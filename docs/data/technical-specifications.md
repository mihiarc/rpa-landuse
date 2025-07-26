# Technical Specifications

## Database Technical Overview

The RPA Land Use Analytics database is implemented using **DuckDB 0.11.0+** with optimized configuration for analytical workloads and large-scale time-series data processing.

## System Requirements

### Minimum Requirements
- **Storage**: 500 MB available disk space
- **Memory**: 1 GB RAM  
- **CPU**: Single core (any modern processor)
- **OS**: Windows 10+, macOS 10.14+, Linux (any recent distribution)

### Recommended Requirements  
- **Storage**: 2 GB available disk space (for working files and indexes)
- **Memory**: 4 GB+ RAM for complex analytical queries
- **CPU**: Multi-core processor for parallel query execution
- **OS**: 64-bit operating system

### Production Environment
- **Storage**: SSD recommended for optimal query performance
- **Memory**: 8-16 GB RAM for concurrent user access
- **CPU**: 4+ cores for optimal DuckDB parallel processing
- **Network**: High-bandwidth connection for web dashboard access

---

## Database Configuration

### File Specifications

| Property | Value |
|----------|-------|
| **File Path** | `data/processed/landuse_analytics.duckdb` |
| **File Size** | 372 MB (390,070,272 bytes) |
| **Database Format** | DuckDB v0.11.0+ |
| **Encoding** | UTF-8 |
| **Compression** | Native DuckDB columnar compression |
| **Block Size** | 262,144 bytes (256 KB) |

### Storage Utilization

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total Blocks** | 1,487 | 100% |
| **Used Blocks** | 1,472 | 98.99% |
| **Free Blocks** | 15 | 1.01% |
| **WAL Size** | 0 bytes | - |
| **Storage Efficiency** | Excellent | 98.99% |

### Memory Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Working Memory** | 512.0 KiB | Query execution buffer |
| **Memory Limit** | 12.7 GiB | Maximum memory usage |
| **Parallel Threads** | Auto-detected | Concurrent query processing |
| **Enable Optimizer** | TRUE | Query plan optimization |

---

## Performance Characteristics

### Query Performance Metrics

| Query Type | Typical Response Time | Complexity |
|------------|----------------------|------------|
| **Simple Lookups** | < 1ms | Single table, indexed columns |
| **Star Schema Joins** | 10-100ms | Multi-table analytical queries |
| **Large Aggregations** | 100ms-1s | Full table scans with grouping |
| **Cross-Scenario Analysis** | 1-5s | Multiple scenario comparisons |
| **Complex Analytics** | 5-30s | Advanced statistical computations |

### Throughput Characteristics

| Metric | Value |
|--------|-------|
| **Records Scanned/sec** | 1M+ records | 
| **Concurrent Queries** | 10-50 (read-only) |
| **Data Transfer Rate** | 100+ MB/sec |
| **Index Lookup Speed** | 10,000+ lookups/sec |

### Scalability Limits

| Dimension | Current | Maximum Supported |
|-----------|---------|-------------------|
| **Total Records** | 5.7M | 100M+ |
| **Concurrent Users** | 10-20 | 100+ |
| **Query Complexity** | High | Very High |
| **Database Size** | 372 MB | 100+ GB |

---

## Index Strategy and Performance

### Primary Indexes

| Index Name | Table | Columns | Type | Purpose |
|------------|-------|---------|------|---------|
| `pk_scenario` | dim_scenario | scenario_id | Primary Key | Scenario lookups |
| `pk_geography` | dim_geography | geography_id | Primary Key | Geographic lookups |
| `pk_time` | dim_time | time_id | Primary Key | Time period lookups |
| `pk_landuse` | dim_landuse | landuse_id | Primary Key | Land use lookups |
| `pk_socioeconomic` | dim_socioeconomic | socioeconomic_id | Primary Key | SSP lookups |
| `pk_indicators` | dim_indicators | indicator_id | Primary Key | Indicator lookups |

### Secondary Indexes

| Index Name | Table | Columns | Selectivity | Usage Pattern |
|------------|-------|---------|-------------|---------------|
| `idx_geography_fips` | dim_geography | fips_code | High | County identification |
| `idx_geography_state` | dim_geography | state_name | Medium | State-level filtering |
| `idx_landuse_code` | dim_landuse | landuse_code | High | Land use filtering |
| `idx_scenario_name` | dim_scenario | scenario_name | High | Scenario identification |
| `idx_time_range` | dim_time | year_range | High | Time period filtering |

### Composite Indexes

| Index Name | Table | Columns | Cardinality | Query Patterns |
|------------|-------|---------|-------------|----------------|
| `idx_fact_composite` | fact_landuse_transitions | scenario_id, time_id, geography_id | High | Multi-dimensional queries |
| `idx_fact_landuse` | fact_landuse_transitions | from_landuse_id, to_landuse_id | Medium | Transition analysis |
| `idx_fact_acres` | fact_landuse_transitions | acres | Low | Area-based filtering |
| `idx_fact_transition_type` | fact_landuse_transitions | transition_type | Very Low | Change vs. same filtering |
| `idx_socioeconomic_composite` | fact_socioeconomic_projections | geography_id, socioeconomic_id, indicator_id, year | High | Demographic queries |

### Index Performance Characteristics

| Index Type | Avg Lookup Time | Memory Usage | Maintenance Cost |
|------------|-----------------|---------------|------------------|
| **Primary Key** | < 0.1ms | Low | Minimal |
| **Secondary** | < 1ms | Low-Medium | Low |
| **Composite** | 1-5ms | Medium | Medium |
| **Covering** | 0.5-2ms | Medium-High | Medium-High |

---

## Query Optimization

### DuckDB Optimizer Features

| Feature | Status | Benefit |
|---------|--------|---------|
| **Cost-Based Optimization** | Enabled | Optimal join order selection |
| **Predicate Pushdown** | Enabled | Early filtering |
| **Projection Pushdown** | Enabled | Reduced data transfer |
| **Join Elimination** | Enabled | Simplified query plans |
| **Constant Folding** | Enabled | Compile-time optimization |
| **Statistics-Based** | Enabled | Accurate cardinality estimates |

### Recommended Query Patterns

#### Optimal Pattern
```sql
-- Filter on indexed columns first, then join
SELECT g.state_name, lu.landuse_name, SUM(f.acres)
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse lu ON f.to_landuse_id = lu.landuse_id
WHERE 
    f.scenario_id = 1               -- Indexed filter
    AND f.time_id IN (4, 5, 6)      -- Indexed filter
    AND g.region = 'West'           -- Secondary filter
    AND f.transition_type = 'change' -- Final filter
GROUP BY g.state_name, lu.landuse_name;
```

#### Anti-Patterns to Avoid
```sql
-- Avoid: Cartesian products
SELECT * FROM fact_landuse_transitions f, dim_geography g;

-- Avoid: Non-indexed function calls in WHERE
SELECT * FROM fact_landuse_transitions 
WHERE UPPER(transition_type) = 'CHANGE';

-- Avoid: Leading wildcards
SELECT * FROM dim_geography WHERE county_name LIKE '%County';
```

### Query Execution Plans

DuckDB provides detailed execution plans for optimization:

```sql
-- Analyze query performance
EXPLAIN ANALYZE 
SELECT g.state_name, SUM(f.acres)
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
WHERE f.scenario_id = 1
GROUP BY g.state_name;
```

---

## Backup and Recovery

### Backup Strategy

| Backup Type | Frequency | Retention | Method |
|-------------|-----------|-----------|---------|
| **Full Database** | Daily | 30 days | File copy |
| **Incremental** | Not applicable | - | Static data |
| **Point-in-Time** | Not applicable | - | Read-only database |

### Backup Implementation

```bash
# Simple file-based backup
cp data/processed/landuse_analytics.duckdb \
   backups/landuse_analytics_$(date +%Y%m%d).duckdb

# Compressed backup
tar -czf backups/landuse_analytics_$(date +%Y%m%d).tar.gz \
    data/processed/landuse_analytics.duckdb

# Cloud backup (example)
aws s3 cp data/processed/landuse_analytics.duckdb \
    s3://bucket/backups/landuse_analytics_$(date +%Y%m%d).duckdb
```

### Recovery Procedures

```bash
# Restore from backup
cp backups/landuse_analytics_20250126.duckdb \
   data/processed/landuse_analytics.duckdb

# Verify database integrity
duckdb data/processed/landuse_analytics.duckdb \
    "SELECT COUNT(*) FROM fact_landuse_transitions;"

# Test basic functionality
duckdb data/processed/landuse_analytics.duckdb \
    "SELECT * FROM v_scenarios_combined LIMIT 1;"
```

---

## Security Configuration

### Access Control

| Level | Configuration | Implementation |
|-------|---------------|----------------|
| **File System** | Read-only access | OS permissions |
| **Database** | No authentication | Single-user/read-only |
| **Application** | Environment variables | API key management |
| **Network** | Local access only | No remote connections |

### Data Protection

| Protection Type | Implementation | Purpose |
|----------------|----------------|---------|
| **Encryption at Rest** | File system level | Sensitive data protection |
| **Encryption in Transit** | HTTPS for web interface | Network security |
| **Data Masking** | Not required | Public/research data |
| **Audit Logging** | Application level | Usage tracking |

### Security Best Practices

```bash
# Set appropriate file permissions
chmod 644 data/processed/landuse_analytics.duckdb

# Use environment variables for configuration
export DUCKDB_DATABASE_PATH="data/processed/landuse_analytics.duckdb"
export DUCKDB_READ_ONLY="true"

# Application-level access control
export ANTHROPIC_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
```

---

## Monitoring and Diagnostics

### Health Check Queries

```sql
-- Database connectivity
SELECT 'Database Connected' as status;

-- Data integrity check
SELECT 
    COUNT(*) as total_transitions,
    COUNT(DISTINCT scenario_id) as scenarios,
    COUNT(DISTINCT geography_id) as counties,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record
FROM fact_landuse_transitions;

-- Performance baseline
SELECT 
    table_name,
    estimated_size as size_bytes,
    column_count,
    has_stats
FROM duckdb_tables();
```

### Performance Monitoring

```sql
-- Query performance profiling
PRAGMA enable_profiling;
-- Run query here
PRAGMA disable_profiling;

-- Table statistics
SELECT table_name, 
       estimated_size, 
       has_stats 
FROM duckdb_tables() 
WHERE schema_name = 'main';

-- Index usage statistics
PRAGMA show_tables;
```

### System Diagnostics

```sql
-- Memory usage
PRAGMA memory_limit;
PRAGMA threads;

-- Database configuration
PRAGMA table_info('fact_landuse_transitions');

-- Storage statistics
PRAGMA database_size;
```

---

## Integration Specifications

### Python Integration

```python
import duckdb
import pandas as pd

# Connection patterns
conn = duckdb.connect('data/processed/landuse_analytics.duckdb', read_only=True)

# Query execution
df = conn.execute("""
    SELECT * FROM v_scenarios_combined
""").fetchdf()

# Pandas integration
result = conn.execute("SELECT * FROM fact_landuse_transitions LIMIT 1000")
df = result.df()

# Resource management
conn.close()
```

### Streamlit Integration

```python
import streamlit as st
from src.landuse.connections.duckdb_connection import DuckDBConnection

# Streamlit connection pattern
@st.cache_data
def get_data(query: str):
    conn = st.connection("duckdb", type=DuckDBConnection)
    return conn.query(query, ttl=3600)

# Usage
data = get_data("SELECT * FROM v_scenarios_combined")
```

### API Integration

```python
from src.landuse.tools.common_tools import execute_landuse_query

# Agent tool integration
result = execute_landuse_query(
    query="SELECT * FROM dim_scenario",
    params={}
)
```

---

## Deployment Configurations

### Development Environment

```yaml
# Development configuration
database:
  path: "data/processed/landuse_analytics.duckdb"
  read_only: true
  memory_limit: "2GB"
  threads: 2

logging:
  level: "DEBUG"
  performance: true
```

### Production Environment

```yaml
# Production configuration
database:
  path: "/data/landuse_analytics.duckdb"
  read_only: true
  memory_limit: "8GB"
  threads: 4

caching:
  enabled: true
  ttl: 3600

monitoring:
  enabled: true
  health_check_interval: 300
```

### Cloud Deployment

```yaml
# Cloud configuration
database:
  path: "s3://bucket/landuse_analytics.duckdb"
  read_only: true
  memory_limit: "16GB"
  threads: 8

scaling:
  auto_scaling: true
  min_instances: 2
  max_instances: 10
```

---

## Performance Tuning

### Memory Optimization

```sql
-- Set memory limit
PRAGMA memory_limit='4GB';

-- Enable memory monitoring
PRAGMA enable_profiling='memory';

-- Optimize for analytical workloads
PRAGMA enable_object_cache;
```

### Query Optimization

```sql
-- Update table statistics
ANALYZE fact_landuse_transitions;
ANALYZE dim_geography;

-- Verify index usage
EXPLAIN SELECT * FROM fact_landuse_transitions 
WHERE scenario_id = 1 AND geography_id = 100;
```

### Storage Optimization

```bash
# Vacuum database (reclaim space)
duckdb landuse_analytics.duckdb "VACUUM;"

# Checkpoint WAL
duckdb landuse_analytics.duckdb "CHECKPOINT;"
```

---

## Version Compatibility

### DuckDB Version Requirements

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| **DuckDB Core** | 0.9.0 | 0.11.0+ | Core functionality |
| **Python Client** | 0.9.0 | 0.11.0+ | Python integration |
| **CLI Tools** | 0.9.0 | 0.11.0+ | Command line access |

### Application Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **pandas** | 1.5.0+ | Data manipulation |
| **streamlit** | 1.40.0+ | Web interface |
| **plotly** | 5.0.0+ | Visualizations |
| **geopandas** | 0.14.0+ | Spatial analysis |

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **File Lock Error** | "Database is locked" | Close all connections |
| **Memory Error** | "Out of memory" | Increase memory limit |
| **Slow Queries** | High response time | Check index usage |
| **Connection Failed** | Cannot connect | Verify file path |

### Diagnostic Commands

```bash
# Test database connectivity
duckdb data/processed/landuse_analytics.duckdb "SELECT 1;"

# Check database integrity
duckdb data/processed/landuse_analytics.duckdb "PRAGMA integrity_check;"

# Verify table counts
duckdb data/processed/landuse_analytics.duckdb \
    "SELECT table_name, estimated_size FROM duckdb_tables();"

# Performance test
time duckdb data/processed/landuse_analytics.duckdb \
    "SELECT COUNT(*) FROM fact_landuse_transitions;"
```

---

## Next Steps

- **Query Optimization**: See [DuckDB Optimization](../performance/duckdb-copy-optimization.md)
- **Application Integration**: See [API Reference](../api/tools.md)
- **Performance Guide**: See [Streamlit Fragments](../performance/streamlit-fragments.md)
- **Monitoring Setup**: See [Development Guide](../development/architecture.md)