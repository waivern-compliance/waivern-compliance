"""Tests for SecurityDocumentEvidenceExtractor DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract:
- prepare() parses documents and builds LLMRequest when LLM available
- finalise() maps dispatch results into classified document output
- deserialise_prepare_result() round-trips through JSON serialisation
"""

from unittest.mock import Mock

from waivern_llm import LLMService
from waivern_llm.types import BatchingMode, LLMDispatchResult, LLMRequest
from waivern_schemas.security_domain import SecurityDomain

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
)
from waivern_security_document_evidence_extractor.prompts.prompt_builder import (
    DomainClassificationPromptBuilder,
)
from waivern_security_document_evidence_extractor.types import (
    DomainClassificationResponse,
    SecurityDocumentEvidenceExtractorConfig,
)

from .test_helpers import OUTPUT_SCHEMA, RUN_ID, make_input_message, parse_output


def _make_extractor(
    *,
    llm_service: LLMService | None = None,
) -> SecurityDocumentEvidenceExtractor:
    """Build an extractor with optional LLM service.

    Args:
        llm_service: LLM service instance. Pass None for LLM-disabled mode.
            Defaults to a mock LLMService (LLM enabled).

    """
    config = SecurityDocumentEvidenceExtractorConfig()
    if llm_service is None:
        llm_service = Mock(spec=LLMService)
    return SecurityDocumentEvidenceExtractor(config=config, llm_service=llm_service)


def _make_extractor_without_llm() -> SecurityDocumentEvidenceExtractor:
    """Build an extractor with LLM disabled (llm_service=None)."""
    config = SecurityDocumentEvidenceExtractorConfig()
    return SecurityDocumentEvidenceExtractor(config=config, llm_service=None)


# =============================================================================
# Prepare
# =============================================================================


class TestPrepare:
    """Tests for prepare() — document parsing and request building."""

    def test_single_document_with_llm_builds_request(self) -> None:
        """One document + LLM enabled → LLMRequest with correct properties."""
        extractor = _make_extractor()
        msg = make_input_message(
            [{"content": "Encryption policy", "source": "enc.docx"}]
        )

        result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.llm_enabled is True

        llm_request = result.requests[0]
        assert isinstance(llm_request, LLMRequest)
        assert llm_request.batching_mode == BatchingMode.INDEPENDENT
        assert isinstance(llm_request.prompt_builder, DomainClassificationPromptBuilder)
        assert llm_request.response_model is DomainClassificationResponse
        assert len(llm_request.groups) == 1
        assert llm_request.groups[0].group_id == "enc.docx"

    def test_multiple_documents_build_one_group_per_document(self) -> None:
        """N documents → single LLMRequest with N ItemGroups, each group_id=filename."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Encryption policy", "source": "enc.docx"},
                {"content": "Incident response plan", "source": "incident.docx"},
                {"content": "ISMS overview", "source": "isms.md"},
            ]
        )

        result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        llm_request = result.requests[0]
        assert isinstance(llm_request, LLMRequest)
        assert len(llm_request.groups) == 3
        assert llm_request.groups[0].group_id == "enc.docx"
        assert llm_request.groups[1].group_id == "incident.docx"
        assert llm_request.groups[2].group_id == "isms.md"

    def test_without_llm_returns_empty_requests(self) -> None:
        """No llm_service → empty requests, llm_enabled=False in state."""
        extractor = _make_extractor_without_llm()
        msg = make_input_message([{"content": "Policy doc", "source": "policy.md"}])

        result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False

    def test_state_captures_documents_and_contents(self) -> None:
        """State contains correct document_items, document_contents, and run_id."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Doc A text", "source": "a.docx"},
                {"content": "Doc B text", "source": "b.docx"},
            ]
        )

        result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)

        assert len(result.state.document_items) == 2
        assert len(result.state.document_contents) == 2
        assert result.state.document_items[0].metadata.source == "a.docx"
        assert result.state.document_items[1].metadata.source == "b.docx"
        assert result.state.document_contents[0] == "Doc A text"
        assert result.state.document_contents[1] == "Doc B text"
        assert result.state.run_id == RUN_ID


# =============================================================================
# Finalise
# =============================================================================


class TestFinalise:
    """Tests for finalise() — output production from state and results."""

    def test_llm_disabled_produces_degraded_output(self) -> None:
        """llm_enabled=False → all docs get empty domains, content as summary."""
        extractor = _make_extractor_without_llm()
        msg = make_input_message(
            [
                {"content": "Encryption policy text", "source": "enc.docx"},
                {"content": "Incident plan text", "source": "incident.docx"},
            ]
        )

        prepare_result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)
        result = extractor.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        output = parse_output(result)
        assert len(output.findings) == 2
        for i, finding in enumerate(output.findings):
            assert finding.security_domains == []
            assert finding.summary == prepare_result.state.document_contents[i]

    def test_llm_result_maps_to_classified_output(self) -> None:
        """LLMDispatchResult with responses → domains and summaries in output."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Encryption policy", "source": "enc.docx"},
            ]
        )

        prepare_result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[
                {
                    "security_domains": ["encryption", "data_protection"],
                    "summary": "Covers AES-256 encryption and key management.",
                }
            ],
            skipped=[],
        )

        result = extractor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert set(finding.security_domains) == {
            SecurityDomain.ENCRYPTION,
            SecurityDomain.DATA_PROTECTION,
        }
        assert finding.summary == "Covers AES-256 encryption and key management."
        assert finding.content == "Encryption policy"

    def test_empty_llm_responses_produces_degraded_output(self) -> None:
        """LLMDispatchResult with empty responses → degraded output."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Policy text", "source": "policy.docx"},
            ]
        )

        prepare_result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[],
            skipped=[],
        )

        result = extractor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.security_domains == []
        assert finding.summary == "Policy text"

    def test_output_summary_statistics(self) -> None:
        """Summary has correct total_documents, cross_cutting_count, domain_coverage."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Encryption + DLP", "source": "enc.docx"},
                {"content": "ISMS overview", "source": "isms.docx"},
                {"content": "TLS config", "source": "tls.docx"},
            ]
        )

        prepare_result = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)
        llm_result = LLMDispatchResult(
            request_id=prepare_result.requests[0].request_id,
            model_name="claude-sonnet-4-5-20250929",
            responses=[
                {
                    "security_domains": ["encryption", "data_protection"],
                    "summary": "Encryption and DLP summary",
                },
                {
                    "security_domains": [],
                    "summary": "ISMS overview summary",
                },
                {
                    "security_domains": ["encryption"],
                    "summary": "TLS configuration summary",
                },
            ],
            skipped=[],
        )

        result = extractor.finalise(prepare_result.state, [llm_result], OUTPUT_SCHEMA)

        output = parse_output(result)
        assert output.summary.total_documents == 3
        assert output.summary.cross_cutting_count == 1
        assert sorted(output.summary.domain_coverage) == [
            "data_protection",
            "encryption",
        ]


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
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Encryption policy", "source": "enc.docx"},
            ]
        )

        original = extractor.prepare(inputs=[msg], output_schema=OUTPUT_SCHEMA)
        raw = original.model_dump(mode="json")
        restored = extractor.deserialise_prepare_result(raw)

        # State fields
        assert len(restored.state.document_items) == len(original.state.document_items)
        assert (
            restored.state.document_items[0].metadata.source
            == original.state.document_items[0].metadata.source
        )
        assert restored.state.document_contents == original.state.document_contents
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert restored.state.run_id == original.state.run_id

        # Request metadata (prompt_builder/response_model excluded from serialisation)
        assert len(restored.requests) == len(original.requests)
        assert restored.requests[0].request_id == original.requests[0].request_id
        assert restored.requests[0].batching_mode == original.requests[0].batching_mode
        assert restored.requests[0].run_id == original.requests[0].run_id
