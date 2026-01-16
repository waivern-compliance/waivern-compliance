"""Tests for configuration types."""

import pytest
from pydantic import ValidationError

from waivern_analysers_shared.types import (
    BatchingConfig,
    LLMValidationConfig,
)


class TestBatchingConfig:
    """Tests for BatchingConfig model."""

    def test_default_context_window_is_none_for_auto_detect(self) -> None:
        """Default is None, meaning auto-detect from model name."""
        config = BatchingConfig()
        assert config.model_context_window is None

    def test_can_override_context_window(self) -> None:
        """Can set explicit context window when auto-detect is not suitable."""
        config = BatchingConfig(model_context_window=128_000)
        assert config.model_context_window == 128_000


class TestLLMValidationConfig:
    """Tests for LLMValidationConfig business rules."""

    def test_default_configuration_is_ready_to_use(self) -> None:
        """Default config enables validation with sensible defaults."""
        config = LLMValidationConfig()

        # Validation enabled by default - users want false positive filtering
        assert config.enable_llm_validation is True

        # Standard mode balances precision and recall
        assert config.llm_validation_mode == "standard"

        # Batch size of 50 balances throughput and context usage
        assert config.llm_batch_size == 50

        # Batching config uses auto-detect
        assert config.batching.model_context_window is None

    def test_batch_size_minimum_prevents_degenerate_batches(self) -> None:
        """Batch size must be at least 1 - zero findings per batch is not useful."""
        with pytest.raises(ValidationError, match="llm_batch_size"):
            LLMValidationConfig(llm_batch_size=0)

    def test_batch_size_maximum_prevents_context_overflow(self) -> None:
        """Batch size capped at 200 to avoid exceeding LLM context windows."""
        with pytest.raises(ValidationError, match="llm_batch_size"):
            LLMValidationConfig(llm_batch_size=201)

    def test_validation_mode_limited_to_implemented_strategies(self) -> None:
        """Only standard/conservative/aggressive modes are supported."""
        # Valid modes work
        for mode in ["standard", "conservative", "aggressive"]:
            config = LLMValidationConfig(llm_validation_mode=mode)  # type: ignore[arg-type]
            assert config.llm_validation_mode == mode

        # Invalid mode rejected
        with pytest.raises(ValidationError, match="llm_validation_mode"):
            LLMValidationConfig(llm_validation_mode="invalid")  # type: ignore[arg-type]
