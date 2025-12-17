"""Test the centralized prompts module."""

import pytest

from landuse.agents.prompts import (
    SYSTEM_PROMPT_BASE,
    get_system_prompt,
)


class TestSystemPrompt:
    """Test the base system prompt."""

    def test_base_prompt_content(self):
        """Test that base prompt contains expected content."""
        assert "land use analytics expert" in SYSTEM_PROMPT_BASE
        assert "RPA Assessment database" in SYSTEM_PROMPT_BASE
        assert "Land use categories:" in SYSTEM_PROMPT_BASE
        assert "DATABASE SCHEMA:" in SYSTEM_PROMPT_BASE
        assert "{schema_info}" in SYSTEM_PROMPT_BASE

    def test_base_prompt_sections(self):
        """Test that base prompt has all required sections."""
        assert "KEY CONTEXT:" in SYSTEM_PROMPT_BASE
        assert "WHEN ANSWERING QUESTIONS" in SYSTEM_PROMPT_BASE
        assert "ALWAYS CONSIDER:" in SYSTEM_PROMPT_BASE
        assert "DEFAULT ASSUMPTIONS" in SYSTEM_PROMPT_BASE
        assert "QUERY PATTERNS:" in SYSTEM_PROMPT_BASE
        assert "TELL THE USER YOUR ASSUMPTIONS" in SYSTEM_PROMPT_BASE


class TestGetSystemPrompt:
    """Test the get_system_prompt function."""

    def test_standard_prompt(self):
        """Test standard prompt generation."""
        prompt = get_system_prompt(
            include_maps=False, analysis_style="standard", domain_focus=None, schema_info="TEST_SCHEMA"
        )

        assert "land use analytics expert" in prompt
        assert "TEST_SCHEMA" in prompt
        # Should return just the base prompt now
        assert prompt == SYSTEM_PROMPT_BASE.format(schema_info="TEST_SCHEMA")

    def test_prompt_with_schema(self):
        """Test that schema info is properly inserted."""
        test_schema = "CUSTOM_SCHEMA_INFO"
        prompt = get_system_prompt(schema_info=test_schema)

        assert test_schema in prompt
        assert "{schema_info}" not in prompt  # Should be replaced

    def test_prompt_parameters_ignored(self):
        """Test that additional parameters are ignored (since functionality was removed)."""
        # All these should return the same base prompt
        prompt1 = get_system_prompt(
            include_maps=True, analysis_style="detailed", domain_focus="climate", schema_info="TEST"
        )

        prompt2 = get_system_prompt(
            include_maps=False, analysis_style="standard", domain_focus=None, schema_info="TEST"
        )

        # Both should be identical (just base prompt with schema)
        assert prompt1 == prompt2
        assert prompt1 == SYSTEM_PROMPT_BASE.format(schema_info="TEST")
