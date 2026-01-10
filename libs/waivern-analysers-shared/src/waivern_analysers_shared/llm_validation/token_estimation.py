"""Token estimation utilities for LLM context management."""

# Model context windows for auto-detection (current as of late 2025)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic Claude 4.5 family (200k standard, 1M beta for Sonnet)
    "claude-opus-4-5": 200_000,
    "claude-sonnet-4-5": 200_000,
    "claude-haiku-4-5": 200_000,
    # Anthropic Claude 4 family
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-4": 200_000,
    # OpenAI GPT-5 family
    "gpt-5.2-pro": 400_000,
    "gpt-5.2": 400_000,
    "gpt-5.1": 256_000,
    "gpt-5-mini": 256_000,
    "gpt-5-nano": 128_000,
    "gpt-5": 256_000,
    # OpenAI o-series reasoning models
    "o3": 200_000,
    "o4-mini": 200_000,
    # Google Gemini 3 family (1M context)
    "gemini-3-pro": 1_000_000,
    "gemini-3-flash": 1_000_000,
    # Google Gemini 2.5 family (still current)
    "gemini-2.5-pro": 1_000_000,
    "gemini-2.5-flash": 1_000_000,
}

# Conservative fallback for unknown models
DEFAULT_CONTEXT_WINDOW = 128_000

# Constants for max payload calculation (implementation details)
OUTPUT_RATIO = 0.15  # Expected output tokens as ratio of input
SAFETY_BUFFER = 0.2  # Buffer for token estimation variance
PROMPT_OVERHEAD_TOKENS = 3000  # Estimated prompt template size


def estimate_tokens(text: str) -> int:
    """Estimate token count for text using character-based heuristic.

    Uses ~0.25 tokens per character as approximation.
    This is sufficient for batching decisions without external dependencies.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.

    """
    if not text:
        return 0
    return max(1, int(len(text) * 0.25))


def get_model_context_window(model_name: str) -> int:
    """Get context window size for a model.

    Uses fuzzy matching to handle version suffixes in model names.
    Returns a conservative default for unknown models.

    Args:
        model_name: The model name (e.g., "claude-sonnet-4-5-20251022").

    Returns:
        Context window size in tokens.

    """
    model_lower = model_name.lower()
    for key, window in MODEL_CONTEXT_WINDOWS.items():
        if key in model_lower:
            return window
    return DEFAULT_CONTEXT_WINDOW


def calculate_max_payload_tokens(context_window: int) -> int:
    """Calculate safe token limit for file content payload.

    Reserves space for:
    - Model output (OUTPUT_RATIO of available context)
    - Safety buffer for estimation variance (SAFETY_BUFFER)
    - Prompt overhead (PROMPT_OVERHEAD_TOKENS)

    Args:
        context_window: Total context window size in tokens.

    Returns:
        Maximum tokens that can safely be used for file content.

    """
    available = context_window / (1 + OUTPUT_RATIO)
    safe = available * (1 - SAFETY_BUFFER)
    return int(safe - PROMPT_OVERHEAD_TOKENS)
