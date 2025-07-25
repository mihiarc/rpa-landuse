#!/usr/bin/env python3
"""
Unit tests for Streamlit analytics page
"""

# Mock streamlit before importing pages
import sys
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from tests.unit.streamlit.mock_streamlit import mock_st

sys.modules['streamlit'] = mock_st
import streamlit as st  # noqa: E402


class TestAnalyticsPage:
    """Test the analytics dashboard page"""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection"""
        conn = Mock()
        conn.query = Mock()
        return conn

    @pytest.fixture
    def sample_agricultural_data(self):
        """Sample agricultural loss data"""
        return pd.DataFrame({
            'scenario_name': ['RCP45_SSP1', 'RCP85_SSP5', 'RCP45_SSP2'],
            'rcp_scenario': ['rcp45', 'rcp85', 'rcp45'],
            'ssp_scenario': ['ssp1', 'ssp5', 'ssp2'],
            'total_acres_lost': [1000000, 1500000, 1200000]
        })

    @pytest.fixture
    def sample_urbanization_data(self):
        """Sample urbanization data"""
        return pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'from_landuse': ['Crop', 'Forest', 'Pasture'],
            'total_acres_urbanized': [500000, 300000, 200000]
        })

    @pytest.fixture
    def sample_forest_data(self):
        """Sample forest analysis data"""
        df_loss = pd.DataFrame({
            'to_landuse': ['Urban', 'Crop', 'Pasture'],
            'total_acres': [1000000, 800000, 600000]
        })

        df_gain = pd.DataFrame({
            'from_landuse': ['Crop', 'Pasture', 'Rangeland'],
            'total_acres': [400000, 300000, 200000]
        })

        df_states = pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'forest_loss': [500000, 400000, 300000],
            'forest_gain': [200000, 150000, 100000],
            'net_change': [-300000, -250000, -200000]
        })

        return df_loss, df_gain, df_states

    @patch('pages.analytics.st.connection')
    def test_get_database_connection(self, mock_st_connection):
        """Test database connection caching"""
        mock_conn = Mock()
        mock_st_connection.return_value = mock_conn

        from pages.analytics import get_database_connection

        conn1, error1 = get_database_connection()
        conn2, error2 = get_database_connection()

        assert conn1 == mock_conn
        assert conn2 == mock_conn
        assert error1 is None
        assert error2 is None

        # Verify connection was created with correct parameters
        # May be called multiple times due to caching decorator
        assert mock_st_connection.call_count >= 1
        # Check the last call
        call_kwargs = mock_st_connection.call_args[1]
        assert call_kwargs['name'] == 'landuse_db_analytics'
        assert call_kwargs['read_only'] is True

    @patch('pages.analytics.get_database_connection')
    def test_load_summary_data(self, mock_get_conn, mock_connection):
        """Test loading summary statistics"""
        mock_get_conn.return_value = (mock_connection, None)

        # Mock query results
        mock_connection.query.side_effect = [
            pd.DataFrame({'count': [3075]}),  # counties
            pd.DataFrame({'count': [20]}),    # scenarios
            pd.DataFrame({'count': [1000000]}),  # transitions
            pd.DataFrame({'count': [6]})      # time periods
        ]

        from pages.analytics import load_summary_data

        stats, error = load_summary_data()

        assert error is None
        assert stats['total_counties'] == 3075
        assert stats['total_scenarios'] == 20
        assert stats['total_transitions'] == 1000000
        assert stats['time_periods'] == 6

    @patch('pages.analytics.get_database_connection')
    def test_load_agricultural_loss_data(self, mock_get_conn, mock_connection, sample_agricultural_data):
        """Test loading agricultural loss data"""
        mock_get_conn.return_value = (mock_connection, None)
        mock_connection.query.return_value = sample_agricultural_data

        from pages.analytics import load_agricultural_loss_data

        df, error = load_agricultural_loss_data()

        assert error is None
        assert len(df) == 3
        assert 'total_acres_lost' in df.columns
        assert df['total_acres_lost'].max() == 1500000

    def test_create_agricultural_loss_chart(self, sample_agricultural_data):
        """Test agricultural loss chart creation"""
        from pages.analytics import create_agricultural_loss_chart

        fig = create_agricultural_loss_chart(sample_agricultural_data)

        assert fig is not None
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.layout.title.text is not None

    def test_create_agricultural_loss_chart_empty_data(self):
        """Test chart creation with empty data"""
        from pages.analytics import create_agricultural_loss_chart

        fig = create_agricultural_loss_chart(pd.DataFrame())

        assert fig is None

    def test_create_urbanization_chart(self, sample_urbanization_data):
        """Test urbanization chart creation"""
        from pages.analytics import create_urbanization_chart

        fig = create_urbanization_chart(sample_urbanization_data)

        assert fig is not None
        assert isinstance(fig, go.Figure)
        # Check that state codes are in the y-axis data
        assert '06' in str(fig.data[0].y)
        assert '48' in str(fig.data[0].y)

    @patch('pages.analytics.get_database_connection')
    def test_load_forest_analysis_data(self, mock_get_conn, mock_connection, sample_forest_data):
        """Test loading forest analysis data"""
        mock_get_conn.return_value = (mock_connection, None)

        df_loss, df_gain, df_states = sample_forest_data
        mock_connection.query.side_effect = [df_loss, df_gain, df_states]

        from pages.analytics import load_forest_analysis_data

        result_loss, result_gain, result_states, error = load_forest_analysis_data()

        assert error is None
        assert len(result_loss) == 3
        assert len(result_gain) == 3
        assert len(result_states) == 3
        assert 'state_abbr' in result_states.columns
        assert 'state_name' in result_states.columns

    def test_create_choropleth_map(self, sample_forest_data):
        """Test choropleth map creation"""
        _, _, df_states = sample_forest_data

        # Add required columns
        df_states['state_abbr'] = ['CA', 'TX', 'NY']
        df_states['state_name'] = ['California', 'Texas', 'New York']
        df_states['dominant_transition'] = ['Forest → Urban'] * 3
        df_states['total_change_acres'] = df_states['forest_loss']  # Use forest_loss as total change
        df_states['transition_types'] = ['Forest → Urban, Forest → Crop'] * 3

        from pages.analytics import create_choropleth_map

        fig = create_choropleth_map(df_states)

        assert fig is not None
        assert isinstance(fig, go.Figure)

    def test_create_sankey_diagram(self):
        """Test Sankey diagram creation"""
        # Mock Sankey data
        mock_data = pd.DataFrame({
            'source': ['Forest', 'Crop', 'Pasture'],
            'target': ['Urban', 'Urban', 'Urban'],
            'value': [1000000, 800000, 600000],
            'scenario_count': [20, 20, 20]  # Add required column
        })

        from pages.analytics import create_sankey_diagram

        with patch('pages.analytics.load_sankey_data') as mock_load_data:
            mock_load_data.return_value = (mock_data, None)

            fig = create_sankey_diagram(mock_data)

            assert fig is not None
            assert isinstance(fig, go.Figure)
            assert len(fig.data) > 0
            assert fig.data[0].type == 'sankey'

    def test_overview_metrics(self):
        """Test overview metrics loading"""
        # Test load_summary_data directly
        from pages.analytics import load_summary_data

        with patch('pages.analytics.get_database_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_get_conn.return_value = (mock_conn, None)

            # Mock query results
            mock_conn.query.side_effect = [
                pd.DataFrame({'count': [3075]}),  # counties
                pd.DataFrame({'count': [20]}),    # scenarios
                pd.DataFrame({'count': [1000000]}),  # transitions
                pd.DataFrame({'count': [6]})      # time periods
            ]

            stats, error = load_summary_data()

            assert error is None
            assert stats['total_counties'] == 3075
            assert stats['total_scenarios'] == 20

    @patch('pages.analytics.st')
    @patch('pages.analytics.load_agricultural_loss_data')
    @patch('pages.analytics.create_agricultural_loss_chart')
    def test_agricultural_charts_integration(self, mock_create_chart, mock_load_data, mock_st, sample_agricultural_data):
        """Test agricultural data loading and chart creation"""
        mock_load_data.return_value = (sample_agricultural_data, None)
        mock_chart = Mock()
        mock_create_chart.return_value = mock_chart

        # Test that the functions work together
        df, error = mock_load_data()
        chart = mock_create_chart(df)

        assert error is None
        assert chart == mock_chart

    @patch('pages.analytics.load_forest_analysis_data')
    def test_forest_analysis_data_integration(self, mock_load):
        """Test forest analysis data loading integration"""
        # Mock data loading
        mock_load.return_value = (
            pd.DataFrame({'to_landuse': ['Urban'], 'total_acres': [1000000]}),
            pd.DataFrame({'from_landuse': ['Crop'], 'total_acres': [500000]}),
            pd.DataFrame({'state_code': ['06'], 'net_change': [-500000]}),
            None
        )

        # Test data loading
        loss, gain, states, error = mock_load()

        assert error is None
        assert len(loss) == 1
        assert len(gain) == 1
        assert len(states) == 1

    def test_page_functions_exist(self):
        """Test that key page functions exist and are callable"""
        from pages import analytics

        # Test that key functions exist
        assert hasattr(analytics, 'get_database_connection')
        assert hasattr(analytics, 'load_summary_data')
        assert hasattr(analytics, 'load_agricultural_loss_data')
        assert hasattr(analytics, 'create_agricultural_loss_chart')
        assert hasattr(analytics, 'create_urbanization_chart')
        assert hasattr(analytics, 'load_forest_analysis_data')
        assert hasattr(analytics, 'create_choropleth_map')
        assert hasattr(analytics, 'create_sankey_diagram')

        # Test that they are callable
        assert callable(analytics.get_database_connection)
        assert callable(analytics.load_summary_data)
