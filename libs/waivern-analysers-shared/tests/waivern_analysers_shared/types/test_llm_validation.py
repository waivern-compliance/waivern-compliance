"""Tests for LLM validation configuration types."""

import pytest
from pydantic import ValidationError

from waivern_analysers_shared.types import LLMValidationConfig


class TestLLMValidationConfig:
    """Tests for LLMValidationConfig business rules."""

    def test_default_configuration_is_ready_to_use(self) -> None:
        """Default config disables validation to avoid unexpected costs."""
        config = LLMValidationConfig()

        # Validation disabled by default - users must opt-in to incur LLM costs
        assert config.enable_llm_validation is False

        # Standard mode balances precision and recall
        assert config.llm_validation_mode == "standard"

        # Sampling enabled by default to limit API costs
        assert config.sampling_size == 3

    def test_validation_mode_limited_to_implemented_strategies(self) -> None:
        """Only standard/conservative/aggressive modes are supported."""
        # Valid modes work
        for mode in ["standard", "conservative", "aggressive"]:
            config = LLMValidationConfig(llm_validation_mode=mode)  # type: ignore[arg-type]
            assert config.llm_validation_mode == mode

        # Invalid mode rejected
        with pytest.raises(ValidationError, match="llm_validation_mode"):
            LLMValidationConfig(llm_validation_mode="invalid")  # type: ignore[arg-type]
