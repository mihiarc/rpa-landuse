"""Unit tests for database connection pool."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from landuse.infrastructure.connection_pool import (
    DatabaseConnectionPool,
    PooledConnection,
    PoolStatistics,
)


class TestPoolStatistics:
    """Test PoolStatistics dataclass."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = PoolStatistics()
        assert stats.total_connections == 0
        assert stats.active_connections == 0
        assert stats.idle_connections == 0
        assert stats.total_acquisitions == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = PoolStatistics(
            total_connections=5,
            active_connections=2,
            idle_connections=3,
            total_acquisitions=100,
            total_releases=98,
            total_wait_time_ms=500.0,
            max_wait_time_ms=50.0,
        )
        result = stats.to_dict()

        assert result["total_connections"] == 5
        assert result["active_connections"] == 2
        assert result["idle_connections"] == 3
        assert result["avg_wait_time_ms"] == 5.0  # 500/100


class TestPooledConnection:
    """Test PooledConnection wrapper."""

    def test_mark_used(self):
        """Test marking connection as used."""
        mock_conn = MagicMock()
        pooled = PooledConnection(connection=mock_conn)

        initial_count = pooled.use_count
        pooled.mark_used()

        assert pooled.use_count == initial_count + 1
        assert pooled.last_used_at > pooled.created_at - 1  # Allow for timing

    def test_is_healthy_success(self):
        """Test health check with working connection."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (1,)
        pooled = PooledConnection(connection=mock_conn)

        assert pooled.is_healthy() is True
        mock_conn.execute.assert_called_with("SELECT 1")

    def test_is_healthy_failure(self):
        """Test health check with broken connection."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Connection lost")
        pooled = PooledConnection(connection=mock_conn)

        assert pooled.is_healthy() is False


class TestDatabaseConnectionPool:
    """Test DatabaseConnectionPool class."""

    @pytest.fixture
    def mock_duckdb(self):
        """Mock duckdb module."""
        with patch("landuse.infrastructure.connection_pool.duckdb") as mock:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = (1,)
            mock.connect.return_value = mock_conn
            yield mock

    def test_pool_initialization(self, mock_duckdb):
        """Test pool initializes with correct parameters."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5, connection_timeout=10, read_only=True)

        assert pool.database_path == "test.db"
        assert pool.max_connections == 5
        assert pool.connection_timeout == 10
        assert pool.read_only is True

        pool.close()

    def test_acquire_connection(self, mock_duckdb):
        """Test acquiring a connection from pool."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        conn = pool.acquire()
        assert conn is not None

        # Check statistics updated
        stats = pool.get_statistics()
        assert stats["total_acquisitions"] >= 1
        assert stats["active_connections"] >= 1

        pool.release(conn)
        pool.close()

    def test_release_connection(self, mock_duckdb):
        """Test releasing a connection back to pool."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        conn = pool.acquire()
        pool.release(conn)

        stats = pool.get_statistics()
        assert stats["total_releases"] >= 1

        pool.close()

    def test_context_manager(self, mock_duckdb):
        """Test using pool connection as context manager."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        with pool.connection() as conn:
            assert conn is not None
            conn.execute("SELECT 1")

        pool.close()

    def test_pool_context_manager(self, mock_duckdb):
        """Test pool itself as context manager."""
        with DatabaseConnectionPool(database_path="test.db", max_connections=5) as pool:
            conn = pool.acquire()
            assert conn is not None
            pool.release(conn)

    def test_is_healthy(self, mock_duckdb):
        """Test pool health check."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        assert pool.is_healthy() is True

        pool.close()

    def test_closed_pool_raises_error(self, mock_duckdb):
        """Test that closed pool raises error on acquire."""
        from landuse.exceptions import DatabaseConnectionError

        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)
        pool.close()

        with pytest.raises(DatabaseConnectionError, match="closed"):
            pool.acquire()

    def test_statistics_tracking(self, mock_duckdb):
        """Test that statistics are properly tracked."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        # Acquire and release several times
        for _ in range(3):
            conn = pool.acquire()
            pool.release(conn)

        stats = pool.get_statistics()
        assert stats["total_acquisitions"] >= 3
        assert stats["total_releases"] >= 3

        pool.close()

    def test_concurrent_access(self, mock_duckdb):
        """Test pool handles concurrent access."""
        pool = DatabaseConnectionPool(database_path="test.db", max_connections=5)

        results = []
        errors = []

        def worker():
            try:
                with pool.connection() as conn:
                    conn.execute("SELECT 1")
                    time.sleep(0.01)  # Simulate work
                results.append(True)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert len(errors) == 0

        pool.close()


class TestDatabaseManagerPooling:
    """Test DatabaseManager with connection pooling."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.database.path = "data/processed/landuse_analytics.duckdb"
        config.database.max_connections = 5
        config.database.connection_timeout = 30
        config.database.read_only = True
        return config

    @patch("landuse.agents.database_manager.DatabaseConnectionPool")
    @patch("landuse.agents.database_manager.SchemaVersionManager")
    def test_pool_initialization(self, mock_version_mgr, mock_pool_cls, mock_config):
        """Test DatabaseManager initializes connection pool."""
        from landuse.agents.database_manager import DatabaseManager

        # Setup mock pool
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_cls.return_value = mock_pool

        db_manager = DatabaseManager(config=mock_config)

        assert db_manager._pool is not None
        mock_pool_cls.assert_called_once()

        db_manager.close()

    @patch("landuse.agents.database_manager.DatabaseConnectionPool")
    @patch("landuse.agents.database_manager.SchemaVersionManager")
    def test_get_pool_statistics(self, mock_version_mgr, mock_pool_cls, mock_config):
        """Test getting pool statistics."""
        from landuse.agents.database_manager import DatabaseManager

        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.get_statistics.return_value = {"total_connections": 5}
        mock_pool_cls.return_value = mock_pool

        db_manager = DatabaseManager(config=mock_config)
        stats = db_manager.get_pool_statistics()

        assert stats is not None
        assert stats["total_connections"] == 5

        db_manager.close()

    @patch("landuse.agents.database_manager.DatabaseConnectionPool")
    @patch("landuse.agents.database_manager.SchemaVersionManager")
    def test_is_pool_healthy(self, mock_version_mgr, mock_pool_cls, mock_config):
        """Test pool health check."""
        from landuse.agents.database_manager import DatabaseManager

        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.is_healthy.return_value = True
        mock_pool_cls.return_value = mock_pool

        db_manager = DatabaseManager(config=mock_config)
        assert db_manager.is_pool_healthy() is True

        db_manager.close()

    @patch("landuse.agents.database_manager.DatabaseConnectionPool")
    @patch("landuse.agents.database_manager.SchemaVersionManager")
    def test_connection_context_manager(self, mock_version_mgr, mock_pool_cls, mock_config):
        """Test connection context manager delegates to pool."""
        from landuse.agents.database_manager import DatabaseManager

        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_cls.return_value = mock_pool

        db_manager = DatabaseManager(config=mock_config)

        with db_manager.connection() as conn:
            assert conn is mock_conn

        db_manager.close()
