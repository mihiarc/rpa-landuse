"""State definitions for LangGraph agents."""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State definition for the landuse agent."""
    messages: list[BaseMessage]
    context: dict[str, Any]
    iteration_count: int
    max_iterations: int
