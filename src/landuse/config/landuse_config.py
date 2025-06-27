#!/usr/bin/env python3
"""
Unified Configuration System for Landuse Agents
Provides clean dataclass-based configuration for all agent types
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class LanduseConfig:
    """
    Unified configuration for all landuse agents.

    This configuration system provides a clean, type-safe way to configure
    all agent types while maintaining backward compatibility.
    """

    # Database Configuration
    db_path: str = field(
        default_factory=lambda: os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
    )

    # Model Configuration
    model_name: str = field(
        default_factory=lambda: os.getenv('LANDUSE_MODEL', 'claude-3-5-sonnet-20241022')
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv('TEMPERATURE', '0.2'))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv('MAX_TOKENS', '4000'))
    )

    # Agent Behavior Configuration
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_MAX_ITERATIONS', '8'))
    )
    max_execution_time: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120'))
    )
    max_query_rows: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_MAX_QUERY_ROWS', '1000'))
    )
    default_display_limit: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_DEFAULT_DISPLAY_LIMIT', '50'))
    )

    # Memory and State Management
    enable_memory: bool = field(
        default_factory=lambda: os.getenv('LANDUSE_ENABLE_MEMORY', 'true').lower() == 'true'
    )

    # Logging and Debugging
    verbose: bool = field(
        default_factory=lambda: os.getenv('VERBOSE', 'false').lower() == 'true'
    )
    debug: bool = field(
        default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true'
    )

    # Rate Limiting (for API calls)
    rate_limit_calls: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_RATE_LIMIT_CALLS', '60'))
    )
    rate_limit_window: int = field(
        default_factory=lambda: int(os.getenv('LANDUSE_RATE_LIMIT_WINDOW', '60'))
    )

    # Map Generation Configuration (for map-enabled agents)
    map_output_dir: str = field(
        default_factory=lambda: os.getenv('LANDUSE_MAP_OUTPUT_DIR', 'maps/agent_generated')
    )
    enable_map_generation: bool = field(
        default_factory=lambda: os.getenv('LANDUSE_ENABLE_MAPS', 'true').lower() == 'true'
    )

    # Streamlit Configuration
    streamlit_cache_ttl: int = field(
        default_factory=lambda: int(os.getenv('STREAMLIT_CACHE_TTL', '300'))
    )

    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Validate database path
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        # Validate model configuration
        if self.model_name.startswith("claude"):
            if not os.getenv('ANTHROPIC_API_KEY'):
                raise ValueError("ANTHROPIC_API_KEY required for Claude models")
        else:
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OPENAI_API_KEY required for OpenAI models")

        # Validate numeric ranges
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

        if self.max_tokens < 100:
            raise ValueError("max_tokens must be at least 100")

        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if self.max_query_rows < 1:
            raise ValueError("max_query_rows must be at least 1")

        # Create map output directory if enabled
        if self.enable_map_generation:
            Path(self.map_output_dir).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, **overrides) -> 'LanduseConfig':
        """
        Create configuration from environment variables with optional overrides.

        Args:
            **overrides: Keyword arguments to override default values

        Returns:
            LanduseConfig instance
        """
        config = cls()

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")

        return config

    @classmethod
    def for_agent_type(cls, agent_type: str, **overrides) -> 'LanduseConfig':
        """
        Create configuration optimized for specific agent type.

        Args:
            agent_type: Type of agent ('basic', 'map', 'streamlit')
            **overrides: Additional overrides

        Returns:
            LanduseConfig instance
        """
        # Agent type specific defaults
        type_defaults = {
            'basic': {
                'enable_map_generation': False,
                'max_iterations': 5,
                'verbose': False
            },
            'map': {
                'enable_map_generation': True,
                'max_iterations': 8,
                'verbose': True
            },
            'streamlit': {
                'enable_map_generation': True,
                'enable_memory': False,  # Streamlit handles its own state
                'verbose': False,
                'streamlit_cache_ttl': 300
            }
        }

        # Get defaults for agent type
        defaults = type_defaults.get(agent_type, {})

        # Merge with user overrides
        defaults.update(overrides)

        return cls.from_env(**defaults)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }

    def __repr__(self) -> str:
        """Clean string representation for debugging"""
        masked_keys = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']

        # Create a copy of the dict with masked sensitive values
        config_dict = self.to_dict()

        # Mask API keys if they would be visible in repr
        api_key_anthropic = os.getenv('ANTHROPIC_API_KEY', '')
        api_key_openai = os.getenv('OPENAI_API_KEY', '')

        repr_lines = [f"{self.__class__.__name__}("]
        for key, value in config_dict.items():
            repr_lines.append(f"    {key}={value!r},")
        repr_lines.append(")")

        return "\n".join(repr_lines)

# Convenience functions for common use cases
def get_basic_config(**overrides) -> LanduseConfig:
    """Get configuration for basic agents"""
    return LanduseConfig.for_agent_type('basic', **overrides)

def get_map_config(**overrides) -> LanduseConfig:
    """Get configuration for map-enabled agents"""
    return LanduseConfig.for_agent_type('map', **overrides)

def get_streamlit_config(**overrides) -> LanduseConfig:
    """Get configuration for Streamlit applications"""
    return LanduseConfig.for_agent_type('streamlit', **overrides)

# Legacy compatibility - these match the old LandGraphConfig field names
def create_langgraph_config(**overrides) -> LanduseConfig:
    """
    Create LanduseConfig with LangGraph-style field names for backward compatibility.
    Maps old field names to new unified configuration.
    """
    # Map old field names to new ones if needed
    field_mapping: dict[str, str] = {
        # Old LandGraphConfig fields -> New LanduseConfig fields
        # (currently they're the same, but this allows for future changes)
    }

    # Apply field mapping
    mapped_overrides = {}
    for key, value in overrides.items():
        mapped_key = field_mapping.get(key, key)
        mapped_overrides[mapped_key] = value

    return LanduseConfig.for_agent_type('map', **mapped_overrides)
