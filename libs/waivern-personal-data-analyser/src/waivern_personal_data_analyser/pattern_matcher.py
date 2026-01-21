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
        self.config = config
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
            self.config.ruleset, PersonalDataIndicatorRule
        )
        findings: list[PersonalDataIndicatorModel] = []

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
                    self.config.evidence_context_size,
                )

                # Collect all matched patterns with their counts
                matched_patterns = [
                    PatternMatchDetail(pattern=r.pattern, match_count=r.match_count)
                    for r in results
                    if r.first_match
                ]

                finding_metadata = None
                if metadata:
                    finding_metadata = PersonalDataIndicatorMetadata(
                        source=metadata.source,
                        context=metadata.context,
                    )

                finding = PersonalDataIndicatorModel(
                    category=rule.category,
                    matched_patterns=matched_patterns,
                    evidence=[evidence],
                    metadata=finding_metadata,
                )
                findings.append(finding)

        return findings
