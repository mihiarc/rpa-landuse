#!/usr/bin/env python3
"""
DuckDB Connection Manager

Provides efficient database access with connection pooling, caching, and retry logic.
"""

import os
import time
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import duckdb
import pandas as pd
from pydantic import BaseModel, Field

from ..exceptions import DatabaseConnectionError, DatabaseError, wrap_exception
from ..models import QueryResult, SQLQuery
from ..security.database_security import DatabaseSecurity
from ..utils.retry_decorators import database_retry


class ConnectionConfig(BaseModel):
    """Configuration for DuckDB connection"""

    database: str = Field(
        default="data/processed/landuse_analytics.duckdb",
        description="Path to DuckDB file or ':memory:'",
    )
    read_only: bool = Field(default=True, description="Open in read-only mode")
    memory_limit: Optional[str] = Field(default=None, description="Memory limit for DuckDB")
    threads: Optional[int] = Field(default=None, description="Number of threads for DuckDB")


class DuckDBConnection:
    """
    A connection manager for DuckDB databases.

    This connection supports:
    - Local DuckDB files
    - In-memory databases
    - Thread-safe operations
    - Automatic retry on transient failures

    Example:
        >>> config = ConnectionConfig(database="data/analytics.duckdb")
        >>> conn = DuckDBConnection(config)
        >>> df = conn.query("SELECT * FROM dim_scenario LIMIT 10")
        >>> conn.close()
    """

    _instance: Optional[duckdb.DuckDBPyConnection] = None
    _lock: Lock = Lock()
    _query_cache: dict = {}
    _cache_ttl: dict = {}

    def __init__(
        self,
        config: Optional[ConnectionConfig] = None,
        database: Optional[str] = None,
        read_only: bool = True,
    ):
        """
        Initialize DuckDB connection.

        Args:
            config: ConnectionConfig object with database settings
            database: Path to database file (overrides config)
            read_only: Open in read-only mode (overrides config)
        """
        if config:
            self._config = config
        else:
            db_path = database or os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
            self._config = ConnectionConfig(database=db_path, read_only=read_only)

        self._instance = None

    @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
    def _connect(self) -> duckdb.DuckDBPyConnection:
        """
        Connect to DuckDB database with retry logic.

        Returns:
            DuckDB connection object

        Raises:
            DatabaseConnectionError: If connection fails after retries
        """
        db = self._config.database

        # Validate database file exists (if not in-memory or MotherDuck)
        if db != ":memory:" and not db.startswith("md:") and not Path(db).exists():
            raise FileNotFoundError(f"Database file not found: {db}")

        # Build connection kwargs
        kwargs = {"read_only": self._config.read_only}
        if self._config.memory_limit:
            kwargs["config"] = {"memory_limit": self._config.memory_limit}
        if self._config.threads:
            kwargs.setdefault("config", {})["threads"] = self._config.threads

        try:
            return duckdb.connect(database=db, **kwargs)
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to DuckDB at {db}: {e}") from e

    def connect(self) -> "DuckDBConnection":
        """
        Establish database connection.

        Returns:
            Self for method chaining
        """
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._connect()
        return self

    def cursor(self) -> duckdb.DuckDBPyConnection:
        """
        Return a cursor (DuckDB connections are their own cursors).

        Returns:
            DuckDB connection object
        """
        if self._instance is None:
            self.connect()
        return self._instance

    def query(self, query: str, ttl: Optional[int] = 3600, use_cache: bool = True, **kwargs) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query to execute
            ttl: Time-to-live for cached results in seconds (default: 3600)
            use_cache: Whether to use query caching (default: True)
            **kwargs: Additional parameters to pass to the query

        Returns:
            pd.DataFrame: Query results

        Raises:
            ValueError: If query fails security validation
        """
        # Validate query security before execution
        DatabaseSecurity.validate_query_safety(query)

        # Check cache
        cache_key = (query, tuple(sorted(kwargs.items())))
        current_time = time.time()

        if use_cache and cache_key in self._query_cache:
            cached_time = self._cache_ttl.get(cache_key, 0)
            if current_time - cached_time < (ttl or 3600):
                return self._query_cache[cache_key].copy()

        # Execute query
        cursor = self.cursor()
        if kwargs:
            params = list(kwargs.values())
            result = cursor.execute(query, params)
        else:
            result = cursor.execute(query)

        df = result.df()

        # Cache result
        if use_cache and ttl:
            self._query_cache[cache_key] = df.copy()
            self._cache_ttl[cache_key] = current_time

        return df

    def query_with_result(self, query: str, ttl: Optional[int] = 3600) -> QueryResult:
        """
        Execute a query and return a QueryResult object with metadata.

        Args:
            query: SQL query to execute
            ttl: Time-to-live for cached results in seconds

        Returns:
            QueryResult: Query results with metadata

        Raises:
            ValueError: If query fails security validation
        """
        try:
            # Validate query security before execution
            DatabaseSecurity.validate_query_safety(query)

            # Validate SQL query
            sql_obj = SQLQuery(sql=query)

            # Execute query with timing
            start_time = time.time()
            df = self.query(sql_obj.sql, ttl=ttl)
            execution_time = time.time() - start_time

            return QueryResult(success=True, data=df, execution_time=execution_time, query=sql_obj.sql)
        except ValueError as e:
            return QueryResult(success=False, error=f"SQL validation error: {str(e)}", query=query)
        except (duckdb.Error, duckdb.CatalogException, duckdb.SyntaxException) as e:
            return QueryResult(success=False, error=f"Database error: {str(e)}", query=query)
        except Exception as e:
            wrapped_error = wrap_exception(e, "Query execution")
            return QueryResult(success=False, error=str(wrapped_error), query=query)

    def execute(self, query: str, **kwargs) -> None:
        """
        Execute a query without returning results.

        Args:
            query: SQL query to execute
            **kwargs: Additional parameters to pass to the query
        """
        cursor = self.cursor()
        if kwargs:
            params = list(kwargs.values())
            cursor.execute(query, params)
        else:
            cursor.execute(query)

    def get_table_info(self, table_name: str, ttl: int = 3600) -> pd.DataFrame:
        """
        Get information about a table's columns.

        Args:
            table_name: Name of the table
            ttl: Cache time-to-live in seconds

        Returns:
            pd.DataFrame: Table schema information
        """
        DatabaseSecurity.validate_table_name(table_name)
        query = f"DESCRIBE {table_name}"
        return self.query(query, ttl=ttl)

    def list_tables(self, ttl: int = 3600) -> pd.DataFrame:
        """
        List all tables in the database.

        Args:
            ttl: Cache time-to-live in seconds

        Returns:
            pd.DataFrame: List of tables
        """
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
        """
        return self.query(query, ttl=ttl)

    def get_row_count(self, table_name: str, ttl: int = 300) -> int:
        """
        Get the row count for a table.

        Args:
            table_name: Name of the table
            ttl: Cache time-to-live in seconds (default: 300)

        Returns:
            int: Number of rows in the table
        """
        DatabaseSecurity.validate_table_name(table_name)
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.query(query, ttl=ttl)
        return result["count"].iloc[0]

    def health_check(self) -> bool:
        """
        Check if the connection is healthy.

        Returns:
            bool: True if connection is healthy
        """
        try:
            self.query("SELECT 1", ttl=0, use_cache=False)
            return True
        except Exception:
            return False

    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self._query_cache.clear()
        self._cache_ttl.clear()

    def close(self) -> None:
        """Close the database connection."""
        if self._instance is not None:
            with self._lock:
                if self._instance is not None:
                    self._instance.close()
                    self._instance = None

    def __enter__(self) -> "DuckDBConnection":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
