"""GDPR service integration classifier implementation."""

import logging
from typing import Any, Literal, cast, override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement, Schema
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_rulesets import GDPRServiceIntegrationClassificationRule
from waivern_schemas.gdpr_service_integration import (
    GDPRServiceIntegrationFindingMetadata,
    GDPRServiceIntegrationFindingModel,
)

from waivern_gdpr_service_integration_classifier.result_builder import (
    GDPRServiceIntegrationResultBuilder,
)
from waivern_gdpr_service_integration_classifier.types import (
    GDPRServiceIntegrationClassifierConfig,
)

logger = logging.getLogger(__name__)


class GDPRServiceIntegrationClassifier(Classifier):
    """Classifier that enriches service integration indicators with GDPR classification.

    Takes service integration indicator findings and adds GDPR-specific information:
    - GDPR purpose category (may differ from the indicator's own purpose category)
    - Relevant GDPR article references
    - Typical lawful bases for processing
    - Sensitivity indicators and DPIA recommendations
    """

    def __init__(
        self, config: GDPRServiceIntegrationClassifierConfig | None = None
    ) -> None:
        """Initialise the classifier.

        Args:
            config: Configuration for the classifier. If not provided,
                   uses default configuration.

        """
        config = config or GDPRServiceIntegrationClassifierConfig()
        self._ruleset = RulesetManager.get_ruleset(
            config.ruleset, GDPRServiceIntegrationClassificationRule
        )
        self._classification_map = self._build_classification_map()
        self._result_builder = GDPRServiceIntegrationResultBuilder()

    def _build_classification_map(self) -> dict[str, dict[str, Any]]:
        """Build a lookup map from service category slug to GDPR classification.

        Returns:
            Dictionary mapping service category slugs to their GDPR classification data.

        """
        classification_map: dict[str, dict[str, Any]] = {}
        for rule in self._ruleset.get_rules():
            for service_category in rule.indicator_service_categories:
                classification_map[service_category] = {
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
        return "gdpr_service_integration_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        """Return the regulatory framework this classifier targets."""
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("service_integration_indicator", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this classifier can produce."""
        return [Schema("gdpr_service_integration", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        """Process input findings and classify according to GDPR.

        Args:
            inputs: List of input messages containing service integration indicators.
            output_schema: The schema to use for the output message.

        Returns:
            Message containing GDPR-classified service integration findings.

        Raises:
            ValueError: If inputs list is empty.

        """
        if not inputs:
            raise ValueError(
                "GDPRServiceIntegrationClassifier requires at least one input message. "
                "Received empty inputs list."
            )

        # Aggregate findings from all input messages (fan-in support)
        input_findings: list[dict[str, object]] = []
        for input_message in inputs:
            input_findings.extend(input_message.content.get("findings", []))

        # Classify each finding
        classified_findings: list[GDPRServiceIntegrationFindingModel] = []
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
    ) -> GDPRServiceIntegrationFindingModel:
        """Classify a single finding according to GDPR rules.

        Args:
            finding: Raw finding dictionary from input message.

        Returns:
            Classified finding with GDPR enrichment.

        """
        # Look up classification based on service_category from indicator schema
        service_category = finding.get("service_category", "")
        classification = self._classification_map.get(service_category, {})

        if not classification:
            logger.warning(
                "Service category '%s' has no GDPR classification mapping. "
                "Add mapping to gdpr_service_integration_classification.yaml",
                service_category,
            )

        # Propagate metadata from indicator finding (always present, fallback to "unknown")
        raw_metadata = finding.get("metadata")
        if isinstance(raw_metadata, dict):
            meta_dict = cast(dict[str, Any], raw_metadata)
            metadata = GDPRServiceIntegrationFindingMetadata(
                source=meta_dict.get("source", "unknown"),
                context=meta_dict.get("context", {}),
            )
        else:
            metadata = GDPRServiceIntegrationFindingMetadata(source="unknown")

        gdpr_purpose_category = classification.get(
            "gdpr_purpose_category", "unclassified"
        )

        # Propagate indicator's purpose_category with warning if missing
        service_integration_purpose = finding.get("purpose_category")
        if service_integration_purpose is None:
            logger.warning(
                "Finding for service category '%s' has no purpose_category field. "
                "Expected from service_integration_indicator schema.",
                service_category,
            )
            service_integration_purpose = "unknown"

        # Set require_review=True for context-dependent purposes (service integrations
        # that need human review to determine actual processing purpose).
        # Leave as None (default) otherwise - excluded from JSON output by exclude_none.
        require_review = True if gdpr_purpose_category == "context_dependent" else None

        return GDPRServiceIntegrationFindingModel(
            service_category=service_category,
            service_integration_purpose=service_integration_purpose,
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
