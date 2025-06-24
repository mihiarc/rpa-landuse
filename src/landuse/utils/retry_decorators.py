#!/usr/bin/env python3
"""
Retry decorators and utilities using tenacity for robust error handling
"""

import functools
import time
from typing import Type, Union, Callable, Any, Optional, List
from rich.console import Console

try:
    from tenacity import (
        retry, stop_after_attempt, wait_exponential, wait_fixed,
        retry_if_exception_type, retry_if_result, before_sleep_log,
        after_log, RetryError, Retrying
    )
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    # Fallback implementation for environments without tenacity
    class retry:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func

console = Console()


class RetryConfig:
    """Configuration for retry behavior"""
    
    # Database operations
    DATABASE_RETRY = {
        'stop': 'stop_after_attempt(3)',
        'wait': 'wait_exponential(multiplier=1, min=1, max=10)',
        'retry': 'retry_if_exception_type((ConnectionError, TimeoutError))'
    }
    
    # API operations  
    API_RETRY = {
        'stop': 'stop_after_attempt(5)',
        'wait': 'wait_exponential(multiplier=2, min=1, max=60)',
        'retry': 'retry_if_exception_type((ConnectionError, TimeoutError, OSError))'
    }
    
    # File operations
    FILE_RETRY = {
        'stop': 'stop_after_attempt(3)',
        'wait': 'wait_fixed(2)',
        'retry': 'retry_if_exception_type((FileNotFoundError, PermissionError, OSError))'
    }
    
    # Network operations
    NETWORK_RETRY = {
        'stop': 'stop_after_attempt(5)',
        'wait': 'wait_exponential(multiplier=1, min=2, max=30)',
        'retry': 'retry_if_exception_type((ConnectionError, TimeoutError))'
    }


def database_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = None
):
    """
    Retry decorator for database operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    """
    if not HAS_TENACITY:
        return _fallback_retry(max_attempts, min_wait)
    
    if exceptions is None:
        exceptions = (ConnectionError, TimeoutError, OSError)
    
    # Create a standard logger for tenacity (Rich console doesn't work with tenacity logging)
    import logging
    logger = logging.getLogger('landuse.retry.database')
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def api_retry(
    max_attempts: int = 5,
    base_wait: float = 2.0,
    max_wait: float = 60.0,
    exceptions: tuple = None
):
    """
    Retry decorator for API operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_wait: Base wait time multiplier
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    """
    if not HAS_TENACITY:
        return _fallback_retry(max_attempts, base_wait)
    
    if exceptions is None:
        exceptions = (ConnectionError, TimeoutError, OSError)
    
    # Create a standard logger for tenacity
    import logging
    logger = logging.getLogger('landuse.retry.api')
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, min=1, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def file_retry(
    max_attempts: int = 3,
    wait_time: float = 2.0,
    exceptions: tuple = None
):
    """
    Retry decorator for file operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_time: Fixed wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    """
    if not HAS_TENACITY:
        return _fallback_retry(max_attempts, wait_time)
    
    if exceptions is None:
        exceptions = (FileNotFoundError, PermissionError, OSError)
    
    # Create a standard logger for tenacity
    import logging
    logger = logging.getLogger('landuse.retry.file')
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_time),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def network_retry(
    max_attempts: int = 5,
    min_wait: float = 2.0,
    max_wait: float = 30.0,
    exceptions: tuple = None
):
    """
    Retry decorator for network operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    """
    if not HAS_TENACITY:
        return _fallback_retry(max_attempts, min_wait)
    
    if exceptions is None:
        exceptions = (ConnectionError, TimeoutError)
    
    # Create a standard logger for tenacity
    import logging
    logger = logging.getLogger('landuse.retry.network')
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def custom_retry(
    stop_condition=None,
    wait_strategy=None,
    retry_condition=None,
    before_sleep_func=None,
    after_attempt_func=None
):
    """
    Custom retry decorator with full configuration options.
    
    Args:
        stop_condition: When to stop retrying (e.g., stop_after_attempt(3))
        wait_strategy: How long to wait between retries (e.g., wait_exponential())
        retry_condition: Which exceptions/conditions to retry on
        before_sleep_func: Function to call before sleeping
        after_attempt_func: Function to call after each attempt
    """
    if not HAS_TENACITY:
        return _fallback_retry(3, 1.0)
    
    kwargs = {}
    if stop_condition:
        kwargs['stop'] = stop_condition
    if wait_strategy:
        kwargs['wait'] = wait_strategy
    if retry_condition:
        kwargs['retry'] = retry_condition
    if before_sleep_func:
        kwargs['before_sleep'] = before_sleep_func
    if after_attempt_func:
        kwargs['after'] = after_attempt_func
    
    return retry(**kwargs)


def retry_on_result(
    result_predicate: Callable[[Any], bool],
    max_attempts: int = 3,
    wait_time: float = 1.0
):
    """
    Retry decorator that retries based on the result value.
    
    Args:
        result_predicate: Function that returns True if result should trigger retry
        max_attempts: Maximum number of retry attempts
        wait_time: Time to wait between retries (seconds)
    """
    if not HAS_TENACITY:
        return _fallback_retry_result(result_predicate, max_attempts, wait_time)
    
    # Create a standard logger for tenacity
    import logging
    logger = logging.getLogger('landuse.retry.result')
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_time),
        retry=retry_if_result(result_predicate),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )


def _fallback_retry(max_attempts: int, wait_time: float):
    """
    Fallback retry implementation when tenacity is not available.
    
    This provides basic retry functionality without the advanced features
    of tenacity, but ensures the decorators still work.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        console.print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                        console.print(f"🔄 Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        console.print(f"❌ All {max_attempts} attempts failed")
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


def _fallback_retry_result(result_predicate: Callable, max_attempts: int, wait_time: float):
    """Fallback retry implementation for result-based retries"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                result = func(*args, **kwargs)
                
                if not result_predicate(result):
                    return result
                
                if attempt < max_attempts - 1:
                    console.print(f"⚠️ Attempt {attempt + 1} returned unsatisfactory result")
                    console.print(f"🔄 Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            console.print(f"❌ All {max_attempts} attempts returned unsatisfactory results")
            return result  # Return the last result
        
        return wrapper
    return decorator


class RetryableOperation:
    """
    Context manager for retryable operations with detailed logging.
    
    Example:
        with RetryableOperation("Database connection", max_attempts=3) as op:
            result = op.execute(lambda: connect_to_database())
    """
    
    def __init__(
        self, 
        operation_name: str,
        max_attempts: int = 3,
        wait_strategy: str = "exponential",
        min_wait: float = 1.0,
        max_wait: float = 60.0,
        exceptions: tuple = None
    ):
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.wait_strategy = wait_strategy
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.exceptions = exceptions or (Exception,)
        self.attempt_count = 0
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        console.print(f"🚀 Starting retryable operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        if exc_type is None:
            console.print(f"✅ Operation completed successfully in {elapsed_time:.2f}s after {self.attempt_count} attempts")
        else:
            console.print(f"❌ Operation failed after {elapsed_time:.2f}s and {self.attempt_count} attempts")
        return False
    
    def execute(self, func: Callable, *args, **kwargs):
        """Execute a function with retry logic"""
        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            
            try:
                console.print(f"🔄 Attempt {attempt}/{self.max_attempts}: {self.operation_name}")
                result = func(*args, **kwargs)
                console.print(f"✅ Attempt {attempt} succeeded")
                return result
                
            except self.exceptions as e:
                if attempt == self.max_attempts:
                    console.print(f"❌ Final attempt {attempt} failed: {e}")
                    raise
                
                wait_time = self._calculate_wait_time(attempt)
                console.print(f"⚠️ Attempt {attempt} failed: {e}")
                console.print(f"⏳ Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
    
    def _calculate_wait_time(self, attempt: int) -> float:
        """Calculate wait time based on strategy"""
        if self.wait_strategy == "fixed":
            return self.min_wait
        elif self.wait_strategy == "exponential":
            wait = self.min_wait * (2 ** (attempt - 1))
            return min(wait, self.max_wait)
        elif self.wait_strategy == "linear":
            wait = self.min_wait * attempt
            return min(wait, self.max_wait)
        else:
            return self.min_wait


# Convenience function for one-off retryable operations
def execute_with_retry(
    func: Callable,
    operation_name: str = "Operation",
    max_attempts: int = 3,
    wait_strategy: str = "exponential",
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: tuple = None,
    *args,
    **kwargs
):
    """
    Execute a function with retry logic.
    
    Args:
        func: Function to execute
        operation_name: Descriptive name for logging
        max_attempts: Maximum retry attempts
        wait_strategy: "fixed", "exponential", or "linear"
        min_wait: Minimum wait time between retries
        max_wait: Maximum wait time between retries
        exceptions: Tuple of exceptions to retry on
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        Result of successful function execution
        
    Raises:
        Last exception if all attempts fail
    """
    with RetryableOperation(
        operation_name, max_attempts, wait_strategy, 
        min_wait, max_wait, exceptions
    ) as op:
        return op.execute(func, *args, **kwargs)


# Export the main decorators and utilities
__all__ = [
    'database_retry',
    'api_retry', 
    'file_retry',
    'network_retry',
    'custom_retry',
    'retry_on_result',
    'RetryableOperation',
    'execute_with_retry',
    'RetryConfig',
    'HAS_TENACITY'
]