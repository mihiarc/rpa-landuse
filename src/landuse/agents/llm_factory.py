"""Factory for creating LLM instances with consistent configuration."""

import os
from typing import Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from landuse.config.landuse_config import LanduseConfig


class LLMFactory:
    """Factory class for creating LLM instances following 2025 best practices."""

    @staticmethod
    def create_llm(
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        config: Optional[LanduseConfig] = None
    ) -> BaseChatModel:
        """
        Create an LLM instance based on model name and configuration.

        Args:
            model_name: The model to use (e.g., 'gpt-4o-mini', 'claude-3-haiku-20240307')
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            config: LanduseConfig instance (if provided, overrides other params)

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If required API keys are missing
        """
        # Use config if provided, otherwise use individual params
        if config:
            model_name = model_name or config.model_name
            temperature = temperature or config.temperature
            max_tokens = max_tokens or config.max_tokens
        else:
            # Load config for API keys
            config = LanduseConfig()
            model_name = model_name or config.model_name
            temperature = temperature or config.temperature
            max_tokens = max_tokens or config.max_tokens

        # Create OpenAI LLM
        return LLMFactory._create_openai_llm(
            model_name, temperature, max_tokens, config
        )

    @staticmethod
    def _create_openai_llm(
        model_name: str,
        temperature: float,
        max_tokens: int,
        config: LanduseConfig
    ) -> ChatOpenAI:
        """Create an OpenAI LLM instance."""
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for OpenAI models. "
                "Please set it in your .env file or environment."
            )

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def get_supported_models() -> dict[str, list[str]]:
        """Get list of supported models by provider."""
        return {
            "openai": [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
            ]
        }

    @staticmethod
    def mask_api_key(key: Optional[str]) -> str:
        """Mask an API key for safe logging."""
        if not key:
            return "NOT_SET"
        if len(key) <= 12:
            return "***"
        return f"{key[:8]}...{key[-4:]}"
