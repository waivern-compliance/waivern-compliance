"""Tests for SecurityDocumentEvidenceExtractor.process() — standalone degraded-mode fallback.

process() delegates to prepare/finalise with LLM forced off. These tests
verify document parsing and output structure still work correctly through
the standalone path.
"""

import pytest
from waivern_core.testing import ProcessorContractTests

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
)
from waivern_security_document_evidence_extractor.types import (
    SecurityDocumentEvidenceExtractorConfig,
)

from .test_helpers import OUTPUT_SCHEMA, make_input_message, parse_output


def _make_extractor() -> SecurityDocumentEvidenceExtractor:
    """Build an extractor without LLM service (standalone mode)."""
    config = SecurityDocumentEvidenceExtractorConfig()
    return SecurityDocumentEvidenceExtractor(config=config)


class TestSecurityDocumentEvidenceExtractorContract(
    ProcessorContractTests[SecurityDocumentEvidenceExtractor],
):
    """Contract tests for SecurityDocumentEvidenceExtractor."""

    @pytest.fixture
    def processor_class(self):
        return SecurityDocumentEvidenceExtractor


# =============================================================================
# Content Preservation
# =============================================================================


class TestContentPreservation:
    """Tests for document content and metadata pass-through."""

    def test_full_content_preserved(self) -> None:
        """Document content in output equals input file text verbatim."""
        raw_text = "Full policy text\nwith newlines\nand special chars: £€¥"
        extractor = _make_extractor()
        msg = make_input_message([{"content": raw_text, "source": "policy.txt"}])

        result = extractor.process([msg], OUTPUT_SCHEMA)

        output = parse_output(result)
        assert output.findings[0].content == raw_text

    def test_filename_preserved(self) -> None:
        """Output filename matches metadata.source from input."""
        extractor = _make_extractor()
        msg = make_input_message(
            [{"content": "text", "source": "access-control-policy.docx"}]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.filename == "access-control-policy.docx"
        assert finding.metadata.source == "access-control-policy.docx"


# =============================================================================
# Degraded Mode Behaviour
# =============================================================================


class TestDegradedMode:
    """Tests for degraded-mode output (LLM unavailable)."""

    def test_all_documents_get_empty_domains(self) -> None:
        """All documents get security_domains=[] without LLM."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Doc A", "source": "a.docx"},
                {"content": "Doc B", "source": "b.docx"},
            ]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        output = parse_output(result)
        assert all(f.security_domains == [] for f in output.findings)

    def test_degraded_summary_all_cross_cutting(self) -> None:
        """Summary: cross_cutting_count = total, domain_coverage = []."""
        extractor = _make_extractor()
        msg = make_input_message(
            [
                {"content": "Doc A", "source": "a.docx"},
                {"content": "Doc B", "source": "b.docx"},
            ]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        output = parse_output(result)
        assert output.summary.total_documents == 2
        assert output.summary.cross_cutting_count == 2
        assert output.summary.domain_coverage == []

    def test_analysis_metadata_llm_disabled(self) -> None:
        """analysis_metadata.llm_validation_enabled = False."""
        extractor = _make_extractor()
        msg = make_input_message([{"content": "Doc A", "source": "a.docx"}])

        result = extractor.process([msg], OUTPUT_SCHEMA)

        assert result.content["analysis_metadata"]["llm_validation_enabled"] is False
