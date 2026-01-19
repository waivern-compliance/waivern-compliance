"""Unit tests for GDPRDataSubjectClassifier.

This test module focuses on testing the public API of GDPRDataSubjectClassifier,
following black-box testing principles and TDD methodology.
"""

from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message
from waivern_rulesets import (
    DataSubjectIndicatorRuleset,
    GDPRDataSubjectClassificationRuleset,
)

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier

# =============================================================================
# Contract Tests (inherited from ClassifierContractTests)
# =============================================================================


class TestGDPRDataSubjectClassifierContract(
    ClassifierContractTests[GDPRDataSubjectClassifier]
):
    """Contract tests for GDPRDataSubjectClassifier.

    Inherits all standard classifier contract tests automatically:
    - test_input_requirements_not_empty
    - test_no_duplicate_combinations
    - test_no_empty_combinations
    - test_get_framework_returns_non_empty_string
    """

    @pytest.fixture
    def processor_class(self) -> type[GDPRDataSubjectClassifier]:
        """Provide the classifier class to test."""
        return GDPRDataSubjectClassifier


# =============================================================================
# Classifier-specific Tests (unique to GDPRDataSubjectClassifier)
# =============================================================================


class TestGDPRDataSubjectClassifier:
    """Test suite for GDPRDataSubjectClassifier behaviour."""

    def test_get_name_returns_classifier_name(self) -> None:
        """Test that get_name returns the expected classifier name."""
        name = GDPRDataSubjectClassifier.get_name()

        assert name == "gdpr_data_subject_classifier"

    def test_get_framework_returns_gdpr(self) -> None:
        """Test that get_framework returns 'GDPR'."""
        framework = GDPRDataSubjectClassifier.get_framework()

        assert framework == "GDPR"

    def test_get_input_requirements_accepts_data_subject_indicator(self) -> None:
        """Test that classifier accepts data_subject_indicator/1.0.0 schema."""
        requirements = GDPRDataSubjectClassifier.get_input_requirements()

        assert len(requirements) == 1
        assert len(requirements[0]) == 1
        assert requirements[0][0].schema_name == "data_subject_indicator"
        assert requirements[0][0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_gdpr_data_subject(self) -> None:
        """Test that classifier outputs gdpr_data_subject/1.0.0 schema."""
        schemas = GDPRDataSubjectClassifier.get_supported_output_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "gdpr_data_subject"
        assert schemas[0].version == "1.0.0"

    def test_process_classifies_employee(self) -> None:
        """Test that employee indicator is classified as employee."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee John Smith, HR ID: 12345"}],
                    "matched_patterns": ["employee", "HR"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test_input",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        output_schema = Schema("gdpr_data_subject", "1.0.0")
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process([input_message], output_schema)

        assert result.content["findings"][0]["data_subject_category"] == "employee"
        assert result.content["findings"][0]["confidence_score"] == 85

    def test_process_classifies_customer(self) -> None:
        """Test that customer indicator is classified as customer."""
        input_data = {
            "findings": [
                {
                    "subject_category": "customer",
                    "confidence_score": 90,
                    "evidence": [{"content": "Customer order placed by Jane Doe"}],
                    "matched_patterns": ["customer", "order"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["customer"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        assert result.content["findings"][0]["data_subject_category"] == "customer"

    def test_process_includes_article_references(self) -> None:
        """Test that classified findings include GDPR article references."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 80,
                    "evidence": [{"content": "Employee record"}],
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        article_refs: list[str] = result.content["findings"][0]["article_references"]
        assert isinstance(article_refs, list)
        assert len(article_refs) > 0
        assert any("Article" in ref for ref in article_refs)

    def test_process_includes_typical_lawful_bases(self) -> None:
        """Test that classified findings include typical lawful bases."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 80,
                    "evidence": [{"content": "Employee salary"}],
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        lawful_bases: list[str] = result.content["findings"][0]["typical_lawful_bases"]
        assert isinstance(lawful_bases, list)
        assert len(lawful_bases) > 0

    def test_process_preserves_original_evidence(self) -> None:
        """Test that classification preserves evidence from input findings."""
        original_evidence = [
            {"content": "Employee John Smith"},
            {"content": "Department: Engineering"},
        ]
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": original_evidence,
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        result_evidence = result.content["findings"][0]["evidence"]
        assert len(result_evidence) == 2
        assert result_evidence[0]["content"] == "Employee John Smith"
        assert result_evidence[1]["content"] == "Department: Engineering"

    def test_process_builds_summary_statistics(self) -> None:
        """Test that process builds correct summary with counts."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee data"}],
                    "matched_patterns": ["employee"],
                },
                {
                    "subject_category": "customer",
                    "confidence_score": 90,
                    "evidence": [{"content": "Customer purchase"}],
                    "matched_patterns": ["customer"],
                },
            ],
            "summary": {
                "total_indicators": 2,
                "categories_identified": [
                    "employee",
                    "customer",
                ],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        summary = result.content["summary"]
        assert summary["total_findings"] == 2
        assert "employee" in summary["categories_identified"]
        assert "customer" in summary["categories_identified"]

    def test_process_handles_unmapped_indicator_category(self) -> None:
        """Test graceful handling of indicator categories without mapping."""
        input_data = {
            "findings": [
                {
                    "subject_category": "unknown_category",
                    "confidence_score": 50,
                    "evidence": [{"content": "some data"}],
                    "matched_patterns": ["unknown"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["unknown_category"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        # Should still produce output with default/unclassified values
        finding = result.content["findings"][0]
        assert finding["data_subject_category"] == "unclassified"

    def test_process_propagates_metadata_from_indicator_findings(self) -> None:
        """Test that metadata (source, context) is propagated from input findings."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee data"}],
                    "matched_patterns": ["employee"],
                    "metadata": {
                        "source": "hr_database",
                        "context": {
                            "connector_type": "mysql",
                            "database": "hr_db",
                        },
                    },
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        # Verify metadata is propagated
        finding = result.content["findings"][0]
        assert finding["metadata"] is not None
        assert finding["metadata"]["source"] == "hr_database"
        assert finding["metadata"]["context"]["connector_type"] == "mysql"
        assert finding["metadata"]["context"]["database"] == "hr_db"

    def test_process_handles_findings_without_metadata(self) -> None:
        """Test graceful handling of findings that lack metadata."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee data"}],
                    "matched_patterns": ["employee"],
                    # No metadata field
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        # Should still work, metadata should be None
        finding = result.content["findings"][0]
        assert finding.get("metadata") is None


# =============================================================================
# Risk Modifier Tests
# =============================================================================


class TestRiskModifierDetection:
    """Test suite for risk modifier detection from evidence."""

    def test_detects_minor_risk_modifier(self) -> None:
        """Test that 'minor' risk modifier is detected from evidence containing minor indicators."""
        input_data = {
            "findings": [
                {
                    "subject_category": "student",
                    "confidence_score": 90,
                    "evidence": [
                        {"content": "Student record for minor under 16 years"}
                    ],
                    "matched_patterns": ["student"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["student"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        risk_modifiers = result.content["findings"][0]["risk_modifiers"]
        assert "minor" in risk_modifiers

    def test_detects_child_risk_modifier(self) -> None:
        """Test that 'minor' risk modifier is detected from 'child' in evidence."""
        input_data = {
            "findings": [
                {
                    "subject_category": "patient",
                    "confidence_score": 85,
                    "evidence": [{"content": "Pediatric patient - child under 10"}],
                    "matched_patterns": ["patient"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["patient"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        risk_modifiers = result.content["findings"][0]["risk_modifiers"]
        assert "minor" in risk_modifiers

    def test_no_risk_modifiers_for_regular_evidence(self) -> None:
        """Test that regular evidence without risk indicators has empty risk_modifiers."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee salary record"}],
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        risk_modifiers = result.content["findings"][0]["risk_modifiers"]
        assert risk_modifiers == []

    def test_high_risk_count_in_summary(self) -> None:
        """Test that summary correctly counts findings with risk modifiers."""
        input_data = {
            "findings": [
                {
                    "subject_category": "student",
                    "confidence_score": 90,
                    "evidence": [{"content": "Minor student, age 14"}],
                    "matched_patterns": ["student"],
                },
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Adult employee"}],
                    "matched_patterns": ["employee"],
                },
            ],
            "summary": {
                "total_indicators": 2,
                "categories_identified": [
                    "student",
                    "employee",
                ],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        summary = result.content["summary"]
        assert summary["high_risk_count"] == 1  # Only the minor student


# =============================================================================
# Negative Tests (error paths and edge cases)
# =============================================================================


class TestGDPRDataSubjectClassifierErrorHandling:
    """Test suite for error handling and edge cases."""

    def test_process_raises_error_on_empty_inputs(self) -> None:
        """Test that process raises ValueError when given empty inputs list."""
        classifier = GDPRDataSubjectClassifier()
        output_schema = Schema("gdpr_data_subject", "1.0.0")

        with pytest.raises(ValueError, match="at least one input message"):
            classifier.process([], output_schema)

    def test_process_handles_malformed_metadata_gracefully(self) -> None:
        """Test that non-dict metadata values don't crash the classifier."""
        input_data = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee data"}],
                    "matched_patterns": ["employee"],
                    "metadata": "not_a_dict",  # Malformed: string instead of dict
                }
            ],
            "summary": {
                "total_indicators": 1,
                "categories_identified": ["employee"],
            },
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        # Should not crash, metadata should be None
        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        finding = result.content["findings"][0]
        assert finding.get("metadata") is None
        assert finding["data_subject_category"] == "employee"

    def test_process_handles_empty_findings_list(self) -> None:
        """Test that empty findings list produces valid output with zero counts."""
        findings: list[dict[str, Any]] = []
        categories: list[str] = []
        input_data: dict[str, Any] = {
            "findings": findings,
            "summary": {"total_indicators": 0, "categories_identified": categories},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_message = Message(
            id="test",
            content=input_data,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )
        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_message], Schema("gdpr_data_subject", "1.0.0")
        )

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0
        assert result.content["summary"]["high_risk_count"] == 0


# =============================================================================
# Fan-in Tests (multiple input aggregation)
# =============================================================================


class TestFanInSupport:
    """Test suite for fan-in support (aggregating findings from multiple inputs)."""

    def test_process_aggregates_findings_from_multiple_inputs(self) -> None:
        """Test that findings from multiple input messages are concatenated."""
        # Input 1: employee finding
        input_data_1 = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee John Smith"}],
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["employee"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_1 = Message(
            id="input_1",
            content=input_data_1,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        # Input 2: customer finding
        input_data_2 = {
            "findings": [
                {
                    "subject_category": "customer",
                    "confidence_score": 90,
                    "evidence": [{"content": "Customer order placed"}],
                    "matched_patterns": ["customer"],
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["customer"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_2 = Message(
            id="input_2",
            content=input_data_2,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_1, input_2], Schema("gdpr_data_subject", "1.0.0")
        )

        # Should have 2 findings (aggregated from both inputs)
        assert len(result.content["findings"]) == 2
        # Verify both categories are present
        categories = [f["data_subject_category"] for f in result.content["findings"]]
        assert "employee" in categories
        assert "customer" in categories

    def test_process_recalculates_summary_for_aggregated_findings(self) -> None:
        """Test that summary statistics reflect ALL aggregated findings."""
        # Input 1: employee finding (no risk modifiers)
        input_data_1 = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Adult employee record"}],
                    "matched_patterns": ["employee"],
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["employee"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_1 = Message(
            id="input_1",
            content=input_data_1,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        # Input 2: student finding with minor (has risk modifier)
        input_data_2 = {
            "findings": [
                {
                    "subject_category": "student",
                    "confidence_score": 90,
                    "evidence": [{"content": "Minor student, age 14"}],
                    "matched_patterns": ["student"],
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["student"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_2 = Message(
            id="input_2",
            content=input_data_2,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_1, input_2], Schema("gdpr_data_subject", "1.0.0")
        )

        # Summary should reflect BOTH inputs
        summary = result.content["summary"]
        assert summary["total_findings"] == 2
        assert summary["high_risk_count"] == 1  # Only the minor student
        assert "employee" in summary["categories_identified"]
        # Note: "student" indicator maps to "education" GDPR category
        assert "education" in summary["categories_identified"]

    def test_process_preserves_metadata_per_finding_when_aggregating(self) -> None:
        """Test that each finding retains its original metadata after aggregation."""
        # Input 1: finding from MySQL source
        input_data_1 = {
            "findings": [
                {
                    "subject_category": "employee",
                    "confidence_score": 85,
                    "evidence": [{"content": "Employee data"}],
                    "matched_patterns": ["employee"],
                    "metadata": {
                        "source": "mysql_hr_table",
                        "context": {"connector_type": "mysql"},
                    },
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["employee"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_1 = Message(
            id="input_1",
            content=input_data_1,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        # Input 2: finding from filesystem source
        input_data_2 = {
            "findings": [
                {
                    "subject_category": "customer",
                    "confidence_score": 90,
                    "evidence": [{"content": "Customer record"}],
                    "matched_patterns": ["customer"],
                    "metadata": {
                        "source": "customers.csv",
                        "context": {"connector_type": "filesystem"},
                    },
                }
            ],
            "summary": {"total_indicators": 1, "categories_identified": ["customer"]},
            "analysis_metadata": {
                "ruleset_used": "local/data_subject_indicator/1.0.0",
                "llm_validation_enabled": False,
            },
        }
        input_2 = Message(
            id="input_2",
            content=input_data_2,
            schema=Schema("data_subject_indicator", "1.0.0"),
        )

        classifier = GDPRDataSubjectClassifier()

        result = classifier.process(
            [input_1, input_2], Schema("gdpr_data_subject", "1.0.0")
        )

        # Find findings by their category to check metadata
        findings_by_category = {
            f["data_subject_category"]: f for f in result.content["findings"]
        }

        # Employee finding should have MySQL metadata
        assert (
            findings_by_category["employee"]["metadata"]["source"] == "mysql_hr_table"
        )
        assert (
            findings_by_category["employee"]["metadata"]["context"]["connector_type"]
            == "mysql"
        )

        # Customer finding should have filesystem metadata
        assert findings_by_category["customer"]["metadata"]["source"] == "customers.csv"
        assert (
            findings_by_category["customer"]["metadata"]["context"]["connector_type"]
            == "filesystem"
        )


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
        indicator_ruleset = DataSubjectIndicatorRuleset()
        indicator_categories = {
            rule.subject_category for rule in indicator_ruleset.get_rules()
        }

        # Get all mapped categories from GDPR classification ruleset
        gdpr_ruleset = GDPRDataSubjectClassificationRuleset()
        mapped_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            mapped_categories.update(rule.indicator_categories)

        # Find unmapped categories
        unmapped = indicator_categories - mapped_categories

        assert unmapped == set(), (
            f"Indicator categories missing GDPR mapping: {unmapped}\n"
            f"Add mappings to gdpr_data_subject_classification.yaml"
        )

    def test_gdpr_mappings_reference_valid_indicator_categories(self) -> None:
        """Verify GDPR mappings only reference existing indicator categories.

        This catches typos or stale references when indicator categories are renamed.
        """
        # Get all unique categories from indicator ruleset
        indicator_ruleset = DataSubjectIndicatorRuleset()
        indicator_categories = {
            rule.subject_category for rule in indicator_ruleset.get_rules()
        }

        # Get all referenced categories from GDPR classification ruleset
        gdpr_ruleset = GDPRDataSubjectClassificationRuleset()
        referenced_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            referenced_categories.update(rule.indicator_categories)

        # Find invalid references
        invalid = referenced_categories - indicator_categories

        assert invalid == set(), (
            f"GDPR mappings reference non-existent indicator categories: {invalid}\n"
            f"These may be typos or stale references after renaming."
        )
