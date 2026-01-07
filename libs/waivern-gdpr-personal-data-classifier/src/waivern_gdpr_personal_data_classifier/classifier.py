"""GDPR personal data classifier implementation."""

import logging
from functools import cache
from typing import Any, cast, override

from waivern_core import InputRequirement, Schema, update_analyses_chain
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_core.schemas import AnalysisChainEntry, BaseAnalysisOutputMetadata
from waivern_rulesets import GDPRPersonalDataClassificationRuleset

from waivern_gdpr_personal_data_classifier.schemas import (
    GDPRPersonalDataFindingMetadata,
    GDPRPersonalDataFindingModel,
    GDPRPersonalDataFindingOutput,
    GDPRPersonalDataSummary,
)

logger = logging.getLogger(__name__)


@cache
def _get_ruleset() -> GDPRPersonalDataClassificationRuleset:
    """Get the cached GDPR classification ruleset.

    The ruleset is loaded once and cached for all classifier instances.
    """
    return GDPRPersonalDataClassificationRuleset()


@cache
def _get_classification_map() -> dict[str, dict[str, Any]]:
    """Build a cached lookup map from indicator category to GDPR classification.

    This function is cached at module level to avoid rebuilding the map
    for each classifier instance. The ruleset is static (loaded from YAML),
    so caching is safe and improves performance in high-throughput pipelines.
    """
    ruleset = _get_ruleset()
    classification_map: dict[str, dict[str, Any]] = {}
    for rule in ruleset.get_rules():
        for indicator_category in rule.indicator_categories:
            classification_map[indicator_category] = {
                "privacy_category": rule.privacy_category,
                "special_category": rule.special_category,
                "article_references": rule.article_references,
                "lawful_bases": rule.lawful_bases,
            }
    return classification_map


class GDPRPersonalDataClassifier(Classifier):
    """Classifier that enriches personal data findings with GDPR classification.

    Takes personal data indicator findings and adds GDPR-specific information:
    - Privacy category (for reporting/governance)
    - Article 9 special category determination (core GDPR concern)
    - Relevant GDPR article references
    - Applicable lawful bases
    """

    def __init__(self) -> None:
        """Initialise the classifier."""
        self._classification_map = _get_classification_map()

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the classifier."""
        return "gdpr_personal_data_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        """Return the regulatory framework this classifier targets."""
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("personal_data_indicator", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this classifier can produce."""
        return [Schema("gdpr_personal_data", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        """Process input findings and classify according to GDPR."""
        if not inputs:
            raise ValueError(
                "GDPRPersonalDataClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        if len(inputs) > 1:
            logger.warning(
                "GDPRPersonalDataClassifier received %d inputs but only processes the first. "
                "Extra inputs will be ignored. Consider merging inputs upstream.",
                len(inputs),
            )

        # Extract findings from input
        input_findings = inputs[0].content.get("findings", [])

        # Classify each finding
        classified_findings: list[GDPRPersonalDataFindingModel] = []
        for finding in input_findings:
            classified = self._classify_finding(finding)
            classified_findings.append(classified)

        # Update analysis chain
        updated_chain_dicts = update_analyses_chain(inputs[0], self.get_name())
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Build summary
        summary = self._build_summary(classified_findings)

        # Build analysis metadata
        ruleset = _get_ruleset()
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=f"local/{ruleset.name}/{ruleset.version}",
            llm_validation_enabled=False,
            analyses_chain=updated_chain,
        )

        # Create output
        output = GDPRPersonalDataFindingOutput(
            findings=classified_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
        )

        result_data = output.model_dump(mode="json", exclude_none=True)

        return Message(
            id="gdpr_personal_data_classification",
            content=result_data,
            schema=output_schema,
        )

    def _classify_finding(
        self, finding: dict[str, Any]
    ) -> GDPRPersonalDataFindingModel:
        """Classify a single finding according to GDPR rules."""
        # Look up classification based on category (indicator category)
        # Note: The indicator finding uses 'category' field with granular values
        # like 'email', 'phone', 'health' which map to privacy_category groupings
        category = finding.get("category", "")
        classification = self._classification_map.get(category, {})

        if not classification:
            logger.warning(
                "Indicator category '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_personal_data_classification.yaml",
                category,
            )

        # Propagate metadata from indicator finding
        metadata = None
        raw_metadata = finding.get("metadata")
        if isinstance(raw_metadata, dict):
            meta_dict = cast(dict[str, Any], raw_metadata)
            metadata = GDPRPersonalDataFindingMetadata(
                source=meta_dict.get("source", "unknown"),
                context=meta_dict.get("context", {}),
            )

        return GDPRPersonalDataFindingModel(
            indicator_type=category,
            privacy_category=classification.get("privacy_category", "unclassified"),
            special_category=classification.get("special_category", False),
            article_references=tuple(classification.get("article_references", ())),
            lawful_bases=tuple(classification.get("lawful_bases", ())),
            evidence=finding.get("evidence", []),
            matched_patterns=finding.get("matched_patterns", []),
            metadata=metadata,
        )

    def _build_summary(
        self, findings: list[GDPRPersonalDataFindingModel]
    ) -> GDPRPersonalDataSummary:
        """Build summary statistics from classified findings."""
        return GDPRPersonalDataSummary(
            total_findings=len(findings),
            special_category_count=len([f for f in findings if f.special_category]),
        )
