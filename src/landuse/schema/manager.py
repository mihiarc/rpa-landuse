"""Central schema management system for DuckDB database."""

import hashlib
import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import yaml
from rich.console import Console

from landuse.core.app_config import AppConfig
from landuse.database.schema_version import SchemaVersionManager
from landuse.exceptions import SchemaError
from landuse.infrastructure.cache import InMemoryCache
from landuse.infrastructure.performance import time_database_operation

from .generator import ModelGenerator, SchemaDocGenerator
from .migration import MigrationEngine
from .models import MigrationPlan, MigrationResult, SchemaDefinition, TableDefinition, ValidationResult, ViewDefinition
from .validator import SchemaValidator


class SchemaManager:
    """Central schema management system.

    Manages schema definitions, migrations, validation, and code generation
    for the DuckDB analytics database.
    """

    def __init__(
        self,
        db_path: Path,
        schema_dir: Path,
        config: Optional[AppConfig] = None,
        console: Optional[Console] = None,
        read_only: bool = True
    ):
        """Initialize schema manager.

        Args:
            db_path: Path to DuckDB database file
            schema_dir: Directory containing schema definitions
            config: Application configuration
            console: Rich console for output
            read_only: Whether to open database in read-only mode (default: True)
        """
        self.db_path = Path(db_path)
        self.schema_dir = Path(schema_dir)
        self.config = config or AppConfig()
        self.console = console or Console()
        self.read_only = read_only

        # Create directories if they don't exist
        self.definitions_dir = self.schema_dir / "definitions"
        self.migrations_dir = self.schema_dir / "migrations"
        self.generated_dir = self.schema_dir / "generated"

        for dir_path in [self.definitions_dir, self.migrations_dir, self.generated_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self._cache = InMemoryCache(max_size=100, default_ttl=3600)
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._version_manager: Optional[SchemaVersionManager] = None
        self._migration_engine: Optional[MigrationEngine] = None
        self._validator: Optional[SchemaValidator] = None

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = duckdb.connect(
                str(self.db_path),
                read_only=self.read_only
            )
        return self._connection

    @property
    def version_manager(self) -> SchemaVersionManager:
        """Get schema version manager."""
        if self._version_manager is None:
            self._version_manager = SchemaVersionManager(self.connection)
        return self._version_manager

    @property
    def migration_engine(self) -> MigrationEngine:
        """Get migration engine."""
        if self._migration_engine is None:
            self._migration_engine = MigrationEngine(
                connection=self.connection,
                migrations_dir=self.migrations_dir
            )
        return self._migration_engine

    @property
    def validator(self) -> SchemaValidator:
        """Get schema validator."""
        if self._validator is None:
            self._validator = SchemaValidator(console=self.console)
        return self._validator

    def load_definition(self, version: str = "latest") -> SchemaDefinition:
        """Load schema definition from YAML file.

        Args:
            version: Schema version to load (or "latest")

        Returns:
            Schema definition object

        Raises:
            SchemaError: If definition file not found or invalid
        """
        cache_key = f"schema_def_{version}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        # Resolve version to file path
        if version == "latest":
            # Find latest version file
            version_files = sorted(self.definitions_dir.glob("v*.yaml"))
            if not version_files:
                raise SchemaError(f"No schema definitions found in {self.definitions_dir}")
            definition_file = version_files[-1]
        else:
            definition_file = self.definitions_dir / f"v{version}.yaml"
            if not definition_file.exists():
                raise SchemaError(f"Schema definition not found: {definition_file}")

        # Load and parse YAML
        try:
            with open(definition_file) as f:
                data = yaml.safe_load(f)

            # Convert to Pydantic model
            schema_def = self._parse_definition(data)

            # Cache the definition
            self._cache.set(cache_key, schema_def)

            return schema_def

        except yaml.YAMLError as e:
            raise SchemaError(f"Invalid YAML in schema definition: {e}")
        except Exception as e:
            raise SchemaError(f"Failed to load schema definition: {e}")

    def _parse_definition(self, data: Dict[str, Any]) -> SchemaDefinition:
        """Parse YAML data into SchemaDefinition model.

        Args:
            data: Raw YAML data

        Returns:
            Parsed schema definition
        """
        # Parse tables
        tables = {}
        for table_name, table_data in data.get('tables', {}).items():
            tables[table_name] = TableDefinition(
                name=table_name,
                description=table_data.get('description'),
                ddl=table_data['ddl'],
                indexes=[{'ddl': idx} for idx in table_data.get('indexes', [])]
            )

        # Parse views
        views = {}
        for view_name, view_data in data.get('views', {}).items():
            views[view_name] = ViewDefinition(
                name=view_name,
                description=view_data.get('description'),
                ddl=view_data['ddl'],
                materialized=view_data.get('materialized', False)
            )

        return SchemaDefinition(
            version=data['version'],
            description=data.get('description', ''),
            author=data.get('author', 'system'),
            created_at=data.get('created_at'),
            backward_compatible=data.get('backward_compatible', True),
            tables=tables,
            views=views
        )

    @time_database_operation("get_current_version")
    def get_current_version(self) -> Optional[str]:
        """Get current database schema version.

        Returns:
            Current version string or None if not versioned
        """
        return self.version_manager.get_current_version()

    @time_database_operation("get_cached_schema")
    def get_cached_schema(self) -> str:
        """Get cached schema documentation.

        Returns:
            Formatted schema documentation string
        """
        cache_key = "schema_documentation"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        # Generate schema documentation
        current_version = self.get_current_version() or "2.2.0"  # Default to known version
        schema_def = self.load_definition(current_version)

        doc_generator = SchemaDocGenerator()
        schema_doc = doc_generator.generate_prompt_format(schema_def)

        # Cache the documentation
        self._cache.set(cache_key, schema_doc, ttl=7200)  # 2 hour TTL

        return schema_doc

    def validate_schema(self) -> ValidationResult:
        """Validate database matches expected schema.

        Returns:
            Validation result with any issues found
        """
        current_version = self.get_current_version()
        if not current_version:
            return ValidationResult(
                is_valid=False,
                issues=[{
                    'level': 'error',
                    'category': 'version',
                    'message': 'Database has no schema version'
                }]
            )

        schema_def = self.load_definition(current_version)
        return self.validator.validate_database(self.connection, schema_def)

    def migrate(
        self,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> MigrationResult:
        """Migrate database to target version.

        Args:
            target_version: Target schema version (None for latest)
            dry_run: If True, plan but don't execute migration

        Returns:
            Migration execution result
        """
        # Determine target version
        if target_version is None:
            # Find latest version
            version_files = sorted(self.definitions_dir.glob("v*.yaml"))
            if not version_files:
                raise SchemaError("No schema definitions found")
            target_version = version_files[-1].stem[1:]  # Remove 'v' prefix

        # Get current version
        current_version = self.get_current_version()
        if not current_version:
            # Database not versioned - detect version
            current_version = self.version_manager.detect_schema_version() or "2.2.0"
            self.console.print(f"[yellow]Detected schema version: {current_version}[/yellow]")

        if current_version == target_version:
            self.console.print(f"[green]Already at version {target_version}[/green]")
            return MigrationResult(
                plan=MigrationPlan(
                    from_version=current_version,
                    to_version=target_version,
                    steps=[]
                ),
                status="completed",
                started_at=datetime.utcnow()
            )

        # Plan migration
        plan = self.migration_engine.plan_migration(current_version, target_version)

        if dry_run:
            self.console.print("[yellow]Dry run - migration not executed[/yellow]")
            return MigrationResult(
                plan=plan,
                status="pending",
                started_at=datetime.utcnow()
            )

        # Execute migration
        return self.migration_engine.execute_migration(plan)

    def generate_models(self) -> Path:
        """Generate Pydantic models from current schema.

        Returns:
            Path to generated models file
        """
        current_version = self.get_current_version() or "2.2.0"
        schema_def = self.load_definition(current_version)

        generator = ModelGenerator()
        models_code = generator.generate_from_schema(schema_def)

        models_path = self.generated_dir / "models.py"
        models_path.write_text(models_code)

        self.console.print(f"[green]Generated models at {models_path}[/green]")
        return models_path

    def export_schema(self, format: str = "sql", version: Optional[str] = None) -> str:
        """Export schema in specified format.

        Args:
            format: Export format (sql, markdown, json, mermaid)
            version: Schema version to export (defaults to latest available)

        Returns:
            Exported schema string
        """
        # If no version specified, use latest available schema definition
        if version is None:
            available_versions = sorted(self.definitions_dir.glob("v*.yaml"))
            if available_versions:
                # Get version from filename (e.g., "v2.2.0.yaml" -> "2.2.0")
                version = available_versions[-1].stem[1:]  # Remove 'v' prefix from stem
            else:
                version = "2.2.0"  # Fallback

        schema_def = self.load_definition(version)

        doc_generator = SchemaDocGenerator()

        if format == "sql":
            return doc_generator.generate_sql_ddl(schema_def)
        elif format == "markdown":
            return doc_generator.generate_markdown(schema_def)
        elif format == "json":
            return schema_def.model_dump_json(indent=2)
        elif format == "mermaid":
            return doc_generator.generate_er_diagram(schema_def)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def create_checkpoint(self) -> Path:
        """Create a checkpoint of current schema state.

        Returns:
            Path to checkpoint file
        """
        current_version = self.get_current_version() or "unknown"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        checkpoint_dir = self.schema_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / f"checkpoint_{current_version}_{timestamp}.json"

        # Export complete schema state
        checkpoint_data = {
            'version': current_version,
            'created_at': datetime.utcnow().isoformat(),
            'schema_sql': self.export_schema('sql'),
            'schema_json': json.loads(self.export_schema('json'))
        }

        # Calculate checksum
        checksum = hashlib.sha256(
            json.dumps(checkpoint_data, sort_keys=True).encode()
        ).hexdigest()
        checkpoint_data['checksum'] = checksum

        # Write checkpoint
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))

        self.console.print(f"[green]Created checkpoint at {checkpoint_file}[/green]")
        return checkpoint_file

    def close(self):
        """Close database connection and cleanup resources."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._cache.clear()


from datetime import datetime
