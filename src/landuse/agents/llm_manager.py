"""LLM management functionality extracted from monolithic agent class."""

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from rich.console import Console

from landuse.core.app_config import AppConfig, LLMConfig
from landuse.core.interfaces import LLMInterface
from landuse.exceptions import APIKeyError, LLMError
from landuse.infrastructure.logging import get_logger
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
        self._logger = get_logger('llm')

    @time_llm_operation("create_llm", track_tokens=False)
    def create_llm(self) -> BaseChatModel:
        """
        Create LLM instance based on configuration using factory pattern.

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If required API keys are missing
        """
        model_name = self.config.llm.model_name
        self._logger.info("Creating LLM", model=model_name)
        self.console.print(f"[blue]Initializing LLM: {model_name}[/blue]")
        return self._create_openai_llm(model_name)

    def _create_openai_llm(self, model_name: str) -> ChatOpenAI:
        """Create OpenAI LLM instance."""
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            self._logger.error("OpenAI API key not configured", model=model_name)
            raise APIKeyError("OPENAI_API_KEY environment variable is required for OpenAI models", model_name)

        self._logger.debug(
            "OpenAI LLM configured",
            model=model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens
        )
        self.console.print("[dim]Using OpenAI API key: ✓ Configured[/dim]")

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )

    def get_api_key_status(self) -> str:
        """
        Get API key configuration status without revealing any key content.

        Returns:
            Status string indicating if API key is configured
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "Not configured"
        return "Configured"

    def get_model_name(self) -> str:
        """Get the current model name."""
        return self.config.llm.model_name

    def validate_api_key(self) -> bool:
        """Validate API key is available and valid."""
        return os.getenv('OPENAI_API_KEY') is not None
