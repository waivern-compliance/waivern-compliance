"""Tests for GDPRDataSubjectClassifier DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract for the enrichment
paradigm: category-level risk modifier detection via LLM, with graceful
degradation to per-finding regex fallback when dispatch is unavailable.
"""

from typing import Any, cast

import pytest
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BatchingMode, SkippedFinding
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_schemas.gdpr_data_subject import GDPRDataSubjectFindingModel

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.prompts import RiskModifierPromptBuilder
from waivern_gdpr_data_subject_classifier.types import (
    GDPRDataSubjectClassifierConfig,
    GDPRDataSubjectPrepareState,
)
from waivern_gdpr_data_subject_classifier.validation.models import (
    RiskModifierResultModel,
    RiskModifierValidationResponseModel,
)

OUTPUT_SCHEMA = Schema("gdpr_data_subject", "1.0.0")
INPUT_SCHEMA = Schema("data_subject_indicator", "1.0.0")
RUN_ID = "test-run-id"


# =============================================================================
# Helpers
# =============================================================================


def _make_classifier(*, enable_llm: bool = True) -> GDPRDataSubjectClassifier:
    """Build a classifier with controllable LLM enablement via config."""
    config = GDPRDataSubjectClassifierConfig.from_properties(
        {"llm_validation": {"enable_llm_validation": enable_llm}}
    )
    return GDPRDataSubjectClassifier(config=config)


def _make_message(findings: list[dict[str, Any]]) -> Message:
    """Build a data_subject_indicator Message from finding dicts."""
    return Message(
        id="test-input",
        content={"findings": findings},
        schema=INPUT_SCHEMA,
        run_id=RUN_ID,
    )


def _make_patient_finding(evidence_content: str = "Patient record") -> dict[str, Any]:
    """Raw finding dict with subject_category='patient' (maps to 'healthcare')."""
    return {
        "subject_category": "patient",
        "confidence_score": 85,
        "evidence": [{"content": evidence_content}],
        "matched_patterns": [{"pattern": "patient", "match_count": 1}],
        "metadata": {"source": "medical_records"},
    }


def _make_employee_finding(
    evidence_content: str = "Adult employee record",
) -> dict[str, Any]:
    """Raw finding dict with subject_category='employee' (maps to 'employee')."""
    return {
        "subject_category": "employee",
        "confidence_score": 90,
        "evidence": [{"content": evidence_content}],
        "matched_patterns": [{"pattern": "employee", "match_count": 1}],
        "metadata": {"source": "hr_database"},
    }


def _build_llm_dispatch_result(
    request: LLMRequest[GDPRDataSubjectFindingModel],
    finding_modifiers: dict[str, list[str]],
    skipped: list[SkippedFinding[GDPRDataSubjectFindingModel]] | None = None,
) -> LLMDispatchResult:
    """Build an LLMDispatchResult mapping finding IDs to their detected modifiers."""
    results = [
        RiskModifierResultModel(
            finding_id=finding_id,
            risk_modifiers=modifiers,
            confidence=0.9,
            reasoning="test reasoning",
        )
        for finding_id, modifiers in finding_modifiers.items()
    ]
    response = RiskModifierValidationResponseModel(results=results)
    return LLMDispatchResult(
        request_id=request.request_id,
        model_name="claude-sonnet-4-5-20250929",
        responses=[response.model_dump(mode="json")],
        skipped=list(skipped) if skipped else [],
    )


# =============================================================================
# Prepare
# =============================================================================


class TestPrepare:
    """Tests for prepare() — classification, request building, capability gating."""

    def test_empty_inputs_raises_value_error(self) -> None:
        """prepare([]) must raise ValueError (contract preserved from process())."""
        classifier = _make_classifier()

        with pytest.raises(ValueError, match="at least one input message"):
            classifier.prepare(inputs=[], output_schema=OUTPUT_SCHEMA)

    def test_no_findings_returns_empty_requests(self) -> None:
        """No findings in input → no dispatch request, classified_findings empty."""
        classifier = _make_classifier()
        message = _make_message(findings=[])

        result = classifier.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.classified_findings == []
        assert result.state.llm_enabled is True
        assert result.state.run_id == RUN_ID

    def test_findings_with_llm_enabled_builds_count_based_request(self) -> None:
        """Findings + LLM available → single COUNT_BASED LLMRequest with prompt builder."""
        classifier = _make_classifier()
        message = _make_message(
            findings=[_make_patient_finding(), _make_employee_finding()]
        )

        result = classifier.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.llm_enabled is True
        assert len(result.state.classified_findings) == 2

        assert isinstance(result.requests[0], LLMRequest)
        llm_request = cast(LLMRequest[GDPRDataSubjectFindingModel], result.requests[0])
        assert llm_request.batching_mode == BatchingMode.COUNT_BASED
        assert isinstance(llm_request.prompt_builder, RiskModifierPromptBuilder)
        assert llm_request.response_model is RiskModifierValidationResponseModel
        assert llm_request.run_id == RUN_ID
        assert len(llm_request.groups) == 1

    def test_findings_with_llm_disabled_returns_empty_requests(self) -> None:
        """Findings with ``enable_llm_validation=False`` yield no dispatch requests."""
        classifier = _make_classifier(enable_llm=False)
        message = _make_message(findings=[_make_patient_finding()])

        result = classifier.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False
        assert len(result.state.classified_findings) == 1


# =============================================================================
# Finalise
# =============================================================================


class TestFinalise:
    """Tests for finalise() — category aggregation and regex fallback."""

    def test_llm_disabled_uses_regex_and_reports_method(self) -> None:
        """llm_enabled=False state → regex modifier detection, method_used='regex'.

        The "child patient" evidence should match the 'minor' risk modifier
        pattern through regex detection.
        """
        classifier = _make_classifier(enable_llm=False)
        message = _make_message(
            findings=[_make_patient_finding("child patient admitted to ward")]
        )

        prepare_result = classifier.prepare(
            inputs=[message], output_schema=OUTPUT_SCHEMA
        )
        result = classifier.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["method_used"] == "regex"

        findings = result.content["findings"]
        healthcare = next(
            f for f in findings if f["data_subject_category"] == "healthcare"
        )
        assert "minor" in healthcare["risk_modifiers"]

    def test_empty_results_falls_back_to_regex_preserving_findings(self) -> None:
        """llm_enabled=True but empty results → regex applied, no data loss."""
        classifier = _make_classifier()
        message = _make_message(
            findings=[
                _make_patient_finding("child patient, age 8"),
                _make_employee_finding(),
            ]
        )

        prepare_result = classifier.prepare(
            inputs=[message], output_schema=OUTPUT_SCHEMA
        )
        assert prepare_result.state.llm_enabled is True
        result = classifier.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["method_used"] == "regex"

        findings = result.content["findings"]
        # Every original finding preserved
        assert len(findings) == 2
        # Regex still detected 'minor' from the healthcare finding
        healthcare = next(
            f for f in findings if f["data_subject_category"] == "healthcare"
        )
        assert "minor" in healthcare["risk_modifiers"]

    def test_llm_dispatch_result_applies_category_level_modifiers(self) -> None:
        """Valid LLMDispatchResult → modifiers applied to ALL findings per category.

        Three 'patient' findings + LLM returns 'minor' modifier for one →
        all three healthcare findings inherit the modifier (union semantics).
        """
        classifier = _make_classifier()
        message = _make_message(
            findings=[
                _make_patient_finding("Patient A"),
                _make_patient_finding("Patient B"),
                _make_patient_finding("Patient C"),
            ]
        )

        prepare_result = classifier.prepare(
            inputs=[message], output_schema=OUTPUT_SCHEMA
        )
        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[GDPRDataSubjectFindingModel], prepare_result.requests[0]
        )
        classified = prepare_result.state.classified_findings
        # LLM reports 'minor' for the first classified finding only
        dispatch_result = _build_llm_dispatch_result(
            llm_request,
            finding_modifiers={classified[0].id: ["minor"]},
        )

        result = classifier.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )

        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["method_used"] == "llm"

        findings = result.content["findings"]
        assert len(findings) == 3
        # Category-level application: ALL three healthcare findings get 'minor'
        for finding in findings:
            assert finding["data_subject_category"] == "healthcare"
            assert "minor" in finding["risk_modifiers"], (
                f"Expected 'minor' via category-level application, "
                f"got {finding['risk_modifiers']}"
            )

    def test_dispatch_result_with_empty_responses_falls_back_to_regex(self) -> None:
        """LLMDispatchResult with responses=[] → regex fallback (context overflow case)."""
        classifier = _make_classifier()
        message = _make_message(
            findings=[_make_patient_finding("child patient, age 8")]
        )

        prepare_result = classifier.prepare(
            inputs=[message], output_schema=OUTPUT_SCHEMA
        )
        assert isinstance(prepare_result.requests[0], LLMRequest)
        empty_dispatch_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[],
            skipped=[],
        )

        result = classifier.finalise(
            prepare_result.state, [empty_dispatch_result], OUTPUT_SCHEMA
        )

        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["method_used"] == "regex"
        healthcare = next(
            f
            for f in result.content["findings"]
            if f["data_subject_category"] == "healthcare"
        )
        assert "minor" in healthcare["risk_modifiers"]

    def test_no_findings_produces_empty_output(self) -> None:
        """Empty state → empty findings, valid summary, no aggregator errors."""
        classifier = _make_classifier()
        message = _make_message(findings=[])

        prepare_result = classifier.prepare(
            inputs=[message], output_schema=OUTPUT_SCHEMA
        )
        result = classifier.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0
        assert result.content["summary"]["high_risk_count"] == 0


class TestDeserialise:
    """Tests for deserialise_prepare_result() round-trip fidelity."""

    def test_round_trip_with_llm_request(self) -> None:
        """Prepare → model_dump(mode='json') → deserialise → equivalent state + request."""
        classifier = _make_classifier()
        message = _make_message(
            findings=[_make_patient_finding(), _make_employee_finding()]
        )

        original = classifier.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = classifier.deserialise_prepare_result(raw)

        assert isinstance(restored.state, GDPRDataSubjectPrepareState)
        assert restored.state.run_id == original.state.run_id
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert len(restored.state.classified_findings) == len(
            original.state.classified_findings
        )

        assert len(restored.requests) == len(original.requests) == 1
        original_llm_request = original.requests[0]
        restored_llm_request = restored.requests[0]
        assert isinstance(original_llm_request, LLMRequest)
        assert isinstance(restored_llm_request, LLMRequest)
        assert restored_llm_request.request_id == original_llm_request.request_id
        assert restored_llm_request.batching_mode == original_llm_request.batching_mode
        assert restored_llm_request.run_id == original_llm_request.run_id

    def test_round_trip_without_llm_request(self) -> None:
        """LLM disabled → empty requests preserved through round-trip."""
        classifier = _make_classifier(enable_llm=False)
        message = _make_message(findings=[_make_patient_finding()])

        original = classifier.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = classifier.deserialise_prepare_result(raw)

        assert restored.requests == []
        assert restored.state.llm_enabled is False
        assert len(restored.state.classified_findings) == 1
