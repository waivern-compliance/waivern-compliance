"""Pattern matcher class for personal data analysis."""

from pydantic import BaseModel

from wct.analysers.runners.types import PatternMatchingConfig
from wct.analysers.utilities import EvidenceExtractor
from wct.rulesets.types import Rule

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

    def match_patterns(
        self,
        rule: Rule,
        content: str,
        content_metadata: BaseModel,
    ) -> list[PersonalDataFindingModel]:
        """Perform pattern matching for personal data analysis.

        Args:
            rule: The rule containing patterns to match against
            content: The content being analyzed
            content_metadata: Metadata about the content being analyzed

        Returns:
            List of personal data findings

        """
        # Check if content is empty
        if not content.strip():
            return []

        findings: list[PersonalDataFindingModel] = []
        content_lower = content.lower()

        # Perform pattern matching for all patterns in the rule
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
                    if content_metadata:
                        metadata_dict = content_metadata.model_dump()
                        finding_metadata = PersonalDataFindingMetadata(**metadata_dict)

                    finding = PersonalDataFindingModel(
                        type=rule.name,
                        risk_level=rule.risk_level,
                        special_category=rule.metadata.get("special_category"),
                        matched_pattern=pattern,
                        evidence=evidence_matches,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings
