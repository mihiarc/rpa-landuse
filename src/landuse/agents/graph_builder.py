"""LangGraph workflow construction extracted from monolithic agent class."""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from rich.console import Console

from landuse.agents.state import AgentState
from landuse.core.app_config import AppConfig


class GraphBuilder:
    """
    Constructs and manages LangGraph workflows.

    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles graph construction, node creation, and workflow orchestration.
    """

    def __init__(
        self,
        config: AppConfig,
        llm: BaseChatModel,
        tools: List[BaseTool],
        system_prompt: str,
        console: Optional[Console] = None
    ):
        """
        Initialize graph builder.

        Args:
            config: Configuration object
            llm: Language model instance
            tools: List of available tools
            system_prompt: System prompt for the agent
            console: Rich console for logging (optional)
        """
        self.config = config
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.console = console or Console()
        self.memory = MemorySaver()

    def build_graph(self) -> StateGraph:
        """
        Build the main LangGraph state graph.

        Returns:
            Compiled StateGraph ready for execution
        """
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
        if self.config.agent.enable_memory:
            return workflow.compile(checkpointer=self.memory)
        else:
            return workflow.compile()

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
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

    def _analyzer_node(self, state: AgentState) -> Dict[str, Any]:
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

    def _human_review_node(self, state: AgentState) -> Dict[str, Any]:
        """Human-in-the-loop node for complex queries.

        TODO: Implement proper human-in-the-loop review when Streamlit UI integration
        is complete. This should:
        1. Pause execution and display query for user approval
        2. Allow user to modify or reject the query
        3. Log review decisions for audit trail
        4. Support async approval via webhook for batch processing

        Currently auto-approves all requests as a placeholder.
        """
        if self.console:
            self.console.print("[yellow]Human review requested (auto-approved)[/yellow]")
        return {"messages": state["messages"]}

    def _should_continue(self, state: AgentState) -> str:
        """Decide next step in the workflow."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check iteration limit
        if state.get("iteration_count", 0) >= self.config.agent.max_iterations:
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

    def _needs_analysis(self, messages: List[BaseMessage]) -> bool:
        """Determine if results need analysis."""
        # Check if recent messages contain query results
        for msg in messages[-3:]:
            if isinstance(msg, AIMessage) and "SELECT" in str(msg.content).upper():
                return True
        return False

    def _needs_human_review(self, messages: List[BaseMessage]) -> bool:
        """Determine if human review is needed."""
        # Check for sensitive operations
        sensitive_keywords = ["DELETE", "UPDATE", "DROP", "TRUNCATE"]
        last_message = str(messages[-1].content).upper()

        return any(keyword in last_message for keyword in sensitive_keywords)

    def _extract_recent_results(self, messages: List[BaseMessage]) -> Optional[str]:
        """Extract recent query results from messages."""
        for msg in reversed(messages[-5:]):
            content = str(msg.content)
            if "rows returned" in content or "│" in content:
                return content
        return None

    def create_subgraph(self, name: str, specialized_tools: List[BaseTool]) -> StateGraph:
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
