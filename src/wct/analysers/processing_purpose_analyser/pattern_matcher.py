"""Pattern matcher function for processing purpose analysis."""

from typing import Any

from wct.analysers.runners.types import PatternMatcherContext

from .types import ProcessingPurposeFindingMetadata, ProcessingPurposeFindingModel

# Default confidence for all findings (from original analyser)
DEFAULT_FINDING_CONFIDENCE = 0.5


def processing_purpose_pattern_matcher(
    content: str,
    pattern: str,
    rule_metadata: dict[str, Any],
    context: PatternMatcherContext,
) -> ProcessingPurposeFindingModel | None:
    """Pattern matcher function for processing purpose analysis.

    This function defines how processing purpose patterns are matched and how
    findings are structured for the ProcessingPurposeAnalyser.

    Args:
        content: The content being analyzed
        pattern: The matched pattern
        rule_metadata: Metadata from the rule
        context: Strongly typed context with rule info, metadata, config, and utilities

    Returns:
        Processing purpose finding dictionary or None if no finding should be created

    """
    # Access typed context fields directly
    evidence_extractor = context.evidence_extractor
    metadata = context.metadata
    config = context.config
    rule_name = context.rule_name  # This is the purpose_name

    # Check if content is empty
    if not content.strip():
        return None

    # Get configuration specific to processing purpose analysis
    max_evidence = config.maximum_evidence_count
    evidence_context_size = config.evidence_context_size

    # Extract evidence snippets
    evidence = evidence_extractor.extract_evidence(
        content, pattern, max_evidence, evidence_context_size
    )

    if not evidence:  # Only create finding if we have evidence
        return None

    # Use default confidence for all findings (from original implementation)
    # Note: This is processing purpose specific and not in PatternMatchingRunnerConfig
    confidence = DEFAULT_FINDING_CONFIDENCE

    # Create processing purpose specific finding structure with proper metadata
    finding_metadata = None
    if metadata:
        # Convert input metadata to ProcessingPurposeFindingMetadata, preserving all fields
        metadata_dict = metadata.model_dump()
        finding_metadata = ProcessingPurposeFindingMetadata(**metadata_dict)

    return ProcessingPurposeFindingModel(
        purpose=rule_name,
        purpose_category=rule_metadata.get("purpose_category", "OPERATIONAL"),
        risk_level=context.risk_level,
        compliance_relevance=rule_metadata.get("compliance_relevance", ["GDPR"]),
        matched_pattern=pattern,
        confidence=confidence,
        evidence=evidence,
        metadata=finding_metadata,
    )
