"""Abstract interfaces for dependency injection and clean architecture."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, TypeVar

import duckdb
import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from landuse.core.app_config import AppConfig

T = TypeVar("T")


class ConfigInterface(Protocol):
    """Interface for configuration providers."""

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting by key."""
        ...

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        ...


class DatabaseInterface(ABC):
    """Abstract interface for database operations."""

    @abstractmethod
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get database connection."""
        ...

    @abstractmethod
    def execute_query(self, query: str, **kwargs) -> pd.DataFrame:
        """Execute SQL query and return results."""
        ...

    @abstractmethod
    def get_schema(self) -> str:
        """Get database schema information."""
        ...

    @abstractmethod
    def validate_table_name(self, table_name: str) -> bool:
        """Validate table name exists and is accessible."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        ...


class LLMInterface(ABC):
    """Abstract interface for language model operations."""

    @abstractmethod
    def create_llm(self) -> BaseChatModel:
        """Create and configure language model."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name."""
        ...

    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate API key is available and valid."""
        ...


class ConversationInterface(ABC):
    """Abstract interface for conversation management."""

    @abstractmethod
    def add_conversation(self, question: str, response: str) -> None:
        """Add conversation to history."""
        ...

    @abstractmethod
    def get_conversation_messages(self) -> List[BaseMessage]:
        """Get conversation history as LangChain messages."""
        ...

    @abstractmethod
    def clear_history(self) -> None:
        """Clear conversation history."""
        ...

    @abstractmethod
    def get_history_length(self) -> int:
        """Get current conversation history length."""
        ...


class QueryExecutorInterface(ABC):
    """Abstract interface for query execution."""

    @abstractmethod
    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL query with error handling."""
        ...

    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """Validate query safety."""
        ...


class SecurityInterface(ABC):
    """Abstract interface for security validation."""

    @abstractmethod
    def validate_query_safety(self, query: str) -> None:
        """Validate query for security issues."""
        ...

    @abstractmethod
    def validate_table_name(self, table_name: str) -> str:
        """Validate and return safe table name."""
        ...

    @abstractmethod
    def scan_for_dangerous_content(self, content: str) -> List[str]:
        """Scan content for dangerous patterns."""
        ...


class ToolInterface(ABC):
    """Abstract interface for tool creation and management."""

    @abstractmethod
    def create_tools(self) -> List[BaseTool]:
        """Create list of available tools."""
        ...

    @abstractmethod
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute specific tool by name."""
        ...


class CacheInterface(ABC):
    """Abstract interface for caching operations."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        ...


class LoggerInterface(ABC):
    """Abstract interface for logging operations."""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        ...

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        ...

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        ...

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        ...


class MetricsInterface(ABC):
    """Abstract interface for metrics collection."""

    @abstractmethod
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...

    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        ...

    @abstractmethod
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        ...


class AgentInterface(ABC):
    """Abstract interface for agent implementations."""

    @abstractmethod
    def query(self, question: str, **kwargs) -> str:
        """Execute natural language query."""
        ...

    @abstractmethod
    def clear_history(self) -> None:
        """Clear conversation history."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Get current model name."""
        ...


# Type aliases for common interface combinations
DatabaseProvider = DatabaseInterface
LLMProvider = LLMInterface
ConversationProvider = ConversationInterface
SecurityProvider = SecurityInterface


class ComponentInterface(Protocol):
    """Generic interface for dependency injection components."""

    def initialize(self, config: AppConfig) -> None:
        """Initialize component with configuration."""
        ...

    def cleanup(self) -> None:
        """Cleanup component resources."""
        ...

    def health_check(self) -> bool:
        """Check component health status."""
        ...


class ServiceInterface(ABC):
    """Abstract base for service layer components."""

    def __init__(self, config: AppConfig):
        """Initialize service with configuration."""
        self.config = config

    @abstractmethod
    def initialize(self) -> None:
        """Initialize service resources."""
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup service resources."""
        ...

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
