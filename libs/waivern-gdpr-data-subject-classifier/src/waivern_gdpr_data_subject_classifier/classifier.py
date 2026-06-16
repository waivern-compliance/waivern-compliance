"""GDPR data subject classifier implementation."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, cast, override

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, JsonValue, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.message import Message
from waivern_llm import (
    BatchingMode,
    ItemGroup,
)
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_rulesets import (
    GDPRDataSubjectClassificationRule,
    RiskModifiers,
)
from waivern_schemas.gdpr_data_subject import (
    GDPRDataSubjectFindingMetadata,
    GDPRDataSubjectFindingModel,
)

from waivern_gdpr_data_subject_classifier.prompts import RiskModifierPromptBuilder
from waivern_gdpr_data_subject_classifier.result_builder import (
    GDPRDataSubjectResultBuilder,
)
from waivern_gdpr_data_subject_classifier.types import (
    GDPRDataSubjectClassifierConfig,
    GDPRDataSubjectPrepareState,
)
from waivern_gdpr_data_subject_classifier.validation.models import (
    CategoryRiskModifierResult,
    RiskModifierValidationResponseModel,
    RiskModifierValidationResult,
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

    Implements the ``DistributedProcessor`` protocol via
    ``prepare()``/``finalise()``. The executor drives LLM dispatch; when
    dispatch is unavailable or fails, ``finalise()`` falls back to
    per-finding regex risk modifier detection — no data loss.
    """

    def __init__(
        self,
        config: GDPRDataSubjectClassifierConfig | None = None,
    ) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.

        """
        config = config or GDPRDataSubjectClassifierConfig()
        self._config = config
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRDataSubjectClassificationRule
        )
        self._classification_map = self._build_classification_map()
        risk_modifiers = self._ruleset.get_risk_modifiers()
        self._available_modifiers = list(
            risk_modifiers.risk_increasing + risk_modifiers.risk_decreasing
        )
        self._risk_modifier_detector = RiskModifierDetector(risk_modifiers)
        self._result_builder = GDPRDataSubjectResultBuilder(config)

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from indicator category to GDPR classification."""
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

    # ── DistributedProcessor ─────────────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[GDPRDataSubjectPrepareState]:
        """Classify findings and declare LLM dispatch needs.

        1. Validate inputs and extract run_id.
        2. Aggregate findings across input messages (fan-in).
        3. Classify each finding (GDPR category, articles, lawful bases);
           risk_modifiers stay empty pending enrichment.
        4. If LLM is enabled and findings exist, build a single COUNT_BASED
           LLMRequest so the dispatcher can detect category-level modifiers.

        """
        if not inputs:
            raise ValueError(
                "GDPRDataSubjectClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        run_id = inputs[0].run_id or ""
        input_findings = self._aggregate_findings(inputs)
        classified_findings = [
            self._classify_finding(finding, include_risk_modifiers=False)
            for finding in input_findings
        ]
        # Missing run_id means no cache scope for LLM dispatch — degrade to
        # the regex path rather than failing. This preserves the classifier's
        # long-standing graceful behaviour under partial upstream metadata.
        llm_enabled = self._config.llm_validation.enable_llm_validation and bool(run_id)

        requests: list[DispatchRequest] = []
        if llm_enabled and classified_findings:
            requests.append(self._build_llm_request(classified_findings, run_id))

        return PrepareResult(
            state=GDPRDataSubjectPrepareState(
                classified_findings=classified_findings,
                run_id=run_id,
                llm_enabled=llm_enabled,
            ),
            requests=requests,
        )

    def finalise(
        self,
        state: GDPRDataSubjectPrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> tuple[Message, list[Message]]:
        """Produce output from classified findings and dispatch results.

        Paths:
        - LLM disabled / no usable dispatch result → regex-based per-finding
          modifier detection, ``validation_result=None`` so the result builder
          reports method_used="regex".
        - Valid LLM result with responses → category-level modifier aggregation
          applied to all findings per category (union semantics).
        """
        llm_result = self._extract_llm_result(results)
        if not state.llm_enabled or llm_result is None or not llm_result.responses:
            enriched = self._apply_risk_modifiers_via_regex(state.classified_findings)
            primary = self._result_builder.build_output_message(
                enriched,
                output_schema,
                self._ruleset.name,
                self._ruleset.version,
                validation_result=None,
            )
            return primary, []

        validation_result = self._aggregate_llm_responses(
            state.classified_findings, llm_result
        )
        enriched = self._apply_category_modifiers(
            state.classified_findings, validation_result
        )
        primary = self._result_builder.build_output_message(
            enriched,
            output_schema,
            self._ruleset.name,
            self._ruleset.version,
            validation_result=validation_result,
        )
        return primary, []

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[GDPRDataSubjectPrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. ``prompt_builder`` and ``response_model`` remain ``None``
        on resume — they are not needed since ``built_cache_keys`` drives
        cache lookup.

        """
        state = GDPRDataSubjectPrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[GDPRDataSubjectFindingModel].model_validate(r)
            for r in raw.get("requests", [])
        ]
        return PrepareResult(state=state, requests=requests)

    # ── Private helpers ──────────────────────────────────────────────────

    def _aggregate_findings(self, inputs: list[Message]) -> list[dict[str, Any]]:
        """Concatenate ``findings`` lists across input messages (fan-in)."""
        aggregated: list[dict[str, Any]] = []
        for input_message in inputs:
            raw_findings = cast(
                list[dict[str, Any]], input_message.content.get("findings", [])
            )
            aggregated.extend(raw_findings)
        return aggregated

    def _build_llm_request(
        self,
        classified_findings: list[GDPRDataSubjectFindingModel],
        run_id: str,
    ) -> LLMRequest[GDPRDataSubjectFindingModel]:
        """Build the COUNT_BASED LLMRequest for risk modifier enrichment."""
        return LLMRequest(
            name="risk_modifier_enrichment",
            groups=[ItemGroup(items=classified_findings, content=None)],
            prompt_builder=RiskModifierPromptBuilder(self._available_modifiers),
            response_model=RiskModifierValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )

    def _extract_llm_result(
        self, results: Sequence[DispatchResult]
    ) -> LLMDispatchResult | None:
        """Extract the first LLMDispatchResult from dispatch results."""
        for result in results:
            match result:
                case LLMDispatchResult() as llm_result:
                    return llm_result
                case _:
                    continue
        return None

    def _aggregate_llm_responses(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        llm_result: LLMDispatchResult,
    ) -> RiskModifierValidationResult:
        """Aggregate LLM responses into category-level results.

        Groups findings by data_subject_category and aggregates:
        - Modifiers: union of all modifiers per category
        - Confidence: average of per-finding confidences
        - Count: number of findings per category
        """
        findings_by_id = {f.id: f for f in findings}

        category_modifiers: dict[str, set[str]] = defaultdict(set)
        category_confidences: dict[str, list[float]] = defaultdict(list)
        category_counts: dict[str, int] = defaultdict(int)

        for raw_response in llm_result.responses:
            response = RiskModifierValidationResponseModel.model_validate(raw_response)
            for result in response.results:
                finding = findings_by_id.get(result.finding_id)
                if finding is None:
                    logger.warning(f"Unknown finding_id from LLM: {result.finding_id}")
                    continue

                category = finding.data_subject_category
                category_modifiers[category].update(result.risk_modifiers)
                category_confidences[category].append(result.confidence)
                category_counts[category] += 1

        category_results = [
            CategoryRiskModifierResult(
                category=cat,
                detected_modifiers=sorted(category_modifiers[cat]),
                sample_count=category_counts[cat],
                confidence=(
                    sum(category_confidences[cat]) / len(category_confidences[cat])
                    if category_confidences[cat]
                    else 0.0
                ),
            )
            for cat in category_modifiers
        ]

        return RiskModifierValidationResult(
            category_results=category_results,
            total_findings=len(findings),
            total_sampled=sum(category_counts.values()),
            validation_succeeded=len(llm_result.skipped) == 0,
        )

    def _apply_category_modifiers(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        validation_result: RiskModifierValidationResult,
    ) -> list[GDPRDataSubjectFindingModel]:
        """Apply category-level modifiers to ALL findings in each category."""
        category_modifiers: dict[str, list[str]] = {
            cat_result.category: cat_result.detected_modifiers
            for cat_result in validation_result.category_results
        }
        return [
            self._finding_with_modifiers(
                finding,
                category_modifiers.get(finding.data_subject_category, []),
            )
            for finding in findings
        ]

    def _apply_risk_modifiers_via_regex(
        self,
        findings: list[GDPRDataSubjectFindingModel],
    ) -> list[GDPRDataSubjectFindingModel]:
        """Apply risk modifiers using regex pattern matching per-finding."""
        result: list[GDPRDataSubjectFindingModel] = []
        for finding in findings:
            evidence_texts = [
                ev.content if hasattr(ev, "content") else str(ev)
                for ev in finding.evidence
                if ev
            ]
            modifiers = self._risk_modifier_detector.detect(evidence_texts)
            result.append(self._finding_with_modifiers(finding, modifiers))
        return result

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

        """
        subject_category = finding.get("subject_category", "")
        classification = self._classification_map.get(subject_category, {})

        if not classification:
            logger.warning(
                "Indicator category '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_data_subject_classification.yaml",
                subject_category,
            )

        if include_risk_modifiers:
            evidence_texts = self._extract_evidence_texts(finding)
            risk_modifiers = self._risk_modifier_detector.detect(evidence_texts)
        else:
            risk_modifiers = []

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
        """
        evidence_list: list[JsonValue] = finding.get("evidence", [])
        evidence_texts: list[str] = []

        for ev in evidence_list:
            match ev:
                case dict():
                    content = ev.get("content", "")
                    if isinstance(content, str) and content:
                        evidence_texts.append(content)
                case str():
                    evidence_texts.append(ev)
                case _:
                    pass

        return evidence_texts

    def _finding_with_modifiers(
        self,
        finding: GDPRDataSubjectFindingModel,
        modifiers: list[str],
    ) -> GDPRDataSubjectFindingModel:
        """Create a new finding with the specified risk modifiers."""
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
