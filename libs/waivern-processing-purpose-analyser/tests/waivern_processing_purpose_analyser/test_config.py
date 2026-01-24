"""Tests for ProcessingPurposeAnalyserConfig."""

import pytest
from pydantic import ValidationError

from waivern_processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)


class TestProcessingPurposeAnalyserConfig:
    """Test ProcessingPurposeAnalyserConfig class."""

    def test_from_properties_with_minimal_config_applies_defaults(self):
        """Test from_properties applies correct defaults with minimal config."""
        config = ProcessingPurposeAnalyserConfig.from_properties({})

        # Verify pattern matching defaults
        assert config.pattern_matching.ruleset == "local/processing_purposes/1.0.0"
        assert config.pattern_matching.evidence_context_size == "medium"
        assert config.pattern_matching.maximum_evidence_count == 3

        # Verify LLM validation field exists with disabled default
        # (LLMValidationConfig defaults are tested in waivern-analysers-shared)
        assert config.llm_validation.enable_llm_validation is False

    def test_from_properties_with_full_config_respects_all_values(self):
        """Test from_properties respects all provided properties."""
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "local/custom_purposes/1.0.0",
                    "evidence_context_size": "large",
                    "maximum_evidence_count": 10,
                },
                "llm_validation": {
                    "enable_llm_validation": True,
                    "llm_batch_size": 100,
                },
            }
        )

        # Verify pattern matching config respected
        assert config.pattern_matching.ruleset == "local/custom_purposes/1.0.0"
        assert config.pattern_matching.evidence_context_size == "large"
        assert config.pattern_matching.maximum_evidence_count == 10

        # Verify LLM validation config respected (tests nested model parsing)
        assert config.llm_validation.enable_llm_validation is True
        assert config.llm_validation.llm_batch_size == 100

    def test_from_properties_invalid_ruleset_type_raises_validation_error(self):
        """Test from_properties rejects invalid ruleset type."""
        invalid_properties = {"pattern_matching": {"ruleset": 123}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions the field with type issue
        assert "ruleset" in str(exc_info.value)

    def test_from_properties_invalid_evidence_context_size_raises_validation_error(
        self,
    ):
        """Test from_properties rejects invalid evidence context size enum."""
        invalid_properties = {
            "pattern_matching": {"evidence_context_size": "invalid_size"}
        }

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions the invalid enum value
        error_message = str(exc_info.value)
        assert "evidence_context_size" in error_message
        assert "small" in error_message or "medium" in error_message

    def test_from_properties_invalid_maximum_evidence_count_raises_validation_error(
        self,
    ):
        """Test from_properties rejects maximum evidence count outside valid range."""
        # Test below minimum (< 1)
        invalid_properties_low = {"pattern_matching": {"maximum_evidence_count": 0}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties_low)

        assert "maximum_evidence_count" in str(exc_info.value)

        # Test above maximum (> 20)
        invalid_properties_high = {"pattern_matching": {"maximum_evidence_count": 21}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties_high)

        assert "maximum_evidence_count" in str(exc_info.value)

    def test_from_properties_extra_fields_rejected(self):
        """Test from_properties rejects extra unknown fields."""
        invalid_properties = {
            "pattern_matching": {"ruleset": "local/processing_purposes/1.0.0"},
            "unknown_field": "should_not_be_accepted",
        }

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions extra field
        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


class TestSourceCodeContextWindowConfig:
    """Tests for source_code_context_window configuration field."""

    @pytest.mark.parametrize("window_size", ["small", "medium", "large", "full"])
    def test_config_accepts_valid_context_window_values(self, window_size: str) -> None:
        """Test that config accepts valid context window values."""
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {"source_code_context_window": window_size}
        )

        assert config.source_code_context_window == window_size

    def test_config_rejects_invalid_context_window(self) -> None:
        """Test that config rejects invalid context window values."""
        # Arrange
        invalid_properties = {"source_code_context_window": "invalid_size"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions the field
        error_message = str(exc_info.value)
        assert "source_code_context_window" in error_message

    def test_config_default_context_window_is_small(self) -> None:
        """Test that default context window is 'small' when not specified."""
        # Arrange & Act
        config = ProcessingPurposeAnalyserConfig.from_properties({})

        # Assert
        assert config.source_code_context_window == "small"
