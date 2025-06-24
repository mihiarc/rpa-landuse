# Retry Logic with Tenacity

This document describes the implementation of robust retry logic throughout the landuse project using the tenacity library and custom fallback mechanisms.

## Overview

The retry system provides automatic error recovery for transient failures in database connections, API calls, file operations, and network requests. This improves reliability and user experience by handling temporary issues gracefully.

## Implementation

### Core Components

1. **Retry Decorators** (`src/landuse/utils/retry_decorators.py`)
   - Specialized decorators for different operation types
   - Configurable retry strategies and wait times
   - Fallback implementation when tenacity is unavailable

2. **Integration Points**
   - Database connections and queries
   - Bulk loading operations
   - Agent tool executions
   - File I/O operations

### Retry Decorators

#### Database Operations

```python
from landuse.utils.retry_decorators import database_retry

@database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
def connect_to_database():
    return duckdb.connect("database.duckdb")
```

**Configuration:**
- **Max Attempts**: 3 (reasonable for database operations)
- **Wait Strategy**: Exponential backoff (1s → 2s → 4s → ...)
- **Max Wait**: 10 seconds (prevents excessive delays)
- **Retryable Exceptions**: `ConnectionError`, `TimeoutError`, `OSError`

#### API Operations

```python
from landuse.utils.retry_decorators import api_retry

@api_retry(max_attempts=5, base_wait=2.0, max_wait=60.0)
def call_external_api():
    response = requests.get("https://api.example.com/data")
    return response.json()
```

**Configuration:**
- **Max Attempts**: 5 (APIs may have intermittent issues)
- **Wait Strategy**: Exponential backoff with base 2 seconds
- **Max Wait**: 60 seconds (API rate limiting consideration)
- **Retryable Exceptions**: `ConnectionError`, `TimeoutError`, `OSError`

#### File Operations

```python
from landuse.utils.retry_decorators import file_retry

@file_retry(max_attempts=3, wait_time=2.0)
def write_to_file(filename, data):
    with open(filename, 'w') as f:
        f.write(data)
```

**Configuration:**
- **Max Attempts**: 3 (file locks usually resolve quickly)
- **Wait Strategy**: Fixed wait time
- **Wait Time**: 2 seconds (allows file locks to clear)
- **Retryable Exceptions**: `FileNotFoundError`, `PermissionError`, `OSError`

#### Network Operations

```python
from landuse.utils.retry_decorators import network_retry

@network_retry(max_attempts=5, min_wait=2.0, max_wait=30.0)
def download_data():
    response = urllib.request.urlopen("https://example.com/data.json")
    return response.read()
```

**Configuration:**
- **Max Attempts**: 5 (network issues can be intermittent)
- **Wait Strategy**: Exponential backoff
- **Wait Range**: 2-30 seconds
- **Retryable Exceptions**: `ConnectionError`, `TimeoutError`

### Advanced Retry Patterns

#### Result-Based Retries

```python
from landuse.utils.retry_decorators import retry_on_result

@retry_on_result(
    result_predicate=lambda x: x is None or x.get('status') == 'pending',
    max_attempts=10,
    wait_time=5.0
)
def poll_for_completion():
    """Retry until we get a complete result"""
    status = check_processing_status()
    return status
```

#### Custom Retry Logic

```python
from landuse.utils.retry_decorators import custom_retry
from tenacity import stop_after_delay, wait_random_exponential

@custom_retry(
    stop_condition=stop_after_delay(300),  # Stop after 5 minutes
    wait_strategy=wait_random_exponential(multiplier=1, max=60),
    retry_condition=retry_if_exception_type((ConnectionError, TimeoutError))
)
def complex_operation():
    # Complex operation with custom retry logic
    pass
```

#### Context Manager Approach

```python
from landuse.utils.retry_decorators import RetryableOperation

with RetryableOperation(
    "Database migration",
    max_attempts=5,
    wait_strategy="exponential",
    min_wait=2.0,
    max_wait=60.0
) as op:
    result = op.execute(migrate_database_schema)
```

#### Utility Function Approach

```python
from landuse.utils.retry_decorators import execute_with_retry

result = execute_with_retry(
    func=complex_database_operation,
    operation_name="Complex DB Operation",
    max_attempts=3,
    wait_strategy="exponential",
    min_wait=1.0,
    max_wait=30.0,
    exceptions=(ConnectionError, TimeoutError),
    # Function arguments
    table_name="landuse_data",
    batch_size=10000
)
```

## Integration Examples

### Database Connections

**Before (no retry):**
```python
def connect_to_database():
    return duckdb.connect("database.duckdb")  # Fails on temporary issues
```

**After (with retry):**
```python
@database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
def connect_to_database():
    try:
        return duckdb.connect("database.duckdb")
    except Exception as e:
        raise ConnectionError(f"Failed to connect: {e}") from e
```

### Bulk Loading Operations

**Enhanced bulk loader with retry logic:**
```python
class DuckDBBulkLoader:
    @contextmanager
    def connection(self):
        try:
            self.conn = execute_with_retry(
                duckdb.connect,
                operation_name=f"DuckDB connection to {self.db_path}",
                max_attempts=3,
                wait_strategy="exponential",
                exceptions=(ConnectionError, OSError, RuntimeError),
                database=str(self.db_path)
            )
            yield self.conn
        finally:
            if self.conn:
                self.conn.close()
    
    def bulk_load_dataframe(self, df, table_name):
        # Write Parquet with retry
        execute_with_retry(
            df.to_parquet,
            operation_name=f"Writing Parquet file",
            max_attempts=3,
            exceptions=(OSError, PermissionError, IOError),
            path=temp_file,
            index=False,
            compression=self.compression
        )
        
        # Execute COPY with retry
        with self.connection() as conn:
            execute_with_retry(
                conn.execute,
                operation_name=f"COPY command for {table_name}",
                max_attempts=3,
                wait_strategy="exponential",
                exceptions=(ConnectionError, RuntimeError, OSError),
                query=copy_sql
            )
```

### Agent Query Execution

**Enhanced agent with retry logic:**
```python
class BaseLanduseAgent:
    @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0, 
                   exceptions=(ConnectionError, TimeoutError, OSError))
    def _execute_landuse_query(self, sql_query: str) -> str:
        try:
            # Query execution with automatic retry on connection issues
            conn = duckdb.connect(str(self.db_path), read_only=True)
            result = conn.execute(sql_query)
            df = result.df()
            conn.close()
            return format_query_results(df, sql_query)
        except (ConnectionError, TimeoutError, OSError):
            # These will trigger retries via the decorator
            raise
        except Exception as e:
            # Other errors (syntax, etc.) should not be retried
            return f"❌ Error: {e}"
```

## Configuration

### Environment Variables

Configure retry behavior via environment variables:

```bash
# Retry configuration
LANDUSE_DB_RETRY_ATTEMPTS=3
LANDUSE_DB_RETRY_MIN_WAIT=1.0
LANDUSE_DB_RETRY_MAX_WAIT=10.0

LANDUSE_API_RETRY_ATTEMPTS=5
LANDUSE_API_RETRY_BASE_WAIT=2.0
LANDUSE_API_RETRY_MAX_WAIT=60.0

LANDUSE_FILE_RETRY_ATTEMPTS=3
LANDUSE_FILE_RETRY_WAIT=2.0
```

### Pydantic Configuration Model

```python
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    """Configuration for retry behavior"""
    
    # Database retries
    db_max_attempts: int = Field(default=3, ge=1, le=10)
    db_min_wait: float = Field(default=1.0, ge=0.1, le=60.0)
    db_max_wait: float = Field(default=10.0, ge=1.0, le=300.0)
    
    # API retries
    api_max_attempts: int = Field(default=5, ge=1, le=20)
    api_base_wait: float = Field(default=2.0, ge=0.1, le=60.0)
    api_max_wait: float = Field(default=60.0, ge=1.0, le=600.0)
    
    # File retries
    file_max_attempts: int = Field(default=3, ge=1, le=10)
    file_wait_time: float = Field(default=2.0, ge=0.1, le=60.0)
```

## Best Practices

### When to Use Retries

✅ **Good candidates for retries:**
- Database connection failures
- Network timeouts
- Temporary file access issues
- API rate limiting (with backoff)
- Cloud service intermittent failures

❌ **Poor candidates for retries:**
- SQL syntax errors
- Authentication failures
- Permission denied errors
- Invalid input data
- Logic errors in code

### Retry Strategy Selection

1. **Exponential Backoff** (recommended for most cases)
   - Good for handling increasing load
   - Prevents thundering herd problems
   - Self-adapting to system recovery time

2. **Fixed Wait** (good for known recovery times)
   - Predictable timing
   - Good for file locking scenarios
   - Simple and deterministic

3. **Linear Backoff** (middle ground)
   - Gradual increase in wait time
   - Less aggressive than exponential
   - Good for rate-limited APIs

### Error Classification

**Retryable Errors:**
```python
RETRYABLE_EXCEPTIONS = (
    ConnectionError,      # Network/DB connection issues
    TimeoutError,        # Request timeouts
    OSError,             # System-level errors
    RuntimeError,        # DuckDB runtime issues (sometimes)
)
```

**Non-Retryable Errors:**
```python
NON_RETRYABLE_EXCEPTIONS = (
    ValueError,          # Input validation errors
    TypeError,           # Programming errors
    KeyError,           # Missing keys/columns
    AttributeError,     # Object attribute errors
    SyntaxError,        # SQL syntax errors
    PermissionError,    # Authorization failures (usually)
)
```

### Monitoring and Logging

**Rich Console Integration:**
```python
from rich.console import Console

console = Console()

@database_retry(max_attempts=3)
def database_operation():
    try:
        # Operation logic
        console.print("✅ Database operation succeeded")
        return result
    except Exception as e:
        console.print(f"⚠️ Database operation failed: {e}")
        raise
```

**Structured Logging:**
```python
import logging
from landuse.utils.retry_decorators import database_retry

logger = logging.getLogger(__name__)

@database_retry(max_attempts=3)
def database_operation():
    logger.info("Starting database operation")
    try:
        result = perform_operation()
        logger.info("Database operation completed successfully")
        return result
    except Exception as e:
        logger.warning(f"Database operation failed, will retry: {e}")
        raise
```

## Fallback Implementation

When tenacity is not available, the system provides a fallback implementation:

```python
def _fallback_retry(max_attempts: int, wait_time: float):
    """Basic retry implementation without tenacity"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        console.print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                        console.print(f"🔄 Retrying in {wait_time}s...")
                        time.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator
```

**Features of fallback:**
- Basic retry functionality
- Fixed wait times
- Rich console output
- Exception preservation
- No external dependencies

## Testing

### Unit Tests

```python
def test_retry_with_eventual_success():
    call_count = 0
    
    @database_retry(max_attempts=3, min_wait=0.1)
    def mock_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = mock_operation()
    assert result == "success"
    assert call_count == 3
```

### Integration Tests

```python
def test_database_retry_integration():
    """Test retry behavior with real database operations"""
    with temporary_database() as db_path:
        # Test connection retry
        @database_retry(max_attempts=3)
        def connect_and_query():
            conn = duckdb.connect(db_path)
            result = conn.execute("SELECT 1").fetchone()
            conn.close()
            return result[0]
        
        result = connect_and_query()
        assert result == 1
```

### Mocking for Tests

```python
from unittest.mock import patch, Mock

def test_retry_with_mocked_failures():
    mock_func = Mock()
    mock_func.side_effect = [
        ConnectionError("First failure"),
        ConnectionError("Second failure"), 
        "success"
    ]
    
    @database_retry(max_attempts=3, min_wait=0.1)
    def operation():
        return mock_func()
    
    result = operation()
    assert result == "success"
    assert mock_func.call_count == 3
```

## Performance Considerations

### Retry Overhead

- **Minimal overhead** for successful operations (single decorator call)
- **Exponential cost** for failing operations (wait times increase)
- **Memory usage** remains constant (no accumulation)

### Timing Considerations

```python
# Fast operations - shorter timeouts
@database_retry(max_attempts=3, min_wait=0.5, max_wait=5.0)
def quick_query():
    pass

# Slow operations - longer timeouts  
@database_retry(max_attempts=5, min_wait=2.0, max_wait=60.0)
def heavy_computation():
    pass
```

### Circuit Breaker Pattern

For high-failure scenarios, consider implementing circuit breaker:

```python
from landuse.utils.retry_decorators import RetryableOperation

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            with RetryableOperation("Circuit breaker operation") as op:
                result = op.execute(func, *args, **kwargs)
            
            # Success - reset circuit breaker
            self.failure_count = 0
            self.state = "CLOSED"
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise
```

## Dependencies

### Required Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "tenacity>=8.0.0",  # Advanced retry functionality
    "rich>=13.0.0",     # Console output
]

[project.optional-dependencies]
retry = [
    "tenacity>=8.0.0",
]
```

### Installation

```bash
# Install with retry functionality
uv add tenacity

# Or install optional retry dependencies
uv sync --extras retry
```

## Migration Guide

### Adding Retries to Existing Code

1. **Identify retry candidates:**
   ```python
   # Before: No error handling
   def fragile_operation():
       conn = duckdb.connect("database.duckdb")
       return conn.execute("SELECT * FROM table").fetchall()
   ```

2. **Add appropriate retry decorator:**
   ```python
   # After: With retry logic
   from landuse.utils.retry_decorators import database_retry
   
   @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
   def robust_operation():
       try:
           conn = duckdb.connect("database.duckdb")
           return conn.execute("SELECT * FROM table").fetchall()
       except Exception as e:
           # Convert to retryable exception if appropriate
           if "connection" in str(e).lower():
               raise ConnectionError(f"Database connection failed: {e}")
           raise  # Re-raise non-retryable exceptions
   ```

3. **Test retry behavior:**
   ```python
   # Test with mocked failures
   with patch('duckdb.connect') as mock_connect:
       mock_connect.side_effect = [
           ConnectionError("First failure"),
           ConnectionError("Second failure"),
           Mock()  # Success on third attempt
       ]
       
       result = robust_operation()
       assert mock_connect.call_count == 3
   ```

### Gradual Migration Strategy

1. **Phase 1**: Add retries to critical database operations
2. **Phase 2**: Add retries to file I/O operations  
3. **Phase 3**: Add retries to API calls and network operations
4. **Phase 4**: Implement circuit breaker for high-failure scenarios

## Troubleshooting

### Common Issues

**Problem**: Retries not working
```python
# Check if tenacity is installed
from landuse.utils.retry_decorators import HAS_TENACITY
print(f"Tenacity available: {HAS_TENACITY}")

# Verify exception types are retryable
@database_retry(exceptions=(YourExceptionType,))
def your_function():
    pass
```

**Problem**: Too many retries
```python
# Reduce retry attempts for faster failure
@database_retry(max_attempts=2, min_wait=0.5, max_wait=5.0)
def quick_fail_operation():
    pass
```

**Problem**: Retries too slow
```python
# Use fixed wait for predictable timing
@file_retry(max_attempts=3, wait_time=1.0)
def fast_retry_operation():
    pass
```

### Debugging Retry Behavior

```python
import logging

# Enable tenacity logging
logging.getLogger('tenacity').setLevel(logging.DEBUG)

# Add custom retry callback
from tenacity import before_sleep_log, after_log

@database_retry(
    max_attempts=3,
    before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    after=after_log(logging.getLogger(__name__), logging.INFO)
)
def debug_operation():
    pass
```

## Related Documentation

- [Database Connections](./database-connections.md)
- [Error Handling](./error-handling.md)
- [Performance Optimization](../performance/optimization-guide.md)
- [Testing Guidelines](./testing-guidelines.md)