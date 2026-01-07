"""Unit tests for GDPRPersonalDataClassifier.

This test module focuses on testing the public API of GDPRPersonalDataClassifier,
following black-box testing principles and TDD methodology.
"""

from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message

from waivern_gdpr_personal_data_classifier.classifier import GDPRPersonalDataClassifier

# =============================================================================
# Contract Tests (inherited from ClassifierContractTests)
# =============================================================================


class TestGDPRPersonalDataClassifierContract(
    ClassifierContractTests[GDPRPersonalDataClassifier]
):
    """Contract tests for GDPRPersonalDataClassifier.

    Inherits all standard classifier contract tests automatically:
    - test_input_requirements_not_empty
    - test_no_duplicate_combinations
    - test_no_empty_combinations
    - test_get_framework_returns_non_empty_string
    """

    @pytest.fixture
    def processor_class(self) -> type[GDPRPersonalDataClassifier]:
        """Provide the classifier class to test."""
        return GDPRPersonalDataClassifier


# =============================================================================
# Classifier-specific Tests (unique to GDPRPersonalDataClassifier)
# =============================================================================


class TestGDPRPersonalDataClassifier:
    """Test suite for GDPRPersonalDataClassifier behaviour."""

    def test_get_name_returns_classifier_name(self) -> None:
        """Test that get_name returns the expected classifier name."""
        name = GDPRPersonalDataClassifier.get_name()

        assert name == "gdpr_personal_data_classifier"

    def test_get_framework_returns_gdpr(self) -> None:
        """Test that get_framework returns 'GDPR'."""
        framework = GDPRPersonalDataClassifier.get_framework()

        assert framework == "GDPR"

    def test_get_input_requirements_accepts_personal_data_indicator(self) -> None:
        """Test that classifier accepts personal_data_indicator/1.0.0 schema."""
        requirements = GDPRPersonalDataClassifier.get_input_requirements()

        assert len(requirements) == 1
        assert len(requirements[0]) == 1
        assert requirements[0][0].schema_name == "personal_data_indicator"
        assert requirements[0][0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_gdpr_personal_data(self) -> None:
        """Test that classifier outputs gdpr_personal_data/1.0.0 schema."""
        schemas = GDPRPersonalDataClassifier.get_supported_output_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "gdpr_personal_data"
        assert schemas[0].version == "1.0.0"

    def test_process_classifies_email_as_identification_data(self) -> None:
        """Test that email indicator is classified as identification_data."""
        input_data = {
            "findings": [
                {
                    "type": "Email Address",
                    "category": "email",
                    "evidence": [{"content": "user@example.com"}],
                    "matched_patterns": ["email"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test_input",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        output_schema = Schema("gdpr_personal_data", "1.0.0")
        classifier = GDPRPersonalDataClassifier()

        # Act
        result = classifier.process([input_message], output_schema)

        assert (
            result.content["findings"][0]["privacy_category"] == "identification_data"
        )
        assert result.content["findings"][0]["special_category"] is False

    def test_process_classifies_health_as_special_category(self) -> None:
        """Test that health indicator is classified as special category."""
        input_data = {
            "findings": [
                {
                    "type": "Health Data",
                    "category": "health",
                    "evidence": [{"content": "patient diagnosis"}],
                    "matched_patterns": ["medical"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        assert result.content["findings"][0]["privacy_category"] == "health_data"
        assert result.content["findings"][0]["special_category"] is True

    def test_process_includes_article_references(self) -> None:
        """Test that classified findings include GDPR article references."""
        input_data = {
            "findings": [
                {
                    "type": "Email Address",
                    "category": "email",
                    "evidence": [{"content": "test@example.com"}],
                    "matched_patterns": ["email"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        article_refs: list[str] = result.content["findings"][0]["article_references"]
        assert isinstance(article_refs, list)
        assert len(article_refs) > 0
        assert any("Article" in ref for ref in article_refs)

    def test_process_preserves_original_evidence(self) -> None:
        """Test that classification preserves evidence from input findings."""
        original_evidence = [
            {"content": "user@example.com"},
            {"content": "john.doe@test.com"},
        ]
        input_data = {
            "findings": [
                {
                    "type": "Email Address",
                    "category": "email",
                    "evidence": original_evidence,
                    "matched_patterns": ["email"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        result_evidence = result.content["findings"][0]["evidence"]
        assert len(result_evidence) == 2
        assert result_evidence[0]["content"] == "user@example.com"
        assert result_evidence[1]["content"] == "john.doe@test.com"

    def test_process_updates_analysis_chain(self) -> None:
        """Test that process adds classifier to analysis chain."""
        findings: list[dict[str, Any]] = []
        input_data = {
            "findings": findings,
            "summary": {
                "total_findings": 0,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        chain = result.content["analysis_metadata"]["analyses_chain"]
        assert len(chain) == 2
        assert chain[0]["analyser"] == "personal_data_analyser"
        assert chain[1]["analyser"] == "gdpr_personal_data_classifier"
        assert chain[1]["order"] == 2

    def test_process_builds_summary_statistics(self) -> None:
        """Test that process builds correct summary with counts."""
        input_data = {
            "findings": [
                {
                    "type": "Email Address",
                    "category": "email",
                    "evidence": [{"content": "test@example.com"}],
                    "matched_patterns": ["email"],
                },
                {
                    "type": "Health Data",
                    "category": "health",
                    "evidence": [{"content": "patient data"}],
                    "matched_patterns": ["medical"],
                },
            ],
            "summary": {
                "total_findings": 2,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        summary = result.content["summary"]
        assert summary["total_findings"] == 2
        assert summary["special_category_count"] == 1

    def test_process_handles_unmapped_indicator_category(self) -> None:
        """Test graceful handling of indicator categories without mapping."""
        input_data = {
            "findings": [
                {
                    "type": "unknown_type",
                    "category": "unknown_category",
                    "evidence": [{"content": "some data"}],
                    "matched_patterns": ["unknown"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data/1.0.0",
                "llm_validation_enabled": False,
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        # Should still produce output with default/unclassified values
        finding = result.content["findings"][0]
        assert finding["privacy_category"] == "unclassified"
        assert finding["special_category"] is False
        assert finding["indicator_type"] == "unknown_type"
