"""Database management functionality extracted from monolithic agent class.

Provides database connection management with connection pooling for
improved performance and resource utilization in multi-threaded environments.
"""

import warnings
from typing import Optional

import duckdb
import pandas as pd
from rich.console import Console

from landuse.core.app_config import AppConfig
from landuse.core.interfaces import DatabaseInterface
from landuse.database.schema_version import SchemaVersion, SchemaVersionManager
from landuse.exceptions import DatabaseConnectionError, SchemaError
from landuse.infrastructure.connection_pool import DatabaseConnectionPool
from landuse.infrastructure.logging import get_logger
from landuse.infrastructure.performance import time_database_operation
from landuse.utils.retry_decorators import database_retry


class DatabaseManager(DatabaseInterface):
    """
    Manages database connections and schema operations with connection pooling.

    Uses a thread-safe connection pool for efficient connection sharing across
    concurrent requests. Extracted from the monolithic LanduseAgent class to
    follow Single Responsibility Principle.

    Example:
        >>> with DatabaseManager(config) as db:
        ...     schema = db.get_schema()
        ...     with db.connection() as conn:
        ...         result = conn.execute("SELECT * FROM table")
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        console: Optional[Console] = None,
    ):
        """Initialize database manager with configuration.

        Args:
            config: Application configuration (uses defaults if not provided)
            console: Rich console for output (creates new one if not provided)

        Raises:
            DatabaseConnectionError: If connection pool initialization fails
        """
        self.config = config or AppConfig()
        self.console = console or Console()
        self._logger = get_logger("database")

        # Cached schema and version info
        self._schema: Optional[str] = None
        self._version_manager: Optional[SchemaVersionManager] = None
        self._db_version: Optional[str] = None
        self._version_checked: bool = False

        self._logger.info("Initializing DatabaseManager", path=self.config.database.path)

        # Initialize connection pool
        self._pool = self._create_pool()

    def _create_pool(self) -> DatabaseConnectionPool:
        """Create and initialize the connection pool.

        Returns:
            Initialized connection pool

        Raises:
            DatabaseConnectionError: If pool creation fails
        """
        try:
            pool = DatabaseConnectionPool(
                database_path=self.config.database.path,
                max_connections=self.config.database.max_connections,
                connection_timeout=self.config.database.connection_timeout,
                read_only=self.config.database.read_only,
                console=self.console,
            )
            self._logger.info(
                "Connection pool initialized",
                max_connections=self.config.database.max_connections,
                read_only=self.config.database.read_only,
            )
            self.console.print(
                f"[green]✓ Connection pool initialized (max: {self.config.database.max_connections})[/green]"
            )

            # Check schema version with a pooled connection
            with pool.connection() as conn:
                self._check_schema_version(conn)

            return pool

        except DatabaseConnectionError:
            self._logger.error("Failed to create connection pool", path=self.config.database.path)
            raise
        except Exception as e:
            self._logger.exception("Unexpected error creating connection pool")
            raise DatabaseConnectionError(f"Failed to initialize connection pool: {e}", host=self.config.database.path)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Acquire a database connection from the pool.

        Returns:
            DuckDB connection instance

        Note:
            Prefer using the connection() context manager to ensure
            proper connection release.
        """
        return self._pool.acquire()

    def release_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        self._pool.release(connection)

    def connection(self, timeout: Optional[float] = None):
        """Context manager for safely acquiring and releasing connections.

        Args:
            timeout: Optional timeout override for connection acquisition

        Yields:
            DuckDB connection instance

        Example:
            >>> with db_manager.connection() as conn:
            ...     result = conn.execute("SELECT * FROM table")
        """
        return self._pool.connection(timeout=timeout)

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

        with self.connection() as conn:
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

            # Get schema information - ONLY RPA landuse tables
            # Filter to avoid picking up FIA or other project tables in shared MotherDuck
            schema_query = """
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main'
            -- CRITICAL: Only include RPA landuse tables (dim_*, fact_*, v_* patterns)
            AND (
                table_name LIKE 'dim_%'
                OR table_name LIKE 'fact_%'
                OR table_name LIKE 'v_%'
            )
            -- Exclude original tables if combined versions exist
            AND table_name NOT IN ('dim_scenario_original', 'fact_landuse_transitions_original')
            ORDER BY
                -- Prioritize core tables
                CASE
                    WHEN table_name = 'fact_landuse_transitions' THEN 1
                    WHEN table_name = 'dim_scenario' THEN 2
                    WHEN table_name = 'dim_geography' THEN 3
                    WHEN table_name = 'dim_landuse' THEN 4
                    WHEN table_name = 'dim_time' THEN 5
                    WHEN table_name LIKE 'v_%' THEN 6
                    ELSE 7
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
        """Close the connection pool and release all connections."""
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up connection."""
        self.close()

    @time_database_operation("execute_query")
    def execute_query(self, query: str, **kwargs) -> pd.DataFrame:
        """Execute SQL query and return DataFrame (DatabaseInterface implementation)."""
        with self.connection() as conn:
            result = conn.execute(query).fetchall()
            columns = [desc[0] for desc in conn.description] if conn.description else []
            return pd.DataFrame(result, columns=columns)

    def validate_table_name(self, table_name: str) -> bool:
        """Validate table name exists and is accessible (DatabaseInterface implementation).

        Args:
            table_name: Name of table to validate

        Returns:
            True if table exists, False otherwise

        Note:
            Returns False for any database errors rather than raising,
            as validation is used in conditional checks.
        """
        try:
            with self.connection() as conn:
                result = conn.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name = ? AND table_schema = 'main'
                """,
                    [table_name],
                ).fetchone()
                return result[0] > 0 if result else False
        except duckdb.Error as e:
            # Log the specific database error but return False for validation
            self.console.print(f"[dim]Table validation error for '{table_name}': {str(e)}[/dim]")
            return False
        except Exception as e:
            # Unexpected errors should be logged
            self.console.print(f"[yellow]⚠ Unexpected error validating table '{table_name}': {str(e)}[/yellow]")
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
                    UserWarning,
                    stacklevel=2,
                )
                self.console.print(
                    f"[yellow]⚠ Version compatibility warning: Database v{current_version} "
                    f"with application v{SchemaVersion.CURRENT_VERSION}[/yellow]"
                )

        except duckdb.Error as e:
            # Database-specific errors during version check - don't fail connection
            self.console.print(f"[yellow]⚠ Database error checking schema version: {str(e)}[/yellow]")
        except SchemaError as e:
            # Schema-related issues - expected during version detection
            self.console.print(f"[yellow]⚠ Schema version check: {e.message}[/yellow]")
        except Exception as e:
            # Unexpected errors - log but don't fail connection
            self.console.print(f"[yellow]⚠ Could not check schema version: {type(e).__name__}: {str(e)}[/yellow]")
        finally:
            self._version_checked = True

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

    def get_pool_statistics(self) -> dict:
        """Get connection pool statistics.

        Returns:
            Dictionary of pool statistics
        """
        return self._pool.get_statistics()

    def is_pool_healthy(self) -> bool:
        """Check if connection pool is healthy.

        Returns:
            True if pool is healthy, False otherwise
        """
        return self._pool.is_healthy()
