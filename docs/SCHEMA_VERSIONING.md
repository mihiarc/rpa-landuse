# Schema Versioning System

## Overview

The RPA Land Use database uses a schema versioning system to track database evolution and ensure compatibility between application and database versions.

## Current Schema Versions

| Version | Description | Key Changes |
|---------|-------------|-------------|
| 1.0.0 | Original schema | 20 individual GCM scenarios |
| 2.0.0 | Combined scenarios | Aggregated into 5 RCP-SSP combinations with OVERALL default |
| 2.1.0 | Statistical fields | Added std_dev, min, max fields for uncertainty tracking |
| 2.2.0 | Versioning system | Added schema_version table and tracking |

## How It Works

### Automatic Version Detection

When connecting to a database, the system:
1. Checks for existing version in `schema_version` table
2. If no version found, attempts to detect from schema structure
3. Logs version and checks compatibility
4. Warns if incompatible versions detected

### Version Compatibility

The system maintains a compatibility matrix:
- **2.2.0**: Compatible with 2.0.0, 2.1.0, 2.2.0
- **2.1.0**: Compatible with 2.0.0, 2.1.0
- **2.0.0**: Compatible with 2.0.0 only
- **1.0.0**: Compatible with 1.0.0 only

## Usage

### Check Database Version

```python
from landuse.agents.database_manager import DatabaseManager

with DatabaseManager() as db:
    version = db.get_database_version()
    print(f"Database version: {version}")

    history = db.get_version_history()
    for v in history:
        print(f"  {v[0]}: {v[1]} (applied {v[2]})")
```

### Apply Version During Conversion

The converter automatically applies version 2.2.0 when creating new databases:

```bash
uv run python scripts/converters/convert_to_duckdb.py
```

### Manual Version Application

```python
import duckdb
from landuse.database.schema_version import SchemaVersionManager

conn = duckdb.connect('database.duckdb')
manager = SchemaVersionManager(conn)
manager.apply_version('2.2.0', applied_by='manual_update')
```

## Troubleshooting

### Version Mismatch Warning

**Symptom**: Warning about incompatible versions on connection

**Solution**:
- Check database version with `get_database_version()`
- Review breaking changes between versions
- Consider upgrading database or application

### Unknown Version

**Symptom**: "Database schema version unknown" warning

**Solution**:
- Let system auto-detect version from schema
- Or manually apply appropriate version
- New databases get versioned automatically

### Read-Only Database

**Symptom**: Cannot create version table in read-only mode

**Solution**:
- Normal for read-only connections
- Version checking still works via detection
- Write operations require write access

## Breaking Changes

### 1.0.0 → 2.0.0
- Schema restructured for combined scenarios
- dim_scenario table modified
- New OVERALL scenario added

### 2.0.0 → 2.1.0
- Statistical fields added to fact table
- No breaking changes for existing queries

### 2.1.0 → 2.2.0
- Schema versioning table added
- No breaking changes for existing functionality

## Future Migration Support

The current system provides version tracking. Future enhancements planned:
- Migration script execution
- Automated schema upgrades
- Rollback capabilities
- Migration validation

## Best Practices

1. **Always version new databases**: Converters apply version automatically
2. **Check compatibility**: Review warnings about version mismatches
3. **Document changes**: Update version history when schema changes
4. **Test migrations**: Verify compatibility before production deployment

## API Reference

### SchemaVersion Class

Static class providing version constants and compatibility checking:
- `CURRENT_VERSION`: Current application version
- `SCHEMA_VERSIONS`: Version history dictionary
- `is_compatible(db_version, app_version)`: Check compatibility
- `get_breaking_changes(from_version, to_version)`: List breaking changes

### SchemaVersionManager Class

Manages version operations on database:
- `apply_version(version, applied_by)`: Apply version to database
- `get_current_version()`: Get current database version
- `get_version_history()`: Get all applied versions
- `check_compatibility(required_version)`: Check if compatible
- `detect_schema_version()`: Auto-detect from schema structure