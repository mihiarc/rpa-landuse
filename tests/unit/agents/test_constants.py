#!/usr/bin/env python3
"""
Tests for the constants module
"""

import pytest

from landuse.agents.constants import (
    CHAT_EXAMPLES,
    DB_CONFIG,
    DEFAULT_ASSUMPTIONS,
    MODEL_CONFIG,
    QUERY_EXAMPLES,
    RATE_LIMIT_CONFIG,
    RESPONSE_SECTIONS,
    SCHEMA_INFO_TEMPLATE,
    STATE_NAMES,
)


def test_state_names_mapping():
    """Test state names mapping has expected values"""
    # Test some key states
    assert STATE_NAMES['06'] == 'California'
    assert STATE_NAMES['48'] == 'Texas'
    assert STATE_NAMES['36'] == 'New York'
    assert STATE_NAMES['12'] == 'Florida'

    # Verify all state codes are 2 digits
    for code in STATE_NAMES:
        assert len(code) == 2
        assert code.isdigit()

    # Verify we have reasonable number of states
    assert len(STATE_NAMES) >= 50  # At least 50 states


def test_schema_info_template():
    """Test schema info template contains expected content"""
    assert "RPA Land Use Transitions Database Schema" in SCHEMA_INFO_TEMPLATE
    assert "fact_landuse_transitions" in SCHEMA_INFO_TEMPLATE
    assert "dim_scenario" in SCHEMA_INFO_TEMPLATE
    assert "dim_time" in SCHEMA_INFO_TEMPLATE
    assert "dim_geography_enhanced" in SCHEMA_INFO_TEMPLATE
    assert "dim_landuse" in SCHEMA_INFO_TEMPLATE

    # Check for important fields
    assert "transition_id" in SCHEMA_INFO_TEMPLATE
    assert "scenario_id" in SCHEMA_INFO_TEMPLATE
    assert "acres" in SCHEMA_INFO_TEMPLATE
    assert "rcp45" in SCHEMA_INFO_TEMPLATE
    assert "rcp85" in SCHEMA_INFO_TEMPLATE


def test_default_assumptions():
    """Test default assumptions dictionary"""
    assert "scenarios" in DEFAULT_ASSUMPTIONS
    assert "time_period" in DEFAULT_ASSUMPTIONS
    assert "geographic_scope" in DEFAULT_ASSUMPTIONS
    assert "transition_type" in DEFAULT_ASSUMPTIONS

    # Check values contain expected content
    assert "20 RPA scenarios" in DEFAULT_ASSUMPTIONS["scenarios"]
    assert "2012-2070" in DEFAULT_ASSUMPTIONS["time_period"]
    assert "U.S. counties" in DEFAULT_ASSUMPTIONS["geographic_scope"]
    assert "change" in DEFAULT_ASSUMPTIONS["transition_type"]


def test_query_examples():
    """Test query examples dictionary"""
    # Check expected keys exist
    assert "agricultural_loss" in QUERY_EXAMPLES
    assert "urbanization" in QUERY_EXAMPLES
    assert "climate_comparison" in QUERY_EXAMPLES
    assert "time_series" in QUERY_EXAMPLES

    # Check each example is valid SQL
    for _name, sql in QUERY_EXAMPLES.items():
        assert "SELECT" in sql.upper()
        assert "FROM" in sql.upper()
        assert "fact_landuse_transitions" in sql
        assert "JOIN" in sql


def test_chat_examples():
    """Test chat examples list"""
    assert isinstance(CHAT_EXAMPLES, list)
    assert len(CHAT_EXAMPLES) > 0

    # Check some expected examples
    example_keywords = ["agricultural", "urban", "forest", "state"]
    found_keywords = []
    for example in CHAT_EXAMPLES:
        for keyword in example_keywords:
            if keyword.lower() in example.lower():
                found_keywords.append(keyword)

    assert len(set(found_keywords)) >= 3  # At least 3 different topics


def test_response_sections():
    """Test response section headers"""
    assert "assumptions" in RESPONSE_SECTIONS
    assert "findings" in RESPONSE_SECTIONS
    assert "interpretation" in RESPONSE_SECTIONS
    assert "followup" in RESPONSE_SECTIONS

    # Check they contain emoji and formatting
    for _section, header in RESPONSE_SECTIONS.items():
        assert "**" in header  # Bold formatting
        assert any(ord(c) > 127 for c in header)  # Contains emoji


def test_db_config():
    """Test database configuration defaults"""
    assert "default_path" in DB_CONFIG
    assert "max_query_limit" in DB_CONFIG
    assert "default_display_limit" in DB_CONFIG
    assert "read_only" in DB_CONFIG

    # Check values
    assert DB_CONFIG["default_path"] == "data/processed/landuse_analytics.duckdb"
    assert DB_CONFIG["max_query_limit"] == 1000
    assert DB_CONFIG["default_display_limit"] == 50
    assert DB_CONFIG["read_only"] is True


def test_model_config():
    """Test model configuration defaults"""
    assert "default_temperature" in MODEL_CONFIG
    assert "default_max_tokens" in MODEL_CONFIG
    assert "max_iterations" in MODEL_CONFIG
    assert "default_openai_model" in MODEL_CONFIG
    assert "default_anthropic_model" in MODEL_CONFIG

    # Check values
    assert MODEL_CONFIG["default_temperature"] == 0.1
    assert MODEL_CONFIG["default_max_tokens"] == 4000
    assert MODEL_CONFIG["max_iterations"] == 5  # Updated default
    assert MODEL_CONFIG["max_execution_time"] == 120  # New field
    assert "gpt" in MODEL_CONFIG["default_openai_model"]
    assert "claude" in MODEL_CONFIG["default_anthropic_model"]


def test_rate_limit_config():
    """Test rate limit configuration structure and defaults"""
    # Check structure
    assert isinstance(RATE_LIMIT_CONFIG, dict)
    assert "max_calls" in RATE_LIMIT_CONFIG
    assert "time_window" in RATE_LIMIT_CONFIG

    # Check values
    assert RATE_LIMIT_CONFIG["max_calls"] == 60
    assert RATE_LIMIT_CONFIG["time_window"] == 60
