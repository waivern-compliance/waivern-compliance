"""Handler for processing purpose detection in source code.

Uses dict-based schema handling with TypedDict for type safety.
No dependency on source code analyser package - relies on Message validation.

TODO: Architecture improvements to consider:

1. TypedDict Modelling: The TypedDict definitions (SourceCodeFunctionDict,
   SourceCodeClassDict, etc.) have fields "omitted for brevity". Consider
   completing these definitions to match the full source_code JSON schema,
   or importing from a shared location if source-code-analyser exposes them.

2. Pattern Matching Consolidation: This handler duplicates pattern matching
   logic from ProcessingPurposePatternMatcher. Both do:
   - Case-insensitive pattern matching against rulesets
   - Creating ProcessingPurposeFindingModel with compliance/evidence

   Consider extracting a shared base class or utility that both can use,
   with the key difference being evidence extraction strategy:
   - pattern_matcher: uses EvidenceExtractor for context windows
   - source_code_handler: uses line-by-line evidence with line numbers

   The structured element analysis (imports, functions, classes) is unique
   to source code and should remain here.
"""

from typing import NotRequired, TypedDict

from pydantic import BaseModel
from waivern_core.schemas import BaseFindingCompliance, BaseFindingEvidence
from waivern_rulesets import RulesetLoader
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_rulesets.processing_purposes import ProcessingPurposeRule
from waivern_rulesets.service_integrations import ServiceIntegrationRule

from .schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)

# TypedDict definitions for source_code schema v1.0.0
# These mirror the JSON schema structure without importing from SourceCodeAnalyser


class SourceCodeImportDict(TypedDict):
    """Import statement in source code."""

    module: str
    alias: NotRequired[str | None]
    line: int
    type: str  # "require", "require_once", "include", "include_once", "use", "import"


class SourceCodeFunctionDict(TypedDict):
    """Function definition in source code."""

    name: str
    line_start: int
    line_end: int
    # Additional fields from schema (parameters, return_type, etc.) omitted for brevity


class SourceCodeClassDict(TypedDict):
    """Class definition in source code."""

    name: str
    line_start: int
    line_end: int
    # Additional fields from schema (extends, implements, properties, methods) omitted for brevity


class SourceCodeFileMetadataDict(TypedDict):
    """Metadata for a source code file."""

    file_size: int
    line_count: int
    last_modified: str


class SourceCodeFileDict(TypedDict):
    """Individual source code file data."""

    file_path: str
    language: str
    raw_content: str
    imports: NotRequired[list[SourceCodeImportDict]]
    functions: NotRequired[list[SourceCodeFunctionDict]]
    classes: NotRequired[list[SourceCodeClassDict]]
    metadata: SourceCodeFileMetadataDict


class SourceCodeAnalysisMetadataDict(TypedDict):
    """Metadata for source code analysis."""

    total_files: int
    total_lines: int
    analysis_timestamp: str


class SourceCodeSchemaDict(TypedDict):
    """Top-level source_code schema structure (v1.0.0)."""

    schemaVersion: str
    name: str
    description: str
    language: str
    source: str
    metadata: SourceCodeAnalysisMetadataDict
    data: list[SourceCodeFileDict]


class SourceCodeFileMetadata(BaseModel):
    """Metadata for a source code file being analyzed."""

    source: str
    file_path: str


class SourceCodeSchemaInputHandler:
    """Handler for processing purpose detection in source code.

    Processes dict-based source_code schema data using TypedDict for type safety.
    Trusts Message validation - no Pydantic models needed.
    Uses .get() for optional fields (imports, functions, classes).
    """

    def __init__(self) -> None:
        """Initialise the handler and load required rulesets.

        The handler manages its own ruleset dependencies and is fully self-contained.
        """
        # Load all three rulesets for comprehensive source code analysis with proper typing
        self._processing_purposes_rules = RulesetLoader.load_ruleset(
            "local/processing_purposes/1.0.0", ProcessingPurposeRule
        )
        self._service_integrations_rules = RulesetLoader.load_ruleset(
            "local/service_integrations/1.0.0", ServiceIntegrationRule
        )
        self._data_collection_rules = RulesetLoader.load_ruleset(
            "local/data_collection/1.0.0", DataCollectionRule
        )

    def analyse_source_code_data(
        self, data: SourceCodeSchemaDict
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse source code analysis data for processing purpose patterns.

        Args:
            data: Dict conforming to source_code schema v1.0.0.
                  Type-checked via TypedDict for compile-time safety.
                  Data has already been validated by Message against JSON schema.

        Returns:
            List of processing purpose findings detected in the source code

        """
        findings: list[ProcessingPurposeFindingModel] = []

        for file_data in data["data"]:
            file_metadata = SourceCodeFileMetadata(
                source="source_code", file_path=file_data["file_path"]
            )

            # Analyse each file with all rulesets
            findings.extend(self._analyse_file_data(file_data, file_metadata))

        return findings

    def _analyse_file_data(
        self,
        file_data: SourceCodeFileDict,
        file_metadata: SourceCodeFileMetadata,
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse a single source code file for processing purpose patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse processing purpose rules against file content
        for rule in self._processing_purposes_rules:
            for i, line in enumerate(file_data["raw_content"].splitlines()):
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
            for i, line in enumerate(file_data["raw_content"].splitlines()):
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
            for i, line in enumerate(file_data["raw_content"].splitlines()):
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
        self, file_data: SourceCodeFileDict, file_metadata: SourceCodeFileMetadata
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse structured code elements for service integration patterns."""
        findings: list[ProcessingPurposeFindingModel] = []

        # Analyse imports for service integrations
        for import_item in file_data.get("imports", []):
            text_lower = import_item["module"].lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Import: {import_item['module']}",
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
        for function in file_data.get("functions", []):
            text_lower = function["name"].lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Function: {function['name']}",
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
        for class_item in file_data.get("classes", []):
            text_lower = class_item["name"].lower()
            for rule in self._service_integrations_rules:
                for pattern in rule.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in text_lower:
                        evidence = [
                            BaseFindingEvidence(
                                content=f"Class: {class_item['name']}",
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
            # TODO: DataCollectionRule doesn't have purpose_category - consider adding
            # purpose_category to DataCollectionRule in waivern-rulesets, or derive it
            # from collection_type/data_source to avoid hardcoding "operational"
            purpose_category="operational",
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
