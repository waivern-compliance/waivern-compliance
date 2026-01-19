"""Pattern matcher for data subject classification.

This module provides pattern matching to identify potential data subjects in content.
Pattern matching operates as a high-recall first pass - it finds all potential matches
based on keyword patterns (e.g., "customer", "patient", "employee").

Context-aware filtering and false positive reduction is handled by LLM validation,
which receives rich metadata (source, connector_type, table/field names, file paths)
to make intelligent decisions about whether matches are genuine data subject indicators.
"""

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import (
    EvidenceExtractor,
    PatternMatcher,
    RulesetManager,
)
from waivern_core.schemas import BaseMetadata
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule

from .confidence_scorer import DataSubjectConfidenceScorer
from .schemas.types import DataSubjectIndicatorMetadata, DataSubjectIndicatorModel


class DataSubjectPatternMatcher:
    """Pattern matcher for data subject classification.

    This class provides pattern matching functionality specifically for data subject
    detection, creating structured findings with confidence scoring.
    """

    def __init__(self, config: PatternMatchingConfig) -> None:
        """Initialise the pattern matcher with configuration.

        Args:
            config: Pattern matching configuration

        """
        self._config = config
        self._evidence_extractor = EvidenceExtractor()
        self._ruleset_manager = RulesetManager()
        self._confidence_scorer = DataSubjectConfidenceScorer()
        self._pattern_matcher = PatternMatcher()

    def find_patterns(
        self, content: str, metadata: BaseMetadata
    ) -> list[DataSubjectIndicatorModel]:
        """Find data subject patterns in content with confidence scoring.

        Args:
            content: Text content to analyze
            metadata: Content metadata for context filtering

        Returns:
            List of data subject indicators with confidence scores

        """
        # Check if content is empty
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, DataSubjectIndicatorRule
        )
        indicators: list[DataSubjectIndicatorModel] = []

        # Group matched rules and patterns by subject category for confidence calculation
        category_matched_data: dict[
            str, list[tuple[DataSubjectIndicatorRule, list[str]]]
        ] = {}

        # Find all matching rules and track which patterns matched
        for rule in rules:
            # Check each pattern in the rule and collect all matches
            # Uses word boundary-aware matching to reduce false positives
            matched_patterns_for_rule: list[str] = []
            for pattern in rule.patterns:
                if self._pattern_matcher.matches(content, pattern):
                    matched_patterns_for_rule.append(pattern)

            # If any patterns matched, add the rule and its matched patterns
            if matched_patterns_for_rule:
                category = rule.subject_category
                if category not in category_matched_data:
                    category_matched_data[category] = []
                category_matched_data[category].append(
                    (rule, matched_patterns_for_rule)
                )

        # Create indicators for each category with matched data
        for category, matched_data in category_matched_data.items():
            # Extract rules and patterns from matched data
            matched_rules = [rule for rule, _ in matched_data]
            matched_patterns: list[str] = []
            for _, patterns in matched_data:
                matched_patterns.extend(patterns)

            # Calculate confidence for this category
            confidence_score = self._confidence_scorer.calculate_confidence(
                matched_rules
            )

            # Extract evidence for the first matched pattern (representative)
            evidence = self._evidence_extractor.extract_evidence(
                content,
                matched_patterns[0],  # Use first actually matched pattern for evidence
                self._config.maximum_evidence_count,
                self._config.evidence_context_size,
            )

            if evidence:  # Only create indicator if we have evidence
                # Create metadata for the indicator
                indicator_metadata = DataSubjectIndicatorMetadata(
                    source=metadata.source,
                    context=metadata.context,
                )

                # Create the indicator
                # Note: Risk modifiers (vulnerable, minor, etc.) are GDPR-specific
                # and will be detected by the GDPRDataSubjectClassifier
                indicator = DataSubjectIndicatorModel(
                    subject_category=category,
                    confidence_score=confidence_score,
                    evidence=evidence,
                    matched_patterns=matched_patterns,
                    metadata=indicator_metadata,
                )
                indicators.append(indicator)

        return indicators
