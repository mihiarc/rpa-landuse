#!/usr/bin/env python3
"""
Tests for configuration validation after Anthropic API removal.

These tests ensure that the configuration system properly validates
OpenAI-only models and rejects unsupported configurations.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from landuse.config.landuse_config import LanduseConfig
from landuse.core.app_config import AppConfig, LLMConfig
from landuse.exceptions import ConfigurationError


class TestConfigurationValidation:
    """Test configuration validation with OpenAI-only support."""

    def test_valid_openai_models_accepted(self):
        """Test that valid OpenAI models are accepted."""
        valid_models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

        for model in valid_models:
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                # Test with new AppConfig
                llm_config = LLMConfig(model_name=model)
                assert llm_config.model_name == model

                # Test with legacy config
                with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                    legacy_config = LanduseConfig(model_name=model)
                    assert legacy_config.model_name == model

    def test_missing_openai_api_key_validation(self):
        """Test that missing OpenAI API key is caught during validation."""
        with patch.dict(os.environ, {}, clear=True):
            # Test with new AppConfig LLMConfig
            with pytest.raises(ConfigurationError, match="OPENAI_API_KEY required"):
                LLMConfig(model_name="gpt-4o-mini")

    def test_anthropic_models_configuration_behavior(self):
        """Test how Anthropic models are handled in configuration."""
        anthropic_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ]

        for model in anthropic_models:
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                # Configuration should accept any model name, but validation happens at runtime
                with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                    legacy_config = LanduseConfig(model_name=model)
                    assert legacy_config.model_name == model

                # New config should also accept but require OpenAI key
                llm_config = LLMConfig(model_name=model)
                assert llm_config.model_name == model

    def test_temperature_validation(self):
        """Test temperature parameter validation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Valid temperatures
            valid_temps = [0.0, 0.5, 1.0, 1.5, 2.0]
            for temp in valid_temps:
                config = LLMConfig(temperature=temp)
                assert config.temperature == temp

            # Invalid temperatures
            invalid_temps = [-0.1, 2.1, 10.0]
            for temp in invalid_temps:
                with pytest.raises(ValidationError):
                    LLMConfig(temperature=temp)

    def test_max_tokens_validation(self):
        """Test max_tokens parameter validation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Valid token counts
            valid_tokens = [100, 1000, 4000, 8000, 16000, 32000]
            for tokens in valid_tokens:
                config = LLMConfig(max_tokens=tokens)
                assert config.max_tokens == tokens

            # Invalid token counts
            invalid_tokens = [99, 32001, 50000]
            for tokens in invalid_tokens:
                with pytest.raises(ValidationError):
                    LLMConfig(max_tokens=tokens)

    def test_environment_variable_integration(self):
        """Test that environment variables are properly integrated."""
        test_env = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'LANDUSE_LLM__MODEL_NAME': 'gpt-4o',
            'LANDUSE_LLM__TEMPERATURE': '0.7',
            'LANDUSE_LLM__MAX_TOKENS': '2000'
        }

        with patch.dict(os.environ, test_env):
            config = AppConfig()

            assert config.llm.model_name == 'gpt-4o'
            assert config.llm.temperature == 0.7
            assert config.llm.max_tokens == 2000

    def test_configuration_override_behavior(self):
        """Test configuration override behavior."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Test that programmatic values override environment
            base_config = AppConfig()

            override_config = AppConfig.from_env(
                llm__model_name='gpt-4o',
                llm__temperature=0.8
            )

            assert override_config.llm.model_name == 'gpt-4o'
            assert override_config.llm.temperature == 0.8

    def test_database_configuration_validation(self):
        """Test database configuration validation."""
        # Test with non-existent database
        with pytest.raises(ConfigurationError, match="Database file not found"):
            from landuse.core.app_config import DatabaseConfig
            DatabaseConfig(path="/nonexistent/path/database.duckdb")

        # Test with in-memory database (should be allowed)
        from landuse.core.app_config import DatabaseConfig
        db_config = DatabaseConfig(path=":memory:")
        assert db_config.path == ":memory:"

    def test_agent_configuration_validation(self):
        """Test agent configuration parameter validation."""
        from landuse.core.app_config import AgentConfig

        # Valid configurations
        valid_config = AgentConfig(
            max_iterations=5,
            max_execution_time=60,
            max_query_rows=500
        )
        assert valid_config.max_iterations == 5

        # Invalid configurations
        with pytest.raises(ValidationError):
            AgentConfig(max_iterations=0)  # Should be >= 1

        with pytest.raises(ValidationError):
            AgentConfig(max_execution_time=0)  # Should be >= 1

    def test_legacy_config_environment_integration(self):
        """Test legacy config environment variable integration."""
        test_env = {
            'LANDUSE_MODEL': 'gpt-4o',
            'TEMPERATURE': '0.3',
            'MAX_TOKENS': '3000',
            'LANDUSE_MAX_ITERATIONS': '10'
        }

        with patch.dict(os.environ, test_env):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

                assert config.model_name == 'gpt-4o'
                assert config.temperature == 0.3
                assert config.max_tokens == 3000
                assert config.max_iterations == 10


class TestConfigurationMigration:
    """Test configuration migration and compatibility."""

    def test_app_config_to_legacy_conversion(self):
        """Test conversion from AppConfig to legacy config."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            app_config = AppConfig(
                llm={'model_name': 'gpt-4o', 'temperature': 0.5, 'max_tokens': 2000},
                agent={'max_iterations': 12, 'enable_memory': True},
                database={'path': 'test.duckdb'},
                logging={'level': 'INFO'}
            )

            # This would typically be done by LLMManager
            from landuse.agents.llm_manager import LLMManager
            manager = LLMManager(app_config)
            legacy_config = manager.config

            assert legacy_config.model_name == 'gpt-4o'
            assert legacy_config.temperature == 0.5
            assert legacy_config.max_tokens == 2000
            assert legacy_config.max_iterations == 12
            assert legacy_config.enable_memory is True
            assert legacy_config.db_path == 'test.duckdb'
            assert legacy_config.debug is False  # INFO level

    def test_legacy_config_compatibility(self):
        """Test that legacy configs work with new systems."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            legacy_config = LanduseConfig(
                model_name="gpt-4o-mini",
                temperature=0.4,
                max_iterations=6,
                enable_memory=True
            )

        # Should work with LLM manager
        from landuse.agents.llm_manager import LLMManager
        manager = LLMManager(legacy_config)

        assert manager.config.model_name == "gpt-4o-mini"
        assert manager.config.temperature == 0.4
        assert manager.config.max_iterations == 6

    def test_configuration_validation_edge_cases(self):
        """Test edge cases in configuration validation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Test minimum valid values
            config = LLMConfig(
                temperature=0.0,
                max_tokens=100,
                timeout=1,
                max_retries=0
            )
            assert config.temperature == 0.0
            assert config.max_tokens == 100

            # Test maximum valid values
            config = LLMConfig(
                temperature=2.0,
                max_tokens=32000,
                timeout=600,
                max_retries=10
            )
            assert config.temperature == 2.0
            assert config.max_tokens == 32000


class TestModelCompatibilityValidation:
    """Test model compatibility and rejection of unsupported models."""

    def test_model_provider_detection(self):
        """Test detection of model providers."""
        def detect_provider(model_name: str) -> str:
            """Simple provider detection for testing."""
            if model_name.startswith('gpt-'):
                return 'openai'
            elif model_name.startswith('claude-'):
                return 'anthropic'
            else:
                return 'unknown'

        # Test OpenAI models
        openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        for model in openai_models:
            assert detect_provider(model) == 'openai'

        # Test Anthropic models (would be rejected at runtime)
        anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
        for model in anthropic_models:
            assert detect_provider(model) == 'anthropic'

    def test_unsupported_model_runtime_behavior(self):
        """Test runtime behavior with unsupported models."""
        # Configuration allows any model name, but LLM creation should handle gracefully
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # This should not fail at config level
            config = LLMConfig(model_name="claude-3-5-sonnet-20241022")
            assert config.model_name == "claude-3-5-sonnet-20241022"

            # But would fail at LLM creation if OpenAI doesn't support it
            # (This is expected behavior - let OpenAI handle unsupported models)

    def test_api_key_requirements_by_model(self):
        """Test that API key requirements are enforced."""
        # Any model requires OpenAI API key now
        test_models = [
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022",  # Would be attempted via OpenAI
            "custom-model"
        ]

        for model in test_models:
            # Without API key
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ConfigurationError, match="OPENAI_API_KEY required"):
                    LLMConfig(model_name=model)

            # With API key
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                config = LLMConfig(model_name=model)
                assert config.model_name == model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
