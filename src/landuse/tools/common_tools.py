"""Common tools shared across landuse agents."""

from typing import Any, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from landuse.agents.formatting import clean_sql_query, format_query_results
from landuse.config.landuse_config import LanduseConfig
import duckdb
from landuse.utils.retry_decorators import database_retry


class QueryInput(BaseModel):
    """Input model for SQL query execution."""
    query: str = Field(description="SQL query to execute against the landuse database")


def create_execute_query_tool(
    config: LanduseConfig,
    db_connection: duckdb.DuckDBPyConnection,
    schema: str
) -> Any:
    """
    Create a tool for executing SQL queries with consistent error handling.

    Args:
        config: Configuration object
        db_connection: Database connection instance
        schema: Database schema information

    Returns:
        Configured tool function
    """

    @tool(args_schema=QueryInput)
    def execute_landuse_query(query: str) -> str:
        """
        Execute a SQL query against the landuse database.

        The database contains:
        - fact_landuse_transitions: Land use changes by county, year, and scenario
        - dim_scenario: Climate scenario details (RCP45/85, SSP1-5)
        - dim_geography: County and state information
        - dim_landuse: Land use categories (crop, pasture, forest, urban, rangeland)
        - dim_time: Time periods from 2012 to 2100

        Args:
            query: SQL query to execute

        Returns:
            Query results as formatted string or error message
        """
        cleaned_query = clean_sql_query(query)

        try:
            # Apply row limit if not present
            if "limit" not in cleaned_query.lower():
                cleaned_query = f"{cleaned_query.rstrip(';')} LIMIT {config.max_query_rows}"

            # Execute query with retry logic
            result = _execute_with_retry(db_connection, cleaned_query)

            if result["success"]:
                return _format_success_response(result, config)
            else:
                return _format_error_response(result, schema)

        except Exception as e:
            return f"Error executing query: {str(e)}"

    return execute_landuse_query


@database_retry(max_attempts=3)
def _execute_with_retry(db_connection: duckdb.DuckDBPyConnection, query: str) -> dict[str, Any]:
    """Execute query with retry logic."""
    try:
        conn = db_connection
        result = conn.execute(query).fetchall()
        columns = [desc[0] for desc in conn.description] if conn.description else []

        return {
            "success": True,
            "results": result,
            "columns": columns,
            "row_count": len(result)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


def _format_success_response(result: dict[str, Any], config: LanduseConfig) -> str:
    """Format successful query results."""
    formatted = format_query_results(result["results"], result["columns"])

    # Add row count information if truncated
    if result["row_count"] >= config.max_query_rows:
        formatted += f"\n\n(Note: Results limited to {config.max_query_rows} rows)"

    return formatted


def _format_error_response(result: dict[str, Any], schema: str) -> str:
    """Format error response with helpful suggestions."""
    error_msg = result["error"]
    suggestion = _get_error_suggestion(error_msg)

    response = f"Error: {error_msg}\n\nSuggestion: {suggestion}"

    # Add schema hint for column/table errors
    if "column" in error_msg.lower() or "table" in error_msg.lower():
        response += f"\n\nAvailable schema:\n{schema[:500]}..."

    return response


def _get_error_suggestion(error_msg: str) -> str:
    """Get helpful suggestions for common SQL errors."""
    error_lower = error_msg.lower()

    suggestions = {
        "no such column": "Check column names in the schema. Use exact column names.",
        "could not find column": "Verify column exists in the specified table.",
        "no such table": "Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time",
        "syntax error": "Check SQL syntax. Common issues: missing commas, unclosed quotes.",
        "ambiguous column": "Specify table name for columns (e.g., fact.year instead of year)",
        "division by zero": "Add WHERE clause to filter out zero values.",
        "timeout": "Query may be too complex. Try adding filters or limiting results."
    }

    for key, suggestion in suggestions.items():
        if key in error_lower:
            return suggestion

    return "Check query syntax and ensure table/column names match schema exactly."


def create_analysis_tool() -> Any:
    """
    Create a tool for analyzing query results and providing insights.

    Returns:
        Configured analysis tool
    """

    @tool
    def analyze_landuse_results(
        query_results: str,
        original_question: str,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Analyze landuse query results and provide business insights.

        This tool helps interpret raw SQL results in the context of:
        - Land use transitions and trends
        - Climate scenario impacts
        - Geographic patterns
        - Policy implications

        Args:
            query_results: The raw query results to analyze
            original_question: The original user question for context
            additional_context: Any additional context for analysis

        Returns:
            Analysis and insights based on the results
        """
        insights = []

        # Parse key patterns from results
        if "urban" in query_results.lower() and "increase" in original_question.lower():
            insights.append(
                "Urban expansion typically comes at the expense of agricultural and forest lands. "
                "The model shows development is irreversible - once land becomes urban, it stays urban."
            )

        if "forest" in query_results.lower() and "loss" in original_question.lower():
            insights.append(
                "Forest loss is a critical indicator of environmental change. "
                "Historically, ~46% of new developed land comes from forest conversion."
            )

        if "rcp85" in query_results.lower() or "ssp5" in query_results.lower():
            insights.append(
                "High-emission scenarios (RCP85/SSP5) generally show more dramatic land use changes "
                "due to increased pressure on natural resources and agricultural systems."
            )

        if "agricultural" in query_results.lower() or "crop" in query_results.lower():
            insights.append(
                "Agricultural land changes reflect both climate impacts and socioeconomic factors. "
                "Consider both cropland and pasture when analyzing total agricultural impact."
            )

        # Add geographic context if present
        if any(state in query_results.lower() for state in ["california", "texas", "florida"]):
            insights.append(
                "Large states show significant variation at the county level. "
                "Consider disaggregating to county-level analysis for more detailed insights."
            )

        # Combine insights
        if insights:
            return "\n\n".join(["Key Insights:"] + [f"• {insight}" for insight in insights])
        else:
            return "Results show the requested data. Consider examining trends over time or comparing scenarios for deeper insights."

    return analyze_landuse_results


def create_schema_tool(schema: str) -> Any:
    """
    Create a tool for exploring database schema.

    Args:
        schema: Database schema information

    Returns:
        Configured schema exploration tool
    """

    @tool
    def explore_landuse_schema(table_name: Optional[str] = None) -> str:
        """
        Explore the landuse database schema.

        Args:
            table_name: Optional specific table to explore in detail

        Returns:
            Schema information
        """
        if table_name:
            # Extract schema for specific table
            lines = schema.split('\n')
            table_schema = []
            capturing = False

            for line in lines:
                if f"Table: {table_name}" in line:
                    capturing = True
                    table_schema.append(line)
                elif capturing and line.startswith("Table:"):
                    break
                elif capturing:
                    table_schema.append(line)

            if table_schema:
                return "\n".join(table_schema)
            else:
                return f"Table '{table_name}' not found. Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time"
        else:
            return schema

    return explore_landuse_schema
