"""Thread-safe database connection pool for DuckDB.

Provides a pool of reusable database connections with:
- Configurable pool size and connection timeout
- Thread-safe connection acquisition and release
- Automatic connection health checking
- Context manager support for safe resource handling
- Statistics and monitoring capabilities
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Optional

import duckdb
from rich.console import Console

from landuse.exceptions import DatabaseConnectionError, DatabaseError


@dataclass
class PoolStatistics:
    """Statistics for connection pool monitoring."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_acquisitions: int = 0
    total_releases: int = 0
    failed_acquisitions: int = 0
    total_wait_time_ms: float = 0.0
    max_wait_time_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert statistics to dictionary."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "total_acquisitions": self.total_acquisitions,
            "total_releases": self.total_releases,
            "failed_acquisitions": self.failed_acquisitions,
            "avg_wait_time_ms": (
                self.total_wait_time_ms / self.total_acquisitions
                if self.total_acquisitions > 0
                else 0.0
            ),
            "max_wait_time_ms": self.max_wait_time_ms,
        }


@dataclass
class PooledConnection:
    """Wrapper for a pooled database connection."""

    connection: duckdb.DuckDBPyConnection
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0

    def is_healthy(self) -> bool:
        """Check if connection is still valid."""
        try:
            self.connection.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def mark_used(self) -> None:
        """Update usage statistics."""
        self.last_used_at = time.time()
        self.use_count += 1


class DatabaseConnectionPool:
    """Thread-safe connection pool for DuckDB databases.

    Manages a pool of reusable database connections with configurable
    size limits, timeouts, and health checking.

    Example:
        >>> pool = DatabaseConnectionPool(
        ...     database_path="data/landuse.duckdb",
        ...     max_connections=10,
        ...     read_only=True
        ... )
        >>> with pool.acquire() as conn:
        ...     result = conn.execute("SELECT * FROM table").fetchall()
        >>> pool.close()

    Attributes:
        database_path: Path to the DuckDB database file
        max_connections: Maximum number of connections in the pool
        connection_timeout: Timeout for acquiring connections in seconds
        read_only: Whether to open connections in read-only mode
    """

    def __init__(
        self,
        database_path: str,
        max_connections: int = 10,
        connection_timeout: int = 30,
        read_only: bool = True,
        console: Optional[Console] = None,
    ):
        """Initialize the connection pool.

        Args:
            database_path: Path to DuckDB database file
            max_connections: Maximum pool size (default: 10)
            connection_timeout: Seconds to wait for connection (default: 30)
            read_only: Open connections in read-only mode (default: True)
            console: Rich console for logging (optional)
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.read_only = read_only
        self.console = console or Console()

        # Thread-safe pool storage
        self._pool: Queue[PooledConnection] = Queue(maxsize=max_connections)
        self._lock = threading.RLock()
        self._closed = False

        # Statistics tracking
        self._stats = PoolStatistics()
        self._active_connections: set[int] = set()

        # Pre-create minimum connections
        self._initialize_pool()

    def _initialize_pool(self, min_connections: int = 1) -> None:
        """Pre-create minimum number of connections.

        Args:
            min_connections: Minimum connections to create (default: 1)
        """
        for _ in range(min(min_connections, self.max_connections)):
            try:
                pooled_conn = self._create_connection()
                self._pool.put_nowait(pooled_conn)
            except Exception as e:
                self.console.print(f"[yellow]⚠ Failed to pre-create connection: {e}[/yellow]")

    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection.

        Returns:
            PooledConnection: New connection wrapper

        Raises:
            DatabaseConnectionError: If connection creation fails
        """
        try:
            conn = duckdb.connect(
                database=self.database_path,
                read_only=self.read_only
            )
            pooled = PooledConnection(connection=conn)

            with self._lock:
                self._stats.total_connections += 1

            return pooled

        except duckdb.Error as e:
            raise DatabaseConnectionError(
                f"Failed to create DuckDB connection: {e}",
                host=self.database_path
            )
        except Exception as e:
            raise DatabaseConnectionError(
                f"Unexpected error creating connection: {type(e).__name__}: {e}",
                host=self.database_path
            )

    def acquire(self, timeout: Optional[float] = None) -> duckdb.DuckDBPyConnection:
        """Acquire a connection from the pool.

        Args:
            timeout: Override default timeout (seconds)

        Returns:
            DuckDB connection instance

        Raises:
            DatabaseConnectionError: If pool is closed or timeout exceeded
            DatabaseError: If no healthy connection available
        """
        if self._closed:
            raise DatabaseConnectionError("Connection pool is closed")

        timeout = timeout if timeout is not None else self.connection_timeout
        start_time = time.time()

        # First, try to create a new connection if under limit and pool is empty
        with self._lock:
            if self._pool.empty() and self._stats.total_connections < self.max_connections:
                try:
                    pooled_conn = self._create_connection()
                    pooled_conn.mark_used()

                    self._stats.total_acquisitions += 1
                    self._stats.active_connections += 1
                    wait_time = (time.time() - start_time) * 1000
                    self._stats.total_wait_time_ms += wait_time

                    return pooled_conn.connection
                except Exception as e:
                    self._stats.failed_acquisitions += 1
                    # Fall through to try getting from pool
                    pass

        try:
            # Try to get an existing connection from pool
            pooled_conn = self._pool.get(timeout=timeout)
            wait_time = (time.time() - start_time) * 1000

            # Update statistics
            with self._lock:
                self._stats.total_acquisitions += 1
                self._stats.total_wait_time_ms += wait_time
                self._stats.max_wait_time_ms = max(self._stats.max_wait_time_ms, wait_time)
                self._stats.active_connections += 1
                self._stats.idle_connections = self._pool.qsize()

            # Check connection health
            if not pooled_conn.is_healthy():
                # Connection is stale, create new one
                with self._lock:
                    self._stats.total_connections -= 1  # Old connection is dead

                try:
                    pooled_conn.connection.close()
                except Exception:
                    pass  # Ignore close errors for stale connections

                pooled_conn = self._create_connection()

            pooled_conn.mark_used()
            return pooled_conn.connection

        except Empty:
            # Queue is empty, try to create new connection if under limit
            with self._lock:
                if self._stats.total_connections < self.max_connections:
                    try:
                        pooled_conn = self._create_connection()
                        pooled_conn.mark_used()

                        self._stats.total_acquisitions += 1
                        self._stats.active_connections += 1

                        return pooled_conn.connection
                    except Exception:
                        self._stats.failed_acquisitions += 1
                        raise

                self._stats.failed_acquisitions += 1

            raise DatabaseConnectionError(
                f"Connection pool exhausted (max: {self.max_connections}, "
                f"timeout: {timeout}s)"
            )

    def release(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        if self._closed:
            # Pool is closed, just close the connection
            try:
                connection.close()
            except Exception:
                pass
            return

        # Create pooled wrapper for the connection
        pooled_conn = PooledConnection(connection=connection)

        with self._lock:
            self._stats.total_releases += 1
            self._stats.active_connections = max(0, self._stats.active_connections - 1)

        try:
            self._pool.put_nowait(pooled_conn)
            with self._lock:
                self._stats.idle_connections = self._pool.qsize()
        except Exception:
            # Pool is full, close the connection
            try:
                connection.close()
            except Exception:
                pass

    @contextmanager
    def connection(self, timeout: Optional[float] = None):
        """Context manager for acquiring and releasing connections.

        Args:
            timeout: Override default timeout (seconds)

        Yields:
            DuckDB connection instance

        Example:
            >>> with pool.connection() as conn:
            ...     conn.execute("SELECT * FROM table")
        """
        conn = self.acquire(timeout=timeout)
        try:
            yield conn
        finally:
            self.release(conn)

    def get_statistics(self) -> dict:
        """Get current pool statistics.

        Returns:
            Dictionary of pool statistics
        """
        with self._lock:
            return self._stats.to_dict()

    def is_healthy(self) -> bool:
        """Check if pool is healthy and operational.

        Returns:
            True if pool can provide connections
        """
        if self._closed:
            return False

        try:
            with self.connection(timeout=5) as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close all connections and shut down the pool."""
        with self._lock:
            self._closed = True

        # Drain and close all pooled connections
        while not self._pool.empty():
            try:
                pooled_conn = self._pool.get_nowait()
                try:
                    pooled_conn.connection.close()
                except Exception:
                    pass
            except Empty:
                break

        self.console.print("[dim]Connection pool closed[/dim]")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close pool."""
        self.close()

    def __del__(self):
        """Destructor - ensure connections are closed."""
        if not self._closed:
            self.close()
