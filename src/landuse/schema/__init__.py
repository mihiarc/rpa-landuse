"""Schema management system for DuckDB database.

This module provides comprehensive schema management capabilities including:
- Declarative schema definitions using YAML
- Forward migration system with rollback support
- Automatic Pydantic model generation
- Schema validation and drift detection
- Documentation generation
"""

from .manager import SchemaManager
from .migration import MigrationEngine, MigrationPlan, MigrationResult
from .validator import SchemaValidator, ValidationResult
from .generator import SchemaDocGenerator, ModelGenerator
from .models import (
    SchemaDefinition,
    TableDefinition,
    ViewDefinition,
    IndexDefinition,
    MigrationStatus
)

__all__ = [
    'SchemaManager',
    'MigrationEngine',
    'MigrationPlan',
    'MigrationResult',
    'SchemaValidator',
    'ValidationResult',
    'SchemaDocGenerator',
    'ModelGenerator',
    'SchemaDefinition',
    'TableDefinition',
    'ViewDefinition',
    'IndexDefinition',
    'MigrationStatus'
]