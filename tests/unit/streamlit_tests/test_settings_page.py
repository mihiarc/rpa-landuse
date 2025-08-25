#!/usr/bin/env python3
"""
Unit tests for Streamlit settings page
"""

import json
import os

# Mock streamlit before importing pages
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from tests.unit.streamlit_tests.mock_streamlit import mock_st

sys.modules['streamlit'] = mock_st
import streamlit as st  # noqa: E402


class TestSettingsPage:
    """Test the settings and help page"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        monkeypatch.setenv("LANDUSE_DB_PATH", "/path/to/test.duckdb")
        monkeypatch.setenv("LANDUSE_MODEL", "gpt-4")
        monkeypatch.setenv("TEMPERATURE", "0.3")
        monkeypatch.setenv("MAX_TOKENS", "2000")

    @patch('pages.settings.st')
    @patch('pages.settings.Path')
    def test_check_environment_status(self, mock_path, mock_st, mock_env):
        """Test environment status checking"""
        # Mock file existence
        mock_path.return_value.exists.return_value = True

        from pages.settings import check_environment_status

        status = check_environment_status()

        assert status['api_keys']['openai'] is True
        assert status['api_keys']['anthropic'] is True
        assert status['database']['exists'] is True
        assert status['database']['path'] == "/path/to/test.duckdb"
        assert status['model_config']['model'] == "gpt-4"
        assert status['model_config']['temperature'] == 0.3

    @patch('pages.settings.st')
    def test_check_environment_status_missing_keys(self, mock_st, monkeypatch):
        """Test environment status with missing API keys"""
        # Remove API keys
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        from pages.settings import check_environment_status

        status = check_environment_status()

        assert status['api_keys']['openai'] is False
        assert status['api_keys']['anthropic'] is False

    @patch('pages.settings.Path')
    def test_get_env_file_path(self, mock_path):
        """Test getting environment file path"""
        from pages.settings import get_env_file_path

        env_path = get_env_file_path()

        assert isinstance(env_path, Path)
        assert env_path.name == ".env"
        assert "config" in str(env_path)

    @patch('pages.settings.Path.exists')
    @patch('pages.settings.Path.read_text')
    def test_load_env_file_exists(self, mock_read_text, mock_exists):
        """Test loading existing env file"""
        mock_exists.return_value = True
        mock_read_text.return_value = """
OPENAI_API_KEY=test-key
LANDUSE_MODEL=gpt-4
TEMPERATURE=0.5
"""

        from pages.settings import load_env_file

        content = load_env_file()

        assert "OPENAI_API_KEY=test-key" in content
        assert "LANDUSE_MODEL=gpt-4" in content

    @patch('pages.settings.Path.exists')
    def test_load_env_file_not_exists(self, mock_exists):
        """Test loading non-existent env file"""
        mock_exists.return_value = False

        from pages.settings import load_env_file

        content = load_env_file()

        assert "OPENAI_API_KEY=" in content
        assert "ANTHROPIC_API_KEY=" in content
        assert "# Landuse Agent Configuration" in content

    @patch('pages.settings.Path.parent.mkdir')
    @patch('pages.settings.Path.write_text')
    @patch('pages.settings.st')
    def test_save_env_file_success(self, mock_st, mock_write_text, mock_mkdir):
        """Test saving env file successfully"""
        from pages.settings import save_env_file

        content = "OPENAI_API_KEY=new-key\nTEMPERATURE=0.7"
        save_env_file(content)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write_text.assert_called_once_with(content)
        mock_st.success.assert_called_once()

    @patch('pages.settings.Path.write_text')
    @patch('pages.settings.st')
    def test_save_env_file_error(self, mock_st, mock_write_text):
        """Test saving env file with error"""
        mock_write_text.side_effect = Exception("Permission denied")

        from pages.settings import save_env_file

        save_env_file("content")

        mock_st.error.assert_called_once()
        assert "Permission denied" in str(mock_st.error.call_args)

    def test_mask_api_key(self):
        """Test API key masking"""
        from pages.settings import mask_api_key

        assert mask_api_key("sk-1234567890abcdef") == "sk-123...def"
        assert mask_api_key("short") == "sho...ort"
        assert mask_api_key("") == "Not set"
        assert mask_api_key(None) == "Not set"

    @patch('pages.settings.st')
    def test_show_status_card(self, mock_st):
        """Test status card display"""
        mock_container = Mock()
        mock_st.container.return_value.__enter__ = Mock(return_value=mock_container)
        mock_st.container.return_value.__exit__ = Mock(return_value=None)

        from pages.settings import show_status_card

        show_status_card("Test Title", {"item1": True, "item2": False})

        mock_container.subheader.assert_called_once_with("Test Title")

        # Verify status items were displayed
        success_calls = list(mock_container.success.call_args_list)
        error_calls = list(mock_container.error.call_args_list)

        assert len(success_calls) >= 1
        assert len(error_calls) >= 1

    @patch('pages.settings.st')
    @patch('pages.settings.check_environment_status')
    def test_show_environment_status(self, mock_check_status, mock_st, mock_env):
        """Test environment status display"""
        mock_check_status.return_value = {
            'api_keys': {'openai': True, 'anthropic': False},
            'database': {'exists': True, 'path': '/test.db'},
            'model_config': {'model': 'gpt-4', 'temperature': 0.5}
        }

        mock_st.columns.return_value = [Mock(), Mock()]

        from pages.settings import show_environment_status

        show_environment_status()

        # Verify columns were created
        mock_st.columns.assert_called()

        # Verify status was checked
        mock_check_status.assert_called_once()

    @patch('pages.settings.st')
    @patch('pages.settings.load_env_file')
    @patch('pages.settings.save_env_file')
    def test_show_configuration_editor(self, mock_save, mock_load, mock_st):
        """Test configuration editor"""
        mock_load.return_value = "OPENAI_API_KEY=test-key"
        mock_st.text_area.return_value = "OPENAI_API_KEY=new-key"
        mock_st.button.return_value = True  # Simulate save button click

        from pages.settings import show_configuration_editor

        show_configuration_editor()

        # Verify editor was shown
        mock_st.text_area.assert_called()

        # Verify save was called
        mock_save.assert_called_once_with("OPENAI_API_KEY=new-key")

    @patch('pages.settings.st')
    def test_show_usage_guide(self, mock_st):
        """Test usage guide display"""
        from pages.settings import show_usage_guide

        show_usage_guide()

        # Verify guide sections were displayed
        markdown_calls = mock_st.markdown.call_args_list
        assert any("Getting Started" in str(call) for call in markdown_calls)
        assert any("Example Questions" in str(call) for call in markdown_calls)

    @patch('pages.settings.st')
    def test_show_api_documentation(self, mock_st):
        """Test API documentation display"""
        from pages.settings import show_api_documentation

        show_api_documentation()

        # Verify documentation sections
        markdown_calls = mock_st.markdown.call_args_list
        assert any("Database Schema" in str(call) for call in markdown_calls)
        assert any("dim_scenario" in str(call) for call in markdown_calls)

    @patch('pages.settings.st')
    def test_main_settings_page(self, mock_st):
        """Test main settings page structure"""
        # Mock tabs
        mock_st.tabs.return_value = [Mock(), Mock(), Mock(), Mock()]

        # Import main
        import pages.settings

        # Verify page title
        mock_st.title.assert_called()
        assert "Settings & Help" in str(mock_st.title.call_args)

        # Verify tabs were created
        mock_st.tabs.assert_called()
        tab_names = mock_st.tabs.call_args[0][0]
        assert "Environment Status" in tab_names
        assert "Configuration" in tab_names
        assert "Usage Guide" in tab_names
        assert "API Documentation" in tab_names
