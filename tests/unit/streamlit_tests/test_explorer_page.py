#!/usr/bin/env python3
"""
Unit tests for Streamlit data explorer page
"""

# Mock streamlit before importing pages
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

    @patch('pages.explorer.st.connection')
    def test_get_database_connection(self, mock_st_connection):
        """Test database connection with caching"""
        mock_conn = Mock()
        mock_st_connection.return_value = mock_conn

        from pages.explorer import get_database_connection

        conn, error = get_database_connection()

        assert conn == mock_conn
        assert error is None

        # Verify connection parameters
        call_kwargs = mock_st_connection.call_args[1]
        assert call_kwargs['name'] == 'landuse_db_explorer'
        assert call_kwargs['read_only'] is True

    @patch('pages.explorer.get_database_connection')
    def test_get_table_schema(self, mock_get_conn, mock_connection):
        """Test retrieving table schema"""
        mock_get_conn.return_value = (mock_connection, None)

        # Mock table list
        mock_connection.list_tables.return_value = pd.DataFrame({
            'table_name': ['dim_scenario', 'fact_landuse_transitions']
        })

        # Mock table info
        mock_connection.get_table_info.side_effect = [
            pd.DataFrame({
                'column_name': ['scenario_id', 'scenario_name'],
                'column_type': ['INTEGER', 'VARCHAR']
            }),
            pd.DataFrame({
                'column_name': ['transition_id', 'acres'],
                'column_type': ['BIGINT', 'DECIMAL']
            })
        ]

        # Mock row counts
        mock_connection.get_row_count.side_effect = [20, 5400000]

        # Mock sample data
        mock_connection.query.side_effect = [
            pd.DataFrame({'scenario_id': [1, 2], 'scenario_name': ['A', 'B']}),
            pd.DataFrame({'transition_id': [1, 2], 'acres': [100, 200]})
        ]

        from pages.explorer import get_table_schema

        schema_info, error = get_table_schema()

        assert error is None
        assert 'dim_scenario' in schema_info
        assert 'fact_landuse_transitions' in schema_info
        assert schema_info['dim_scenario']['row_count'] == 20

    def test_get_query_examples(self):
        """Test query examples retrieval"""
        from pages.explorer import get_query_examples

        examples = get_query_examples()

        assert isinstance(examples, dict)
        assert 'Basic Queries' in examples
        assert 'Agricultural Analysis' in examples
        assert 'Climate Analysis' in examples

        # Verify example structure
        basic_queries = examples['Basic Queries']
        assert isinstance(basic_queries, dict)
        assert len(basic_queries) > 0

        # Check that queries are strings
        for category in examples.values():
            for query in category.values():
                assert isinstance(query, str)
                assert 'SELECT' in query.upper()

    @patch('pages.explorer.get_database_connection')
    def test_execute_custom_query_success(self, mock_get_conn, mock_connection):
        """Test executing a custom query successfully"""
        mock_get_conn.return_value = (mock_connection, None)

        result_df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        mock_connection.query.return_value = result_df

        from pages.explorer import execute_custom_query

        df, error = execute_custom_query("SELECT * FROM test_table")

        assert error is None
        assert df is not None
        assert len(df) == 3

        # Verify LIMIT was added
        actual_query = mock_connection.query.call_args[0][0]
        assert 'LIMIT 1000' in actual_query

    @patch('pages.explorer.get_database_connection')
    def test_execute_custom_query_with_limit(self, mock_get_conn, mock_connection):
        """Test query with existing LIMIT clause"""
        mock_get_conn.return_value = (mock_connection, None)
        mock_connection.query.return_value = pd.DataFrame()

        from pages.explorer import execute_custom_query

        execute_custom_query("SELECT * FROM test LIMIT 50")

        # Should not add another LIMIT
        actual_query = mock_connection.query.call_args[0][0]
        assert actual_query.count('LIMIT') == 1

    @patch('pages.explorer.get_database_connection')
    def test_execute_custom_query_error(self, mock_get_conn, mock_connection):
        """Test query execution error handling"""
        mock_get_conn.return_value = (mock_connection, None)
        mock_connection.query.side_effect = Exception("Invalid SQL")

        from pages.explorer import execute_custom_query

        df, error = execute_custom_query("INVALID SQL")

        assert df is None
        assert error is not None
        assert "Invalid SQL" in error

    @patch('pages.explorer.st')
    @patch('pages.explorer.get_table_schema')
    def test_show_schema_browser(self, mock_get_schema, mock_st, sample_schema_info):
        """Test schema browser display"""
        mock_get_schema.return_value = (sample_schema_info, None)

        # Mock selectbox
        mock_st.selectbox.return_value = 'dim_scenario'

        # Mock columns
        mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]

        from pages.explorer import show_schema_browser

        show_schema_browser()

        # Verify schema was loaded
        mock_get_schema.assert_called_once()

        # Verify table selector was shown
        mock_st.selectbox.assert_called()

        # Verify metrics were displayed
        mock_col1.metric.assert_called_with("Total Rows", "20")
        mock_col2.metric.assert_called_with("Columns", 2)
        mock_col3.metric.assert_called_with("Table Type", "Dimension")

        # Verify dataframes were displayed
        assert mock_st.dataframe.called

    @patch('pages.explorer.st')
    @patch('pages.explorer.get_query_examples')
    @patch('pages.explorer.execute_custom_query')
    def test_show_query_interface(self, mock_execute, mock_get_examples, mock_st):
        """Test SQL query interface"""
        # Mock examples
        mock_get_examples.return_value = {
            'Basic Queries': {
                'Count records': 'SELECT COUNT(*) FROM table'
            }
        }

        # Mock UI elements
        mock_st.selectbox.side_effect = ['Basic Queries', 'Count records']
        mock_st.text_area.return_value = 'SELECT COUNT(*) FROM dim_scenario'
        mock_st.button.side_effect = [True, False]  # Execute button clicked

        # Mock columns
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock query result
        result_df = pd.DataFrame({'count': [20]})
        mock_execute.return_value = (result_df, None)

        # Mock spinner
        mock_st.spinner.return_value.__enter__ = Mock()
        mock_st.spinner.return_value.__exit__ = Mock(return_value=None)

        from pages.explorer import show_query_interface

        show_query_interface()

        # Verify query was executed
        mock_execute.assert_called_with('SELECT COUNT(*) FROM dim_scenario')

        # Verify results were displayed
        mock_st.dataframe.assert_called()
        mock_st.metric.assert_called()

    @patch('pages.explorer.st')
    def test_show_data_dictionary(self, mock_st):
        """Test data dictionary display"""
        from pages.explorer import show_data_dictionary

        show_data_dictionary()

        # Verify sections were displayed
        markdown_calls = mock_st.markdown.call_args_list
        assert any("Land Use Categories" in str(call) for call in markdown_calls)
        assert any("Climate Scenarios" in str(call) for call in markdown_calls)
        assert any("Time Periods" in str(call) for call in markdown_calls)

        # Verify dataframes were shown
        assert mock_st.dataframe.called

    @patch('pages.explorer.st')
    def test_main_explorer_page(self, mock_st):
        """Test main explorer page structure"""
        # Mock tabs
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]

        # Import main
        import pages.explorer

        # Verify page title
        mock_st.title.assert_called()
        assert "Data Explorer" in str(mock_st.title.call_args)

        # Verify tabs
        mock_st.tabs.assert_called()
        tab_names = mock_st.tabs.call_args[0][0]
        assert "Schema Browser" in tab_names
        assert "SQL Interface" in tab_names
        assert "Data Dictionary" in tab_names
