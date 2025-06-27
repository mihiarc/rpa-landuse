#!/usr/bin/env python3
"""
Base LangGraph Agent for Landuse Analysis
Modern graph-based architecture for all landuse agents
"""

import logging
import operator
import os
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Optional, TypedDict, Union

import duckdb
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool, tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..config import LanduseConfig
from ..models import ExecuteQueryInput, QueryInput, QueryResult, SQLQuery
from ..utils.retry_decorators import api_retry, database_retry
from .constants import DB_CONFIG, QUERY_EXAMPLES, SCHEMA_INFO_TEMPLATE
from .formatting import (
    clean_sql_query,
    create_examples_panel,
    create_welcome_panel,
    format_error,
    format_query_results,
    format_response,
)

# Load environment variables
load_dotenv("config/.env")
load_dotenv()


class BaseLanduseState(TypedDict):
    """Base state for all LangGraph landuse agents"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_query: Optional[str]
    sql_queries: list[str]
    query_results: list[dict[str, Any]]
    analysis_context: dict[str, Any]
    iteration_count: int
    max_iterations: int


class BaseLangGraphAgent(ABC):
    """
    Base class for all LangGraph-based landuse agents.
    
    This modern architecture provides:
    - Graph-based control flow
    - State management
    - Tool integration
    - Memory/checkpointing support
    - Streaming capabilities
    """

    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the LangGraph agent"""
        self.console = Console()
        
        # Configuration
        if config is None:
            config = LanduseConfig.for_agent_type('basic')
        
        self.config = config
        self.db_path = Path(config.db_path)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize LLM
        self._init_llm()
        
        # Get schema information
        self.schema_info = self._get_schema_info()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create the graph
        self.graph = self._create_graph()
        
        # Setup memory if enabled
        if config.enable_memory:
            self.memory = MemorySaver()
            self.graph = self.graph.compile(checkpointer=self.memory)
        else:
            self.graph = self.graph.compile()
        
        self.logger.info(f"LangGraph agent initialized with model: {config.model_name}")

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
            # Safe: These table names are hardcoded, not from user input
            tables = ['dim_scenario', 'dim_time', 'dim_geography_enhanced', 'dim_landuse', 'fact_landuse_transitions']
            
            for table in tables:
                try:
                    # Safe: table names from hardcoded list above
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
                pass  # Optional info
            
            conn.close()
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"

    def _create_tools(self) -> list:
        """Create tools for the agent - can be overridden by subclasses"""
        # Create the core tools using @tool decorator for LangGraph compatibility
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
        
        tools = [execute_landuse_query, get_schema_info, suggest_query_examples]
        
        # Allow subclasses to add additional tools
        additional_tools = self._get_additional_tools()
        if additional_tools:
            tools.extend(additional_tools)
        
        return tools

    def _get_additional_tools(self) -> Optional[list]:
        """Hook for subclasses to add additional tools"""
        return None

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
            
            # Validate query if needed (hook for subclasses)
            validation_result = self._validate_query(sql_query)
            if validation_result:
                return validation_result
            
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
                query_result = QueryResult(
                    success=False,
                    error="Query returned no result object",
                    query=sql_query
                )
                return f"❌ {query_result.error}\nSQL: {sql_query}"
            
            df = result.df()
            conn.close()
            
            # Create QueryResult object
            query_result = QueryResult(
                success=True,
                data=df,
                execution_time=execution_time,
                query=sql_query
            )
            
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
            query_result = QueryResult(
                success=False,
                error=str(e),
                query=sql_query if 'sql_query' in locals() else 'Unknown'
            )
            return f"❌ Error executing query: {query_result.error}\nSQL: {query_result.query}"

    def _validate_query(self, sql_query: str) -> Optional[str]:
        """Hook for subclasses to validate queries before execution"""
        return None

    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns"""
        if category in QUERY_EXAMPLES:
            return f"💡 **Example Query - {category.title()}:**\n```sql\n{QUERY_EXAMPLES[category]}\n```"
        
        result = "💡 **Common Query Examples:**\n\n"
        for name, sql in QUERY_EXAMPLES.items():
            result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"
        
        return result

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent - must be implemented by subclasses"""
        pass

    @abstractmethod
    def _get_state_class(self):
        """Get the state class for the graph - can be overridden by subclasses"""
        return BaseLanduseState

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        state_class = self._get_state_class()
        
        # Define nodes
        def agent_node(state: state_class) -> dict[str, Any]:
            """Agent reasoning node"""
            messages = state["messages"]
            iteration_count = state.get("iteration_count", 0)
            max_iterations = state.get("max_iterations", self.config.max_iterations)
            
            # Check iteration limit
            if iteration_count >= max_iterations:
                return {
                    "messages": [AIMessage(content=f"🔄 Reached maximum iterations ({max_iterations}). Please try a simpler query.")],
                    "iteration_count": iteration_count + 1
                }
            
            # Get system prompt from subclass
            system_prompt = self._get_system_prompt()
            system_message = SystemMessage(content=system_prompt)
            
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
        
        def should_continue(state: state_class) -> str:
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
        workflow = StateGraph(state_class)
        
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
        Process a natural language query using the LangGraph workflow.
        
        Args:
            natural_language_query: The user's question
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Formatted response from the agent
        """
        try:
            # Validate input
            query_input = QueryInput(query=natural_language_query)
            
            # Pre-query hook
            pre_result = self._pre_query_hook(query_input.query)
            if pre_result:
                return pre_result
            
            # Log query start
            self.logger.info(f"Processing query: {query_input.query[:100]}...")
            
            # Get state class
            state_class = self._get_state_class()
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=query_input.query)],
                "current_query": query_input.query,
                "sql_queries": [],
                "query_results": [],
                "analysis_context": {},
                "iteration_count": 0,
                "max_iterations": self.config.max_iterations
            }
            
            # Add any additional state fields from subclasses
            additional_state = self._get_additional_initial_state()
            if additional_state:
                initial_state.update(additional_state)
            
            # Configure execution
            config = {"recursion_limit": self.config.max_iterations + 2}
            if self.config.enable_memory and thread_id:
                config["configurable"] = {"thread_id": thread_id}
            
            # Execute the graph
            result = self.graph.invoke(initial_state, config=config)
            
            # Extract final response
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                    # Post-query hook
                    return self._post_query_hook(output, result)
                else:
                    return str(last_message)
            
            return "No response generated"
            
        except TimeoutError:
            self.logger.error(f"Query timed out after {self.config.max_execution_time} seconds")
            return (f"⏱️ Query timed out after {self.config.max_execution_time} seconds. "
                   f"Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME.")
        except Exception as e:
            # Check for specific error messages
            error_msg = str(e)
            if "Agent stopped due to iteration limit" in error_msg:
                self.logger.warning(f"Agent hit iteration limit: {error_msg}")
                return (f"🔄 Query required too many steps (>{self.config.max_iterations}). "
                       f"Try a simpler query or increase LANDUSE_MAX_ITERATIONS.")
            elif "Agent stopped due to time limit" in error_msg:
                self.logger.warning(f"Agent hit time limit: {error_msg}")
                return (f"⏱️ Query took too long (>{self.config.max_execution_time}s). "
                       f"Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME.")
            else:
                self.logger.error(f"Error processing query: {e}")
                return f"❌ Error processing query: {error_msg}"

    def _get_additional_initial_state(self) -> Optional[dict[str, Any]]:
        """Hook for subclasses to add additional initial state"""
        return None

    def _pre_query_hook(self, query: str) -> Optional[str]:
        """Hook called before query processing"""
        return None

    def _post_query_hook(self, output: str, full_state: dict[str, Any]) -> str:
        """Hook called after query processing"""
        return output

    def chat(self):
        """Interactive chat mode for landuse queries"""
        # Welcome message
        self.console.print(create_welcome_panel(
            str(self.db_path),
            self.config.model_name,
            self.api_key_masked
        ))
        
        # Show additional info if needed (hook for subclasses)
        self._show_chat_intro()
        
        # Show examples
        examples_panel = create_examples_panel()
        self.console.print(examples_panel)
        
        # Generate thread ID for this session if memory enabled
        thread_id = None
        if self.config.enable_memory:
            import uuid
            thread_id = str(uuid.uuid4())
        
        while True:
            try:
                user_input = self.console.input("[bold green]🌲 RPA Analytics>[/bold green] ").strip()
                
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
                self.console.print(format_error(e))

    def _show_chat_intro(self):
        """Hook for subclasses to show additional intro information"""
        # This is intentionally empty - subclasses can override
        return