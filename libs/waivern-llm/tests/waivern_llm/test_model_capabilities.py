"""Tests for ModelCapabilities lookup functionality."""

from waivern_llm.model_capabilities import ModelCapabilities


class TestModelCapabilitiesGet:
    """Tests for ModelCapabilities.get() class method."""

    def test_get_returns_capabilities_for_known_model(self) -> None:
        """Known model names should return their specific capabilities."""
        # Claude 4.5 models have 200k context and 8192 output tokens
        caps = ModelCapabilities.get("claude-sonnet-4-5")

        assert caps.context_window == 200_000
        assert caps.max_output_tokens == 8192

    def test_get_fuzzy_matches_version_suffix(self) -> None:
        """Model names with version suffixes should match base model."""
        # Real API model names include date suffixes
        caps = ModelCapabilities.get("claude-sonnet-4-5-20251022")

        # Should match "claude-sonnet-4-5" base model
        assert caps.context_window == 200_000
        assert caps.max_output_tokens == 8192

    def test_get_returns_defaults_for_unknown_model(self) -> None:
        """Unknown models should return default capabilities."""
        caps = ModelCapabilities.get("some-future-model-v9")

        # Defaults from current codebase: 128k context, 16k output
        assert caps.context_window == 128_000
        assert caps.max_output_tokens == 16_000

    def test_get_is_case_insensitive(self) -> None:
        """Model name lookup should be case insensitive."""
        # Users might pass uppercase model names
        caps = ModelCapabilities.get("CLAUDE-SONNET-4-5")

        assert caps.context_window == 200_000
        assert caps.max_output_tokens == 8192
