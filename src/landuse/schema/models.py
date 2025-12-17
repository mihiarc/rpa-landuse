"""Pydantic models for schema management system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MigrationStatus(str, Enum):
    """Migration execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ValidationLevel(str, Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IndexDefinition(BaseModel):
    """Index definition for a table."""

    name: Optional[str] = Field(default=None, description="Index name (optional if ddl provided)")
    columns: Optional[List[str]] = Field(default=None, description="Columns to index (optional if ddl provided)")
    unique: bool = Field(default=False, description="Whether index is unique")
    type: Optional[str] = Field(default=None, description="Index type (btree, hash, etc)")
    ddl: Optional[str] = Field(default=None, description="Custom DDL for index creation")



class ConstraintDefinition(BaseModel):
    """Constraint definition for a table."""

    name: Optional[str] = Field(default=None, description="Constraint name")
    type: str = Field(description="Constraint type (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)")
    columns: Optional[List[str]] = Field(default=None, description="Columns involved")
    references: Optional[str] = Field(default=None, description="Referenced table for FK")
    condition: Optional[str] = Field(default=None, description="CHECK constraint condition")


class ColumnDefinition(BaseModel):
    """Column definition for a table."""

    name: str = Field(description="Column name")
    type: str = Field(description="Column data type")
    nullable: bool = Field(default=True, description="Whether column allows NULL")
    default: Optional[Any] = Field(default=None, description="Default value")
    primary_key: bool = Field(default=False, description="Whether column is primary key")
    description: Optional[str] = Field(default=None, description="Column description")


class TableDefinition(BaseModel):
    """Table definition in schema."""

    name: str = Field(description="Table name")
    description: Optional[str] = Field(default=None, description="Table description")
    ddl: str = Field(description="Complete DDL for table creation")
    columns: Optional[List[ColumnDefinition]] = Field(default=None, description="Column definitions")
    indexes: List[IndexDefinition] = Field(default_factory=list, description="Table indexes")
    constraints: List[ConstraintDefinition] = Field(default_factory=list, description="Table constraints")
    partitioning: Optional[Dict[str, Any]] = Field(default=None, description="Partitioning configuration")


class ViewDefinition(BaseModel):
    """View definition in schema."""

    name: str = Field(description="View name")
    description: Optional[str] = Field(default=None, description="View description")
    ddl: str = Field(description="Complete DDL for view creation")
    materialized: bool = Field(default=False, description="Whether view is materialized")


class SchemaDefinition(BaseModel):
    """Complete schema definition."""

    version: str = Field(description="Schema version (semantic versioning)")
    description: str = Field(description="Version description")
    author: str = Field(default="system", description="Author of this version")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    backward_compatible: bool = Field(default=True, description="Whether backward compatible")
    tables: Dict[str, TableDefinition] = Field(default_factory=dict, description="Table definitions")
    views: Dict[str, ViewDefinition] = Field(default_factory=dict, description="View definitions")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        import re
        pattern = r'^\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid semantic version: {v}")
        return v


class MigrationStep(BaseModel):
    """Individual migration step."""

    description: str = Field(description="Step description")
    sql: str = Field(description="SQL to execute")
    rollback_sql: Optional[str] = Field(default=None, description="SQL to rollback this step")
    validate_sql: Optional[str] = Field(default=None, description="SQL to validate step success")


class MigrationPlan(BaseModel):
    """Migration execution plan."""

    from_version: str = Field(description="Starting version")
    to_version: str = Field(description="Target version")
    steps: List[MigrationStep] = Field(description="Migration steps in order")
    estimated_duration: Optional[int] = Field(default=None, description="Estimated duration in seconds")
    requires_downtime: bool = Field(default=False, description="Whether migration requires downtime")
    data_loss_risk: bool = Field(default=False, description="Whether migration risks data loss")


class MigrationResult(BaseModel):
    """Migration execution result."""

    plan: MigrationPlan = Field(description="Executed migration plan")
    status: MigrationStatus = Field(description="Migration status")
    started_at: datetime = Field(description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    duration_seconds: Optional[float] = Field(default=None, description="Actual duration")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated")
    rollback_available: bool = Field(default=True, description="Whether rollback is available")


class ValidationIssue(BaseModel):
    """Validation issue found during schema validation."""

    level: ValidationLevel = Field(description="Issue severity")
    category: str = Field(description="Issue category (schema, data, performance)")
    message: str = Field(description="Issue description")
    table: Optional[str] = Field(default=None, description="Affected table")
    column: Optional[str] = Field(default=None, description="Affected column")
    suggestion: Optional[str] = Field(default=None, description="Fix suggestion")


class ValidationResult(BaseModel):
    """Schema validation result."""

    is_valid: bool = Field(description="Overall validation status")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues")
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    schema_version: Optional[str] = Field(default=None, description="Schema version validated")
    database_version: Optional[str] = Field(default=None, description="Database version found")

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len([i for i in self.issues if i.level == ValidationLevel.ERROR])

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len([i for i in self.issues if i.level == ValidationLevel.WARNING])


class SchemaCheckpoint(BaseModel):
    """Schema checkpoint for recovery."""

    version: str = Field(description="Schema version")
    created_at: datetime = Field(description="Checkpoint timestamp")
    backup_path: Optional[Path] = Field(default=None, description="Backup file path")
    checksum: str = Field(description="Schema checksum")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
