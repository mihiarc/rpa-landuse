#!/usr/bin/env python3
"""
Unit tests for the InMemoryMetrics implementation.

Tests metrics collection functionality including:
- Counter metrics (increment operations)
- Gauge metrics (current value recording)
- Timer metrics (duration recording)
- Tag-based filtering
- Statistics calculation (min, max, mean)
- Thread safety
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from landuse.infrastructure.metrics import (
    InMemoryMetrics,
    MetricsCollector,
    MetricValue,
    TimerContext,
)


class TestMetricValue:
    """Test the MetricValue helper class."""

    def test_metric_value_creation(self):
        """Test creating a metric value with timestamp."""
        mv = MetricValue(value=10.5, tags={"env": "test"})

        assert mv.value == 10.5
        assert mv.tags == {"env": "test"}
        assert mv.timestamp > 0

    def test_metric_value_no_tags(self):
        """Test metric value with no tags defaults to empty dict."""
        mv = MetricValue(value=5.0)

        assert mv.tags == {}


class TestInMemoryMetricsCounters:
    """Test counter metric operations."""

    def test_increment_counter(self):
        """Test incrementing a counter metric."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("requests")
        total = metrics.get_counter_total("requests")

        assert total == 1.0

    def test_increment_counter_multiple_times(self):
        """Test incrementing a counter multiple times."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("requests")
        metrics.increment_counter("requests")
        metrics.increment_counter("requests")
        total = metrics.get_counter_total("requests")

        assert total == 3.0

    def test_increment_counter_with_tags(self):
        """Test counter increments with different tags."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("api_calls", {"endpoint": "/query"})
        metrics.increment_counter("api_calls", {"endpoint": "/query"})
        metrics.increment_counter("api_calls", {"endpoint": "/health"})

        total_all = metrics.get_counter_total("api_calls")
        total_query = metrics.get_counter_total("api_calls", {"endpoint": "/query"})
        total_health = metrics.get_counter_total("api_calls", {"endpoint": "/health"})

        assert total_all == 3.0
        assert total_query == 2.0
        assert total_health == 1.0

    def test_get_counter_nonexistent(self):
        """Test getting nonexistent counter returns 0."""
        metrics = InMemoryMetrics()

        total = metrics.get_counter_total("nonexistent")

        assert total == 0.0


class TestInMemoryMetricsGauges:
    """Test gauge metric operations."""

    def test_record_gauge(self):
        """Test recording a gauge metric."""
        metrics = InMemoryMetrics()

        metrics.record_gauge("connections", 15.0)
        current = metrics.get_gauge_current("connections")

        assert current == 15.0

    def test_record_gauge_updates(self):
        """Test that gauge returns most recent value."""
        metrics = InMemoryMetrics()

        metrics.record_gauge("memory_usage", 100.0)
        metrics.record_gauge("memory_usage", 200.0)
        metrics.record_gauge("memory_usage", 150.0)

        current = metrics.get_gauge_current("memory_usage")

        # Should return most recent value
        assert current == 150.0

    def test_record_gauge_with_tags(self):
        """Test gauge recording with tags."""
        metrics = InMemoryMetrics()

        metrics.record_gauge("cpu", 25.0, {"host": "server1"})
        metrics.record_gauge("cpu", 75.0, {"host": "server2"})

        server1_cpu = metrics.get_gauge_current("cpu", {"host": "server1"})
        server2_cpu = metrics.get_gauge_current("cpu", {"host": "server2"})

        assert server1_cpu == 25.0
        assert server2_cpu == 75.0

    def test_get_gauge_nonexistent(self):
        """Test getting nonexistent gauge returns None."""
        metrics = InMemoryMetrics()

        current = metrics.get_gauge_current("nonexistent")

        assert current is None


class TestInMemoryMetricsTimers:
    """Test timer metric operations."""

    def test_record_timer(self):
        """Test recording a timer metric."""
        metrics = InMemoryMetrics()

        metrics.record_timer("query_duration", 0.5)
        stats = metrics.get_timer_stats("query_duration")

        assert stats["count"] == 1
        assert stats["min"] == 0.5
        assert stats["max"] == 0.5
        assert stats["mean"] == 0.5
        assert stats["total"] == 0.5

    def test_timer_statistics_calculation(self):
        """Test timer statistics are calculated correctly."""
        metrics = InMemoryMetrics()

        # Record various durations
        metrics.record_timer("processing_time", 0.1)
        metrics.record_timer("processing_time", 0.2)
        metrics.record_timer("processing_time", 0.3)
        metrics.record_timer("processing_time", 0.4)

        stats = metrics.get_timer_stats("processing_time")

        assert stats["count"] == 4
        assert stats["min"] == 0.1
        assert stats["max"] == 0.4
        assert abs(stats["mean"] - 0.25) < 0.001  # (0.1 + 0.2 + 0.3 + 0.4) / 4
        assert stats["total"] == 1.0

    def test_timer_with_tags(self):
        """Test timer recording with tags."""
        metrics = InMemoryMetrics()

        metrics.record_timer("api_latency", 0.1, {"method": "GET"})
        metrics.record_timer("api_latency", 0.15, {"method": "GET"})
        metrics.record_timer("api_latency", 0.5, {"method": "POST"})

        get_stats = metrics.get_timer_stats("api_latency", {"method": "GET"})
        post_stats = metrics.get_timer_stats("api_latency", {"method": "POST"})
        all_stats = metrics.get_timer_stats("api_latency")

        assert get_stats["count"] == 2
        assert get_stats["min"] == 0.1
        assert get_stats["max"] == 0.15

        assert post_stats["count"] == 1
        assert post_stats["mean"] == 0.5

        assert all_stats["count"] == 3

    def test_get_timer_stats_nonexistent(self):
        """Test getting nonexistent timer returns empty dict."""
        metrics = InMemoryMetrics()

        stats = metrics.get_timer_stats("nonexistent")

        assert stats == {}


class TestInMemoryMetricsTagFiltering:
    """Test tag-based filtering functionality."""

    def test_filter_by_single_tag(self):
        """Test filtering by a single tag."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("errors", {"severity": "high"})
        metrics.increment_counter("errors", {"severity": "high"})
        metrics.increment_counter("errors", {"severity": "low"})

        high_severity = metrics.get_counter_total("errors", {"severity": "high"})
        low_severity = metrics.get_counter_total("errors", {"severity": "low"})

        assert high_severity == 2.0
        assert low_severity == 1.0

    def test_filter_by_multiple_tags(self):
        """Test filtering by multiple tags."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("requests", {"env": "prod", "region": "us-east"})
        metrics.increment_counter("requests", {"env": "prod", "region": "us-west"})
        metrics.increment_counter("requests", {"env": "staging", "region": "us-east"})

        prod_east = metrics.get_counter_total("requests", {"env": "prod", "region": "us-east"})
        prod_any = metrics.get_counter_total("requests", {"env": "prod"})

        assert prod_east == 1.0
        assert prod_any == 2.0

    def test_filter_no_match(self):
        """Test filtering with no matching tags returns 0 or None."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("events", {"type": "click"})

        result = metrics.get_counter_total("events", {"type": "hover"})

        assert result == 0.0


class TestInMemoryMetricsGetAllMetrics:
    """Test getting all metrics at once."""

    def test_get_all_metrics_empty(self):
        """Test getting all metrics when empty."""
        metrics = InMemoryMetrics()

        all_metrics = metrics.get_all_metrics()

        assert all_metrics["counters"] == {}
        assert all_metrics["gauges"] == {}
        assert all_metrics["timers"] == {}

    def test_get_all_metrics_populated(self):
        """Test getting all metrics with data."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("requests")
        metrics.record_gauge("connections", 10.0)
        metrics.record_timer("latency", 0.5)

        all_metrics = metrics.get_all_metrics()

        assert "requests" in all_metrics["counters"]
        assert all_metrics["counters"]["requests"] == 1.0

        assert "connections" in all_metrics["gauges"]
        assert all_metrics["gauges"]["connections"] == 10.0

        assert "latency" in all_metrics["timers"]
        assert all_metrics["timers"]["latency"]["count"] == 1


class TestInMemoryMetricsClearAndRetention:
    """Test clear and retention functionality."""

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        metrics = InMemoryMetrics()

        metrics.increment_counter("counter1")
        metrics.record_gauge("gauge1", 10.0)
        metrics.record_timer("timer1", 0.5)

        metrics.clear_metrics()

        assert metrics.get_counter_total("counter1") == 0.0
        assert metrics.get_gauge_current("gauge1") is None
        assert metrics.get_timer_stats("timer1") == {}

    def test_retention_period(self):
        """Test that metrics are cleaned up after retention period."""
        # Use very short retention for testing
        metrics = InMemoryMetrics(retention_seconds=0)

        metrics.increment_counter("old_counter")
        time.sleep(0.01)

        # Trigger cleanup by recording new metric
        metrics.increment_counter("new_counter")

        # Old counter should have been cleaned up
        total = metrics.get_counter_total("old_counter")
        assert total == 0.0


class TestInMemoryMetricsThreadSafety:
    """Test thread safety with concurrent access."""

    def test_concurrent_counter_increments(self):
        """Test concurrent counter increments don't lose counts."""
        metrics = InMemoryMetrics()
        num_threads = 10
        increments_per_thread = 100

        def worker():
            for _ in range(increments_per_thread):
                metrics.increment_counter("concurrent_counter")

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total = metrics.get_counter_total("concurrent_counter")
        expected = num_threads * increments_per_thread
        assert total == expected

    def test_concurrent_mixed_operations(self):
        """Test concurrent operations of different types."""
        metrics = InMemoryMetrics()
        errors = []

        def counter_worker():
            try:
                for i in range(50):
                    metrics.increment_counter("test_counter", {"worker": "counter"})
            except Exception as e:
                errors.append(str(e))

        def gauge_worker():
            try:
                for i in range(50):
                    metrics.record_gauge("test_gauge", float(i), {"worker": "gauge"})
            except Exception as e:
                errors.append(str(e))

        def timer_worker():
            try:
                for i in range(50):
                    metrics.record_timer("test_timer", 0.01 * i, {"worker": "timer"})
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=counter_worker),
            threading.Thread(target=gauge_worker),
            threading.Thread(target=timer_worker),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"


class TestTimerContext:
    """Test TimerContext context manager."""

    def test_timer_context_basic(self):
        """Test basic timer context manager usage."""
        metrics = InMemoryMetrics()

        with TimerContext(metrics, "operation"):
            time.sleep(0.05)

        stats = metrics.get_timer_stats("operation")
        assert stats["count"] == 1
        assert stats["mean"] >= 0.04  # Allow some tolerance

    def test_timer_context_with_tags(self):
        """Test timer context manager with tags."""
        metrics = InMemoryMetrics()

        with TimerContext(metrics, "db_query", {"table": "users"}):
            time.sleep(0.01)

        stats = metrics.get_timer_stats("db_query", {"table": "users"})
        assert stats["count"] == 1


class TestMetricsCollector:
    """Test high-level MetricsCollector functionality."""

    def test_record_query_execution(self):
        """Test recording database query metrics."""
        metrics = InMemoryMetrics()
        collector = MetricsCollector(metrics)

        collector.record_query_execution(duration=0.5, row_count=100, success=True)

        timer_stats = metrics.get_timer_stats("database.query.duration")
        assert timer_stats["count"] == 1
        assert timer_stats["mean"] == 0.5

        counter_total = metrics.get_counter_total("database.query.total")
        assert counter_total == 1.0

    def test_record_llm_call(self):
        """Test recording LLM API call metrics."""
        metrics = InMemoryMetrics()
        collector = MetricsCollector(metrics)

        collector.record_llm_call(model="gpt-4o", duration=1.5, token_count=500, success=True)

        timer_stats = metrics.get_timer_stats("llm.call.duration")
        assert timer_stats["count"] == 1

        counter_total = metrics.get_counter_total("llm.call.total")
        assert counter_total == 1.0

    def test_record_agent_query(self):
        """Test recording agent query metrics."""
        metrics = InMemoryMetrics()
        collector = MetricsCollector(metrics)

        collector.record_agent_query(duration=2.5, iterations=3, success=True)

        timer_stats = metrics.get_timer_stats("agent.query.duration")
        assert timer_stats["count"] == 1
        assert timer_stats["mean"] == 2.5

    def test_time_operation_context_manager(self):
        """Test the time_operation context manager."""
        metrics = InMemoryMetrics()
        collector = MetricsCollector(metrics)

        with collector.time_operation("custom_operation", {"type": "test"}):
            time.sleep(0.01)

        stats = metrics.get_timer_stats("custom_operation")
        assert stats["count"] == 1
        assert stats["mean"] >= 0.01
