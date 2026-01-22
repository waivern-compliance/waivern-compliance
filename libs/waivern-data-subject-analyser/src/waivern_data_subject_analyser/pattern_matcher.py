"""Pattern matcher for data subject classification.

This module provides pattern matching to identify potential data subjects in content.
Pattern matching operates as a high-recall first pass - it finds all potential matches
based on keyword patterns (e.g., "customer", "patient", "employee").

Context-aware filtering and false positive reduction is handled by LLM validation,
which receives rich metadata (source, connector_type, table/field names, file paths)
to make intelligent decisions about whether matches are genuine data subject indicators.
"""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig, PatternMatchResult
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseMetadata, PatternMatchDetail
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
        self._dispatcher = RulePatternDispatcher()

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
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, DataSubjectIndicatorRule
        )
        indicators: list[DataSubjectIndicatorModel] = []

        # Group matched rules and results by subject category for confidence calculation
        category_matched_data: dict[
            str, list[tuple[DataSubjectIndicatorRule, list[PatternMatchResult]]]
        ] = {}

        # Find all matching rules and track results
        for rule in rules:
            results = self._dispatcher.find_matches(
                content,
                rule,
                proximity_threshold=self._config.evidence_proximity_threshold,
                max_representatives=self._config.maximum_evidence_count,
            )

            if results:
                category = rule.subject_category
                if category not in category_matched_data:
                    category_matched_data[category] = []
                category_matched_data[category].append((rule, results))

        # Create indicators for each category with matched data
        for category, matched_data in category_matched_data.items():
            # Extract rules for confidence calculation
            matched_rules = [rule for rule, _ in matched_data]

            # Collect all matched patterns and results
            all_results: list[PatternMatchResult] = []
            for _, results in matched_data:
                all_results.extend(results)

            matched_patterns = [
                PatternMatchDetail(pattern=r.pattern, match_count=r.match_count)
                for r in all_results
                if r.representative_matches
            ]

            # Extract evidence from representative matches (up to max evidence count)
            evidence_items = self._evidence_extractor.extract_from_results(
                content,
                all_results,
                self._config.evidence_context_size,
                self._config.maximum_evidence_count,
            )

            # Calculate confidence for this category
            confidence_score = self._confidence_scorer.calculate_confidence(
                matched_rules
            )

            # Create metadata for the indicator
            indicator_metadata = DataSubjectIndicatorMetadata(
                source=metadata.source,
                context=metadata.context,
            )

            # Create the indicator
            indicator = DataSubjectIndicatorModel(
                subject_category=category,
                confidence_score=confidence_score,
                evidence=evidence_items,
                matched_patterns=matched_patterns,
                metadata=indicator_metadata,
            )
            indicators.append(indicator)

        return indicators
