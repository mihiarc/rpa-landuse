"""Simple service factory for managing component creation.

Simplified from a full DI container to a basic factory pattern.
Components are created lazily on first access and cached.
"""

from typing import Any, Dict, Optional, Type, TypeVar

from landuse.core.app_config import AppConfig
from landuse.exceptions import ConfigurationError

T = TypeVar('T')


class ServiceFactory:
    """
    Simple factory for creating and caching service instances.

    Provides lazy initialization of services with configuration injection.
    Thread-safety is handled by Python's GIL for simple use cases.

    Example:
        factory = ServiceFactory(config)
        db_manager = factory.get_database_manager()
        llm_manager = factory.get_llm_manager()
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize factory with configuration."""
        self._config = config or AppConfig()
        self._cache: Dict[str, Any] = {}

    @property
    def config(self) -> AppConfig:
        """Get current configuration."""
        return self._config

    def get_database_manager(self):
        """Get or create DatabaseManager instance."""
        if 'database_manager' not in self._cache:
            from landuse.agents.database_manager import DatabaseManager
            self._cache['database_manager'] = DatabaseManager(self._config, None)
        return self._cache['database_manager']

    def get_llm_manager(self):
        """Get or create LLMManager instance."""
        if 'llm_manager' not in self._cache:
            from landuse.agents.llm_manager import LLMManager
            self._cache['llm_manager'] = LLMManager(self._config, None)
        return self._cache['llm_manager']

    def get_conversation_manager(self):
        """Get or create ConversationManager instance."""
        if 'conversation_manager' not in self._cache:
            from landuse.agents.conversation_manager import ConversationManager
            self._cache['conversation_manager'] = ConversationManager(
                max_history_length=self._config.agent.conversation_history_limit,
                console=None
            )
        return self._cache['conversation_manager']

    def get_query_executor(self, db_connection=None):
        """Get or create QueryExecutor instance.

        Args:
            db_connection: Database connection (required on first call)
        """
        if 'query_executor' not in self._cache:
            if db_connection is None:
                db_manager = self.get_database_manager()
                db_connection = db_manager.get_connection()
            from landuse.agents.query_executor import QueryExecutor
            self._cache['query_executor'] = QueryExecutor(
                self._config, db_connection, None
            )
        return self._cache['query_executor']

    def get_cache(self):
        """Get or create InMemoryCache instance."""
        if 'cache' not in self._cache:
            from landuse.infrastructure.cache import InMemoryCache
            self._cache['cache'] = InMemoryCache()
        return self._cache['cache']

    def get_logger(self):
        """Get or create StructuredLogger instance."""
        if 'logger' not in self._cache:
            from landuse.infrastructure.logging import StructuredLogger
            self._cache['logger'] = StructuredLogger(self._config.logging)
        return self._cache['logger']

    def get_metrics(self):
        """Get or create InMemoryMetrics instance."""
        if 'metrics' not in self._cache:
            from landuse.infrastructure.metrics import InMemoryMetrics
            self._cache['metrics'] = InMemoryMetrics()
        return self._cache['metrics']

    def cleanup(self) -> None:
        """Cleanup all cached services."""
        for service in self._cache.values():
            if hasattr(service, 'cleanup'):
                try:
                    service.cleanup()
                except Exception:
                    pass
            elif hasattr(service, 'close'):
                try:
                    service.close()
                except Exception:
                    pass
        self._cache.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()


# Global factory instance
_factory: Optional[ServiceFactory] = None


def get_factory(config: Optional[AppConfig] = None) -> ServiceFactory:
    """
    Get or create global service factory.

    Args:
        config: Optional configuration (only used for first creation)

    Returns:
        Global service factory
    """
    global _factory
    if _factory is None:
        _factory = ServiceFactory(config)
    return _factory


def cleanup_factory() -> None:
    """Cleanup the global factory."""
    global _factory
    if _factory is not None:
        _factory.cleanup()
        _factory = None


# Backward compatibility aliases
DependencyContainer = ServiceFactory
get_container = get_factory
cleanup_container = cleanup_factory
