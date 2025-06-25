#!/usr/bin/env python3
"""
Unit tests for retry decorators and utilities
"""

import os
import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from landuse.utils.retry_decorators import (
    HAS_TENACITY,
    RetryableOperation,
    api_retry,
    custom_retry,
    database_retry,
    execute_with_retry,
    file_retry,
    network_retry,
    retry_on_result,
)


class TestRetryDecorators:
    """Test suite for retry decorators"""

    def test_database_retry_success(self):
        """Test database retry on successful operation"""
        call_count = 0

        @database_retry(max_attempts=3, min_wait=0.1, max_wait=1.0)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = mock_db_operation()
        assert result == "success"
        assert call_count == 1

    def test_database_retry_with_failures(self):
        """Test database retry with initial failures"""
        call_count = 0

        @database_retry(max_attempts=3, min_wait=0.1, max_wait=1.0)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Database connection failed")
            return "success"

        result = mock_db_operation()
        assert result == "success"
        assert call_count == 3

    def test_database_retry_exhausted(self):
        """Test database retry when all attempts fail"""
        call_count = 0

        @database_retry(max_attempts=2, min_wait=0.1, max_wait=1.0)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Database connection failed")

        with pytest.raises(ConnectionError):
            mock_db_operation()

        assert call_count == 2

    def test_api_retry_success(self):
        """Test API retry on successful operation"""
        call_count = 0

        @api_retry(max_attempts=3, base_wait=0.1, max_wait=1.0)
        def mock_api_call():
            nonlocal call_count
            call_count += 1
            return {"status": "success"}

        result = mock_api_call()
        assert result == {"status": "success"}
        assert call_count == 1

    def test_file_retry_success(self):
        """Test file retry on successful operation"""
        call_count = 0

        @file_retry(max_attempts=3, wait_time=0.1)
        def mock_file_operation():
            nonlocal call_count
            call_count += 1
            return "file_content"

        result = mock_file_operation()
        assert result == "file_content"
        assert call_count == 1

    def test_network_retry_with_timeouts(self):
        """Test network retry with timeout errors"""
        call_count = 0

        @network_retry(max_attempts=3, min_wait=0.1, max_wait=1.0)
        def mock_network_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Network timeout")
            return "network_response"

        result = mock_network_operation()
        assert result == "network_response"
        assert call_count == 3

    def test_retry_on_result_success(self):
        """Test retry based on result value"""
        call_count = 0

        @retry_on_result(
            result_predicate=lambda x: x is None,
            max_attempts=3,
            wait_time=0.1
        )
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None  # Triggers retry
            return "valid_result"

        result = mock_operation()
        assert result == "valid_result"
        assert call_count == 3

    def test_retry_on_result_exhausted(self):
        """Test retry on result when all attempts return bad result"""
        call_count = 0

        @retry_on_result(
            result_predicate=lambda x: x is None,
            max_attempts=2,
            wait_time=0.1
        )
        def mock_operation():
            nonlocal call_count
            call_count += 1
            return None  # Always triggers retry

        result = mock_operation()
        assert result is None  # Returns last result
        assert call_count == 2

    @pytest.mark.skipif(not HAS_TENACITY, reason="tenacity not available")
    def test_custom_retry_with_tenacity(self):
        """Test custom retry configuration with tenacity"""
        from tenacity import retry_if_exception_type, stop_after_attempt, wait_fixed

        call_count = 0

        @custom_retry(
            stop_condition=stop_after_attempt(3),
            wait_strategy=wait_fixed(0.1),
            retry_condition=retry_if_exception_type(ValueError)
        )
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Custom error")
            return "success"

        result = mock_operation()
        assert result == "success"
        assert call_count == 3

    def test_fallback_retry_without_tenacity(self):
        """Test fallback retry when tenacity is not available"""
        call_count = 0

        # Simulate tenacity not being available
        with patch('landuse.utils.retry_decorators.HAS_TENACITY', False):
            from landuse.utils.retry_decorators import database_retry

            @database_retry(max_attempts=3, min_wait=0.1)
            def mock_operation():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("Test error")
                return "success"

            result = mock_operation()
            assert result == "success"
            assert call_count == 3


class TestRetryableOperation:
    """Test RetryableOperation context manager"""

    def test_retryable_operation_success(self):
        """Test successful operation with RetryableOperation"""
        with RetryableOperation(
            "Test operation",
            max_attempts=3,
            wait_strategy="fixed",
            min_wait=0.1
        ) as op:
            result = op.execute(lambda: "success")
            assert result == "success"
            assert op.attempt_count == 1

    def test_retryable_operation_with_failures(self):
        """Test RetryableOperation with initial failures"""
        call_count = 0

        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Test error")
            return "success"

        with RetryableOperation(
            "Test operation",
            max_attempts=3,
            wait_strategy="fixed",
            min_wait=0.1,
            exceptions=(ConnectionError,)
        ) as op:
            result = op.execute(failing_operation)
            assert result == "success"
            assert op.attempt_count == 3

    def test_retryable_operation_exhausted(self):
        """Test RetryableOperation when all attempts fail"""
        def always_failing_operation():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            with RetryableOperation(
                "Test operation",
                max_attempts=2,
                wait_strategy="fixed",
                min_wait=0.1,
                exceptions=(ConnectionError,)
            ) as op:
                op.execute(always_failing_operation)

    def test_wait_time_calculation(self):
        """Test different wait time calculation strategies"""
        op = RetryableOperation(
            "Test operation",
            max_attempts=5,
            wait_strategy="exponential",
            min_wait=1.0,
            max_wait=10.0
        )

        # Test exponential backoff
        assert op._calculate_wait_time(1) == 1.0
        assert op._calculate_wait_time(2) == 2.0
        assert op._calculate_wait_time(3) == 4.0
        assert op._calculate_wait_time(4) == 8.0
        assert op._calculate_wait_time(5) == 10.0  # Capped at max_wait

        # Test fixed wait
        op.wait_strategy = "fixed"
        assert op._calculate_wait_time(1) == 1.0
        assert op._calculate_wait_time(5) == 1.0

        # Test linear wait
        op.wait_strategy = "linear"
        assert op._calculate_wait_time(1) == 1.0
        assert op._calculate_wait_time(2) == 2.0
        assert op._calculate_wait_time(3) == 3.0
        assert op._calculate_wait_time(15) == 10.0  # Capped at max_wait


class TestExecuteWithRetry:
    """Test execute_with_retry utility function"""

    def test_execute_with_retry_success(self):
        """Test successful execution with retry utility"""
        call_count = 0

        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = execute_with_retry(
            test_function,
            operation_name="Test operation",
            max_attempts=3,
            wait_strategy="fixed",
            min_wait=0.1
        )

        assert result == "success"
        assert call_count == 1

    def test_execute_with_retry_with_args(self):
        """Test execute_with_retry with function arguments"""
        def test_function(x, y, multiplier=1):
            return (x + y) * multiplier

        result = execute_with_retry(
            test_function,
            operation_name="Math operation",
            max_attempts=2,
            wait_strategy="fixed",
            min_wait=0.1,
            x=5,
            y=3,
            multiplier=2
        )

        assert result == 16  # (5 + 3) * 2

    def test_execute_with_retry_failures(self):
        """Test execute_with_retry with initial failures"""
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Test error")
            return "success"

        result = execute_with_retry(
            failing_function,
            operation_name="Failing operation",
            max_attempts=3,
            wait_strategy="fixed",
            min_wait=0.1,
            exceptions=(ConnectionError,)
        )

        assert result == "success"
        assert call_count == 3


class TestErrorHandling:
    """Test error handling in retry decorators"""

    def test_non_retryable_exceptions(self):
        """Test that non-retryable exceptions are not retried"""
        call_count = 0

        @database_retry(max_attempts=3, min_wait=0.1)
        def mock_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")

        with pytest.raises(ValueError):
            mock_operation()

        # Should only be called once since ValueError is not in retryable exceptions
        assert call_count == 1

    def test_mixed_exceptions(self):
        """Test handling of both retryable and non-retryable exceptions"""
        call_count = 0

        @database_retry(max_attempts=3, min_wait=0.1)
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Retryable error")
            elif call_count == 2:
                raise ValueError("Non-retryable error")
            return "success"

        with pytest.raises(ValueError):
            mock_operation()

        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
