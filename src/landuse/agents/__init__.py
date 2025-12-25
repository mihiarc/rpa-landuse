# Agents package initialization
"""
RPA Land Use Analytics Agent.

Simplified LangChain tool-calling agent for querying USDA Forest Service
RPA Assessment land use projections.
"""

# Import the primary agent
from .landuse_agent import LandUseAgent

# Import constants and utilities for backward compatibility
from .constants import (
    CHAT_EXAMPLES,
    CLIMATE_MODELS,
    DB_CONFIG,
    DEFAULT_ASSUMPTIONS,
    MODEL_CONFIG,
    QUERY_EXAMPLES,
    RESPONSE_SECTIONS,
    RPA_SCENARIOS,
    SCHEMA_INFO_TEMPLATE,
    STATE_NAMES,
)
from .formatting import (
    clean_sql_query,
    create_examples_panel,
    create_welcome_panel,
    format_error,
    format_query_results,
    format_response,
    format_row_values,
    get_summary_statistics,
)

# Import prompts system
from .prompts import SYSTEM_PROMPT, get_system_prompt

# Import tools
from .tools import TOOLS

__all__ = [
    # Agent class
    "LandUseAgent",
    # Tools
    "TOOLS",
    # Constants
    "STATE_NAMES",
    "SCHEMA_INFO_TEMPLATE",
    "DEFAULT_ASSUMPTIONS",
    "QUERY_EXAMPLES",
    "CHAT_EXAMPLES",
    "RESPONSE_SECTIONS",
    "DB_CONFIG",
    "MODEL_CONFIG",
    "RPA_SCENARIOS",
    "CLIMATE_MODELS",
    # Formatting utilities
    "clean_sql_query",
    "format_query_results",
    "format_row_values",
    "get_summary_statistics",
    "create_welcome_panel",
    "create_examples_panel",
    "format_error",
    "format_response",
    # Prompts
    "SYSTEM_PROMPT",
    "get_system_prompt",
]
