#!/usr/bin/env python3
"""
Unified LangGraph-based agent for landuse analysis.
This module consolidates all agent functionality into a single, clean implementation.
"""

import os
import logging
import duckdb
import operator
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Sequence, Union
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from ..models import AgentConfig
from .constants import (
    SCHEMA_INFO_TEMPLATE, DB_CONFIG, MODEL_CONFIG,
    QUERY_EXAMPLES, STATE_NAMES, DEFAULT_ASSUMPTIONS
)
from .formatting import (
    clean_sql_query, format_query_results, create_welcome_panel,
    create_examples_panel, format_error, format_response
)

# Load environment variables
load_dotenv("config/.env")
load_dotenv()


class LanduseAgentState(TypedDict):
    """State for the landuse analysis agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_query: Optional[str]
    sql_queries: list[str]
    query_results: list[dict[str, Any]]
    analysis_context: dict[str, Any]
    iteration_count: int
    max_iterations: int
    include_maps: bool  # Whether to generate map visualizations


class LanduseAgent:
    """
    Unified LangGraph-based agent for natural language analysis of land use data.
    
    This agent consolidates all functionality:
    - Natural language to SQL conversion
    - Business intelligence and insights
    - Map generation capabilities (when enabled)
    - Interactive chat interface
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        verbose: bool = False,
        config: Optional[AgentConfig] = None,
        enable_memory: bool = False,
        enable_maps: bool = False
    ):
        """
        Initialize the landuse agent.
        
        Args:
            db_path: Path to DuckDB database
            model_name: LLM model to use (e.g., 'gpt-4', 'claude-3-5-sonnet')
            temperature: LLM temperature
            max_tokens: Maximum tokens for LLM response
            verbose: Enable verbose logging
            config: Complete AgentConfig object
            enable_memory: Enable conversation memory/checkpointing
            enable_maps: Enable map generation capabilities
        """
        self.console = Console()
        self.verbose = verbose
        self.enable_maps = enable_maps
        
        # Setup logging
        self._setup_logging()
        
        # Use provided config or create from parameters
        if config:
            self.config = config
        else:
            config_dict = {
                'db_path': Path(db_path or os.getenv('LANDUSE_DB_PATH', DB_CONFIG['default_path'])),
                'model_name': model_name or os.getenv('LANDUSE_MODEL', MODEL_CONFIG['default_openai_model']),
                'temperature': temperature or float(os.getenv('TEMPERATURE', str(MODEL_CONFIG['default_temperature']))),
                'max_tokens': max_tokens or int(os.getenv('MAX_TOKENS', str(MODEL_CONFIG['default_max_tokens']))),
                'max_iterations': int(os.getenv('LANDUSE_MAX_ITERATIONS', '5')),
                'max_execution_time': int(os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120')),
                'max_query_rows': int(os.getenv('LANDUSE_MAX_QUERY_ROWS', '1000')),
                'default_display_limit': int(os.getenv('LANDUSE_DEFAULT_DISPLAY_LIMIT', '50'))
            }
            self.config = AgentConfig(**config_dict)
        
        # Extract commonly used values
        self.db_path = self.config.db_path
        self.model_name = self.config.model_name
        
        # Initialize LLM
        self._init_llm()
        
        # Get database schema
        self.schema_info = self._get_schema_info()
        
        # Create tools
        self._create_tools()
        
        # Build the graph
        self._build_graph(enable_memory)
        
        self.logger.info(f"LanduseAgent initialized with model: {self.model_name}")
        if enable_maps:
            self.logger.info("Map generation capabilities enabled")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.ERROR if not self.verbose else logging.INFO
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
        if self.model_name.startswith("claude"):
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Anthropic API key required for Claude models")
            
            self.llm = ChatAnthropic(
                api_key=api_key,
                model=self.model_name,
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
                model=self.model_name,
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
        """Get comprehensive schema information"""
        try:
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            # Start with template
            schema_info = SCHEMA_INFO_TEMPLATE
            
            # Add actual table counts
            tables_info = []
            tables = ['dim_scenario', 'dim_time', 'dim_geography', 'dim_landuse', 'fact_landuse_transitions']
            
            for table in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    tables_info.append(f"- {table}: {count:,} records")
                except Exception:
                    pass
            
            if tables_info:
                schema_info += f"\n## Current Data Counts\n" + "\n".join(tables_info)
            
            conn.close()
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"
    
    def _create_tools(self):
        """Create tools for the agent"""
        
        @tool
        def execute_landuse_query(sql_query: str) -> dict:
            """Execute DuckDB SQL query on the landuse database."""
            try:
                # Clean SQL
                sql_query = clean_sql_query(sql_query)
                
                # Connect to database
                conn = duckdb.connect(str(self.db_path), read_only=True)
                
                # Add LIMIT if not present
                if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                    query_trimmed = sql_query.rstrip().rstrip(';').rstrip()
                    sql_query = f"{query_trimmed} LIMIT {self.config.max_query_rows}"
                
                # Execute query
                import time
                start_time = time.time()
                result = conn.execute(sql_query)
                execution_time = time.time() - start_time
                
                if result is None:
                    conn.close()
                    return {"error": "Query returned no result", "sql": sql_query}
                
                df = result.df()
                conn.close()
                
                # Format results
                formatted = format_query_results(
                    df, sql_query,
                    max_display_rows=self.config.default_display_limit
                )
                
                return {
                    "success": True,
                    "formatted_output": formatted,
                    "row_count": len(df),
                    "execution_time": execution_time,
                    "sql": sql_query
                }
                
            except Exception as e:
                return {"error": str(e), "sql": sql_query}
        
        @tool
        def get_schema_info() -> str:
            """Get detailed schema information about the landuse database."""
            return self.schema_info
        
        @tool
        def suggest_query_examples(category: str = "general") -> str:
            """Get example queries for common landuse analysis patterns."""
            if category.lower() in QUERY_EXAMPLES:
                return f"Example Query - {category.title()}:\n{QUERY_EXAMPLES[category.lower()]}"
            
            result = "Common Query Examples:\n\n"
            for name, sql in QUERY_EXAMPLES.items():
                result += f"{name.replace('_', ' ').title()}:\n{sql}\n\n"
            
            return result
        
        @tool
        def get_state_code(state_name: str) -> str:
            """Get the numeric state code for a given state name."""
            # Create reverse mapping
            name_to_code = {v.lower(): k for k, v in STATE_NAMES.items()}
            
            # Clean the input
            state_clean = state_name.strip().lower()
            
            # Check exact match
            if state_clean in name_to_code:
                code = name_to_code[state_clean]
                return f"{STATE_NAMES[code]} has state_code = '{code}'"
            
            # Check partial matches
            matches = [(code, name) for code, name in STATE_NAMES.items() if state_clean in name.lower()]
            if matches:
                result = "Possible State Matches:\n"
                for code, name in matches[:5]:
                    result += f"- {name}: state_code = '{code}'\n"
                return result
            
            return "State not found. Common codes: Texas='48', California='06', New York='36'"
        
        @tool
        def get_default_assumptions() -> str:
            """Get the default assumptions used in analysis."""
            return DEFAULT_ASSUMPTIONS
        
        # Store tools
        self.tools = [
            execute_landuse_query,
            get_schema_info,
            suggest_query_examples,
            get_state_code,
            get_default_assumptions
        ]
        
        # Add map tools if enabled
        if self.enable_maps:
            @tool
            def create_choropleth_map(query_result: dict, value_column: str, title: str = "Land Use Map") -> dict:
                """Create a choropleth map from query results containing state_code and a value column."""
                # Placeholder for map generation
                return {
                    "map_type": "choropleth",
                    "title": title,
                    "value_column": value_column,
                    "note": "Map generation would create an interactive visualization here"
                }
            
            self.tools.append(create_choropleth_map)
    
    def _build_graph(self, enable_memory: bool = False):
        """Build the LangGraph workflow"""
        # Create workflow
        workflow = StateGraph(LanduseAgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            }
        )
        workflow.add_edge("tools", "agent")
        
        # Compile with optional memory
        checkpointer = MemorySaver() if enable_memory else None
        self.app = workflow.compile(checkpointer=checkpointer)
    
    def _agent_node(self, state: LanduseAgentState) -> dict:
        """Main agent node that processes queries"""
        messages = state["messages"]
        
        # Check iteration limit
        if state.get("iteration_count", 0) >= state.get("max_iterations", self.config.max_iterations):
            return {
                "messages": [AIMessage(content="Reached maximum iterations. Please try a simpler query.")]
            }
        
        # Get system prompt
        system_prompt = self._get_system_prompt(state.get("include_maps", False))
        
        # Invoke LLM with tools
        response = self.llm.bind_tools(self.tools).invoke([
            {"role": "system", "content": system_prompt},
            *messages
        ])
        
        # Update iteration count
        return {
            "messages": [response],
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    def _should_continue(self, state: LanduseAgentState) -> str:
        """Determine whether to continue processing"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If LLM makes a tool call, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        # Otherwise, end
        return "end"
    
    def _get_system_prompt(self, include_maps: bool = False) -> str:
        """Get the system prompt for the agent"""
        base_prompt = f"""You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries.

DATABASE SCHEMA:
{self.schema_info}

INSTRUCTIONS:
1. Convert natural language questions to appropriate SQL queries
2. Use the star schema joins to get meaningful results
3. Focus on relevant metrics (acres, transitions, geographic patterns)
4. Add meaningful ORDER BY clauses
5. Include appropriate LIMIT clauses
6. Explain the business meaning of results

DEFAULT ASSUMPTIONS (when user doesn't specify):
- Scenarios: Average across all scenarios (typical outcome)
- Time Periods: Full range 2012-2100
- Geographic Scope: All states/counties
- Transition Type: Focus on 'change' transitions

ALWAYS CLEARLY STATE YOUR ASSUMPTIONS in the response.

COMMON STATE CODES:
- Texas: '48', California: '06', New York: '36', Florida: '12'

QUERY PATTERNS:
- "Agricultural land loss" → Agriculture → non-Agriculture transitions
- "Forest loss" → Forest → non-Forest transitions
- "Urbanization" → Any → Urban transitions"""

        if include_maps:
            base_prompt += """

MAP GENERATION:
When results include geographic data (state_code), consider creating choropleth maps to visualize patterns.
Use the create_choropleth_map tool when appropriate."""

        return base_prompt
    
    def query(self, natural_language_query: str, include_maps: bool = None) -> str:
        """
        Process a natural language query.
        
        Args:
            natural_language_query: The user's question
            include_maps: Whether to generate maps (overrides instance setting)
        
        Returns:
            Formatted response string
        """
        try:
            # Determine if maps should be included
            use_maps = include_maps if include_maps is not None else self.enable_maps
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=natural_language_query)],
                "current_query": natural_language_query,
                "sql_queries": [],
                "query_results": [],
                "analysis_context": {},
                "iteration_count": 0,
                "max_iterations": self.config.max_iterations,
                "include_maps": use_maps
            }
            
            # Run the graph
            result = self.app.invoke(initial_state)
            
            # Extract final message
            final_message = result["messages"][-1]
            
            if hasattr(final_message, "content"):
                return final_message.content
            else:
                return str(final_message)
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"Error processing query: {str(e)}"
    
    def chat(self):
        """Interactive chat mode"""
        # Welcome message
        self.console.print(create_welcome_panel(
            str(self.db_path),
            self.model_name,
            self.api_key_masked
        ))
        
        # Show examples
        examples_panel = create_examples_panel()
        self.console.print(examples_panel)
        
        # Additional features info
        if self.enable_maps:
            self.console.print(Panel(
                "[bold cyan]🗺️ Map Generation Enabled[/bold cyan]\n"
                "Geographic results can be visualized as interactive maps!",
                border_style="cyan"
            ))
        
        while True:
            try:
                user_input = self.console.input("[bold green]🌾 Ask>[/bold green] ").strip()
                
                if user_input.lower() == 'exit':
                    self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                    break
                elif user_input.lower() == 'help':
                    self.console.print(examples_panel)
                elif user_input.lower() == 'schema':
                    schema_md = Markdown(self.schema_info)
                    self.console.print(Panel(schema_md, title="📊 Database Schema", border_style="cyan"))
                elif user_input:
                    # Show processing message
                    self.console.print()
                    with self.console.status("[bold cyan]🔍 Analyzing your query...[/bold cyan]", spinner="dots"):
                        response = self.query(user_input)
                    
                    # Format and display response
                    self.console.print()
                    self.console.print(format_response(response))
                    self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                break
            except Exception as e:
                self.logger.error(f"Chat error: {e}")
                self.console.print(format_error(e))


def main():
    """Main entry point"""
    try:
        # Check for command line arguments
        import sys
        enable_maps = "--maps" in sys.argv
        
        agent = LanduseAgent(enable_maps=enable_maps)
        agent.chat()
    except KeyboardInterrupt:
        print("\n👋 Happy analyzing!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()