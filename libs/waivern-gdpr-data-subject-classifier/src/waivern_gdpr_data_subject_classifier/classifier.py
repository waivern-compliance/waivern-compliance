"""GDPR data subject classifier implementation."""

import logging
from typing import Any, cast, override

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_llm import LLMService
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
from waivern_gdpr_data_subject_classifier.validation.models import (
    RiskModifierValidationResult,
)
from waivern_gdpr_data_subject_classifier.validation.strategy import (
    RiskModifierValidationStrategy,
)

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
        llm_service: LLMService | None = None,
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
        self._result_builder = GDPRDataSubjectResultBuilder(config)

        # Create validation strategy when LLM validation is enabled
        # (Factory ensures llm_service is available when config enables validation)
        risk_modifiers = self._ruleset.get_risk_modifiers()
        self._validation_strategy = (
            RiskModifierValidationStrategy(
                available_modifiers=list(
                    risk_modifiers.risk_increasing + risk_modifiers.risk_decreasing
                ),
                llm_service=llm_service,
            )
            if config.llm_validation.enable_llm_validation and llm_service
            else None
        )

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

        Orchestrates the classification flow:
        1. Aggregate findings from all inputs
        2. Classify each finding (GDPR mapping, no risk modifiers yet)
        3. Detect risk modifiers via LLM (category-level) or regex (per-finding)
        4. Build and return output message

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

        # Extract run_id from inputs (set by executor, used for cache scoping)
        run_id = inputs[0].run_id

        # Step 1: Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Step 2: Classify each finding (without risk modifiers)
        classified_findings = [
            self._classify_finding(finding, include_risk_modifiers=False)
            for finding in input_findings
        ]

        # Step 3: Detect risk modifiers
        classified_findings, validation_result = self._apply_risk_modifiers(
            classified_findings, run_id=run_id
        )

        # Step 4: Build and return output message
        return self._result_builder.build_output_message(
            classified_findings,
            output_schema,
            self._ruleset.name,
            self._ruleset.version,
            validation_result,
        )

    def _classify_finding(
        self,
        finding: dict[str, Any],
        include_risk_modifiers: bool = True,
    ) -> GDPRDataSubjectFindingModel:
        """Classify a single finding according to GDPR rules.

        Args:
            finding: Raw finding dictionary from input message.
            include_risk_modifiers: If True, detect risk modifiers via regex.
                If False, return empty risk_modifiers (for LLM path where
                modifiers are applied at category level later).

        Returns:
            Classified finding with GDPR enrichment.

        """
        # Classification: Map category to GDPR articles and lawful bases
        subject_category = finding.get("subject_category", "")
        classification = self._classification_map.get(subject_category, {})

        if not classification:
            logger.warning(
                "Indicator category '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_data_subject_classification.yaml",
                subject_category,
            )

        # Risk detection (regex) - only when include_risk_modifiers=True
        if include_risk_modifiers:
            evidence_texts = self._extract_evidence_texts(finding)
            risk_modifiers = self._detect_risk_modifiers(evidence_texts)
        else:
            risk_modifiers = []

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

    def _extract_evidence_texts(self, finding: dict[str, Any]) -> list[str]:
        """Extract text content from finding evidence.

        Handles two evidence formats:
        - Dict with 'content' field (BaseFindingEvidence format)
        - Direct string evidence

        Args:
            finding: Raw finding dictionary containing evidence.

        Returns:
            List of evidence text strings.

        """
        evidence_list: list[Any] = finding.get("evidence", [])
        evidence_texts: list[str] = []

        for ev in evidence_list:
            if isinstance(ev, dict):
                ev_dict = cast(dict[str, Any], ev)
                content = ev_dict.get("content", "")
                if isinstance(content, str) and content:
                    evidence_texts.append(content)
            elif isinstance(ev, str):
                evidence_texts.append(ev)

        return evidence_texts

    def _detect_risk_modifiers(self, evidence_texts: list[str]) -> list[str]:
        """Detect risk modifiers from evidence texts using regex.

        Args:
            evidence_texts: List of evidence text strings to analyse.

        Returns:
            Sorted list of detected risk modifier names.

        """
        return self._risk_modifier_detector.detect(evidence_texts)

    def _apply_risk_modifiers(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        run_id: str | None = None,
    ) -> tuple[list[GDPRDataSubjectFindingModel], RiskModifierValidationResult | None]:
        """Apply risk modifiers to findings via LLM or regex fallback.

        Two paths:
        - LLM path: Detect modifiers at category level, apply to ALL findings in category
        - Regex path: Detect modifiers per-finding using pattern matching

        Args:
            findings: Classified findings without risk modifiers.
            run_id: Unique identifier for the current run, used for cache scoping.
                    If None, falls back to regex path.

        Returns:
            Tuple of (findings with risk modifiers applied, validation result or None).

        """
        if self._validation_strategy and self._llm_service and run_id is not None:
            return self._apply_risk_modifiers_via_llm(findings, run_id=run_id)
        return self._apply_risk_modifiers_via_regex(findings), None

    def _apply_risk_modifiers_via_llm(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        run_id: str,
    ) -> tuple[list[GDPRDataSubjectFindingModel], RiskModifierValidationResult | None]:
        """Apply risk modifiers using LLM validation at category level.

        Args:
            findings: Classified findings without risk modifiers.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            Tuple of (findings with category-level risk modifiers, validation result).

        """
        # Type narrowing handled by caller check, but be explicit for type checker
        if self._validation_strategy is None:
            return self._apply_risk_modifiers_via_regex(findings), None

        # Call LLM enrichment strategy
        result = self._validation_strategy.enrich(findings, run_id=run_id)

        # If validation failed, fall back to regex
        if not result.validation_succeeded or not result.category_results:
            logger.warning(
                "LLM validation failed or returned no results, falling back to regex"
            )
            return self._apply_risk_modifiers_via_regex(findings), None

        # Build category → modifiers mapping
        category_modifiers: dict[str, list[str]] = {
            cat_result.category: cat_result.detected_modifiers
            for cat_result in result.category_results
        }

        # Apply modifiers to ALL findings in each category
        enriched_findings = [
            self._finding_with_modifiers(
                finding,
                category_modifiers.get(finding.data_subject_category, []),
            )
            for finding in findings
        ]

        return enriched_findings, result

    def _apply_risk_modifiers_via_regex(
        self,
        findings: list[GDPRDataSubjectFindingModel],
    ) -> list[GDPRDataSubjectFindingModel]:
        """Apply risk modifiers using regex pattern matching per-finding.

        Args:
            findings: Classified findings without risk modifiers.

        Returns:
            Findings with per-finding risk modifiers applied.

        """
        result: list[GDPRDataSubjectFindingModel] = []
        for finding in findings:
            evidence_texts = [
                ev.content if hasattr(ev, "content") else str(ev)
                for ev in finding.evidence
                if ev
            ]
            modifiers = self._detect_risk_modifiers(evidence_texts)
            result.append(self._finding_with_modifiers(finding, modifiers))
        return result

    def _finding_with_modifiers(
        self,
        finding: GDPRDataSubjectFindingModel,
        modifiers: list[str],
    ) -> GDPRDataSubjectFindingModel:
        """Create a new finding with the specified risk modifiers.

        Args:
            finding: Original finding.
            modifiers: Risk modifiers to apply.

        Returns:
            New finding with updated risk_modifiers field.

        """
        return GDPRDataSubjectFindingModel(
            data_subject_category=finding.data_subject_category,
            article_references=finding.article_references,
            typical_lawful_bases=finding.typical_lawful_bases,
            risk_modifiers=modifiers,
            confidence_score=finding.confidence_score,
            evidence=finding.evidence,
            matched_patterns=finding.matched_patterns,
            metadata=finding.metadata,
        )
