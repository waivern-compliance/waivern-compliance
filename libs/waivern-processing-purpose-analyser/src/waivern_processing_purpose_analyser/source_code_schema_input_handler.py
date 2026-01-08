"""Handler for processing purpose detection in source code.

Uses dict-based schema handling with TypedDict for type safety.
No dependency on source code analyser package - relies on Message validation.

TODO: Architecture improvements to consider:

Pattern Matching Consolidation: This handler duplicates pattern matching
logic from ProcessingPurposePatternMatcher. Both do:
- Case-insensitive pattern matching against rulesets
- Creating ProcessingPurposeFindingModel with compliance/evidence

Consider extracting a shared base class or utility that both can use,
with the key difference being evidence extraction strategy:
- pattern_matcher: uses EvidenceExtractor for context windows
- source_code_handler: uses line-by-line evidence with line numbers
"""

from collections.abc import Generator, Sequence
from typing import NotRequired, TypedDict

from pydantic import BaseModel
from waivern_core.schemas import BaseFindingEvidence
from waivern_rulesets import RulesetLoader
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_rulesets.processing_purposes import ProcessingPurposeRule
from waivern_rulesets.service_integrations import ServiceIntegrationRule

from .schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)
from .types import SourceCodeContextWindow

# Context window sizes (lines before/after match)
CONTEXT_WINDOW_SIZES: dict[SourceCodeContextWindow, int | None] = {
    "small": 3,  # ±3 lines
    "medium": 15,  # ±15 lines
    "large": 50,  # ±50 lines
    "full": None,  # Entire file
}

# TypedDict definitions for source_code schema v1.0.0
# These mirror the JSON schema structure without importing from SourceCodeAnalyser


class SourceCodeFileMetadataDict(TypedDict):
    """Metadata for a source code file."""

    file_size: int
    line_count: int
    last_modified: NotRequired[str | None]


class SourceCodeFileDict(TypedDict):
    """Individual source code file data."""

    file_path: str
    language: str
    raw_content: str
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

    def __init__(self, context_window: SourceCodeContextWindow = "small") -> None:
        """Initialise the handler and load required rulesets.

        Args:
            context_window: Size of context to include around matches.
                'small' = ±3 lines, 'medium' = ±15 lines, 'large' = ±50 lines, 'full' = entire file.

        """
        self.context_window: SourceCodeContextWindow = context_window
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
        lines = file_data["raw_content"].splitlines()
        file_path = file_data["file_path"]

        # Analyse processing purpose rules
        for rule in self._processing_purposes_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(file_path, line_idx, lines)
                findings.append(
                    self._create_finding_from_processing_purpose_rule(
                        rule, [pattern], evidence, file_metadata
                    )
                )

        # Analyse service integration rules
        for rule in self._service_integrations_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(file_path, line_idx, lines)
                findings.append(
                    self._create_finding_from_service_integration_rule(
                        rule, [pattern], evidence, file_metadata
                    )
                )

        # Analyse data collection rules
        for rule in self._data_collection_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(file_path, line_idx, lines)
                findings.append(
                    self._create_finding_from_data_collection_rule(
                        rule, [pattern], evidence, file_metadata
                    )
                )

        return findings

    def _find_pattern_matches(
        self, lines: list[str], patterns: Sequence[str]
    ) -> Generator[tuple[int, str], None, None]:
        """Find all pattern matches in source code lines.

        Args:
            lines: Source code lines to search
            patterns: Patterns to match (case-insensitive)

        Yields:
            Tuples of (line_index, matched_pattern)

        """
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for pattern in patterns:
                if pattern.lower() in line_lower:
                    yield (i, pattern)

    def _create_evidence(
        self,
        file_path: str,
        line_index: int,
        lines: list[str],
    ) -> list[BaseFindingEvidence]:
        """Create evidence for a pattern match with context window.

        Args:
            file_path: Path to the source file
            line_index: Zero-based index of the matched line
            lines: All lines in the file (for context extraction)

        Returns:
            List containing a single BaseFindingEvidence item with context

        """
        window_size = CONTEXT_WINDOW_SIZES[self.context_window]

        if window_size is None:
            # Full file context
            start_idx = 0
            end_idx = len(lines)
        else:
            # ±N lines around the match
            start_idx = max(0, line_index - window_size)
            end_idx = min(len(lines), line_index + window_size + 1)

        # Build context with line numbers and arrow indicator for matched line
        context_lines: list[str] = []
        for i in range(start_idx, end_idx):
            line_num = i + 1  # 1-based line numbers
            indicator = "→" if i == line_index else " "
            context_lines.append(f"{line_num:4d}{indicator} {lines[i].rstrip()}")

        content = f"{file_path}\n" + "\n".join(context_lines)

        return [BaseFindingEvidence(content=content)]

    def _create_finding_from_processing_purpose_rule(
        self,
        rule: ProcessingPurposeRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_metadata: SourceCodeFileMetadata,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from ProcessingPurposeRule - fully type-safe."""
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,  # Type-safe!
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
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,  # Type-safe!
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
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            # TODO: DataCollectionRule doesn't have purpose_category - consider adding
            # purpose_category to DataCollectionRule in waivern-rulesets, or derive it
            # from collection_type/data_source to avoid hardcoding "operational"
            purpose_category="operational",
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_metadata.source,
            ),
            collection_type=rule.collection_type,
            data_source=rule.data_source,
        )
