"""Schema validation system for database consistency checks."""

import re
from typing import Dict, List, Optional, Set

import duckdb
from rich.console import Console

from landuse.exceptions import ValidationError

from .models import SchemaDefinition, TableDefinition, ValidationIssue, ValidationLevel, ValidationResult


class SchemaValidator:
    """Validates schema consistency and database integrity.

    Provides multi-level validation including:
    - Schema definition syntax validation
    - Database structure verification
    - Data integrity checks
    - Performance optimization validation
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize schema validator.

        Args:
            console: Rich console for output
        """
        self.console = console or Console()

    def validate_definition(self, definition: SchemaDefinition) -> ValidationResult:
        """Validate schema definition syntax and semantics.

        Args:
            definition: Schema definition to validate

        Returns:
            Validation result with any issues found
        """
        issues = []

        # Validate version format
        if not self._is_valid_version(definition.version):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="schema",
                    message=f"Invalid version format: {definition.version}",
                    suggestion="Use semantic versioning (e.g., 2.3.0)",
                )
            )

        # Validate tables
        for table_name, table_def in definition.tables.items():
            table_issues = self._validate_table_definition(table_name, table_def)
            issues.extend(table_issues)

        # Validate views
        for view_name, view_def in definition.views.items():
            view_issues = self._validate_view_definition(view_name, view_def)
            issues.extend(view_issues)

        # Check foreign key relationships
        fk_issues = self._validate_foreign_keys(definition)
        issues.extend(fk_issues)

        return ValidationResult(
            is_valid=len([i for i in issues if i.level == ValidationLevel.ERROR]) == 0,
            issues=issues,
            schema_version=definition.version,
        )

    def validate_database(self, connection: duckdb.DuckDBPyConnection, expected: SchemaDefinition) -> ValidationResult:
        """Validate database matches expected schema.

        Args:
            connection: Database connection
            expected: Expected schema definition

        Returns:
            Validation result with any issues found
        """
        issues = []

        # Get actual database schema
        actual_tables = self._get_database_tables(connection)
        actual_views = self._get_database_views(connection)

        # Check for missing tables
        for table_name in expected.tables:
            if table_name not in actual_tables:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="schema",
                        message=f"Table missing: {table_name}",
                        table=table_name,
                        suggestion="Create table using migration or schema sync",
                    )
                )
            else:
                # Validate table structure
                table_issues = self._validate_table_structure(
                    connection, table_name, expected.tables[table_name], actual_tables[table_name]
                )
                issues.extend(table_issues)

        # Check for extra tables
        expected_table_names = set(expected.tables.keys())
        extra_tables = set(actual_tables.keys()) - expected_table_names
        for table_name in extra_tables:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="schema",
                    message=f"Unexpected table found: {table_name}",
                    table=table_name,
                    suggestion="Remove table or update schema definition",
                )
            )

        # Check views
        for view_name in expected.views:
            if view_name not in actual_views:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="schema",
                        message=f"View missing: {view_name}",
                        table=view_name,
                        suggestion="Create view using migration",
                    )
                )

        # Validate data integrity
        integrity_issues = self._validate_data_integrity(connection, expected)
        issues.extend(integrity_issues)

        # Validate performance optimizations
        performance_issues = self._validate_performance(connection, expected)
        issues.extend(performance_issues)

        return ValidationResult(
            is_valid=len([i for i in issues if i.level == ValidationLevel.ERROR]) == 0,
            issues=issues,
            schema_version=expected.version,
        )

    def validate_migration(self, migration_sql: str) -> ValidationResult:
        """Validate migration SQL for safety.

        Args:
            migration_sql: SQL migration script

        Returns:
            Validation result with any issues found
        """
        issues = []

        # Check for dangerous operations
        dangerous_patterns = [
            (r"DROP\s+DATABASE", "DROP DATABASE is not allowed"),
            (r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1", "Unconditional DELETE detected"),
            (r"UPDATE.*SET.*WHERE\s+1\s*=\s*1", "Unconditional UPDATE detected"),
            (r"TRUNCATE", "TRUNCATE should be used with caution"),
        ]

        sql_upper = migration_sql.upper()
        for pattern, message in dangerous_patterns:
            if re.search(pattern, sql_upper):
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="migration",
                        message=message,
                        suggestion="Review and modify the dangerous operation",
                    )
                )

        # Check for transaction safety
        if "BEGIN" not in sql_upper or "COMMIT" not in sql_upper:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="migration",
                    message="Migration not wrapped in transaction",
                    suggestion="Wrap migration in BEGIN/COMMIT for atomicity",
                )
            )

        # Check for validation steps
        if "VALIDATE" not in migration_sql and "SELECT" not in sql_upper:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="migration",
                    message="No validation steps found",
                    suggestion="Add validation queries to verify migration success",
                )
            )

        return ValidationResult(
            is_valid=len([i for i in issues if i.level == ValidationLevel.ERROR]) == 0, issues=issues
        )

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semantic version.

        Args:
            version: Version string

        Returns:
            True if valid semantic version
        """
        pattern = r"^\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$"
        return bool(re.match(pattern, version))

    def _validate_table_definition(self, table_name: str, table_def: TableDefinition) -> List[ValidationIssue]:
        """Validate individual table definition.

        Args:
            table_name: Table name
            table_def: Table definition

        Returns:
            List of validation issues
        """
        issues = []

        # Validate table name
        if not re.match(r"^[a-z][a-z0-9_]*$", table_name):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="naming",
                    message=f"Table name '{table_name}' doesn't follow naming convention",
                    table=table_name,
                    suggestion="Use lowercase with underscores (e.g., fact_transitions)",
                )
            )

        # Validate DDL syntax
        try:
            # Basic SQL parsing - check for CREATE TABLE
            if "CREATE TABLE" not in table_def.ddl.upper():
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="schema",
                        message=f"Invalid DDL for table {table_name}",
                        table=table_name,
                        suggestion="DDL must contain CREATE TABLE statement",
                    )
                )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="schema",
                    message=f"Error parsing DDL for table {table_name}: {str(e)}",
                    table=table_name,
                )
            )

        return issues

    def _validate_view_definition(self, view_name: str, view_def) -> List[ValidationIssue]:
        """Validate individual view definition.

        Args:
            view_name: View name
            view_def: View definition

        Returns:
            List of validation issues
        """
        issues = []

        # Validate view name
        if not re.match(r"^v_[a-z][a-z0-9_]*$", view_name):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="naming",
                    message=f"View '{view_name}' doesn't follow naming convention",
                    table=view_name,
                    suggestion="Prefix views with 'v_' (e.g., v_summary)",
                )
            )

        # Validate DDL
        if "CREATE" not in view_def.ddl.upper() or "VIEW" not in view_def.ddl.upper():
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="schema",
                    message=f"Invalid DDL for view {view_name}",
                    table=view_name,
                    suggestion="DDL must contain CREATE VIEW statement",
                )
            )

        return issues

    def _validate_foreign_keys(self, definition: SchemaDefinition) -> List[ValidationIssue]:
        """Validate foreign key relationships.

        Args:
            definition: Schema definition

        Returns:
            List of validation issues
        """
        issues = []
        table_names = set(definition.tables.keys())

        for table_name, table_def in definition.tables.items():
            # Extract foreign key references from DDL
            fk_pattern = r"FOREIGN\s+KEY.*REFERENCES\s+(\w+)"
            matches = re.finditer(fk_pattern, table_def.ddl, re.IGNORECASE)

            for match in matches:
                referenced_table = match.group(1).lower()
                if referenced_table not in table_names:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category="schema",
                            message=f"Foreign key references non-existent table: {referenced_table}",
                            table=table_name,
                            suggestion=f"Create table '{referenced_table}' or fix reference",
                        )
                    )

        return issues

    def _get_database_tables(self, connection: duckdb.DuckDBPyConnection) -> Dict[str, Dict]:
        """Get actual table structure from database.

        Args:
            connection: Database connection

        Returns:
            Dictionary of table definitions
        """
        tables = {}

        # Get list of tables
        result = connection.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            AND table_type = 'BASE TABLE'
        """).fetchall()

        for (table_name,) in result:
            # Get columns for each table
            columns = connection.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'main'
                AND table_name = ?
                ORDER BY ordinal_position
            """,
                [table_name],
            ).fetchall()

            tables[table_name] = {"columns": columns}

        return tables

    def _get_database_views(self, connection: duckdb.DuckDBPyConnection) -> Set[str]:
        """Get view names from database.

        Args:
            connection: Database connection

        Returns:
            Set of view names
        """
        result = connection.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            AND table_type = 'VIEW'
        """).fetchall()

        return {row[0] for row in result}

    def _validate_table_structure(
        self, connection: duckdb.DuckDBPyConnection, table_name: str, expected: TableDefinition, actual: Dict
    ) -> List[ValidationIssue]:
        """Validate table structure matches expected.

        Args:
            connection: Database connection
            table_name: Table name
            expected: Expected table definition
            actual: Actual table structure

        Returns:
            List of validation issues
        """
        issues = []

        # For now, just check that table has columns
        if not actual.get("columns"):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="schema",
                    message=f"Table {table_name} has no columns",
                    table=table_name,
                )
            )

        return issues

    def _validate_data_integrity(
        self, connection: duckdb.DuckDBPyConnection, definition: SchemaDefinition
    ) -> List[ValidationIssue]:
        """Validate data integrity constraints.

        Args:
            connection: Database connection
            definition: Schema definition

        Returns:
            List of validation issues
        """
        issues = []

        # Check for orphaned foreign keys in fact tables
        if "fact_landuse_transitions" in definition.tables:
            orphan_check = """
                SELECT COUNT(*) as orphans
                FROM fact_landuse_transitions f
                LEFT JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                WHERE s.scenario_id IS NULL
            """
            try:
                result = connection.execute(orphan_check).fetchone()
                if result and result[0] > 0:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category="data",
                            message=f"Found {result[0]} orphaned records in fact_landuse_transitions",
                            table="fact_landuse_transitions",
                            suggestion="Fix referential integrity or clean orphaned records",
                        )
                    )
            except:
                pass  # Table might not exist yet

        return issues

    def _validate_performance(
        self, connection: duckdb.DuckDBPyConnection, definition: SchemaDefinition
    ) -> List[ValidationIssue]:
        """Validate performance optimizations.

        Args:
            connection: Database connection
            definition: Schema definition

        Returns:
            List of validation issues
        """
        issues = []

        # Check for missing indexes on foreign keys
        for table_name in definition.tables:
            try:
                # Get foreign key columns
                fk_columns = self._extract_foreign_key_columns(definition.tables[table_name].ddl)

                # Get existing indexes
                index_result = connection.execute(
                    """
                    SELECT DISTINCT column_name
                    FROM duckdb_indexes()
                    WHERE table_name = ?
                """,
                    [table_name],
                ).fetchall()

                indexed_columns = {row[0] for row in index_result}

                # Check if FK columns are indexed
                for fk_column in fk_columns:
                    if fk_column not in indexed_columns:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                category="performance",
                                message=f"Foreign key column '{fk_column}' not indexed",
                                table=table_name,
                                column=fk_column,
                                suggestion=f"CREATE INDEX idx_{table_name}_{fk_column} ON {table_name}({fk_column})",
                            )
                        )
            except:
                pass  # Ignore errors for missing tables

        return issues

    def _extract_foreign_key_columns(self, ddl: str) -> Set[str]:
        """Extract foreign key column names from DDL.

        Args:
            ddl: Table DDL

        Returns:
            Set of foreign key column names
        """
        fk_columns = set()

        # Pattern to match foreign key definitions
        patterns = [
            r"(\w+)\s+.*REFERENCES",  # Column-level FK
            r"FOREIGN\s+KEY\s*\((\w+)\)",  # Table-level FK
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, ddl, re.IGNORECASE)
            for match in matches:
                fk_columns.add(match.group(1).lower())

        return fk_columns
