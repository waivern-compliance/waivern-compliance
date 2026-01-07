"""GDPR personal data classifier implementation."""

from typing import Any, override

from waivern_core import InputRequirement, Schema, update_analyses_chain
from waivern_core.base_classifier import Classifier
from waivern_core.message import Message
from waivern_core.schemas import AnalysisChainEntry, BaseAnalysisOutputMetadata
from waivern_rulesets import GDPRPersonalDataClassificationRuleset

from waivern_gdpr_personal_data_classifier.schemas import (
    GDPRPersonalDataFindingModel,
    GDPRPersonalDataFindingOutput,
    GDPRPersonalDataSummary,
)


class GDPRPersonalDataClassifier(Classifier):
    """Classifier that enriches personal data findings with GDPR classification.

    Takes personal data indicator findings and adds GDPR-specific information:
    - Privacy category (for reporting/governance)
    - Article 9 special category determination (core GDPR concern)
    - Relevant GDPR article references
    - Applicable lawful bases
    """

    def __init__(self) -> None:
        """Initialise the classifier with ruleset."""
        self._ruleset = GDPRPersonalDataClassificationRuleset()
        self._classification_map = self._build_classification_map()

    def _build_classification_map(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Build a lookup map from indicator category to classification."""
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
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=f"local/{self._ruleset.name}/{self._ruleset.version}",
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

        return GDPRPersonalDataFindingModel(
            indicator_type=finding.get("type", ""),
            privacy_category=classification.get("privacy_category", "unclassified"),
            special_category=classification.get("special_category", False),
            article_references=tuple(classification.get("article_references", ())),
            lawful_bases=tuple(classification.get("lawful_bases", ())),
            evidence=finding.get("evidence", []),
            matched_patterns=finding.get("matched_patterns", []),
        )

    def _build_summary(
        self, findings: list[GDPRPersonalDataFindingModel]
    ) -> GDPRPersonalDataSummary:
        """Build summary statistics from classified findings."""
        return GDPRPersonalDataSummary(
            total_findings=len(findings),
            special_category_count=len([f for f in findings if f.special_category]),
        )
