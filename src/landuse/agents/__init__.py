# Agents package initialization

# Import the unified agent
from .agent import LanduseAgent

# Import constants and utilities for backward compatibility
from .constants import (
    CHAT_EXAMPLES,
    DB_CONFIG,
    DEFAULT_ASSUMPTIONS,
    MODEL_CONFIG,
    QUERY_EXAMPLES,
    RESPONSE_SECTIONS,
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
from .prompts import get_system_prompt, create_custom_prompt, PromptVariations

__all__ = [
    # Main agent class
    'LanduseAgent',
    
    # Constants
    'STATE_NAMES', 'SCHEMA_INFO_TEMPLATE', 'DEFAULT_ASSUMPTIONS',
    'QUERY_EXAMPLES', 'CHAT_EXAMPLES', 'RESPONSE_SECTIONS',
    'DB_CONFIG', 'MODEL_CONFIG',

    # Formatting utilities
    'clean_sql_query', 'format_query_results', 'format_row_values',
    'get_summary_statistics', 'create_welcome_panel', 'create_examples_panel',
    'format_error', 'format_response',
    
    # Prompts
    'get_system_prompt', 'create_custom_prompt', 'PromptVariations'
]