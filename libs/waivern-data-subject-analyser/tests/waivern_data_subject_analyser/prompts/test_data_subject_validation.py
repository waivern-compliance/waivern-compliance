"""Tests for data subject validation prompts focusing on behaviour."""

import pytest
from waivern_core.schemas import BaseFindingEvidence

from waivern_data_subject_analyser.prompts.data_subject_validation import (
    get_data_subject_validation_prompt,
)
from waivern_data_subject_analyser.schemas.types import (
    DataSubjectIndicatorMetadata,
    DataSubjectIndicatorModel,
)


class TestDataSubjectValidationPrompt:
    """Test data subject validation prompt generation focusing on behaviour."""

    def create_test_finding(
        self,
        subject_category: str = "Customer",
        matched_pattern: str = "customer_id",
        evidence: list[str] | None = None,
        source: str = "test_source",
        confidence_score: int = 80,
    ) -> DataSubjectIndicatorModel:
        """Create a test finding object."""
        evidence_list = evidence if evidence is not None else ["test evidence"]
        evidence_items = [
            BaseFindingEvidence(content=content) for content in evidence_list
        ]
        metadata = DataSubjectIndicatorMetadata(source=source)

        return DataSubjectIndicatorModel(
            subject_category=subject_category,
            matched_patterns=[matched_pattern],
            confidence_score=confidence_score,
            evidence=evidence_items,
            metadata=metadata,
        )

    # -------------------------------------------------------------------------
    # Basic Functionality
    # -------------------------------------------------------------------------

    def test_basic_prompt_generation(self) -> None:
        """Test that prompt generation works with basic finding data."""
        # Arrange
        findings = [
            self.create_test_finding(
                subject_category="Customer",
                matched_pattern="customer_id",
                evidence=["customer_id field in database table"],
                source="mysql_database_(prod)_table_(customers)",
            )
        ]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert isinstance(prompt, str)
        assert len(prompt) > 100

        # Finding data is properly injected
        assert "Customer" in prompt
        assert "customer_id" in prompt
        assert "mysql_database_(prod)_table_(customers)" in prompt
        assert "customer_id field in database table" in prompt

    def test_multiple_findings_in_prompt(self) -> None:
        """Test that multiple findings are all included in the prompt."""
        # Arrange
        findings = [
            self.create_test_finding(
                subject_category="Customer",
                matched_pattern="customer_id",
                source="database_1",
            ),
            self.create_test_finding(
                subject_category="Employee",
                matched_pattern="employee_id",
                source="database_2",
            ),
        ]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "Customer" in prompt
        assert "Employee" in prompt
        assert "customer_id" in prompt
        assert "employee_id" in prompt
        assert "Review all 2 findings" in prompt

    # -------------------------------------------------------------------------
    # Validation Criteria
    # -------------------------------------------------------------------------

    def test_prompt_includes_validation_criteria(self) -> None:
        """Test that prompt includes clear validation criteria."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "TRUE_POSITIVE" in prompt
        assert "FALSE_POSITIVE" in prompt
        assert "VALIDATION CRITERIA" in prompt

    def test_prompt_includes_source_context_guidelines(self) -> None:
        """Test that prompt includes source context interpretation guidelines."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "SOURCE CONTEXT GUIDELINES" in prompt
        assert "Database content" in prompt
        assert "Source code" in prompt
        assert "Documentation files" in prompt

    def test_prompt_includes_category_guidance(self) -> None:
        """Test that prompt includes category-specific guidance."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "CATEGORY-SPECIFIC GUIDANCE" in prompt
        assert "Customer" in prompt
        assert "Employee" in prompt
        assert "Patient" in prompt

    # -------------------------------------------------------------------------
    # Source Code Interpretation
    # -------------------------------------------------------------------------

    def test_prompt_includes_source_code_path_interpretation(self) -> None:
        """Test that prompt includes file path interpretation guidelines."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "FILE PATH INTERPRETATION" in prompt
        assert "test_*.py" in prompt or "Test files" in prompt
        assert "migrations/*" in prompt or "Migration files" in prompt

    def test_prompt_includes_database_metadata_interpretation(self) -> None:
        """Test that prompt includes database source metadata interpretation."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "DATABASE" in prompt
        assert "test" in prompt.lower()  # test database indicators
        assert "prod" in prompt.lower()  # production indicators

    # -------------------------------------------------------------------------
    # Few-Shot Examples
    # -------------------------------------------------------------------------

    def test_prompt_includes_few_shot_examples(self) -> None:
        """Test that prompt includes few-shot examples for better LLM guidance."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "FEW-SHOT EXAMPLES" in prompt or "Example" in prompt
        assert "TRUE_POSITIVE" in prompt
        assert "FALSE_POSITIVE" in prompt

    # -------------------------------------------------------------------------
    # Response Format
    # -------------------------------------------------------------------------

    def test_always_uses_array_response_format(self) -> None:
        """Test that response format is always array-based for consistency."""
        # Test single finding
        single = [self.create_test_finding()]
        prompt_single = get_data_subject_validation_prompt(single, "standard")

        # Test multiple findings
        multiple = [self.create_test_finding(), self.create_test_finding()]
        prompt_multiple = get_data_subject_validation_prompt(multiple, "standard")

        # Both should use array format with finding_id
        assert '"finding_id":' in prompt_single
        assert '"finding_id":' in prompt_multiple
        assert "Review all 1 findings" in prompt_single
        assert "Review all 2 findings" in prompt_multiple

    def test_response_format_includes_required_fields(self) -> None:
        """Test that response format specifies all required fields."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert '"finding_id"' in prompt
        assert '"validation_result"' in prompt
        assert '"confidence"' in prompt
        assert '"reasoning"' in prompt
        assert '"recommended_action"' in prompt

    # -------------------------------------------------------------------------
    # Evidence Formatting
    # -------------------------------------------------------------------------

    def test_evidence_formatting(self) -> None:
        """Test that evidence is properly formatted in the prompt."""
        # Arrange
        findings = [
            self.create_test_finding(
                evidence=["evidence 1", "evidence 2", "evidence 3"]
            )
        ]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert
        assert "- evidence 1" in prompt
        assert "- evidence 2" in prompt
        assert "- evidence 3" in prompt

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_empty_findings_raises_error(self) -> None:
        """Test error handling for empty findings list."""
        with pytest.raises(ValueError, match="At least one finding must be provided"):
            get_data_subject_validation_prompt([], "standard")

    # -------------------------------------------------------------------------
    # Finding ID Preservation
    # -------------------------------------------------------------------------

    def test_finding_ids_are_included_in_prompt(self) -> None:
        """Test that finding IDs (UUIDs) are included for response matching."""
        # Arrange
        finding = self.create_test_finding()
        findings = [finding]

        # Act
        prompt = get_data_subject_validation_prompt(findings, "standard")

        # Assert - The finding's UUID should appear in the prompt
        assert finding.id in prompt
        assert f"Finding [{finding.id}]:" in prompt
