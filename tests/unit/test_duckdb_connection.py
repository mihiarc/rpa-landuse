#!/usr/bin/env python3
"""
Unit tests for DuckDBConnection class
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import duckdb
import pandas as pd
import pytest

from landuse.connections.duckdb_connection import DuckDBConnection, ConnectionConfig


class TestDuckDBConnection:
    """Test the DuckDB connection manager"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.duckdb")

            # Create a simple test database
            conn = duckdb.connect(db_path)
            conn.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
            conn.execute("INSERT INTO test_table VALUES (1, 'test1'), (2, 'test2')")
            conn.close()

            yield db_path
            # Cleanup happens automatically when exiting the context

    def test_connect_with_config(self, temp_db_path):
        """Test connection with ConnectionConfig"""
        config = ConnectionConfig(database=temp_db_path, read_only=True)
        connection = DuckDBConnection(config=config)
        connection.connect()

        assert connection._instance is not None
        assert isinstance(connection._instance, duckdb.DuckDBPyConnection)

        # Verify we can query
        result = connection._instance.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        connection.close()

    def test_connect_with_database_path(self, temp_db_path):
        """Test connection with database path parameter"""
        connection = DuckDBConnection(database=temp_db_path, read_only=True)
        connection.connect()

        assert connection._instance is not None
        result = connection._instance.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        connection.close()

    def test_connect_with_env_variable(self, monkeypatch, temp_db_path):
        """Test connection with environment variable fallback"""
        monkeypatch.setenv("LANDUSE_DB_PATH", temp_db_path)

        connection = DuckDBConnection()
        connection.connect()

        assert connection._instance is not None
        result = connection._instance.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        connection.close()

    def test_connect_missing_database(self):
        """Test connection with non-existent database file"""
        from tenacity import RetryError

        connection = DuckDBConnection(database="/nonexistent/path.duckdb")

        # The method has a retry decorator, so it raises RetryError
        with pytest.raises(RetryError):
            connection.connect()

    def test_connect_memory_database(self):
        """Test connection with in-memory database"""
        connection = DuckDBConnection(database=":memory:", read_only=False)
        connection.connect()

        assert connection._instance is not None
        # Create and query a test table
        connection._instance.execute("CREATE TABLE test (id INTEGER)")
        connection._instance.execute("INSERT INTO test VALUES (1), (2), (3)")
        result = connection._instance.execute("SELECT COUNT(*) FROM test").fetchone()
        assert result[0] == 3

        connection.close()

    def test_cursor_method(self, temp_db_path):
        """Test cursor method returns connection itself"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        cursor = connection.cursor()
        assert cursor == connection._instance

        connection.close()

    def test_query_method(self, temp_db_path):
        """Test query method"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        # Test basic query
        df = connection.query("SELECT * FROM test_table", use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]

        connection.close()

    def test_query_with_caching(self, temp_db_path):
        """Test query caching functionality"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        # First query - should cache
        df1 = connection.query("SELECT * FROM test_table", ttl=3600, use_cache=True)

        # Second query - should hit cache
        df2 = connection.query("SELECT * FROM test_table", ttl=3600, use_cache=True)

        assert len(df1) == 2
        assert len(df2) == 2
        # Cache should have one entry
        assert len(connection._query_cache) == 1

        connection.close()

    def test_query_with_parameters(self, temp_db_path):
        """Test query with parameters"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        # Test query with parameters
        df = connection.query("SELECT * FROM test_table WHERE id = $1", use_cache=False, id=1)

        assert len(df) == 1
        assert df.iloc[0]["name"] == "test1"

        connection.close()

    def test_execute_method(self, temp_db_path):
        """Test execute method for DDL/DML statements"""
        connection = DuckDBConnection(database=temp_db_path, read_only=False)
        connection.connect()

        # Test CREATE TABLE
        connection.execute("CREATE TABLE new_table (id INTEGER, value FLOAT)")

        # Test INSERT
        connection.execute("INSERT INTO new_table VALUES (1, 1.5), (2, 2.5)")

        # Verify the changes
        result = connection._instance.execute("SELECT COUNT(*) FROM new_table").fetchone()
        assert result[0] == 2

        connection.close()

    def test_execute_with_parameters(self, temp_db_path):
        """Test execute with parameters"""
        connection = DuckDBConnection(database=temp_db_path, read_only=False)
        connection.connect()

        # Create table
        connection.execute("CREATE TABLE param_test (id INTEGER, name VARCHAR)")

        # Insert with parameters
        connection.execute("INSERT INTO param_test VALUES ($1, $2)", id=1, name="test")

        # Verify
        result = connection._instance.execute("SELECT name FROM param_test WHERE id = 1").fetchone()
        assert result[0] == "test"

        connection.close()

    def test_list_tables(self, temp_db_path):
        """Test list_tables method"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        df = connection.list_tables()

        assert isinstance(df, pd.DataFrame)
        assert "table_name" in df.columns
        assert "test_table" in df["table_name"].values

        connection.close()

    def test_health_check_success(self, temp_db_path):
        """Test health_check when connection is healthy"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        is_healthy = connection.health_check()

        assert is_healthy is True

        connection.close()

    def test_health_check_failure(self):
        """Test health_check when connection fails"""
        connection = DuckDBConnection(database=":memory:", read_only=False)
        # Mock a broken connection
        connection._instance = Mock()
        connection._instance.execute.side_effect = Exception("Connection lost")

        is_healthy = connection.health_check()

        assert is_healthy is False

    def test_read_only_mode(self, temp_db_path):
        """Test read-only mode enforcement"""
        connection = DuckDBConnection(database=temp_db_path, read_only=True)
        connection.connect()

        # Try to create a table in read-only mode
        with pytest.raises(duckdb.InvalidInputException):
            connection._instance.execute("CREATE TABLE should_fail (id INTEGER)")

        connection.close()

    def test_context_manager(self, temp_db_path):
        """Test context manager functionality"""
        with DuckDBConnection(database=temp_db_path) as connection:
            result = connection._instance.execute("SELECT COUNT(*) FROM test_table").fetchone()
            assert result[0] == 2

        # Connection should be closed after context exit
        assert connection._instance is None

    def test_clear_cache(self, temp_db_path):
        """Test cache clearing functionality"""
        connection = DuckDBConnection(database=temp_db_path)
        connection.connect()

        # Start with clean cache
        connection.clear_cache()
        assert len(connection._query_cache) == 0

        # Add something to cache
        connection.query("SELECT * FROM test_table", use_cache=True)
        assert len(connection._query_cache) == 1

        # Clear cache
        connection.clear_cache()
        assert len(connection._query_cache) == 0

        connection.close()

    def test_connection_config_defaults(self):
        """Test ConnectionConfig default values"""
        config = ConnectionConfig()

        assert config.database == "data/processed/landuse_analytics.duckdb"
        assert config.read_only is True
        assert config.memory_limit is None
        assert config.threads is None
