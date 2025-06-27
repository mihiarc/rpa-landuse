#!/usr/bin/env python3
"""
Migration wrappers to help transition from LangChain to LangGraph agents.
These wrappers allow existing code to work with minimal changes.
"""

import warnings
from typing import Optional, Union

from ..config import LanduseConfig
from ..models import AgentConfig
from .landuse_natural_language_agent_v2 import LanduseNaturalLanguageAgent as NewNaturalLanguageAgent
from .langgraph_map_agent_v2 import LangGraphMapAgent as NewMapAgent


def create_natural_language_agent(
    db_path: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    verbose: bool = False,
    config: Optional[Union[AgentConfig, LanduseConfig]] = None,
    use_langgraph: bool = True
) -> Union['LanduseNaturalLanguageAgent', NewNaturalLanguageAgent]:
    """
    Factory function to create a natural language agent.
    
    Args:
        use_langgraph: If True, creates the new LangGraph agent. If False, creates the old agent.
        Other args are passed to the agent constructor.
    
    Returns:
        Agent instance (old or new based on use_langgraph)
    """
    if use_langgraph:
        # Convert parameters to LanduseConfig if needed
        if config is None:
            overrides = {}
            if db_path:
                overrides['db_path'] = db_path
            if model_name:
                overrides['model_name'] = model_name
            if temperature is not None:
                overrides['temperature'] = temperature
            if max_tokens is not None:
                overrides['max_tokens'] = max_tokens
            if verbose:
                overrides['verbose'] = verbose
            
            config = LanduseConfig.for_agent_type('basic', **overrides)
        
        return NewNaturalLanguageAgent(config)
    else:
        # Import old agent only if needed
        from .agent import LanduseAgent
        warnings.warn(
            "Using legacy LanduseNaturalLanguageAgent. Please migrate to LangGraph version.",
            DeprecationWarning,
            stacklevel=2
        )
        return LanduseAgent(db_path, model_name, temperature, max_tokens, verbose, config)


def create_map_agent(
    config: Optional[LanduseConfig] = None,
    use_langgraph: bool = True
) -> Union['LangGraphMapAgent', NewMapAgent]:
    """
    Factory function to create a map-enabled agent.
    
    Args:
        config: Configuration for the agent
        use_langgraph: If True, creates the new unified agent. If False, creates the old agent.
    
    Returns:
        Agent instance (old or new based on use_langgraph)
    """
    if use_langgraph:
        if config is None:
            config = LanduseConfig.for_agent_type('map')
        return NewMapAgent(config)
    else:
        # Import old agent only if needed
        from .langgraph_map_agent import LangGraphMapAgent
        warnings.warn(
            "Using legacy LangGraphMapAgent. Please migrate to the unified LangGraph version.",
            DeprecationWarning,
            stacklevel=2
        )
        return LanduseAgent(enable_maps=True, config)


# Environment variable to control migration
import os
FORCE_LEGACY_AGENTS = os.getenv('LANDUSE_FORCE_LEGACY_AGENTS', 'false').lower() == 'true'


def get_default_agent_type() -> str:
    """Get the default agent type based on environment settings"""
    if FORCE_LEGACY_AGENTS:
        warnings.warn(
            "LANDUSE_FORCE_LEGACY_AGENTS is set. Using legacy agents. "
            "Please test with new agents and remove this setting.",
            DeprecationWarning
        )
        return 'legacy'
    return 'langgraph'