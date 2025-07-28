"""Query execution functionality extracted from monolithic agent class."""

from typing import Any, Dict

import duckdb
import pandas as pd
from rich.console import Console

from landuse.agents.formatting import clean_sql_query, format_query_results
from landuse.config.landuse_config import LanduseConfig
from landuse.exceptions import DatabaseError, QueryValidationError, wrap_exception
from landuse.security.database_security import DatabaseSecurity


class QueryExecutor:
    """
    Handles SQL query execution and error management.
    
    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Provides standardized query execution with error handling and result formatting.
    """

    def __init__(self, config: LanduseConfig, db_connection: duckdb.DuckDBPyConnection, console: Console = None):
        """
        Initialize query executor.
        
        Args:
            config: Configuration object
            db_connection: Database connection
            console: Rich console for logging (optional)
        """
        self.config = config
        self.db_connection = db_connection
        self.console = console or Console()

    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a SQL query with standard error handling and formatting.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            Dictionary with execution results including success status, data, and formatting
        """
        cleaned_query = clean_sql_query(query)
        
        if self.config.debug:
            print(f"\nDEBUG execute_query: Executing SQL query")
            print(f"DEBUG execute_query: Query: {cleaned_query}")

        try:
            # Validate query security before execution
            DatabaseSecurity.validate_query_safety(cleaned_query)
            
            # Add row limit if not present for safety
            if "limit" not in cleaned_query.lower():
                cleaned_query = f"{cleaned_query.rstrip(';')} LIMIT {self.config.max_query_rows}"

            result = self.db_connection.execute(cleaned_query).fetchall()
            columns = [desc[0] for desc in self.db_connection.description] if self.db_connection.description else []
            
            if self.config.debug:
                print(f"DEBUG execute_query: Result row count: {len(result)}")
                print(f"DEBUG execute_query: Columns: {columns}")
                if result and len(result) > 0:
                    print(f"DEBUG execute_query: First row: {result[0]}")
                else:
                    print("DEBUG execute_query: No rows returned")

            # Convert to DataFrame for formatting
            df = pd.DataFrame(result, columns=columns)
            
            # Format results
            formatted_results = format_query_results(df, cleaned_query)

            return {
                "success": True,
                "query": cleaned_query,
                "results": result,
                "columns": columns,
                "formatted": formatted_results,
                "row_count": len(result)
            }

        except (duckdb.Error, duckdb.CatalogException, duckdb.SyntaxException, duckdb.BinderException) as e:
            error_msg = str(e)
            suggestion = self._get_error_suggestion(error_msg)
            
            if self.config.debug:
                print(f"DEBUG execute_query: DuckDB Error: {error_msg}")
                print(f"DEBUG execute_query: Suggestion: {suggestion}")

            return {
                "success": False,
                "query": cleaned_query,
                "error": f"Database error: {error_msg}",
                "suggestion": suggestion
            }
        except ValueError as e:
            # Security validation or other validation errors
            error_msg = str(e)
            if self.config.debug:
                print(f"DEBUG execute_query: Validation Error: {error_msg}")

            return {
                "success": False,
                "query": cleaned_query,
                "error": f"Query validation error: {error_msg}",
                "suggestion": "Check query syntax and security requirements"
            }
        except Exception as e:
            # Wrap other unexpected errors
            wrapped_error = wrap_exception(e, "Query execution")
            error_msg = str(wrapped_error)
            
            if self.config.debug:
                print(f"DEBUG execute_query: Unexpected Error: {error_msg}")
                import traceback
                traceback.print_exc()

            return {
                "success": False,
                "query": cleaned_query,
                "error": f"Unexpected error: {error_msg}",
                "suggestion": "Contact support if this persists"
            }

    def _get_error_suggestion(self, error_msg: str) -> str:
        """
        Get helpful suggestions for common SQL errors.
        
        Args:
            error_msg: The error message from query execution
            
        Returns:
            Human-readable suggestion for fixing the error
        """
        error_lower = error_msg.lower()

        if "no such column" in error_lower or "could not find column" in error_lower:
            return "Check column names in the schema. Use exact column names from the database schema."
        elif "no such table" in error_lower:
            return "Check table names. Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time"
        elif "syntax error" in error_lower:
            return "Check SQL syntax. Common issues: missing commas, unclosed quotes, invalid keywords."
        elif "ambiguous column" in error_lower:
            return "Specify table name for columns used in joins (e.g., fact.year instead of just year)"
        else:
            return "Check the query syntax and ensure all table/column names match the schema exactly."