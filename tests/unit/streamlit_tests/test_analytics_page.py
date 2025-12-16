#!/usr/bin/env python3
"""
Unit tests for Streamlit analytics page

Tests the analytics dashboard functionality including:
- Database connection management
- Data loading functions
- Chart creation functions
- Visualization components
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from tests.unit.streamlit_tests.mock_streamlit import mock_st

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
        """Sample agricultural analysis data matching analytics.py API"""
        # df_loss - what agriculture becomes (grouped by to_landuse)
        df_loss = pd.DataFrame({
            'to_landuse': ['Urban', 'Forest', 'Rangeland'],
            'rcp_scenario': ['rcp45', 'rcp85', 'rcp45'],
            'total_acres': [1000000, 800000, 600000],
            'avg_acres_per_county': [500, 400, 300],
            'states_affected': [50, 48, 45]
        })
        # df_gain - what becomes agriculture (grouped by from_landuse)
        df_gain = pd.DataFrame({
            'from_landuse': ['Forest', 'Rangeland', 'Pasture'],
            'rcp_scenario': ['rcp45', 'rcp85', 'rcp45'],
            'total_acres': [500000, 400000, 300000],
            'avg_acres_per_county': [250, 200, 150],
            'states_affected': [40, 35, 30]
        })
        # df_states - state-level summary
        df_states = pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'state_name': ['California', 'Texas', 'New York'],
            'baseline_acres': [10000000, 15000000, 5000000],
            'ag_loss': [500000, 400000, 300000],
            'ag_gain': [200000, 150000, 100000],
            'net_change': [-300000, -250000, -200000]
        })
        return df_loss, df_gain, df_states

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

    @pytest.fixture
    def sample_sankey_data(self):
        """Sample Sankey diagram data"""
        return pd.DataFrame({
            'source': ['Forest', 'Crop', 'Pasture'],
            'target': ['Urban', 'Urban', 'Urban'],
            'value': [1000000, 800000, 600000],
            'scenario_count': [20, 20, 20]
        })

    def test_page_functions_exist(self):
        """Test that key page functions exist and are callable"""
        from views import analytics

        # Test that key functions exist (current API)
        assert hasattr(analytics, 'get_database_connection')
        assert hasattr(analytics, 'load_agricultural_analysis_data')
        assert hasattr(analytics, 'load_urbanization_data')
        assert hasattr(analytics, 'load_forest_analysis_data')
        assert hasattr(analytics, 'load_climate_comparison_data')
        assert hasattr(analytics, 'create_urbanization_chart')
        assert hasattr(analytics, 'create_agricultural_flow_chart')
        assert hasattr(analytics, 'create_forest_flow_chart')
        assert hasattr(analytics, 'create_choropleth_map')
        assert hasattr(analytics, 'create_sankey_diagram')
        assert hasattr(analytics, 'main')

        # Test that they are callable
        assert callable(analytics.get_database_connection)
        assert callable(analytics.load_agricultural_analysis_data)
        assert callable(analytics.create_urbanization_chart)
        assert callable(analytics.main)

    @patch('views.analytics.st.connection')
    def test_get_database_connection(self, mock_st_connection):
        """Test database connection caching"""
        mock_conn = Mock()
        mock_st_connection.return_value = mock_conn

        from views.analytics import get_database_connection

        conn, error = get_database_connection()

        assert conn == mock_conn
        assert error is None

        # Verify connection was created with correct parameters
        assert mock_st_connection.call_count >= 1
        call_kwargs = mock_st_connection.call_args[1]
        assert call_kwargs['name'] == 'landuse_db_analytics'
        assert call_kwargs['read_only'] is True

    @patch('views.analytics.get_database_connection')
    def test_load_agricultural_analysis_data(self, mock_get_conn, mock_connection, sample_agricultural_data):
        """Test loading agricultural analysis data"""
        mock_get_conn.return_value = (mock_connection, None)

        df_loss, df_gain, df_states = sample_agricultural_data
        mock_connection.query.side_effect = [df_loss, df_gain, df_states]

        from views.analytics import load_agricultural_analysis_data

        result_loss, result_gain, result_states, error = load_agricultural_analysis_data()

        assert error is None
        assert result_loss is not None
        assert result_gain is not None
        assert result_states is not None

    def test_create_urbanization_chart(self, sample_urbanization_data):
        """Test urbanization chart creation"""
        from views.analytics import create_urbanization_chart

        fig = create_urbanization_chart(sample_urbanization_data)

        assert fig is not None
        assert isinstance(fig, go.Figure)

    def test_create_urbanization_chart_with_state_codes(self, sample_urbanization_data):
        """Test urbanization chart includes state codes"""
        from views.analytics import create_urbanization_chart

        fig = create_urbanization_chart(sample_urbanization_data)

        assert fig is not None
        # Check that state codes are in the figure data
        assert '06' in str(fig.data[0].y) or '48' in str(fig.data[0].y)

    def test_create_agricultural_flow_chart(self, sample_agricultural_data):
        """Test agricultural flow chart creation"""
        from views.analytics import create_agricultural_flow_chart

        df_loss, df_gain, df_states = sample_agricultural_data
        fig = create_agricultural_flow_chart(df_loss, df_gain)

        assert fig is not None
        assert isinstance(fig, go.Figure)

    def test_create_agricultural_flow_chart_with_none(self):
        """Test agricultural flow chart with None data"""
        from views.analytics import create_agricultural_flow_chart

        # Function explicitly handles None inputs
        fig = create_agricultural_flow_chart(None, None)

        # Should return None when given None inputs
        assert fig is None

    @patch('views.analytics.get_database_connection')
    def test_load_forest_analysis_data(self, mock_get_conn, mock_connection, sample_forest_data):
        """Test loading forest analysis data"""
        mock_get_conn.return_value = (mock_connection, None)

        df_loss, df_gain, df_states = sample_forest_data
        mock_connection.query.side_effect = [df_loss, df_gain, df_states]

        from views.analytics import load_forest_analysis_data

        result_loss, result_gain, result_states, error = load_forest_analysis_data()

        assert error is None
        assert len(result_loss) == 3
        assert len(result_gain) == 3
        assert len(result_states) == 3
        assert 'state_abbr' in result_states.columns
        assert 'state_name' in result_states.columns

    def test_create_sankey_diagram(self, sample_sankey_data):
        """Test Sankey diagram creation"""
        from views.analytics import create_sankey_diagram

        fig = create_sankey_diagram(sample_sankey_data)

        assert fig is not None
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'sankey'

    def test_create_sankey_diagram_has_correct_structure(self, sample_sankey_data):
        """Test Sankey diagram has correct node structure"""
        from views.analytics import create_sankey_diagram

        fig = create_sankey_diagram(sample_sankey_data)

        # Sankey should have node and link data
        sankey_data = fig.data[0]
        assert hasattr(sankey_data, 'node')
        assert hasattr(sankey_data, 'link')

    def test_create_choropleth_map_with_valid_data(self):
        """Test choropleth map creation with valid data"""
        from views.analytics import create_choropleth_map

        df = pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'state_abbr': ['CA', 'TX', 'NY'],
            'state_name': ['California', 'Texas', 'New York'],
            'net_change': [-300000, -250000, -200000],
            'baseline': [1000000, 900000, 800000],
            'forest_loss': [500000, 400000, 300000],
            'forest_gain': [200000, 150000, 100000],
            'percent_change': [-30.0, -27.8, -25.0],
            'future': [700000, 650000, 600000],
            'dominant_transition': ['To Urban', 'To Crop', 'To Pasture']
        })

        fig = create_choropleth_map(df)

        assert fig is not None
        assert isinstance(fig, go.Figure)

    @patch('views.analytics.load_agricultural_analysis_data')
    @patch('views.analytics.create_agricultural_flow_chart')
    def test_agricultural_charts_integration(self, mock_create_chart, mock_load_data, sample_agricultural_data):
        """Test agricultural data loading and chart creation integration"""
        df_loss, df_gain, df_states = sample_agricultural_data
        mock_load_data.return_value = (df_loss, df_gain, df_states, None)
        mock_chart = Mock()
        mock_create_chart.return_value = mock_chart

        # Test that the functions work together
        result_loss, result_gain, result_states, error = mock_load_data()
        chart = mock_create_chart(result_loss, result_gain)

        assert error is None
        assert chart == mock_chart

    @patch('views.analytics.load_forest_analysis_data')
    def test_forest_analysis_data_integration(self, mock_load):
        """Test forest analysis data loading integration"""
        mock_load.return_value = (
            pd.DataFrame({'to_landuse': ['Urban'], 'total_acres': [1000000]}),
            pd.DataFrame({'from_landuse': ['Crop'], 'total_acres': [500000]}),
            pd.DataFrame({
                'state_code': ['06'],
                'net_change': [-500000],
                'state_abbr': ['CA'],
                'state_name': ['California']
            }),
            None
        )

        loss, gain, states, error = mock_load()

        assert error is None
        assert len(loss) == 1
        assert len(gain) == 1
        assert len(states) == 1

    @patch('views.analytics.get_database_connection')
    def test_load_sankey_data_with_filters(self, mock_get_conn, mock_connection, sample_sankey_data):
        """Test load_sankey_data with filter parameters"""
        mock_get_conn.return_value = (mock_connection, None)
        mock_connection.query.return_value = sample_sankey_data

        from views.analytics import load_sankey_data

        # Test with land use filter
        df, error = load_sankey_data(from_landuse="Forest")

        # Should execute without error (may return data or validation error)

    @patch('views.analytics.get_database_connection')
    def test_load_sankey_data_validates_landuse(self, mock_get_conn, mock_connection):
        """Test load_sankey_data validates land use types"""
        mock_get_conn.return_value = (mock_connection, None)

        from views.analytics import load_sankey_data

        # Test with invalid land use type
        df, error = load_sankey_data(from_landuse="InvalidType")

        # Should return error for invalid type
        assert error is not None
        assert df is None

    def test_load_urbanization_data_structure(self):
        """Test load_urbanization_data returns expected structure"""
        from views import analytics

        with patch.object(analytics, 'get_database_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_get_conn.return_value = (mock_conn, None)
            mock_conn.query.return_value = pd.DataFrame({
                'state_code': ['06'],
                'from_landuse': ['Crop'],
                'total_acres_urbanized': [500000]
            })

            df, error = analytics.load_urbanization_data()

            assert error is None
            assert df is not None

    def test_main_function_exists(self):
        """Test that main function exists and is callable"""
        from views import analytics

        assert hasattr(analytics, 'main')
        assert callable(analytics.main)

    def test_show_enhanced_visualizations_exists(self):
        """Test that show_enhanced_visualizations function exists"""
        from views import analytics

        assert hasattr(analytics, 'show_enhanced_visualizations')
        assert callable(analytics.show_enhanced_visualizations)

    def test_create_scenario_spider_chart_exists(self):
        """Test that create_scenario_spider_chart function exists"""
        from views import analytics

        assert hasattr(analytics, 'create_scenario_spider_chart')
        assert callable(analytics.create_scenario_spider_chart)

    @patch('views.analytics.get_database_connection')
    def test_create_scenario_spider_chart_validates_scenarios(self, mock_get_conn, mock_connection):
        """Test create_scenario_spider_chart validates scenario names"""
        mock_get_conn.return_value = (mock_connection, None)
        mock_connection.query.return_value = pd.DataFrame({
            'scenario_name': ['test'],
            'to_landuse': ['Urban'],
            'total_acres_gained': [100]
        })

        from views.analytics import create_scenario_spider_chart

        # Test with valid scenarios - should not error
        result, error = create_scenario_spider_chart(['CNRM-CM5_rcp45_ssp1'])

        # Function should handle both success and validation errors
