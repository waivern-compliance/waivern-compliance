"""Result builder for security document evidence extractor output.

Constructs SecurityDocumentContextOutput from classification results.
"""

import logging
from datetime import UTC, datetime

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema

from .schemas.types import (
    SecurityDocumentContextMetadata,
    SecurityDocumentContextModel,
    SecurityDocumentContextOutput,
    SecurityDocumentContextSummary,
)
from .types import DocumentItem, DomainClassificationResponse

logger = logging.getLogger(__name__)


def build_output_message(
    document_items: list[DocumentItem],
    document_contents: list[str],
    responses: list[DomainClassificationResponse],
    output_schema: Schema,
    *,
    llm_classification_enabled: bool,
) -> Message:
    """Build the complete output message from classification results.

    Args:
        document_items: Original document items (one per document).
        document_contents: Full text of each document (parallel to items).
        responses: LLM classification responses (one per document).
        output_schema: Schema for output validation.
        llm_classification_enabled: Whether LLM was used for classification.

    Returns:
        Complete validated output message.

    """
    findings = _build_findings(document_items, document_contents, responses)
    summary = _build_summary(findings)
    analysis_metadata = BaseAnalysisOutputMetadata(
        ruleset_used="n/a",
        llm_validation_enabled=llm_classification_enabled,
    )

    output_model = SecurityDocumentContextOutput(
        findings=findings,
        summary=summary,
        analysis_metadata=analysis_metadata,
    )

    result_data = output_model.model_dump(mode="json", exclude_none=True)

    message = Message(
        id=f"security_document_context_{datetime.now(UTC).isoformat()}",
        content=result_data,
        schema=output_schema,
    )

    message.validate()

    logger.info(f"Classified {len(findings)} documents into security domains")
    return message


def _build_findings(
    document_items: list[DocumentItem],
    document_contents: list[str],
    responses: list[DomainClassificationResponse],
) -> list[SecurityDocumentContextModel]:
    """Pair each document with its classification result."""
    findings: list[SecurityDocumentContextModel] = []

    for item, content, response in zip(
        document_items, document_contents, responses, strict=True
    ):
        findings.append(
            SecurityDocumentContextModel(
                filename=item.metadata.source,
                content=content,
                summary=response.summary,
                security_domains=response.security_domains,
                metadata=SecurityDocumentContextMetadata(
                    source=item.metadata.source,
                ),
            )
        )

    return findings


def _build_summary(
    findings: list[SecurityDocumentContextModel],
) -> SecurityDocumentContextSummary:
    """Build summary statistics from classified documents."""
    cross_cutting = sum(1 for f in findings if not f.security_domains)
    all_domains: set[str] = set()
    for finding in findings:
        for domain in finding.security_domains:
            all_domains.add(domain.value)

    return SecurityDocumentContextSummary(
        total_documents=len(findings),
        cross_cutting_count=cross_cutting,
        domain_coverage=sorted(all_domains),
    )
