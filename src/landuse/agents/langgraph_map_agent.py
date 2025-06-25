#!/usr/bin/env python3
"""
Enhanced LangGraph Landuse Agent with Map Generation Capabilities
Extends the base agent to create visualizations and maps
"""

import json
import logging
import operator
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Optional, TypedDict

import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..config import LanduseConfig
from ..models import ExecuteQueryInput, SQLQuery
from ..tools.map_generation_tool import create_map_generation_tool
from ..utils.retry_decorators import database_retry
from .constants import SCHEMA_INFO_TEMPLATE, STATE_NAMES
from .formatting import clean_sql_query, format_query_results, format_response

# Load environment variables
load_dotenv("config/.env")
load_dotenv()


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_query: Optional[str]
    sql_queries: list[str]
    query_results: list[dict[str, Any]]
    analysis_context: dict[str, Any]
    iteration_count: int
    max_iterations: int




class MapAgentState(AgentState):
    """Extended state for map-capable agent"""
    generated_maps: list[dict[str, Any]]
    visualization_requested: bool


class LangGraphMapAgent:
    """
    Enhanced LangGraph agent with map generation capabilities.

    Extends the base agent to:
    - Generate county-level maps for states
    - Create regional and national visualizations
    - Show land use transitions visually
    - Integrate map generation with natural language queries
    """

    def __init__(self, config: Optional[LanduseConfig] = None):
        self.console = Console()

        # Configuration
        if config is None:
            config = LanduseConfig.for_agent_type('map')

        self.config = config
        self.db_path = Path(config.db_path)

        # Setup logging
        self._setup_logging()

        # Initialize LLM
        self._init_llm()

        # Get schema information
        self.schema_info = self._get_schema_info()

        # Create tools including map tool
        self.tools = self._create_tools()

        # Create map output directory
        self.map_output_dir = Path(config.map_output_dir)
        self.map_output_dir.mkdir(exist_ok=True, parents=True)

        # Add map generation tool to tools list
        map_tool = create_map_generation_tool(
            str(self.db_path),
            str(self.map_output_dir)
        )
        self.tools.append(map_tool)

        # Create graph with map capabilities
        self.graph = self._create_enhanced_graph()

        # Setup memory if enabled
        if config.enable_memory:
            self.memory = MemorySaver()
            self.graph = self.graph.compile(checkpointer=self.memory)
        else:
            self.graph = self.graph.compile()

        self.logger.info("Enhanced map agent initialized with visualization capabilities")

    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.ERROR if not self.config.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

        # Suppress noisy libraries
        logging.getLogger("httpx").setLevel(logging.CRITICAL)
        logging.getLogger("langchain").setLevel(logging.WARNING)

    def _init_llm(self):
        """Initialize the language model"""
        if self.config.model_name.startswith("claude"):
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Anthropic API key required for Claude models")

            self.llm = ChatAnthropic(
                api_key=api_key,
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            self.api_key_masked = self._mask_api_key(api_key)
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key required for GPT models")

            self.llm = ChatOpenAI(
                api_key=api_key,
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            self.api_key_masked = self._mask_api_key(api_key)

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for display"""
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}...{api_key[-4:]}"

    def _get_schema_info(self) -> str:
        """Get comprehensive schema information for the agent"""
        try:
            conn = duckdb.connect(str(self.db_path), read_only=True)

            # Start with template
            schema_info = SCHEMA_INFO_TEMPLATE

            # Add actual table counts
            tables_info = []
            tables = ['dim_scenario', 'dim_time', 'dim_geography_enhanced', 'dim_landuse', 'fact_landuse_transitions']

            for table in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    tables_info.append(f"- {table}: {count:,} records")
                except Exception:
                    pass

            if tables_info:
                schema_info += "\n## Current Data Counts\n" + "\n".join(tables_info)

            # Get sample scenarios
            try:
                scenarios = conn.execute("SELECT scenario_name FROM dim_scenario LIMIT 5").fetchall()
                scenario_names = [s[0] for s in scenarios]
                if scenario_names:
                    schema_info += "\n\n## Sample Scenarios\n" + "\n".join([f"- {s}" for s in scenario_names])
            except Exception:
                pass

            conn.close()
            return schema_info

        except Exception as e:
            self.logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"

    def _create_tools(self) -> list:
        """Create tools for the LangGraph agent"""
        # Create the core tools using @tool decorator
        @tool
        def execute_landuse_query(sql_query: str) -> str:
            """Execute DuckDB SQL query on the landuse database. Input should be a SQL query string."""
            return self._execute_landuse_query(sql_query)

        @tool
        def get_schema_info(query: str = "") -> str:
            """Get detailed schema information about the landuse database tables and relationships."""
            return self.schema_info

        @tool
        def suggest_query_examples(category: str = "general") -> str:
            """Get example queries for common landuse analysis patterns."""
            return self._suggest_query_examples(category)

        return [execute_landuse_query, get_schema_info, suggest_query_examples]

    @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0,
                   exceptions=(ConnectionError, TimeoutError, OSError))
    def _execute_landuse_query(self, sql_query: str) -> str:
        """Execute SQL query on the landuse database with validation and retry logic"""
        try:
            # Validate input using Pydantic
            input_data = ExecuteQueryInput(sql_query=sql_query)

            # Clean and validate SQL
            query_obj = SQLQuery(sql=clean_sql_query(input_data.sql_query))
            sql_query = query_obj.sql

            # Connect to database
            conn = duckdb.connect(str(self.db_path), read_only=True)

            # Add LIMIT if not present
            if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                # Remove trailing semicolon if present
                query_trimmed = sql_query.rstrip().rstrip(';').rstrip()
                sql_query = f"{query_trimmed} LIMIT {self.config.max_query_rows}"

            # Execute query
            import time
            start_time = time.time()
            result = conn.execute(sql_query)
            execution_time = time.time() - start_time

            if result is None:
                conn.close()
                return f"❌ Query returned no result object\nSQL: {sql_query}"

            df = result.df()
            conn.close()

            # Format results
            return format_query_results(
                df, sql_query,
                max_display_rows=self.config.default_display_limit
            )

        except ValueError as e:
            # Pydantic validation error
            self.logger.error(f"Validation error: {e}")
            return f"❌ Invalid query: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return f"❌ Error executing query: {str(e)}\nSQL: {sql_query}"

    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns"""
        query_examples = {
            "general": """
                SELECT
                    s.scenario_name,
                    t.year_range,
                    SUM(f.acres) as total_acres
                FROM fact_landuse_transitions f
                JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                JOIN dim_time t ON f.time_id = t.time_id
                GROUP BY s.scenario_name, t.year_range
                ORDER BY s.scenario_name, t.year_range
                LIMIT 10
            """,
            "forest_loss": """
                SELECT
                    g.state_name,
                    SUM(f.acres) as forest_to_urban_acres
                FROM fact_landuse_transitions f
                JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
                JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
                JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
                WHERE fl.landuse_name = 'Forest'
                    AND tl.landuse_name = 'Urban'
                    AND f.transition_type = 'change'
                GROUP BY g.state_name
                ORDER BY forest_to_urban_acres DESC
                LIMIT 10
            """,
            "agricultural": """
                SELECT
                    t.year_range,
                    SUM(CASE WHEN l.landuse_name = 'Crop' THEN f.acres ELSE 0 END) as crop_acres,
                    SUM(CASE WHEN l.landuse_name = 'Pasture' THEN f.acres ELSE 0 END) as pasture_acres,
                    SUM(CASE WHEN l.landuse_name IN ('Crop', 'Pasture') THEN f.acres ELSE 0 END) as total_ag_acres
                FROM fact_landuse_transitions f
                JOIN dim_landuse l ON f.to_landuse_id = l.landuse_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE f.transition_type = 'same'
                GROUP BY t.year_range
                ORDER BY t.year_range
            """
        }

        if category in query_examples:
            return f"💡 **Example Query - {category.replace('_', ' ').title()}:**\n```sql\n{query_examples[category]}\n```"

        result = "💡 **Common Query Examples:**\n\n"
        for name, sql in query_examples.items():
            result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"

        return result

    def _create_enhanced_graph(self) -> StateGraph:
        """Create enhanced graph with map generation capabilities"""

        # Define nodes
        def agent_node(state: MapAgentState) -> dict[str, Any]:
            """Enhanced agent reasoning node"""
            messages = state["messages"]
            iteration_count = state.get("iteration_count", 0)
            max_iterations = state.get("max_iterations", self.config.max_iterations)

            # Check iteration limit
            if iteration_count >= max_iterations:
                return {
                    "messages": [AIMessage(content=f"🔄 Reached maximum iterations ({max_iterations}). Please try a simpler query.")],
                    "iteration_count": iteration_count + 1
                }

            # Enhanced system message with map capabilities
            system_message = SystemMessage(content=f"""
You are a specialized Landuse Data Analyst AI with visualization capabilities.

DATABASE SCHEMA:
{self.schema_info}

CAPABILITIES:
1. Convert natural language questions into DuckDB SQL queries
2. Generate maps and visualizations when requested
3. Analyze land use patterns and transitions
4. Create county-level, regional, and national maps

MAP GENERATION:
- Use generate_landuse_map tool when users request visualizations
- Map types available:
  * "state_counties": County-level maps for specific states
  * "regional": Regional maps showing all states
  * "transitions": Maps showing land use transitions
- Always provide the map file path in your response

SQL QUERY RULES:
1. **GROUP BY**: When using aggregate functions (SUM, COUNT, AVG), include ALL non-aggregate SELECT columns in GROUP BY
2. **ORDER BY**: Only use columns that are either in SELECT list or are aggregated
3. **Common Pattern**: SELECT col1, col2, SUM(col3) ... GROUP BY col1, col2 ORDER BY col1
4. **Texas Example**: For "forest in Texas" queries, use state filtering with proper grouping

INSTRUCTIONS:
1. First understand what data the user wants to see
2. Execute appropriate SQL queries to analyze the data (follow SQL QUERY RULES above)
3. If visualization is requested or would be helpful, generate appropriate maps
4. Explain both the data insights and any visualizations created
5. For map requests, identify the appropriate map type and parameters

DEFAULT ASSUMPTIONS:
- **Scenarios**: Use AVERAGE across all scenarios unless specified
- **Time Periods**: Use FULL time range unless specified
- **Geographic Scope**: All states/counties unless specified
- **Map Type**: Generate most relevant map type based on query

EXAMPLE SQL PATTERNS:
- **Forest in Texas**:
  ```sql
  SELECT SUM(f.acres) as total_forest_acres
  FROM fact_landuse_transitions f
  JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
  JOIN dim_landuse l ON f.to_landuse_id = l.landuse_id
  WHERE g.state_code = '48' AND l.landuse_name = 'Forest' AND f.transition_type = 'same'
  ```

ALWAYS provide file paths for generated maps and explain what they show.
""")

            # Check if visualization might be helpful
            last_human_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
            if last_human_msg:
                query_lower = last_human_msg.content.lower()
                viz_keywords = ['map', 'show', 'visualize', 'display', 'plot', 'chart', 'geographic', 'spatial']
                state["visualization_requested"] = any(keyword in query_lower for keyword in viz_keywords)

            # Prepare messages for LLM
            llm_messages = [system_message] + messages

            # Bind tools to LLM
            llm_with_tools = self.llm.bind_tools(self.tools)

            # Get response
            response = llm_with_tools.invoke(llm_messages)

            return {
                "messages": [response],
                "iteration_count": iteration_count + 1
            }

        def should_continue(state: MapAgentState) -> str:
            """Determine if we should continue or end"""
            messages = state["messages"]
            last_message = messages[-1]
            iteration_count = state.get("iteration_count", 0)
            max_iterations = state.get("max_iterations", self.config.max_iterations)

            # Check iteration limit
            if iteration_count >= max_iterations:
                return "end"

            # If the last message has tool calls, continue to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"

            # Otherwise, we're done
            return "end"

        # Create tool node
        tool_node = ToolNode(self.tools)

        # Build the graph
        workflow = StateGraph(MapAgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END,
            }
        )

        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")

        return workflow

    def query(self, natural_language_query: str, thread_id: Optional[str] = None) -> str:
        """
        Process a natural language query with map generation support.

        Args:
            natural_language_query: The user's question
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Formatted response with map information if applicable
        """
        try:
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=natural_language_query)],
                "current_query": natural_language_query,
                "sql_queries": [],
                "query_results": [],
                "analysis_context": {},
                "iteration_count": 0,
                "max_iterations": self.config.max_iterations,
                "generated_maps": [],
                "visualization_requested": False
            }

            # Configure execution
            config = {"recursion_limit": self.config.max_iterations + 2}
            if self.config.enable_memory:
                import uuid
                actual_thread_id = thread_id or str(uuid.uuid4())
                config["configurable"] = {"thread_id": actual_thread_id}

            # Execute the graph
            result = self.graph.invoke(initial_state, config=config)

            # Extract final response
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    response = last_message.content

                    # Process tool call artifacts for maps
                    for msg in messages:
                        if hasattr(msg, 'tool_calls'):
                            for tool_call in msg.tool_calls:
                                if tool_call.get('name') == 'generate_landuse_map':
                                    # Look for corresponding tool message with artifact
                                    tool_msg_idx = messages.index(msg) + 1
                                    if tool_msg_idx < len(messages):
                                        tool_msg = messages[tool_msg_idx]
                                        if hasattr(tool_msg, 'artifact') and tool_msg.artifact:
                                            map_info = tool_msg.artifact
                                            if map_info.get('success') and 'generated_maps' not in result:
                                                result['generated_maps'] = []
                                            if map_info.get('success'):
                                                result['generated_maps'].append(map_info)

                    # Check if any maps were generated
                    generated_maps = result.get("generated_maps", [])
                    if generated_maps:
                        response += "\n\n📊 **Generated Visualizations:**\n"
                        for map_info in generated_maps:
                            if map_info.get("success"):
                                response += f"- {map_info.get('description', 'Map')}: `{map_info.get('map_path')}`\n"

                    return response
                else:
                    return str(last_message)

            return "No response generated"

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"❌ Error processing query: {str(e)}"

    def chat(self):
        """Enhanced interactive chat mode with map generation examples"""
        # Welcome message
        welcome_panel = Panel(
            f"""[bold cyan]🚀 LangGraph Map Agent[/bold cyan]

[yellow]Database:[/yellow] {self.db_path}
[yellow]Model:[/yellow] {self.config.model_name}
[yellow]Memory:[/yellow] {'Enabled' if self.config.enable_memory else 'Disabled'}
[yellow]Map Output:[/yellow] {self.map_output_dir}

[green]Enhanced Capabilities:[/green]
• Natural language to SQL queries
• 🗺️ Generate county-level maps
• 📊 Create regional visualizations
• 🔄 Show land use transitions
• 📈 Visualize trends and patterns

[green]Commands:[/green]
• Type your questions naturally
• 'help' - Show examples
• 'schema' - Show database schema
• 'maps' - Show map generation examples
• 'exit' - Quit

[dim]Now with integrated map generation capabilities![/dim]""",
            title="🌾 Enhanced Landuse Agent with Maps",
            border_style="green"
        )
        self.console.print(welcome_panel)

        # Generate thread ID for this session
        import uuid
        thread_id = str(uuid.uuid4()) if self.config.enable_memory else None

        # Show examples
        self._show_examples()

        while True:
            try:
                user_input = self.console.input("[bold green]🌾 Map Agent>[/bold green] ").strip()

                if user_input.lower() == 'exit':
                    self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                    break
                elif user_input.lower() == 'help':
                    self._show_examples()
                elif user_input.lower() == 'maps':
                    self._show_map_examples()
                elif user_input.lower() == 'schema':
                    schema_md = Markdown(self.schema_info)
                    self.console.print(Panel(schema_md, title="📊 Database Schema", border_style="cyan"))
                elif user_input:
                    # Show processing message
                    self.console.print()
                    with self.console.status("[bold cyan]🔍 Processing with map generation...[/bold cyan]", spinner="dots"):
                        response = self.query(user_input, thread_id)

                    # Format and display response
                    self.console.print()
                    self.console.print(format_response(response))
                    self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                break
            except Exception as e:
                self.logger.error(f"Chat error: {e}")
                self.console.print(f"❌ Error: {str(e)}")

    def _show_examples(self):
        """Show enhanced examples including map generation"""
        examples_panel = Panel(
            """[bold cyan]🚀 Try these questions:[/bold cyan]

[yellow]Data Analysis:[/yellow]
• "How much agricultural land is being lost?"
• "Which states have the most urban expansion?"
• "Compare forest loss between climate scenarios"

[yellow]Map Generation:[/yellow]
• "Show me a map of forest coverage in Texas"
• "Create a map showing urban areas by county in California"
• "Visualize agricultural land distribution across regions"
• "Display forest to urban transitions nationally"

[yellow]Combined Analysis:[/yellow]
• "Analyze and map crop land changes in the Midwest"
• "Show me urbanization patterns in Florida with a map"
• "Compare and visualize land use between Texas and California"

[green]💡 The agent will generate maps when visualization would be helpful![/green]""",
            title="🌾 Example Questions",
            border_style="blue"
        )
        self.console.print(examples_panel)

    def _show_map_examples(self):
        """Show specific map generation examples"""
        map_panel = Panel(
            """[bold cyan]🗺️ Map Generation Examples:[/bold cyan]

[yellow]State County Maps:[/yellow]
• "Create a county map of Texas showing forest coverage"
• "Show me urban areas by county in California"
• "Map agricultural land in Florida counties"

[yellow]Regional Maps:[/yellow]
• "Create a regional map of forest distribution"
• "Show urban land use across all US regions"
• "Map crop land by state and region"

[yellow]Transition Maps:[/yellow]
• "Map forest to urban transitions"
• "Show agricultural to urban conversions in Texas"
• "Visualize land use changes nationally"

[yellow]Analysis with Maps:[/yellow]
• "Which counties in Texas have the most forest? Show me a map"
• "Analyze and visualize urban growth patterns"
• "Compare land use between states with maps"

[green]💡 Maps are saved to: {self.map_output_dir}[/green]""",
            title="🗺️ Map Generation Guide",
            border_style="magenta"
        )
        self.console.print(map_panel)


def main():
    """Main entry point for the enhanced map agent"""
    try:
        config = LanduseConfig.for_agent_type('map')
        agent = LangGraphMapAgent(config)
        agent.chat()
    except KeyboardInterrupt:
        print("\n👋 Happy analyzing!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
