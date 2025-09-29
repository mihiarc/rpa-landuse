"""Conversation history management extracted from monolithic agent class."""

from collections import deque
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from rich.console import Console

from landuse.core.app_config import AppConfig
from landuse.core.interfaces import ConversationInterface


class ConversationManager(ConversationInterface):
    """
    Manages conversation history and message handling.

    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Implements sliding window memory management to prevent unlimited memory growth.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        max_history_length: Optional[int] = None,
        console: Optional[Console] = None
    ):
        """
        Initialize conversation manager.

        Args:
            config: Configuration object
            max_history_length: Maximum number of messages to keep in history (overrides config)
            console: Rich console for logging (optional)
        """
        # Handle configuration
        self.config = config or AppConfig()
        self._max_history_length = max_history_length or self.config.agent.conversation_history_limit
        self.console = console or Console()

        # Use deque for efficient sliding window operations
        self._conversation_history: deque = deque(maxlen=self._max_history_length)

    @property
    def max_history_length(self) -> int:
        """Get maximum history length."""
        return self._max_history_length

    @max_history_length.setter
    def max_history_length(self, value: int):
        """Set maximum history length and recreate deque with new maxlen."""
        self._max_history_length = value
        # Convert existing history to list, create new deque with new maxlen, and populate it
        old_history = list(self._conversation_history)
        self._conversation_history = deque(old_history, maxlen=value)

    def add_conversation(self, question: str, response: str) -> None:
        """
        Add a question-response pair to conversation history.

        Args:
            question: User's question
            response: Agent's response
        """
        # Add user question
        self._conversation_history.append(("user", question))
        # Add assistant response
        self._conversation_history.append(("assistant", response))

    def get_conversation_messages(self) -> List[BaseMessage]:
        """
        Get conversation history as LangChain messages.

        Returns:
            List of BaseMessage objects representing conversation history
        """
        messages = []
        for role, content in self._conversation_history:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def get_conversation_tuples(self) -> List[Tuple[str, str]]:
        """
        Get conversation history as list of (role, content) tuples.

        Returns:
            List of tuples with role and content
        """
        return list(self._conversation_history)

    def clear_history(self) -> None:
        """Clear all conversation history."""
        self._conversation_history.clear()
        if self.console:
            self.console.print("[yellow]Conversation history cleared.[/yellow]")

    def get_history_length(self) -> int:
        """Get current number of messages in history."""
        return len(self._conversation_history)

    def is_history_full(self) -> bool:
        """Check if history has reached maximum capacity."""
        return len(self._conversation_history) >= self._max_history_length

    def get_recent_context(self, num_messages: int = 4) -> List[Tuple[str, str]]:
        """
        Get the most recent conversation context.

        Args:
            num_messages: Number of recent messages to retrieve

        Returns:
            List of recent (role, content) tuples
        """
        return list(self._conversation_history)[-num_messages:] if self._conversation_history else []

    @property
    def conversation_history(self) -> List[Tuple[str, str]]:
        """
        Get conversation history as a list (property for backward compatibility).

        Returns:
            List of (role, content) tuples
        """
        return list(self._conversation_history)
