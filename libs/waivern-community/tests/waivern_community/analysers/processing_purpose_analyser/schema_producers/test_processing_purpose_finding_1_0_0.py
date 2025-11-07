"""Tests for processing_purpose_finding v1.0.0 producer."""

from waivern_core.schemas import AnalysisChainEntry, BaseAnalysisOutputMetadata


class TestProcessingPurposeFindingProducer:
    """Tests for processing_purpose_finding schema v1.0.0 producer module."""

    def test_produce_formats_findings_correctly(self) -> None:
        """Test producer formats findings list correctly for schema."""
        from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence

        from waivern_community.analysers.processing_purpose_analyser.schema_producers import (
            processing_purpose_finding_1_0_0,
        )
        from waivern_community.analysers.processing_purpose_analyser.schemas.types import (
            ProcessingPurposeFindingModel,
        )

        # Arrange
        findings = [
            ProcessingPurposeFindingModel(
                purpose="user authentication",
                purpose_category="security",
                risk_level="medium",
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 6(1)(b) - Contract performance",
                    )
                ],
                evidence=[BaseFindingEvidence(content="login processing code")],
                matched_patterns=["authentication_pattern"],
            )
        ]

        summary = {
            "total_findings": 1,
            "purposes_identified": 1,
            "high_risk_count": 0,
        }

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="processing_purposes",
            llm_validation_enabled=False,
            evidence_context_size="medium",
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="processing_purpose_analyser")
            ],
        )

        # Act
        result = processing_purpose_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        # Assert
        assert "findings" in result
        assert len(result["findings"]) == 1
        assert result["findings"][0]["purpose"] == "user authentication"
        assert result["findings"][0]["purpose_category"] == "security"
        assert result["findings"][0]["risk_level"] == "medium"
        assert "summary" in result
        assert result["summary"]["total_findings"] == 1
