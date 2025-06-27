# Agents package initialization

# Import both old and new base classes for compatibility
from .base_agent import BaseLanduseAgent
from .langgraph_base_agent import BaseLangGraphAgent
from .constants import (
    STATE_NAMES, SCHEMA_INFO_TEMPLATE, DEFAULT_ASSUMPTIONS,
    QUERY_EXAMPLES, CHAT_EXAMPLES, RESPONSE_SECTIONS,
    DB_CONFIG, MODEL_CONFIG
)
from .formatting import (
    clean_sql_query, format_query_results, format_row_values,
    get_summary_statistics, create_welcome_panel, create_examples_panel,
    format_error, format_response
)

# Import migration helpers
from .migration_wrappers import create_natural_language_agent, create_map_agent

__all__ = [
    # Base classes
    'BaseLanduseAgent',  # Legacy - will be deprecated
    'BaseLangGraphAgent',  # New LangGraph base
    
    # Constants
    'STATE_NAMES', 'SCHEMA_INFO_TEMPLATE', 'DEFAULT_ASSUMPTIONS',
    'QUERY_EXAMPLES', 'CHAT_EXAMPLES', 'RESPONSE_SECTIONS',
    'DB_CONFIG', 'MODEL_CONFIG',
    
    # Formatting utilities
    'clean_sql_query', 'format_query_results', 'format_row_values',
    'get_summary_statistics', 'create_welcome_panel', 'create_examples_panel',
    'format_error', 'format_response',
    
    # Migration helpers
    'create_natural_language_agent', 'create_map_agent'
]