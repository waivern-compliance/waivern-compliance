"""GDPR data collection classifier implementation."""

import logging
from typing import Any, Literal, cast, override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_rulesets import GDPRDataCollectionClassificationRule
from waivern_schemas.gdpr_data_collection import (
    GDPRDataCollectionFindingMetadata,
    GDPRDataCollectionFindingModel,
)

from waivern_gdpr_data_collection_classifier.result_builder import (
    GDPRDataCollectionResultBuilder,
)
from waivern_gdpr_data_collection_classifier.types import (
    GDPRDataCollectionClassifierConfig,
)

logger = logging.getLogger(__name__)


class GDPRDataCollectionClassifier(Classifier):
    """Classifier that enriches data collection indicators with GDPR classification.

    Takes data collection indicator findings and adds GDPR-specific information:
    - GDPR purpose category (all data collection mechanisms are context-dependent)
    - Relevant GDPR article references
    - Typical lawful bases for processing
    - Sensitivity indicators and DPIA recommendations
    """

    def __init__(
        self, config: GDPRDataCollectionClassifierConfig | None = None
    ) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.

        """
        config = config or GDPRDataCollectionClassifierConfig()
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRDataCollectionClassificationRule
        )
        self._classification_map = self._build_classification_map()
        self._result_builder = GDPRDataCollectionResultBuilder()

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from collection type slug to GDPR classification.

        Returns:
            Dictionary mapping collection type slugs to their GDPR classification data.

        """
        classification_map: dict[str, dict[str, Any]] = {}
        for rule in self._ruleset.get_rules():
            for collection_type in rule.indicator_collection_types:
                classification_map[collection_type] = {
                    "gdpr_purpose_category": rule.purpose_category,
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
        return "gdpr_data_collection_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        """Return the regulatory framework this classifier targets."""
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("data_collection_indicator", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this classifier can produce."""
        return [Schema("gdpr_data_collection", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        """Process input findings and classify according to GDPR.

        Args:
            inputs: List of input messages containing data collection indicators.
            output_schema: The schema to use for the output message.

        Returns:
            Message containing GDPR-classified data collection findings.

        Raises:
            ValueError: If inputs list is empty.

        """
        if not inputs:
            raise ValueError(
                "GDPRDataCollectionClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        # Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Classify each finding
        classified_findings: list[GDPRDataCollectionFindingModel] = []
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
    ) -> GDPRDataCollectionFindingModel:
        """Classify a single finding according to GDPR rules.

        Args:
            finding: Raw finding dictionary from input message.

        Returns:
            Classified finding with GDPR enrichment.

        """
        # Look up classification based on collection_type from indicator schema
        collection_type = finding.get("collection_type")
        if collection_type is None:
            logger.warning(
                "Finding has no collection_type field. "
                "Expected from data_collection_indicator schema.",
            )
            collection_type = "unknown"
        classification = self._classification_map.get(collection_type, {})

        if not classification:
            logger.warning(
                "Collection type '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_data_collection_classification.yaml",
                collection_type,
            )

        # Propagate metadata from indicator finding (always present, fallback to "unknown")
        raw_metadata = finding.get("metadata")
        if isinstance(raw_metadata, dict):
            meta_dict = cast(dict[str, Any], raw_metadata)
            metadata = GDPRDataCollectionFindingMetadata(
                source=meta_dict.get("source", "unknown"),
                context=meta_dict.get("context", {}),
            )
        else:
            metadata = GDPRDataCollectionFindingMetadata(source="unknown")

        gdpr_purpose_category = classification.get(
            "gdpr_purpose_category", "unclassified"
        )

        # Propagate indicator's data_source with warning if missing
        data_source = finding.get("data_source")
        if data_source is None:
            logger.warning(
                "Finding for collection type '%s' has no data_source field. "
                "Expected from data_collection_indicator schema.",
                collection_type,
            )
            data_source = "unknown"

        # Set require_review=True for context-dependent purposes (data collection
        # mechanisms that need human review to determine actual processing purpose).
        # Leave as None (default) otherwise - excluded from JSON output by exclude_none.
        require_review = True if gdpr_purpose_category == "context_dependent" else None

        return GDPRDataCollectionFindingModel(
            collection_type=collection_type,
            data_source=data_source,
            gdpr_purpose_category=gdpr_purpose_category,
            article_references=tuple(classification.get("article_references", ())),
            typical_lawful_bases=tuple(classification.get("typical_lawful_bases", ())),
            sensitive_purpose=classification.get("sensitive_purpose", False),
            dpia_recommendation=cast(
                Literal["required", "recommended", "not_required"],
                classification.get("dpia_recommendation", "not_required"),
            ),
            require_review=require_review,
            evidence=finding.get("evidence", []),
            matched_patterns=finding.get("matched_patterns", []),
            metadata=metadata,
        )
