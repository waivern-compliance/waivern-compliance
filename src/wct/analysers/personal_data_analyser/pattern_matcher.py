"""Pattern matcher function for personal data analysis."""

from typing import Any


def personal_data_pattern_matcher(
    content: str, pattern: str, rule_metadata: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any] | None:
    """Pattern matcher function for personal data analysis.

    This function defines how personal data patterns are matched and how
    findings are structured for the PersonalDataAnalyser.

    Args:
        content: The content being analyzed
        pattern: The matched pattern
        rule_metadata: Metadata from the rule
        context: Additional context including rule info, metadata, config, and utilities

    Returns:
        Personal data finding dictionary or None if no finding should be created
    """
    evidence_extractor = context["evidence_extractor"]
    metadata = context["metadata"]
    config = context["config"]
    rule_name = context["rule_name"]

    # Get configuration specific to personal data analysis
    maximum_evidence_count = config.get("maximum_evidence_count", 3)
    evidence_context_size = config.get("evidence_context_size", "small")

    # Extract evidence - find all occurrences of the pattern in the content
    evidence_matches = evidence_extractor.extract_evidence(
        content, pattern, maximum_evidence_count, evidence_context_size
    )

    if not evidence_matches:
        return None

    # Pass metadata as-is since source is guaranteed by schema
    finding_metadata = metadata.copy() if metadata else {}

    # Create personal data specific finding structure
    finding = {
        "type": rule_name,
        "risk_level": context["risk_level"],
        "special_category": rule_metadata["special_category"],  # Personal data specific
        "matched_pattern": pattern,
        "evidence": evidence_matches,
        "metadata": finding_metadata,
    }

    return finding
