"""Database management functionality extracted from monolithic agent class."""

from typing import Optional
import warnings

import duckdb
import pandas as pd
from rich.console import Console

from landuse.core.app_config import AppConfig
from landuse.core.interfaces import DatabaseInterface
from landuse.database.schema_version import SchemaVersion, SchemaVersionManager
from landuse.infrastructure.performance import time_database_operation
from landuse.utils.retry_decorators import database_retry


class DatabaseManager(DatabaseInterface):
    """
    Manages database connections and schema operations.

    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles database connection creation, schema retrieval, and connection management.
    """

    def __init__(self, config: Optional[AppConfig] = None, console: Optional[Console] = None):
        """Initialize database manager with configuration."""
        self.config = config or AppConfig()
        self.console = console or Console()
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._schema: Optional[str] = None
        self._version_manager: Optional[SchemaVersionManager] = None
        self._db_version: Optional[str] = None

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get or create database connection.

        Returns:
            DuckDB connection instance
        """
        if self._connection is None:
            self._connection = self.create_connection()
        return self._connection

    def create_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Create a new database connection and check schema version.

        Returns:
            DuckDB connection in read-only mode
        """
        connection = duckdb.connect(database=self.config.database.path, read_only=True)
        self._check_schema_version(connection)
        return connection

    @database_retry(max_attempts=3)
    @time_database_operation("get_schema", track_row_count=False)
    def get_schema(self) -> str:
        """
        Get the database schema with retry logic.

        Returns:
            Formatted schema string

        Raises:
            ValueError: If no tables found in database
        """
        if self._schema is not None:
            return self._schema

        conn = self.get_connection()

        # Get table count for validation
        table_count_query = """
        SELECT COUNT(*) as table_count
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
        result = conn.execute(table_count_query).fetchone()
        table_count = result[0] if result else 0

        if table_count == 0:
            raise ValueError(f"No tables found in database at {self.config.database.path}")

        self.console.print(f"[green]✓ Found {table_count} tables in database[/green]")

        # Get schema information - prioritize combined tables
        schema_query = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'main'
        -- Exclude original tables if combined versions exist
        AND table_name NOT IN ('dim_scenario_original', 'fact_landuse_transitions_original')
        -- Prioritize combined tables by excluding originals when both exist
        AND (
            (table_name = 'dim_scenario_combined' OR table_name NOT LIKE 'dim_scenario')
            AND (table_name = 'fact_landuse_combined' OR table_name NOT LIKE 'fact_landuse_transitions')
        )
        ORDER BY
            -- Prioritize combined tables and views
            CASE
                WHEN table_name = 'dim_scenario_combined' THEN 1
                WHEN table_name = 'fact_landuse_combined' THEN 2
                WHEN table_name LIKE 'v_default_transitions' THEN 3
                WHEN table_name LIKE 'v_scenario_comparisons' THEN 4
                ELSE 5
            END,
            table_name, ordinal_position
        """

        result = conn.execute(schema_query).fetchall()
        self._schema = self._format_schema(result)
        return self._schema

    def _format_schema(self, schema_result: list[tuple]) -> str:
        """
        Format schema query results into a readable string.

        Args:
            schema_result: Raw schema query results

        Returns:
            Formatted schema string
        """
        schema_lines = ["Database Schema:"]
        current_table = None

        for row in schema_result:
            table_name, column_name, data_type, is_nullable = row
            if table_name != current_table:
                schema_lines.append(f"\nTable: {table_name}")
                current_table = table_name
            nullable = "" if is_nullable == "YES" else " NOT NULL"
            schema_lines.append(f"  - {column_name}: {data_type}{nullable}")

        return "\n".join(schema_lines)

    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up connection."""
        self.close()

    @time_database_operation("execute_query")
    def execute_query(self, query: str, **kwargs) -> pd.DataFrame:
        """Execute SQL query and return DataFrame (DatabaseInterface implementation)."""
        conn = self.get_connection()
        result = conn.execute(query).fetchall()
        columns = [desc[0] for desc in conn.description] if conn.description else []

        return pd.DataFrame(result, columns=columns)

    def validate_table_name(self, table_name: str) -> bool:
        """Validate table name exists and is accessible (DatabaseInterface implementation)."""
        try:
            conn = self.get_connection()
            result = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = ? AND table_schema = 'main'
            """, [table_name]).fetchone()
            return result[0] > 0 if result else False
        except Exception:
            return False

    def _check_schema_version(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Check and log database schema version on connection.

        Args:
            connection: DuckDB connection to check
        """
        try:
            # Create version manager (read-only safe - only creates table structure if missing)
            self._version_manager = SchemaVersionManager(connection)

            # Get current database version
            self._db_version = self._version_manager.get_current_version()

            if self._db_version is None:
                # Try to detect version from schema structure
                detected_version = self._version_manager.detect_schema_version()
                if detected_version:
                    self._db_version = detected_version
                    self.console.print(
                        f"[yellow]⚠ Database schema version not set. Detected as v{detected_version}[/yellow]"
                    )
                else:
                    self.console.print(
                        "[yellow]⚠ Database schema version unknown. Consider running version migration.[/yellow]"
                    )
            else:
                self.console.print(f"[green]✓ Database schema version: {self._db_version}[/green]")

            # Check compatibility
            is_compatible, current_version = self._version_manager.check_compatibility()
            if not is_compatible:
                warnings.warn(
                    f"Database version {current_version} may not be fully compatible with "
                    f"application version {SchemaVersion.CURRENT_VERSION}. "
                    f"Some features may not work as expected.",
                    UserWarning
                )
                self.console.print(
                    f"[yellow]⚠ Version compatibility warning: Database v{current_version} "
                    f"with application v{SchemaVersion.CURRENT_VERSION}[/yellow]"
                )

        except Exception as e:
            # Don't fail connection, just log warning
            self.console.print(f"[yellow]⚠ Could not check schema version: {str(e)}[/yellow]")

    def get_database_version(self) -> Optional[str]:
        """Get the current database schema version.

        Returns:
            Version string or None if not versioned
        """
        return self._db_version

    def get_version_history(self) -> list:
        """Get database version history.

        Returns:
            List of version records or empty list
        """
        if self._version_manager:
            return self._version_manager.get_version_history()
        return []
