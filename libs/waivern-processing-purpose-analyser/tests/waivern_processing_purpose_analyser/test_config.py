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
        assert config.pattern_matching.ruleset == "processing_purposes"
        assert config.pattern_matching.evidence_context_size == "medium"
        assert config.pattern_matching.maximum_evidence_count == 3

        # Verify LLM validation defaults
        assert config.llm_validation.enable_llm_validation is True
        assert config.llm_validation.llm_batch_size == 50
        assert config.llm_validation.llm_validation_mode == "standard"

    def test_from_properties_with_full_config_respects_all_values(self):
        """Test from_properties respects all provided properties."""
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "custom_purposes",
                    "evidence_context_size": "large",
                    "maximum_evidence_count": 10,
                },
                "llm_validation": {
                    "enable_llm_validation": False,
                    "llm_batch_size": 100,
                    "llm_validation_mode": "aggressive",
                },
            }
        )

        # Verify pattern matching config respected
        assert config.pattern_matching.ruleset == "custom_purposes"
        assert config.pattern_matching.evidence_context_size == "large"
        assert config.pattern_matching.maximum_evidence_count == 10

        # Verify LLM validation config respected
        assert config.llm_validation.enable_llm_validation is False
        assert config.llm_validation.llm_batch_size == 100
        assert config.llm_validation.llm_validation_mode == "aggressive"

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

    def test_from_properties_invalid_llm_batch_size_raises_validation_error(self):
        """Test from_properties rejects LLM batch size outside valid range."""
        # Test below minimum (< 1)
        invalid_properties_low = {"llm_validation": {"llm_batch_size": 0}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties_low)

        assert "llm_batch_size" in str(exc_info.value)

        # Test above maximum (> 200)
        invalid_properties_high = {"llm_validation": {"llm_batch_size": 201}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties_high)

        assert "llm_batch_size" in str(exc_info.value)

    def test_from_properties_invalid_llm_validation_mode_raises_validation_error(self):
        """Test from_properties rejects invalid LLM validation mode."""
        invalid_properties = {"llm_validation": {"llm_validation_mode": "invalid_mode"}}

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions the field and valid options
        error_message = str(exc_info.value)
        assert "llm_validation_mode" in error_message

    def test_from_properties_extra_fields_rejected(self):
        """Test from_properties rejects extra unknown fields."""
        invalid_properties = {
            "pattern_matching": {"ruleset": "processing_purposes"},
            "unknown_field": "should_not_be_accepted",
        }

        with pytest.raises(ValidationError) as exc_info:
            ProcessingPurposeAnalyserConfig.from_properties(invalid_properties)

        # Verify error mentions extra field
        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )
