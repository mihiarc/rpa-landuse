"""Migration engine for schema changes."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from landuse.exceptions import MigrationError, SchemaError
from landuse.infrastructure.performance import time_database_operation

from .models import MigrationPlan, MigrationResult, MigrationStatus, MigrationStep


class MigrationEngine:
    """Handles database schema migrations.

    Provides forward migration capabilities with transaction safety,
    rollback support, and validation.
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, migrations_dir: Path, console: Optional[Console] = None):
        """Initialize migration engine.

        Args:
            connection: DuckDB database connection
            migrations_dir: Directory containing migration files
            console: Rich console for output
        """
        self.connection = connection
        self.migrations_dir = Path(migrations_dir)
        self.console = console or Console()
        self._checksums: Dict[str, str] = self._load_checksums()

    def _load_checksums(self) -> Dict[str, str]:
        """Load migration checksums for integrity verification.

        Returns:
            Dictionary of migration file to checksum mappings
        """
        checksum_file = self.migrations_dir / "checksums.json"
        if checksum_file.exists():
            return json.loads(checksum_file.read_text())
        return {}

    def _save_checksums(self):
        """Save migration checksums to file."""
        checksum_file = self.migrations_dir / "checksums.json"
        checksum_file.write_text(json.dumps(self._checksums, indent=2))

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of migration content.

        Args:
            content: Migration SQL content

        Returns:
            Hex digest of checksum
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def _verify_checksum(self, migration_file: Path) -> bool:
        """Verify migration file hasn't been tampered with.

        Args:
            migration_file: Path to migration file

        Returns:
            True if checksum matches or not tracked
        """
        if str(migration_file) not in self._checksums:
            return True  # New migration, not yet tracked

        content = migration_file.read_text()
        expected = self._checksums[str(migration_file)]
        actual = self._calculate_checksum(content)

        if expected != actual:
            raise MigrationError(
                f"Migration checksum mismatch for {migration_file.name}. File may have been modified after creation."
            )

        return True

    def find_migration_path(self, from_version: str, to_version: str) -> List[Path]:
        """Find migration files needed to migrate between versions.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            Ordered list of migration files to apply

        Raises:
            MigrationError: If no migration path found
        """
        # Look for direct migration file
        direct_migration = self.migrations_dir / f"v{from_version}_to_v{to_version}.sql"
        if direct_migration.exists():
            return [direct_migration]

        # Find multi-step migration path
        migration_files = sorted(self.migrations_dir.glob("v*_to_v*.sql"))

        # Build migration graph
        migration_graph: Dict[str, List[Tuple[str, Path]]] = {}
        for file in migration_files:
            match = re.match(r"v([\d.]+)_to_v([\d.]+)\.sql", file.name)
            if match:
                from_v, to_v = match.groups()
                if from_v not in migration_graph:
                    migration_graph[from_v] = []
                migration_graph[from_v].append((to_v, file))

        # Find path using BFS
        path = self._find_path_bfs(migration_graph, from_version, to_version)

        if not path:
            raise MigrationError(f"No migration path found from v{from_version} to v{to_version}")

        return path

    def _find_path_bfs(self, graph: Dict[str, List[Tuple[str, Path]]], start: str, target: str) -> Optional[List[Path]]:
        """Find migration path using breadth-first search.

        Args:
            graph: Migration graph
            start: Starting version
            target: Target version

        Returns:
            List of migration files or None if no path
        """
        from collections import deque

        queue = deque([(start, [])])
        visited = {start}

        while queue:
            current, path = queue.popleft()

            if current == target:
                return path

            if current in graph:
                for next_version, migration_file in graph[current]:
                    if next_version not in visited:
                        visited.add(next_version)
                        queue.append((next_version, path + [migration_file]))

        return None

    def plan_migration(self, from_version: str, to_version: str) -> MigrationPlan:
        """Plan migration between versions.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            Migration execution plan
        """
        migration_files = self.find_migration_path(from_version, to_version)

        steps = []
        requires_downtime = False
        data_loss_risk = False

        for migration_file in migration_files:
            # Verify checksum
            self._verify_checksum(migration_file)

            # Parse migration file
            content = migration_file.read_text()
            migration_steps = self._parse_migration_file(content)

            for step in migration_steps:
                steps.append(step)

                # Check for risky operations
                if self._requires_downtime(step.sql):
                    requires_downtime = True
                if self._has_data_loss_risk(step.sql):
                    data_loss_risk = True

        return MigrationPlan(
            from_version=from_version,
            to_version=to_version,
            steps=steps,
            estimated_duration=len(steps) * 2,  # Rough estimate
            requires_downtime=requires_downtime,
            data_loss_risk=data_loss_risk,
        )

    def _parse_migration_file(self, content: str) -> List[MigrationStep]:
        """Parse migration file into steps.

        Args:
            content: Migration file content

        Returns:
            List of migration steps
        """
        steps = []

        # Split by migration markers
        sections = re.split(r"-- MIGRATION STEP:?\s*(.*)", content)

        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                description = sections[i].strip() or f"Step {len(steps) + 1}"
                sql = sections[i + 1].strip()

                if sql:
                    # Look for rollback SQL
                    rollback_match = re.search(r"-- ROLLBACK:\s*(.*?)(?:-- |$)", sql, re.DOTALL)
                    rollback_sql = rollback_match.group(1) if rollback_match else None

                    # Look for validation SQL
                    validate_match = re.search(r"-- VALIDATE:\s*(.*?)(?:-- |$)", sql, re.DOTALL)
                    validate_sql = validate_match.group(1) if validate_match else None

                    # Clean up main SQL
                    sql = re.sub(r"-- (ROLLBACK|VALIDATE):.*?(?=-- |$)", "", sql, flags=re.DOTALL)

                    steps.append(
                        MigrationStep(
                            description=description,
                            sql=sql.strip(),
                            rollback_sql=rollback_sql.strip() if rollback_sql else None,
                            validate_sql=validate_sql.strip() if validate_sql else None,
                        )
                    )

        # If no step markers, treat entire content as single step
        if not steps and content.strip():
            steps.append(MigrationStep(description="Complete migration", sql=content.strip()))

        return steps

    def _requires_downtime(self, sql: str) -> bool:
        """Check if SQL requires downtime.

        Args:
            sql: SQL statement

        Returns:
            True if operation requires downtime
        """
        downtime_patterns = [
            r"ALTER\s+TABLE.*RENAME",
            r"DROP\s+TABLE",
            r"DROP\s+INDEX",
            r"CREATE\s+UNIQUE\s+INDEX",
            r"ALTER\s+TABLE.*ALTER\s+COLUMN.*TYPE",
        ]

        sql_upper = sql.upper()
        for pattern in downtime_patterns:
            if re.search(pattern, sql_upper):
                return True

        return False

    def _has_data_loss_risk(self, sql: str) -> bool:
        """Check if SQL has data loss risk.

        Args:
            sql: SQL statement

        Returns:
            True if operation risks data loss
        """
        risky_patterns = [r"DROP\s+TABLE", r"DROP\s+COLUMN", r"DELETE\s+FROM", r"TRUNCATE", r"ALTER\s+TABLE.*DROP"]

        sql_upper = sql.upper()
        for pattern in risky_patterns:
            if re.search(pattern, sql_upper):
                return True

        return False

    @time_database_operation("execute_migration")
    def execute_migration(self, plan: MigrationPlan, stop_on_error: bool = True) -> MigrationResult:
        """Execute migration plan.

        Args:
            plan: Migration plan to execute
            stop_on_error: Whether to stop on first error

        Returns:
            Migration execution result
        """
        result = MigrationResult(plan=plan, status=MigrationStatus.IN_PROGRESS, started_at=datetime.utcnow())

        # Warn about risky operations
        if plan.data_loss_risk:
            self.console.print("[bold red]WARNING: This migration has data loss risk![/bold red]")
            response = input("Continue? (yes/no): ")
            if response.lower() != "yes":
                result.status = MigrationStatus.FAILED
                result.errors.append("Migration cancelled by user")
                return result

        # Execute migration steps
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console
        ) as progress:
            task = progress.add_task(
                f"Migrating from v{plan.from_version} to v{plan.to_version}", total=len(plan.steps)
            )

            for i, step in enumerate(plan.steps):
                progress.update(task, description=f"Executing: {step.description}")

                try:
                    # Begin transaction for this step
                    self.connection.begin()

                    # Execute migration SQL
                    self.connection.execute(step.sql)

                    # Validate if provided
                    if step.validate_sql:
                        validation_result = self.connection.execute(step.validate_sql).fetchone()
                        if not validation_result or not validation_result[0]:
                            raise MigrationError(f"Validation failed for step: {step.description}")

                    # Commit transaction
                    self.connection.commit()

                    progress.advance(task)

                except Exception as e:
                    # Rollback transaction
                    self.connection.rollback()

                    error_msg = f"Step {i + 1} failed: {str(e)}"
                    result.errors.append(error_msg)
                    self.console.print(f"[red]{error_msg}[/red]")

                    if stop_on_error:
                        result.status = MigrationStatus.FAILED
                        break

            else:
                # All steps completed successfully
                result.status = MigrationStatus.COMPLETED

                # Update schema version
                from landuse.database.schema_version import SchemaVersionManager

                version_manager = SchemaVersionManager(self.connection)
                version_manager.apply_version(plan.to_version, applied_by="migration_engine")

        # Set completion time
        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        # Log result
        if result.status == MigrationStatus.COMPLETED:
            self.console.print(f"[green]✓ Migration completed in {result.duration_seconds:.1f}s[/green]")
        else:
            self.console.print(f"[red]✗ Migration failed with {len(result.errors)} errors[/red]")

        return result

    def create_migration_file(self, from_version: str, to_version: str, steps: List[MigrationStep]) -> Path:
        """Create a new migration file.

        Args:
            from_version: Starting version
            to_version: Target version
            steps: Migration steps

        Returns:
            Path to created migration file
        """
        migration_file = self.migrations_dir / f"v{from_version}_to_v{to_version}.sql"

        # Build migration content
        content_lines = [
            f"-- Migration: v{from_version} to v{to_version}",
            "-- Author: system",
            f"-- Date: {datetime.utcnow().isoformat()}",
            f"-- Description: Schema migration from v{from_version} to v{to_version}",
            "",
            "-- Pre-migration checks",
            "DO $$",
            "BEGIN",
            f"  IF NOT EXISTS (SELECT 1 FROM schema_version WHERE version_number = '{from_version}') THEN",
            f"    RAISE EXCEPTION 'Current version must be {from_version}';",
            "  END IF;",
            "END $$;",
            "",
            "-- Migration",
            "BEGIN TRANSACTION;",
            "",
        ]

        for i, step in enumerate(steps, 1):
            content_lines.extend([f"-- MIGRATION STEP: {step.description}", step.sql, ""])

            if step.rollback_sql:
                content_lines.extend([f"-- ROLLBACK: {step.rollback_sql}", ""])

            if step.validate_sql:
                content_lines.extend([f"-- VALIDATE: {step.validate_sql}", ""])

        content_lines.extend(
            [
                "-- Update version",
                "INSERT INTO schema_version (version_number, description, applied_by)",
                f"VALUES ('{to_version}', 'Migration from v{from_version}', 'migration_system');",
                "",
                "COMMIT;",
                "",
                "-- Post-migration validation",
                f"SELECT 'Migration to v{to_version} successful' WHERE EXISTS (",
                "  SELECT 1 FROM schema_version",
                f"  WHERE version_number = '{to_version}'",
                ");",
            ]
        )

        content = "\n".join(content_lines)

        # Write migration file
        migration_file.write_text(content)

        # Update checksums
        self._checksums[str(migration_file)] = self._calculate_checksum(content)
        self._save_checksums()

        self.console.print(f"[green]Created migration file: {migration_file}[/green]")
        return migration_file
