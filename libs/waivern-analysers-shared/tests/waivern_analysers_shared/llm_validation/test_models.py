"""Tests for shared LLM validation models - focuses on business-critical constraints."""

import pytest
from waivern_core import LLMValidationResultModel
from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)

from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    RemovedItem,
)


def _create_test_finding() -> BaseFindingModel[BaseFindingMetadata]:
    """Create a test finding with auto-generated UUID."""
    return BaseFindingModel(
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=[PatternMatchDetail(pattern="test_pattern", match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


class TestLLMValidationOutcome:
    """Tests for LLMValidationOutcome.with_marked_findings preserving removed items."""

    def test_with_marked_findings_preserves_removed_unchanged(self) -> None:
        """Marker is applied to kept findings only; removed items pass through untouched.

        The marker callback exists to tag findings that survived LLM
        validation (e.g., flagging them as 'llm-validated' in the output).
        Applying it to removed findings would be incoherent — those items are
        being filtered out, so 'marking' them has no consumer. This test
        guards that invariant: ``with_marked_findings`` must return the exact
        same ``RemovedItem`` instances in ``llm_validated_removed``, with
        their reasons untouched.
        """
        kept_finding = _create_test_finding()
        removed_finding = _create_test_finding()
        removed_item = RemovedItem(finding=removed_finding, reason="LLM marked as FP")
        outcome = LLMValidationOutcome[BaseFindingModel[BaseFindingMetadata]](
            llm_validated_kept=[kept_finding],
            llm_validated_removed=[removed_item],
            llm_not_flagged=[],
            skipped=[],
        )

        def _mark(
            f: BaseFindingModel[BaseFindingMetadata],
        ) -> BaseFindingModel[BaseFindingMetadata]:
            return f.model_copy(
                update={"metadata": BaseFindingMetadata(source="MARKED")}
            )

        marked_outcome = outcome.with_marked_findings(_mark)

        # The marker IS applied to kept findings (sanity check).
        assert marked_outcome.llm_validated_kept[0].metadata.source == "MARKED"

        # The marker must not touch removed items: reasons stay intact and
        # the finding's metadata is the original, not the MARKED version.
        assert marked_outcome.llm_validated_removed == [removed_item]
        assert marked_outcome.llm_validated_removed[0].reason == "LLM marked as FP"
        assert (
            marked_outcome.llm_validated_removed[0].finding.metadata.source
            == "test_source"
        )


class TestLLMValidationResultModel:
    """Test LLM validation result model - focuses on business-critical validation constraints."""

    def test_confidence_accepts_llm_output(self) -> None:
        """Test that confidence field accepts LLM output without range constraints.

        The ge/le constraints were removed because the Anthropic Batch API
        does not support minimum/maximum on number types in JSON Schema.
        LLM output is not reliably bounded, so validation is best-effort.
        """
        finding = _create_test_finding()

        result = LLMValidationResultModel(finding_id=finding.id, confidence=0.85)
        assert result.confidence == 0.85

        # Out-of-range values are accepted (LLM output is not reliably bounded)
        high = LLMValidationResultModel(finding_id=finding.id, confidence=1.5)
        assert high.confidence == 1.5

    def test_finding_id_must_be_non_empty(self) -> None:
        """Test that finding_id must be a non-empty string.

        Business requirement: Finding IDs must reference valid findings.
        Production impact: Empty IDs would fail to match any finding.
        """
        finding = _create_test_finding()

        # Valid ID should work - use actual finding.id (UUID)
        valid_result = LLMValidationResultModel(finding_id=finding.id)
        assert valid_result.finding_id == finding.id

        # Invalid ID - empty string
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_id="")
