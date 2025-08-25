"""Dependency injection container for managing component lifecycle and dependencies."""

import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from landuse.core.app_config import AppConfig
from landuse.core.interfaces import (
    AgentInterface,
    CacheInterface,
    ConversationInterface,
    DatabaseInterface,
    LLMInterface,
    LoggerInterface,
    MetricsInterface,
    QueryExecutorInterface,
    SecurityInterface,
    ToolInterface,
)
from landuse.exceptions import ConfigurationError

T = TypeVar('T')


class Singleton(type):
    """Metaclass for singleton pattern."""

    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class DependencyContainer(metaclass=Singleton):
    """
    Dependency injection container for managing application components.

    This container provides:
    - Singleton service registration and resolution
    - Lazy initialization of dependencies
    - Automatic cleanup of resources
    - Thread-safe component access
    - Configuration injection
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize container with configuration."""
        self._config = config or AppConfig()
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.Lock()

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """
        Register a singleton service implementation.

        Args:
            interface: Abstract interface type
            implementation: Concrete implementation type
        """
        with self._lock:
            self._factories[interface] = lambda: implementation(self._config)

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function for creating service instances.

        Args:
            interface: Abstract interface type
            factory: Factory function that creates instances
        """
        with self._lock:
            self._factories[interface] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created instance.

        Args:
            interface: Abstract interface type
            instance: Pre-created instance
        """
        with self._lock:
            self._singletons[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service instance by interface type.

        Args:
            interface: Interface type to resolve

        Returns:
            Service instance

        Raises:
            ConfigurationError: If service not registered
        """
        # Check for pre-registered instance
        if interface in self._singletons:
            return self._singletons[interface]

        # Check for factory
        if interface in self._factories:
            with self._lock:
                # Double-check pattern for thread safety
                if interface not in self._singletons:
                    self._singletons[interface] = self._factories[interface]()
                return self._singletons[interface]

        # Try to auto-resolve from known implementations
        return self._auto_resolve(interface)

    def _auto_resolve(self, interface: Type[T]) -> T:
        """
        Attempt to auto-resolve interface to concrete implementation.

        Args:
            interface: Interface type to resolve

        Returns:
            Service instance

        Raises:
            ConfigurationError: If cannot auto-resolve
        """
        # Auto-resolution mappings for common interfaces
        auto_mappings = {
            DatabaseInterface: self._create_database_service,
            LLMInterface: self._create_llm_service,
            ConversationInterface: self._create_conversation_service,
            QueryExecutorInterface: self._create_query_executor_service,
            SecurityInterface: self._create_security_service,
            ToolInterface: self._create_tool_service,
            CacheInterface: self._create_cache_service,
            LoggerInterface: self._create_logger_service,
            MetricsInterface: self._create_metrics_service
        }

        if interface in auto_mappings:
            with self._lock:
                if interface not in self._singletons:
                    self._singletons[interface] = auto_mappings[interface]()
                return self._singletons[interface]

        raise ConfigurationError(f"No registration found for interface: {interface}")

    def _create_database_service(self) -> DatabaseInterface:
        """Create database service instance."""
        from landuse.agents.database_manager import DatabaseManager
        return DatabaseManager(self._config, None)

    def _create_llm_service(self) -> LLMInterface:
        """Create LLM service instance."""
        from landuse.agents.llm_manager import LLMManager
        return LLMManager(self._config, None)

    def _create_conversation_service(self) -> ConversationInterface:
        """Create conversation service instance."""
        from landuse.agents.conversation_manager import ConversationManager
        return ConversationManager(
            max_history_length=self._config.agent.conversation_history_limit,
            console=None
        )

    def _create_query_executor_service(self) -> QueryExecutorInterface:
        """Create query executor service instance."""
        from landuse.agents.query_executor import QueryExecutor
        db_service = self.resolve(DatabaseInterface)
        return QueryExecutor(self._config, db_service.get_connection(), None)

    def _create_security_service(self) -> SecurityInterface:
        """Create security service instance."""
        from landuse.security.database_security import DatabaseSecurity
        return DatabaseSecurity()

    def _create_tool_service(self) -> ToolInterface:
        """Create tool service instance."""
        from landuse.tools.tool_factory import ToolFactory
        return ToolFactory(self)

    def _create_cache_service(self) -> CacheInterface:
        """Create cache service instance."""
        from landuse.infrastructure.cache import InMemoryCache
        return InMemoryCache()

    def _create_logger_service(self) -> LoggerInterface:
        """Create logger service instance."""
        from landuse.infrastructure.logging import StructuredLogger
        return StructuredLogger(self._config.logging)

    def _create_metrics_service(self) -> MetricsInterface:
        """Create metrics service instance."""
        from landuse.infrastructure.metrics import InMemoryMetrics
        return InMemoryMetrics()

    def configure_from_config(self, config: AppConfig) -> None:
        """
        Update container configuration and reinitialize services.

        Args:
            config: New configuration
        """
        with self._lock:
            self._config = config
            # Clear singletons to force recreation with new config
            self._singletons.clear()

    def cleanup(self) -> None:
        """Cleanup all registered services and resources."""
        with self._lock:
            for service in self._singletons.values():
                if hasattr(service, 'cleanup'):
                    try:
                        service.cleanup()
                    except Exception as e:
                        # Log but don't fail cleanup
                        print(f"Error cleaning up service {type(service)}: {e}")
                elif hasattr(service, 'close'):
                    try:
                        service.close()
                    except Exception as e:
                        print(f"Error closing service {type(service)}: {e}")

            self._singletons.clear()

    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all registered services.

        Returns:
            Dictionary mapping service names to health status
        """
        health_status = {}

        for interface, service in self._singletons.items():
            service_name = interface.__name__
            try:
                if hasattr(service, 'health_check'):
                    health_status[service_name] = service.health_check()
                else:
                    # Default health check - just verify service exists
                    health_status[service_name] = service is not None
            except Exception as e:
                health_status[service_name] = False
                print(f"Health check failed for {service_name}: {e}")

        return health_status

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        return self._config

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container(config: Optional[AppConfig] = None) -> DependencyContainer:
    """
    Get or create global dependency container.

    Args:
        config: Optional configuration (only used for first creation)

    Returns:
        Global dependency container
    """
    global _container
    if _container is None:
        _container = DependencyContainer(config)
    elif config is not None:
        _container.configure_from_config(config)
    return _container


def register_service(interface: Type[T], implementation: Union[Type[T], Callable[[], T], T]) -> None:
    """
    Register a service with the global container.

    Args:
        interface: Interface type
        implementation: Implementation class, factory function, or instance
    """
    container = get_container()

    if callable(implementation) and not isinstance(implementation, type):
        # Factory function
        container.register_factory(interface, implementation)
    elif isinstance(implementation, type):
        # Class type
        container.register_singleton(interface, implementation)
    else:
        # Instance
        container.register_instance(interface, implementation)


def resolve_service(interface: Type[T]) -> T:
    """
    Resolve a service from the global container.

    Args:
        interface: Interface type to resolve

    Returns:
        Service instance
    """
    container = get_container()
    return container.resolve(interface)


def cleanup_container() -> None:
    """Cleanup the global container."""
    global _container
    if _container is not None:
        _container.cleanup()
        _container = None
