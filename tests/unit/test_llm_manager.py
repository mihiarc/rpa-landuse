#!/usr/bin/env python3
"""
Unit tests for LLM Manager functionality after Anthropic removal.

These tests ensure proper LLM creation, model validation, and error handling
now that only OpenAI models are supported.
"""

import os
from unittest.mock import Mock, patch

import pytest
from langchain_openai import ChatOpenAI

from landuse.agents.llm_manager import LLMManager
from landuse.core.app_config import AppConfig
from landuse.exceptions import APIKeyError, LLMError


class TestLLMManager:
    """Test LLM Manager functionality with OpenAI-only support."""

    def test_create_llm_with_openai_model(self):
        """Test creating LLM with valid OpenAI model."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig(llm={'model_name': 'gpt-4o-mini'})

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_llm_instance = Mock(spec=ChatOpenAI)
                mock_openai.return_value = mock_llm_instance

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Verify OpenAI was called with correct parameters
                mock_openai.assert_called_once_with(
                    model="gpt-4o-mini",
                    openai_api_key='sk-test123456789012345678901234567890123456789012345',
                    temperature=config.llm.temperature,
                    max_tokens=config.llm.max_tokens,
                )

                assert llm == mock_llm_instance

    def test_create_llm_with_different_openai_models(self):
        """Test creating LLM with various OpenAI models."""
        models_to_test = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]

        for model_name in models_to_test:
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                config = AppConfig(llm={'model_name': model_name})

                with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                    mock_openai.return_value = Mock(spec=ChatOpenAI)

                    manager = LLMManager(config)
                    manager.create_llm()

                    # Verify the configured model is used
                    mock_openai.assert_called_once()
                    call_args = mock_openai.call_args
                    assert call_args[1]['model'] == model_name

    def test_create_llm_missing_api_key(self):
        """Test error handling when OpenAI API key is missing."""
        # Remove API key from environment - this should fail at config creation
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):  # AppConfig will raise ConfigurationError
                config = AppConfig(llm={'model_name': 'gpt-4o-mini'})


    def test_api_key_masking(self):
        """Test API key masking for security."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig()
        manager = LLMManager(config)

        # Test various API key formats
        test_cases = [
            ("sk-1234567890123456789012345678901234567890123456", "sk-12345...3456"),
            ("sk-abc", "***"),  # Too short
            (None, "NOT_SET"),
            ("", "NOT_SET")
        ]

        for api_key, expected_masked in test_cases:
            masked = manager._mask_api_key(api_key)
            assert masked == expected_masked

    def test_validate_api_key(self):
        """Test API key validation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig()
        manager = LLMManager(config)

        # Test with valid key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            assert manager.validate_api_key() is True

        # Test without key
        with patch.dict(os.environ, {}, clear=True):
            assert manager.validate_api_key() is False

    def test_get_model_name(self):
        """Test getting current model name from config."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig(llm={'model_name': 'gpt-4o'})

        manager = LLMManager(config)
        assert manager.get_model_name() == "gpt-4o"

    def test_app_config_compatibility(self):
        """Test LLM Manager works with new AppConfig."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            app_config = AppConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(app_config)
                llm = manager.create_llm()

                # Verify correct parameters were used
                mock_openai.assert_called_once()
                call_args = mock_openai.call_args
                assert call_args[1]['model'] == app_config.llm.model_name
                assert call_args[1]['temperature'] == app_config.llm.temperature
                assert call_args[1]['max_tokens'] == app_config.llm.max_tokens

    def test_different_temperature_and_tokens(self):
        """Test LLM Manager with different temperature and max_tokens settings."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig(
                llm={'model_name': 'gpt-4o-mini', 'temperature': 0.3, 'max_tokens': 2000}
            )

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Verify correct parameters were used
                mock_openai.assert_called_once()
                call_args = mock_openai.call_args
                assert call_args[1]['model'] == "gpt-4o-mini"
                assert call_args[1]['temperature'] == 0.3
                assert call_args[1]['max_tokens'] == 2000

    def test_performance_monitoring_integration(self):
        """Test that performance monitoring is properly integrated."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(config)

                # The @time_llm_operation decorator should be applied
                assert hasattr(manager.create_llm, '__wrapped__')

                # Call should still work normally
                llm = manager.create_llm()
                assert llm is not None

    def test_console_output_integration(self):
        """Test that console output works correctly."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig(llm={'model_name': 'gpt-4o'})

            mock_console = Mock()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(config, console=mock_console)
                manager.create_llm()

                # Verify console output was called
                assert mock_console.print.call_count >= 2  # At least model name and API key info

                # Check that model name appears in output
                calls = [call[0][0] for call in mock_console.print.call_args_list]
                model_mentioned = any("gpt-4o" in str(call) for call in calls)
                assert model_mentioned


class TestLLMManagerErrorHandling:
    """Test error handling scenarios for LLM Manager."""

    def test_invalid_api_key_format(self):
        """Test handling of invalid API key formats."""
        # Test with invalid key format - but manager doesn't validate format, only existence
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'invalid-key'}):
            config = AppConfig()
            manager = LLMManager(config)

            # Manager just checks for key existence, OpenAI client would handle invalid format
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.side_effect = Exception("Invalid API key format")

                with pytest.raises(Exception, match="Invalid API key format"):
                    manager.create_llm()

    def test_openai_client_failure(self):
        """Test handling of OpenAI client creation failures."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = AppConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                # Simulate OpenAI client failure
                mock_openai.side_effect = Exception("OpenAI service unavailable")

                manager = LLMManager(config)

                with pytest.raises(Exception, match="OpenAI service unavailable"):
                    manager.create_llm()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
