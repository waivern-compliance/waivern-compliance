"""GDPR processing purpose classifier implementation."""

import logging
from typing import Any, Literal, cast, override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_rulesets import GDPRProcessingPurposeClassificationRule

from waivern_gdpr_processing_purpose_classifier.result_builder import (
    GDPRProcessingPurposeResultBuilder,
)
from waivern_gdpr_processing_purpose_classifier.schemas import (
    GDPRProcessingPurposeFindingMetadata,
    GDPRProcessingPurposeFindingModel,
)
from waivern_gdpr_processing_purpose_classifier.types import (
    GDPRProcessingPurposeClassifierConfig,
)

logger = logging.getLogger(__name__)


class GDPRProcessingPurposeClassifier(Classifier):
    """Classifier that enriches processing purpose indicators with GDPR classification.

    Takes processing purpose indicator findings and adds GDPR-specific information:
    - Purpose category (normalised for reporting/governance)
    - Relevant GDPR article references
    - Typical lawful bases for processing
    - Sensitivity indicators and DPIA recommendations
    """

    def __init__(
        self, config: GDPRProcessingPurposeClassifierConfig | None = None
    ) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.

        """
        config = config or GDPRProcessingPurposeClassifierConfig()
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRProcessingPurposeClassificationRule
        )
        self._classification_map = self._build_classification_map()
        self._result_builder = GDPRProcessingPurposeResultBuilder()

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from indicator purpose to GDPR classification.

        Returns:
            Dictionary mapping indicator purposes to their GDPR classification data.

        """
        classification_map: dict[str, dict[str, Any]] = {}
        for rule in self._ruleset.get_rules():
            for indicator_purpose in rule.indicator_purposes:
                classification_map[indicator_purpose] = {
                    "purpose_category": rule.purpose_category,
                    "article_references": rule.article_references,
                    "typical_lawful_bases": rule.typical_lawful_bases,
                    "sensitive_purpose": rule.sensitive_purpose,
                    "dpia_recommendation": rule.dpia_recommendation,
                }
        return classification_map

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the classifier."""
        return "gdpr_processing_purpose_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        """Return the regulatory framework this classifier targets."""
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("processing_purpose_indicator", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this classifier can produce."""
        return [Schema("gdpr_processing_purpose", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        """Process input findings and classify according to GDPR.

        Args:
            inputs: List of input messages containing processing purpose indicators.
            output_schema: The schema to use for the output message.

        Returns:
            Message containing GDPR-classified processing purpose findings.

        Raises:
            ValueError: If inputs list is empty.

        """
        if not inputs:
            raise ValueError(
                "GDPRProcessingPurposeClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        # Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Classify each finding
        classified_findings: list[GDPRProcessingPurposeFindingModel] = []
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

    def _classify_finding(
        self, finding: dict[str, Any]
    ) -> GDPRProcessingPurposeFindingModel:
        """Classify a single finding according to GDPR rules.

        Args:
            finding: Raw finding dictionary from input message.

        Returns:
            Classified finding with GDPR enrichment.

        """
        # Look up classification based on purpose field from indicator schema
        processing_purpose = finding.get("purpose", "")
        classification = self._classification_map.get(processing_purpose, {})

        if not classification:
            logger.warning(
                "Indicator purpose '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_processing_purpose_classification.yaml",
                processing_purpose,
            )

        # Propagate metadata from indicator finding (always present, fallback to "unknown")
        raw_metadata = finding.get("metadata")
        if isinstance(raw_metadata, dict):
            meta_dict = cast(dict[str, Any], raw_metadata)
            metadata = GDPRProcessingPurposeFindingMetadata(
                source=meta_dict.get("source", "unknown"),
                context=meta_dict.get("context", {}),
            )
        else:
            metadata = GDPRProcessingPurposeFindingMetadata(source="unknown")

        return GDPRProcessingPurposeFindingModel(
            processing_purpose=processing_purpose,
            purpose_category=classification.get("purpose_category", "unclassified"),
            article_references=tuple(classification.get("article_references", ())),
            typical_lawful_bases=tuple(classification.get("typical_lawful_bases", ())),
            sensitive_purpose=classification.get("sensitive_purpose", False),
            dpia_recommendation=cast(
                Literal["required", "recommended", "not_required"],
                classification.get("dpia_recommendation", "not_required"),
            ),
            evidence=finding.get("evidence", []),
            matched_patterns=finding.get("matched_patterns", []),
            metadata=metadata,
        )
