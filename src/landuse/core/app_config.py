"""Unified application configuration with dependency injection support."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from landuse.exceptions import ConfigurationError

T = TypeVar('T', bound='AppConfig')


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    
    path: str = Field(
        default='data/processed/landuse_analytics.duckdb',
        description="Path to DuckDB database file"
    )
    read_only: bool = Field(
        default=True,
        description="Open database in read-only mode for security"
    )
    connection_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Database connection timeout in seconds"
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of database connections in pool"
    )
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Default cache TTL for query results in seconds"
    )

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate database path exists."""
        path = Path(v)
        if not path.exists() and not v.startswith(':memory:'):
            raise ConfigurationError(f"Database file not found: {v}")
        return v


class LLMConfig(BaseModel):
    """LLM configuration settings."""
    
    model_name: str = Field(
        default='gpt-4o-mini',
        description="Name of the LLM model to use"
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses"
    )
    max_tokens: int = Field(
        default=4000,
        ge=100,
        le=32000,
        description="Maximum tokens for LLM responses"
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=600,
        description="LLM request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for LLM calls"
    )

    @field_validator('model_name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name and check API key availability."""
        if v.lower().startswith('claude'):
            if not os.getenv('ANTHROPIC_API_KEY'):
                raise ConfigurationError("ANTHROPIC_API_KEY required for Claude models")
        elif v.lower().startswith('gpt') or v.lower().startswith('o1'):
            if not os.getenv('OPENAI_API_KEY'):
                raise ConfigurationError("OPENAI_API_KEY required for OpenAI models")
        return v


class AgentConfig(BaseModel):
    """Agent behavior configuration."""
    
    max_iterations: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum iterations for agent execution"
    )
    max_execution_time: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Maximum execution time in seconds"
    )
    max_query_rows: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum rows returned by queries"
    )
    default_display_limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Default number of rows to display"
    )
    enable_memory: bool = Field(
        default=True,
        description="Enable conversation memory and checkpointing"
    )
    conversation_history_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of conversation messages to keep"
    )


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    
    enable_sql_validation: bool = Field(
        default=True,
        description="Enable SQL injection validation"
    )
    strict_table_validation: bool = Field(
        default=True,
        description="Enable strict table name validation using allowlists"
    )
    rate_limit_calls: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum API calls per time window"
    )
    rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Rate limiting time window in seconds"
    )
    log_security_events: bool = Field(
        default=True,
        description="Log security validation events"
    )


class FeatureConfig(BaseModel):
    """Feature toggle configuration."""
    
    enable_map_generation: bool = Field(
        default=True,
        description="Enable map generation capabilities"
    )
    enable_knowledge_base: bool = Field(
        default=False,
        description="Enable RPA knowledge base integration"
    )
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses"
    )
    enable_graph_mode: bool = Field(
        default=True,
        description="Enable LangGraph workflow mode"
    )
    map_output_dir: str = Field(
        default='maps/agent_generated',
        description="Directory for generated maps"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(
        default='INFO',
        description="Logging level"
    )
    enable_debug: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    enable_performance_logging: bool = Field(
        default=False,
        description="Enable performance logging"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path (None for console only)"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ConfigurationError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class AppConfig(BaseSettings):
    """
    Unified application configuration with dependency injection support.
    
    This configuration system provides:
    - Type-safe configuration with Pydantic validation  
    - Environment variable integration
    - Dependency injection ready structure
    - Component-specific configuration sections
    - Validation and error handling
    """
    
    model_config = SettingsConfigDict(
        env_prefix='LANDUSE_',
        env_nested_delimiter='__',
        case_sensitive=False,
        extra='forbid'
    )
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Application metadata
    app_name: str = Field(default='RPA Land Use Analytics')
    app_version: str = Field(default='2025.1.0')
    environment: str = Field(default='development')

    @model_validator(mode='after')
    def validate_configuration(self) -> 'AppConfig':
        """Validate configuration consistency and create required directories."""
        # Create map output directory if map generation is enabled
        if self.features.enable_map_generation:
            Path(self.features.map_output_dir).mkdir(parents=True, exist_ok=True)
            
        # Validate logging configuration
        if self.logging.log_file:
            log_path = Path(self.logging.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
        return self

    @classmethod
    def from_env(cls: Type[T], **overrides: Any) -> T:
        """
        Create configuration from environment variables with overrides.
        
        Args:
            **overrides: Configuration overrides
            
        Returns:
            AppConfig instance
        """
        # Load from environment
        config = cls()
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                # Handle nested overrides (e.g., database__path)
                if '__' in key:
                    section, field = key.split('__', 1)
                    if hasattr(config, section):
                        section_config = getattr(config, section)
                        if hasattr(section_config, field):
                            setattr(section_config, field, value)
                        else:
                            raise ConfigurationError(f"Unknown field: {section}.{field}")
                    else:
                        raise ConfigurationError(f"Unknown section: {section}")
                else:
                    raise ConfigurationError(f"Unknown configuration parameter: {key}")
        
        return config

    @classmethod
    def for_environment(cls: Type[T], env: str, **overrides: Any) -> T:
        """
        Create configuration for specific environment.
        
        Args:
            env: Environment name ('development', 'testing', 'production')
            **overrides: Additional overrides
            
        Returns:
            AppConfig instance
        """
        env_configs = {
            'development': {
                'logging__level': 'DEBUG',
                'logging__enable_debug': True,
                'security__log_security_events': True,
                'agent__max_execution_time': 300
            },
            'testing': {
                'database__path': ':memory:',
                'logging__level': 'WARNING',
                'security__rate_limit_calls': 1000,
                'features__enable_map_generation': False
            },
            'production': {
                'logging__level': 'INFO',
                'logging__enable_performance_logging': True,
                'security__strict_table_validation': True,
                'agent__max_execution_time': 60
            }
        }
        
        base_config = env_configs.get(env, {})
        base_config.update(overrides)
        base_config['environment'] = env
        
        return cls.from_env(**base_config)

    def get_legacy_config(self) -> Dict[str, Any]:
        """
        Convert to legacy LanduseConfig format for backward compatibility.
        
        Returns:
            Dictionary matching old configuration structure
        """
        return {
            # Database
            'db_path': self.database.path,
            
            # LLM
            'model_name': self.llm.model_name,
            'temperature': self.llm.temperature,
            'max_tokens': self.llm.max_tokens,
            
            # Agent
            'max_iterations': self.agent.max_iterations,
            'max_execution_time': self.agent.max_execution_time,
            'max_query_rows': self.agent.max_query_rows,
            'default_display_limit': self.agent.default_display_limit,
            'enable_memory': self.agent.enable_memory,
            
            # Features
            'enable_map_generation': self.features.enable_map_generation,
            'enable_knowledge_base': self.features.enable_knowledge_base,
            'map_output_dir': self.features.map_output_dir,
            
            # Logging
            'debug': self.logging.enable_debug,
            'verbose': self.logging.level == 'DEBUG',
            
            # Security/Rate Limiting
            'rate_limit_calls': self.security.rate_limit_calls,
            'rate_limit_window': self.security.rate_limit_window
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return self.model_dump()

    def mask_sensitive_fields(self) -> Dict[str, Any]:
        """Get configuration dictionary with sensitive fields masked."""
        config_dict = self.to_dict()
        
        # API keys are in environment, not config, but mask if present
        for key in config_dict:
            if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower():
                if isinstance(config_dict[key], str) and len(config_dict[key]) > 8:
                    config_dict[key] = f"{config_dict[key][:4]}...{config_dict[key][-4:]}"
                    
        return config_dict

    def __repr__(self) -> str:
        """Clean string representation without sensitive data."""
        masked_config = self.mask_sensitive_fields()
        return f"{self.__class__.__name__}({masked_config})"


# Convenience functions for common configurations
def get_development_config(**overrides: Any) -> AppConfig:
    """Get configuration for development environment."""
    return AppConfig.for_environment('development', **overrides)


def get_testing_config(**overrides: Any) -> AppConfig:
    """Get configuration for testing environment."""
    return AppConfig.for_environment('testing', **overrides)


def get_production_config(**overrides: Any) -> AppConfig:
    """Get configuration for production environment."""
    return AppConfig.for_environment('production', **overrides)


# Legacy compatibility function
def create_legacy_config(**overrides: Any) -> Dict[str, Any]:
    """Create legacy configuration format for backward compatibility."""
    config = AppConfig.from_env(**overrides)
    return config.get_legacy_config()