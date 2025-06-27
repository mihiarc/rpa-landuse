#!/usr/bin/env python3
"""
Compatibility wrapper for BaseLanduseAgent
Provides backward compatibility while transitioning to LangGraph architecture
"""

import warnings
from typing import Optional, Union
from pathlib import Path

from ..config import AgentConfig, LanduseConfig
from .langgraph_base_agent import BaseLangGraphAgent


class BaseLanduseAgent(BaseLangGraphAgent):
    """
    Compatibility wrapper for the old BaseLanduseAgent.
    
    This class maintains the old API while using the new LangGraph implementation.
    It will be deprecated in a future version.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        verbose: bool = False,
        config: Optional[Union[AgentConfig, LanduseConfig]] = None
    ):
        """Initialize with backward-compatible parameters"""
        warnings.warn(
            "BaseLanduseAgent is deprecated. Please use BaseLangGraphAgent instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Convert old-style parameters to LanduseConfig
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
        elif isinstance(config, AgentConfig):
            # Convert AgentConfig to LanduseConfig
            config = LanduseConfig(
                db_path=str(config.db_path),
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                max_iterations=config.max_iterations,
                max_execution_time=config.max_execution_time,
                max_query_rows=config.max_query_rows,
                default_display_limit=config.default_display_limit,
                rate_limit_calls=config.rate_limit_calls,
                rate_limit_window=config.rate_limit_window,
                verbose=verbose
            )
        
        # Initialize the LangGraph base class
        super().__init__(config)
        
        # Maintain backward compatibility for these attributes
        if hasattr(self, 'config') and isinstance(self.config, LanduseConfig):
            # Create a backward-compatible config attribute
            self.config = AgentConfig(
                db_path=Path(self.config.db_path),
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                max_iterations=self.config.max_iterations,
                max_execution_time=self.config.max_execution_time,
                max_query_rows=self.config.max_query_rows,
                default_display_limit=self.config.default_display_limit,
                rate_limit_calls=self.config.rate_limit_calls,
                rate_limit_window=self.config.rate_limit_window
            )