"""Tests for base finding model validation of business requirements."""

import pytest
from pydantic import ValidationError
from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence
from waivern_personal_data_analyser.types import (
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)


class TestBaseFindingModelValidation:
    """Test that finding models enforce business requirements for valid findings."""

    def test_finding_rejects_empty_compliance_array(self) -> None:
        """Test that findings require compliance context for business justification.

        Business Logic: Findings represent compliance violations or data discoveries
        and must have regulatory context to be meaningful for compliance reporting.
        """
        with pytest.raises(ValidationError) as exc_info:
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=["test@example.com"],
                compliance=[],  # Empty compliance - should fail business requirement
                evidence=[BaseFindingEvidence(content="test evidence")],
                metadata=PersonalDataFindingMetadata(source="test_source"),
            )

        # Verify the validation error is about compliance requirement
        errors = exc_info.value.errors()
        compliance_error = next(
            (err for err in errors if "compliance" in str(err.get("loc", []))), None
        )
        assert compliance_error is not None
        assert (
            "at least 1" in compliance_error["msg"]
            or "min_length" in compliance_error["type"]
        )

    def test_finding_rejects_empty_matched_patterns_array(self) -> None:
        """Test that findings require detection evidence for business justification.

        Business Logic: Findings must show what patterns triggered detection
        to provide evidence for compliance and audit purposes.
        """
        with pytest.raises(ValidationError) as exc_info:
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=[],  # Empty patterns - should fail business requirement
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 6 personal data processing",
                    )
                ],
                evidence=[BaseFindingEvidence(content="test evidence")],
                metadata=PersonalDataFindingMetadata(source="test_source"),
            )

        # Verify the validation error is about matched_patterns requirement
        errors = exc_info.value.errors()
        patterns_error = next(
            (err for err in errors if "matched_patterns" in str(err.get("loc", []))),
            None,
        )
        assert patterns_error is not None
        assert (
            "at least 1" in patterns_error["msg"]
            or "min_length" in patterns_error["type"]
        )
