"""Unit tests for GDPRPersonalDataClassifier.

This test module focuses on testing the public API of GDPRPersonalDataClassifier,
following black-box testing principles and TDD methodology.
"""

import logging
from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message
from waivern_rulesets import (
    GDPRPersonalDataClassificationRuleset,
    PersonalDataIndicatorRuleset,
)

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

    def test_process_builds_summary_statistics(self) -> None:
        """Test that process builds correct summary with counts."""
        input_data = {
            "findings": [
                {
                    "category": "email",
                    "evidence": [{"content": "test@example.com"}],
                    "matched_patterns": ["email"],
                },
                {
                    "category": "health",
                    "evidence": [{"content": "patient data"}],
                    "matched_patterns": ["medical"],
                },
            ],
            "summary": {
                "total_findings": 2,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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
                    "category": "unknown_category",
                    "evidence": [{"content": "some data"}],
                    "matched_patterns": ["unknown"],
                }
            ],
            "summary": {
                "total_findings": 1,
            },
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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
        assert finding["indicator_type"] == "unknown_category"

    def test_process_propagates_metadata_from_indicator_findings(self) -> None:
        """Test that metadata (source, context) is propagated from input findings."""
        input_data = {
            "findings": [
                {
                    "category": "email",
                    "evidence": [{"content": "user@example.com"}],
                    "matched_patterns": ["email"],
                    "metadata": {
                        "source": "users_table",
                        "context": {
                            "connector_type": "mysql",
                            "database": "customers_db",
                        },
                    },
                }
            ],
            "summary": {"total_findings": 1},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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

        # Verify metadata is propagated
        finding = result.content["findings"][0]
        assert finding["metadata"] is not None
        assert finding["metadata"]["source"] == "users_table"
        assert finding["metadata"]["context"]["connector_type"] == "mysql"
        assert finding["metadata"]["context"]["database"] == "customers_db"

    def test_process_handles_findings_without_metadata(self) -> None:
        """Test graceful handling of findings that lack metadata."""
        input_data = {
            "findings": [
                {
                    "category": "email",
                    "evidence": [{"content": "user@example.com"}],
                    "matched_patterns": ["email"],
                    # No metadata field
                }
            ],
            "summary": {"total_findings": 1},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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

        # Should still work, metadata should be None
        finding = result.content["findings"][0]
        assert finding.get("metadata") is None


# =============================================================================
# Negative Tests (error paths and edge cases)
# =============================================================================


class TestGDPRPersonalDataClassifierErrorHandling:
    """Test suite for error handling and edge cases."""

    def test_process_raises_error_on_empty_inputs(self) -> None:
        """Test that process raises ValueError when given empty inputs list."""
        classifier = GDPRPersonalDataClassifier()
        output_schema = Schema("gdpr_personal_data", "1.0.0")

        with pytest.raises(ValueError, match="at least one input message"):
            classifier.process([], output_schema)

    def test_process_handles_malformed_metadata_gracefully(self) -> None:
        """Test that non-dict metadata values don't crash the classifier."""
        input_data = {
            "findings": [
                {
                    "category": "email",
                    "evidence": [{"content": "test@example.com"}],
                    "matched_patterns": ["email"],
                    "metadata": "not_a_dict",  # Malformed: string instead of dict
                }
            ],
            "summary": {"total_findings": 1},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        # Should not crash, metadata should be None
        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        finding = result.content["findings"][0]
        assert finding.get("metadata") is None
        assert finding["privacy_category"] == "identification_data"

    def test_process_handles_list_metadata_gracefully(self) -> None:
        """Test that list metadata values (another malformed type) don't crash."""
        input_data = {
            "findings": [
                {
                    "category": "email",
                    "evidence": [{"content": "test@example.com"}],
                    "matched_patterns": ["email"],
                    "metadata": ["not", "a", "dict"],  # Malformed: list instead of dict
                }
            ],
            "summary": {"total_findings": 1},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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

        finding = result.content["findings"][0]
        assert finding.get("metadata") is None

    def test_process_logs_warning_for_multiple_inputs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that multiple inputs logs a warning but processes first input."""
        findings: list[dict[str, Any]] = []
        input_data = {
            "findings": findings,
            "summary": {"total_findings": 0},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input1 = Message(
            id="first",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        input2 = Message(
            id="second",
            content=input_data,
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        classifier = GDPRPersonalDataClassifier()

        with caplog.at_level(logging.WARNING):
            result = classifier.process(
                [input1, input2], Schema("gdpr_personal_data", "1.0.0")
            )

        # Should still produce valid output
        assert result.schema.name == "gdpr_personal_data"

        # Should have logged a warning
        assert "received 2 inputs but only processes the first" in caplog.text

    def test_process_handles_empty_findings_list(self) -> None:
        """Test that empty findings list produces valid output with zero counts."""
        findings: list[dict[str, Any]] = []
        input_data = {
            "findings": findings,
            "summary": {"total_findings": 0},
            "analysis_metadata": {
                "ruleset_used": "local/personal_data_indicator/1.0.0",
                "llm_validation_enabled": False,
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

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0
        assert result.content["summary"]["special_category_count"] == 0


class TestRulesetContractValidation:
    """Contract tests ensuring indicator categories map to GDPR classifications.

    These tests catch when someone adds a new indicator category but forgets
    to add the corresponding GDPR classification mapping.
    """

    def test_all_indicator_categories_have_gdpr_mapping(self) -> None:
        """Verify every indicator category is mapped in GDPR classification ruleset.

        This is a critical contract test. If this fails, it means:
        - A new indicator category was added
        - But no GDPR classification mapping was created
        - Resulting in silent 'unclassified' output
        """
        # Get all unique categories from indicator ruleset
        indicator_ruleset = PersonalDataIndicatorRuleset()
        indicator_categories = {rule.category for rule in indicator_ruleset.get_rules()}

        # Get all mapped categories from GDPR classification ruleset
        gdpr_ruleset = GDPRPersonalDataClassificationRuleset()
        mapped_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            mapped_categories.update(rule.indicator_categories)

        # Find unmapped categories
        unmapped = indicator_categories - mapped_categories

        assert unmapped == set(), (
            f"Indicator categories missing GDPR mapping: {unmapped}\n"
            f"Add mappings to gdpr_personal_data_classification.yaml"
        )

    def test_gdpr_mappings_reference_valid_indicator_categories(self) -> None:
        """Verify GDPR mappings only reference existing indicator categories.

        This catches typos or stale references when indicator categories are renamed.
        """
        # Get all unique categories from indicator ruleset
        indicator_ruleset = PersonalDataIndicatorRuleset()
        indicator_categories = {rule.category for rule in indicator_ruleset.get_rules()}

        # Get all referenced categories from GDPR classification ruleset
        gdpr_ruleset = GDPRPersonalDataClassificationRuleset()
        referenced_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            referenced_categories.update(rule.indicator_categories)

        # Find invalid references
        invalid = referenced_categories - indicator_categories

        assert invalid == set(), (
            f"GDPR mappings reference non-existent indicator categories: {invalid}\n"
            f"These may be typos or stale references after renaming."
        )
