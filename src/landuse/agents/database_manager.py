"""Database management functionality extracted from monolithic agent class."""

from typing import Optional, Union

import duckdb
import pandas as pd
from rich.console import Console

from landuse.config.landuse_config import LanduseConfig
from landuse.core.app_config import AppConfig
from landuse.core.interfaces import DatabaseInterface
from landuse.infrastructure.performance import time_database_operation
from landuse.utils.retry_decorators import database_retry


class DatabaseManager(DatabaseInterface):
    """
    Manages database connections and schema operations.

    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles database connection creation, schema retrieval, and connection management.
    """

    def __init__(self, config: Optional[Union[LanduseConfig, AppConfig]] = None, console: Optional[Console] = None):
        """Initialize database manager with configuration."""
        if isinstance(config, AppConfig):
            self.app_config = config
            self.config = self._convert_to_legacy_config(config)
        else:
            self.config = config or LanduseConfig()
            self.app_config = None

        self.console = console or Console()
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._schema: Optional[str] = None

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
        Create a new database connection.

        Returns:
            DuckDB connection in read-only mode
        """
        return duckdb.connect(database=self.config.db_path, read_only=True)

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
            raise ValueError(f"No tables found in database at {self.config.db_path}")

        self.console.print(f"[green]✓ Found {table_count} tables in database[/green]")

        # Get schema information
        schema_query = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'main'
        ORDER BY table_name, ordinal_position
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

    def _convert_to_legacy_config(self, app_config: AppConfig) -> LanduseConfig:
        """Convert AppConfig to legacy LanduseConfig for backward compatibility."""
        # Create legacy config bypassing validation for now
        from landuse.config.landuse_config import LanduseConfig

        # Create instance without validation to avoid API key issues during conversion
        legacy_config = object.__new__(LanduseConfig)

        # Map database settings
        legacy_config.db_path = app_config.database.path

        # Map LLM settings
        legacy_config.model = app_config.llm.model_name  # Note: model_name in AppConfig vs model in legacy
        legacy_config.temperature = app_config.llm.temperature
        legacy_config.max_tokens = app_config.llm.max_tokens

        # Map agent execution settings
        legacy_config.max_iterations = app_config.agent.max_iterations
        legacy_config.max_execution_time = app_config.agent.max_execution_time
        legacy_config.max_query_rows = app_config.agent.max_query_rows
        legacy_config.default_display_limit = app_config.agent.default_display_limit

        # Map debugging settings
        legacy_config.debug = app_config.logging.level == 'DEBUG'
        legacy_config.enable_memory = app_config.agent.enable_memory

        return legacy_config

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
