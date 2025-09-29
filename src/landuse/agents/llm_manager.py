"""LLM management functionality extracted from monolithic agent class."""

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from rich.console import Console

from landuse.core.app_config import AppConfig, LLMConfig
from landuse.core.interfaces import LLMInterface
from landuse.exceptions import APIKeyError, LLMError
from landuse.infrastructure.performance import time_llm_operation


class LLMManager(LLMInterface):
    """
    Manages LLM creation and configuration.

    Extracted from the monolithic LanduseAgent class to follow Single Responsibility Principle.
    Handles model selection, API key validation, and LLM instantiation.
    Implements LLMInterface for dependency injection compatibility.
    """

    def __init__(self, config: Optional[AppConfig] = None, console: Optional[Console] = None):
        """Initialize LLM manager with configuration."""
        self.config = config or AppConfig()
        self.console = console or Console()

    @time_llm_operation("create_llm", track_tokens=False)
    def create_llm(self) -> BaseChatModel:
        """
        Create LLM instance based on configuration using factory pattern.

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If required API keys are missing
        """
        model_name = "gpt-4o-mini"
        self.console.print(f"[blue]Initializing LLM: {model_name}[/blue]")
        return self._create_openai_llm(model_name)

    def _create_openai_llm(self, model_name: str) -> ChatOpenAI:
        """Create OpenAI LLM instance."""
        api_key = os.getenv('OPENAI_API_KEY')
        self.console.print(f"[dim]Using OpenAI API key: {self._mask_api_key(api_key)}[/dim]")

        if not api_key:
            raise APIKeyError("OPENAI_API_KEY environment variable is required for OpenAI models", model_name)

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
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

    def get_model_name(self) -> str:
        """Get the current model name."""
        return "gpt-4o-mini"

    def validate_api_key(self) -> bool:
        """Validate API key is available and valid."""
        return os.getenv('OPENAI_API_KEY') is not None
