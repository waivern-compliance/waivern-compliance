"""Pattern matcher for crypto quality analysis."""

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor
from waivern_core.schemas import PatternMatchDetail
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.crypto_quality_indicator import (
    CryptoQualityIndicatorMetadata,
    CryptoQualityIndicatorModel,
)

# Maps quality_rating to evidence polarity.
# strong → positive (the implementation uses a secure algorithm)
# weak / deprecated → negative (the implementation is insecure or outdated)
_POLARITY_MAP: dict[str, str] = {
    "strong": "positive",
    "weak": "negative",
    "deprecated": "negative",
}


class CryptoQualityPatternMatcher:
    """Pattern matcher for cryptographic algorithm quality analysis.

    Accepts rules via constructor to decouple from ruleset loading.
    The analyser loads rules and passes them in at construction time.
    """

    def __init__(
        self,
        rules: tuple[CryptoQualityIndicatorRule, ...],
        config: PatternMatchingConfig,
    ) -> None:
        """Initialise the pattern matcher with rules and configuration.

        Args:
            rules: Crypto quality indicator detection rules.
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
    ) -> list[CryptoQualityIndicatorModel]:
        """Find all cryptographic algorithm patterns in content.

        Args:
            content: Text content to analyse
            metadata: Content metadata

        Returns:
            List of crypto quality indicators with polarity set

        """
        if not content.strip():
            return []

        findings: list[CryptoQualityIndicatorModel] = []

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

                matched_patterns = [
                    PatternMatchDetail(pattern=r.pattern, match_count=r.match_count)
                    for r in results
                    if r.representative_matches
                ]

                # Polarity is derived from quality_rating at construction time.
                # strong → positive, weak/deprecated → negative.
                polarity = _POLARITY_MAP[rule.quality_rating]

                finding = CryptoQualityIndicatorModel(
                    algorithm=rule.algorithm,
                    quality_rating=rule.quality_rating,
                    polarity=polarity,  # type: ignore[arg-type]
                    matched_patterns=matched_patterns,
                    evidence=evidence_items,
                    metadata=CryptoQualityIndicatorMetadata(
                        source=metadata.source,
                        context=metadata.context,
                    ),
                )
                findings.append(finding)

        return findings
