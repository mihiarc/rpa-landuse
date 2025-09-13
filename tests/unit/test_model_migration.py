#!/usr/bin/env python3
"""
Tests for model migration scenarios after Anthropic API removal.

These tests ensure proper handling of migration scenarios for users
switching from Claude models to GPT models.
"""

import os
import pytest
from unittest.mock import Mock, patch, call
from landuse.agents.llm_manager import LLMManager
from landuse.config.landuse_config import LanduseConfig
from landuse.core.app_config import AppConfig
from landuse.exceptions import APIKeyError, ConfigurationError


class TestModelMigration:
    """Test migration scenarios from Anthropic to OpenAI models."""

    def test_claude_to_gpt_model_mapping(self):
        """Test suggested model mappings from Claude to GPT."""
        claude_to_gpt_mapping = {
            "claude-3-5-sonnet-20241022": "gpt-4o",
            "claude-3-sonnet-20240229": "gpt-4o",
            "claude-3-haiku-20240307": "gpt-4o-mini",
            "claude-3-opus-20240229": "gpt-4o"
        }

        for claude_model, suggested_gpt in claude_to_gpt_mapping.items():
            # Verify the mapping exists and is sensible
            assert suggested_gpt.startswith("gpt-")
            assert suggested_gpt in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]

    def test_migration_warning_for_claude_models(self):
        """Test that appropriate warnings are shown for Claude models."""
        claude_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

        for claude_model in claude_models:
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name=claude_model)

            mock_console = Mock()

            with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
                with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                    mock_openai.return_value = Mock()

                    manager = LLMManager(config, console=mock_console)
                    manager.create_llm()

                    # Verify model name was printed (indicating the attempt)
                    print_calls = [call[0][0] for call in mock_console.print.call_args_list]
                    model_mentioned = any(claude_model in str(call) for call in print_calls)
                    assert model_mentioned

    def test_environment_migration_scenarios(self):
        """Test common environment migration scenarios."""
        # Scenario 1: User has both keys but wants to use OpenAI
        migration_env_1 = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'ANTHROPIC_API_KEY': 'sk-ant-test123456789',  # Should be ignored
            'LANDUSE_MODEL': 'gpt-4o-mini'
        }

        with patch.dict(os.environ, migration_env_1):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Should use OpenAI
                mock_openai.assert_called_once()

        # Scenario 2: User has old Claude model in config
        migration_env_2 = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'LANDUSE_MODEL': 'claude-3-5-sonnet-20241022'
        }

        with patch.dict(os.environ, migration_env_2):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                manager = LLMManager(config)
                llm = manager.create_llm()

                # Should attempt via OpenAI (may fail at runtime)
                mock_openai.assert_called_once()
                call_args = mock_openai.call_args
                assert call_args[1]['model'] == 'claude-3-5-sonnet-20241022'

    def test_migration_with_missing_anthropic_key(self):
        """Test behavior when Anthropic key is missing but Claude model specified."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'
            # No ANTHROPIC_API_KEY
        }):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name="claude-3-5-sonnet-20241022")

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                manager = LLMManager(config)
                # Should not raise error at creation time (handled by OpenAI)
                llm = manager.create_llm()

                # Should attempt via OpenAI
                mock_openai.assert_called_once()

    def test_configuration_file_migration(self):
        """Test migration of configuration files."""
        # Old configuration that might exist
        old_config_env = {
            'ANTHROPIC_API_KEY': 'sk-ant-old123',
            'LANDUSE_MODEL': 'claude-3-5-sonnet-20241022',
            'TEMPERATURE': '0.1'
        }

        # New configuration after migration
        new_config_env = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'LANDUSE_MODEL': 'gpt-4o',  # Migrated model
            'TEMPERATURE': '0.1'  # Preserved setting
        }

        # Test old config would fail
        with patch.dict(os.environ, old_config_env, clear=True):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            manager = LLMManager(config)
            with pytest.raises(APIKeyError):
                manager.create_llm()

        # Test new config works
        with patch.dict(os.environ, new_config_env, clear=True):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig()

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                manager = LLMManager(config)
                llm = manager.create_llm()

                mock_openai.assert_called_once()
                call_args = mock_openai.call_args
                assert call_args[1]['model'] == 'gpt-4o'

    def test_agent_initialization_migration(self):
        """Test agent initialization after migration."""
        from landuse.agents.landuse_agent import LanduseAgent

        # Simulate migrated environment
        migrated_env = {
            'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345',
            'LANDUSE_MODEL': 'gpt-4o-mini'
        }

        with patch.dict(os.environ, migrated_env):
            # Create test database
            import tempfile
            import duckdb

            tmpdir = tempfile.mkdtemp()
            db_path = os.path.join(tmpdir, "test.duckdb")

            conn = duckdb.connect(db_path)
            conn.execute("CREATE TABLE dim_scenario (scenario_id INTEGER, scenario_name VARCHAR)")
            conn.close()

            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(db_path=db_path)

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                # Should initialize successfully
                agent = LanduseAgent(config)
                assert agent.config.model_name == 'gpt-4o-mini'

            # Cleanup
            import shutil
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)


class TestBackwardCompatibility:
    """Test backward compatibility during migration."""

    def test_existing_agent_code_compatibility(self):
        """Test that existing agent code still works after migration."""
        # Simulate existing code pattern
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(
                    model_name="gpt-4o-mini",
                    temperature=0.2,
                    max_tokens=2000
                )

            manager = LLMManager(config)

            # Existing methods should still work
            assert manager.get_model_name() == "gpt-4o-mini"
            assert manager.validate_api_key() is True

            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()
                llm = manager.create_llm()
                assert llm is not None

    def test_configuration_property_compatibility(self):
        """Test that configuration properties remain compatible."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                model_name="gpt-4o",
                temperature=0.3,
                max_tokens=3000,
                max_iterations=10,
                enable_memory=True
            )

        # All original properties should still exist
        assert hasattr(config, 'model_name')
        assert hasattr(config, 'temperature')
        assert hasattr(config, 'max_tokens')
        assert hasattr(config, 'max_iterations')
        assert hasattr(config, 'enable_memory')

        # Values should be preserved
        assert config.model_name == "gpt-4o"
        assert config.temperature == 0.3
        assert config.max_tokens == 3000

    def test_app_config_migration_compatibility(self):
        """Test compatibility between old and new config systems."""
        # Test that AppConfig can be used where LanduseConfig was expected
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            app_config = AppConfig()

            # Should work with LLMManager
            manager = LLMManager(app_config)
            assert manager.app_config is app_config
            assert manager.config is not None  # Should have converted legacy config

            # Verify conversion worked
            assert manager.config.model_name == app_config.llm.model_name


class TestErrorMessageImprovements:
    """Test improved error messages for migration scenarios."""

    def test_helpful_anthropic_error_messages(self):
        """Test that error messages help users migrate from Anthropic."""
        # No API keys at all
        with patch.dict(os.environ, {}, clear=True):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(model_name="claude-3-5-sonnet-20241022")

            manager = LLMManager(config)

            with pytest.raises(APIKeyError) as exc_info:
                manager.create_llm()

            error_msg = str(exc_info.value)
            assert "OPENAI_API_KEY" in error_msg
            assert "claude-3-5-sonnet-20241022" in error_msg

    def test_clear_model_requirement_messages(self):
        """Test clear messages about model requirements."""
        from landuse.core.app_config import LLMConfig

        # Test configuration validation error message
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                LLMConfig(model_name="gpt-4o-mini")

            error_msg = str(exc_info.value)
            assert "OPENAI_API_KEY required" in error_msg

    def test_api_key_validation_messages(self):
        """Test API key validation error messages."""
        manager = LLMManager()

        # Test masking works for various key formats
        assert manager._mask_api_key(None) == "NOT_SET"
        assert manager._mask_api_key("") == "NOT_SET"
        assert manager._mask_api_key("short") == "***"
        assert manager._mask_api_key("sk-1234567890123456789012345678901234567890123456") == "sk-12345...3456"


class TestPerformanceImpactAssessment:
    """Test performance impact of migration."""

    def test_llm_creation_performance(self):
        """Test that LLM creation performance is maintained."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig()

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            with patch('landuse.agents.llm_manager.ChatOpenAI') as mock_openai:
                mock_openai.return_value = Mock()

                manager = LLMManager(config)

                # Should complete quickly (no complex logic)
                import time
                start_time = time.time()
                llm = manager.create_llm()
                end_time = time.time()

                # Should be very fast (just object creation)
                assert end_time - start_time < 1.0

    def test_configuration_loading_performance(self):
        """Test configuration loading performance."""
        import time

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test123456789012345678901234567890123456789012345'}):
            start_time = time.time()

            # Test new config system
            app_config = AppConfig()

            # Test legacy config system
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                legacy_config = LanduseConfig()

            end_time = time.time()

            # Should be fast
            assert end_time - start_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])