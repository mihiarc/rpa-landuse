"""Custom exception hierarchy for the landuse application.

Provides a comprehensive exception hierarchy with specific exception types:
- LanduseError: Base exception for all landuse-related errors
- DatabaseError: Database-related errors with specific subtypes
- ConfigurationError: Configuration and setup errors
- AgentError: Agent-related errors with specific subtypes
- SecurityError: Security-related errors
- ValidationError: Data validation errors
"""


class LanduseError(Exception):
    """Base exception for all landuse-related errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


# =============================================================================
# Database Exceptions
# =============================================================================

class DatabaseError(LanduseError):
    """Base class for database-related errors."""

    def __init__(self, message: str, query: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.query = query


class DatabaseConnectionError(DatabaseError):
    """Database connection failures."""

    def __init__(self, message: str, host: str = None, error_code: str = None):
        super().__init__(message, error_code=error_code)
        self.host = host


class SchemaError(DatabaseError):
    """Schema-related errors (missing tables, columns, etc.)."""

    def __init__(self, message: str, table_name: str = None, error_code: str = None):
        super().__init__(message, error_code=error_code)
        self.table_name = table_name


class MigrationError(DatabaseError):
    """Database migration failures."""

    def __init__(self, message: str, migration_version: str = None, error_code: str = None):
        super().__init__(message, error_code=error_code)
        self.migration_version = migration_version


class QueryValidationError(DatabaseError):
    """SQL query validation failures (security, syntax)."""

    def __init__(self, message: str, query: str = None, validation_type: str = None, error_code: str = None):
        super().__init__(message, query=query, error_code=error_code)
        self.validation_type = validation_type


# =============================================================================
# Configuration Exceptions
# =============================================================================

class ConfigurationError(LanduseError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_key: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.config_key = config_key


# =============================================================================
# Agent Exceptions
# =============================================================================

class AgentError(LanduseError):
    """Base class for agent-related errors."""

    def __init__(self, message: str, component: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.component = component


class LLMError(AgentError):
    """LLM API errors (rate limits, invalid responses, etc.)."""

    def __init__(self, message: str, model_name: str = None, error_code: str = None):
        super().__init__(message, component='llm', error_code=error_code)
        self.model_name = model_name


class APIKeyError(AgentError):
    """API key validation errors."""

    def __init__(self, message: str, key_type: str = None, error_code: str = None):
        super().__init__(message, component='api_key', error_code=error_code)
        self.key_type = key_type


class ToolExecutionError(AgentError):
    """Tool execution failures."""

    def __init__(self, message: str, tool_name: str = None, error_code: str = None):
        super().__init__(message, component='tool', error_code=error_code)
        self.tool_name = tool_name


class GraphExecutionError(AgentError):
    """LangGraph workflow execution errors."""

    def __init__(self, message: str, node_name: str = None, error_code: str = None):
        super().__init__(message, component='graph', error_code=error_code)
        self.node_name = node_name


class ConversationError(AgentError):
    """Conversation memory/history errors."""

    def __init__(self, message: str, thread_id: str = None, error_code: str = None):
        super().__init__(message, component='conversation', error_code=error_code)
        self.thread_id = thread_id


class MapGenerationError(AgentError):
    """Map generation/visualization errors."""

    def __init__(self, message: str, map_type: str = None, error_code: str = None):
        super().__init__(message, component='map', error_code=error_code)
        self.map_type = map_type


# =============================================================================
# Security Exceptions
# =============================================================================

class SecurityError(LanduseError):
    """Security-related errors (SQL injection, unauthorized access, etc.)."""

    def __init__(self, message: str, security_context: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.security_context = security_context


class RateLimitError(SecurityError):
    """Rate limit exceeded errors."""

    def __init__(self, message: str, retry_after: float = None, error_code: str = None):
        super().__init__(message, security_context='rate_limit', error_code=error_code)
        self.retry_after = retry_after


# =============================================================================
# Validation Exceptions
# =============================================================================

class ValidationError(LanduseError):
    """Data validation errors."""

    def __init__(self, message: str, field_name: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.field_name = field_name


class DataProcessingError(ValidationError):
    """Data processing/transformation errors."""

    def __init__(self, message: str, data_type: str = None, error_code: str = None):
        super().__init__(message, error_code=error_code)
        self.data_type = data_type


# =============================================================================
# Exception Mapping and Utilities
# =============================================================================

# Mapping of common exception types to our custom exceptions
EXCEPTION_MAPPING = {
    # Database exceptions
    'duckdb.Error': DatabaseError,
    'duckdb.CatalogException': SchemaError,
    'duckdb.SyntaxException': QueryValidationError,
    'duckdb.BinderException': QueryValidationError,
    'duckdb.ConversionException': ValidationError,
    'sqlite3.Error': DatabaseError,
    'sqlite3.OperationalError': DatabaseConnectionError,

    # Network/API exceptions
    'requests.exceptions.RequestException': LLMError,
    'requests.exceptions.ConnectionError': DatabaseConnectionError,
    'requests.exceptions.Timeout': LLMError,
    'requests.exceptions.HTTPError': LLMError,

    # File/IO exceptions
    'FileNotFoundError': ValidationError,
    'PermissionError': SecurityError,
    'OSError': ValidationError,
    'IOError': ValidationError,

    # JSON/Data exceptions
    'json.JSONDecodeError': ValidationError,
    'ValueError': ValidationError,
    'KeyError': ValidationError,
    'TypeError': ValidationError,

    # LangChain exceptions
    'langchain.schema.LLMError': LLMError,
    'langchain_core.exceptions.LangChainException': AgentError,
}


def wrap_exception(original_exception: Exception, context: str = None) -> LanduseError:
    """
    Wrap a standard exception into our custom exception hierarchy.

    Args:
        original_exception: The original exception to wrap
        context: Additional context about where the error occurred

    Returns:
        LanduseError: Wrapped exception with proper type
    """
    exception_type = type(original_exception).__name__
    exception_module = type(original_exception).__module__
    full_type = f"{exception_module}.{exception_type}" if exception_module != 'builtins' else exception_type

    # Look for specific mapping
    if full_type in EXCEPTION_MAPPING:
        custom_exception_class = EXCEPTION_MAPPING[full_type]
    elif exception_type in EXCEPTION_MAPPING:
        custom_exception_class = EXCEPTION_MAPPING[exception_type]
    else:
        # Default to base exception
        custom_exception_class = LanduseError

    # Create message with context
    message = str(original_exception)
    if context:
        message = f"{context}: {message}"

    # Create the custom exception
    try:
        return custom_exception_class(message)
    except TypeError:
        # Fallback if constructor doesn't match
        return LanduseError(message)


def handle_database_exception(func):
    """
    Decorator to handle database exceptions and convert them to custom exceptions.

    Usage:
        @handle_database_exception
        def my_database_function():
            # database code here
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert to our custom exception hierarchy
            if 'duckdb' in str(type(e)).lower():
                raise wrap_exception(e, f"Database error in {func.__name__}")
            elif isinstance(e, OSError):
                raise DatabaseConnectionError(f"Connection failed in {func.__name__}: {str(e)}")
            else:
                raise wrap_exception(e, f"Error in {func.__name__}")

    return wrapper
