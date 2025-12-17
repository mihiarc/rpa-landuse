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
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LanduseError:
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            # Convert to our custom exception hierarchy
            if 'duckdb' in str(type(e)).lower():
                raise wrap_exception(e, f"Database error in {func.__name__}")
            elif isinstance(e, OSError):
                raise DatabaseConnectionError(f"Connection failed in {func.__name__}: {str(e)}")
            else:
                raise wrap_exception(e, f"Error in {func.__name__}")

    return wrapper


def handle_tool_exception(func):
    """
    Decorator to handle tool execution exceptions consistently.

    Usage:
        @handle_tool_exception
        def my_tool_function():
            # tool code here
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LanduseError:
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"Tool '{func.__name__}' failed: {str(e)}",
                tool_name=func.__name__
            )

    return wrapper


def handle_query_error(error: Exception, query: str = None, context: str = None) -> dict:
    """
    Handle query errors and return a standardized error response dict.

    Args:
        error: The exception that occurred
        query: The SQL query that failed (optional)
        context: Additional context about where the error occurred

    Returns:
        dict: Standardized error response with 'success', 'error', and 'suggestion' keys
    """
    import duckdb

    # Determine error type and suggestion
    error_msg = str(error)
    suggestion = None

    if isinstance(error, (duckdb.CatalogException, SchemaError)):
        suggestion = "Check table and column names. Use explore_landuse_schema to see available tables."
    elif isinstance(error, (duckdb.SyntaxException, duckdb.BinderException, QueryValidationError)):
        suggestion = "Check SQL syntax. Ensure proper quoting and valid expressions."
    elif isinstance(error, SecurityError):
        suggestion = "Query was blocked for security reasons. Only SELECT queries are allowed."
    elif isinstance(error, DatabaseConnectionError):
        suggestion = "Check database connectivity and file permissions."
    elif isinstance(error, ValueError):
        suggestion = "Check input values and query parameters."
    else:
        suggestion = "Check query syntax and try a simpler query."

    # Build context-aware message
    if context:
        error_msg = f"{context}: {error_msg}"

    return {
        "success": False,
        "error": error_msg,
        "query": query,
        "suggestion": suggestion
    }


def safe_execute(func, *args, default=None, context: str = None, **kwargs):
    """
    Safely execute a function, returning a default value on error.

    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        default: Default value to return on error (default: None)
        context: Context string for error logging
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except LanduseError:
        # Re-raise our custom exceptions
        raise
    except Exception:
        return default


def format_error_for_user(error: Exception, include_suggestion: bool = True) -> str:
    """
    Format an error message for display to users.

    Args:
        error: The exception to format
        include_suggestion: Whether to include a suggestion for fixing the error

    Returns:
        str: User-friendly error message
    """
    if isinstance(error, LanduseError):
        msg = error.message
        if include_suggestion:
            if isinstance(error, DatabaseError):
                msg += "\n\nSuggestion: Check database connectivity and query syntax."
            elif isinstance(error, SecurityError):
                msg += "\n\nSuggestion: This action was blocked for security reasons."
            elif isinstance(error, ValidationError):
                msg += "\n\nSuggestion: Check input values and try again."
        return msg
    else:
        return f"An unexpected error occurred: {str(error)}"
