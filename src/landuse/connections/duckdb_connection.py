#!/usr/bin/env python3
"""
Custom DuckDB Connection for Streamlit
Implements st.connection pattern for efficient database access
"""

try:
    from streamlit.connections import BaseConnection
    from streamlit.runtime.caching import cache_data
    HAS_STREAMLIT = True
except ImportError:
    # For testing environments where streamlit might not be fully available
    from typing import Generic, TypeVar
    T = TypeVar('T')
    class BaseConnection(Generic[T]):
        def __init__(self, connection_name: str, **kwargs):
            self.connection_name = connection_name
            self._secrets = None
            self._instance = None
    def cache_data(ttl=None):
        def decorator(func):
            return func
        return decorator
    HAS_STREAMLIT = False
import duckdb
import pandas as pd
from typing import Optional, Dict, Any, List
import os
from pathlib import Path
from pydantic import BaseModel, Field

from ..models import QueryResult, SQLQuery
from ..utils.retry_decorators import database_retry, network_retry


class ConnectionConfig(BaseModel):
    """Configuration for DuckDB connection"""
    database: str = Field(
        default="data/processed/landuse_analytics.duckdb",
        description="Path to DuckDB file or ':memory:'"
    )
    read_only: bool = Field(
        default=True,
        description="Open in read-only mode"
    )
    memory_limit: Optional[str] = Field(
        default=None,
        description="Memory limit for DuckDB"
    )
    threads: Optional[int] = Field(
        default=None,
        description="Number of threads for DuckDB"
    )


class DuckDBConnection(BaseConnection[duckdb.DuckDBPyConnection]):
    """
    A Streamlit connection implementation for DuckDB databases.
    
    This connection supports:
    - Local DuckDB files
    - In-memory databases
    - Automatic caching of query results
    - Thread-safe operations
    """
    
    @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
    def _connect(self, **kwargs) -> duckdb.DuckDBPyConnection:
        """
        Connect to DuckDB database with retry logic.
        
        Parameters from kwargs or secrets:
        - database: Path to DuckDB file or ':memory:' for in-memory database
        - read_only: Whether to open in read-only mode (default: True)
        """
        # Get database path from kwargs or secrets
        if 'database' in kwargs:
            db = kwargs.pop('database')
        elif hasattr(self, '_secrets') and self._secrets:
            if hasattr(self._secrets, 'database'):
                db = self._secrets.database
            elif hasattr(self._secrets, '__getitem__'):
                try:
                    db = self._secrets['database']
                except (KeyError, TypeError):
                    db = None
            else:
                db = None
            
            if not db:
                db = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        else:
            # Default to environment variable or standard path
            db = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        
        # Get read_only setting
        read_only = kwargs.pop('read_only', True)
        
        # Validate database file exists (if not in-memory)
        if db != ':memory:' and not Path(db).exists():
            raise FileNotFoundError(f"Database file not found: {db}")
        
        # Connect to DuckDB with potential retries for connection issues
        try:
            return duckdb.connect(database=db, read_only=read_only, **kwargs)
        except Exception as e:
            # Add context to connection errors
            raise ConnectionError(f"Failed to connect to DuckDB at {db}: {e}") from e
    
    def cursor(self) -> duckdb.DuckDBPyConnection:
        """Return a cursor (DuckDB connections are their own cursors)"""
        return self._instance
    
    def query(self, query: str, ttl: Optional[int] = 3600, **kwargs) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.
        
        Args:
            query: SQL query to execute
            ttl: Time-to-live for cached results in seconds (default: 3600)
            **kwargs: Additional parameters to pass to the query
            
        Returns:
            pd.DataFrame: Query results
        """
        @cache_data(ttl=ttl)
        def _query(query: str, **kwargs) -> pd.DataFrame:
            cursor = self.cursor()
            if kwargs:
                # DuckDB uses positional parameters ($1, $2, etc.)
                # Convert kwargs to list in the order they appear
                params = list(kwargs.values())
                result = cursor.execute(query, params)
            else:
                # Execute without parameters
                result = cursor.execute(query)
            return result.df()
        
        return _query(query, **kwargs)
    
    def query_with_result(self, query: str, ttl: Optional[int] = 3600) -> QueryResult:
        """
        Execute a query and return a QueryResult object with metadata.
        
        Args:
            query: SQL query to execute
            ttl: Time-to-live for cached results in seconds
            
        Returns:
            QueryResult: Query results with metadata
        """
        import time
        
        try:
            # Validate SQL query
            sql_obj = SQLQuery(sql=query)
            
            # Execute query with timing
            start_time = time.time()
            df = self.query(sql_obj.sql, ttl=ttl)
            execution_time = time.time() - start_time
            
            # Create QueryResult
            return QueryResult(
                success=True,
                data=df,
                execution_time=execution_time,
                query=sql_obj.sql
            )
        except ValueError as e:
            # SQL validation error
            return QueryResult(
                success=False,
                error=f"SQL validation error: {str(e)}",
                query=query
            )
        except Exception as e:
            # Other errors
            return QueryResult(
                success=False,
                error=str(e),
                query=query
            )
    
    def execute(self, query: str, **kwargs) -> None:
        """
        Execute a query without returning results.
        Useful for DDL statements or updates.
        
        Args:
            query: SQL query to execute
            **kwargs: Additional parameters to pass to the query
        """
        cursor = self.cursor()
        if kwargs:
            # DuckDB uses positional parameters ($1, $2, etc.)
            # Convert kwargs to list in the order they appear
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
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.query(query, ttl=ttl)
        return result['count'].iloc[0]
    
    def health_check(self) -> bool:
        """
        Check if the connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            self.query("SELECT 1", ttl=0)
            return True
        except Exception:
            return False