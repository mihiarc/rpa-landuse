"""
Unit tests for the General Data Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import pandas as pd
import sqlite3
import duckdb
import json
from landuse.agents.general_data_agent import (
    GeneralDataAgent, FileQueryParams, DatabaseQueryParams, 
    DatabaseExportParams, TransformParams
)
from tests.fixtures.agent_fixtures import *


class TestParameterModels:
    """Test parameter validation models"""
    
    def test_file_query_params(self):
        """Test FileQueryParams validation"""
        params = FileQueryParams(
            file_path="data/test.csv",
            query="SELECT * FROM data"
        )
        assert params.file_path == "data/test.csv"
        assert params.query == "SELECT * FROM data"
    
    def test_database_query_params(self):
        """Test DatabaseQueryParams validation"""
        params = DatabaseQueryParams(
            db_path="test.db",
            query="SELECT * FROM users",
            limit=500
        )
        assert params.db_path == "test.db"
        assert params.query == "SELECT * FROM users"
        assert params.limit == 500
        
        # Test default limit
        params2 = DatabaseQueryParams(db_path="test.db", query="SELECT *")
        assert params2.limit == 1000
    
    def test_database_export_params(self):
        """Test DatabaseExportParams validation"""
        params = DatabaseExportParams(
            db_path="test.db",
            table_name="users",
            output_path="export.csv",
            output_format="csv",
            where_clause="age > 18",
            limit=100
        )
        assert params.output_format == "csv"
        assert params.where_clause == "age > 18"
        assert params.limit == 100
    
    def test_transform_params_validation(self):
        """Test TransformParams validation"""
        # Valid format
        params = TransformParams(
            input_path="input.csv",
            output_path="output.parquet",
            output_format="parquet",
            compression="snappy"
        )
        assert params.output_format == "parquet"
        assert params.compression == "snappy"
        
        # Invalid format should raise error
        with pytest.raises(ValueError):
            TransformParams(
                input_path="input.csv",
                output_path="output.txt",
                output_format="invalid"
            )


class TestGeneralDataAgent:
    """Test the main general data agent"""
    
    @pytest.fixture
    @patch('scripts.agents.general_data_agent.ChatOpenAI')
    def agent(self, mock_openai, mock_openai_llm):
        """Create agent instance with mocked dependencies"""
        mock_openai.return_value = mock_openai_llm
        
        with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
            agent = GeneralDataAgent(root_dir="./test_data")
        
        return agent
    
    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        with patch('scripts.agents.general_data_agent.ChatOpenAI') as mock_openai:
            with patch('scripts.agents.general_data_agent.FileManagementToolkit') as mock_toolkit:
                agent = GeneralDataAgent()
                
                assert agent.root_dir == "./data"  # Default from env
                assert agent.llm is not None
                assert agent.tools is not None
                assert agent.agent is not None
    
    def test_agent_initialization_custom_root(self):
        """Test agent with custom root directory"""
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent(root_dir="/custom/path")
                assert agent.root_dir == "/custom/path"
    
    @patch('sqlite3.connect')
    def test_list_database_tables(self, mock_sqlite, agent):
        """Test listing database tables"""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock table list
        mock_cursor.fetchall.return_value = [
            ('users',), ('orders',), ('products',)
        ]
        
        # Mock path operations
        mock_path = Mock()
        mock_path.exists.return_value = True
        
        with patch('pathlib.Path') as path_mock:
            path_mock.return_value.__truediv__.return_value = mock_path
            result = agent._list_database_tables("test.db")
        
        assert "users" in result
        assert "orders" in result
        assert "products" in result
        assert "3 tables" in result.lower()
        mock_conn.close.assert_called_once()
    
    @patch('sqlite3.connect')
    def test_describe_database_table(self, mock_sqlite, agent):
        """Test describing a database table"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock table schema
        mock_cursor.fetchall.side_effect = [
            # PRAGMA table_info
            [(0, 'id', 'INTEGER', 1, None, 1),
             (1, 'name', 'TEXT', 0, None, 0)],
            # Sample data
            [(1, 'John'), (2, 'Jane')]
        ]
        mock_cursor.fetchone.side_effect = [
            ('users',),  # Table exists check
            (2,),        # Row count
        ]
        mock_cursor.fetchall.side_effect.append(
            [(0, 'index1', 0, 'c', 0)]  # Index list
        )
        
        params = {"db_path": "test.db", "table_name": "users"}
        
        with patch('pathlib.Path.exists', return_value=True):
            result = agent._describe_database_table(params)
        
        assert "users" in result
        assert "columns" in result.lower()
        assert "sample data" in result.lower()
        assert "John" in result
    
    @patch('sqlite3.connect')
    def test_database_statistics(self, mock_sqlite, agent):
        """Test getting database statistics"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlite.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock statistics
        mock_cursor.fetchall.return_value = [
            ('users',), ('orders',)
        ]
        mock_cursor.fetchone.side_effect = [
            (100,),  # users count
            (500,)   # orders count
        ]
        
        with patch('os.path.getsize', return_value=1024*1024):  # 1MB
            with patch('pathlib.Path.exists', return_value=True):
                result = agent._database_statistics("test.db")
        
        assert "Database Statistics" in result
        assert "tables" in result.lower()
        assert "size" in result.lower()
        assert "users" in result
        assert "100" in result
    
    @patch('sqlite3.connect')
    def test_query_database(self, mock_sqlite, agent):
        """Test executing database queries"""
        mock_conn = Mock()
        mock_sqlite.return_value = mock_conn
        
        # Mock query results
        mock_df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })
        with patch('pandas.read_sql_query', return_value=mock_df):
            params = {
                "db_path": "test.db",
                "query": "SELECT * FROM users",
                "limit": 10
            }
            result = agent._query_database(params)
        
        assert "3 rows" in result.lower()
        assert "Alice" in result
        mock_conn.close.assert_called_once()
    
    @patch('duckdb.connect')
    def test_query_duckdb(self, mock_duckdb, agent):
        """Test DuckDB query execution"""
        mock_conn = Mock()
        mock_duckdb.return_value = mock_conn
        
        # Mock query results
        mock_df = pd.DataFrame({
            "count": [100]
        })
        mock_conn.execute.return_value.df.return_value = mock_df
        
        params = {
            "db_path": "test.duckdb",
            "query": "SELECT COUNT(*) as count FROM table"
        }
        result = agent._query_duckdb(params)
        
        assert "100" in result
        assert "duckdb" in result.lower()
        mock_conn.close.assert_called_once()
    
    def test_query_data_file_csv(self, agent):
        """Test querying CSV files"""
        mock_df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [25, 30]
        })
        
        with patch('pandas.read_csv', return_value=mock_df):
            with patch('duckdb.query') as mock_query:
                mock_query.return_value.df.return_value = mock_df
                
                params = {
                    "file_path": "test.csv",
                    "query": "SELECT * FROM df WHERE age > 25"
                }
                result = agent._query_data(params)
                
                assert "csv" in result.lower()
                assert "2 rows" in result.lower() or "Bob" in result
    
    def test_query_data_file_json(self, agent):
        """Test querying JSON files"""
        mock_df = pd.DataFrame({
            "id": [1, 2],
            "value": ["a", "b"]
        })
        
        with patch('pandas.read_json', return_value=mock_df):
            with patch('duckdb.query') as mock_query:
                mock_query.return_value.df.return_value = mock_df
                
                params = {
                    "file_path": "test.json",
                    "query": "SELECT * FROM df"
                }
                result = agent._query_data(params)
                
                assert "json" in result.lower()
                assert "success" in result.lower()
    
    def test_query_data_file_parquet(self, agent):
        """Test querying Parquet files"""
        mock_df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["x", "y", "z"]
        })
        
        with patch('pandas.read_parquet', return_value=mock_df):
            with patch('duckdb.query') as mock_query:
                mock_query.return_value.df.return_value = mock_df
                
                params = {
                    "file_path": "test.parquet",
                    "query": "SELECT * FROM df"
                }
                result = agent._query_data(params)
                
                assert "parquet" in result.lower()
                assert "3 rows" in result.lower() or "success" in result.lower()
    
    @patch('sqlite3.connect')
    def test_export_database_table(self, mock_sqlite, agent):
        """Test exporting database table"""
        mock_conn = Mock()
        mock_sqlite.return_value = mock_conn
        
        mock_df = pd.DataFrame({
            "id": [1, 2],
            "name": ["A", "B"]
        })
        
        with patch('pandas.read_sql_query', return_value=mock_df):
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                params = {
                    "db_path": "test.db",
                    "table_name": "users",
                    "output_path": "export.csv",
                    "output_format": "csv"
                }
                result = agent._export_database_table(params)
                
                assert "exported" in result.lower()
                assert "2 rows" in result
                mock_to_csv.assert_called_once()
    
    def test_export_database_table_with_filters(self, agent):
        """Test exporting with WHERE clause and limit"""
        with patch('sqlite3.connect'):
            with patch('pandas.read_sql_query') as mock_read_sql:
                mock_df = pd.DataFrame({"id": [1, 2, 3]})
                mock_read_sql.return_value = mock_df
                
                with patch('pandas.DataFrame.to_csv'):
                    params = {
                        "db_path": "test.db",
                        "table_name": "users",
                        "output_path": "export.csv",
                        "output_format": "csv",
                        "where_clause": "age > 18",
                        "limit": 100
                    }
                    result = agent._export_database_table(params)
                    
                    # Check that WHERE and LIMIT were added to query
                    query = mock_read_sql.call_args[0][0]
                    assert "WHERE age > 18" in query
                    assert "LIMIT 100" in query
    
    def test_analyze_dataframe(self, agent):
        """Test dataframe analysis"""
        mock_df = pd.DataFrame({
            "numeric": [1, 2, 3, 4, 5],
            "category": ["A", "B", "A", "B", "C"],
            "values": [10.5, 20.3, 15.7, 25.1, 30.9]
        })
        
        with patch('pandas.read_csv', return_value=mock_df):
            result = agent._analyze_dataframe("test.csv")
            
            assert "Data Analysis" in result
            assert "shape" in result.lower()
            assert "5 rows" in result
            assert "3 columns" in result
            assert "numeric" in result.lower()
    
    def test_transform_data_csv_to_parquet(self, agent):
        """Test data transformation from CSV to Parquet"""
        mock_df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"]
        })
        
        with patch('pandas.read_csv', return_value=mock_df):
            with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
                params = {
                    "input_path": "input.csv",
                    "output_path": "output.parquet",
                    "output_format": "parquet",
                    "compression": "snappy"
                }
                result = agent._transform_data(params)
                
                assert "success" in result.lower()
                assert "csv" in result.lower()
                assert "parquet" in result.lower()
                mock_to_parquet.assert_called_once()
    
    def test_search_databases(self, agent):
        """Test database search functionality"""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ("./data", [], ["test.db", "data.csv", "analytics.duckdb"]),
                ("./data/archive", [], ["old.db"])
            ]
            
            with patch('os.path.getsize', return_value=1024):
                result = agent._search_databases("")
                
                assert "test.db" in result
                assert "analytics.duckdb" in result
                assert "old.db" in result
                assert "1.0 KB" in result
    
    def test_create_agent_prompt(self, agent):
        """Test agent prompt creation"""
        # The prompt should be part of the agent configuration
        # This is a basic test to ensure the agent has proper setup
        assert agent.agent is not None
        assert hasattr(agent.agent, 'agent')
    
    def test_error_handling_file_not_found(self, agent):
        """Test error handling for missing files"""
        with patch('pandas.read_csv', side_effect=FileNotFoundError("File not found")):
            params = {"file_path": "missing.csv", "query": "SELECT *"}
            result = agent._query_data(params)
            
            assert "error" in result.lower()
            assert "not found" in result.lower()
    
    def test_error_handling_invalid_query(self, agent):
        """Test error handling for invalid SQL queries"""
        with patch('duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.side_effect = Exception("Invalid SQL syntax")
            
            params = {
                "db_path": "test.duckdb",
                "query": "INVALID SQL"
            }
            result = agent._query_duckdb(params)
            
            assert "error" in result.lower()
            assert "Invalid SQL" in result


class TestGeneralDataAgentIntegration:
    """Integration tests for the general data agent"""
    
    @pytest.mark.integration
    def test_sqlite_workflow(self, tmp_path):
        """Test complete SQLite workflow"""
        # Create test database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            [("Alice", 25), ("Bob", 30), ("Charlie", 35)]
        )
        conn.commit()
        conn.close()
        
        # Test agent operations
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent(root_dir=str(tmp_path))
                
                # List tables
                result = agent._list_database_tables(str(db_path))
                assert "users" in result
                
                # Query data
                params = {
                    "db_path": str(db_path),
                    "query": "SELECT * FROM users WHERE age > 25"
                }
                result = agent._query_database(params)
                assert "Bob" in result
                assert "Charlie" in result
                assert "Alice" not in result
    
    @pytest.mark.integration
    def test_csv_to_parquet_workflow(self, tmp_path):
        """Test CSV to Parquet conversion workflow"""
        # Create test CSV
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            "id": range(10),
            "value": [f"val_{i}" for i in range(10)]
        })
        df.to_csv(csv_path, index=False)
        
        # Test transformation
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent()
                
                params = {
                    "input_path": str(csv_path),
                    "output_path": str(tmp_path / "output.parquet"),
                    "output_format": "parquet"
                }
                result = agent._transform_data(params)
                
                assert "success" in result.lower()
                assert Path(tmp_path / "output.parquet").exists()
    
    @pytest.mark.integration
    def test_multi_format_query(self, tmp_path):
        """Test querying different file formats"""
        # Create test files
        test_data = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"]
        })
        
        # CSV
        csv_path = tmp_path / "data.csv"
        test_data.to_csv(csv_path, index=False)
        
        # JSON
        json_path = tmp_path / "data.json"
        test_data.to_json(json_path, orient='records')
        
        # Parquet
        parquet_path = tmp_path / "data.parquet"
        test_data.to_parquet(parquet_path)
        
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent()
                
                # Test each format
                for file_path in [csv_path, json_path, parquet_path]:
                    params = {
                        "file_path": str(file_path),
                        "query": "SELECT * FROM df WHERE id > 1"
                    }
                    result = agent._query_data(params)
                    assert "success" in result.lower() or "2 rows" in result.lower()
    
    @pytest.mark.slow
    def test_large_dataset_handling(self, agent):
        """Test handling of large datasets"""
        # Create large mock dataset
        large_df = pd.DataFrame({
            "id": range(10000),
            "value": [f"value_{i}" for i in range(10000)],
            "category": ["A", "B", "C", "D"] * 2500
        })
        
        with patch('pandas.read_csv', return_value=large_df):
            result = agent._analyze_dataframe("large_data.csv")
            
            assert "10000 rows" in result or "10,000" in result
            assert "memory usage" in result.lower()
            assert "category" in result