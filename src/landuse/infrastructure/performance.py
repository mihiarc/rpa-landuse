"""Performance monitoring decorators and utilities."""

import time
import functools
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from landuse.core.interfaces import LoggerInterface, MetricsInterface

F = TypeVar('F', bound=Callable[..., Any])


class PerformanceMonitor:
    """
    Performance monitoring system with decorator support.
    
    Features:
    - Method execution timing
    - Automatic metrics collection
    - Structured logging integration
    - Context manager support
    - Exception tracking
    """
    
    def __init__(self, logger: Optional[LoggerInterface] = None, metrics: Optional[MetricsInterface] = None):
        """Initialize performance monitor."""
        self.logger = logger
        self.metrics = metrics
    
    def time_execution(
        self, 
        operation_name: Optional[str] = None,
        log_params: bool = False,
        track_exceptions: bool = True,
        tags: Optional[Dict[str, str]] = None
    ) -> Callable[[F], F]:
        """
        Decorator to time method execution and collect performance metrics.
        
        Args:
            operation_name: Custom operation name (defaults to function name)
            log_params: Whether to log function parameters (be careful with sensitive data)
            track_exceptions: Whether to track exceptions in metrics
            tags: Additional tags for metrics
            
        Returns:
            Decorated function
            
        Example:
            @performance_monitor.time_execution("database_query", tags={"type": "select"})
            def execute_query(self, query: str) -> pd.DataFrame:
                return self.connection.execute(query)
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Determine operation name
                op_name = operation_name or f"{func.__module__}.{func.__qualname__}"
                
                # Prepare tags
                metric_tags = tags or {}
                if args and hasattr(args[0], '__class__'):
                    metric_tags['class'] = args[0].__class__.__name__
                
                # Start timing
                start_time = time.time()
                exception_occurred = False
                result = None
                
                try:
                    # Log start if logger available
                    if self.logger:
                        log_data = {'operation': op_name, 'start_time': start_time}
                        if log_params:
                            log_data.update({
                                'args_count': len(args),
                                'kwargs_keys': list(kwargs.keys())
                            })
                        self.logger.debug(f"Starting {op_name}", **log_data)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    exception_occurred = True
                    if track_exceptions and self.metrics:
                        error_tags = {**metric_tags, 'error_type': type(e).__name__}
                        self.metrics.increment_counter(f'{op_name}.errors', error_tags)
                    
                    if self.logger:
                        self.logger.error(
                            f"Exception in {op_name}: {str(e)}", 
                            operation=op_name,
                            error_type=type(e).__name__,
                            exception=str(e)
                        )
                    raise
                    
                finally:
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Update metrics
                    if self.metrics:
                        success_tags = {**metric_tags, 'success': str(not exception_occurred)}
                        self.metrics.record_timer(f'{op_name}.duration', duration, success_tags)
                        self.metrics.increment_counter(f'{op_name}.calls', success_tags)
                    
                    # Log completion
                    if self.logger:
                        self.logger.performance_event(
                            op_name, 
                            duration,
                            success=not exception_occurred,
                            **metric_tags
                        )
            
            return wrapper
        return decorator
    
    def time_context(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing code blocks.
        
        Args:
            operation_name: Name of the operation being timed
            tags: Additional tags for metrics
            
        Example:
            with performance_monitor.time_context("data_processing", {"type": "batch"}):
                process_large_dataset(data)
        """
        return TimedContext(self, operation_name, tags)


class TimedContext:
    """Context manager for timing code execution."""
    
    def __init__(
        self, 
        monitor: PerformanceMonitor, 
        operation_name: str, 
        tags: Optional[Dict[str, str]] = None
    ):
        """Initialize timed context."""
        self.monitor = monitor
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time: Optional[float] = None
        self.exception_occurred = False
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        
        if self.monitor.logger:
            self.monitor.logger.debug(
                f"Starting timed context: {self.operation_name}",
                operation=self.operation_name,
                start_time=self.start_time
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        if self.start_time is None:
            return
        
        duration = time.time() - self.start_time
        self.exception_occurred = exc_type is not None
        
        # Record metrics
        if self.monitor.metrics:
            success_tags = {**self.tags, 'success': str(not self.exception_occurred)}
            self.monitor.metrics.record_timer(
                f'{self.operation_name}.duration', 
                duration, 
                success_tags
            )
            self.monitor.metrics.increment_counter(
                f'{self.operation_name}.calls', 
                success_tags
            )
            
            if self.exception_occurred:
                error_tags = {**self.tags, 'error_type': exc_type.__name__}
                self.monitor.metrics.increment_counter(
                    f'{self.operation_name}.errors', 
                    error_tags
                )
        
        # Log completion
        if self.monitor.logger:
            self.monitor.logger.performance_event(
                self.operation_name,
                duration,
                success=not self.exception_occurred,
                **self.tags
            )


def create_performance_decorator(
    logger: Optional[LoggerInterface] = None,
    metrics: Optional[MetricsInterface] = None
) -> PerformanceMonitor:
    """
    Factory function to create a performance monitor with logging and metrics.
    
    Args:
        logger: Logger interface for structured logging
        metrics: Metrics interface for performance tracking
        
    Returns:
        Configured PerformanceMonitor instance
        
    Example:
        # Create monitor
        perf_monitor = create_performance_decorator(logger, metrics)
        
        # Use as decorator
        @perf_monitor.time_execution("critical_operation")
        def important_function():
            pass
    """
    return PerformanceMonitor(logger, metrics)


# Convenience decorators for common use cases
def time_database_operation(
    operation_name: Optional[str] = None,
    track_row_count: bool = True
) -> Callable[[F], F]:
    """
    Specialized decorator for database operations.
    
    Args:
        operation_name: Custom operation name
        track_row_count: Whether to extract and log row count from result
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"db_{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Try to extract row count
                row_count = 0
                if track_row_count and hasattr(result, '__len__'):
                    try:
                        row_count = len(result)
                    except (TypeError, AttributeError):
                        pass
                
                # Log database-specific metrics
                print(f"[PERF] {op_name}: {duration:.3f}s ({row_count} rows)")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                print(f"[PERF] {op_name} FAILED: {duration:.3f}s - {str(e)}")
                raise
        
        return wrapper
    return decorator


def time_llm_operation(
    operation_name: Optional[str] = None,
    track_tokens: bool = True
) -> Callable[[F], F]:
    """
    Specialized decorator for LLM API operations.
    
    Args:
        operation_name: Custom operation name
        track_tokens: Whether to track token usage
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"llm_{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Try to extract token count
                token_info = ""
                if track_tokens and hasattr(result, 'usage_metadata'):
                    try:
                        tokens = result.usage_metadata.get('total_tokens', 0)
                        token_info = f" ({tokens} tokens)"
                    except (AttributeError, TypeError):
                        pass
                
                print(f"[PERF] {op_name}: {duration:.3f}s{token_info}")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                print(f"[PERF] {op_name} FAILED: {duration:.3f}s - {str(e)}")
                raise
        
        return wrapper
    return decorator