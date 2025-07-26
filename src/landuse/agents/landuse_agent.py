"""Consolidated landuse agent with modern LangGraph architecture."""

import os
import time
from typing import Any, Optional, TypedDict

import duckdb
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
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
from landuse.tools.state_lookup_tool import create_state_lookup_tool
from landuse.utils.retry_decorators import database_retry


class AgentState(TypedDict):
    """State definition for the landuse agent
    ."""
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
        self.knowledge_base = None
        
        # Initialize conversation history for simple mode
        self.conversation_history = []  # Store (role, content) tuples
        self.max_history_length = 20  # Keep last N messages
        
        # Initialize knowledge base if enabled
        if self.config.enable_knowledge_base:
            self._initialize_knowledge_base()
        
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

    def _initialize_knowledge_base(self):
        """Initialize the knowledge base if enabled."""
        try:
            from landuse.knowledge import RPAKnowledgeBase
            
            self.console.print("[yellow]Initializing RPA knowledge base...[/yellow]")
            self.knowledge_base = RPAKnowledgeBase(
                docs_path=self.config.knowledge_base_path,
                persist_directory=self.config.chroma_persist_dir
            )
            self.knowledge_base.initialize()
            self.console.print("[green]✓ Knowledge base ready[/green]")
        except Exception as e:
            self.console.print(f"[red]Warning: Failed to initialize knowledge base: {str(e)}[/red]")
            self.console.print("[yellow]Continuing without knowledge base...[/yellow]")
            self.knowledge_base = None

    def _create_tools(self) -> list[BaseTool]:
        """Create tools for the agent."""
        tools = [
            create_execute_query_tool(self.config, self.db_connection, self.schema),
            create_analysis_tool(),
            create_schema_tool(self.schema),
            create_state_lookup_tool()
        ]
        
        # Add knowledge base retriever if available
        if self.knowledge_base:
            try:
                retriever_tool = self.knowledge_base.create_retriever_tool()
                tools.append(retriever_tool)
                self.console.print("[green]✓ Added RPA documentation retriever tool[/green]")
            except Exception as e:
                self.console.print(f"[red]Warning: Failed to create retriever tool: {str(e)}[/red]")
        
        return tools

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

        # Compile with memory if enabled
        if self.config.enable_memory:
            return workflow.compile(checkpointer=self.memory)
        else:
            return workflow.compile()

    def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """Main agent node that decides next action."""
        messages = state["messages"]

        # Ensure we have proper message types
        if not messages:
            messages = []
        
        # Add system prompt as first message if needed
        has_system = any(
            isinstance(m, (HumanMessage, AIMessage)) and 
            self.system_prompt[:50] in str(m.content) 
            for m in messages[:1]
        )
        
        if not has_system:
            messages = [HumanMessage(content=self.system_prompt)] + messages

        # Get LLM response with tools bound
        response = self.llm.bind_tools(self.tools).invoke(messages)

        # Update state with new message
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
    
    def _update_conversation_history(self, question: str, response: str) -> None:
        """Update conversation history with new question and response."""
        # Add user question
        self.conversation_history.append(("user", question))
        # Add assistant response
        self.conversation_history.append(("assistant", response))
        
        # Trim history if it gets too long (keep last N messages)
        if len(self.conversation_history) > self.max_history_length:
            # Keep only the last max_history_length messages
            self.conversation_history = self.conversation_history[-self.max_history_length:]

    def _execute_query(self, query: str) -> dict[str, Any]:
        """Execute a SQL query with standard error handling and formatting."""
        cleaned_query = clean_sql_query(query)
        
        if self.config.debug:
            print(f"\nDEBUG _execute_query: Executing SQL query")
            print(f"DEBUG _execute_query: Query: {cleaned_query}")

        try:
            conn = self.db_connection

            # Add row limit if not present
            if "limit" not in cleaned_query.lower():
                cleaned_query = f"{cleaned_query.rstrip(';')} LIMIT {self.config.max_query_rows}"

            result = conn.execute(cleaned_query).fetchall()
            columns = [desc[0] for desc in conn.description] if conn.description else []
            
            if self.config.debug:
                print(f"DEBUG _execute_query: Result row count: {len(result)}")
                print(f"DEBUG _execute_query: Columns: {columns}")
                if result and len(result) > 0:
                    print(f"DEBUG _execute_query: First row: {result[0]}")
                else:
                    print("DEBUG _execute_query: No rows returned")

            # Convert to DataFrame for formatting
            import pandas as pd
            df = pd.DataFrame(result, columns=columns)
            
            # Format results - format_query_results expects (DataFrame, sql_query)
            formatted_results = format_query_results(df, cleaned_query)

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
            
            if self.config.debug:
                print(f"DEBUG _execute_query: SQL Error: {error_msg}")
                print(f"DEBUG _execute_query: Suggestion: {suggestion}")
                import traceback
                traceback.print_exc()

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
            return "Check table names. Available tables: fact_landuse_transitions, dim_scenario, dim_geography_enhanced, dim_landuse, dim_time"
        elif "syntax error" in error_lower:
            return "Check SQL syntax. Common issues: missing commas, unclosed quotes, invalid keywords."
        elif "ambiguous column" in error_lower:
            return "Specify table name for columns used in joins (e.g., fact.year instead of just year)"
        else:
            return "Check the query syntax and ensure all table/column names match the schema exactly."

    def simple_query(self, question: str) -> str:
        """Execute a query using simple direct LLM interaction without LangGraph state management."""
        try:
            # Build conversation with history
            messages = [HumanMessage(content=self.system_prompt)]
            
            # Add conversation history
            for role, content in self.conversation_history:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
            
            # Add current question
            messages.append(HumanMessage(content=question))
            
            # Get initial response
            response = self.llm.bind_tools(self.tools).invoke(messages)
            messages.append(response)
            
            if self.config.debug:
                print(f"DEBUG: Initial response type: {type(response)}")
                print(f"DEBUG: Has tool calls: {hasattr(response, 'tool_calls') and bool(response.tool_calls)}")
                if hasattr(response, 'content'):
                    print(f"DEBUG: Initial content: {response.content[:200] if response.content else 'Empty'}")
            
            # Handle tool calls if any
            max_iterations = 3
            iteration = 0
            
            # Store tool results for creative formatting
            query_results = []
            analysis_results = []
            
            while hasattr(response, 'tool_calls') and response.tool_calls and iteration < max_iterations:
                iteration += 1
                
                # Execute each tool call and add proper ToolMessage
                for tool_call in response.tool_calls:
                    # Find the matching tool
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]  # Important: use the tool call ID
                    
                    # Execute the tool
                    tool_result = None
                    for tool in self.tools:
                        if tool.name == tool_name:
                            try:
                                if self.config.debug:
                                    print(f"\nDEBUG: Executing tool '{tool_name}'")
                                    print(f"DEBUG: Tool args: {tool_args}")
                                    
                                tool_result = tool.invoke(tool_args)
                                
                                if self.config.debug:
                                    result_str = str(tool_result)
                                    print(f"DEBUG: Tool result length: {len(result_str)} chars")
                                    
                                    # Show more details for query execution
                                    if tool_name == "execute_landuse_query" and "query" in tool_args:
                                        print(f"DEBUG: SQL Query: {tool_args['query']}")
                                        if "rows returned" in result_str:
                                            # Extract row count
                                            import re
                                            row_match = re.search(r'(\d+) rows returned', result_str)
                                            if row_match:
                                                print(f"DEBUG: Query returned {row_match.group(1)} rows")
                                        if "No results found" in result_str:
                                            print("DEBUG: Query returned NO RESULTS")
                                        # Show first 300 chars of results
                                        print(f"DEBUG: Query result preview: {result_str[:300]}...")
                                    
                                    # Show analysis details
                                    elif tool_name == "analyze_landuse_results":
                                        print(f"DEBUG: Analysis preview: {result_str[:200]}...")
                                
                                # Store results for formatting
                                if tool_name == "execute_landuse_query":
                                    query_results.append(str(tool_result))
                                elif tool_name == "analyze_landuse_results":
                                    analysis_results.append(str(tool_result))
                                    
                                break
                            except Exception as e:
                                error_msg = f"Tool error: {str(e)}"
                                if self.config.debug:
                                    print(f"DEBUG: Tool error: {error_msg}")
                                    import traceback
                                    traceback.print_exc()
                                tool_result = error_msg
                    
                    if tool_result is None:
                        tool_result = f"Unknown tool: {tool_name}"
                    
                    # Add tool result using proper ToolMessage format
                    messages.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_id
                    ))
                
                # Get next response
                response = self.llm.bind_tools(self.tools).invoke(messages)
                messages.append(response)
                
                if self.config.debug:
                    print(f"DEBUG: Response after tool execution: {type(response)}")
                    if hasattr(response, 'content'):
                        print(f"DEBUG: Response content type: {type(response.content)}")
                        print(f"DEBUG: Response content: {response.content[:200] if response.content else 'None'}")
            
            # Extract the final text content from the response
            if self.config.debug:
                print(f"\nDEBUG: Extracting final content from response")
                print(f"DEBUG: Response type: {type(response)}")
                print(f"DEBUG: Has content attr: {hasattr(response, 'content')}")
                print(f"DEBUG: Has text attr: {hasattr(response, 'text')}")
                
            final_content = ""
            if hasattr(response, 'content'):
                content = response.content
                if self.config.debug:
                    print(f"DEBUG: Content type: {type(content)}")
                    print(f"DEBUG: Content value: {content[:200] if content else 'None'}")
                    
                # Handle different content formats
                if isinstance(content, list):
                    # Extract text from list of content blocks
                    text_parts = []
                    for i, item in enumerate(content):
                        if self.config.debug:
                            print(f"DEBUG: Content item {i}: type={type(item)}, value={str(item)[:100]}")
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif isinstance(item, str):
                            text_parts.append(item)
                        else:
                            # Skip non-text items like tool calls
                            continue
                    final_content = ' '.join(text_parts)
                else:
                    final_content = str(content)
            elif hasattr(response, 'text'):
                final_content = str(response.text)
            else:
                final_content = str(response)
            
            # If we still have no content, check if we have tool results we can summarize
            if not final_content.strip() and (query_results or analysis_results):
                if self.config.debug:
                    print(f"\nDEBUG: Final content is empty, checking tool results")
                    print(f"DEBUG: Query results count: {len(query_results)}")
                    print(f"DEBUG: Analysis results count: {len(analysis_results)}")
                    
                # Build a response from the tool results
                if query_results and analysis_results:
                    final_content = f"{query_results[-1]}\n\n{analysis_results[-1]}"
                elif query_results:
                    final_content = query_results[-1]
                elif analysis_results:
                    final_content = analysis_results[-1]
                    
                # If still empty, provide helpful message
                if not final_content.strip():
                    final_content = "I executed the query but couldn't generate a formatted response. The query completed successfully but may have returned no results."
            
            # Update conversation history
            self._update_conversation_history(question, final_content)
            
            # Return clean final content without any special formatting
            if self.config.debug:
                print(f"\nDEBUG: Final content length: {len(final_content)}")
                print(f"DEBUG: Final content preview: {final_content[:200]}...")
                print("DEBUG: === End of simple_query execution ===")
                
            return final_content
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            # Still update history even on error
            self._update_conversation_history(question, error_msg)
            return error_msg

    def _graph_query(self, question: str, thread_id: Optional[str] = None) -> str:
        """Execute a query using the LangGraph workflow."""
        try:
            # Build graph if not already built
            if not self.graph:
                self.graph = self._build_graph()
            
            # Prepare initial state with conversation history
            initial_messages = [HumanMessage(content=self.system_prompt)]
            
            # Add conversation history to context
            for role, content in self.conversation_history:
                if role == "user":
                    initial_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    initial_messages.append(AIMessage(content=content))
            
            # Add current question
            initial_messages.append(HumanMessage(content=question))
            
            initial_state = {
                "messages": initial_messages,
                "context": {},
                "iteration_count": 0,
                "max_iterations": self.config.max_iterations
            }
            
            # Prepare config with thread_id for memory
            config = {}
            if thread_id and self.config.enable_memory:
                config = {"configurable": {"thread_id": thread_id}}
            
            # Execute the graph
            result = self.graph.invoke(initial_state, config=config)
            
            # Extract the final response from messages
            if result and "messages" in result:
                messages = result["messages"]
                # Find the last AI message that's not a tool call
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
                        return str(msg.content)
                    elif isinstance(msg, AIMessage) and hasattr(msg, 'content'):
                        # Handle AIMessage with content even if it has tool_calls
                        content = msg.content
                        if isinstance(content, list):
                            # Extract text content from list
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_parts.append(item.get('text', ''))
                                elif isinstance(item, str):
                                    text_parts.append(item)
                            if text_parts:
                                final_response = ' '.join(text_parts)
                                self._update_conversation_history(question, final_response)
                                return final_response
                        elif content:
                            final_response = str(content)
                            self._update_conversation_history(question, final_response)
                            return final_response
            
            default_response = "I couldn't generate a proper response. Please try rephrasing your question."
            self._update_conversation_history(question, default_response)
            return default_response
            
        except Exception as e:
            error_msg = f"Error in graph execution: {str(e)}"
            if self.config.debug:
                import traceback
                self.console.print(f"[red]DEBUG: {error_msg}[/red]")
                self.console.print(f"[red]{traceback.format_exc()}[/red]")
            error_response = f"I encountered an error while processing your query: {str(e)}"
            self._update_conversation_history(question, error_response)
            return error_response

    def query(self, question: str, use_graph: bool = False, thread_id: Optional[str] = None) -> str:
        """
        Execute a natural language query using the agent.
        
        Args:
            question: The natural language question to answer
            use_graph: Whether to use the full LangGraph workflow (default: False for stability)
            thread_id: Optional thread ID for conversation memory (only used with graph)
            
        Returns:
            The agent's response as a string
        """
        if use_graph:
            return self._graph_query(question, thread_id)
        else:
            # Use the simple approach for stability
            return self.simple_query(question)

    def stream_query(self, question: str, thread_id: Optional[str] = None) -> Any:
        """
        Stream responses for real-time interaction.

        Args:
            question: Natural language question
            thread_id: Optional thread ID for conversation memory

        Yields:
            Streaming response chunks
        """
        if not self.graph:
            self.graph = self._build_graph()

        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "context": {},
            "iteration_count": 0,
            "max_iterations": self.config.max_iterations
        }
        
        # Prepare config
        config = {}
        if thread_id and self.config.enable_memory:
            config = {"configurable": {"thread_id": thread_id}}
        elif not thread_id:
            config = {"configurable": {"thread_id": f"landuse-stream-{int(time.time())}"}}

        # Stream the response
        try:
            for chunk in self.graph.stream(initial_state, config=config):
                yield chunk
        except Exception as e:
            yield {"error": f"Streaming error: {str(e)}"}

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
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        self.console.print("[yellow]Conversation history cleared.[/yellow]")
    
    def chat(self) -> None:
        """Interactive chat interface for the agent."""
        self.console.print(Panel.fit(
            "[bold green]RPA Land Use Analytics Agent[/bold green]\n"
            "Ask questions about land use projections and transitions.\n"
            "Type 'exit' to quit, 'help' for examples, 'clear' to reset conversation.",
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
                
                if question.lower() == 'clear':
                    self.clear_history()
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

    @property
    def model_name(self) -> str:
        """Get the model name from configuration."""
        return self.config.model_name

    def _get_schema_help(self) -> str:
        """Get user-friendly schema information for display in the UI."""
        return self.schema
    
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up resources."""
        if hasattr(self, 'db_connection') and self.db_connection:
            self.db_connection.close()
        # Knowledge base (Chroma) will persist automatically