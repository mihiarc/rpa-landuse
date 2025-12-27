# Agents package initialization
"""
RPA Land Use Analytics Agent.

Simplified LangChain tool-calling agent for querying USDA Forest Service
RPA Assessment land use projections.
"""

# Import the primary agent
from .landuse_agent import LandUseAgent

# Import prompts system
from .prompts import SYSTEM_PROMPT, get_system_prompt

# Import tools
from .tools import TOOLS

__all__ = [
    # Agent class
    "LandUseAgent",
    # Tools
    "TOOLS",
    # Prompts
    "SYSTEM_PROMPT",
    "get_system_prompt",
]
