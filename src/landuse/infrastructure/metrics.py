"""Metrics collection implementation."""

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional

from landuse.core.interfaces import MetricsInterface


class MetricValue:
    """Container for metric values with timestamps."""

    def __init__(self, value: float, tags: Optional[Dict[str, str]] = None):
        """Initialize metric value."""
        self.value = value
        self.tags = tags or {}
        self.timestamp = time.time()


class InMemoryMetrics(MetricsInterface):
    """
    In-memory metrics collection for monitoring application performance.

    Features:
    - Counter metrics (increment only)
    - Gauge metrics (current values)
    - Timer metrics (duration tracking)
    - Tag-based filtering
    - Thread-safe operations
    """

    def __init__(self, retention_seconds: int = 3600):
        """
        Initialize metrics collector.

        Args:
            retention_seconds: How long to keep metrics in memory
        """
        self.retention_seconds = retention_seconds
        self._lock = threading.RLock()

        # Metric storage
        self._counters: Dict[str, List[MetricValue]] = defaultdict(list)
        self._gauges: Dict[str, List[MetricValue]] = defaultdict(list)
        self._timers: Dict[str, List[MetricValue]] = defaultdict(list)

    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name].append(MetricValue(1.0, tags))
            self._cleanup_old_metrics()

    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        with self._lock:
            self._gauges[name].append(MetricValue(value, tags))
            self._cleanup_old_metrics()

    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        with self._lock:
            self._timers[name].append(MetricValue(duration, tags))
            self._cleanup_old_metrics()

    def get_counter_total(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get total value for a counter."""
        with self._lock:
            values = self._counters.get(name, [])
            if tags:
                values = [v for v in values if self._tags_match(v.tags, tags)]
            return sum(v.value for v in values)

    def get_gauge_current(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value for a gauge."""
        with self._lock:
            values = self._gauges.get(name, [])
            if tags:
                values = [v for v in values if self._tags_match(v.tags, tags)]

            if not values:
                return None

            # Return most recent value
            return max(values, key=lambda v: v.timestamp).value

    def get_timer_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get statistics for a timer metric."""
        with self._lock:
            values = self._timers.get(name, [])
            if tags:
                values = [v for v in values if self._tags_match(v.tags, tags)]

            if not values:
                return {}

            durations = [v.value for v in values]
            return {
                'count': len(durations),
                'min': min(durations),
                'max': max(durations),
                'mean': sum(durations) / len(durations),
                'total': sum(durations)
            }

    def get_all_metrics(self) -> Dict[str, Dict[str, any]]:
        """Get all metrics data."""
        with self._lock:
            return {
                'counters': {
                    name: self.get_counter_total(name)
                    for name in self._counters.keys()
                },
                'gauges': {
                    name: self.get_gauge_current(name)
                    for name in self._gauges.keys()
                },
                'timers': {
                    name: self.get_timer_stats(name)
                    for name in self._timers.keys()
                }
            }

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()

    def _tags_match(self, metric_tags: Dict[str, str], filter_tags: Dict[str, str]) -> bool:
        """Check if metric tags match filter tags."""
        for key, value in filter_tags.items():
            if metric_tags.get(key) != value:
                return False
        return True

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = time.time() - self.retention_seconds

        # Clean counters
        for name in list(self._counters.keys()):
            self._counters[name] = [
                v for v in self._counters[name]
                if v.timestamp >= cutoff_time
            ]
            if not self._counters[name]:
                del self._counters[name]

        # Clean gauges
        for name in list(self._gauges.keys()):
            self._gauges[name] = [
                v for v in self._gauges[name]
                if v.timestamp >= cutoff_time
            ]
            if not self._gauges[name]:
                del self._gauges[name]

        # Clean timers
        for name in list(self._timers.keys()):
            self._timers[name] = [
                v for v in self._timers[name]
                if v.timestamp >= cutoff_time
            ]
            if not self._timers[name]:
                del self._timers[name]


class MetricsCollector:
    """High-level metrics collection with common patterns."""

    def __init__(self, metrics: MetricsInterface):
        """Initialize metrics collector."""
        self.metrics = metrics

    def time_operation(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimerContext(self.metrics, operation_name, tags)

    def record_query_execution(self, duration: float, row_count: int, success: bool) -> None:
        """Record database query metrics."""
        tags = {'success': str(success)}
        self.metrics.record_timer('database.query.duration', duration, tags)
        self.metrics.record_gauge('database.query.rows', row_count, tags)
        self.metrics.increment_counter('database.query.total', tags)

    def record_llm_call(self, model: str, duration: float, token_count: int, success: bool) -> None:
        """Record LLM API call metrics."""
        tags = {'model': model, 'success': str(success)}
        self.metrics.record_timer('llm.call.duration', duration, tags)
        self.metrics.record_gauge('llm.call.tokens', token_count, tags)
        self.metrics.increment_counter('llm.call.total', tags)

    def record_agent_query(self, duration: float, iterations: int, success: bool) -> None:
        """Record agent query metrics."""
        tags = {'success': str(success)}
        self.metrics.record_timer('agent.query.duration', duration, tags)
        self.metrics.record_gauge('agent.query.iterations', iterations, tags)
        self.metrics.increment_counter('agent.query.total', tags)


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, metrics: MetricsInterface, name: str, tags: Optional[Dict[str, str]] = None):
        """Initialize timer context."""
        self.metrics = metrics
        self.name = name
        self.tags = tags
        self.start_time: Optional[float] = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.metrics.record_timer(self.name, duration, self.tags)
