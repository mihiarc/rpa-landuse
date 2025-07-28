"""LLM management functionality extracted from monolithic agent class."""

import os
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from rich.console import Console

from landuse.config.landuse_config import LanduseConfig
from landuse.exceptions import APIKeyError, LLMError


class LLMManager:
    """
    Manages LLM creation and configuration.
    
    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles model selection, API key validation, and LLM instantiation.
    """

    def __init__(self, config: Optional[LanduseConfig] = None, console: Optional[Console] = None):
        """Initialize LLM manager with configuration."""
        self.config = config or LanduseConfig()
        self.console = console or Console()

    def create_llm(self) -> BaseChatModel:
        """
        Create LLM instance based on configuration using factory pattern.
        
        Returns:
            Configured LLM instance
            
        Raises:
            ValueError: If required API keys are missing
        """
        model_name = self.config.model_name
        
        self.console.print(f"[blue]Initializing LLM: {model_name}[/blue]")

        if "claude" in model_name.lower():
            return self._create_anthropic_llm(model_name)
        else:
            return self._create_openai_llm(model_name)

    def _create_anthropic_llm(self, model_name: str) -> ChatAnthropic:
        """Create Anthropic Claude LLM instance."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.console.print(f"[dim]Using Anthropic API key: {self._mask_api_key(api_key)}[/dim]")
        
        if not api_key:
            raise APIKeyError("ANTHROPIC_API_KEY environment variable is required for Claude models", model_name)

        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def _create_openai_llm(self, model_name: str) -> ChatOpenAI:
        """Create OpenAI LLM instance."""
        api_key = os.getenv('OPENAI_API_KEY')
        self.console.print(f"[dim]Using OpenAI API key: {self._mask_api_key(api_key)}[/dim]")
        
        if not api_key:
            raise APIKeyError("OPENAI_API_KEY environment variable is required for OpenAI models", model_name)

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def _mask_api_key(self, api_key: Optional[str]) -> str:
        """
        Safely mask API key for logging purposes.
        
        Args:
            api_key: The API key to mask
            
        Returns:
            Masked API key string
        """
        if not api_key:
            return "NOT_SET"
        return f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"