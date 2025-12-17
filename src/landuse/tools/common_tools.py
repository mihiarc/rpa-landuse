"""Common tools shared across landuse agents."""

from typing import Any, Optional

import duckdb
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from landuse.agents.formatting import clean_sql_query, format_raw_query_results
from landuse.agents.response_formatter import ResponseFormatter
from landuse.core.app_config import AppConfig
from landuse.exceptions import (
    DatabaseError,
    QueryValidationError,
    SecurityError,
    handle_query_error,
    wrap_exception,
)
from landuse.utils.retry_decorators import database_retry


class QueryInput(BaseModel):
    """Input model for SQL query execution."""
    query: str = Field(description="SQL query to execute against the landuse database")


def create_execute_query_tool(
    config: AppConfig,
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
        - dim_geography: County and state information with enhanced metadata
        - fact_socioeconomic_projections: Population and income projections by SSP scenario
        - dim_socioeconomic: SSP scenario narratives and characteristics
        - dim_indicators: Socioeconomic indicator definitions
        - dim_landuse: Land use categories (crop, pasture, forest, urban, rangeland)
        - dim_time: Time periods from 2012 to 2100
        
        RECOMMENDED VIEWS (use these first for socioeconomic analysis):
        - v_population_trends: Easy population analysis by county/state/scenario
        - v_income_trends: Easy income analysis by county/state/scenario
        - v_scenarios_combined: Combined scenario and socioeconomic information

        Args:
            query: SQL query to execute

        Returns:
            Query results as formatted string or error message
        """
        cleaned_query = clean_sql_query(query)

        try:
            # Apply row limit if not present
            if "limit" not in cleaned_query.lower():
                cleaned_query = f"{cleaned_query.rstrip(';')} LIMIT {config.agent.max_query_rows}"

            # Execute query with retry logic
            result = _execute_with_retry(db_connection, cleaned_query)

            if result["success"]:
                return _format_success_response(result, config)
            else:
                return _format_error_response(result, schema)

        except (duckdb.CatalogException, duckdb.SyntaxException, duckdb.BinderException) as e:
            # Database-specific errors with helpful suggestions
            error_response = handle_query_error(e, cleaned_query, "Query execution")
            return f"Error: {error_response['error']}\n\nSuggestion: {error_response['suggestion']}"
        except (SecurityError, QueryValidationError) as e:
            # Security or validation errors
            return f"Query blocked: {e.message}\n\nSuggestion: Only SELECT queries are allowed."
        except duckdb.Error as e:
            # Other DuckDB errors
            error_response = handle_query_error(e, cleaned_query, "Database error")
            return f"Database error: {error_response['error']}\n\nSuggestion: {error_response['suggestion']}"
        except Exception as e:
            # Wrap unexpected errors
            wrapped = wrap_exception(e, "Query execution")
            return f"Error: {wrapped.message}"

    return execute_landuse_query


@database_retry(max_attempts=3)
def _execute_with_retry(db_connection: duckdb.DuckDBPyConnection, query: str) -> dict[str, Any]:
    """Execute query with retry logic.

    Args:
        db_connection: Active DuckDB connection
        query: SQL query to execute

    Returns:
        dict with 'success', 'results', 'columns', 'row_count' on success
        dict with 'success', 'error', 'query', 'error_type' on failure
    """
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
    except (duckdb.CatalogException, duckdb.SyntaxException, duckdb.BinderException) as e:
        # Schema/syntax errors - don't retry these
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "error_type": "schema"
        }
    except duckdb.Error as e:
        # Other DuckDB errors - may be transient
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "error_type": "database"
        }
    except Exception as e:
        # Unexpected errors
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "error_type": "unexpected"
        }


def _format_success_response(result: dict[str, Any], config: AppConfig) -> str:
    """Format successful query results with user-friendly scenario names."""
    formatted = format_raw_query_results(result["results"], result["columns"])

    # Replace technical scenario names with user-friendly names in the formatted output
    # This ensures users see "LM (Lower-Moderate)" instead of "RCP45_SSP1"
    formatted = ResponseFormatter.format_scenario_in_text(formatted, format='full')

    # Add row count information if truncated
    if result["row_count"] >= config.agent.max_query_rows:
        formatted += f"\n\n(Note: Results limited to {config.agent.max_query_rows} rows)"

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
        "no such table": "Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time, fact_socioeconomic_projections, dim_socioeconomic, dim_indicators",
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

        # Enhanced socioeconomic insights
        if "population" in query_results.lower():
            if "thousands" in query_results.lower():
                insights.append(
                    "Population values are in thousands (e.g., 1,000 = 1 million people). "
                    "Population growth drives urban development and agricultural land conversion. "
                    "SSP5 typically shows the highest growth, SSP3 the most constrained."
                )
            if "growth" in original_question.lower() or "change" in original_question.lower():
                insights.append(
                    "Population projections should be analyzed from current 2025 baseline levels. "
                    "SSP scenarios show different growth paths: "
                    "SSP1 (Sustainability) = moderate growth, SSP2 (Middle Road) = business-as-usual, "
                    "SSP3 (Regional Rivalry) = slower growth, SSP5 (Fossil Development) = rapid growth. "
                    "Use 2025 as baseline unless historical context is specifically requested."
                )

        if "income" in query_results.lower():
            if "per_capita" in query_results.lower() or "capita" in query_results.lower():
                insights.append(
                    "Income values are per capita in constant 2009 USD thousands. "
                    "Multiply by 1,000 for actual dollar amounts (e.g., 45.5 = $45,500 per person). "
                    "Higher income areas typically experience more urban development pressure."
                )
            if "economic" in original_question.lower() or "trend" in original_question.lower():
                insights.append(
                    "Income growth patterns vary significantly by SSP scenario and reflect different "
                    "economic development pathways. Higher income growth often correlates with land use intensification."
                )

        if "demographic" in original_question.lower() or "socioeconomic" in original_question.lower():
            insights.append(
                "Demographic trends directly drive land use changes. Population and income growth "
                "create demand for housing, infrastructure, and services, leading to agricultural and forest land conversion."
            )

        if "ssp" in query_results.lower():
            insights.append(
                "SSP scenarios represent different socioeconomic pathways: "
                "SSP1 (Sustainability), SSP2 (Middle Road), SSP3 (Regional Rivalry), SSP5 (Fossil Development). "
                "Each scenario has distinct population, economic, and urbanization trends."
            )

        if "correlation" in original_question.lower() or "relationship" in original_question.lower():
            insights.append(
                "Consider analyzing both direct correlations (population vs. urban growth) and "
                "indirect relationships (income growth driving agricultural intensification)."
            )

        # Add geographic context if present
        if any(state in query_results.lower() for state in ["california", "texas", "florida", "north carolina"]):
            insights.append(
                "Large states show significant variation at the county level. "
                "Consider disaggregating to county-level analysis for more detailed insights."
            )

        # Cross-dataset recommendations - suggest related queries
        cross_dataset_suggestions = []
        
        if "population" in query_results.lower() and "urban" not in query_results.lower():
            cross_dataset_suggestions.append(
                "RECOMMENDATION: Query urban land transitions to see how population growth drives development: "
                "SELECT scenario_name, SUM(acres) FROM fact_landuse_transitions WHERE to_landuse_name = 'Urban'"
            )
        
        if "urban" in query_results.lower() and "population" not in query_results.lower():
            cross_dataset_suggestions.append(
                "RECOMMENDATION: Query population projections to understand demographic drivers: "
                "SELECT ssp_scenario, population_thousands FROM v_population_trends"
            )
            
        if "forest" in query_results.lower() and "population" not in query_results.lower():
            cross_dataset_suggestions.append(
                "RECOMMENDATION: Query population growth to understand development pressure on forests: "
                "Population growth often drives forest conversion to urban/agricultural uses"
            )
            
        if "agricultural" in query_results.lower() and "income" not in query_results.lower():
            cross_dataset_suggestions.append(
                "RECOMMENDATION: Query income trends to understand agricultural economic drivers: "
                "SELECT ssp_scenario, income_per_capita_2009usd FROM v_income_trends"
            )

        # State-specific recommendations
        if "north carolina" in query_results.lower():
            if "population" in query_results.lower() and "land" not in original_question.lower():
                cross_dataset_suggestions.append(
                    "FOLLOW-UP: Query NC urban expansion patterns: "
                    "SELECT scenario_name, SUM(acres) as urban_acres FROM fact_landuse_transitions f "
                    "JOIN dim_scenario s ON f.scenario_id = s.scenario_id "
                    "JOIN dim_geography g ON f.geography_id = g.geography_id "
                    "JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id "
                    "WHERE g.state_name = 'North Carolina' AND tl.landuse_name = 'Urban' GROUP BY scenario_name"
                )

        # Combine all insights and recommendations
        all_content = []
        if insights:
            all_content.append("Key Insights:")
            all_content.extend([f"• {insight}" for insight in insights])
        
        if cross_dataset_suggestions:
            if all_content:
                all_content.append("")  # Add blank line
            all_content.append("Suggested Related Queries:")
            all_content.extend([f"• {suggestion}" for suggestion in cross_dataset_suggestions])

        if all_content:
            return "\n\n".join(all_content)
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
                return f"Table '{table_name}' not found. Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time, fact_socioeconomic_projections, dim_socioeconomic, dim_indicators"
        else:
            return schema

    return explore_landuse_schema


def create_socioeconomic_analysis_tool() -> Any:
    """
    Create a tool for analyzing socioeconomic projections and correlations.

    Returns:
        Configured socioeconomic analysis tool
    """

    @tool
    def analyze_socioeconomic_trends(
        query_results: str,
        analysis_type: str,
        original_question: str,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Analyze socioeconomic projections and their relationship to land use changes.

        This tool provides specialized analysis for:
        - Population growth trends and drivers
        - Income and economic development patterns
        - SSP scenario comparisons
        - Demographic-landuse correlations
        - Economic drivers of land conversion

        Args:
            query_results: The socioeconomic query results to analyze
            analysis_type: Type of analysis (population, income, correlation, etc.)
            original_question: The original user question for context
            additional_context: Any additional context for analysis

        Returns:
            Analysis and insights specific to socioeconomic trends
        """
        insights = []

        # Population-specific analysis
        if "population" in analysis_type.lower():
            insights.append(
                "Population projections follow SSP narrative pathways. SSP3 shows highest growth "
                "due to regional rivalry and slower demographic transition, while SSP1 shows "
                "lower growth with rapid development and education improvements."
            )

            if "growth" in query_results.lower() or "increase" in query_results.lower():
                insights.append(
                    "Population growth drives land development pressure. Fast-growing counties "
                    "typically experience more forest-to-urban and agricultural-to-urban transitions."
                )

        # Income-specific analysis
        if "income" in analysis_type.lower():
            insights.append(
                "Income projections reflect economic development pathways. SSP5 shows highest "
                "per capita income growth due to fossil-fueled development, while SSP3 shows "
                "slower income growth due to regional conflicts and inequality."
            )

            if "per capita" in query_results.lower():
                insights.append(
                    "Per capita income (in constant 2009 USD) accounts for inflation. Rising income "
                    "typically correlates with increased urban development and agricultural intensification."
                )

        # Correlation analysis
        if "correlation" in analysis_type.lower() or "relationship" in analysis_type.lower():
            insights.append(
                "Key correlations to examine: (1) Population growth → Urban expansion, "
                "(2) Income growth → Agricultural intensification, (3) Economic development → Forest loss, "
                "(4) Urbanization → Infrastructure development."
            )

            insights.append(
                "Consider time lags between socioeconomic changes and land use responses. "
                "Population growth may precede urban development by 5-10 years."
            )

        # SSP scenario context
        if any(ssp in query_results.lower() for ssp in ["ssp1", "ssp2", "ssp3", "ssp5"]):
            insights.append(
                "SSP Scenario Context:\n"
                "• SSP1 (Sustainability): Low population growth, medium-high income, sustainable development\n"
                "• SSP2 (Middle Road): Medium population/income growth, gradual progress\n"
                "• SSP3 (Regional Rivalry): High population growth, low income growth, fragmented development\n"
                "• SSP5 (Fossil Development): Low population growth, high income growth, energy-intensive lifestyle"
            )

        # Regional patterns
        if any(region in query_results.lower() for region in ["south", "west", "northeast", "midwest"]):
            insights.append(
                "Regional differences in socioeconomic trends reflect historical patterns, policy differences, "
                "and economic structures. Southern and Western states often show higher population growth rates."
            )

        # Combine insights
        if insights:
            return "\n\n".join(["Socioeconomic Analysis:"] + [f"• {insight}" for insight in insights])
        else:
            return "Socioeconomic data analysis complete. Consider examining trends over time or comparing scenarios for deeper insights."

    return analyze_socioeconomic_trends


def create_integration_query_tool() -> Any:
    """
    Create a tool for suggesting integrated landuse + socioeconomic queries.

    Returns:
        Configured integration query suggestion tool
    """

    @tool
    def suggest_integration_queries(
        user_question: str,
        analysis_focus: Optional[str] = None
    ) -> str:
        """
        Suggest SQL queries that integrate landuse and socioeconomic data.

        This tool helps construct queries that combine:
        - Land use transitions with population/income trends
        - Development patterns with demographic drivers
        - Climate scenarios with socioeconomic pathways
        - County-level correlations across datasets

        Args:
            user_question: The user's question about integrated analysis
            analysis_focus: Optional focus area (population, income, development, etc.)

        Returns:
            Suggested SQL queries and analysis approaches
        """
        suggestions = []

        # Base integration patterns
        if "population" in user_question.lower() and "urban" in user_question.lower():
            suggestions.append(
                "Population-Urban Development Analysis:\n"
                "```sql\n"
                "SELECT \n"
                "    g.state_name,\n"
                "    lu.ssp_scenario,\n"
                "    SUM(lu.acres) as urban_expansion_acres,\n"
                "    AVG(lu.population_start) as avg_population,\n"
                "    SUM(lu.acres) / AVG(lu.population_start) as acres_per_1000_people\n"
                "FROM v_landuse_socioeconomic lu\n"
                "JOIN dim_geography g ON lu.fips_code = g.fips_code\n"
                "WHERE lu.to_landuse = 'Urban' AND lu.from_landuse != 'Urban'\n"
                "GROUP BY g.state_name, lu.ssp_scenario\n"
                "ORDER BY urban_expansion_acres DESC\n"
                "```"
            )

        if "income" in user_question.lower() and ("agricultural" in user_question.lower() or "farm" in user_question.lower()):
            suggestions.append(
                "Income-Agricultural Change Analysis:\n"
                "```sql\n"
                "SELECT \n"
                "    lu.county_name,\n"
                "    lu.ssp_scenario,\n"
                "    SUM(CASE WHEN lu.from_landuse IN ('Crop', 'Pasture') AND lu.to_landuse = 'Urban' \n"
                "             THEN lu.acres ELSE 0 END) as ag_to_urban_acres,\n"
                "    AVG(lu.income_start) as avg_income,\n"
                "    CASE WHEN AVG(lu.income_start) > 50 THEN 'High Income'\n"
                "         WHEN AVG(lu.income_start) > 30 THEN 'Medium Income'\n"
                "         ELSE 'Low Income' END as income_category\n"
                "FROM v_landuse_socioeconomic lu\n"
                "WHERE lu.from_landuse IN ('Crop', 'Pasture')\n"
                "GROUP BY lu.county_name, lu.ssp_scenario, income_category\n"
                "HAVING ag_to_urban_acres > 0\n"
                "ORDER BY ag_to_urban_acres DESC\n"
                "```"
            )

        if "correlation" in user_question.lower() or "relationship" in user_question.lower():
            suggestions.append(
                "Cross-Dataset Correlation Analysis:\n"
                "```sql\n"
                "WITH county_metrics AS (\n"
                "    SELECT \n"
                "        g.fips_code,\n"
                "        g.county_name,\n"
                "        g.state_name,\n"
                "        -- Population metrics\n"
                "        p1.value as pop_2020,\n"
                "        p2.value as pop_2050,\n"
                "        (p2.value - p1.value) / p1.value as pop_growth_rate,\n"
                "        -- Income metrics\n"
                "        i1.value as income_2020,\n"
                "        i2.value as income_2050,\n"
                "        (i2.value - i1.value) / i1.value as income_growth_rate,\n"
                "        -- Land use metrics\n"
                "        SUM(CASE WHEN f.to_landuse_id = (SELECT landuse_id FROM dim_landuse WHERE landuse_code = 'ur') \n"
                "                 AND f.from_landuse_id != f.to_landuse_id THEN f.acres ELSE 0 END) as urban_expansion\n"
                "    FROM dim_geography g\n"
                "    LEFT JOIN v_population_trends p1 ON g.fips_code = p1.fips_code AND p1.year = 2020 AND p1.ssp_scenario = 'SSP2'\n"
                "    LEFT JOIN v_population_trends p2 ON g.fips_code = p2.fips_code AND p2.year = 2050 AND p2.ssp_scenario = 'SSP2'\n"
                "    LEFT JOIN v_income_trends i1 ON g.fips_code = i1.fips_code AND i1.year = 2020 AND i1.ssp_scenario = 'SSP2'\n"
                "    LEFT JOIN v_income_trends i2 ON g.fips_code = i2.fips_code AND i2.year = 2050 AND i2.ssp_scenario = 'SSP2'\n"
                "    LEFT JOIN fact_landuse_transitions f ON g.geography_id = f.geography_id\n"
                "    GROUP BY 1,2,3,4,5,6,7,8,9\n"
                ")\n"
                "SELECT \n"
                "    state_name,\n"
                "    CORR(pop_growth_rate, urban_expansion) as pop_urban_correlation,\n"
                "    CORR(income_growth_rate, urban_expansion) as income_urban_correlation,\n"
                "    COUNT(*) as county_count\n"
                "FROM county_metrics\n"
                "WHERE pop_growth_rate IS NOT NULL AND income_growth_rate IS NOT NULL\n"
                "GROUP BY state_name\n"
                "ORDER BY pop_urban_correlation DESC\n"
                "```"
            )

        if "scenario" in user_question.lower() and "comparison" in user_question.lower():
            suggestions.append(
                "Multi-Scenario Comparison:\n"
                "```sql\n"
                "SELECT \n"
                "    sc.ssp_scenario,\n"
                "    sc.scenario_name,\n"
                "    -- Population projections\n"
                "    AVG(CASE WHEN pt.year = 2050 THEN pt.population_thousands END) as avg_pop_2050,\n"
                "    -- Income projections\n"
                "    AVG(CASE WHEN it.year = 2050 THEN it.income_per_capita_2009usd END) as avg_income_2050,\n"
                "    -- Land use changes\n"
                "    SUM(CASE WHEN s.ssp_scenario = sc.ssp_scenario AND lu_to.landuse_code = 'ur' \n"
                "             AND lu_from.landuse_code != 'ur' THEN f.acres ELSE 0 END) as total_urban_expansion\n"
                "FROM dim_socioeconomic sc\n"
                "LEFT JOIN v_population_trends pt ON sc.ssp_scenario = pt.ssp_scenario\n"
                "LEFT JOIN v_income_trends it ON sc.ssp_scenario = it.ssp_scenario AND it.year = pt.year\n"
                "LEFT JOIN dim_scenario s ON sc.ssp_scenario = s.ssp_scenario\n"
                "LEFT JOIN fact_landuse_transitions f ON s.scenario_id = f.scenario_id\n"
                "LEFT JOIN dim_landuse lu_from ON f.from_landuse_id = lu_from.landuse_id\n"
                "LEFT JOIN dim_landuse lu_to ON f.to_landuse_id = lu_to.landuse_id\n"
                "GROUP BY sc.ssp_scenario, sc.scenario_name\n"
                "ORDER BY total_urban_expansion DESC\n"
                "```"
            )

        # Generic suggestions if no specific pattern matched
        if not suggestions:
            suggestions.append(
                "General Integration Approaches:\n"
                "1. Use v_landuse_socioeconomic view for combined analysis\n"
                "2. Join v_population_trends and v_income_trends with landuse data on FIPS codes and scenarios\n"
                "3. Compare SSP scenarios across both socioeconomic and landuse dimensions\n"
                "4. Analyze time series relationships between demographic and land use changes\n"
                "5. Examine county-level correlations using statistical functions (CORR, REGR_SLOPE)"
            )

        return "\n\n".join(["Integration Query Suggestions:"] + suggestions)

    return suggest_integration_queries
