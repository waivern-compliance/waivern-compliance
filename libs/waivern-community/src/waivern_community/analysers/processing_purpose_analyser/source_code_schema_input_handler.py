"""Source code schema input handler for processing purpose detection in source code analysis results."""

from pydantic import BaseModel
from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence

from waivern_community.connectors.source_code.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)
from waivern_community.rulesets import RulesetLoader
from waivern_community.rulesets.data_collection import DataCollectionRule
from waivern_community.rulesets.processing_purposes import ProcessingPurposeRule
from waivern_community.rulesets.service_integrations import ServiceIntegrationRule

from .types import ProcessingPurposeFindingMetadata, ProcessingPurposeFindingModel


class SourceCodeFileMetadata(BaseModel):
    """Metadata for a source code file being analyzed."""

    source: str
    file_path: str


class SourceCodeSchemaInputHandler:
    """Handler for processing purpose detection in source code analysis results.

    This handler processes structured source code analysis data to identify
    processing purposes based on code patterns, imports, function names, and other elements.
    """

    def __init__(self) -> None:
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load all three rulesets for comprehensive source code analysis with proper typing
        self._processing_purposes_rules = RulesetLoader.load_ruleset(
            "processing_purposes", ProcessingPurposeRule
        )
        self._service_integrations_rules = RulesetLoader.load_ruleset(
            "service_integrations", ServiceIntegrationRule
        )
        self._data_collection_rules = RulesetLoader.load_ruleset(
            "data_collection", DataCollectionRule
        )

    def analyse_source_code_data(
        self, data: SourceCodeDataModel
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse source code analysis data for processing purpose patterns.

        Args:
            data: Structured source code analysis data

        Returns:
            List of processing purpose findings detected in the source code

        """
        findings: list[ProcessingPurposeFindingModel] = []

        for file_data in data.data:
            file_metadata = SourceCodeFileMetadata(
                source="source_code", file_path=file_data.file_path
            )

            # Analyse each file with all rulesets
            findings.extend(self._analyse_file_data(file_data, file_metadata))

        return findings

    def _analyse_file_data(
        self,
        file_data: SourceCodeFileDataModel,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse a single source code file for processing purpose patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse processing purpose rules against file content
        for rule in self._processing_purposes_rules:
            for i, line in enumerate(file_data.raw_content.splitlines()):
                line_lower = line.lower()
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in line_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Line {i + 1}: {line.strip()}",
                            )
                        ]
                        finding = self._create_finding_from_processing_purpose_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        # Analyse service integration rules against file content
        for rule in self._service_integrations_rules:
            for i, line in enumerate(file_data.raw_content.splitlines()):
                line_lower = line.lower()
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in line_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Line {i + 1}: {line.strip()}",
                            )
                        ]
                        finding = self._create_finding_from_service_integration_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        # Analyse data collection rules against file content
        for rule in self._data_collection_rules:
            for i, line in enumerate(file_data.raw_content.splitlines()):
                line_lower = line.lower()
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in line_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Line {i + 1}: {line.strip()}",
                            )
                        ]
                        finding = self._create_finding_from_data_collection_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        # Analyse structured code elements for service integrations
        findings.extend(self._analyse_structured_elements(file_data, file_metadata))

        return findings

    def _analyse_structured_elements(
        self, file_data: SourceCodeFileDataModel, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse structured code elements for service integration patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse imports for service integrations
        for import_item in file_data.imports:
            text_lower = import_item.module.lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Import: {import_item.module}",
                            )
                        ]
                        finding = self._create_finding_from_service_integration_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        # Analyse function names
        for function in file_data.functions:
            text_lower = function.name.lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Function: {function.name}",
                            )
                        ]
                        finding = self._create_finding_from_service_integration_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        # Analyse class names
        for class_item in file_data.classes:
            text_lower = class_item.name.lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Class: {class_item.name}",
                            )
                        ]
                        finding = self._create_finding_from_service_integration_rule(
                            rule=rule,
                            matched_patterns=[pattern],
                            evidence=evidence,
                            file_metadata=file_metadata,
                        )
                        findings.append(finding)

        return findings

    def _create_finding_from_processing_purpose_rule(
        self,
        rule: ProcessingPurposeRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_metadata: SourceCodeFileMetadata,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from ProcessingPurposeRule - fully type-safe."""
        compliance_data = [
            BaseFindingCompliance(regulation=comp.regulation, relevance=comp.relevance)
            for comp in rule.compliance
        ]

        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,  # Type-safe!
            risk_level=rule.risk_level,
            compliance=compliance_data,
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
            ),
        )

    def _create_finding_from_service_integration_rule(
        self,
        rule: ServiceIntegrationRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_metadata: SourceCodeFileMetadata,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from ServiceIntegrationRule - fully type-safe."""
        compliance_data = [
            BaseFindingCompliance(regulation=comp.regulation, relevance=comp.relevance)
            for comp in rule.compliance
        ]

        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,  # Type-safe!
            risk_level=rule.risk_level,
            compliance=compliance_data,
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
            ),
            service_category=rule.service_category,
        )

    def _create_finding_from_data_collection_rule(
        self,
        rule: DataCollectionRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_metadata: SourceCodeFileMetadata,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from DataCollectionRule - fully type-safe."""
        compliance_data = [
            BaseFindingCompliance(regulation=comp.regulation, relevance=comp.relevance)
            for comp in rule.compliance
        ]

        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category="operational",  # DataCollectionRule doesn't have purpose_category
            risk_level=rule.risk_level,
            compliance=compliance_data,
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
            ),
            collection_type=rule.collection_type,
            data_source=rule.data_source,
        )
