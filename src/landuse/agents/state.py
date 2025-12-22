"""State definitions for LangGraph agents with RPA domain context.

This module defines the enhanced AgentState for the RPA Land Use agent,
supporting progressive disclosure of domain knowledge and context tracking.
"""

from typing import Annotated, Any, Literal, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Enhanced state definition for the RPA landuse agent.

    Combines core LangGraph message handling with RPA-specific context tracking
    to enable progressive disclosure of domain knowledge and context-aware responses.

    Attributes:
        messages: Conversation history with proper message reduction.
        context: General context dictionary for tool outputs.
        iteration_count: Current iteration in the workflow.
        max_iterations: Maximum allowed iterations before stopping.
        user_expertise: User's domain expertise level for response calibration.
        explained_concepts: RPA concepts already explained (avoids repetition).
        preferred_scenarios: User's preferred climate scenarios (LM, HM, HL, HH).
        focus_states: Geographic areas of interest.
        focus_time_range: Time period focus (start_year, end_year).
        current_query_type: Classification of current query intent.
        detected_scenarios: Scenarios detected in current query.
        detected_geography: Geographic entities detected in current query.
        pending_sql_approval: SQL query awaiting user approval (for interrupt).
        thread_id: Session thread identifier for memory/checkpointing.
        user_id: User identifier for personalization.
    """

    # Core message handling with proper reducer for appending
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # General context (for backward compatibility)
    context: dict[str, Any]

    # Execution control
    iteration_count: int
    max_iterations: int

    # RPA Domain Context - Progressive Disclosure
    user_expertise: Literal["novice", "intermediate", "expert"]
    explained_concepts: list[str]  # Concepts already explained in this session
    preferred_scenarios: list[str]  # User's scenario preferences (LM, HM, HL, HH)
    focus_states: list[str]  # Geographic areas of interest
    focus_time_range: Optional[tuple[int, int]]  # e.g., (2030, 2070)

    # Query Context - Updated per query
    current_query_type: Optional[str]  # "aggregate", "comparison", "geographic", "temporal"
    detected_scenarios: list[str]  # Scenarios mentioned in current query
    detected_geography: list[str]  # States/regions mentioned in current query

    # Human-in-the-Loop
    pending_sql_approval: Optional[dict]  # Query awaiting approval

    # Session Management
    thread_id: Optional[str]
    user_id: Optional[str]


def create_initial_state(
    user_expertise: Literal["novice", "intermediate", "expert"] = "novice",
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_iterations: int = 10,
) -> AgentState:
    """Create initial agent state with sensible defaults.

    Args:
        user_expertise: User's domain expertise level.
        thread_id: Session thread identifier.
        user_id: User identifier.
        max_iterations: Maximum iterations before stopping.

    Returns:
        AgentState with initialized fields.
    """
    return AgentState(
        messages=[],
        context={},
        iteration_count=0,
        max_iterations=max_iterations,
        user_expertise=user_expertise,
        explained_concepts=[],
        preferred_scenarios=[],
        focus_states=[],
        focus_time_range=None,
        current_query_type=None,
        detected_scenarios=[],
        detected_geography=[],
        pending_sql_approval=None,
        thread_id=thread_id,
        user_id=user_id,
    )
