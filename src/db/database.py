"""
Database connection module for RPA land use viewer.
"""

import os
import logging
import contextlib
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'database_path': os.getenv('DB_PATH', 'data/database/rpa.db')
}

class DBManager:
    """
    A simplified database manager for DuckDB connections with connection pooling.
    
    This class provides methods for working with the database:
    - context manager for connections
    - pandas DataFrame query support
    - standardized error handling
    """
    
    _pool = None
    
    @classmethod
    def _ensure_db_exists(cls) -> str:
        """Ensure database directory exists and return absolute path."""
        db_path = DB_CONFIG['database_path']
        path_obj = Path(db_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        return str(path_obj.absolute())
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool or create a new one."""
        try:
            import duckdb
            db_path = cls._ensure_db_exists()
            connection = duckdb.connect(db_path)
            # Set the number of threads for concurrent processing
            connection.execute("SET threads=4")
            return connection
        except Exception as err:
            logger.error(f"Error connecting to DuckDB: {err}")
            raise
    
    @classmethod
    @contextlib.contextmanager
    def connection(cls):
        """Context manager for database connections."""
        conn = None
        try:
            conn = cls.get_connection()
            yield conn
        except Exception as err:
            logger.error(f"Database operation failed: {err}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
    
    @classmethod
    def query_df(cls, query: str, params: Optional[list] = None):
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        Args:
            query: SQL query with ? placeholders
            params: List of parameters for the query
            
        Returns:
            pandas.DataFrame: Query results
        """
        import pandas as pd
        
        with cls.connection() as conn:
            try:
                if params:
                    result = conn.execute(query, params).fetchdf()
                else:
                    result = conn.execute(query).fetchdf()
                return result
            except Exception as err:
                logger.error(f"Query failed: {err}")
                logger.debug(f"Query: {query}")
                logger.debug(f"Params: {params}")
                return pd.DataFrame()
    
    @classmethod
    def execute(cls, query: str, params: Optional[list] = None) -> Any:
        """
        Execute a SQL query and return raw results.
        
        Args:
            query: SQL query with ? placeholders
            params: List of parameters for the query
            
        Returns:
            Query results
        """
        with cls.connection() as conn:
            try:
                if params:
                    return conn.execute(query, params).fetchall()
                else:
                    return conn.execute(query).fetchall()
            except Exception as err:
                logger.error(f"Query execution failed: {err}")
                logger.debug(f"Query: {query}")
                logger.debug(f"Params: {params}")
                return [] 