#!/usr/bin/env python3
"""
Unit tests for main Streamlit app
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Mock streamlit before importing pages
from tests.unit.streamlit.mock_streamlit import mock_st
sys.modules['streamlit'] = mock_st
import streamlit as st


class TestStreamlitApp:
    """Test the main Streamlit application"""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit components"""
        with patch('streamlit.set_page_config') as mock_config:
            with patch('streamlit.markdown') as mock_markdown:
                with patch('streamlit.navigation') as mock_nav:
                    with patch('streamlit.Page') as mock_page:
                        yield {
                            'config': mock_config,
                            'markdown': mock_markdown,
                            'navigation': mock_nav,
                            'page': mock_page
                        }
    
    @pytest.fixture
    def mock_env(self, monkeypatch, tmp_path):
        """Mock environment setup"""
        # Create a mock database file
        db_path = tmp_path / "test.duckdb"
        db_path.touch()
        
        monkeypatch.setenv("LANDUSE_DB_PATH", str(db_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        
        return {'db_path': db_path}
    
    def test_check_environment_all_good(self, mock_env):
        """Test environment check when everything is configured"""
        # Import here to avoid issues with module-level imports
        with patch('streamlit_app.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            
            from streamlit_app import check_environment
            
            checks = check_environment()
            
            assert checks['database'] is True
            assert checks['api_keys'] is True
            assert checks['dependencies'] is True
    
    def test_check_environment_missing_database(self, monkeypatch):
        """Test environment check with missing database"""
        monkeypatch.setenv("LANDUSE_DB_PATH", "/nonexistent/path.duckdb")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        
        from streamlit_app import check_environment
        
        checks = check_environment()
        
        assert checks['database'] is False
        assert checks['api_keys'] is True
        assert checks['dependencies'] is True
    
    def test_check_environment_missing_api_keys(self, mock_env, monkeypatch):
        """Test environment check with missing API keys"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        
        from streamlit_app import check_environment
        
        checks = check_environment()
        
        assert checks['database'] is True
        assert checks['api_keys'] is False
        assert checks['dependencies'] is True
    
    @patch('streamlit_app.st')
    @patch('streamlit_app.check_environment')
    @patch('streamlit_app.duckdb')
    def test_show_welcome_page(self, mock_duckdb, mock_check_env, mock_st, mock_env):
        """Test welcome page display"""
        # Mock environment checks
        mock_check_env.return_value = {
            'database': True,
            'api_keys': True,
            'dependencies': True
        }
        
        # Mock database connection
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = (100,)
        mock_duckdb.connect.return_value = mock_conn
        
        # Mock streamlit components
        mock_st.columns.return_value = [Mock(), Mock()]
        mock_st.metric = Mock()
        
        from streamlit_app import show_welcome_page
        
        show_welcome_page()
        
        # Verify page title was set
        assert mock_st.title.called
        assert "Landuse Analytics Dashboard" in str(mock_st.title.call_args)
        
        # Verify metrics were displayed
        assert mock_st.metric.called
        
        # Verify database was queried
        assert mock_conn.execute.called
        mock_conn.close.assert_called()
    
    @patch('streamlit_app.st')
    @patch('streamlit_app.check_environment')
    def test_show_welcome_page_with_warnings(self, mock_check_env, mock_st):
        """Test welcome page with system warnings"""
        # Mock environment checks with issues
        mock_check_env.return_value = {
            'database': False,
            'api_keys': False,
            'dependencies': True
        }
        
        mock_st.columns.return_value = [Mock(), Mock()]
        
        from streamlit_app import show_welcome_page
        
        show_welcome_page()
        
        # Verify warning was shown
        mock_st.warning.assert_called()
        assert "Some components need setup" in str(mock_st.warning.call_args)
    
    @patch('streamlit_app.st')
    def test_create_pages(self, mock_st):
        """Test page creation"""
        mock_st.Page = Mock(side_effect=lambda *args, **kwargs: Mock(
            title=kwargs.get('title'),
            icon=kwargs.get('icon')
        ))
        
        from streamlit_app import create_pages
        
        pages = create_pages()
        
        # Verify structure
        assert 'Main' in pages
        assert 'Analysis' in pages
        assert 'Configuration' in pages
        
        # Verify pages were created
        assert len(pages['Main']) >= 1
        assert len(pages['Analysis']) >= 3
        assert len(pages['Configuration']) >= 1
        
        # Verify specific pages
        page_titles = []
        for section in pages.values():
            for page in section:
                if hasattr(page, 'title'):
                    page_titles.append(page.title)
        
        assert "Home" in page_titles
        assert "Natural Language Chat" in page_titles
        assert "Analytics Dashboard" in page_titles
        assert "Data Explorer" in page_titles
        assert "Data Extraction" in page_titles
        assert "Settings & Help" in page_titles
    
    @patch('streamlit_app.st')
    @patch('streamlit_app.create_pages')
    def test_main_function(self, mock_create_pages, mock_st):
        """Test main application entry point"""
        # Mock page structure
        mock_pages = {
            'Main': [Mock()],
            'Analysis': [Mock(), Mock()],
            'Configuration': [Mock()]
        }
        mock_create_pages.return_value = mock_pages
        
        # Mock navigation
        mock_pg = Mock()
        mock_st.navigation.return_value = mock_pg
        
        from streamlit_app import main
        
        main()
        
        # Verify pages were created
        mock_create_pages.assert_called_once()
        
        # Verify navigation was set up
        mock_st.navigation.assert_called_once_with(mock_pages)
        
        # Verify page was run
        mock_pg.run.assert_called_once()
    
    def test_page_config_settings(self):
        """Test that page config is set correctly"""
        with patch('streamlit.set_page_config') as mock_config:
            # Import triggers the set_page_config call
            import streamlit_app
            
            # Verify set_page_config was called
            mock_config.assert_called_once()
            
            # Get the call arguments
            call_args = mock_config.call_args
            kwargs = call_args[1]
            
            # Verify settings
            assert kwargs['page_title'] == "🌾 Landuse Analytics Dashboard"
            assert kwargs['page_icon'] == "🌾"
            assert kwargs['layout'] == "wide"
            assert kwargs['initial_sidebar_state'] == "expanded"
            assert 'menu_items' in kwargs
    
    def test_custom_css_injection(self):
        """Test that custom CSS is injected"""
        with patch('streamlit.markdown') as mock_markdown:
            with patch('streamlit.set_page_config'):
                import streamlit_app
                
                # Find CSS injection call
                css_calls = [call for call in mock_markdown.call_args_list 
                           if call[0][0] and '<style>' in str(call[0][0])]
                
                assert len(css_calls) > 0
                
                # Verify CSS content
                css_content = css_calls[0][0][0]
                assert '.main-header' in css_content
                assert '.metric-card' in css_content
                assert '.feature-card' in css_content
                assert '.status-ok' in css_content
                assert 'unsafe_allow_html=True' in str(css_calls[0][1])
    
    @patch('streamlit_app.load_dotenv')
    def test_environment_loading(self, mock_load_dotenv):
        """Test that environment variables are loaded"""
        with patch('streamlit.set_page_config'):
            import streamlit_app
            
            # Verify load_dotenv was called for both .env files
            assert mock_load_dotenv.call_count >= 2
            
            # Check that config/.env was loaded
            config_env_calls = [call for call in mock_load_dotenv.call_args_list
                              if 'config/.env' in str(call)]
            assert len(config_env_calls) > 0