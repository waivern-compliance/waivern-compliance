"""Tests for LLMProvider protocol.

Verifies the protocol contract is usable and documents what a conforming
implementation looks like.
"""

from pydantic import BaseModel

from waivern_llm.providers import LLMProvider


class MockResponse(BaseModel):
    """Mock response model for testing."""

    content: str


class MockProvider:
    """Mock provider that satisfies LLMProvider protocol."""

    @property
    def model_name(self) -> str:
        return "mock-model"

    @property
    def context_window(self) -> int:
        return 100_000

    async def invoke_structured[R: BaseModel](
        self, prompt: str, response_model: type[R]
    ) -> R:
        return response_model.model_validate({"content": "mock response"})


class TestLLMProviderProtocol:
    """Tests for LLMProvider protocol compliance."""

    def test_mock_provider_satisfies_protocol(self) -> None:
        """A class with correct signatures should satisfy LLMProvider protocol."""
        provider = MockProvider()

        # Verify runtime protocol check
        assert isinstance(provider, LLMProvider)

        # Verify properties are accessible
        assert provider.model_name == "mock-model"
        assert provider.context_window == 100_000
