# Schema Management System

Production-ready schema management for the RPA Land Use Analytics DuckDB database.

## Overview

This directory contains the complete schema management system including:
- **Schema Definitions**: Declarative YAML files defining database structure
- **Migrations**: SQL migration scripts for schema evolution
- **Generated Code**: Auto-generated Pydantic models and documentation
- **Checkpoints**: Schema state snapshots for recovery

## Directory Structure

```
schema/
├── definitions/           # Schema definitions in YAML
│   ├── v2.2.0.yaml       # Current production schema
│   └── v2.3.0.yaml       # Next version (example)
│
├── migrations/           # Migration SQL scripts
│   ├── v2.2.0_to_v2.3.0_example.sql
│   └── checksums.json   # Migration integrity checksums
│
├── generated/            # Auto-generated files (git-ignored)
│   ├── models.py        # Pydantic models
│   ├── schema.sql       # Complete DDL
│   └── docs.md          # Schema documentation
│
├── checkpoints/         # Schema state snapshots
│   └── checkpoint_*.json
│
└── README.md            # This file
```

## Quick Start

### Check Current Status

```bash
# Show current schema version and status
uv run python -m landuse.schema.cli status

# Validate database against schema definition
uv run python -m landuse.schema.cli validate
```

### Run Migrations

```bash
# Migrate to latest version
uv run python -m landuse.schema.cli migrate

# Migrate to specific version
uv run python -m landuse.schema.cli migrate --version 2.3.0

# Dry run to preview changes
uv run python -m landuse.schema.cli migrate --dry-run
```

### Generate Code & Documentation

```bash
# Generate Pydantic models
uv run python -m landuse.schema.cli generate-models

# Export schema documentation
uv run python -m landuse.schema.cli export --format markdown
uv run python -m landuse.schema.cli export --format sql > schema.sql
uv run python -m landuse.schema.cli export --format mermaid  # ER diagram
```

### Create Checkpoint

```bash
# Create recovery checkpoint
uv run python -m landuse.schema.cli checkpoint
```

## Schema Definition Format

Schema definitions use YAML with embedded SQL DDL:

```yaml
version: 2.3.0
description: "Add new features"
author: "developer"
backward_compatible: true

tables:
  table_name:
    description: "Table description"
    ddl: |
      CREATE TABLE IF NOT EXISTS table_name (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    indexes:
      - CREATE INDEX idx_name ON table_name(name)

views:
  v_summary:
    description: "Summary view"
    ddl: |
      CREATE VIEW v_summary AS
      SELECT * FROM table_name
```

## Migration Workflow

### 1. Create New Schema Version

Copy and modify the latest schema definition:

```bash
cp definitions/v2.2.0.yaml definitions/v2.3.0.yaml
# Edit v2.3.0.yaml with your changes
```

### 2. Create Migration Script

```bash
# Create migration template
uv run python -m landuse.schema.cli create-migration 2.2.0 2.3.0

# Edit the generated migration file
vim migrations/v2.2.0_to_v2.3.0.sql
```

### 3. Test Migration

```bash
# Test on development database first
uv run python -m landuse.schema.cli migrate --dry-run

# Validate after migration
uv run python -m landuse.schema.cli validate
```

### 4. Apply to Production

```bash
# Create checkpoint before migration
uv run python -m landuse.schema.cli checkpoint

# Apply migration
uv run python -m landuse.schema.cli migrate --version 2.3.0
```

## Migration Script Format

Migration scripts support rollback and validation:

```sql
-- Migration: v2.2.0 to v2.3.0
-- Author: developer
-- Date: 2025-01-15

-- Pre-migration checks
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_version WHERE version_number = '2.2.0') THEN
    RAISE EXCEPTION 'Current version must be 2.2.0';
  END IF;
END $$;

BEGIN TRANSACTION;

-- MIGRATION STEP: Add new table
CREATE TABLE new_table (
  id INTEGER PRIMARY KEY
);
-- ROLLBACK: DROP TABLE IF EXISTS new_table;
-- VALIDATE: SELECT 1 FROM information_schema.tables WHERE table_name = 'new_table';

-- Update version
INSERT INTO schema_version (version_number, description, applied_by)
VALUES ('2.3.0', 'Add new table', 'migration_system');

COMMIT;
```

## Python API

Use the schema manager programmatically:

```python
from pathlib import Path
from landuse.schema import SchemaManager

# Initialize manager
manager = SchemaManager(
    db_path=Path("data/landuse.duckdb"),
    schema_dir=Path("schema")
)

# Get current version
version = manager.get_current_version()

# Validate schema
result = manager.validate_schema()
if not result.is_valid:
    for issue in result.issues:
        print(f"{issue.level}: {issue.message}")

# Run migration
migration_result = manager.migrate(target_version="2.3.0")

# Generate models
models_path = manager.generate_models()

# Export documentation
markdown_doc = manager.export_schema("markdown")
```

## Integration with Application

The schema manager integrates with existing components:

### DatabaseManager Integration

```python
from landuse.agents.database_manager import DatabaseManager

# DatabaseManager now uses cached schema
db_manager = DatabaseManager(config)
schema = db_manager.get_schema()  # Uses SchemaManager internally
```

### Converter Integration

```python
from scripts.converters.convert_to_duckdb import LanduseConverter

# Converter uses schema definitions
converter = LanduseConverter(schema_version="2.2.0")
converter.create_schema()  # Uses YAML definition
```

## Best Practices

### Schema Changes

1. **Always create a checkpoint** before migrations
2. **Test migrations** on development database first
3. **Use semantic versioning** (MAJOR.MINOR.PATCH)
4. **Document breaking changes** in migration description
5. **Include rollback steps** for risky operations

### Naming Conventions

- **Tables**: `lowercase_with_underscores`
- **Views**: `v_` prefix (e.g., `v_summary`)
- **Indexes**: `idx_table_column` format
- **Versions**: Semantic versioning `X.Y.Z`

### Performance

- **Index foreign keys** for join performance
- **Consider partitioning** for large fact tables
- **Use materialized views** for complex aggregations
- **Monitor query performance** after migrations

## Troubleshooting

### Migration Failures

If a migration fails:

1. Check error messages in console output
2. Review migration SQL for syntax errors
3. Verify pre-migration checks are correct
4. Use checkpoint to restore if needed

### Schema Drift

If database doesn't match schema:

1. Run validation to identify differences
2. Create migration to reconcile
3. Or sync from checkpoint if appropriate

### Version Conflicts

If version mismatch occurs:

1. Check current version: `schema status`
2. Detect actual version from structure
3. Apply appropriate migrations

## Security Considerations

- **Validate all SQL** before execution
- **Use transactions** for atomicity
- **Check for data loss** operations
- **Require confirmation** for destructive changes
- **Maintain audit trail** in schema_version table

## Future Enhancements

Planned improvements:

- [ ] Automatic migration generation from schema diff
- [ ] Backward migration support
- [ ] Schema comparison tools
- [ ] Performance impact analysis
- [ ] Integration with CI/CD pipelines
- [ ] Cloud backup integration
- [ ] Schema documentation website

## Support

For issues or questions:

1. Check this documentation
2. Review example migrations
3. Run validation for diagnostics
4. Create GitHub issue with details