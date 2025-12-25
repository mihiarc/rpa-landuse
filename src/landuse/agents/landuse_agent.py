"""
Simplified LangChain tool-calling agent for RPA Land Use Analytics.

Uses Claude Sonnet 4.5 with domain-specific tools instead of SQL generation.
Follows the proven AskFIA pattern for better performance.
"""

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Load environment variables from .env files
# Try multiple locations in order of priority
_env_paths = [
    Path.cwd() / ".env",  # Current working directory
    Path.cwd() / "config" / ".env",  # config/.env
    Path(__file__).parent.parent.parent.parent / ".env",  # Project root
    Path(__file__).parent.parent.parent.parent / "config" / ".env",  # Project config/
]

for env_path in _env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from rich.console import Console
from rich.panel import Panel

from landuse.agents.prompts import SYSTEM_PROMPT
from landuse.agents.tools import TOOLS
from landuse.core.app_config import AppConfig
from landuse.services.landuse_service import landuse_service

logger = logging.getLogger(__name__)


class LandUseAgent:
    """
    Simple tool-calling agent for RPA land use queries.

    Uses Claude Sonnet 4.5 with domain-specific tools that encapsulate
    all SQL queries. The LLM never generates SQL directly.
    """

    def __init__(self, config: AppConfig | None = None):
        """
        Initialize the agent.

        Args:
            config: Optional AppConfig. If not provided, uses defaults.
        """
        self.config = config or AppConfig()
        self.console = Console()

        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in your environment or .env file."
            )

        # Initialize Claude
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )
        self.llm_with_tools = self.llm.bind_tools(TOOLS)

        # Conversation history for multi-turn
        self._messages: list[dict] = []
        self._max_history = 20

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "claude-sonnet-4-5-20250929"

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._messages.clear()
        self.console.print("[yellow]Conversation history cleared.[/yellow]")

    async def stream(
        self,
        messages: list[dict],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream a response with tool use, supporting multi-turn tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: Optional user identifier
            session_id: Optional session identifier

        Yields:
            Event dicts with 'type' key:
            - {"type": "text", "content": "..."} - Text response
            - {"type": "tool_call", "tool_name": "...", "args": {...}} - Tool invocation
            - {"type": "tool_result", "tool_call_id": "...", "result": "..."} - Tool result
            - {"type": "finish"} - Stream complete
        """
        start_time = time.time()
        tool_calls_count = 0

        # Convert to LangChain message format
        lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]

        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        # Tool execution loop
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                # Get response (may include tool calls)
                response = await self.llm_with_tools.ainvoke(lc_messages)
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}", exc_info=True)
                yield {"type": "text", "content": f"Error communicating with Claude: {e}"}
                yield {"type": "finish"}
                return

            # No tool calls - final response
            if not response.tool_calls:
                content = response.content
                if isinstance(content, str):
                    yield {"type": "text", "content": content}
                elif isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, str):
                            text_parts.append(block)
                        elif hasattr(block, "text"):
                            text_parts.append(block.text)
                        elif isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                    yield {"type": "text", "content": "".join(text_parts)}
                break

            # Process tool calls
            tool_calls_count += len(response.tool_calls)
            tool_results = {}

            for tool_call in response.tool_calls:
                yield {
                    "type": "tool_call",
                    "tool_name": tool_call["name"],
                    "tool_call_id": tool_call["id"],
                    "args": tool_call["args"],
                }

                # Execute the tool
                tool_func = {t.name: t for t in TOOLS}.get(tool_call["name"])
                if tool_func:
                    try:
                        result = await tool_func.ainvoke(tool_call["args"])
                        tool_results[tool_call["id"]] = result
                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_call["id"],
                            "result": result,
                        }
                    except Exception as e:
                        error_result = f"Error executing tool: {e}"
                        tool_results[tool_call["id"]] = error_result
                        logger.error(f"Tool execution failed: {e}", exc_info=True)
                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_call["id"],
                            "result": error_result,
                        }
                else:
                    error_result = f"Unknown tool: {tool_call['name']}"
                    tool_results[tool_call["id"]] = error_result
                    yield {
                        "type": "tool_result",
                        "tool_call_id": tool_call["id"],
                        "result": error_result,
                    }

            # Add results to messages for next iteration
            lc_messages.append(response)
            for tool_call in response.tool_calls:
                result = tool_results.get(tool_call["id"], "Tool execution failed")
                lc_messages.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )

        # Iteration limit reached
        if iteration >= max_iterations:
            logger.warning(f"Hit max_iterations limit ({max_iterations})")
            yield {
                "type": "text",
                "content": "I apologize, but this query required more steps than expected. "
                "Please try a simpler question.",
            }

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Query completed: {tool_calls_count} tool calls, {latency_ms}ms")

        yield {"type": "finish"}

    def query(self, question: str, **kwargs) -> str:
        """
        Query the agent with a question.

        Args:
            question: Natural language question about land use

        Returns:
            Agent's response as a string
        """
        # Add to message history
        self._messages.append({"role": "user", "content": question})

        # Trim history if needed
        if len(self._messages) > self._max_history * 2:
            self._messages = self._messages[-self._max_history * 2:]

        # Run async stream and collect text
        async def _run():
            response_text = ""
            async for event in self.stream(self._messages):
                if event["type"] == "text":
                    response_text = event["content"]
            return response_text

        response = asyncio.run(_run())

        # Add response to history
        self._messages.append({"role": "assistant", "content": response})

        return response

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
            except Exception as e:
                self.console.print(f"\n[red]Error: {e}[/red]")
                logger.error(f"Chat error: {e}", exc_info=True)

    def _show_help(self) -> None:
        """Show help information with example queries."""
        examples = [
            "How much forest is in California?",
            "Compare urban expansion between LM and HH scenarios",
            "Which states will see the most agricultural land loss?",
            "What is converting to urban land in Texas?",
            "Show me forest loss trends over time for North Carolina",
            "Find the top 10 counties with most urban growth",
        ]

        self.console.print(
            Panel.fit(
                "\n".join([f"• {ex}" for ex in examples]),
                title="Example Questions",
                border_style="blue",
            )
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up resources."""
        # Close the service connection
        landuse_service.close()


def main() -> None:
    """Main entry point when run as module."""
    from landuse.agents.agent import main as agent_main

    agent_main()


if __name__ == "__main__":
    main()
