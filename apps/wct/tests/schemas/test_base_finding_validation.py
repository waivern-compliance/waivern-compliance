"""Tests for base finding model validation of business requirements."""

import pytest
from pydantic import ValidationError
from waivern_core.schemas import BaseFindingEvidence
from waivern_personal_data_analyser.schemas import (
    PersonalDataFindingModel,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataFindingMetadata,
)


class TestBaseFindingModelValidation:
    """Test that finding models enforce business requirements for valid findings."""

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

    def test_finding_rejects_empty_evidence_array(self) -> None:
        """Test that findings require evidence for business justification.

        Business Logic: Findings must include evidence snippets showing
        why the pattern was matched for audit and review purposes.
        """
        with pytest.raises(ValidationError) as exc_info:
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=["email"],
                evidence=[],  # Empty evidence - should fail business requirement
                metadata=PersonalDataFindingMetadata(source="test_source"),
            )

        # Verify the validation error is about evidence requirement
        errors = exc_info.value.errors()
        evidence_error = next(
            (err for err in errors if "evidence" in str(err.get("loc", []))),
            None,
        )
        assert evidence_error is not None
        assert (
            "at least 1" in evidence_error["msg"]
            or "min_length" in evidence_error["type"]
        )
