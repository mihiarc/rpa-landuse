#!/usr/bin/env python3
"""
Unit tests for LLM Manager functionality after Anthropic removal.

These tests ensure proper LLM creation, model validation, and error handling
now that only OpenAI models are supported.
"""

import os
import pytest
from unittest.mock import Mock, patch
from langchain_openai import ChatOpenAI

from landuse.agents.llm_manager import LLMManager
from landuse.config.landuse_config import LanduseConfig
from landuse.core.app_config import AppConfig
from landuse.exceptions import APIKeyError, LLMError


class TestLLMManager:
    """Test LLM Manager functionality with OpenAI-only support."""

    def test_create_llm_with_openai_model(self):
        """Test creating LLM with valid OpenAI model."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(model_name="gpt-4o-mini")

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_llm_instance = Mock(spec=ChatOpenAI)
                mock_openai.return_value = mock_llm_instance

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Verify OpenAI was called with correct parameters
                mock_openai.assert_called_once_with(
                    model="gpt-4o-mini",
                    openai_api_key='sk-test123456789012345678901234567890123456789012345',
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
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
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name=model_name)

            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                    mock_openai.return_value = Mock(spec=ChatOpenAI)

                    manager = LLMManager(config)
                    manager.create_llm()

                    # Verify correct model was requested
                    mock_openai.assert_called_once()
                    call_args = mock_openai.call_args
                    assert call_args[1]['model'] == model_name

    def test_create_llm_missing_api_key(self):
        """Test error handling when OpenAI API key is missing."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(model_name="gpt-4o-mini")

        # Remove API key from environment
        with patch.dict(os.environ, {}, clear=True):
            manager = LLMManager(config)

            with pytest.raises(APIKeyError) as exc_info:
                manager.create_llm()

            assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)
            assert exc_info.value.model_name == "gpt-4o-mini"

    def test_create_llm_with_anthropic_model_should_fail(self):
        """Test that Anthropic models are rejected gracefully."""
        anthropic_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ]

        for model_name in anthropic_models:
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name=model_name)

            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                manager = LLMManager(config)

                # Claude models should now raise a helpful migration error
                with pytest.raises(LLMError) as exc_info:
                    manager.create_llm()

                # Check the error message provides migration guidance
                error_msg = str(exc_info.value)
                assert "no longer supported" in error_msg
                assert "Please use" in error_msg
                assert "LANDUSE_MODEL=" in error_msg
                assert "OPENAI_API_KEY" in error_msg

    def test_api_key_masking(self):
        """Test API key masking for security."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()
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
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()
        manager = LLMManager(config)

        # Test with valid key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            assert manager.validate_api_key() is True

        # Test without key
        with patch.dict(os.environ, {}, clear=True):
            assert manager.validate_api_key() is False

    def test_get_model_name(self):
        """Test getting current model name."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(model_name="gpt-4o")

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

    def test_legacy_config_compatibility(self):
        """Test LLM Manager works with legacy LanduseConfig."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            legacy_config = LanduseConfig(
                model_name="gpt-4o-mini",
                temperature=0.3,
                max_tokens=2000
            )

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(legacy_config)
                llm = manager.create_llm()

                # Verify correct parameters were used
                mock_openai.assert_called_once()
                call_args = mock_openai.call_args
                assert call_args[1]['model'] == "gpt-4o-mini"
                assert call_args[1]['temperature'] == 0.3
                assert call_args[1]['max_tokens'] == 2000

    def test_performance_monitoring_integration(self):
        """Test that performance monitoring is properly integrated."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
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
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(model_name="gpt-4o")

        mock_console = Mock()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
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

    def test_config_conversion_from_app_config(self):
        """Test conversion from AppConfig to legacy config."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            app_config = AppConfig(
                llm={'model_name': 'gpt-4o', 'temperature': 0.5, 'max_tokens': 3000},
                agent={'max_iterations': 10, 'enable_memory': False},
                logging={'level': 'DEBUG'}
            )

            manager = LLMManager(app_config)

            # Verify conversion worked correctly
            assert manager.config.model_name == 'gpt-4o'
            assert manager.config.temperature == 0.5
            assert manager.config.max_tokens == 3000
            assert manager.config.max_iterations == 10
            assert manager.config.enable_memory is False
            assert manager.config.debug is True


class TestLLMManagerErrorHandling:
    """Test error handling scenarios for LLM Manager."""

    def test_invalid_api_key_format(self):
        """Test handling of invalid API key formats."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        # Test with invalid key format - but manager doesn't validate format, only existence
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'invalid-key'}):
            manager = LLMManager(config)

            # Manager just checks for key existence, OpenAI client would handle invalid format
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.side_effect = Exception("Invalid API key format")

                with pytest.raises(Exception, match="Invalid API key format"):
                    manager.create_llm()

    def test_openai_client_failure(self):
        """Test handling of OpenAI client creation failures."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                # Simulate OpenAI client failure
                mock_openai.side_effect = Exception("OpenAI service unavailable")

                manager = LLMManager(config)

                with pytest.raises(Exception, match="OpenAI service unavailable"):
                    manager.create_llm()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])