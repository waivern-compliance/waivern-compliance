"""GDPR data subject classifier implementation."""

import logging
from typing import Any, cast, override

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_llm import BaseLLMService
from waivern_rulesets import (
    GDPRDataSubjectClassificationRule,
    RiskModifiers,
)

from waivern_gdpr_data_subject_classifier.result_builder import (
    GDPRDataSubjectResultBuilder,
)
from waivern_gdpr_data_subject_classifier.schemas import (
    GDPRDataSubjectFindingMetadata,
    GDPRDataSubjectFindingModel,
)
from waivern_gdpr_data_subject_classifier.types import GDPRDataSubjectClassifierConfig

logger = logging.getLogger(__name__)


class RiskModifierDetector:
    """Detects risk modifiers from evidence text using word boundary and regex patterns.

    Risk modifiers indicate special considerations for data subject processing,
    such as minors (Article 8) or vulnerable individuals (Recital 75) that
    require additional protections under GDPR.

    Uses RulePatternDispatcher for consistent pattern matching:
    - patterns: Word boundary matching (case-insensitive)
    - value_patterns: Regex matching for complex patterns
    """

    def __init__(self, risk_modifiers: RiskModifiers) -> None:
        """Initialise the detector with risk modifier patterns.

        Args:
            risk_modifiers: Risk modifiers containing patterns for risk-increasing
                           and risk-decreasing modifiers.

        """
        self._modifiers = (
            risk_modifiers.risk_increasing + risk_modifiers.risk_decreasing
        )
        self._dispatcher = RulePatternDispatcher()

    def detect(self, evidence_texts: list[str]) -> list[str]:
        """Detect risk modifiers from evidence texts.

        Args:
            evidence_texts: List of evidence text strings to search.

        Returns:
            Sorted list of unique detected modifier names.

        """
        detected: set[str] = set()
        for text in evidence_texts:
            for modifier in self._modifiers:
                # RulePatternDispatcher works with any object that has
                # patterns and value_patterns attributes (duck typing)
                if self._dispatcher.find_matches(text, modifier):  # type: ignore[arg-type]
                    detected.add(modifier.modifier)
        return sorted(detected)


class GDPRDataSubjectClassifier(Classifier):
    """Classifier that enriches data subject indicators with GDPR classification.

    Takes data subject indicator findings and adds GDPR-specific information:
    - Data subject category (normalised for reporting/governance)
    - Relevant GDPR article references
    - Typical lawful bases for processing
    - Risk modifiers detected from evidence context
    """

    def __init__(
        self,
        config: GDPRDataSubjectClassifierConfig | None = None,
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.
            llm_service: Optional LLM service for risk modifier validation.
                        When provided and LLM validation is enabled in config,
                        risk modifiers will be validated/enriched via LLM.

        """
        config = config or GDPRDataSubjectClassifierConfig()
        self._config = config
        self._llm_service = llm_service
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRDataSubjectClassificationRule
        )
        self._classification_map = self._build_classification_map()
        self._risk_modifier_detector = RiskModifierDetector(
            self._ruleset.get_risk_modifiers()
        )
        self._result_builder = GDPRDataSubjectResultBuilder()

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from indicator category to GDPR classification.

        Returns:
            Dictionary mapping indicator categories to their GDPR classification data.

        """
        classification_map: dict[str, dict[str, Any]] = {}
        for rule in self._ruleset.get_rules():
            for indicator_category in rule.indicator_categories:
                classification_map[indicator_category] = {
                    "data_subject_category": rule.data_subject_category,
                    "article_references": rule.article_references,
                    "typical_lawful_bases": rule.typical_lawful_bases,
                }
        return classification_map

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the classifier."""
        return "gdpr_data_subject_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        """Return the regulatory framework this classifier targets."""
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("data_subject_indicator", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this classifier can produce."""
        return [Schema("gdpr_data_subject", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        """Process input findings and classify according to GDPR.

        Args:
            inputs: List of input messages containing data subject indicators.
            output_schema: The schema to use for the output message.

        Returns:
            Message containing GDPR-classified data subject findings.

        Raises:
            ValueError: If inputs list is empty.

        """
        if not inputs:
            raise ValueError(
                "GDPRDataSubjectClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        # Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Classify each finding
        classified_findings: list[GDPRDataSubjectFindingModel] = []
        for finding in input_findings:
            classified = self._classify_finding(finding)
            classified_findings.append(classified)

        # Build and return output message
        return self._result_builder.build_output_message(
            classified_findings,
            output_schema,
            self._ruleset.name,
            self._ruleset.version,
        )

    def _classify_finding(self, finding: dict[str, Any]) -> GDPRDataSubjectFindingModel:
        """Classify a single finding according to GDPR rules.

        Args:
            finding: Raw finding dictionary from input message.

        Returns:
            Classified finding with GDPR enrichment.

        """
        # Look up classification based on subject_category
        subject_category = finding.get("subject_category", "")
        classification = self._classification_map.get(subject_category, {})

        if not classification:
            logger.warning(
                "Indicator category '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_data_subject_classification.yaml",
                subject_category,
            )

        # Extract evidence texts for risk modifier detection
        evidence_list: list[Any] = finding.get("evidence", [])
        evidence_texts: list[str] = []
        for ev in evidence_list:
            if isinstance(ev, dict):
                # Evidence object with 'content' field (BaseFindingEvidence format)
                ev_dict = cast(dict[str, Any], ev)
                content = ev_dict.get("content", "")
                if isinstance(content, str) and content:
                    evidence_texts.append(content)
            elif isinstance(ev, str):
                # Direct string evidence
                evidence_texts.append(ev)

        # Detect risk modifiers from evidence
        risk_modifiers = self._risk_modifier_detector.detect(evidence_texts)

        # Propagate metadata from indicator finding (always present, fallback to "unknown")
        raw_metadata = finding.get("metadata")
        if isinstance(raw_metadata, dict):
            meta_dict = cast(dict[str, Any], raw_metadata)
            metadata = GDPRDataSubjectFindingMetadata(
                source=meta_dict.get("source", "unknown"),
                context=meta_dict.get("context", {}),
            )
        else:
            metadata = GDPRDataSubjectFindingMetadata(source="unknown")

        return GDPRDataSubjectFindingModel(
            data_subject_category=classification.get(
                "data_subject_category", "unclassified"
            ),
            article_references=tuple(classification.get("article_references", ())),
            typical_lawful_bases=tuple(classification.get("typical_lawful_bases", ())),
            risk_modifiers=risk_modifiers,
            confidence_score=finding.get("confidence_score", 0),
            evidence=finding.get("evidence", []),
            matched_patterns=finding.get("matched_patterns", []),
            metadata=metadata,
        )
