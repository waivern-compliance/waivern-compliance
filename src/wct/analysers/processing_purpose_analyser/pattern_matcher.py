"""Pattern matcher function for processing purpose analysis."""

from typing import Any

# Default confidence for all findings (from original analyser)
DEFAULT_FINDING_CONFIDENCE = 0.5


def processing_purpose_pattern_matcher(
    content: str, pattern: str, rule_metadata: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any] | None:
    """Pattern matcher function for processing purpose analysis.

    This function defines how processing purpose patterns are matched and how
    findings are structured for the ProcessingPurposeAnalyser.

    Args:
        content: The content being analyzed
        pattern: The matched pattern
        rule_metadata: Metadata from the rule
        context: Additional context including rule info, metadata, config, and utilities

    Returns:
        Processing purpose finding dictionary or None if no finding should be created

    """
    evidence_extractor = context["evidence_extractor"]
    metadata = context["metadata"]
    config = context["config"]
    rule_name = context["rule_name"]  # This is the purpose_name

    # Check if content is empty
    if not content.strip():
        return None

    # Get configuration specific to processing purpose analysis
    max_evidence = config.get("max_evidence", 3)
    evidence_context_size = config.get("evidence_context_size", "medium")

    # Extract evidence snippets
    evidence = evidence_extractor.extract_evidence(
        content, pattern, max_evidence, evidence_context_size
    )

    if not evidence:  # Only create finding if we have evidence
        return None

    # Use default confidence for all findings (from original implementation)
    confidence = config.get("confidence", DEFAULT_FINDING_CONFIDENCE)

    # Create processing purpose specific finding structure
    finding = {
        "purpose": rule_name,  # Processing purpose name
        "purpose_category": rule_metadata.get("purpose_category", "OPERATIONAL"),
        "risk_level": context.get("risk_level", "low"),
        "compliance_relevance": rule_metadata.get("compliance_relevance", ["GDPR"]),
        "matched_pattern": pattern,
        "confidence": confidence,
        "evidence": evidence,
        "metadata": metadata.copy() if metadata else {},
    }

    return finding
