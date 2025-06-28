"""Consolidated landuse agent with modern LangGraph architecture."""

import os
from typing import Any, Optional, TypedDict, Union

import duckdb
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from landuse.agents.formatting import clean_sql_query, format_query_results
from landuse.agents.prompts import get_system_prompt
from landuse.config.landuse_config import LanduseConfig
from landuse.tools.common_tools import create_analysis_tool, create_execute_query_tool, create_schema_tool
from landuse.utils.retry_decorators import database_retry


class AgentState(TypedDict):
    """State definition for the landuse agent following 2025 patterns."""
    messages: list[BaseMessage]
    context: dict[str, Any]
    iteration_count: int
    max_iterations: int


class LanduseAgent:
    """
    Modern landuse agent implementation with:
    - Memory-first architecture
    - Graph-based workflow
    - Subgraph support for complex queries
    - Human-in-the-loop capability
    - Event-driven execution
    - Integrated LLM and database management
    """

    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the landuse agent with configuration."""
        self.config = config or LanduseConfig()
        self.console = Console()
        self.llm = self._create_llm()
        self.db_connection = self._create_db_connection()
        self.schema = self._get_schema()
        self.tools = self._create_tools()
        self.graph = None
        self.memory = MemorySaver()  # Memory-first architecture (2025 best practice)
        
        # Use centralized prompts system with configuration
        self.system_prompt = get_system_prompt(
            include_maps=self.config.enable_map_generation,
            analysis_style=self.config.analysis_style,
            domain_focus=None if self.config.domain_focus == 'none' else self.config.domain_focus,
            schema_info=self.schema
        )

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

    def _create_tools(self) -> list[BaseTool]:
        """Create tools for the agent."""
        return [
            create_execute_query_tool(self.config, self.db_connection, self.schema),
            create_analysis_tool(),
            create_schema_tool(self.schema)
        ]

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        # Create the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("human_review", self._human_review_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "analyzer": "analyzer",
                "human_review": "human_review",
                "end": END
            }
        )

        # Add edges from tools back to agent
        workflow.add_edge("tools", "agent")
        workflow.add_edge("analyzer", "agent")
        workflow.add_edge("human_review", "agent")

        # Compile with memory
        return workflow.compile(checkpointer=self.memory)

    def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """Main agent node that decides next action."""
        messages = state["messages"]

        # Add system prompt if this is the first message
        if len(messages) == 1:
            messages = [
                {"role": "system", "content": self.system_prompt},
                messages[0]
            ]

        # Get LLM response
        response = self.llm.bind_tools(self.tools).invoke(messages)

        # Update state
        return {
            "messages": messages + [response],
            "iteration_count": state.get("iteration_count", 0) + 1
        }

    def _analyzer_node(self, state: AgentState) -> dict[str, Any]:
        """Analyzer node for providing insights on query results."""
        messages = state["messages"]

        # Extract recent query results
        recent_results = self._extract_recent_results(messages)

        if recent_results:
            # Create analysis prompt
            analysis_prompt = f"""Based on these query results, provide key insights:

Results: {recent_results}

Focus on:
1. Key trends or patterns
2. Implications for land use planning
3. Comparison with historical patterns
4. Recommendations or areas for further investigation
"""

            # Get analysis
            analysis = self.llm.invoke([
                {"role": "system", "content": "You are a land use science expert."},
                {"role": "user", "content": analysis_prompt}
            ])

            return {"messages": messages + [analysis]}

        return {"messages": messages}

    def _human_review_node(self, state: AgentState) -> dict[str, Any]:
        """Human-in-the-loop node for complex queries."""
        # In production, this would integrate with a UI
        # For now, we'll auto-approve
        self.console.print("[yellow]Human review requested (auto-approved)[/yellow]")
        return {"messages": state["messages"]}

    def _should_continue(self, state: AgentState) -> str:
        """Decide next step in the workflow."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check iteration limit
        if state.get("iteration_count", 0) >= self.config.max_iterations:
            return "end"

        # Check if tools were called
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Check if analysis is needed
        if self._needs_analysis(messages):
            return "analyzer"

        # Check if human review is needed (for sensitive queries)
        if self._needs_human_review(messages):
            return "human_review"

        # Otherwise, we're done
        return "end"

    def _needs_analysis(self, messages: list[BaseMessage]) -> bool:
        """Determine if results need analysis."""
        # Check if recent messages contain query results
        for msg in messages[-3:]:
            if isinstance(msg, AIMessage) and "SELECT" in str(msg.content).upper():
                return True
        return False

    def _needs_human_review(self, messages: list[BaseMessage]) -> bool:
        """Determine if human review is needed."""
        # Check for sensitive operations
        sensitive_keywords = ["DELETE", "UPDATE", "DROP", "TRUNCATE"]
        last_message = str(messages[-1].content).upper()

        return any(keyword in last_message for keyword in sensitive_keywords)

    def _extract_recent_results(self, messages: list[BaseMessage]) -> Optional[str]:
        """Extract recent query results from messages."""
        for msg in reversed(messages[-5:]):
            content = str(msg.content)
            if "rows returned" in content or "│" in content:
                return content
        return None

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

    def stream_query(self, question: str) -> Any:
        """
        Stream responses for real-time interaction.

        Args:
            question: Natural language question

        Yields:
            Streaming response chunks
        """
        if not self.graph:
            self.graph = self._build_graph()

        # Stream the response
        yield from self.graph.stream(
            {"messages": [HumanMessage(content=question)], "max_iterations": self.config.max_iterations},
            config={"configurable": {"thread_id": "landuse-stream"}}
        )

    def create_subgraph(self, name: str, specialized_tools: list[BaseTool]) -> StateGraph:
        """
        Create a specialized subgraph for complex workflows.

        This follows the 2025 pattern of using subgraphs for modularity.

        Args:
            name: Name of the subgraph
            specialized_tools: Tools specific to this subgraph

        Returns:
            Compiled subgraph
        """
        subgraph = StateGraph(AgentState)

        # Add specialized nodes
        subgraph.add_node("specialized_agent", self._agent_node)
        subgraph.add_node("specialized_tools", ToolNode(specialized_tools))

        # Set up flow
        subgraph.set_entry_point("specialized_agent")
        subgraph.add_edge("specialized_agent", "specialized_tools")
        subgraph.add_edge("specialized_tools", END)

        return subgraph.compile()

    def create_map_subgraph(self) -> StateGraph:
        """
        Create a specialized subgraph for map-based analysis.
        
        This subgraph adds geographic visualization capabilities.
        
        Returns:
            Compiled map analysis subgraph
        """
        # Import map tools only when needed
        from landuse.tools.map_tools import create_choropleth_tool, create_heatmap_tool
        
        map_tools = [
            create_execute_query_tool(self.config, self.db_connection, self.schema),
            create_choropleth_tool(),
            create_heatmap_tool(),
            create_analysis_tool()
        ]
        
        return self.create_subgraph("map_analysis", map_tools)

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
    
    def chat(self) -> None:
        """Interactive chat interface for the agent."""
        self.console.print(Panel.fit(
            "[bold green]RPA Land Use Analytics Agent[/bold green]\n"
            "Ask questions about land use projections and transitions.\n"
            "Type 'exit' to quit, 'help' for examples.",
            title="Welcome",
            border_style="green"
        ))
        
        while True:
            try:
                question = input("\n[You] > ").strip()
                
                if not question:
                    continue
                    
                if question.lower() in ['exit', 'quit', 'q']:
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break
                    
                if question.lower() in ['help', '?']:
                    self._show_help()
                    continue
                
                # Process the question
                self.console.print("\n[bold cyan][Agent][/bold cyan] Thinking...")
                response = self.query(question)
                self.console.print(f"\n[bold cyan][Agent][/bold cyan] {response}")
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")
    
    def _show_help(self) -> None:
        """Show help information with example queries."""
        examples = [
            "Which states will see the most agricultural land loss?",
            "Compare forest transitions between RCP45 and RCP85 scenarios",
            "Show urbanization trends in California counties",
            "What land use types are converting to urban?",
            "Analyze cropland changes in the Midwest by 2070"
        ]
        
        self.console.print(Panel.fit(
            "\n".join([f"• {ex}" for ex in examples]),
            title="Example Questions",
            border_style="blue"
        ))