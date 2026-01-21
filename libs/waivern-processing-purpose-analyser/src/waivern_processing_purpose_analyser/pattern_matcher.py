"""Pattern matcher class for processing purpose analysis."""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseMetadata
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
            results = self._dispatcher.find_matches(content, rule)

            if results:
                # Get first match for evidence extraction
                first_result = results[0]
                if first_result.first_match is None:
                    continue

                evidence = self._evidence_extractor.extract_from_match(
                    content,
                    first_result.first_match,
                    self._config.evidence_context_size,
                )

                # Collect all matched patterns
                matched_patterns = [
                    r.first_match.pattern for r in results if r.first_match
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
                    evidence=[evidence],
                    metadata=finding_metadata,
                )
                findings.append(finding)

        return findings
