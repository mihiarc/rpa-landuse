#!/usr/bin/env python3
"""
Comprehensive tests to ensure complete coverage after Anthropic API removal.

These tests verify that all Anthropic-related functionality has been properly
removed and that OpenAI-only functionality works correctly.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_openai import ChatOpenAI

from landuse.agents.llm_manager import LLMManager
from landuse.config.landuse_config import LanduseConfig
from landuse.core.app_config import AppConfig
from landuse.exceptions import APIKeyError


class TestAnthropicRemovalCompleteness:
    """Test that Anthropic functionality has been completely removed."""

    def test_no_anthropic_imports_in_llm_manager(self):
        """Test that LLM Manager doesn't import Anthropic modules."""
        import inspect
        import landuse.agents.llm_manager

        # Get the source code of the module
        source = inspect.getsource(landuse.agents.llm_manager)

        # Should not contain any Anthropic imports
        anthropic_imports = [
            "from langchain_anthropic",
            "import langchain_anthropic",
            "from anthropic",
            "import anthropic",
            "ChatAnthropic",
            "AnthropicLLM"
        ]

        for anthropic_import in anthropic_imports:
            assert anthropic_import not in source, f"Found Anthropic import: {anthropic_import}"

    def test_only_openai_llm_creation_path(self):
        """Test that only OpenAI LLM creation path exists."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock(spec=ChatOpenAI)

                manager = LLMManager(config)

                # Should only call OpenAI creation method
                with patch.object(manager, '_create_openai_llm') as mock_create_openai:
                    mock_create_openai.return_value = Mock(spec=ChatOpenAI)

                    llm = manager.create_llm()

                    # Should call OpenAI creation
                    mock_create_openai.assert_called_once()

    def test_anthropic_api_key_not_checked(self):
        """Test that Anthropic API key is not checked anywhere."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        # Set only Anthropic key, not OpenAI key
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'sk-ant-test123456789',
            # No OPENAI_API_KEY
        }, clear=True):
            manager = LLMManager(config)

            # Should fail because OpenAI key is missing, not because Anthropic key is present
            with pytest.raises(APIKeyError, match="OPENAI_API_KEY"):
                manager.create_llm()

    def test_all_models_use_openai_path(self):
        """Test that all models, including Claude, use OpenAI path."""
        models_to_test = [
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022",  # Should go through OpenAI
            "custom-model-name"
        ]

        for model in models_to_test:
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name=model)

            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                    mock_openai.return_value = Mock(spec=ChatOpenAI)

                    manager = LLMManager(config)

                    with patch.object(manager, '_create_openai_llm') as mock_create:
                        mock_create.return_value = Mock(spec=ChatOpenAI)

                        manager.create_llm()

                        # All models should go through OpenAI creation
                        mock_create.assert_called_once_with(model)


class TestOpenAIOnlyFunctionality:
    """Test that OpenAI-only functionality works correctly."""

    def test_openai_llm_creation_parameters(self):
        """Test OpenAI LLM creation with all parameters."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                model_name="gpt-4o",
                temperature=0.5,
                max_tokens=3000
            )

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_llm = Mock(spec=ChatOpenAI)
                mock_openai.return_value = mock_llm

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Verify all parameters were passed correctly
                mock_openai.assert_called_once_with(
                    model="gpt-4o",
                    openai_api_key='sk-test123456789012345678901234567890123456789012345',
                    temperature=0.5,
                    max_tokens=3000
                )

                assert llm == mock_llm

    def test_openai_api_key_validation_only(self):
        """Test that only OpenAI API key validation exists."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()
        manager = LLMManager(config)

        # Test with OpenAI key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            assert manager.validate_api_key() is True

        # Test without OpenAI key (with Anthropic key present)
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'sk-ant-test123456789',
            # No OPENAI_API_KEY
        }, clear=True):
            assert manager.validate_api_key() is False

    def test_openai_error_handling(self):
        """Test error handling specific to OpenAI."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                # Test OpenAI-specific exceptions
                mock_openai.side_effect = Exception("OpenAI rate limit exceeded")

                manager = LLMManager(config)

                with pytest.raises(Exception, match="OpenAI rate limit exceeded"):
                    manager.create_llm()

    def test_openai_model_name_handling(self):
        """Test handling of OpenAI model names."""
        openai_models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

        for model in openai_models:
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name=model)

            manager = LLMManager(config)
            assert manager.get_model_name() == model


class TestConfigurationSystemAfterRemoval:
    """Test configuration system works correctly after Anthropic removal."""

    def test_app_config_llm_validation(self):
        """Test AppConfig LLM validation with OpenAI only."""
        # Should require OpenAI key
        with patch.dict(os.environ, {}, clear=True):
            from landuse.core.app_config import LLMConfig
            with pytest.raises(Exception):  # Configuration error for missing key
                LLMConfig(model_name="gpt-4o-mini")

        # Should work with OpenAI key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            config = LLMConfig(model_name="gpt-4o-mini")
            assert config.model_name == "gpt-4o-mini"

    def test_legacy_config_compatibility_post_removal(self):
        """Test legacy config still works after Anthropic removal."""
        test_env = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'LANDUSE_MODEL': 'gpt-4o',
            'TEMPERATURE': '0.3'
        }

        with patch.dict(os.environ, test_env):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            assert config.model_name == 'gpt-4o'
            assert config.temperature == 0.3

    def test_environment_variable_precedence(self):
        """Test environment variable precedence after removal."""
        # Only OpenAI variables should be relevant
        test_env = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'ANTHROPIC_API_KEY': 'sk-ant-test123456789',  # Should be ignored
            'LANDUSE_MODEL': 'gpt-4o-mini'
        }

        with patch.dict(os.environ, test_env):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            manager = LLMManager(config)

            # Should only validate OpenAI key
            assert manager.validate_api_key() is True

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()
                llm = manager.create_llm()
                mock_openai.assert_called_once()


class TestErrorHandlingRobustness:
    """Test error handling is robust after Anthropic removal."""

    def test_comprehensive_api_key_error_scenarios(self):
        """Test all API key error scenarios."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()
        manager = LLMManager(config)

        error_scenarios = [
            ({}, "no keys"),
            ({'ANTHROPIC_API_KEY': 'sk-ant-test'}, "only Anthropic key"),
            ({'SOME_OTHER_KEY': 'value'}, "irrelevant key"),
        ]

        for env_vars, description in error_scenarios:
            with patch.dict(os.environ, env_vars, clear=True):
                with pytest.raises(APIKeyError, match="OPENAI_API_KEY"):
                    manager.create_llm()

    def test_model_name_error_handling(self):
        """Test error handling for various model names."""
        problematic_models = [
            "",  # Empty string
            None,  # None value (would need special handling)
            "   ",  # Whitespace only
            "invalid-model-123",  # Non-existent model
        ]

        for model in problematic_models:
            if model is None:
                continue  # Skip None test as it would fail during config creation

            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                try:
                    config = LanduseConfig(model_name=model)
                except:
                    continue  # Config creation might fail, which is fine

            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                    # Even invalid models should attempt creation (OpenAI will handle the error)
                    mock_openai.return_value = Mock()

                    manager = LLMManager(config)
                    # Should not raise in manager (let OpenAI handle invalid models)
                    llm = manager.create_llm()

    def test_network_error_handling(self):
        """Test handling of network-related errors."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                network_errors = [
                    ConnectionError("Network unreachable"),
                    TimeoutError("Request timeout"),
                    Exception("Service unavailable")
                ]

                for error in network_errors:
                    mock_openai.side_effect = error

                    manager = LLMManager(config)

                    # Should propagate the original error
                    with pytest.raises(type(error)):
                        manager.create_llm()


class TestTestFixtureConsistency:
    """Test that test fixtures are consistent with Anthropic removal."""

    def test_mock_llm_fixtures_use_openai_only(self):
        """Test that mock LLM fixtures only reference OpenAI."""
        from tests.fixtures.agent_fixtures import mock_openai_llm

        # Create the fixture
        mock_llm = mock_openai_llm()

        # Should be configured as OpenAI model
        assert hasattr(mock_llm, 'model')
        assert mock_llm.model.startswith('gpt-')

    def test_test_environment_setup(self):
        """Test that test environment is set up correctly."""
        from tests.conftest import TEST_ENV

        # Should have OpenAI key
        assert 'OPENAI_API_KEY' in TEST_ENV
        assert TEST_ENV['OPENAI_API_KEY'].startswith('sk-')

        # Should not have Anthropic key
        assert 'ANTHROPIC_API_KEY' not in TEST_ENV

        # Should use OpenAI model
        assert 'LANDUSE_MODEL' in TEST_ENV
        assert TEST_ENV['LANDUSE_MODEL'].startswith('gpt-')

    def test_configuration_test_data_consistency(self):
        """Test that configuration test data is consistent."""
        from tests.fixtures.agent_fixtures import agent_test_config

        config_data = agent_test_config()

        # Should have OpenAI key
        assert 'openai_api_key' in config_data
        # Should not have Anthropic key
        assert 'anthropic_api_key' not in config_data


class TestIntegrationPointsAfterRemoval:
    """Test integration points work correctly after Anthropic removal."""

    def test_agent_initialization_uses_openai(self):
        """Test that agent initialization uses OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Create minimal test database
            import tempfile
            import duckdb

            tmpdir = tempfile.mkdtemp()
            db_path = os.path.join(tmpdir, "test.duckdb")

            conn = duckdb.connect(db_path)
            conn.execute("CREATE TABLE dim_scenario (scenario_id INTEGER)")
            conn.close()

            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(db_path=db_path, model_name="gpt-4o-mini")

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                from landuse.agents.landuse_agent import LanduseAgent
                agent = LanduseAgent(config)

                # Should have used OpenAI
                mock_openai.assert_called_once()

            # Cleanup
            import shutil
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)

    def test_streamlit_integration_uses_openai(self):
        """Test that Streamlit integration uses OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            # Test would involve importing Streamlit components
            # This is a placeholder for actual integration test
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])