"""LangGraph workflow construction with RPA context-aware nodes.

This module builds the enhanced LangGraph workflow with:
- Query analysis for scenario/geography detection
- Progressive context injection from RPA domain knowledge
- Human-in-the-loop for potentially large SQL queries
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from rich.console import Console

from landuse.agents.rpa_context import (
    build_context_injection,
    classify_query_type,
    detect_geography,
    detect_scenarios,
    detect_time_range,
)
from landuse.agents.state import AgentState
from landuse.core.app_config import AppConfig
from landuse.utils.retry_decorators import invoke_llm_with_retry


class GraphBuilder:
    """Constructs and manages LangGraph workflows with RPA context awareness.

    Enhanced from the original implementation to support:
    - Progressive disclosure of RPA domain knowledge
    - Query analysis for scenario/geography detection
    - Human-in-the-loop for potentially large queries
    - Session-based context tracking
    """

    def __init__(
        self,
        config: AppConfig,
        llm: BaseChatModel,
        tools: list[BaseTool],
        system_prompt: str,
        console: Console | None = None,
    ):
        """Initialize graph builder.

        Args:
            config: Configuration object.
            llm: Language model instance.
            tools: List of available tools.
            system_prompt: Base system prompt for the agent.
            console: Rich console for logging (optional).
        """
        self.config = config
        self.llm = llm
        self.tools = tools
        self.base_system_prompt = system_prompt
        self.console = console or Console()
        self.memory = MemorySaver()

    def build_graph(self) -> StateGraph:
        """Build the enhanced LangGraph state graph with RPA context nodes.

        Graph Structure:
            query_analyzer -> context_enricher -> agent -> router
                                                            |
                        +----------------+------------------+----------+
                        |                |                  |          |
                        v                v                  v          v
                      tools          analyzer         sql_approval    END
                        |                |                  |
                        +--------+-------+------------------+
                                 |
                                 v
                               agent

        Returns:
            Compiled StateGraph ready for execution.
        """
        workflow = StateGraph(AgentState)

        # Add nodes - new context-aware flow
        workflow.add_node("query_analyzer", self._query_analyzer_node)
        workflow.add_node("context_enricher", self._context_enricher_node)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("sql_approval", self._sql_approval_node)

        # Entry point is query analysis
        workflow.set_entry_point("query_analyzer")

        # Linear flow: analyzer -> enricher -> agent
        workflow.add_edge("query_analyzer", "context_enricher")
        workflow.add_edge("context_enricher", "agent")

        # Conditional routing from agent
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "analyzer": "analyzer",
                "sql_approval": "sql_approval",
                "end": END,
            },
        )

        # Return paths back to agent
        workflow.add_edge("tools", "agent")
        workflow.add_edge("analyzer", "agent")
        workflow.add_edge("sql_approval", "agent")

        # Compile with memory if enabled
        if self.config.agent.enable_memory:
            return workflow.compile(checkpointer=self.memory)
        return workflow.compile()

    def _query_analyzer_node(self, state: AgentState) -> dict[str, Any]:
        """Analyze incoming query for scenarios, geography, and query type.

        This node extracts metadata from the user's query to inform
        context injection and response calibration.
        """
        messages = state.get("messages", [])

        # Find the latest user message
        user_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = str(msg.content)
                break

        if not user_query:
            return {}

        # Detect query characteristics
        detected_scenarios = detect_scenarios(user_query)
        detected_geography = detect_geography(user_query)
        time_range = detect_time_range(user_query)
        query_type = classify_query_type(user_query)

        if self.console:
            if detected_scenarios:
                self.console.print(f"[dim]Detected scenarios: {detected_scenarios}[/dim]")
            if detected_geography:
                self.console.print(f"[dim]Detected geography: {detected_geography}[/dim]")

        return {
            "detected_scenarios": detected_scenarios,
            "detected_geography": detected_geography,
            "focus_time_range": time_range,
            "current_query_type": query_type,
        }

    def _context_enricher_node(self, state: AgentState) -> dict[str, Any]:
        """Inject relevant RPA context based on query analysis.

        Uses progressive disclosure - only explains concepts that are
        relevant to the current query and haven't been explained yet.
        """
        messages = list(state.get("messages", []))
        explained_concepts = list(state.get("explained_concepts", []))

        # Find the latest user message
        user_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = str(msg.content)
                break

        if not user_query:
            return {}

        # Build context injection
        context_text, new_concepts = build_context_injection(
            user_query,
            explained_concepts,
            max_concepts=3,
        )

        if context_text and new_concepts:
            if self.console:
                self.console.print(f"[dim]Injecting context for: {new_concepts}[/dim]")

            # Add context as a system message before the user's query
            # Find where to insert (before the last human message)
            insert_idx = len(messages)
            for i in range(len(messages) - 1, -1, -1):
                if isinstance(messages[i], HumanMessage):
                    insert_idx = i
                    break

            context_message = SystemMessage(content=context_text)
            messages.insert(insert_idx, context_message)

            return {
                "messages": messages,
                "explained_concepts": explained_concepts + new_concepts,
            }

        return {}

    def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """Main agent node that processes the query with LLM."""
        messages = list(state.get("messages", []))

        if not messages:
            messages = []

        # Add system prompt as first message if needed
        has_system_prompt = False
        for msg in messages[:2]:
            if isinstance(msg, (HumanMessage, SystemMessage)):
                if self.base_system_prompt[:50] in str(msg.content):
                    has_system_prompt = True
                    break

        if not has_system_prompt:
            messages = [SystemMessage(content=self.base_system_prompt)] + messages

        # Get LLM response with tools bound and retry logic
        response = invoke_llm_with_retry(
            self.llm.bind_tools(self.tools),
            messages,
            max_attempts=3,
        )

        return {
            "messages": [response],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def _analyzer_node(self, state: AgentState) -> dict[str, Any]:
        """Analyzer node for providing insights on query results."""
        messages = state.get("messages", [])
        recent_results = self._extract_recent_results(list(messages))

        if not recent_results:
            return {}

        # Get detected context for enhanced analysis
        scenarios = state.get("detected_scenarios", [])
        geography = state.get("detected_geography", [])

        scenario_context = f"\nScenarios being analyzed: {scenarios}" if scenarios else ""
        geo_context = f"\nGeographic focus: {geography}" if geography else ""

        analysis_prompt = f"""Based on these RPA land use query results, provide key insights:

Results: {recent_results}
{scenario_context}
{geo_context}

Focus on:
1. Key trends or patterns in land use change
2. Implications for land use planning and policy
3. How these results compare across scenarios (if applicable)
4. Recommendations for further investigation

Remember the key RPA assumptions:
- Development is irreversible (once urban, stays urban)
- Data covers private lands only (~70% of US)
- ~46% of new urban land historically comes from forest
"""

        analysis = invoke_llm_with_retry(
            self.llm,
            [
                {"role": "system", "content": "You are an RPA land use science expert."},
                {"role": "user", "content": analysis_prompt},
            ],
            max_attempts=3,
        )

        return {"messages": [analysis]}

    def _sql_approval_node(self, state: AgentState) -> dict[str, Any]:
        """Human-in-the-loop node for potentially large SQL queries.

        Uses LangGraph's interrupt() to pause execution and request
        user approval for queries that may return large result sets.
        """
        pending = state.get("pending_sql_approval")

        if not pending:
            return {}

        query = pending.get("query", "")
        reason = pending.get("reason", "Query may return large result set")

        # Use interrupt to pause and request approval
        approval_request = {
            "type": "sql_approval",
            "query": query,
            "reason": reason,
            "message": f"Approval needed: {reason}\n\nQuery:\n{query}",
        }

        if self.console:
            self.console.print(f"[yellow]SQL approval required: {reason}[/yellow]")

        # This pauses the graph until resumed with a response
        response = interrupt(approval_request)

        if response.get("approved"):
            if self.console:
                self.console.print("[green]Query approved[/green]")
            return {"pending_sql_approval": None}
        else:
            if self.console:
                self.console.print(f"[red]Query rejected: {response.get('reason', 'User declined')}[/red]")
            rejection_msg = AIMessage(content=f"Query was not approved: {response.get('reason', 'User declined')}")
            return {
                "messages": [rejection_msg],
                "pending_sql_approval": None,
            }

    def _should_continue(self, state: AgentState) -> str:
        """Decide next step in the workflow based on current state."""
        messages = state.get("messages", [])

        if not messages:
            return "end"

        last_message = messages[-1]

        # Check iteration limit
        max_iterations = state.get("max_iterations", self.config.agent.max_iterations)
        if state.get("iteration_count", 0) >= max_iterations:
            return "end"

        # Check for pending SQL approval
        if state.get("pending_sql_approval"):
            return "sql_approval"

        # Check if tools were called
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Check if any tool call might need approval
            for tool_call in last_message.tool_calls:
                if self._needs_sql_approval(tool_call):
                    return "sql_approval"
            return "tools"

        # Check if analysis is needed for query results
        if self._needs_analysis(list(messages)):
            return "analyzer"

        return "end"

    def _needs_sql_approval(self, tool_call: Any) -> bool:
        """Determine if a SQL query needs user approval.

        Only requires approval for potentially large queries:
        - No LIMIT clause
        - SELECT * queries
        - Queries on large tables without filtering
        """
        if not hasattr(tool_call, "args"):
            return False

        args = tool_call.args
        query = args.get("query", "") if isinstance(args, dict) else ""

        if not query:
            return False

        query_upper = query.upper()

        # Require approval for queries without LIMIT
        if "LIMIT" not in query_upper:
            # Only if it's a SELECT query
            if query_upper.strip().startswith("SELECT"):
                # Check for SELECT * on main fact table
                if "SELECT *" in query_upper and "FACT_LANDUSE" in query_upper:
                    return True

        return False

    def _needs_analysis(self, messages: list[BaseMessage]) -> bool:
        """Determine if results need analysis."""
        for msg in messages[-3:]:
            if isinstance(msg, AIMessage) and "SELECT" in str(msg.content).upper():
                return True
        return False

    def _extract_recent_results(self, messages: list[BaseMessage]) -> str | None:
        """Extract recent query results from messages."""
        for msg in reversed(messages[-5:]):
            content = str(msg.content)
            if "rows returned" in content or "|" in content:
                return content
        return None

    def create_subgraph(self, name: str, specialized_tools: list[BaseTool]) -> StateGraph:
        """Create a specialized subgraph for complex workflows.

        Args:
            name: Name of the subgraph.
            specialized_tools: Tools specific to this subgraph.

        Returns:
            Compiled subgraph.
        """
        subgraph = StateGraph(AgentState)

        subgraph.add_node("specialized_agent", self._agent_node)
        subgraph.add_node("specialized_tools", ToolNode(specialized_tools))

        subgraph.set_entry_point("specialized_agent")
        subgraph.add_edge("specialized_agent", "specialized_tools")
        subgraph.add_edge("specialized_tools", END)

        return subgraph.compile()
