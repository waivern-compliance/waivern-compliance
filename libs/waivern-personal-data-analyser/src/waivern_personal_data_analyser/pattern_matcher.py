"""Pattern matcher class for personal data analysis."""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseMetadata, PatternMatchDetail
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule

from .schemas.types import PersonalDataIndicatorMetadata, PersonalDataIndicatorModel


class PersonalDataPatternMatcher:
    """Pattern matcher for personal data analysis.

    This class provides pattern matching functionality specifically for personal data
    detection, creating structured indicators for the PersonalDataAnalyser.
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
    ) -> list[PersonalDataIndicatorModel]:
        """Find all personal data patterns in content.

        Args:
            content: Text content to analyze
            metadata: Content metadata

        Returns:
            List of personal data indicators

        """
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, PersonalDataIndicatorRule
        )
        findings: list[PersonalDataIndicatorModel] = []

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

                finding = PersonalDataIndicatorModel(
                    category=rule.category,
                    matched_patterns=matched_patterns,
                    evidence=evidence_items,
                    metadata=PersonalDataIndicatorMetadata(
                        source=metadata.source,
                        context=metadata.context,
                    ),
                )
                findings.append(finding)

        return findings
