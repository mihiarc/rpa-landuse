"""Database management functionality extracted from monolithic agent class."""

from typing import Optional

import duckdb
from rich.console import Console

from landuse.config.landuse_config import LanduseConfig
from landuse.utils.retry_decorators import database_retry


class DatabaseManager:
    """
    Manages database connections and schema operations.
    
    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles database connection creation, schema retrieval, and connection management.
    """

    def __init__(self, config: Optional[LanduseConfig] = None, console: Optional[Console] = None):
        """Initialize database manager with configuration."""
        self.config = config or LanduseConfig()
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