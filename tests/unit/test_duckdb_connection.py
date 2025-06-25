#!/usr/bin/env python3
"""
Unit tests for DuckDBConnection class
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import duckdb
import pandas as pd
import pytest

from landuse.connections.duckdb_connection import DuckDBConnection


class TestDuckDBConnection:
    """Test the custom DuckDB connection for Streamlit"""

    @pytest.fixture
    def mock_secrets(self):
        """Mock Streamlit secrets"""
        mock = MagicMock()
        mock.database = ":memory:"
        return mock

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

    def test_connect_with_kwargs(self, temp_db_path):
        """Test connection with database path in kwargs"""
        connection = DuckDBConnection(connection_name="test")

        # Mock the connection
        db_conn = connection._connect(database=temp_db_path, read_only=True)

        assert db_conn is not None
        assert isinstance(db_conn, duckdb.DuckDBPyConnection)

        # Verify we can query
        result = db_conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        db_conn.close()

    def test_connect_with_secrets(self, mock_secrets, temp_db_path):
        """Test connection with database path in secrets"""
        mock_secrets.database = temp_db_path
        mock_secrets.__getitem__ = lambda self, key: temp_db_path if key == 'database' else None

        connection = DuckDBConnection(connection_name="test")
        connection._secrets = mock_secrets

        db_conn = connection._connect()

        assert db_conn is not None
        result = db_conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        db_conn.close()

    def test_connect_with_env_variable(self, monkeypatch, temp_db_path):
        """Test connection with environment variable fallback"""
        monkeypatch.setenv("LANDUSE_DB_PATH", temp_db_path)

        connection = DuckDBConnection(connection_name="test")
        # Create a mock that doesn't have database attribute
        mock_secrets = Mock(spec=[])  # Empty spec means no attributes
        connection._secrets = mock_secrets

        db_conn = connection._connect()

        assert db_conn is not None
        result = db_conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

        db_conn.close()

    def test_connect_missing_database(self):
        """Test connection with non-existent database file"""
        connection = DuckDBConnection(connection_name="test")

        with pytest.raises(FileNotFoundError, match="Database file not found"):
            connection._connect(database="/nonexistent/path.duckdb")

    def test_connect_memory_database(self):
        """Test connection with in-memory database"""
        connection = DuckDBConnection(connection_name="test")

        # In-memory databases cannot be opened in read-only mode
        db_conn = connection._connect(database=":memory:", read_only=False)

        assert db_conn is not None
        # Create and query a test table
        db_conn.execute("CREATE TABLE test (id INTEGER)")
        db_conn.execute("INSERT INTO test VALUES (1), (2), (3)")
        result = db_conn.execute("SELECT COUNT(*) FROM test").fetchone()
        assert result[0] == 3

        db_conn.close()

    def test_cursor_method(self, temp_db_path):
        """Test cursor method returns connection itself"""
        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        cursor = connection.cursor()
        assert cursor == connection._instance

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_query_method(self, mock_cache_data, temp_db_path):
        """Test query method with caching"""
        # Mock the cache decorator to just return the function
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        # Test basic query
        df = connection.query("SELECT * FROM test_table")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['id', 'name']

        # Verify cache decorator was called with correct TTL
        mock_cache_data.assert_called_with(ttl=3600)

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_query_with_parameters(self, mock_cache_data, temp_db_path):
        """Test query with parameters"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        # Test query with parameters
        df = connection.query(
            "SELECT * FROM test_table WHERE id = $1",
            id=1
        )

        assert len(df) == 1
        assert df.iloc[0]['name'] == 'test1'

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_query_custom_ttl(self, mock_cache_data, temp_db_path):
        """Test query with custom TTL"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        # Test with custom TTL
        df = connection.query("SELECT * FROM test_table", ttl=300)

        assert len(df) == 2
        mock_cache_data.assert_called_with(ttl=300)

        connection._instance.close()

    def test_execute_method(self, temp_db_path):
        """Test execute method for DDL/DML statements"""
        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path, read_only=False)

        # Test CREATE TABLE
        connection.execute("CREATE TABLE new_table (id INTEGER, value FLOAT)")

        # Test INSERT
        connection.execute("INSERT INTO new_table VALUES (1, 1.5), (2, 2.5)")

        # Verify the changes
        result = connection._instance.execute("SELECT COUNT(*) FROM new_table").fetchone()
        assert result[0] == 2

        connection._instance.close()

    def test_execute_with_parameters(self, temp_db_path):
        """Test execute with parameters"""
        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path, read_only=False)

        # Create table
        connection.execute("CREATE TABLE param_test (id INTEGER, name VARCHAR)")

        # Insert with parameters
        connection.execute(
            "INSERT INTO param_test VALUES ($1, $2)",
            id=1, name="test"
        )

        # Verify
        result = connection._instance.execute("SELECT name FROM param_test WHERE id = 1").fetchone()
        assert result[0] == "test"

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_get_table_info(self, mock_cache_data, temp_db_path):
        """Test get_table_info method"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        df = connection.get_table_info("test_table")

        assert isinstance(df, pd.DataFrame)
        assert 'column_name' in df.columns
        assert 'column_type' in df.columns
        assert len(df) == 2  # id and name columns

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_list_tables(self, mock_cache_data, temp_db_path):
        """Test list_tables method"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        df = connection.list_tables()

        assert isinstance(df, pd.DataFrame)
        assert 'table_name' in df.columns
        assert 'test_table' in df['table_name'].values

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_get_row_count(self, mock_cache_data, temp_db_path):
        """Test get_row_count method"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        count = connection.get_row_count("test_table")

        assert count == 2
        mock_cache_data.assert_called_with(ttl=300)

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_health_check_success(self, mock_cache_data, temp_db_path):
        """Test health_check when connection is healthy"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path)

        is_healthy = connection.health_check()

        assert is_healthy is True

        connection._instance.close()

    @patch('landuse.connections.duckdb_connection.cache_data')
    def test_health_check_failure(self, mock_cache_data):
        """Test health_check when connection fails"""
        mock_cache_data.return_value = lambda func: func

        connection = DuckDBConnection(connection_name="test")
        # Mock a broken connection
        connection._instance = Mock()
        connection._instance.execute.side_effect = Exception("Connection lost")

        is_healthy = connection.health_check()

        assert is_healthy is False

    def test_read_only_mode(self, temp_db_path):
        """Test read-only mode enforcement"""
        connection = DuckDBConnection(connection_name="test")
        connection._instance = connection._connect(database=temp_db_path, read_only=True)

        # Try to create a table in read-only mode
        with pytest.raises(duckdb.CatalogException):
            connection._instance.execute("CREATE TABLE should_fail (id INTEGER)")

        connection._instance.close()

    def test_connection_kwargs_passthrough(self):
        """Test that additional kwargs are passed to duckdb.connect"""
        connection = DuckDBConnection(connection_name="test")

        # Test with additional config
        db_conn = connection._connect(
            database=":memory:",
            read_only=False,  # In-memory databases cannot be read-only
            config={'threads': 4, 'memory_limit': '1GB'}
        )

        assert db_conn is not None
        # Note: We can't easily verify the config was applied, but we can verify
        # the connection works
        result = db_conn.execute("SELECT 1").fetchone()
        assert result[0] == 1

        db_conn.close()
