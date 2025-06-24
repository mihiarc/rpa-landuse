#!/usr/bin/env python3
"""
LangGraph-based Landuse Natural Language Agent
Modern agent implementation using LangGraph for improved control flow and state management
"""

import os
import logging
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Sequence
from pathlib import Path
from dataclasses import dataclass
import operator

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .base_agent import BaseLanduseAgent
from .constants import STATE_NAMES, SCHEMA_INFO_TEMPLATE, DEFAULT_ASSUMPTIONS
from .formatting import clean_sql_query, format_query_results, format_response
from ..models import (
    AgentConfig, StateCodeInput, QueryExamplesInput,
    ExecuteQueryInput, SQLQuery, QueryResult
)
from ..utils.retry_decorators import database_retry, api_retry

# Load environment variables
load_dotenv("config/.env")
load_dotenv()


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_query: Optional[str]
    sql_queries: List[str]
    query_results: List[Dict[str, Any]]
    analysis_context: Dict[str, Any]
    iteration_count: int
    max_iterations: int


@dataclass
class LandGraphConfig:
    """Configuration for LangGraph agent"""
    db_path: str
    model_name: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.1
    max_tokens: int = 4000
    max_iterations: int = 8
    enable_memory: bool = True
    verbose: bool = False


class LangGraphLanduseAgent:
    """
    Modern LangGraph-based agent for landuse natural language queries.
    
    Features:
    - State-based conversation management
    - Tool composition and orchestration
    - Memory checkpointing for conversation continuity
    - Enhanced error handling and recovery
    - Streaming support for real-time responses
    """
    
    def __init__(self, config: Optional[LandGraphConfig] = None):
        self.console = Console()
        
        # Configuration
        if config is None:
            config = LandGraphConfig(
                db_path=os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
                model_name=os.getenv('LANDUSE_MODEL', 'claude-3-5-sonnet-20241022'),
                temperature=float(os.getenv('TEMPERATURE', '0.1')),
                max_tokens=int(os.getenv('MAX_TOKENS', '4000')),
                max_iterations=int(os.getenv('LANDUSE_MAX_ITERATIONS', '8')),
                verbose=os.getenv('VERBOSE', 'false').lower() == 'true'
            )
        
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
        
        # Create graph
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
    
    def _get_schema_info(self) -> str:
        """Get comprehensive schema information"""
        try:
            import duckdb
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
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
    
    def _create_tools(self) -> List:
        """Create tools for the LangGraph agent"""
        
        @tool
        @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
        def execute_landuse_query(sql_query: str) -> str:
            """
            Execute DuckDB SQL query on the landuse database.
            
            Args:
                sql_query: SQL query string to execute
                
            Returns:
                Formatted query results or error message
            """
            try:
                import duckdb
                import time
                
                # Validate and clean query
                input_data = ExecuteQueryInput(sql_query=sql_query)
                query_obj = SQLQuery(sql=clean_sql_query(input_data.sql_query))
                sql_query = query_obj.sql
                
                # Connect to database
                conn = duckdb.connect(str(self.db_path), read_only=True)
                
                # Add LIMIT if not present
                if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                    query_trimmed = sql_query.rstrip().rstrip(';').rstrip()
                    sql_query = f"{query_trimmed} LIMIT 1000"
                
                # Execute query
                start_time = time.time()
                result = conn.execute(sql_query)
                execution_time = time.time() - start_time
                
                if result is None:
                    conn.close()
                    return f"❌ Query returned no result object\nSQL: {sql_query}"
                
                df = result.df()
                conn.close()
                
                # Format results
                return format_query_results(df, sql_query, max_display_rows=50)
                
            except Exception as e:
                self.logger.error(f"Error executing query: {e}")
                return f"❌ Error executing query: {str(e)}\nSQL: {sql_query}"
        
        @tool
        def get_schema_info(query: str = "") -> str:
            """
            Get detailed schema information about the landuse database.
            
            Args:
                query: Optional specific table or column to get info about
                
            Returns:
                Schema information
            """
            return self.schema_info
        
        @tool
        def get_state_code(state_name: str) -> str:
            """
            Get the numeric state code for a given state name.
            
            Args:
                state_name: Name of the state to look up
                
            Returns:
                State code information
            """
            try:
                input_data = StateCodeInput(state_name=state_name)
                name_to_code = {v.lower(): k for k, v in STATE_NAMES.items()}
                state_clean = input_data.state_name.strip().lower()
                
                if state_clean in name_to_code:
                    code = name_to_code[state_clean]
                    return f"🗺️ **State Code Found**\n\n{STATE_NAMES[code]} has state_code = '{code}' in the database.\n\nExample query:\n```sql\nSELECT COUNT(*) FROM dim_geography WHERE state_code = '{code}'\n```"
                
                matches = [(code, name) for code, name in STATE_NAMES.items() if state_clean in name.lower()]
                if matches:
                    result = "🗺️ **Possible State Matches:**\n\n"
                    for code, name in matches[:5]:
                        result += f"- {name}: state_code = '{code}'\n"
                    return result
                
                return """🗺️ **State Code Not Found**
                
Common state codes in the database:
- Alabama: '01'
- California: '06'  
- Florida: '12'
- Illinois: '17'
- New York: '36'
- Texas: '48'

Note: Use state_code in WHERE clauses as a string (with quotes).
"""
            except Exception as e:
                return f"❌ Error getting state code: {str(e)}"
        
        @tool
        def suggest_query_examples(category: str = "general") -> str:
            """
            Get example queries for common landuse analysis patterns.
            
            Args:
                category: Category of examples (general, agricultural_loss, urbanization, etc.)
                
            Returns:
                Example queries and patterns
            """
            examples = {
                "agricultural_loss": """
-- Agricultural land loss (default: averaged across all scenarios, full time period)
SELECT 
    AVG(f.acres) as avg_acres_lost_per_scenario,
    SUM(f.acres) as total_acres_lost,
    COUNT(DISTINCT s.scenario_id) as scenarios_included
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
WHERE fl.landuse_category = 'Agriculture' 
  AND f.to_landuse_id != f.from_landuse_id
  AND f.transition_type = 'change';
""",
                "urbanization": """
-- Urbanization pressure (default: averaged across scenarios, full time period)
SELECT 
    g.state_code,
    fl.landuse_name as from_landuse,
    AVG(f.acres) as avg_acres_urbanized_per_scenario,
    SUM(f.acres) as total_acres_urbanized
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE tl.landuse_name = 'Urban'
  AND f.transition_type = 'change'
GROUP BY g.state_code, fl.landuse_name
ORDER BY total_acres_urbanized DESC;
"""
            }
            
            if category.lower() in examples:
                return f"💡 **Example Query - {category.title()}:**\n```sql\n{examples[category.lower()]}\n```"
            
            result = "💡 **Common Query Examples:**\n\n"
            for name, sql in examples.items():
                result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"
            
            return result
        
        return [execute_landuse_query, get_schema_info, get_state_code, suggest_query_examples]
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        # Define nodes
        def agent_node(state: AgentState) -> Dict[str, Any]:
            """Main agent reasoning node"""
            messages = state["messages"]
            iteration_count = state.get("iteration_count", 0)
            max_iterations = state.get("max_iterations", self.config.max_iterations)
            
            # Check iteration limit
            if iteration_count >= max_iterations:
                return {
                    "messages": [AIMessage(content=f"🔄 Reached maximum iterations ({max_iterations}). Please try a simpler query.")],
                    "iteration_count": iteration_count + 1
                }
            
            # System message with schema and instructions
            system_message = SystemMessage(content=f"""
You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries.

DATABASE SCHEMA:
{self.schema_info}

INSTRUCTIONS:
1. Convert natural language questions about landuse data into appropriate SQL queries
2. Always use the star schema joins to get meaningful results
3. Focus on the most relevant metrics (acres, transition counts, geographic patterns)
4. Use appropriate aggregations (SUM, COUNT, AVG) and GROUP BY clauses
5. Add meaningful ORDER BY clauses to show most significant results first
6. Include appropriate LIMIT clauses for large datasets
7. Explain the business meaning of results

DEFAULT ASSUMPTIONS (apply when user doesn't specify):
- **Scenarios**: Use AVERAGE across all scenarios (represent typical/mean outcome)
- **Time Periods**: Use FULL time range (all years 2012-2100) 
- **Geographic Scope**: All states/counties unless specified
- **Transition Type**: Focus on 'change' transitions (exclude same-to-same)

ALWAYS CLEARLY STATE YOUR ASSUMPTIONS in the response.

Use the available tools to execute queries and provide comprehensive analysis.
""")
            
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
        
        def should_continue(state: AgentState) -> str:
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
        workflow = StateGraph(AgentState)
        
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
        Process a natural language query using LangGraph.
        
        Args:
            natural_language_query: The user's question
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Formatted response
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
                "max_iterations": self.config.max_iterations
            }
            
            # Configure execution
            config = {"recursion_limit": self.config.max_iterations + 2}
            if thread_id and self.config.enable_memory:
                config["configurable"] = {"thread_id": thread_id}
            
            # Execute the graph
            result = self.graph.invoke(initial_state, config=config)
            
            # Extract final response
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    return last_message.content
                else:
                    return str(last_message)
            
            return "No response generated"
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"❌ Error processing query: {str(e)}"
    
    def stream_query(self, natural_language_query: str, thread_id: Optional[str] = None):
        """
        Stream the processing of a query for real-time updates.
        
        Args:
            natural_language_query: The user's question
            thread_id: Optional thread ID for conversation continuity
            
        Yields:
            Processing updates
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
                "max_iterations": self.config.max_iterations
            }
            
            # Configure execution
            config = {"recursion_limit": self.config.max_iterations + 2}
            if thread_id and self.config.enable_memory:
                config["configurable"] = {"thread_id": thread_id}
            
            # Stream the execution
            for chunk in self.graph.stream(initial_state, config=config):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Error streaming query: {e}")
            yield {"error": f"❌ Error streaming query: {str(e)}"}
    
    def chat(self):
        """Interactive chat mode with conversation memory"""
        # Welcome message
        welcome_panel = Panel(
            f"""[bold cyan]🚀 LangGraph Landuse Agent[/bold cyan]

[yellow]Database:[/yellow] {self.db_path}
[yellow]Model:[/yellow] {self.config.model_name}
[yellow]Memory:[/yellow] {'Enabled' if self.config.enable_memory else 'Disabled'}
[yellow]Max Iterations:[/yellow] {self.config.max_iterations}

[green]Commands:[/green]
• Type your landuse questions naturally
• 'help' - Show examples
• 'schema' - Show database schema
• 'exit' - Quit

[dim]Enhanced with LangGraph for better conversation flow and memory![/dim]""",
            title="🌾 Enhanced Landuse Agent",
            border_style="green"
        )
        self.console.print(welcome_panel)
        
        # Generate thread ID for this session
        import uuid
        thread_id = str(uuid.uuid4()) if self.config.enable_memory else None
        
        # Show examples
        examples_panel = Panel(
            """[bold cyan]🚀 Try these questions:[/bold cyan]

[yellow]Quick Analysis:[/yellow]
• "How much agricultural land is being lost?"
• "What's the rate of forest loss?"
• "How much urban expansion is happening?"

[yellow]Geographic Analysis:[/yellow]
• "Which states have the most urban expansion?"
• "Compare agricultural changes in California vs Texas"
• "Show me land use changes in the Southeast"

[yellow]Climate Scenarios:[/yellow]
• "Compare forest loss between RCP45 and RCP85"
• "Which scenarios show the most agricultural loss?"
• "How do different climate scenarios affect urbanization?"

[green]💡 The agent uses smart defaults and clearly states assumptions![/green]""",
            title="🌾 Example Questions",
            border_style="blue"
        )
        self.console.print(examples_panel)
        
        while True:
            try:
                user_input = self.console.input("[bold green]🌾 LangGraph>[/bold green] ").strip()
                
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
                    with self.console.status("[bold cyan]🔍 Processing with LangGraph...[/bold cyan]", spinner="dots"):
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


def main():
    """Main entry point for the LangGraph landuse agent"""
    try:
        config = LandGraphConfig(
            db_path=os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
            verbose=os.getenv('VERBOSE', 'false').lower() == 'true'
        )
        agent = LangGraphLanduseAgent(config)
        agent.chat()
    except KeyboardInterrupt:
        print("\n👋 Happy analyzing!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()