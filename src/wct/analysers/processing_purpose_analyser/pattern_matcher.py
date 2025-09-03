"""Pattern matcher class for processing purpose analysis."""

from wct.analysers.types import PatternMatchingConfig
from wct.analysers.utilities import EvidenceExtractor, RulesetManager
from wct.rulesets.processing_purposes import ProcessingPurposeRule
from wct.schemas import BaseMetadata
from wct.schemas.types import BaseFindingCompliance

from .types import ProcessingPurposeFindingMetadata, ProcessingPurposeFindingModel


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
        # Check if content is empty
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, ProcessingPurposeRule
        )
        findings: list[ProcessingPurposeFindingModel] = []
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
                evidence = self._evidence_extractor.extract_evidence(
                    content,
                    matched_patterns[0],
                    self._config.maximum_evidence_count,
                    self._config.evidence_context_size,
                )

                if evidence:  # Only create finding if we have evidence
                    # Create processing purpose specific finding
                    finding_metadata = None
                    if metadata:
                        finding_metadata = ProcessingPurposeFindingMetadata(
                            source=metadata.source
                        )

                    compliance_data = [
                        BaseFindingCompliance(
                            regulation=comp.regulation, relevance=comp.relevance
                        )
                        for comp in rule.compliance
                    ]

                    finding = ProcessingPurposeFindingModel(
                        purpose=rule.name,
                        purpose_category=rule.purpose_category,
                        risk_level=rule.risk_level,
                        compliance=compliance_data,
                        matched_patterns=matched_patterns,
                        evidence=evidence,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings
