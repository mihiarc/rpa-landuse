"""Base agent class for landuse analytics agents following 2025 best practices."""

import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console
from rich.table import Table
import duckdb

from landuse.agents.formatting import clean_sql_query, format_query_results
from landuse.config.landuse_config import LanduseConfig
from landuse.utils.retry_decorators import database_retry


class BaseLanduseAgent(ABC):
    """Base class for landuse analytics agents with shared functionality."""

    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the base agent with configuration."""
        self.config = config or LanduseConfig()
        self.console = Console()
        self.llm = self._create_llm()
        self.db_connection = self._create_db_connection()
        self.schema = self._get_schema()
        self.tools = self._create_tools()
        self.graph = None
        self.memory = MemorySaver()  # Memory-first architecture (2025 best practice)

    def _create_llm(self) -> BaseChatModel:
        """Create LLM instance based on configuration (factory pattern)."""
        model_name = self.config.model_name

        # Mask API keys for logging
        def mask_key(key: Optional[str]) -> str:
            if not key:
                return "NOT_SET"
            return f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"

        self.console.print(f"[blue]Initializing LLM: {model_name}[/blue]")

        if "claude" in model_name.lower():
            api_key = os.getenv('ANTHROPIC_API_KEY')
            self.console.print(f"[dim]Using Anthropic API key: {mask_key(api_key)}[/dim]")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required for Claude models")

            return ChatAnthropic(
                model=model_name,
                anthropic_api_key=api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            self.console.print(f"[dim]Using OpenAI API key: {mask_key(api_key)}[/dim]")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")

            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

    def _create_db_connection(self) -> duckdb.DuckDBPyConnection:
        """Create direct database connection."""
        return duckdb.connect(database=self.config.db_path, read_only=True)

    @database_retry(max_attempts=3)
    def _get_schema(self) -> str:
        """Get the database schema with retry logic."""
        conn = self.db_connection

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

        # Format schema as string
        schema_lines = ["Database Schema:"]
        current_table = None

        for row in result:
            table_name, column_name, data_type, is_nullable = row
            if table_name != current_table:
                schema_lines.append(f"\nTable: {table_name}")
                current_table = table_name
            nullable = "" if is_nullable == "YES" else " NOT NULL"
            schema_lines.append(f"  - {column_name}: {data_type}{nullable}")

        return "\n".join(schema_lines)

    @abstractmethod
    def _create_tools(self) -> list[BaseTool]:
        """Create agent-specific tools. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph. Must be implemented by subclasses."""
        pass

    def _execute_query(self, query: str) -> dict[str, Any]:
        """Execute a SQL query with standard error handling and formatting."""
        cleaned_query = clean_sql_query(query)

        try:
            conn = self.db_connection

            # Add row limit if not present
            if "limit" not in cleaned_query.lower():
                cleaned_query = f"{cleaned_query.rstrip(';')} LIMIT {self.config.max_query_rows}"

            result = conn.execute(cleaned_query).fetchall()
            columns = [desc[0] for desc in conn.description] if conn.description else []

            # Format results
            formatted_results = format_query_results(result, columns)

            return {
                "success": True,
                "query": cleaned_query,
                "results": result,
                "columns": columns,
                "formatted": formatted_results,
                "row_count": len(result)
            }

        except Exception as e:
            error_msg = str(e)
            suggestion = self._get_error_suggestion(error_msg)

            return {
                "success": False,
                "query": cleaned_query,
                "error": error_msg,
                "suggestion": suggestion
            }

    def _get_error_suggestion(self, error_msg: str) -> str:
        """Get helpful suggestions for common SQL errors."""
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

    def query(self, question: str) -> str:
        """Execute a natural language query using the agent."""
        try:
            if not self.graph:
                self.graph = self._build_graph()

            # Use the graph with memory checkpointing
            result = self.graph.invoke(
                {"messages": [("user", question)]},
                config={"configurable": {"thread_id": "landuse-session"}}
            )

            # Extract and format the final response
            if "messages" in result:
                return result["messages"][-1].content
            return str(result)
        except Exception as e:
            return f"Error processing query: {str(e)}"

    def _display_results_table(self, results: list[tuple], columns: list[str], title: str = "Query Results") -> None:
        """Display query results in a rich table format."""
        table = Table(title=title, show_header=True, header_style="bold magenta")

        # Add columns
        for col in columns:
            table.add_column(col, style="cyan", no_wrap=False)

        # Add rows (limit display)
        display_limit = min(len(results), self.config.default_display_limit)
        for row in results[:display_limit]:
            table.add_row(*[str(val) for val in row])

        if len(results) > display_limit:
            table.add_row(*["..." for _ in columns])
            table.caption = f"Showing {display_limit} of {len(results)} rows"

        self.console.print(table)
