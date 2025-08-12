"""LLM service module for AI-powered compliance analysis."""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from wct.errors import WCTError

logger = logging.getLogger(__name__)


class LLMServiceError(WCTError):
    """Base exception for LLM service related errors."""

    pass


class LLMConfigurationError(LLMServiceError):
    """Exception raised when LLM service is misconfigured."""

    pass


class LLMConnectionError(LLMServiceError):
    """Exception raised when LLM service connection fails."""

    pass


class AnthropicLLMService:
    """Service for interacting with Anthropic's Claude models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using Anthropic's Claude models through the LangChain framework.
    """

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        """Initialise the Anthropic LLM service.

        Args:
            model_name: The Anthropic model to use (will use ANTHROPIC_MODEL env var or default to claude-sonnet-4-20250514)
            api_key: Anthropic API key (will use ANTHROPIC_API_KEY env var if not provided)

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment
        """
        # Logger is available at module level

        # Get model name from parameter, environment, or default
        self.model_name = (
            model_name or os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-4-20250514"
        )

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or provide api_key parameter."
            )

        self._llm = None
        logger.info(f"Initialised Anthropic LLM service with model: {self.model_name}")

    def _get_llm(self):
        """Get or create the LangChain LLM instance.

        Returns:
            LangChain ChatAnthropic instance

        Raises:
            LLMConnectionError: If API key is not available
        """
        if self._llm is None:
            if not self.api_key:
                raise LLMConnectionError("API key is required but not available")

            self._llm = ChatAnthropic(
                model_name=self.model_name,
                api_key=SecretStr(self.api_key),
                temperature=0,  # Consistent responses for compliance analysis
                max_tokens_to_sample=8000,  # Adjust as needed for response length
                timeout=300,  # Increased timeout for LLM requests
                stop=None,  # Stop sequences for clean output
            )
            logger.debug("Created LangChain ChatAnthropic instance")

        return self._llm

    def test_connection(self) -> dict[str, Any]:
        """Test connection to Anthropic API.

        Returns:
            Dictionary with connection test results

        Raises:
            LLMConnectionError: If connection test fails
        """
        try:
            logger.info("Testing connection to Anthropic API...")

            llm = self._get_llm()

            # Simple test message
            test_prompt = (
                "Respond with 'Hello from Claude' to confirm the connection is working."
            )

            response = llm.invoke(test_prompt)
            response_text = str(response.content).strip()

            logger.info("Connection test successful")

            return {
                "status": "success",
                "model": self.model_name,
                "response": response_text,
                "response_length": len(response_text),
            }

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise LLMConnectionError(f"Failed to connect to Anthropic API: {e}") from e

    def analyse_data(self, text: str, analysis_prompt: str) -> str:
        """Analyse text using the LLM with a custom prompt.

        Args:
            text: The text content to analyse
            analysis_prompt: The prompt/instructions for analysis

        Returns:
            LLM analysis response as string

        Raises:
            LLMConnectionError: If LLM request fails
        """
        try:
            logger.debug(f"Analysing text (length: {len(text)} chars)")

            llm = self._get_llm()

            # Combine the analysis prompt with the text
            full_prompt = f"{analysis_prompt}\n\nText to analyse:\n{text}"

            response = llm.invoke(full_prompt)
            result = str(response.content).strip()

            logger.debug(
                f"LLM analysis completed (response length: {len(result)} chars)"
            )

            return result

        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            raise LLMConnectionError(f"LLM text analysis failed: {e}") from e


class LLMServiceFactory:
    """Factory for creating LLM service instances."""

    @staticmethod
    def create_anthropic_service(
        model_name: str | None = None, api_key: str | None = None
    ) -> AnthropicLLMService:
        """Create an Anthropic LLM service instance.

        Args:
            model_name: The Anthropic model to use (uses ANTHROPIC_MODEL env var or default if not provided)
            api_key: Optional API key (uses ANTHROPIC_API_KEY env var if not provided)

        Returns:
            Configured AnthropicLLMService instance
        """
        return AnthropicLLMService(model_name=model_name, api_key=api_key)
