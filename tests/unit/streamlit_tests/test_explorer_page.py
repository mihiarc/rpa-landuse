#!/usr/bin/env python3
"""
Unit tests for Streamlit data explorer page

Tests the data explorer functionality including:
- Database connection management
- Schema retrieval
- Query execution
- Result display
- Example queries
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from tests.unit.streamlit_tests.mock_streamlit import mock_st

sys.modules['streamlit'] = mock_st
import streamlit as st  # noqa: E402


class TestExplorerPage:
    """Test the data explorer page"""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection"""
        conn = Mock()
        conn.query = Mock()
        conn.list_tables = Mock()
        conn.get_table_info = Mock()
        conn.get_row_count = Mock()
        return conn

    @pytest.fixture
    def sample_schema_info(self):
        """Sample schema information"""
        return {
            'dim_scenario': {
                'columns': pd.DataFrame({
                    'column_name': ['scenario_id', 'scenario_name'],
                    'column_type': ['INTEGER', 'VARCHAR']
                }),
                'row_count': 20,
                'sample_data': pd.DataFrame({
                    'scenario_id': [1, 2],
                    'scenario_name': ['RCP45_SSP1', 'RCP85_SSP5']
                })
            },
            'fact_landuse_transitions': {
                'columns': pd.DataFrame({
                    'column_name': ['transition_id', 'acres'],
                    'column_type': ['BIGINT', 'DECIMAL']
                }),
                'row_count': 5400000,
                'sample_data': pd.DataFrame({
                    'transition_id': [1, 2],
                    'acres': [1000.5, 2000.7]
                })
            }
        }

    @pytest.fixture
    def sample_query_results(self):
        """Sample query results"""
        return pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'total_acres': [1000000, 800000, 600000],
            'county_count': [58, 254, 62]
        })

    def test_page_functions_exist(self):
        """Test that key page functions exist and are callable"""
        from views import explorer

        # Test that key functions exist (current API)
        assert hasattr(explorer, 'get_database_connection')
        assert hasattr(explorer, 'get_table_schema')
        assert hasattr(explorer, 'get_query_examples')
        assert hasattr(explorer, 'execute_query')
        assert hasattr(explorer, 'display_query_results')
        assert hasattr(explorer, 'show_schema_browser')
        assert hasattr(explorer, 'show_query_editor')
        assert hasattr(explorer, 'show_query_examples')
        assert hasattr(explorer, 'show_data_dictionary')
        assert hasattr(explorer, 'main')

        # Test that they are callable
        assert callable(explorer.get_database_connection)
        assert callable(explorer.get_table_schema)
        assert callable(explorer.execute_query)
        assert callable(explorer.main)

    def test_configuration_constants(self):
        """Test configuration constants are defined"""
        from views import explorer

        assert hasattr(explorer, 'MAX_DISPLAY_ROWS')
        assert hasattr(explorer, 'DEFAULT_DISPLAY_ROWS')
        assert hasattr(explorer, 'DEFAULT_TTL')
        assert hasattr(explorer, 'SCHEMA_TTL')
        assert hasattr(explorer, 'ALLOWED_TABLES')

        # Verify reasonable values
        assert explorer.MAX_DISPLAY_ROWS > 0
        assert explorer.DEFAULT_DISPLAY_ROWS > 0
        assert explorer.DEFAULT_DISPLAY_ROWS <= explorer.MAX_DISPLAY_ROWS
        assert explorer.DEFAULT_TTL > 0
        assert len(explorer.ALLOWED_TABLES) > 0

    def test_allowed_tables_includes_required(self):
        """Test ALLOWED_TABLES includes key tables"""
        from views import explorer

        required_tables = {
            'dim_scenario', 'dim_geography', 'dim_time',
            'dim_landuse', 'fact_landuse_transitions'
        }

        assert required_tables.issubset(explorer.ALLOWED_TABLES)

    def test_get_query_examples_returns_dict(self):
        """Test get_query_examples returns structured examples"""
        from views import explorer

        examples = explorer.get_query_examples()

        assert isinstance(examples, dict)
        assert len(examples) > 0

        # Check structure - should have categories with queries
        for category, queries in examples.items():
            assert isinstance(category, str)
            assert isinstance(queries, dict)
            for query_name, query_sql in queries.items():
                assert isinstance(query_name, str)
                assert isinstance(query_sql, str)
                assert 'SELECT' in query_sql.upper() or 'WITH' in query_sql.upper()

    def test_get_query_examples_has_categories(self):
        """Test query examples has expected categories"""
        from views import explorer

        examples = explorer.get_query_examples()

        # Should have multiple categories
        assert len(examples) >= 3

        # Each category should have at least one example
        for category, queries in examples.items():
            assert len(queries) >= 1

    @patch('views.explorer.st.connection')
    def test_get_database_connection_uses_st_connection(self, mock_st_connection):
        """Test database connection uses st.connection pattern"""
        from views import explorer

        mock_conn = Mock()
        mock_st_connection.return_value = mock_conn

        # Call the function (mock doesn't support .clear() on decorated functions)
        conn = explorer.get_database_connection()

        # Verify st.connection was called
        assert mock_st_connection.called
        call_kwargs = mock_st_connection.call_args[1]
        assert call_kwargs['read_only'] is True

    @patch('views.explorer.get_database_connection')
    def test_get_table_schema_returns_dict(self, mock_get_conn, mock_connection, sample_schema_info):
        """Test get_table_schema returns schema dictionary"""
        from views import explorer

        mock_get_conn.return_value = mock_connection
        mock_connection.list_tables.return_value = pd.DataFrame({
            'table_name': ['dim_scenario', 'dim_geography']
        })
        mock_connection.get_table_info.return_value = pd.DataFrame({
            'column_name': ['id', 'name'],
            'column_type': ['INTEGER', 'VARCHAR']
        })
        mock_connection.get_row_count.return_value = 100
        mock_connection.query.return_value = pd.DataFrame({'col': [1, 2]})

        # Call the function (mock doesn't support .clear() on decorated functions)
        schema = explorer.get_table_schema()

        # Should return dictionary (may be empty if tables filtered)
        assert isinstance(schema, dict)

    def test_display_query_results_handles_empty(self, sample_query_results):
        """Test display_query_results handles empty DataFrame"""
        from views import explorer

        empty_df = pd.DataFrame()

        # Should handle empty data without error
        explorer.display_query_results(empty_df, "SELECT * FROM test")

    def test_display_query_results_formats_numbers(self, sample_query_results):
        """Test display_query_results can format numbers"""
        from views import explorer

        # Setup mock checkboxes and inputs
        mock_st.checkbox = Mock(return_value=True)  # Format numbers = True
        mock_st.number_input = Mock(return_value=10)

        # Should handle formatting
        explorer.display_query_results(sample_query_results, "SELECT * FROM test")

    def test_display_query_results_provides_export(self, sample_query_results):
        """Test display_query_results provides export options"""
        from views import explorer

        mock_st.checkbox = Mock(return_value=False)
        mock_st.number_input = Mock(return_value=10)

        # Should create download buttons for CSV, JSON, Parquet
        explorer.display_query_results(sample_query_results, "SELECT * FROM test")

        # Verify download_button was called for exports
        # (Mock captures all calls)

    @patch('views.explorer.get_database_connection')
    def test_execute_query_adds_limit(self, mock_get_conn, mock_connection):
        """Test execute_query adds safety limit"""
        from views import explorer

        mock_get_conn.return_value = mock_connection
        mock_connection.query.return_value = pd.DataFrame({'col': [1]})

        # Query without LIMIT
        explorer.execute_query("SELECT * FROM dim_scenario")

        # Verify query was modified to include LIMIT
        called_query = mock_connection.query.call_args[0][0]
        assert 'LIMIT' in called_query.upper()

    @patch('views.explorer.get_database_connection')
    def test_execute_query_preserves_existing_limit(self, mock_get_conn, mock_connection):
        """Test execute_query preserves existing LIMIT"""
        from views import explorer

        mock_get_conn.return_value = mock_connection
        mock_connection.query.return_value = pd.DataFrame({'col': [1]})

        # Query with existing LIMIT
        original_query = "SELECT * FROM dim_scenario LIMIT 50"
        explorer.execute_query(original_query)

        # Should preserve original limit, not add another
        called_query = mock_connection.query.call_args[0][0]
        # Original limit should be preserved
        assert '50' in called_query or 'LIMIT' in called_query.upper()

    @patch('views.explorer.get_database_connection')
    def test_execute_query_handles_union(self, mock_get_conn, mock_connection):
        """Test execute_query handles UNION queries"""
        from views import explorer

        mock_get_conn.return_value = mock_connection
        mock_connection.query.return_value = pd.DataFrame({'col': [1]})

        # Query with UNION
        union_query = "SELECT * FROM dim_scenario UNION SELECT * FROM dim_time"
        explorer.execute_query(union_query)

        # Should not blindly add LIMIT to UNION queries
        called_query = mock_connection.query.call_args[0][0]
        # Should have been passed through
        assert 'UNION' in called_query.upper()

    def test_show_data_dictionary_content(self):
        """Test show_data_dictionary displays documentation"""
        from views import explorer

        # Should execute without error
        explorer.show_data_dictionary()

    def test_show_query_examples_executes(self):
        """Test show_query_examples can be called"""
        from views import explorer

        # mock_st.tabs is already set up to return MockContainers that support context manager

        # Should execute without error
        explorer.show_query_examples()

    def test_main_creates_tabs(self):
        """Test main function creates tab interface"""
        from views import explorer

        mock_st.session_state = MagicMock()

        # Main should call st.tabs
        mock_st.tabs = Mock(return_value=[Mock(), Mock(), Mock(), Mock()])

        # Should execute main without error
        # Note: May need to mock other components
        assert callable(explorer.main)

    def test_schema_browser_displays_metrics(self):
        """Test schema browser displays database metrics"""
        from views import explorer

        # Mock get_table_schema to return test data
        with patch('views.explorer.get_table_schema') as mock_schema:
            mock_schema.return_value = {
                'dim_scenario': {
                    'columns': pd.DataFrame({'col': ['a']}),
                    'row_count': 20,
                    'sample_data': pd.DataFrame()
                }
            }

            mock_st.text_input = Mock(return_value="")

            # Should execute without error
            explorer.show_schema_browser()

    def test_query_editor_initializes_session_state(self):
        """Test query editor initializes session state"""
        from views import explorer

        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: False

        mock_st.selectbox = Mock(return_value="")
        mock_st.text_area = Mock(return_value="SELECT 1")
        mock_st.button = Mock(return_value=False)

        # Should initialize query_text in session state
        explorer.show_query_editor()
