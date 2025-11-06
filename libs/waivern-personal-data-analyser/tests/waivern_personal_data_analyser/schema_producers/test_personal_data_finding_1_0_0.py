"""Tests for personal_data_finding v1.0.0 producer."""

from typing import Any

from waivern_core.schemas import (
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseFindingCompliance,
    BaseFindingEvidence,
)

from waivern_personal_data_analyser.schema_producers import (
    personal_data_finding_1_0_0,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)


class TestPersonalDataFindingProducer:
    """Tests for personal_data_finding schema v1.0.0 producer module."""

    def test_produce_formats_findings_correctly(self) -> None:
        """Test producer formats findings list correctly for schema."""
        findings = [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                special_category=False,
                risk_level="medium",
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR", relevance="Article 6 - Lawfulness"
                    )
                ],
                evidence=[
                    BaseFindingEvidence(content="test@example.com"),
                ],
                matched_patterns=["email_pattern"],
                metadata=PersonalDataFindingMetadata(source="test_db"),
            )
        ]
        summary = {
            "total_findings": 1,
            "high_risk_count": 0,
            "special_category_count": 0,
        }
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="personal_data",
            llm_validation_enabled=False,
            evidence_context_size="medium",
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="personal_data_analyser")
            ],
        )

        result = personal_data_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        assert "findings" in result
        assert len(result["findings"]) == 1
        assert result["findings"][0]["type"] == "email"
        assert result["findings"][0]["data_type"] == "basic_profile"
        assert result["findings"][0]["risk_level"] == "medium"

    def test_produce_formats_summary_with_correct_fields(self) -> None:
        """Test producer formats summary with required fields."""
        findings: list[PersonalDataFindingModel] = []
        summary: dict[str, Any] = {
            "total_findings": 5,
            "high_risk_count": 2,
            "special_category_count": 1,
        }
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="personal_data",
            llm_validation_enabled=True,
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="personal_data_analyser")
            ],
        )

        result = personal_data_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        assert "summary" in result
        assert result["summary"]["total_findings"] == 5
        assert result["summary"]["high_risk_count"] == 2
        assert result["summary"]["special_category_count"] == 1

    def test_produce_formats_analysis_metadata(self) -> None:
        """Test producer formats analysis_metadata correctly."""
        findings: list[PersonalDataFindingModel] = []
        summary: dict[str, Any] = {}
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="personal_data",
            llm_validation_enabled=False,
            evidence_context_size="large",
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="personal_data_analyser"),
                AnalysisChainEntry(order=2, analyser="another_analyser"),
            ],
        )

        result = personal_data_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        assert "analysis_metadata" in result
        assert result["analysis_metadata"]["ruleset_used"] == "personal_data"
        assert result["analysis_metadata"]["llm_validation_enabled"] is False
        assert result["analysis_metadata"]["evidence_context_size"] == "large"
        assert len(result["analysis_metadata"]["analyses_chain"]) == 2

    def test_produce_includes_validation_summary_when_present(self) -> None:
        """Test producer includes optional validation_summary when provided."""
        findings: list[PersonalDataFindingModel] = []
        summary: dict[str, Any] = {}
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="personal_data",
            llm_validation_enabled=True,
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="personal_data_analyser")
            ],
        )
        validation_summary = {
            "llm_validation_enabled": True,
            "original_findings_count": 10,
            "validated_findings_count": 8,
            "false_positives_removed": 2,
        }

        result = personal_data_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        assert "validation_summary" in result
        assert result["validation_summary"]["original_findings_count"] == 10
        assert result["validation_summary"]["validated_findings_count"] == 8

    def test_produce_handles_empty_findings_list(self) -> None:
        """Test producer handles empty findings gracefully."""
        findings: list[PersonalDataFindingModel] = []  # Empty list
        summary: dict[str, Any] = {"total_findings": 0}
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="personal_data",
            llm_validation_enabled=False,
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="personal_data_analyser")
            ],
        )

        result = personal_data_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        assert "findings" in result
        assert result["findings"] == []
        assert len(result["findings"]) == 0
        # validation_summary should not be present when not provided
        assert "validation_summary" not in result

    def test_produce_handles_missing_optional_fields_in_findings(self) -> None:
        """Test producer uses Pydantic model_dump which handles optional fields."""
        # PersonalDataFindingModel has optional metadata field
        finding_without_metadata = PersonalDataFindingModel(
            type="phone",
            data_type="basic_profile",
            special_category=False,
            risk_level="low",
            compliance=[
                BaseFindingCompliance(regulation="GDPR", relevance="Article 6")
            ],
            evidence=[BaseFindingEvidence(content="555-1234")],
            matched_patterns=["phone_pattern"],
            # metadata is optional - omitted
        )

        summary: dict[str, Any] = {}
        result = personal_data_finding_1_0_0.produce(
            findings=[finding_without_metadata],
            summary=summary,
            analysis_metadata=BaseAnalysisOutputMetadata(
                ruleset_used="personal_data",
                llm_validation_enabled=False,
                analyses_chain=[
                    AnalysisChainEntry(order=1, analyser="personal_data_analyser")
                ],
            ),
        )

        assert len(result["findings"]) == 1
        # metadata should not be in output (exclude_none=True)
        assert "metadata" not in result["findings"][0]
