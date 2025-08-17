"""Pattern matcher function for personal data analysis."""

from typing import Any

from wct.analysers.runners.types import PatternMatcherContext

from .types import PersonalDataFindingMetadata, PersonalDataFindingModel


def personal_data_pattern_matcher(
    content: str,
    pattern: str,
    rule_metadata: dict[str, Any],
    context: PatternMatcherContext,
) -> PersonalDataFindingModel | None:
    """Pattern matcher function for personal data analysis.

    This function defines how personal data patterns are matched and how
    findings are structured for the PersonalDataAnalyser.

    Args:
        content: The content being analyzed
        pattern: The matched pattern
        rule_metadata: Metadata from the rule
        context: Strongly typed context with rule info, metadata, config, and utilities

    Returns:
        PersonalDataFindingModel object or None if no finding should be created

    """
    # Access typed context fields directly
    evidence_extractor = context.evidence_extractor
    metadata = context.metadata
    config = context.config
    rule_name = context.rule_name

    # Get configuration specific to personal data analysis
    maximum_evidence_count = config.maximum_evidence_count
    evidence_context_size = config.evidence_context_size

    # Extract evidence - find all occurrences of the pattern in the content
    evidence_matches = evidence_extractor.extract_evidence(
        content, pattern, maximum_evidence_count, evidence_context_size
    )

    if not evidence_matches:
        return None

    # Create personal data specific finding object with proper metadata
    finding_metadata = None
    if metadata:
        # Convert input metadata to PersonalDataFindingMetadata, preserving all fields
        metadata_dict = metadata.model_dump()
        finding_metadata = PersonalDataFindingMetadata(**metadata_dict)

    return PersonalDataFindingModel(
        type=rule_name,
        risk_level=context.risk_level,
        special_category=rule_metadata.get("special_category"),
        matched_pattern=pattern,
        evidence=evidence_matches,
        metadata=finding_metadata,
    )
