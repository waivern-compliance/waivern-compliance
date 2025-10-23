"""Pattern matcher class for personal data analysis."""

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseFindingCompliance, BaseMetadata
from waivern_rulesets.personal_data import PersonalDataRule

from .types import PersonalDataFindingMetadata, PersonalDataFindingModel


class PersonalDataPatternMatcher:
    """Pattern matcher for personal data analysis.

    This class provides pattern matching functionality specifically for personal data
    detection, creating structured findings for the PersonalDataAnalyser.
    """

    def __init__(self, config: PatternMatchingConfig) -> None:
        """Initialise the pattern matcher with configuration.

        Args:
            config: Pattern matching configuration

        """
        self.config = config
        self.evidence_extractor = EvidenceExtractor()
        self.ruleset_manager = RulesetManager()

    def find_patterns(
        self,
        content: str,
        metadata: BaseMetadata,
    ) -> list[PersonalDataFindingModel]:
        """Find all personal data patterns in content.

        Args:
            content: Text content to analyze
            metadata: Content metadata

        Returns:
            List of personal data findings

        """
        # Check if content is empty
        if not content.strip():
            return []

        rules = self.ruleset_manager.get_rules(self.config.ruleset, PersonalDataRule)
        findings: list[PersonalDataFindingModel] = []
        content_lower = content.lower()

        # Process each rule
        for rule in rules:
            # Check each pattern in the rule and collect all matches
            matched_patterns: list[str] = []
            for pattern in rule.patterns:
                if pattern.lower() in content_lower:
                    matched_patterns.append(pattern)

            # If any patterns matched, create a single finding for this rule
            if matched_patterns:
                # Extract evidence using the first matched pattern as representative
                evidence_matches = self.evidence_extractor.extract_evidence(
                    content,
                    matched_patterns[0],
                    self.config.maximum_evidence_count,
                    self.config.evidence_context_size,
                )

                if evidence_matches:  # Only create finding if we have evidence
                    # Create personal data specific finding
                    finding_metadata = None
                    if metadata:
                        finding_metadata = PersonalDataFindingMetadata(
                            source=metadata.source
                        )

                    compliance_data = [
                        BaseFindingCompliance(
                            regulation=comp.regulation, relevance=comp.relevance
                        )
                        for comp in rule.compliance
                    ]

                    finding = PersonalDataFindingModel(
                        type=rule.name,
                        data_type=rule.data_type,
                        risk_level=rule.risk_level,
                        special_category=rule.special_category,
                        matched_patterns=matched_patterns,
                        compliance=compliance_data,
                        evidence=evidence_matches,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings
