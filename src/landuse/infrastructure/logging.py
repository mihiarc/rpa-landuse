"""Structured logging implementation with global singleton and component loggers."""

import json
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

from landuse.core.app_config import AppConfig, LoggingConfig
from landuse.core.interfaces import LoggerInterface

# Global logger instance (singleton)
_logger_instance: Optional["StructuredLogger"] = None
_logger_lock = threading.Lock()


def get_logger(component: Optional[str] = None) -> "StructuredLogger":
    """
    Get the global logger instance or a component-specific logger.

    This is the recommended way to get a logger throughout the application.
    The logger is lazily initialized on first use with default configuration.

    Args:
        component: Optional component name for child logger (e.g., 'database', 'llm')

    Returns:
        StructuredLogger instance

    Example:
        >>> from landuse.infrastructure.logging import get_logger
        >>> logger = get_logger('database')
        >>> logger.info("Connected to database", path="/data/db.duckdb")
    """
    global _logger_instance

    if _logger_instance is None:
        with _logger_lock:
            if _logger_instance is None:
                # Initialize with default config
                config = AppConfig()
                _logger_instance = StructuredLogger(config.logging)

    if component:
        return _logger_instance.get_child(component)

    return _logger_instance


def configure_logging(config: LoggingConfig) -> "StructuredLogger":
    """
    Configure the global logger with specific settings.

    Call this early in application startup to configure logging before
    other components initialize.

    Args:
        config: Logging configuration

    Returns:
        Configured StructuredLogger instance

    Example:
        >>> from landuse.core.app_config import LoggingConfig
        >>> config = LoggingConfig(level='DEBUG', log_file='logs/app.log')
        >>> logger = configure_logging(config)
    """
    global _logger_instance

    with _logger_lock:
        _logger_instance = StructuredLogger(config)

    return _logger_instance


def reset_logging() -> None:
    """Reset the global logger (primarily for testing)."""
    global _logger_instance

    with _logger_lock:
        if _logger_instance is not None:
            _logger_instance.shutdown()
        _logger_instance = None


class StructuredLogger(LoggerInterface):
    """
    Structured logger with rich console output and optional file logging.

    Features:
    - Structured JSON logging to files
    - Rich console output for development
    - Performance timing support
    - Security event logging
    - Component-specific child loggers
    - Thread-safe operation
    """

    def __init__(self, config: LoggingConfig):
        """Initialize structured logger.

        Args:
            config: Logging configuration
        """
        self.config = config
        self.console = Console(stderr=True)  # Log to stderr to not interfere with output
        self._children: Dict[str, StructuredLogger] = {}
        self._component: Optional[str] = None

        # Create main logger
        self.logger = self._setup_logger()

        # Create specialized loggers
        self.security_logger = self._setup_security_logger()
        self.performance_logger = self._setup_performance_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up main application logger."""
        logger_name = "landuse"
        if self._component:
            logger_name = f"landuse.{self._component}"

        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, self.config.level))

        # Only add handlers to root landuse logger
        if not self._component and not logger.handlers:
            # Add console handler with Rich for non-file logging
            if not self.config.log_file:
                rich_handler = RichHandler(
                    console=self.console, show_time=True, show_path=False, rich_tracebacks=True, markup=True
                )
                rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="%H:%M:%S"))
                rich_handler.setLevel(getattr(logging, self.config.level))
                logger.addHandler(rich_handler)

            # Add file handler if configured
            if self.config.log_file:
                log_path = Path(self.config.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = logging.FileHandler(self.config.log_file)
                file_handler.setFormatter(StructuredFormatter())
                file_handler.setLevel(getattr(logging, self.config.level))
                logger.addHandler(file_handler)

                # Also add a console handler for visibility
                console_handler = logging.StreamHandler(sys.stderr)
                console_handler.setFormatter(
                    logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
                )
                console_handler.setLevel(getattr(logging, self.config.level))
                logger.addHandler(console_handler)

        return logger

    def _setup_security_logger(self) -> logging.Logger:
        """Set up security event logger."""
        security_logger = logging.getLogger("landuse.security")
        security_logger.setLevel(logging.INFO)

        if self.config.log_file and not security_logger.handlers:
            security_log_path = Path(self.config.log_file).parent / "security.log"
            security_log_path.parent.mkdir(parents=True, exist_ok=True)

            security_handler = logging.FileHandler(security_log_path)
            security_handler.setFormatter(StructuredFormatter())
            security_logger.addHandler(security_handler)

        return security_logger

    def _setup_performance_logger(self) -> logging.Logger:
        """Set up performance metrics logger."""
        perf_logger = logging.getLogger("landuse.performance")
        perf_logger.setLevel(logging.INFO)

        if self.config.enable_performance_logging and self.config.log_file:
            if not perf_logger.handlers:
                perf_log_path = Path(self.config.log_file).parent / "performance.log"
                perf_log_path.parent.mkdir(parents=True, exist_ok=True)

                perf_handler = logging.FileHandler(perf_log_path)
                perf_handler.setFormatter(StructuredFormatter())
                perf_logger.addHandler(perf_handler)

        return perf_logger

    def get_child(self, component: str) -> "StructuredLogger":
        """
        Get a child logger for a specific component.

        Child loggers inherit the parent's configuration but use
        a component-specific logger name for filtering.

        Args:
            component: Component name (e.g., 'database', 'llm', 'agent')

        Returns:
            Child StructuredLogger instance
        """
        if component not in self._children:
            child = StructuredLogger.__new__(StructuredLogger)
            child.config = self.config
            child.console = self.console
            child._children = {}
            child._component = component
            child.logger = logging.getLogger(f"landuse.{component}")
            child.logger.setLevel(getattr(logging, self.config.level))
            child.security_logger = self.security_logger
            child.performance_logger = self.performance_logger
            self._children[component] = child

        return self._children[component]

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional context."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional context."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional context."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional context."""
        self._log(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log error message with exception traceback."""
        self.logger.exception(message, extra=self._build_extra(**kwargs))

    def _log(self, level: int, message: str, **kwargs) -> None:
        """Internal logging method with context support."""
        extra = self._build_extra(**kwargs)
        self.logger.log(level, message, extra=extra)

    def _build_extra(self, **kwargs) -> Dict[str, Any]:
        """Build extra dict for log record."""
        extra = {}
        if self._component:
            extra["component"] = self._component
        extra.update(kwargs)
        return extra

    def security_event(self, event_type: str, message: str, **context) -> None:
        """
        Log security event.

        Args:
            event_type: Type of security event (e.g., 'query_blocked', 'rate_limit')
            message: Event description
            **context: Additional context fields
        """
        full_message = f"[SECURITY:{event_type}] {message}"
        self.security_logger.info(full_message, extra={"event_type": event_type, "security_event": True, **context})
        # Also log to main logger at warning level
        self.warning(full_message, event_type=event_type, **context)

    def performance_event(self, operation: str, duration: float, **context) -> None:
        """
        Log performance event.

        Args:
            operation: Operation name
            duration: Duration in seconds
            **context: Additional context fields
        """
        if self.config.enable_performance_logging:
            self.performance_logger.info(
                f"[PERF] {operation}: {duration:.3f}s",
                extra={"operation": operation, "duration_ms": duration * 1000, "performance_event": True, **context},
            )

    def log_query_execution(self, query: str, duration: float, row_count: int, success: bool = True) -> None:
        """
        Log database query execution.

        Args:
            query: SQL query (will be truncated for logging)
            duration: Query duration in seconds
            row_count: Number of rows returned
            success: Whether query succeeded
        """
        # Truncate query for logging
        query_preview = query[:100] + "..." if len(query) > 100 else query
        query_preview = query_preview.replace("\n", " ")

        self.performance_event(
            "database_query",
            duration,
            query_preview=query_preview,
            query_length=len(query),
            row_count=row_count,
            success=success,
        )

        if success:
            self.debug(f"Query executed: {row_count} rows in {duration:.3f}s")
        else:
            self.warning(f"Query failed after {duration:.3f}s")

    def log_llm_call(
        self, model: str, duration: float, token_count: Optional[int] = None, success: bool = True
    ) -> None:
        """
        Log LLM API call.

        Args:
            model: Model name
            duration: Call duration in seconds
            token_count: Number of tokens used (if available)
            success: Whether call succeeded
        """
        context = {"model": model, "success": success}
        if token_count is not None:
            context["token_count"] = token_count

        self.performance_event("llm_call", duration, **context)

        if success:
            self.debug(f"LLM call to {model}: {duration:.3f}s")
        else:
            self.warning(f"LLM call to {model} failed after {duration:.3f}s")

    def log_agent_action(self, action: str, **context) -> None:
        """
        Log agent action for observability.

        Args:
            action: Action name (e.g., 'tool_call', 'response_generated')
            **context: Additional context
        """
        self.info(f"Agent: {action}", action=action, **context)

    def shutdown(self) -> None:
        """Shutdown logger and flush handlers."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging to files."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields (excluding standard LogRecord attributes)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "exc_info",
            "exc_text",
            "stack_info",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                try:
                    json.dumps(value)  # Check if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


# Convenience functions for quick logging without getting logger first
def log_debug(message: str, **kwargs) -> None:
    """Log debug message to global logger."""
    get_logger().debug(message, **kwargs)


def log_info(message: str, **kwargs) -> None:
    """Log info message to global logger."""
    get_logger().info(message, **kwargs)


def log_warning(message: str, **kwargs) -> None:
    """Log warning message to global logger."""
    get_logger().warning(message, **kwargs)


def log_error(message: str, **kwargs) -> None:
    """Log error message to global logger."""
    get_logger().error(message, **kwargs)
