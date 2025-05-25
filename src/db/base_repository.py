"""
Base repository for database operations.

This module provides a foundation for all other repositories 
to access the database with consistent patterns.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from .database import DBManager

logger = logging.getLogger(__name__)

class BaseRepository:
    """
    Base repository class to standardize database access patterns.
    
    This provides common methods for all repositories to use when
    accessing the database, ensuring consistent error handling,
    connection management, and return formats.
    """
    
    @classmethod
    def execute_query(cls, query: str, params: Optional[List] = None) -> List[tuple]:
        """
        Execute a query and return the raw results.
        
        Args:
            query: SQL query string with ? placeholders
            params: List of parameter values
            
        Returns:
            List of result tuples
        """
        return DBManager.execute(query, params)
    
    @classmethod
    def query_to_df(cls, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.
        
        Args:
            query: SQL query string with ? placeholders
            params: List of parameter values
            
        Returns:
            pandas DataFrame with results
        """
        return DBManager.query_df(query, params)
    
    @classmethod
    def get_single_value(cls, query: str, params: Optional[List] = None) -> Any:
        """
        Get a single scalar value from a query.
        
        Args:
            query: SQL query string with ? placeholders
            params: List of parameter values
            
        Returns:
            Single scalar value or None
        """
        results = cls.execute_query(query, params)
        if results and len(results) > 0 and len(results[0]) > 0:
            return results[0][0]
        return None
    
    @classmethod
    def get_single_row(cls, query: str, params: Optional[List] = None) -> Optional[Dict[str, Any]]:
        """
        Get a single row as a dictionary.
        
        Args:
            query: SQL query string with ? placeholders
            params: List of parameter values
            
        Returns:
            Row as dictionary or None
        """
        df = cls.query_to_df(query, params)
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    
    @classmethod
    def check_exists(cls, query: str, params: Optional[List] = None) -> bool:
        """
        Check if records exist matching the query.
        
        Args:
            query: SQL query string with ? placeholders
            params: List of parameter values
            
        Returns:
            True if records exist, False otherwise
        """
        value = cls.get_single_value(query, params)
        return value is not None
    
    @classmethod
    def execute_script(cls, sql_script: str) -> None:
        """
        Execute a multi-statement SQL script.
        
        Args:
            sql_script: SQL script with multiple statements
        """
        with DBManager.connection() as conn:
            try:
                conn.execute(sql_script)
            except Exception as e:
                logger.error(f"Error executing SQL script: {e}")
                raise 