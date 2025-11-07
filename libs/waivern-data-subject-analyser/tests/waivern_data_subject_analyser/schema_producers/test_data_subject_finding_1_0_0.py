"""Tests for data_subject_finding v1.0.0 producer."""

from waivern_core.schemas import AnalysisChainEntry, BaseAnalysisOutputMetadata

from waivern_data_subject_analyser.schemas.types import (
    DataSubjectFindingModel,
)


class TestDataSubjectFindingProducer:
    """Tests for data_subject_finding schema v1.0.0 producer module."""

    def test_produce_formats_findings_correctly(self) -> None:
        """Test producer formats findings list correctly for schema."""
        from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence

        from waivern_data_subject_analyser.schema_producers import (
            data_subject_finding_1_0_0,
        )
        from waivern_data_subject_analyser.schemas.types import (
            DataSubjectFindingMetadata,
        )

        # Arrange
        findings = [
            DataSubjectFindingModel(
                primary_category="customers",
                confidence_score=95,
                risk_level="medium",
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 4(1) - Data subject identification",
                    )
                ],
                evidence=[BaseFindingEvidence(content="user email: test@example.com")],
                matched_patterns=["email_pattern", "customer_category"],
                metadata=DataSubjectFindingMetadata(source="test_db"),
            )
        ]

        summary = {
            "total_classifications": 1,
            "categories_identified": ["customers"],
        }

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="data_subject",
            llm_validation_enabled=False,
            evidence_context_size="medium",
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="data_subject_analyser")
            ],
        )

        # Act
        result = data_subject_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        # Assert
        assert "findings" in result
        assert len(result["findings"]) == 1
        assert result["findings"][0]["primary_category"] == "customers"
        assert result["findings"][0]["confidence_score"] == 95
        assert result["findings"][0]["risk_level"] == "medium"
        assert "email_pattern" in result["findings"][0]["matched_patterns"]
        assert (
            result["findings"][0]["evidence"][0]["content"]
            == "user email: test@example.com"
        )

    def test_produce_formats_summary_with_correct_fields(self) -> None:
        """Test producer formats summary with required fields."""
        from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence

        from waivern_data_subject_analyser.schema_producers import (
            data_subject_finding_1_0_0,
        )

        # Arrange
        findings = [
            DataSubjectFindingModel(
                primary_category="customers",
                confidence_score=95,
                risk_level="medium",
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 4(1) - Data subject identification",
                    )
                ],
                evidence=[BaseFindingEvidence(content="test evidence")],
                matched_patterns=["test_pattern"],
            )
        ]

        summary = {
            "total_classifications": 1,
            "categories_identified": ["customers"],
            "analysis_timestamp": "2025-01-07T10:00:00Z",
        }

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used="data_subject",
            llm_validation_enabled=False,
            evidence_context_size="medium",
            analyses_chain=[
                AnalysisChainEntry(order=1, analyser="data_subject_analyser")
            ],
        )

        # Act
        result = data_subject_finding_1_0_0.produce(
            findings=findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        # Assert
        assert "summary" in result
        assert result["summary"]["total_classifications"] == 1
        assert result["summary"]["categories_identified"] == ["customers"]
        assert result["summary"]["analysis_timestamp"] == "2025-01-07T10:00:00Z"
