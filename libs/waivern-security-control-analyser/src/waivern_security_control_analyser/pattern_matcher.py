"""Pattern matcher for security control analysis."""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor
from waivern_rulesets.security_control_indicator import SecurityControlIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.security_evidence import (
    SecurityEvidenceMetadata,
    SecurityEvidenceModel,
)


class SecurityControlPatternMatcher:
    """Pattern matcher for security control analysis.

    Accepts rules via constructor to decouple from ruleset loading.
    The analyser loads rules and passes them in at construction time.

    Builds SecurityEvidenceModel items directly from the rule's
    security_domain and polarity — no intermediate indicator model
    or derivation map is needed.
    """

    def __init__(
        self,
        rules: tuple[SecurityControlIndicatorRule, ...],
        config: PatternMatchingConfig,
    ) -> None:
        """Initialise the pattern matcher with rules and configuration.

        Args:
            rules: Security control indicator detection rules.
            config: Pattern matching configuration for evidence extraction.

        """
        self._rules = rules
        self._config = config
        self._evidence_extractor = EvidenceExtractor()
        self._dispatcher = RulePatternDispatcher()

    def find_patterns(
        self,
        content: str,
        metadata: BaseMetadata,
    ) -> list[SecurityEvidenceModel]:
        """Find all security control patterns in content.

        Args:
            content: Text content to analyse
            metadata: Content metadata

        Returns:
            List of security evidence items with polarity and domain set

        """
        if not content.strip():
            return []

        findings: list[SecurityEvidenceModel] = []

        for rule in self._rules:
            results = self._dispatcher.find_matches(
                content,
                rule,
                proximity_threshold=self._config.evidence_proximity_threshold,
                max_representatives=self._config.maximum_evidence_count,
            )

            if results:
                evidence_items = self._evidence_extractor.extract_from_results(
                    content,
                    results,
                    self._config.evidence_context_size,
                    self._config.maximum_evidence_count,
                )

                total_matches = sum(r.match_count for r in results)

                # rule.polarity is Literal["positive", "negative"], which is a
                # proper subtype of SecurityEvidenceModel.polarity's
                # Literal["positive", "negative", "neutral"] — no cast needed.
                finding = SecurityEvidenceModel(
                    metadata=SecurityEvidenceMetadata(source=metadata.source),
                    evidence_type="CODE",
                    security_domain=rule.security_domain,
                    polarity=rule.polarity,
                    confidence=1.0,
                    description=(
                        f"{total_matches} match(es) of '{rule.name}' "
                        "security control detected"
                    ),
                    evidence=evidence_items,
                )
                findings.append(finding)

        return findings
