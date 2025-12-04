# Schema Management Architecture Design

## Executive Summary

This document outlines a comprehensive, production-ready schema management system for the RPA Land Use Analytics DuckDB database. The design addresses current limitations while maintaining backward compatibility and follows industry best practices adapted for DuckDB's unique capabilities.

## Current State Analysis

### Problems Identified
1. **No Single Source of Truth**: Schema defined as Python code in `convert_to_duckdb.py`
2. **No Migration System**: Schema changes require full database rebuild (5.4M+ records)
3. **Runtime Schema Discovery**: Queries `information_schema` at runtime, causing performance overhead
4. **Manual Versioning**: `schema_version.py` tracks versions but lacks automation
5. **No Validation**: Cannot verify database matches expected schema
6. **Documentation Scattered**: Schema docs spread across multiple files

### Existing Components
- `convert_to_duckdb.py`: Creates tables with inline CREATE TABLE statements
- `schema_version.py`: Basic version tracking (v2.2.0)
- `database_manager.py`: Runtime schema retrieval
- `prompts.py`: Injects schema via {schema_info} placeholder

## Architecture Design

### Core Principles
1. **Declarative Schema Definition**: Schema as data, not code
2. **Forward-Only Migrations**: Support rollback through compensating migrations
3. **Type Safety**: Generate Pydantic models from schema
4. **Zero-Downtime**: Support online schema changes where possible
5. **DuckDB Optimized**: Leverage DuckDB-specific features (COPY, views, etc.)

### Schema Definition Format

We will use **YAML with SQL DDL** as our schema definition format:

**Rationale:**
- YAML for metadata and configuration (human-readable, version control friendly)
- SQL DDL for actual table definitions (DuckDB native, no translation layer)
- Combines declarative configuration with native SQL power

```yaml
# schema/definitions/v2.3.0.yaml
version: 2.3.0
description: "Add data quality metrics table"
author: "system"
created_at: "2025-01-15T10:00:00Z"
backward_compatible: true

tables:
  dim_scenario:
    description: "Climate scenario dimension table"
    ddl: |
      CREATE TABLE IF NOT EXISTS dim_scenario (
        scenario_id INTEGER PRIMARY KEY,
        scenario_name VARCHAR(100) NOT NULL,
        rcp_scenario VARCHAR(20),
        ssp_scenario VARCHAR(20),
        description TEXT,
        narrative TEXT,
        aggregation_method VARCHAR(50) DEFAULT 'mean',
        gcm_count INTEGER DEFAULT 5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    indexes:
      - CREATE INDEX idx_scenario_name ON dim_scenario(scenario_name)
    constraints:
      - UNIQUE(scenario_name)

  fact_landuse_transitions:
    description: "Main fact table for land use transitions"
    ddl: |
      CREATE TABLE IF NOT EXISTS fact_landuse_transitions (
        transition_id BIGINT PRIMARY KEY,
        scenario_id INTEGER NOT NULL,
        time_id INTEGER NOT NULL,
        geography_id INTEGER NOT NULL,
        from_landuse_id INTEGER NOT NULL,
        to_landuse_id INTEGER NOT NULL,
        acres DECIMAL(15,4) NOT NULL,
        acres_std_dev DECIMAL(15,4),
        acres_min DECIMAL(15,4),
        acres_max DECIMAL(15,4),
        transition_type VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scenario_id) REFERENCES dim_scenario(scenario_id)
      )
    indexes:
      - CREATE INDEX idx_fact_scenario ON fact_landuse_transitions(scenario_id)
      - CREATE INDEX idx_fact_composite ON fact_landuse_transitions(scenario_id, time_id, geography_id)
    partitioning:
      type: "range"
      column: "time_id"

views:
  v_default_transitions:
    description: "Default view for OVERALL scenario"
    ddl: |
      CREATE OR REPLACE VIEW v_default_transitions AS
      SELECT * FROM fact_landuse_transitions f
      JOIN dim_scenario s ON f.scenario_id = s.scenario_id
      WHERE s.scenario_name = 'OVERALL'
```

### Migration System

#### File-Based Migration Structure
```
schema/
├── definitions/           # Schema definitions
│   ├── v2.2.0.yaml       # Current schema
│   ├── v2.3.0.yaml       # Next version
│   └── latest.yaml       # Symlink to latest
├── migrations/           # Migration scripts
│   ├── v2.2.0_to_v2.3.0.sql
│   ├── v2.3.0_to_v2.2.0_rollback.sql
│   └── checksums.json   # Migration checksums
├── generated/            # Auto-generated files
│   ├── models.py        # Pydantic models
│   ├── schema.sql       # Complete DDL
│   └── docs.md          # Schema documentation
└── tests/               # Schema tests
    ├── test_migrations.py
    └── test_validation.py
```

#### Migration File Format
```sql
-- migrations/v2.2.0_to_v2.3.0.sql
-- Migration: v2.2.0 to v2.3.0
-- Author: system
-- Date: 2025-01-15
-- Description: Add data quality metrics

-- Pre-migration checks
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_version WHERE version_number = '2.2.0') THEN
    RAISE EXCEPTION 'Current version must be 2.2.0';
  END IF;
END $$;

-- Migration
BEGIN TRANSACTION;

-- Add new table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
  metric_id INTEGER PRIMARY KEY,
  table_name VARCHAR(100) NOT NULL,
  column_name VARCHAR(100),
  metric_type VARCHAR(50) NOT NULL,
  metric_value DECIMAL(15,4),
  measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add column to existing table (if supported by DuckDB)
ALTER TABLE fact_landuse_transitions
ADD COLUMN IF NOT EXISTS quality_score DECIMAL(5,2);

-- Update version
INSERT INTO schema_version (version_number, description, applied_by)
VALUES ('2.3.0', 'Add data quality metrics', 'migration_system');

COMMIT;

-- Post-migration validation
SELECT 'Migration successful' WHERE EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_name = 'data_quality_metrics'
);
```

### API Design

#### Core Classes

```python
# src/landuse/schema/manager.py
from typing import Optional, List, Dict
from pathlib import Path
import duckdb
from pydantic import BaseModel

class SchemaDefinition(BaseModel):
    """Schema definition model."""
    version: str
    description: str
    author: str
    created_at: datetime
    backward_compatible: bool
    tables: Dict[str, TableDefinition]
    views: Dict[str, ViewDefinition]

class SchemaManager:
    """Central schema management system."""

    def __init__(self, db_path: Path, schema_dir: Path):
        self.db_path = db_path
        self.schema_dir = schema_dir
        self._cache = {}

    def get_current_version(self) -> str:
        """Get current database schema version."""
        pass

    def validate_schema(self) -> ValidationResult:
        """Validate database matches expected schema."""
        pass

    def migrate(self, target_version: Optional[str] = None) -> MigrationResult:
        """Migrate database to target version."""
        pass

    def generate_models(self) -> None:
        """Generate Pydantic models from schema."""
        pass

    def export_schema(self, format: str = "sql") -> str:
        """Export schema in specified format."""
        pass

class MigrationEngine:
    """Handles schema migrations."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection

    def plan_migration(self, from_version: str, to_version: str) -> MigrationPlan:
        """Plan migration path between versions."""
        pass

    def execute_migration(self, plan: MigrationPlan) -> MigrationResult:
        """Execute migration with transaction safety."""
        pass

    def rollback(self, version: str) -> None:
        """Rollback to previous version."""
        pass

class SchemaValidator:
    """Validates schema consistency."""

    def validate_definition(self, definition: SchemaDefinition) -> ValidationResult:
        """Validate schema definition syntax and semantics."""
        pass

    def validate_database(self, connection: duckdb.DuckDBPyConnection,
                         expected: SchemaDefinition) -> ValidationResult:
        """Validate database matches expected schema."""
        pass

    def validate_migration(self, migration_sql: str) -> ValidationResult:
        """Validate migration SQL for safety."""
        pass

class SchemaDocGenerator:
    """Generate documentation from schema."""

    def generate_markdown(self, schema: SchemaDefinition) -> str:
        """Generate Markdown documentation."""
        pass

    def generate_er_diagram(self, schema: SchemaDefinition) -> str:
        """Generate ER diagram in Mermaid format."""
        pass

    def generate_sql_ddl(self, schema: SchemaDefinition) -> str:
        """Generate complete SQL DDL."""
        pass
```

### Integration Points

#### 1. DatabaseManager Integration
```python
# Enhanced database_manager.py
class DatabaseManager:
    def __init__(self, config: AppConfig):
        self.schema_manager = SchemaManager(
            db_path=config.database.path,
            schema_dir=Path("schema/definitions")
        )

    def get_schema(self) -> str:
        # Use cached schema from SchemaManager instead of runtime query
        return self.schema_manager.get_cached_schema()

    def ensure_schema_version(self) -> None:
        # Validate schema on connection
        result = self.schema_manager.validate_schema()
        if not result.is_valid:
            raise SchemaError(f"Schema validation failed: {result.errors}")
```

#### 2. Converter Integration
```python
# Enhanced convert_to_duckdb.py
class LanduseConverter:
    def __init__(self, schema_version: str = "latest"):
        self.schema_manager = SchemaManager(...)
        self.schema = self.schema_manager.load_definition(schema_version)

    def create_schema(self):
        # Use schema definition instead of hardcoded SQL
        for table_name, table_def in self.schema.tables.items():
            self.conn.execute(table_def.ddl)
            for index in table_def.indexes:
                self.conn.execute(index)
```

#### 3. Prompt System Integration
```python
# Enhanced prompts.py
class PromptManager:
    def __init__(self, schema_manager: SchemaManager):
        self.schema_manager = schema_manager

    def get_system_prompt(self) -> str:
        # Use pre-generated schema documentation
        schema_doc = self.schema_manager.get_documentation()
        return SYSTEM_PROMPT_TEMPLATE.format(schema_info=schema_doc)
```

### File Structure

```
src/landuse/
├── schema/                    # Schema management module
│   ├── __init__.py
│   ├── manager.py            # Main SchemaManager class
│   ├── migration.py          # MigrationEngine class
│   ├── validator.py          # SchemaValidator class
│   ├── generator.py          # Code and doc generation
│   ├── models.py             # Pydantic models for schema
│   └── cli.py                # CLI commands
│
schema/                        # Schema definitions (not in src)
├── definitions/
│   ├── v2.2.0.yaml          # Current production schema
│   ├── v2.3.0.yaml          # Next version
│   └── latest.yaml          # Symlink to latest
│
├── migrations/
│   ├── v2.2.0_to_v2.3.0.sql
│   ├── v2.3.0_to_v2.2.0_rollback.sql
│   ├── checksums.json       # Migration integrity
│   └── history.json         # Migration history
│
├── generated/               # Auto-generated (git-ignored)
│   ├── models.py           # Pydantic models
│   ├── schema.sql          # Complete DDL
│   ├── schema.json         # JSON representation
│   └── docs.md             # Documentation
│
└── tests/
    ├── test_migrations.py
    ├── test_validation.py
    └── fixtures/
        └── test_schemas.yaml
```

## Migration Workflow

### Developer Workflow for Schema Changes

1. **Create New Schema Version**
   ```bash
   uv run schema create-version 2.3.0 --from 2.2.0
   # Creates schema/definitions/v2.3.0.yaml from v2.2.0.yaml
   ```

2. **Edit Schema Definition**
   ```yaml
   # Edit schema/definitions/v2.3.0.yaml
   # Add new tables, modify existing ones
   ```

3. **Generate Migration**
   ```bash
   uv run schema generate-migration 2.2.0 2.3.0
   # Creates schema/migrations/v2.2.0_to_v2.3.0.sql
   # Auto-generates based on schema diff
   ```

4. **Test Migration**
   ```bash
   uv run schema test-migration 2.3.0
   # Tests migration on temporary database
   ```

5. **Apply Migration**
   ```bash
   uv run schema migrate --version 2.3.0
   # Applies migration to production database
   ```

6. **Generate Artifacts**
   ```bash
   uv run schema generate --models --docs
   # Generates Pydantic models and documentation
   ```

### CI/CD Integration

```yaml
# .github/workflows/schema.yml
name: Schema Management
on:
  pull_request:
    paths:
      - 'schema/**'

jobs:
  validate:
    steps:
      - name: Validate Schema
        run: uv run schema validate

      - name: Test Migrations
        run: uv run schema test-migration --all

      - name: Check Backward Compatibility
        run: uv run schema check-compatibility
```

## Validation Strategy

### Multi-Level Validation

1. **Definition Validation** (Build Time)
   - YAML syntax validation
   - SQL DDL parsing
   - Foreign key relationship validation
   - Naming convention checks

2. **Migration Validation** (Pre-Migration)
   - SQL syntax validation
   - Destructive operation detection
   - Data loss risk assessment
   - Rollback availability check

3. **Runtime Validation** (Post-Migration)
   - Table existence verification
   - Column type matching
   - Index presence confirmation
   - Constraint enforcement check

4. **Continuous Validation** (Production)
   - Periodic schema drift detection
   - Data quality metrics
   - Performance regression detection

### Validation Implementation

```python
class SchemaValidator:
    def validate_complete(self) -> ValidationReport:
        """Complete validation pipeline."""
        report = ValidationReport()

        # 1. Validate schema definition
        report.add_section(self.validate_definition())

        # 2. Validate against database
        report.add_section(self.validate_database())

        # 3. Validate data integrity
        report.add_section(self.validate_data_integrity())

        # 4. Validate performance indexes
        report.add_section(self.validate_indexes())

        return report
```

## Documentation Generation

### Auto-Generated Documentation

1. **Markdown Documentation**
   ```markdown
   # Schema Documentation v2.3.0

   ## Tables

   ### dim_scenario
   Climate scenario dimension table

   | Column | Type | Constraints | Description |
   |--------|------|------------|-------------|
   | scenario_id | INTEGER | PRIMARY KEY | Unique identifier |
   | scenario_name | VARCHAR(100) | NOT NULL | Scenario name |
   ...
   ```

2. **ER Diagram (Mermaid)**
   ```mermaid
   erDiagram
     dim_scenario ||--o{ fact_landuse_transitions : has
     dim_geography ||--o{ fact_landuse_transitions : has
   ```

3. **Pydantic Models**
   ```python
   class DimScenario(BaseModel):
       scenario_id: int
       scenario_name: str
       rcp_scenario: Optional[str]
       ...
   ```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
- [x] Design schema definition format
- [ ] Implement SchemaManager core
- [ ] Create SchemaValidator
- [ ] Add basic migration support

### Phase 2: Migration System (Week 3-4)
- [ ] Implement MigrationEngine
- [ ] Add rollback support
- [ ] Create migration testing framework
- [ ] Add checksum validation

### Phase 3: Code Generation (Week 5)
- [ ] Implement Pydantic model generator
- [ ] Add documentation generator
- [ ] Create ER diagram generator
- [ ] Add SQL DDL export

### Phase 4: Integration (Week 6)
- [ ] Integrate with DatabaseManager
- [ ] Update convert_to_duckdb.py
- [ ] Modify prompt system
- [ ] Update agent components

### Phase 5: Testing & Documentation (Week 7)
- [ ] Comprehensive test suite
- [ ] Performance benchmarks
- [ ] Migration from current system
- [ ] User documentation

### Phase 6: Production Rollout (Week 8)
- [ ] Gradual rollout plan
- [ ] Monitoring setup
- [ ] Rollback procedures
- [ ] Team training

## Trade-offs and Alternatives

### Alternatives Considered

1. **SQLAlchemy-Style Python Classes**
   - ✅ Pros: Type-safe, IDE support, familiar to Python developers
   - ❌ Cons: Heavy dependency, ORM overhead unnecessary for DuckDB
   - **Decision**: Rejected - too heavyweight for our use case

2. **Pure SQL Files**
   - ✅ Pros: Simple, no translation layer, DuckDB native
   - ❌ Cons: No metadata, poor version control, no programmatic access
   - **Decision**: Rejected - lacks structure needed for automation

3. **JSON Schema**
   - ✅ Pros: Standard format, good tooling, validation support
   - ❌ Cons: Verbose, poor readability, not SQL-native
   - **Decision**: Rejected - YAML is more human-friendly

4. **Alembic Integration**
   - ✅ Pros: Mature, feature-rich, battle-tested
   - ❌ Cons: SQLAlchemy dependency, PostgreSQL-focused, complex for DuckDB
   - **Decision**: Rejected - overkill and not DuckDB-optimized

### Key Trade-offs

1. **Simplicity vs Features**
   - We prioritize DuckDB-specific simplicity over generic database support
   - Custom solution allows DuckDB optimizations (COPY, Parquet, etc.)

2. **Automation vs Control**
   - Auto-generated migrations with manual review required
   - Balance between developer productivity and safety

3. **Performance vs Flexibility**
   - Cache schema at build time vs runtime discovery
   - Trade query-time flexibility for startup performance

## Risk Mitigation

### Identified Risks

1. **Data Loss During Migration**
   - Mitigation: Mandatory backups, dry-run mode, rollback support

2. **Schema Drift**
   - Mitigation: Continuous validation, drift detection alerts

3. **Performance Degradation**
   - Mitigation: Migration performance tests, index validation

4. **Breaking Changes**
   - Mitigation: Compatibility matrix, semantic versioning

## Success Metrics

1. **Development Velocity**
   - Schema change time: < 1 hour (from 1 day currently)
   - Migration testing: Automated (from manual currently)

2. **Reliability**
   - Migration success rate: > 99.9%
   - Rollback time: < 5 minutes

3. **Performance**
   - Schema retrieval: < 10ms (from 100ms+ currently)
   - Migration execution: < 1 minute for schema changes

4. **Documentation**
   - Auto-generated docs: 100% coverage
   - Schema drift: < 1% monthly

## Conclusion

This schema management architecture provides:
- ✅ Single source of truth (YAML definitions)
- ✅ Robust migration system with rollback
- ✅ Type safety through generated Pydantic models
- ✅ Comprehensive validation at multiple levels
- ✅ Auto-generated documentation
- ✅ DuckDB-optimized design
- ✅ Backward compatibility with existing system
- ✅ Production-ready error handling

The design balances simplicity with power, leveraging DuckDB's strengths while providing the schema management capabilities expected in production systems.