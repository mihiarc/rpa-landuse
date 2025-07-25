"""Test the centralized prompts module."""

import pytest

from landuse.agents.prompts import (
    get_system_prompt,
    create_custom_prompt,
    PromptVariations,
    SYSTEM_PROMPT_BASE,
    MAP_GENERATION_PROMPT,
    DETAILED_ANALYSIS_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    AGRICULTURAL_FOCUS_PROMPT,
    CLIMATE_FOCUS_PROMPT,
    URBAN_PLANNING_PROMPT
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
        assert "WHEN ANSWERING QUESTIONS:" in SYSTEM_PROMPT_BASE
        assert "ALWAYS CONSIDER:" in SYSTEM_PROMPT_BASE
        assert "DEFAULT ASSUMPTIONS" in SYSTEM_PROMPT_BASE
        assert "QUERY PATTERNS:" in SYSTEM_PROMPT_BASE


class TestGetSystemPrompt:
    """Test the get_system_prompt function."""
    
    def test_standard_prompt(self):
        """Test standard prompt generation."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="standard",
            domain_focus=None,
            schema_info="TEST_SCHEMA"
        )
        
        assert "land use analytics expert" in prompt
        assert "TEST_SCHEMA" in prompt
        assert MAP_GENERATION_PROMPT not in prompt
        assert DETAILED_ANALYSIS_PROMPT not in prompt
        assert EXECUTIVE_SUMMARY_PROMPT not in prompt
    
    def test_detailed_analysis_prompt(self):
        """Test detailed analysis style."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="detailed",
            domain_focus=None,
            schema_info="TEST_SCHEMA"
        )
        
        assert "DETAILED ANALYSIS MODE:" in prompt
        assert "summary statistics" in prompt
        assert "confidence intervals" in prompt
    
    def test_executive_summary_prompt(self):
        """Test executive summary style."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="executive",
            domain_focus=None,
            schema_info="TEST_SCHEMA"
        )
        
        assert "EXECUTIVE SUMMARY MODE:" in prompt
        assert "key finding in one sentence" in prompt
        assert "3-5 key points max" in prompt
    
    def test_domain_focus_agricultural(self):
        """Test agricultural domain focus."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="standard",
            domain_focus="agricultural",
            schema_info="TEST_SCHEMA"
        )
        
        assert "AGRICULTURAL ANALYSIS FOCUS:" in prompt
        assert "Crop and Pasture transitions" in prompt
        assert "food security implications" in prompt
    
    def test_domain_focus_climate(self):
        """Test climate domain focus."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="standard",
            domain_focus="climate",
            schema_info="TEST_SCHEMA"
        )
        
        assert "CLIMATE SCENARIO FOCUS:" in prompt
        assert "RCP4.5 vs RCP8.5" in prompt
        assert "SSP pathways" in prompt
    
    def test_domain_focus_urban(self):
        """Test urban planning domain focus."""
        prompt = get_system_prompt(
            include_maps=False,
            analysis_style="standard",
            domain_focus="urban",
            schema_info="TEST_SCHEMA"
        )
        
        assert "URBAN PLANNING FOCUS:" in prompt
        assert "Urban expansion patterns" in prompt
        assert "sprawl vs densification" in prompt
    
    def test_map_generation_included(self):
        """Test including map generation instructions."""
        prompt = get_system_prompt(
            include_maps=True,
            analysis_style="standard",
            domain_focus=None,
            schema_info="TEST_SCHEMA"
        )
        
        assert "MAP GENERATION:" in prompt
        assert "choropleth maps" in prompt
        assert "create_map tool" in prompt
    
    def test_combined_features(self):
        """Test combining multiple features."""
        prompt = get_system_prompt(
            include_maps=True,
            analysis_style="detailed",
            domain_focus="climate",
            schema_info="TEST_SCHEMA"
        )
        
        # Should have all components
        assert "land use analytics expert" in prompt
        assert "DETAILED ANALYSIS MODE:" in prompt
        assert "CLIMATE SCENARIO FOCUS:" in prompt
        assert "MAP GENERATION:" in prompt


class TestPromptVariations:
    """Test pre-configured prompt variations."""
    
    def test_research_analyst(self):
        """Test research analyst prompt."""
        prompt = PromptVariations.research_analyst("TEST_SCHEMA")
        
        assert "TEST_SCHEMA" in prompt
        assert "DETAILED ANALYSIS MODE:" in prompt
        assert "MAP GENERATION:" in prompt
    
    def test_policy_maker(self):
        """Test policy maker prompt."""
        prompt = PromptVariations.policy_maker("TEST_SCHEMA")
        
        assert "TEST_SCHEMA" in prompt
        assert "EXECUTIVE SUMMARY MODE:" in prompt
        assert "CLIMATE SCENARIO FOCUS:" in prompt
        assert "MAP GENERATION:" in prompt
    
    def test_agricultural_analyst(self):
        """Test agricultural analyst prompt."""
        prompt = PromptVariations.agricultural_analyst("TEST_SCHEMA")
        
        assert "TEST_SCHEMA" in prompt
        assert "DETAILED ANALYSIS MODE:" in prompt
        assert "AGRICULTURAL ANALYSIS FOCUS:" in prompt
        assert "MAP GENERATION:" in prompt
    
    def test_urban_planner(self):
        """Test urban planner prompt."""
        prompt = PromptVariations.urban_planner("TEST_SCHEMA")
        
        assert "TEST_SCHEMA" in prompt
        assert "URBAN PLANNING FOCUS:" in prompt
        assert "MAP GENERATION:" in prompt


class TestCustomPrompt:
    """Test custom prompt creation."""
    
    def test_create_custom_prompt(self):
        """Test creating a fully custom prompt."""
        prompt = create_custom_prompt(
            expertise_area="water resource management",
            expertise_description="Understanding water-land use connections",
            analysis_approach="1. Consider watersheds\n2. Analyze runoff",
            response_guidelines="1. Mention water quality\n2. Note stormwater",
            schema_info="TEST_SCHEMA"
        )
        
        assert "water resource management" in prompt
        assert "Understanding water-land use connections" in prompt
        assert "Consider watersheds" in prompt
        assert "Mention water quality" in prompt
        assert "TEST_SCHEMA" in prompt
    
    def test_custom_prompt_template_structure(self):
        """Test that custom prompt has correct structure."""
        prompt = create_custom_prompt(
            expertise_area="test area",
            expertise_description="test description",
            analysis_approach="test approach",
            response_guidelines="test guidelines",
            schema_info="TEST_SCHEMA"
        )
        
        assert "DATABASE SCHEMA:" in prompt
        assert "YOUR EXPERTISE:" in prompt
        assert "ANALYSIS APPROACH:" in prompt
        assert "When answering questions:" in prompt