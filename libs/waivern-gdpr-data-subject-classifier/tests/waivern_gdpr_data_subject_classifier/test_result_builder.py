"""Tests for GDPRDataSubjectResultBuilder."""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail, Schema

from waivern_gdpr_data_subject_classifier.result_builder import (
    GDPRDataSubjectResultBuilder,
)
from waivern_gdpr_data_subject_classifier.schemas import (
    GDPRDataSubjectFindingMetadata,
    GDPRDataSubjectFindingModel,
)
from waivern_gdpr_data_subject_classifier.types import GDPRDataSubjectClassifierConfig
from waivern_gdpr_data_subject_classifier.validation.models import (
    CategoryRiskModifierResult,
    RiskModifierValidationResult,
)


class TestBuildOutputMessageMetadata:
    """Tests for analysis_metadata in build_output_message."""

    @pytest.fixture
    def config_llm_enabled(self) -> GDPRDataSubjectClassifierConfig:
        """Config with LLM validation enabled."""
        return GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": True}}
        )

    @pytest.fixture
    def config_llm_disabled(self) -> GDPRDataSubjectClassifierConfig:
        """Config with LLM validation disabled."""
        return GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": False}}
        )

    @pytest.fixture
    def sample_finding(self) -> GDPRDataSubjectFindingModel:
        """Sample finding for output message building."""
        return GDPRDataSubjectFindingModel(
            data_subject_category="healthcare",
            article_references=("Article 9",),
            typical_lawful_bases=("consent",),
            risk_modifiers=["minor"],
            confidence_score=85,
            evidence=[BaseFindingEvidence(content="child patient")],
            matched_patterns=[PatternMatchDetail(pattern="patient", match_count=1)],
            metadata=GDPRDataSubjectFindingMetadata(source="test"),
        )

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Output schema for testing."""
        return Schema("gdpr_data_subject", "1.0.0")

    @pytest.fixture
    def llm_validation_result(self) -> RiskModifierValidationResult:
        """Sample LLM validation result."""
        return RiskModifierValidationResult(
            category_results=[
                CategoryRiskModifierResult(
                    category="healthcare",
                    detected_modifiers=["minor"],
                    sample_count=2,
                    confidence=0.9,
                )
            ],
            total_findings=5,
            total_sampled=2,
            validation_succeeded=True,
        )

    def test_metadata_llm_validation_enabled_when_config_enables(
        self,
        config_llm_enabled: GDPRDataSubjectClassifierConfig,
        sample_finding: GDPRDataSubjectFindingModel,
        output_schema: Schema,
    ) -> None:
        """When LLM validation is enabled in config, metadata reflects this."""
        # Arrange
        builder = GDPRDataSubjectResultBuilder(config_llm_enabled)

        # Act
        message = builder.build_output_message(
            findings=[sample_finding],
            output_schema=output_schema,
            ruleset_name="gdpr_data_subject_classification",
            ruleset_version="1.0.0",
            validation_result=None,
        )

        # Assert
        assert message.content["analysis_metadata"]["llm_validation_enabled"] is True

    def test_metadata_llm_validation_disabled_when_config_disables(
        self,
        config_llm_disabled: GDPRDataSubjectClassifierConfig,
        sample_finding: GDPRDataSubjectFindingModel,
        output_schema: Schema,
    ) -> None:
        """When LLM validation is disabled in config, metadata reflects this."""
        # Arrange
        builder = GDPRDataSubjectResultBuilder(config_llm_disabled)

        # Act
        message = builder.build_output_message(
            findings=[sample_finding],
            output_schema=output_schema,
            ruleset_name="gdpr_data_subject_classification",
            ruleset_version="1.0.0",
            validation_result=None,
        )

        # Assert
        assert message.content["analysis_metadata"]["llm_validation_enabled"] is False

    def test_metadata_includes_validation_summary_from_llm(
        self,
        config_llm_enabled: GDPRDataSubjectClassifierConfig,
        sample_finding: GDPRDataSubjectFindingModel,
        output_schema: Schema,
        llm_validation_result: RiskModifierValidationResult,
    ) -> None:
        """When LLM validation result is provided, metadata includes validation summary."""
        # Arrange
        builder = GDPRDataSubjectResultBuilder(config_llm_enabled)

        # Act
        message = builder.build_output_message(
            findings=[sample_finding],
            output_schema=output_schema,
            ruleset_name="gdpr_data_subject_classification",
            ruleset_version="1.0.0",
            validation_result=llm_validation_result,
        )

        # Assert: validation_summary contains LLM-specific data
        summary = message.content["analysis_metadata"]["validation_summary"]
        assert summary["method_used"] == "llm"
        assert summary["total_findings"] == 5
        assert summary["llm_samples_processed"] == 2
        assert summary["categories_validated"] == 1

    def test_metadata_includes_validation_summary_from_regex(
        self,
        config_llm_disabled: GDPRDataSubjectClassifierConfig,
        sample_finding: GDPRDataSubjectFindingModel,
        output_schema: Schema,
    ) -> None:
        """When no LLM result (regex path), metadata includes regex validation summary."""
        # Arrange
        builder = GDPRDataSubjectResultBuilder(config_llm_disabled)

        # Act
        message = builder.build_output_message(
            findings=[sample_finding],
            output_schema=output_schema,
            ruleset_name="gdpr_data_subject_classification",
            ruleset_version="1.0.0",
            validation_result=None,
        )

        # Assert: validation_summary indicates regex method
        summary = message.content["analysis_metadata"]["validation_summary"]
        assert summary["method_used"] == "regex"
