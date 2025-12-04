"""Custom exception hierarchy for the landuse application.

Consolidated exception hierarchy with 6 main exception types:
- LanduseError: Base exception for all landuse-related errors
- DatabaseError: All database-related errors (connections, schema, migrations, queries)
- ConfigurationError: Configuration and setup errors
- AgentError: LLM, tool execution, graph execution, and conversation errors
- SecurityError: Security-related errors
- ValidationError: Data validation errors
"""


class LanduseError(Exception):
    """Base exception for all landuse-related errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class DatabaseError(LanduseError):
    """Database-related errors including connections, schema, migrations, and queries.

    Consolidates: ConnectionError, SchemaError, MigrationError, QueryValidationError
    """

    def __init__(self, message: str, query: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.query = query


# Backward compatibility aliases for DatabaseError subtypes
DatabaseConnectionError = DatabaseError  # Renamed from ConnectionError to avoid shadowing builtin
SchemaError = DatabaseError
MigrationError = DatabaseError
QueryValidationError = DatabaseError


class ConfigurationError(LanduseError):
    """Configuration-related errors."""
    pass


class AgentError(LanduseError):
    """Agent-related errors including LLM, tool execution, graph execution, and conversation.

    Consolidates: LLMError, APIKeyError, ToolExecutionError, GraphExecutionError,
                  ConversationError, MapGenerationError
    """

    def __init__(self, message: str, component: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.component = component  # e.g., 'llm', 'tool', 'graph', 'conversation'


# Backward compatibility aliases for AgentError subtypes
LLMError = AgentError
APIKeyError = AgentError
ToolExecutionError = AgentError
GraphExecutionError = AgentError
ConversationError = AgentError
MapGenerationError = AgentError


class SecurityError(LanduseError):
    """Security-related errors."""
    pass


class ValidationError(LanduseError):
    """Data validation errors."""

    def __init__(self, message: str, field_name: str = None, error_code: str = None):
        super().__init__(message, error_code)
        self.field_name = field_name


# Backward compatibility alias
DataProcessingError = ValidationError


# Mapping of common exception types to our custom exceptions
EXCEPTION_MAPPING = {
    # Database exceptions
    'duckdb.Error': DatabaseError,
    'duckdb.CatalogException': DatabaseError,
    'duckdb.SyntaxException': DatabaseError,
    'duckdb.BinderException': DatabaseError,
    'duckdb.ConversionException': DatabaseError,
    'sqlite3.Error': DatabaseError,
    'sqlite3.OperationalError': DatabaseError,

    # Network/API exceptions
    'requests.exceptions.RequestException': AgentError,
    'requests.exceptions.ConnectionError': DatabaseError,
    'requests.exceptions.Timeout': AgentError,
    'requests.exceptions.HTTPError': AgentError,

    # File/IO exceptions
    'FileNotFoundError': ValidationError,
    'PermissionError': ValidationError,
    'OSError': ValidationError,
    'IOError': ValidationError,

    # JSON/Data exceptions
    'json.JSONDecodeError': ValidationError,
    'ValueError': ValidationError,
    'KeyError': ValidationError,
    'TypeError': ValidationError,

    # LangChain exceptions
    'langchain.schema.LLMError': AgentError,
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
                raise DatabaseError(f"Connection failed in {func.__name__}: {str(e)}")
            else:
                raise wrap_exception(e, f"Error in {func.__name__}")

    return wrapper
