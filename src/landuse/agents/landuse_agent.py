"""Primary landuse agent with modern LangGraph architecture."""

from typing import Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from rich.panel import Panel

from landuse.agents.base_agent import BaseLanduseAgent
from landuse.agents.prompts import get_system_prompt
from landuse.config.landuse_config import LanduseConfig
from landuse.tools.common_tools import create_analysis_tool, create_execute_query_tool, create_schema_tool


class AgentState(TypedDict):
    """State definition for the landuse agent following 2025 patterns."""
    messages: list[BaseMessage]
    context: dict[str, Any]
    iteration_count: int
    max_iterations: int


class LanduseAgent(BaseLanduseAgent):
    """
    Modern landuse agent implementation with:
    - Memory-first architecture
    - Graph-based workflow
    - Subgraph support for complex queries
    - Human-in-the-loop capability
    - Event-driven execution
    """

    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the modern landuse agent."""
        super().__init__(config)
        # Use centralized prompts system with configuration from config
        self.system_prompt = get_system_prompt(
            include_maps=self.config.enable_map_generation,
            analysis_style=self.config.analysis_style,
            domain_focus=None if self.config.domain_focus == 'none' else self.config.domain_focus,
            schema_info=self.schema
        )

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
        from rich.panel import Panel
        
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
