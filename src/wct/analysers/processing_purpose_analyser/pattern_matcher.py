"""Pattern matcher class for processing purpose analysis."""

from pydantic import BaseModel

from wct.analysers.runners.types import PatternMatchingConfig
from wct.analysers.utilities import EvidenceExtractor
from wct.rulesets.types import Rule

from .types import ProcessingPurposeFindingMetadata, ProcessingPurposeFindingModel


class ProcessingPurposePatternMatcher:
    """Pattern matcher for processing purpose analysis.

    This class provides pattern matching functionality specifically for processing purpose
    detection, creating structured findings for the ProcessingPurposeAnalyser.
    """

    # Private constants
    _DEFAULT_PURPOSE_CATEGORY = "OPERATIONAL"
    _DEFAULT_COMPLIANCE_RELEVANCE = ["GDPR"]

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
    ) -> list[ProcessingPurposeFindingModel]:
        """Perform pattern matching for processing purpose analysis.

        Args:
            rule: The rule containing patterns to match against
            content: The content being analyzed
            content_metadata: Metadata about the content being analyzed

        Returns:
            List of processing purpose findings

        """
        # Check if content is empty
        if not content.strip():
            return []

        findings: list[ProcessingPurposeFindingModel] = []
        content_lower = content.lower()

        # Perform pattern matching for all patterns in the rule
        for pattern in rule.patterns:
            if pattern.lower() in content_lower:
                # Extract evidence for this matched pattern
                evidence = self.evidence_extractor.extract_evidence(
                    content,
                    pattern,
                    self.config.maximum_evidence_count,
                    self.config.evidence_context_size,
                )

                if evidence:  # Only create finding if we have evidence
                    # Create processing purpose specific finding
                    finding_metadata = None
                    if content_metadata:
                        metadata_dict = content_metadata.model_dump()
                        finding_metadata = ProcessingPurposeFindingMetadata(
                            **metadata_dict
                        )

                    finding = ProcessingPurposeFindingModel(
                        purpose=rule.name,
                        purpose_category=rule.metadata.get(
                            "purpose_category",
                            ProcessingPurposePatternMatcher._DEFAULT_PURPOSE_CATEGORY,
                        ),
                        risk_level=rule.risk_level,
                        compliance_relevance=rule.metadata.get(
                            "compliance_relevance",
                            ProcessingPurposePatternMatcher._DEFAULT_COMPLIANCE_RELEVANCE,
                        ),
                        matched_pattern=pattern,
                        evidence=evidence,
                        metadata=finding_metadata,
                    )
                    findings.append(finding)

        return findings
