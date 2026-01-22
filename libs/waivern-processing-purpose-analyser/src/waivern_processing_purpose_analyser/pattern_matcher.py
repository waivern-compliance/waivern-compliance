"""Pattern matcher class for processing purpose analysis."""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseMetadata, PatternMatchDetail
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from .schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)


class ProcessingPurposePatternMatcher:
    """Pattern matcher for processing purpose analysis.

    This class provides pattern matching functionality specifically for processing purpose
    detection, creating structured findings for the ProcessingPurposeAnalyser.
    """

    def __init__(self, config: PatternMatchingConfig) -> None:
        """Initialise the pattern matcher with configuration.

        Args:
            config: Pattern matching configuration

        """
        self._config = config
        self._evidence_extractor = EvidenceExtractor()
        self._ruleset_manager = RulesetManager()
        self._dispatcher = RulePatternDispatcher()

    def find_patterns(
        self,
        content: str,
        metadata: BaseMetadata,
    ) -> list[ProcessingPurposeFindingModel]:
        """Find all processing purpose patterns in content.

        Args:
            content: Text content to analyze
            metadata: Content metadata

        Returns:
            List of processing purpose findings

        """
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, ProcessingPurposeRule
        )
        findings: list[ProcessingPurposeFindingModel] = []

        for rule in rules:
            results = self._dispatcher.find_matches(
                content,
                rule,
                proximity_threshold=self._config.evidence_proximity_threshold,
                max_representatives=self._config.maximum_evidence_count,
            )

            if results:
                # Extract evidence from representative matches (up to max evidence count)
                evidence_items = self._evidence_extractor.extract_from_results(
                    content,
                    results,
                    self._config.evidence_context_size,
                    self._config.maximum_evidence_count,
                )

                # Collect all matched patterns with their counts
                matched_patterns = [
                    PatternMatchDetail(pattern=r.pattern, match_count=r.match_count)
                    for r in results
                    if r.representative_matches
                ]

                finding_metadata = None
                if metadata:
                    finding_metadata = ProcessingPurposeFindingMetadata(
                        source=metadata.source,
                        context=metadata.context,
                    )

                finding = ProcessingPurposeFindingModel(
                    purpose=rule.name,
                    purpose_category=rule.purpose_category,
                    matched_patterns=matched_patterns,
                    evidence=evidence_items,
                    metadata=finding_metadata,
                )
                findings.append(finding)

        return findings
