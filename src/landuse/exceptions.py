"""Custom exception hierarchy for the landuse application."""


class LanduseError(Exception):
    """Base exception for all landuse-related errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class DatabaseError(LanduseError):
    """Database-related errors."""

    def __init__(self, message: str, query: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.query = query


class QueryValidationError(DatabaseError):
    """SQL query validation errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection errors."""
    pass


class SchemaError(DatabaseError):
    """Database schema-related errors."""
    pass


class SecurityError(LanduseError):
    """Security-related errors."""
    pass


class ConfigurationError(LanduseError):
    """Configuration-related errors."""
    pass


class LLMError(LanduseError):
    """Language model related errors."""

    def __init__(self, message: str, model_name: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.model_name = model_name


class APIKeyError(LLMError):
    """API key related errors."""
    pass


class ToolExecutionError(LanduseError):
    """Tool execution errors."""

    def __init__(self, message: str, tool_name: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.tool_name = tool_name


class ConversationError(LanduseError):
    """Conversation management errors."""
    pass


class GraphExecutionError(LanduseError):
    """LangGraph execution errors."""
    pass


class MapGenerationError(ToolExecutionError):
    """Map generation specific errors."""
    pass


class DataProcessingError(LanduseError):
    """Data processing and conversion errors."""

    def __init__(self, message: str, file_path: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.file_path = file_path


class ValidationError(LanduseError):
    """Data validation errors."""

    def __init__(self, message: str, field_name: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.field_name = field_name


# Mapping of common exception types to our custom exceptions
EXCEPTION_MAPPING = {
    # Database exceptions
    'duckdb.Error': DatabaseError,
    'duckdb.CatalogException': SchemaError,
    'duckdb.SyntaxException': QueryValidationError,
    'duckdb.BinderException': QueryValidationError,
    'duckdb.ConversionException': DatabaseError,
    'sqlite3.Error': DatabaseError,
    'sqlite3.OperationalError': DatabaseError,

    # Network/API exceptions
    'requests.exceptions.RequestException': LLMError,
    'requests.exceptions.ConnectionError': ConnectionError,
    'requests.exceptions.Timeout': LLMError,
    'requests.exceptions.HTTPError': LLMError,

    # File/IO exceptions
    'FileNotFoundError': DataProcessingError,
    'PermissionError': DataProcessingError,
    'OSError': DataProcessingError,
    'IOError': DataProcessingError,

    # JSON/Data exceptions
    'json.JSONDecodeError': DataProcessingError,
    'ValueError': ValidationError,
    'KeyError': ValidationError,
    'TypeError': ValidationError,

    # LangChain exceptions
    'langchain.schema.LLMError': LLMError,
    'langchain_core.exceptions.LangChainException': LLMError,
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
            elif isinstance(e, (ConnectionError, OSError)):
                raise ConnectionError(f"Connection failed in {func.__name__}: {str(e)}")
            else:
                raise wrap_exception(e, f"Error in {func.__name__}")

    return wrapper
