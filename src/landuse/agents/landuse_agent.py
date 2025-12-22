"""Refactored landuse agent with modern architecture and separated concerns."""

# Import PromptManager for versioned prompts
import sys
import time
from pathlib import Path
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from landuse.agents.conversation_manager import ConversationManager
from landuse.agents.database_manager import DatabaseManager
from landuse.agents.graph_builder import GraphBuilder
from landuse.agents.llm_manager import LLMManager
from landuse.agents.prompts import get_system_prompt
from landuse.agents.query_executor import QueryExecutor

# Add prompts directory to path if needed
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
try:
    from prompts.prompt_manager import PromptManager
except ImportError:
    # Fallback if PromptManager not available
    PromptManager = None
from landuse.agents.state import AgentState
from landuse.core.app_config import AppConfig
from landuse.exceptions import GraphExecutionError, LanduseError, RateLimitError, ToolExecutionError, wrap_exception
from landuse.tools.common_tools import create_analysis_tool, create_execute_query_tool, create_schema_tool
from landuse.tools.state_lookup_tool import create_state_lookup_tool
from landuse.utils.retry_decorators import invoke_llm_with_retry
from landuse.utils.security import RateLimiter


class LanduseAgent:
    """
    Refactored landuse agent with separated concerns and modern architecture.

    Uses dependency injection and follows Single Responsibility Principle by delegating
    specific responsibilities to specialized manager classes:
    - LLMManager: Handles LLM creation and configuration
    - DatabaseManager: Manages database connections and schema
    - ConversationManager: Handles conversation history
    - QueryExecutor: Executes SQL queries with error handling
    - GraphBuilder: Constructs LangGraph workflows
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize the landuse agent with configuration using dependency injection."""
        self.config = config or AppConfig()
        self.debug = self.config.logging.level == "DEBUG"
        self.console = Console()

        # Initialize rate limiter using security config
        self.rate_limiter = RateLimiter(
            max_calls=self.config.security.rate_limit_calls, time_window=self.config.security.rate_limit_window
        )

        # Initialize component managers
        self.llm_manager = LLMManager(self.config, self.console)
        self.database_manager = DatabaseManager(self.config, self.console)
        self.conversation_manager = ConversationManager(
            max_history_length=self.config.agent.conversation_history_limit, console=self.console
        )

        # Create core components
        self.llm = self.llm_manager.create_llm()
        self.db_connection = self.database_manager.get_connection()
        self.schema = self.database_manager.get_schema()

        # Initialize query executor
        self.query_executor = QueryExecutor(self.config, self.db_connection, self.console)

        # Create tools and system prompt
        self.tools = self._create_tools()

        # Use PromptManager if available, otherwise fall back to legacy
        if PromptManager is not None:
            try:
                self.prompt_manager = PromptManager()
                self.system_prompt = self.prompt_manager.get_prompt_with_schema(schema_info=self.schema)
                # Log which version is being used
                self.console.print(f"[green]✓ Using prompt version: {self.prompt_manager.active_version}[/green]")
            except Exception as e:
                # Fall back to legacy if PromptManager fails
                self.console.print(f"[yellow]⚠ PromptManager not available, using legacy prompts: {e}[/yellow]")
                self.system_prompt = get_system_prompt(
                    include_maps=self.config.features.enable_map_generation,
                    analysis_style="detailed",
                    domain_focus=None,
                    schema_info=self.schema,
                )
        else:
            # Legacy prompt system
            self.system_prompt = get_system_prompt(
                include_maps=self.config.features.enable_map_generation,
                analysis_style="detailed",
                domain_focus=None,
                schema_info=self.schema,
            )

        # Initialize graph builder
        self.graph_builder = GraphBuilder(self.config, self.llm, self.tools, self.system_prompt, self.console)
        self.graph = None

    def _create_tools(self) -> list[BaseTool]:
        """Create tools for the agent."""
        tools = [
            create_execute_query_tool(self.config, self.db_connection, self.schema),
            create_analysis_tool(),
            create_schema_tool(self.schema),
            create_state_lookup_tool(),
        ]

        return tools

    def get_dynamic_system_prompt(self, question: str) -> str:
        """
        Get appropriate system prompt based on query content.

        Args:
            question: User's natural language question

        Returns:
            Specialized system prompt for the query
        """
        # Always use the standard system prompt
        # (Dynamic prompt selection was removed as specialized prompts were not effective)
        return self.system_prompt

    def _check_rate_limit(self, identifier: str = "default") -> None:
        """Check rate limit and raise RateLimitError if exceeded."""
        allowed, error_msg = self.rate_limiter.check_rate_limit(identifier)
        if not allowed:
            raise RateLimitError(
                message=f"Rate limit exceeded: {error_msg}", retry_after=self.config.security.rate_limit_window
            )

    def simple_query(self, question: str) -> str:
        """Execute a query using simple direct LLM interaction without LangGraph state management."""
        # Check rate limit before processing
        self._check_rate_limit()

        try:
            # Build conversation with history using conversation manager
            # Use dynamic prompt selection based on query content
            dynamic_prompt = self.get_dynamic_system_prompt(question)
            messages = [HumanMessage(content=dynamic_prompt)]

            # Add conversation history from manager
            messages.extend(self.conversation_manager.get_conversation_messages())

            # Add current question
            messages.append(HumanMessage(content=question))

            # Get initial response with retry logic
            response = invoke_llm_with_retry(self.llm.bind_tools(self.tools), messages, max_attempts=3)
            messages.append(response)

            if self.debug:
                print(f"DEBUG: Initial response type: {type(response)}")
                print(f"DEBUG: Has tool calls: {hasattr(response, 'tool_calls') and bool(response.tool_calls)}")
                if hasattr(response, "content"):
                    print(f"DEBUG: Initial content: {response.content[:200] if response.content else 'Empty'}")

            # Handle tool calls if any
            max_iterations = 3
            iteration = 0

            # Store tool results for creative formatting
            query_results = []
            analysis_results = []

            while hasattr(response, "tool_calls") and response.tool_calls and iteration < max_iterations:
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
                                if self.debug:
                                    print(f"\nDEBUG: Executing tool '{tool_name}'")
                                    print(f"DEBUG: Tool args: {tool_args}")

                                tool_result = tool.invoke(tool_args)

                                if self.debug:
                                    result_str = str(tool_result)
                                    print(f"DEBUG: Tool result length: {len(result_str)} chars")

                                    # Show more details for query execution
                                    if tool_name == "execute_landuse_query" and "query" in tool_args:
                                        print(f"DEBUG: SQL Query: {tool_args['query']}")
                                        if "rows returned" in result_str:
                                            # Extract row count
                                            import re

                                            row_match = re.search(r"(\d+) rows returned", result_str)
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
                            except ToolExecutionError as e:
                                error_msg = f"Tool execution error: {str(e)}"
                                if self.debug:
                                    print(f"DEBUG: Tool execution error: {error_msg}")
                                tool_result = error_msg
                            except Exception as e:
                                wrapped_error = wrap_exception(e, f"Tool '{tool_name}' execution")
                                error_msg = f"Tool error: {str(wrapped_error)}"
                                if self.debug:
                                    print(f"DEBUG: Tool error: {error_msg}")
                                    import traceback

                                    traceback.print_exc()
                                tool_result = error_msg

                    if tool_result is None:
                        tool_result = f"Unknown tool: {tool_name}"

                    # Add tool result using proper ToolMessage format
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

                # Get next response with retry logic
                response = invoke_llm_with_retry(self.llm.bind_tools(self.tools), messages, max_attempts=3)
                messages.append(response)

                if self.debug:
                    print(f"DEBUG: Response after tool execution: {type(response)}")
                    if hasattr(response, "content"):
                        print(f"DEBUG: Response content type: {type(response.content)}")
                        print(f"DEBUG: Response content: {response.content[:200] if response.content else 'None'}")

            # Extract the final text content from the response
            if self.debug:
                print("\nDEBUG: Extracting final content from response")
                print(f"DEBUG: Response type: {type(response)}")
                print(f"DEBUG: Has content attr: {hasattr(response, 'content')}")
                print(f"DEBUG: Has text attr: {hasattr(response, 'text')}")

            final_content = ""
            if hasattr(response, "content"):
                content = response.content
                if self.debug:
                    print(f"DEBUG: Content type: {type(content)}")
                    print(f"DEBUG: Content value: {content[:200] if content else 'None'}")

                # Handle different content formats
                if isinstance(content, list):
                    # Extract text from list of content blocks
                    text_parts = []
                    for i, item in enumerate(content):
                        if self.debug:
                            print(f"DEBUG: Content item {i}: type={type(item)}, value={str(item)[:100]}")
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                        else:
                            # Skip non-text items like tool calls
                            continue
                    final_content = " ".join(text_parts)
                else:
                    final_content = str(content)
            elif hasattr(response, "text"):
                final_content = str(response.text)
            else:
                final_content = str(response)

            # If we still have no content, check if we have tool results we can summarize
            if not final_content.strip() and (query_results or analysis_results):
                if self.debug:
                    print("\nDEBUG: Final content is empty, checking tool results")
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

            # Update conversation history using manager
            self.conversation_manager.add_conversation(question, final_content)

            # Return clean final content without any special formatting
            if self.debug:
                print(f"\nDEBUG: Final content length: {len(final_content)}")
                print(f"DEBUG: Final content preview: {final_content[:200]}...")
                print("DEBUG: === End of simple_query execution ===")

            return final_content

        except (LanduseError, ToolExecutionError) as e:
            error_msg = f"Query processing error: {str(e)}"
            # Still update history even on error
            self.conversation_manager.add_conversation(question, error_msg)
            return error_msg
        except Exception as e:
            wrapped_error = wrap_exception(e, "Simple query processing")
            error_msg = f"Unexpected error: {str(wrapped_error)}"
            # Still update history even on error
            self.conversation_manager.add_conversation(question, error_msg)
            return error_msg

    def _graph_query(
        self,
        question: str,
        thread_id: str | None = None,
        user_expertise: str = "novice",
    ) -> str:
        """Execute a query using the enhanced LangGraph workflow with RPA context.

        Args:
            question: Natural language question.
            thread_id: Optional thread ID for conversation memory.
            user_expertise: User expertise level (novice, intermediate, expert).

        Returns:
            The agent's response as a string.
        """
        # Check rate limit before processing
        self._check_rate_limit(thread_id or "default")

        try:
            # Build graph if not already built using graph builder
            if not self.graph:
                self.graph = self.graph_builder.build_graph()

            # Prepare initial messages with conversation history
            dynamic_prompt = self.get_dynamic_system_prompt(question)
            initial_messages = [HumanMessage(content=dynamic_prompt)]

            # Add conversation history from manager
            initial_messages.extend(self.conversation_manager.get_conversation_messages())

            # Add current question
            initial_messages.append(HumanMessage(content=question))

            # Use enhanced state with RPA context tracking
            initial_state = {
                "messages": initial_messages,
                "context": {},
                "iteration_count": 0,
                "max_iterations": self.config.agent.max_iterations,
                # RPA context fields
                "user_expertise": user_expertise,
                "explained_concepts": [],
                "preferred_scenarios": [],
                "focus_states": [],
                "focus_time_range": None,
                "current_query_type": None,
                "detected_scenarios": [],
                "detected_geography": [],
                "pending_sql_approval": None,
                "thread_id": thread_id,
                "user_id": None,
            }

            # Prepare config with thread_id for memory
            # MemorySaver requires thread_id, so generate one if not provided
            import time
            effective_thread_id = thread_id or f"landuse-{int(time.time() * 1000)}"
            config = {"configurable": {"thread_id": effective_thread_id}}

            # Execute the graph
            result = self.graph.invoke(initial_state, config=config)

            # Extract the final response from messages
            if result and "messages" in result:
                messages = result["messages"]
                # Find the last AI message with content
                for msg in reversed(messages):
                    if not isinstance(msg, AIMessage):
                        continue

                    # Check if this is a tool call without content
                    tool_calls = getattr(msg, "tool_calls", None)
                    if tool_calls and not msg.content:
                        continue

                    # Extract content
                    content = msg.content
                    if isinstance(content, list):
                        # Extract text content from list
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif isinstance(item, str):
                                text_parts.append(item)
                        if text_parts:
                            final_response = " ".join(text_parts)
                            self.conversation_manager.add_conversation(question, final_response)
                            return final_response
                    elif content:
                        final_response = str(content)
                        self.conversation_manager.add_conversation(question, final_response)
                        return final_response

            default_response = "I couldn't generate a proper response. Please try rephrasing your question."
            self.conversation_manager.add_conversation(question, default_response)
            return default_response

        except GraphExecutionError as e:
            error_msg = f"Graph execution error: {str(e)}"
            if self.debug:
                self.console.print(f"[red]DEBUG: {error_msg}[/red]")
            error_response = f"I encountered a workflow error: {str(e)}"
            self.conversation_manager.add_conversation(question, error_response)
            return error_response
        except Exception as e:
            wrapped_error = wrap_exception(e, "Graph query execution")
            error_msg = f"Unexpected error in graph execution: {str(wrapped_error)}"
            if self.debug:
                import traceback

                self.console.print(f"[red]DEBUG: {error_msg}[/red]")
                self.console.print(f"[red]{traceback.format_exc()}[/red]")
            error_response = f"I encountered an unexpected error: {str(wrapped_error)}"
            self.conversation_manager.add_conversation(question, error_response)
            return error_response

    def query(
        self,
        question: str,
        use_graph: bool | None = None,
        thread_id: str | None = None,
        user_expertise: str = "novice",
    ) -> str:
        """Execute a natural language query using the agent.

        Args:
            question: The natural language question to answer.
            use_graph: Override for graph mode (None uses feature flag).
            thread_id: Optional thread ID for conversation memory.
            user_expertise: User expertise level for response calibration.

        Returns:
            The agent's response as a string.
        """
        # Determine whether to use graph mode based on feature flags
        should_use_graph = use_graph
        if should_use_graph is None:
            # Check feature flags - use full graph mode if enabled
            should_use_graph = self.config.features.enable_full_graph_mode

        if should_use_graph:
            return self._graph_query(question, thread_id, user_expertise)
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
        # Check rate limit before processing
        self._check_rate_limit(thread_id or "default")

        if not self.graph:
            self.graph = self.graph_builder.build_graph()

        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "context": {},
            "iteration_count": 0,
            "max_iterations": self.config.agent.max_iterations,
        }

        # Prepare config
        config = {}
        if thread_id and self.config.agent.enable_memory:
            config = {"configurable": {"thread_id": thread_id}}
        elif not thread_id:
            config = {"configurable": {"thread_id": f"landuse-stream-{int(time.time())}"}}

        # Stream the response
        try:
            for chunk in self.graph.stream(initial_state, config=config):
                yield chunk
        except GraphExecutionError as e:
            yield {"error": f"Graph streaming error: {str(e)}"}
        except Exception as e:
            wrapped_error = wrap_exception(e, "Streaming query")
            yield {"error": f"Streaming error: {str(wrapped_error)}"}

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
        return self.graph_builder.create_subgraph(name, specialized_tools)

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
            create_analysis_tool(),
        ]

        return self.create_subgraph("map_analysis", map_tools)

    def _display_results_table(self, results: list[tuple], columns: list[str], title: str = "Query Results") -> None:
        """Display query results in a rich table format."""
        table = Table(title=title, show_header=True, header_style="bold magenta")

        # Add columns
        for col in columns:
            table.add_column(col, style="cyan", no_wrap=False)

        # Add rows (limit display)
        display_limit = min(len(results), self.config.agent.default_display_limit)
        for row in results[:display_limit]:
            table.add_row(*[str(val) for val in row])

        if len(results) > display_limit:
            table.add_row(*["..." for _ in columns])
            table.caption = f"Showing {display_limit} of {len(results)} rows"

        self.console.print(table)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_manager.clear_history()

    def chat(self) -> None:
        """Interactive chat interface for the agent."""
        self.console.print(
            Panel.fit(
                "[bold green]RPA Land Use Analytics Agent[/bold green]\n"
                "Ask questions about land use projections and transitions.\n"
                "Type 'exit' to quit, 'help' for examples, 'clear' to reset conversation.",
                title="Welcome",
                border_style="green",
            )
        )

        while True:
            try:
                question = input("\n[You] > ").strip()

                if not question:
                    continue

                if question.lower() in ["exit", "quit", "q"]:
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break

                if question.lower() in ["help", "?"]:
                    self._show_help()
                    continue

                if question.lower() == "clear":
                    self.clear_history()
                    continue

                # Process the question
                self.console.print("\n[bold cyan][Agent][/bold cyan] Thinking...")
                response = self.query(question)
                self.console.print(f"\n[bold cyan][Agent][/bold cyan] {response}")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except (LanduseError, ToolExecutionError, GraphExecutionError) as e:
                self.console.print(f"\n[red]Agent Error: {str(e)}[/red]")
            except Exception as e:
                wrapped_error = wrap_exception(e, "Chat interaction")
                self.console.print(f"\n[red]Unexpected Error: {str(wrapped_error)}[/red]")

    def _show_help(self) -> None:
        """Show help information with example queries."""
        examples = [
            "Which states will see the most agricultural land loss?",
            "Compare forest transitions between RCP45 and RCP85 scenarios",
            "Show urbanization trends in California counties",
            "What land use types are converting to urban?",
            "Analyze cropland changes in the Midwest by 2070",
        ]

        self.console.print(
            Panel.fit("\n".join([f"• {ex}" for ex in examples]), title="Example Questions", border_style="blue")
        )

    @property
    def model_name(self) -> str:
        """Get the model name from configuration."""
        return self.config.llm.model_name

    def _get_schema_help(self) -> str:
        """Get user-friendly schema information for display in the UI."""
        return self.schema

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up resources."""
        # Clean up database connection using manager
        if hasattr(self, "database_manager"):
            self.database_manager.close()


def main() -> None:
    """Main entry point when run as module."""
    from landuse.agents.agent import main as agent_main

    agent_main()


if __name__ == "__main__":
    main()
