"""Pattern matcher class for personal data analysis."""

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import (
    EvidenceExtractor,
    PatternMatcher,
    RulesetManager,
)
from waivern_core.schemas import BaseMetadata
from waivern_rulesets.personal_data import PersonalDataRule

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
        self._pattern_matcher = PatternMatcher()

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
        # Check if content is empty
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(self.config.ruleset, PersonalDataRule)
        findings: list[PersonalDataIndicatorModel] = []

        # Process each rule
        for rule in rules:
            # Check each pattern in the rule and collect all matches
            # Uses word boundary-aware matching to reduce false positives
            matched_patterns: list[str] = []
            for pattern in rule.patterns:
                if self._pattern_matcher.matches(content, pattern):
                    matched_patterns.append(pattern)

            # If any patterns matched, create a single indicator for this rule
            if matched_patterns:
                # Extract evidence using the first matched pattern as representative
                evidence_matches = self._evidence_extractor.extract_evidence(
                    content,
                    matched_patterns[0],
                    self.config.maximum_evidence_count,
                    self.config.evidence_context_size,
                )

                if evidence_matches:  # Only create indicator if we have evidence
                    # Create personal data indicator
                    finding_metadata = None
                    if metadata:
                        finding_metadata = PersonalDataIndicatorMetadata(
                            source=metadata.source,
                            context=metadata.context,
                        )

                    finding = PersonalDataIndicatorModel(
                        type=rule.name,
                        data_type=rule.data_type,
                        matched_patterns=matched_patterns,
                        evidence=evidence_matches,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings
