"""
Compatibility layer for old agent imports.
This file provides backward compatibility during the migration period.
"""

import warnings
from .agent import LanduseAgent


class BaseLanduseAgent(LanduseAgent):
    """Compatibility wrapper for BaseLanduseAgent"""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "BaseLanduseAgent is deprecated. Use LanduseAgent instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)


class LanduseNaturalLanguageAgent(LanduseAgent):
    """Compatibility wrapper for LanduseNaturalLanguageAgent"""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "LanduseNaturalLanguageAgent is deprecated. Use LanduseAgent instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)


class LangGraphMapAgent(LanduseAgent):
    """Compatibility wrapper for LangGraphMapAgent"""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "LangGraphMapAgent is deprecated. Use LanduseAgent with enable_maps=True instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Force enable maps for compatibility
        kwargs['enable_maps'] = True
        super().__init__(*args, **kwargs)


# Factory functions for compatibility
def create_natural_language_agent(**kwargs):
    """
    Create a landuse agent (for backward compatibility).
    
    This function now always creates the new unified LanduseAgent.
    The use_langgraph parameter is ignored as we only have LangGraph now.
    """
    kwargs.pop('use_langgraph', None)  # Remove deprecated parameter
    return LanduseAgent(**kwargs)


def create_map_agent(**kwargs):
    """
    Create a map-enabled landuse agent (for backward compatibility).
    
    This function creates a LanduseAgent with map capabilities enabled.
    """
    kwargs['enable_maps'] = True
    return LanduseAgent(**kwargs)