#!/usr/bin/env python3
"""
Retry decorators and utilities using tenacity for robust error handling
"""

import functools
import time
from typing import Any, Callable, Optional, Union

from rich.console import Console

try:
    from tenacity import (
        RetryError,
        Retrying,
        after_log,
        before_sleep_log,
        retry,
        retry_if_exception_type,
        retry_if_result,
        stop_after_attempt,
        wait_exponential,
        wait_fixed,
    )

    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False

    # Fallback implementation for environments without tenacity
    class retry_fallback:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, func):
            return func

    retry = retry_fallback

console = Console()


class RetryConfig:
    """Configuration for retry behavior"""

    # Database operations
    DATABASE_RETRY = {
        "stop": "stop_after_attempt(3)",
        "wait": "wait_exponential(multiplier=1, min=1, max=10)",
        "retry": "retry_if_exception_type((ConnectionError, TimeoutError))",
    }

    # API operations
    API_RETRY = {
        "stop": "stop_after_attempt(5)",
        "wait": "wait_exponential(multiplier=2, min=1, max=60)",
        "retry": "retry_if_exception_type((ConnectionError, TimeoutError, OSError))",
    }

    # File operations
    FILE_RETRY = {
        "stop": "stop_after_attempt(3)",
        "wait": "wait_fixed(2)",
        "retry": "retry_if_exception_type((FileNotFoundError, PermissionError, OSError))",
    }

    # Network operations
    NETWORK_RETRY = {
        "stop": "stop_after_attempt(5)",
        "wait": "wait_exponential(multiplier=1, min=2, max=30)",
        "retry": "retry_if_exception_type((ConnectionError, TimeoutError))",
    }

    # LLM operations (Anthropic)
    LLM_RETRY = {
        "stop": "stop_after_attempt(3)",
        "wait": "wait_exponential(multiplier=2, min=1, max=60)",
        "retry": "retry_if_exception_type(LLM_RETRYABLE_EXCEPTIONS)",
    }


def database_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 10.0, exceptions: tuple = None):
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

    logger = logging.getLogger("landuse.retry.database")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


def api_retry(max_attempts: int = 5, base_wait: float = 2.0, max_wait: float = 60.0, exceptions: tuple = None):
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

    logger = logging.getLogger("landuse.retry.api")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, min=1, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


def file_retry(max_attempts: int = 3, wait_time: float = 2.0, exceptions: tuple = None):
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

    logger = logging.getLogger("landuse.retry.file")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_time),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


def network_retry(max_attempts: int = 5, min_wait: float = 2.0, max_wait: float = 30.0, exceptions: tuple = None):
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

    logger = logging.getLogger("landuse.retry.network")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


def _get_llm_retryable_exceptions() -> tuple:
    """Get Anthropic exceptions that should trigger retries.

    Returns:
        Tuple of exception types to retry on
    """
    try:
        import anthropic

        return (
            anthropic.RateLimitError,  # 429 - Rate limit exceeded
            anthropic.APIConnectionError,  # Network connectivity issues
            anthropic.APITimeoutError,  # Request timeout
            anthropic.InternalServerError,  # 500 - Server error
            ConnectionError,
            TimeoutError,
        )
    except ImportError:
        return (ConnectionError, TimeoutError)


def _is_rate_limit_error(exception: Exception) -> bool:
    """Check if exception is a rate limit error requiring longer backoff."""
    try:
        import anthropic

        return isinstance(exception, anthropic.RateLimitError)
    except ImportError:
        return False


def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    rate_limit_wait: float = 30.0,
):
    """
    Retry decorator for LLM/Anthropic API calls with intelligent backoff.

    Handles common LLM API errors including:
    - Rate limits (429) with extended backoff
    - Server errors (500, 502, 503, 504)
    - Connection and timeout errors

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time between retries in seconds (default: 1.0)
        max_wait: Maximum wait time between retries in seconds (default: 60.0)
        rate_limit_wait: Wait time for rate limit errors in seconds (default: 30.0)

    Example:
        >>> @llm_retry(max_attempts=3)
        ... def call_llm(messages):
        ...     return llm.invoke(messages)
    """
    exceptions = _get_llm_retryable_exceptions()

    if not HAS_TENACITY:
        return _fallback_llm_retry(max_attempts, min_wait, rate_limit_wait, exceptions)

    import logging

    logger = logging.getLogger("landuse.retry.llm")

    def custom_wait(retry_state):
        """Custom wait strategy with longer waits for rate limits."""
        exception = retry_state.outcome.exception()
        if _is_rate_limit_error(exception):
            # Rate limit - use longer wait with jitter
            import random

            jitter = random.uniform(0, 5)
            wait_time = rate_limit_wait + jitter
            logger.warning(f"Rate limit hit, waiting {wait_time:.1f}s before retry")
            return wait_time
        else:
            # Standard exponential backoff
            attempt = retry_state.attempt_number
            wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
            return wait_time

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=custom_wait,
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )


def _fallback_llm_retry(max_attempts: int, min_wait: float, rate_limit_wait: float, exceptions: tuple):
    """Fallback LLM retry when tenacity is not available."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import random

            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        # Determine wait time
                        if _is_rate_limit_error(e):
                            wait_time = rate_limit_wait + random.uniform(0, 5)
                            console.print(f"[yellow]⚠ Rate limit hit on attempt {attempt + 1}[/yellow]")
                        else:
                            wait_time = min_wait * (2**attempt)
                            console.print(
                                f"[yellow]⚠ LLM call failed on attempt {attempt + 1}: {type(e).__name__}[/yellow]"
                            )

                        console.print(f"[dim]🔄 Retrying in {wait_time:.1f}s...[/dim]")
                        time.sleep(wait_time)
                    else:
                        console.print(f"[red]❌ All {max_attempts} LLM attempts failed[/red]")

            raise last_exception

        return wrapper

    return decorator


def invoke_llm_with_retry(
    llm,
    messages,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    rate_limit_wait: float = 30.0,
):
    """
    Invoke an LLM with retry logic for transient errors.

    This is a utility function for wrapping LLM invoke calls that cannot
    easily use the @llm_retry decorator (e.g., inline calls).

    Args:
        llm: The LLM instance (or bound LLM with tools)
        messages: Messages to send to the LLM
        max_attempts: Maximum retry attempts (default: 3)
        min_wait: Minimum wait between retries in seconds (default: 1.0)
        rate_limit_wait: Wait time for rate limits in seconds (default: 30.0)

    Returns:
        LLM response

    Raises:
        The last exception if all retries fail

    Example:
        >>> response = invoke_llm_with_retry(
        ...     llm.bind_tools(tools),
        ...     messages,
        ...     max_attempts=3
        ... )
    """
    import random

    exceptions = _get_llm_retryable_exceptions()
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return llm.invoke(messages)
        except exceptions as e:
            last_exception = e

            if attempt < max_attempts - 1:
                # Determine wait time based on error type
                if _is_rate_limit_error(e):
                    wait_time = rate_limit_wait + random.uniform(0, 5)
                    console.print(f"[yellow]⚠ Rate limit hit (attempt {attempt + 1}/{max_attempts})[/yellow]")
                else:
                    wait_time = min_wait * (2**attempt)
                    console.print(
                        f"[yellow]⚠ LLM error (attempt {attempt + 1}/{max_attempts}): {type(e).__name__}[/yellow]"
                    )

                console.print(f"[dim]🔄 Retrying in {wait_time:.1f}s...[/dim]")
                time.sleep(wait_time)
            else:
                console.print(f"[red]❌ LLM call failed after {max_attempts} attempts[/red]")

    raise last_exception


def custom_retry(
    stop_condition=None, wait_strategy=None, retry_condition=None, before_sleep_func=None, after_attempt_func=None
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
        kwargs["stop"] = stop_condition
    if wait_strategy:
        kwargs["wait"] = wait_strategy
    if retry_condition:
        kwargs["retry"] = retry_condition
    if before_sleep_func:
        kwargs["before_sleep"] = before_sleep_func
    if after_attempt_func:
        kwargs["after"] = after_attempt_func

    return retry(**kwargs)


def retry_on_result(result_predicate: Callable[[Any], bool], max_attempts: int = 3, wait_time: float = 1.0):
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

    logger = logging.getLogger("landuse.retry.result")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_time),
        retry=retry_if_result(result_predicate),
        before_sleep=before_sleep_log(logger, logging.INFO),
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
        exceptions: tuple = None,
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
            console.print(
                f"✅ Operation completed successfully in {elapsed_time:.2f}s after {self.attempt_count} attempts"
            )
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
    **kwargs,
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
    with RetryableOperation(operation_name, max_attempts, wait_strategy, min_wait, max_wait, exceptions) as op:
        return op.execute(func, *args, **kwargs)


# Export the main decorators and utilities
__all__ = [
    "database_retry",
    "api_retry",
    "file_retry",
    "network_retry",
    "llm_retry",
    "invoke_llm_with_retry",
    "custom_retry",
    "retry_on_result",
    "RetryableOperation",
    "execute_with_retry",
    "RetryConfig",
    "HAS_TENACITY",
]
