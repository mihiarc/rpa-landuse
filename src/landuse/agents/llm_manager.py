"""LLM management functionality extracted from monolithic agent class."""

import os
from typing import Optional

import boto3
from langchain_aws import ChatBedrock
from langchain_anthropic import ChatAnthropic
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
        # model_name = "gpt-4o-mini"
        model_name = "bedrock"
        self.console.print(f"[blue]Initializing LLM: {model_name}[/blue]")

        if "bedrock" == model_name.lower():
            return self._create_bedrock_llm(model_name)
        else:
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

    def _create_bedrock_llm(self, model_name: str) -> 'ChatBedrock':
        """
        Create AWS Bedrock LLM instance with boto3 configuration.
        
        Args:
            model_name: The Bedrock model name (e.g., 'amazon.nova-micro-v1:0', 'anthropic.claude-3-sonnet-20240229-v1:0')
            
        Returns:
            Configured ChatBedrock instance
            
        Raises:
            LLMError: If Bedrock dependencies are not available or AWS credentials are missing
        """

        # Get AWS configuration from environment variables
        aws_region = os.getenv('AWS_DEFAULT_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))  # Default to us-east-1
        aws_model = os.getenv('AWS_BEDROCK_MODEL', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        try:
            # Create boto3 session
            session = boto3.Session(region_name=aws_region)
            
            # Create bedrock-runtime client with session
            bedrock_client = session.client(
                service_name='bedrock-runtime',
                region_name=aws_region
            )
            
            # Create ChatBedrock instance with both client and region
            bedrock_llm = ChatBedrock(
                client=bedrock_client,
                model_id=aws_model,
                region_name=aws_region,  # Explicitly pass region to ChatBedrock
                model_kwargs={
                    "max_tokens": 4000,
                    "temperature": 0.1,
                }
            )
            
            self.console.print(f"[green]✓ AWS Bedrock LLM initialized with model: {aws_model}[/green]")
            return bedrock_llm
            
        except Exception as e:
            error_msg = f"Failed to initialize AWS Bedrock client: {str(e)}"
            self.console.print(f"[red]✗ {error_msg}[/red]")
            raise LLMError(error_msg)

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
        model_name = self.config.model_name

        if "claude" in model_name.lower():
            return os.getenv('ANTHROPIC_API_KEY') is not None
        elif "bedrock" == model_name.lower():
            pass
            # For Bedrock, check if AWS credentials are available
            # return (os.getenv('AWS_ACCESS_KEY_ID') is not None and 
            #         os.getenv('AWS_SECRET_ACCESS_KEY') is not None)
        else:
            return os.getenv('OPENAI_API_KEY') is not None
