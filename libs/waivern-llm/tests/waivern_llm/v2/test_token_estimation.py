"""Tests for token estimation utilities in LLM Service v2."""

from waivern_llm.v2.token_estimation import (
    calculate_max_payload_tokens,
    estimate_tokens,
    get_model_context_window,
)


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_empty_text_returns_zero_tokens(self) -> None:
        """Empty string should return 0 tokens."""
        assert estimate_tokens("") == 0

    def test_estimates_tokens_proportional_to_text_length(self) -> None:
        """Longer text should produce proportionally more tokens."""
        short_text = "a" * 100
        long_text = "a" * 1000

        short_tokens = estimate_tokens(short_text)
        long_tokens = estimate_tokens(long_text)

        # Long text (10x chars) should produce roughly 10x tokens (within 20% tolerance)
        ratio = long_tokens / short_tokens
        assert 8 <= ratio <= 12, f"Expected ~10x ratio, got {ratio}"

    def test_estimation_is_in_reasonable_range(self) -> None:
        """Token estimates should be in a reasonable range (~0.25 tokens/char).

        Real tokenizers produce roughly 0.2-0.35 tokens/char for English text.
        Our estimate should be in this ballpark to avoid drastically wrong batching.
        """
        text = "def calculate_total(items): return sum(item.price for item in items)"
        tokens = estimate_tokens(text)

        # 69 chars should produce roughly 17 tokens (0.25 ratio)
        # Allow range of 10-30 to account for estimation variance
        assert 10 <= tokens <= 30, f"Expected 10-30 tokens for 69 chars, got {tokens}"


class TestGetModelContextWindow:
    """Tests for get_model_context_window function."""

    def test_returns_window_for_known_model(self) -> None:
        """Known model names should return their context window size."""
        # Claude 4.x models have 200k context
        assert get_model_context_window("claude-sonnet-4") == 200_000

    def test_fuzzy_matches_model_with_version_suffix(self) -> None:
        """Model names with version suffixes should match base model."""
        # Real API model names include date suffixes
        assert get_model_context_window("claude-sonnet-4-5-20251022") == 200_000
        assert get_model_context_window("gpt-5.2-2025-08-07") == 400_000
        assert get_model_context_window("gemini-3-flash-preview") == 1_000_000

    def test_returns_safe_default_for_unknown_model(self) -> None:
        """Unknown models should return a conservative default.

        New models should not break the system - they get a safe fallback.
        """
        # Unknown model should not raise, should return conservative default
        result = get_model_context_window("some-future-model-v7")
        assert result == 128_000  # Conservative default


class TestCalculateMaxPayloadTokens:
    """Tests for calculate_max_payload_tokens function."""

    def test_max_payload_is_less_than_context_window(self) -> None:
        """Max payload must be less than context window to leave room for output."""
        context_window = 200_000
        max_payload = calculate_max_payload_tokens(context_window)

        assert max_payload < context_window, "Must leave room for output and overhead"

    def test_max_payload_leaves_significant_headroom(self) -> None:
        """Max payload should leave meaningful headroom for safety.

        The calculation reserves space for output, prompt overhead, and safety buffer.
        Result should be at most ~70% of context window for typical models.
        """
        context_window = 200_000
        max_payload = calculate_max_payload_tokens(context_window)

        # Should leave at least 30% headroom for safety
        assert max_payload <= context_window * 0.70, (
            f"Expected ≤70% of context, got {max_payload / context_window:.1%}"
        )
