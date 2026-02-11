"""Model capabilities registry for LLM context and output token limits."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapabilities:
    """Immutable model capability data.

    Attributes:
        context_window: Maximum input context window size in tokens.
        max_output_tokens: Maximum output tokens the model can generate.
        temperature: Temperature setting for the model. Defaults to 0 for
            deterministic output. Some models (e.g. gpt-5-mini) only support
            their default temperature (1).

    """

    context_window: int
    max_output_tokens: int
    temperature: int = 0

    @classmethod
    def get(cls, model_name: str) -> "ModelCapabilities":
        """Get capabilities for a model with fuzzy matching.

        Uses substring matching to handle version suffixes in model names
        (e.g., "claude-sonnet-4-5-20251022" matches "claude-sonnet-4-5").

        Keys are checked longest-first to ensure more specific matches take
        precedence (e.g., "gpt-5.2" matches before "gpt-5").

        Args:
            model_name: The model name to look up.

        Returns:
            ModelCapabilities for the model, or defaults for unknown models.

        """
        model_lower = model_name.lower()
        # Sort by key length descending so more specific matches win
        for key in sorted(_MODEL_CAPABILITIES.keys(), key=len, reverse=True):
            if key in model_lower:
                return _MODEL_CAPABILITIES[key]
        return _DEFAULT_CAPABILITIES


_DEFAULT_CAPABILITIES = ModelCapabilities(
    context_window=128_000,
    max_output_tokens=16_000,
)

_MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    # Anthropic Claude 4.5 family
    "claude-opus-4-5": ModelCapabilities(200_000, 8192),
    "claude-sonnet-4-5": ModelCapabilities(200_000, 8192),
    "claude-haiku-4-5": ModelCapabilities(200_000, 8192),
    # Anthropic Claude 4 family
    "claude-opus-4": ModelCapabilities(200_000, 8192),
    "claude-sonnet-4": ModelCapabilities(200_000, 8192),
    "claude-haiku-4": ModelCapabilities(200_000, 8192),
    # OpenAI GPT-4 family
    "gpt-4o": ModelCapabilities(128_000, 16_384),
    "gpt-4o-mini": ModelCapabilities(128_000, 16_384),
    # OpenAI GPT-5 family (temperature=0 not supported)
    "gpt-5": ModelCapabilities(256_000, 16_384, temperature=1),
    "gpt-5-mini": ModelCapabilities(256_000, 16_384, temperature=1),
    "gpt-5.1": ModelCapabilities(256_000, 16_384, temperature=1),
    "gpt-5.2": ModelCapabilities(400_000, 16_384, temperature=1),
    "gpt-5.2-pro": ModelCapabilities(400_000, 16_384, temperature=1),
    "gpt-5-nano": ModelCapabilities(128_000, 16_384, temperature=1),
    # OpenAI o-series reasoning models (temperature=0 not supported)
    "o3": ModelCapabilities(200_000, 16_384, temperature=1),
    "o4-mini": ModelCapabilities(200_000, 16_384, temperature=1),
    # Google Gemini 2.5 family
    "gemini-2.5-flash": ModelCapabilities(1_000_000, 8192),
    "gemini-2.5-pro": ModelCapabilities(1_000_000, 8192),
    # Google Gemini 3 family
    "gemini-3-flash": ModelCapabilities(1_000_000, 8192),
    "gemini-3-pro": ModelCapabilities(1_000_000, 8192),
}
