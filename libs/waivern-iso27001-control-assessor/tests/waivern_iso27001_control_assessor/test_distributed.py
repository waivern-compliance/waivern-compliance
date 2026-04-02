"""Tests for ISO27001Assessor DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract:
- prepare() classifies evidence and builds LLMRequest when appropriate
- finalise() interprets dispatch results into assessment verdicts
- deserialise_prepare_result() round-trips through JSON serialisation
"""

from unittest.mock import Mock

from waivern_llm import LLMService
from waivern_llm.types import BatchingMode, LLMDispatchResult, LLMRequest
from waivern_schemas.iso27001_assessment import (
    ControlStatus,
    EvidenceStatus,
)

from waivern_iso27001_control_assessor import ISO27001Assessor
from waivern_iso27001_control_assessor.prompts.prompt_builder import (
    ISO27001PromptBuilder,
)
from waivern_iso27001_control_assessor.prompts.response_model import (
    ISO27001LLMResponse,
)
from waivern_iso27001_control_assessor.types import ISO27001AssessorConfig

from .test_helpers import (
    OUTPUT_SCHEMA,
    make_evidence_finding,
    make_evidence_message,
    parse_output,
)


def _make_assessor(
    control_ref: str,
    *,
    llm_service: LLMService | None = None,
) -> ISO27001Assessor:
    """Build an assessor with optional LLM service.

    Args:
        control_ref: ISO 27001 control reference (e.g. "A.8.24").
        llm_service: LLM service instance. Pass None for LLM-disabled mode.
            Defaults to a mock LLMService (LLM enabled).

    """
    config = ISO27001AssessorConfig.from_properties({"control_ref": control_ref})
    if llm_service is None:
        llm_service = Mock(spec=LLMService)
    return ISO27001Assessor(config=config, llm_service=llm_service)


def _make_assessor_without_llm(control_ref: str) -> ISO27001Assessor:
    """Build an assessor with LLM disabled (llm_service=None)."""
    config = ISO27001AssessorConfig.from_properties({"control_ref": control_ref})
    return ISO27001Assessor(config=config, llm_service=None)


# =============================================================================
# Prepare
# =============================================================================


class TestPrepare:
    """Tests for prepare() — evidence classification and request building."""

    def test_no_evidence_returns_empty_requests(self) -> None:
        """Empty findings → empty requests, evidence_status=INSUFFICIENT_EVIDENCE."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message([])

        result = assessor.prepare(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE

    def test_requires_attestation_returns_empty_requests(self) -> None:
        """evidence_required gate fails → empty requests, REQUIRES_ATTESTATION.

        A.5.15 has evidence_required=[DOCUMENT]. Providing only technical
        evidence fails the gate.
        """
        assessor = _make_assessor("A.5.15")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="access_control")]
        )

        result = assessor.prepare(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.evidence_status == EvidenceStatus.REQUIRES_ATTESTATION

    def test_automated_with_llm_builds_llm_request(self) -> None:
        """Matching evidence + LLM enabled → LLMRequest with correct properties.

        A.8.24 (cryptography) has security_domains=[encryption].
        Providing matching evidence should produce an LLMRequest with
        INDEPENDENT batching and the ISO27001PromptBuilder.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        result = assessor.prepare(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.evidence_status == EvidenceStatus.AUTOMATED
        assert result.state.llm_enabled is True

        llm_request = result.requests[0]
        assert isinstance(llm_request, LLMRequest)
        assert llm_request.batching_mode == BatchingMode.INDEPENDENT
        assert isinstance(llm_request.prompt_builder, ISO27001PromptBuilder)
        assert llm_request.response_model is ISO27001LLMResponse
        assert len(llm_request.groups) == 1
        assert llm_request.groups[0].group_id == "A.8.24"

    def test_automated_without_llm_returns_empty_requests(self) -> None:
        """Matching evidence + LLM disabled → empty requests, llm_enabled=False.

        Even though evidence is sufficient for automated assessment,
        the absence of LLM service means no dispatch request is built.
        """
        assessor = _make_assessor_without_llm("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        result = assessor.prepare(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.evidence_status == EvidenceStatus.AUTOMATED
        assert result.state.llm_enabled is False


# =============================================================================
# Finalise
# =============================================================================


class TestFinalise:
    """Tests for finalise() — verdict production from state and results."""

    def test_insufficient_evidence_produces_not_assessed(self) -> None:
        """INSUFFICIENT_EVIDENCE state → NOT_ASSESSED with correct rationale."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message([])

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        result = assessor.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.NOT_ASSESSED
        assert finding.evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        assert "No relevant evidence found" in finding.rationale

    def test_requires_attestation_produces_not_assessed(self) -> None:
        """REQUIRES_ATTESTATION state → NOT_ASSESSED with attestation rationale.

        A.5.15 has evidence_required=[DOCUMENT]. Providing only technical
        evidence fails the gate.
        """
        assessor = _make_assessor("A.5.15")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="access_control")]
        )

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        result = assessor.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.NOT_ASSESSED
        assert finding.evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
        assert "Awaiting document evidence" in finding.rationale

    def test_automated_without_llm_produces_not_assessed(self) -> None:
        """AUTOMATED + llm_enabled=False → NOT_ASSESSED with LLM unavailable rationale."""
        assessor = _make_assessor_without_llm("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        result = assessor.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.NOT_ASSESSED
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert "LLM" in finding.rationale

    def test_compliant_llm_result(self) -> None:
        """AUTOMATED + compliant LLMDispatchResult → COMPLIANT verdict."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[
                {
                    "status": "compliant",
                    "rationale": "AES-256 encryption is correctly implemented.",
                    "gap_description": None,
                    "recommended_actions": [],
                }
            ],
            skipped=[],
        )

        result = assessor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.COMPLIANT
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.gap_description is None
        assert finding.rationale == "AES-256 encryption is correctly implemented."
        assert output.summary.compliant_count == 1

    def test_non_compliant_llm_result(self) -> None:
        """AUTOMATED + non_compliant LLMDispatchResult → NON_COMPLIANT with gap."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[
                {
                    "status": "non_compliant",
                    "rationale": "MD5 is used for password hashing.",
                    "gap_description": "Replace MD5 with bcrypt or Argon2.",
                    "recommended_actions": [
                        "Replace MD5 password hashing with bcrypt.",
                        "Update cryptography policy.",
                    ],
                }
            ],
            skipped=[],
        )

        result = assessor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.NON_COMPLIANT
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.gap_description == "Replace MD5 with bcrypt or Argon2."
        assert len(finding.recommended_actions) == 2
        assert output.summary.non_compliant_count == 1

    def test_empty_llm_responses_produces_not_assessed(self) -> None:
        """AUTOMATED + LLMDispatchResult with no responses → NOT_ASSESSED."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        prepare_result = assessor.prepare(
            inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA
        )
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[],
            skipped=[],
        )

        result = assessor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.status == ControlStatus.NOT_ASSESSED
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert "exceeded context window" in finding.rationale


# =============================================================================
# Deserialise
# =============================================================================


class TestDeserialise:
    """Tests for deserialise_prepare_result() round-trip fidelity."""

    def test_round_trip_serialisation(self) -> None:
        """prepare() → model_dump → deserialise → equivalent state and requests.

        Validates the resume path: the executor persists PrepareResult via
        model_dump(mode="json") and restores it via deserialise_prepare_result().
        State fields and request metadata must survive the round-trip.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [make_evidence_finding(security_domain="encryption")]
        )

        original = assessor.prepare(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)
        raw = original.model_dump(mode="json")
        restored = assessor.deserialise_prepare_result(raw)

        # State fields
        assert restored.state.rule.control_ref == original.state.rule.control_ref
        assert restored.state.evidence_status == original.state.evidence_status
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert restored.state.run_id == original.state.run_id
        assert len(restored.state.evidence) == len(original.state.evidence)

        # Request metadata (prompt_builder/response_model are excluded from serialisation)
        assert len(restored.requests) == len(original.requests)
        assert restored.requests[0].request_id == original.requests[0].request_id
        assert restored.requests[0].batching_mode == original.requests[0].batching_mode
        assert restored.requests[0].run_id == original.requests[0].run_id
