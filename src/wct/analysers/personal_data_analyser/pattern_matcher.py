"""Pattern matcher class for personal data analysis."""

from pydantic import BaseModel

from wct.analysers.types import FindingComplianceData, PatternMatchingConfig
from wct.analysers.utilities import EvidenceExtractor, RulesetManager

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
        metadata: BaseModel,
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

        rules = self.ruleset_manager.get_rules(self.config.ruleset)
        findings: list[PersonalDataFindingModel] = []
        content_lower = content.lower()

        # Process each rule
        for rule in rules:
            # Check each pattern in the rule
            for pattern in rule.patterns:
                if pattern.lower() in content_lower:
                    # Extract evidence for this matched pattern
                    evidence_matches = self.evidence_extractor.extract_evidence(
                        content,
                        pattern,
                        self.config.maximum_evidence_count,
                        self.config.evidence_context_size,
                    )

                    if evidence_matches:  # Only create finding if we have evidence
                        # Create personal data specific finding
                        finding_metadata = None
                        if metadata:
                            metadata_dict = metadata.model_dump()
                            finding_metadata = PersonalDataFindingMetadata(
                                **metadata_dict
                            )

                        compliance_data = [
                            FindingComplianceData(
                                regulation=comp.regulation, relevance=comp.relevance
                            )
                            for comp in rule.compliance
                        ]

                        finding = PersonalDataFindingModel(
                            type=rule.name,
                            risk_level=rule.risk_level,
                            special_category=rule.metadata.get("special_category"),
                            matched_pattern=pattern,
                            compliance=compliance_data,
                            evidence=evidence_matches,
                            metadata=finding_metadata,
                        )
                        findings.append(finding)

        return findings
