"""Handler for processing purpose detection in source code.

Uses authoritative Pydantic models from waivern-source-code-analyser.

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

from waivern_core.schemas import BaseFindingEvidence
from waivern_rulesets import RulesetLoader
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_rulesets.processing_purposes import ProcessingPurposeRule
from waivern_rulesets.service_integrations import ServiceIntegrationRule
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

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


class SourceCodeSchemaInputHandler:
    """Handler for processing purpose detection in source code.

    Processes source_code schema data using authoritative Pydantic models
    from waivern-source-code-analyser.
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

    def analyse(self, data: object) -> list[ProcessingPurposeFindingModel]:
        """Analyse input data for processing purpose patterns.

        This is the public boundary - accepts object to keep analyser schema-agnostic.
        Type safety is maintained internally via SourceCodeDataModel.

        Args:
            data: Source code data (expected to be SourceCodeDataModel from reader).

        Returns:
            List of processing purpose findings detected in the source code

        Raises:
            TypeError: If data is not a SourceCodeDataModel instance.

        """
        # Validate at boundary - handler owns source code schema knowledge
        if not isinstance(data, SourceCodeDataModel):
            raise TypeError(f"Expected SourceCodeDataModel, got {type(data).__name__}")

        return self._analyse_validated_data(data)

    def _analyse_validated_data(
        self, data: SourceCodeDataModel
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse validated source code data (internal, type-safe).

        Args:
            data: Validated SourceCodeDataModel instance.

        Returns:
            List of processing purpose findings detected in the source code

        """
        findings: list[ProcessingPurposeFindingModel] = []

        for file_data in data.data:
            findings.extend(self._analyse_file_data(file_data))

        return findings

    def _analyse_file_data(
        self,
        file_data: SourceCodeFileDataModel,
    ) -> list[ProcessingPurposeFindingModel]:
        """Analyse a single source code file for processing purpose patterns."""
        findings: list[ProcessingPurposeFindingModel] = []
        lines = file_data.raw_content.splitlines()
        file_path = file_data.file_path

        # Analyse processing purpose rules
        for rule in self._processing_purposes_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(line_idx, lines)
                line_number = line_idx + 1  # Convert to 1-based
                findings.append(
                    self._create_finding_from_processing_purpose_rule(
                        rule, [pattern], evidence, file_path, line_number
                    )
                )

        # Analyse service integration rules
        for rule in self._service_integrations_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(line_idx, lines)
                line_number = line_idx + 1  # Convert to 1-based
                findings.append(
                    self._create_finding_from_service_integration_rule(
                        rule, [pattern], evidence, file_path, line_number
                    )
                )

        # Analyse data collection rules
        for rule in self._data_collection_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                evidence = self._create_evidence(line_idx, lines)
                line_number = line_idx + 1  # Convert to 1-based
                findings.append(
                    self._create_finding_from_data_collection_rule(
                        rule, [pattern], evidence, file_path, line_number
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
        line_index: int,
        lines: list[str],
    ) -> list[BaseFindingEvidence]:
        """Create evidence for a pattern match with context window.

        Args:
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

        # Build context with line numbers
        context_lines: list[str] = []
        for i in range(start_idx, end_idx):
            line_num = i + 1  # 1-based line numbers
            context_lines.append(f"{line_num:4d}  {lines[i].rstrip()}")

        content = "\n".join(context_lines)

        return [BaseFindingEvidence(content=content)]

    def _create_finding_from_processing_purpose_rule(
        self,
        rule: ProcessingPurposeRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_path: str,
        line_number: int,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from ProcessingPurposeRule."""
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_path,
                line_number=line_number,
            ),
        )

    def _create_finding_from_service_integration_rule(
        self,
        rule: ServiceIntegrationRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_path: str,
        line_number: int,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from ServiceIntegrationRule."""
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category=rule.purpose_category,
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_path,
                line_number=line_number,
            ),
            service_category=rule.service_category,
        )

    def _create_finding_from_data_collection_rule(
        self,
        rule: DataCollectionRule,
        matched_patterns: list[str],
        evidence: list[BaseFindingEvidence],
        file_path: str,
        line_number: int,
    ) -> ProcessingPurposeFindingModel:
        """Create finding from DataCollectionRule."""
        return ProcessingPurposeFindingModel(
            purpose=rule.name,
            purpose_category="operational",
            matched_patterns=matched_patterns,
            evidence=evidence,
            metadata=ProcessingPurposeFindingMetadata(
                source=file_path,
                line_number=line_number,
            ),
            collection_type=rule.collection_type,
            data_source=rule.data_source,
        )
