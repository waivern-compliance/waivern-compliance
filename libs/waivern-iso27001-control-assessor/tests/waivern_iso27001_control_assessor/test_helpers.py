"""Shared test helpers for waivern-iso27001-control-assessor tests."""

from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_schemas.iso27001_assessment import ISO27001AssessmentOutput

RUN_ID = "test-run-001"
OUTPUT_SCHEMA = Schema("iso27001_assessment", "1.0.0")


def make_evidence_message(
    findings: list[dict[str, object]],
) -> Message:
    """Build a security_evidence/1.0.0 Message from finding dicts."""
    return Message(
        id="test_evidence",
        content={
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "domains_identified": 0,
                "domains": [],
            },
            "analysis_metadata": {
                "ruleset_used": "test",
                "llm_validation_enabled": False,
            },
        },
        schema=Schema("security_evidence", "1.0.0"),
        run_id=RUN_ID,
    )


def make_document_message(
    findings: list[dict[str, object]],
) -> Message:
    """Build a security_document_context/1.0.0 Message from finding dicts."""
    return Message(
        id="test_document",
        content={
            "findings": findings,
            "summary": {
                "total_documents": len(findings),
                "cross_cutting_count": 0,
                "domain_coverage": [],
            },
            "analysis_metadata": {
                "ruleset_used": "test",
                "llm_validation_enabled": False,
            },
        },
        schema=Schema("security_document_context", "1.0.0"),
        run_id=RUN_ID,
    )


def make_evidence_finding(
    security_domain: str = "encryption",
    evidence_type: str = "CODE",
    require_review: bool | None = None,
) -> dict[str, object]:
    """Build a minimal SecurityEvidenceModel dict."""
    return {
        "id": "ev-1",
        "metadata": {"source": "test.py"},
        "evidence_type": evidence_type,
        "security_domain": security_domain,
        "polarity": "positive",
        "confidence": 0.9,
        "description": "Test evidence",
        "require_review": require_review,
    }


def make_document_finding(
    security_domains: list[str] | None = None,
    filename: str = "policy.md",
) -> dict[str, object]:
    """Build a minimal SecurityDocumentContextModel dict."""
    return {
        "id": "doc-1",
        "filename": filename,
        "content": "Test document content",
        "summary": "Test document summary",
        "security_domains": security_domains or [],
        "metadata": {"source": filename},
    }


def parse_output(result: Message) -> ISO27001AssessmentOutput:
    """Parse an assessor output Message into the typed model."""
    return ISO27001AssessmentOutput.model_validate(result.content)
