"""GDPR personal data classifier implementation."""

import logging
from typing import Any, cast, override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_rulesets import GDPRPersonalDataClassificationRule

from waivern_gdpr_personal_data_classifier.result_builder import (
    GDPRClassifierResultBuilder,
)
from waivern_gdpr_personal_data_classifier.schemas import (
    GDPRPersonalDataFindingMetadata,
    GDPRPersonalDataFindingModel,
)
from waivern_gdpr_personal_data_classifier.types import (
    GDPRPersonalDataClassifierConfig,
)

logger = logging.getLogger(__name__)


class GDPRPersonalDataClassifier(Classifier):
    """Classifier that enriches personal data findings with GDPR classification.

    Takes personal data indicator findings and adds GDPR-specific information:
    - Privacy category (for reporting/governance)
    - Article 9 special category determination (core GDPR concern)
    - Relevant GDPR article references
    - Applicable lawful bases
    """

    def __init__(self, config: GDPRPersonalDataClassifierConfig | None = None) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.

        """
        config = config or GDPRPersonalDataClassifierConfig()
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRPersonalDataClassificationRule
        )
        self._classification_map = self._build_classification_map()
        self._result_builder = GDPRClassifierResultBuilder()

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from indicator category to GDPR classification.

        Returns:
            Dictionary mapping indicator categories to their GDPR classification data.

        """
        classification_map: dict[str, dict[str, Any]] = {}
        for rule in self._ruleset.get_rules():
            for indicator_category in rule.indicator_categories:
                classification_map[indicator_category] = {
                    "privacy_category": rule.privacy_category,
                    "special_category": rule.special_category,
                    "article_references": rule.article_references,
                    "lawful_bases": rule.lawful_bases,
                }
        return classification_map

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

        # Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Classify each finding
        classified_findings: list[GDPRPersonalDataFindingModel] = []
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
