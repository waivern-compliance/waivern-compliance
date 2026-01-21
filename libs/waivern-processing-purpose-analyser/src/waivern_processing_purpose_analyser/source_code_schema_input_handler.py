"""Handler for processing purpose detection in source code.

Uses authoritative Pydantic models from waivern-source-code-analyser.

Groups matches by purpose (rule.name) within each file, similar to how
DataSubjectAnalyser groups by subject_category.
"""

from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Literal

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
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

RuleType = Literal["processing_purpose", "service_integration", "data_collection"]


@dataclass
class MatchInfo:
    """Information about a pattern match for grouping."""

    pattern: str
    line_number: int
    rule_type: RuleType
    # Extra fields from specific rule types
    purpose_category: str
    service_category: str | None = None
    collection_type: str | None = None
    data_source: str | None = None


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

        # NOTE: Rulesets are hardcoded here rather than config-driven (unlike
        # DataSubjectAnalyser which uses config.ruleset). This is intentional:
        #
        # Processing purpose detection requires THREE different ruleset types,
        # each with a different Pydantic model (ProcessingPurposeRule,
        # ServiceIntegrationRule, DataCollectionRule). These can't be combined
        # into a single configurable ruleset because they have different schemas.
        #
        # Trade-off: We sacrifice per-ruleset configurability for comprehensive
        # analysis - the handler always analyses all three aspects together.
        # If configurability is needed later, consider accepting a list of
        # (ruleset_path, rule_type) tuples in the config.
        self._processing_purposes_rules = RulesetManager.get_rules(
            "local/processing_purposes/1.0.0", ProcessingPurposeRule
        )
        self._service_integrations_rules = RulesetManager.get_rules(
            "local/service_integrations/1.0.0", ServiceIntegrationRule
        )
        self._data_collection_rules = RulesetManager.get_rules(
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
        """Analyse a single source code file for processing purpose patterns.

        Orchestrates the analysis flow:
        1. Collect matches from all three rule types
        2. Group matches by purpose (rule.name)
        3. Aggregate pattern counts and create one finding per purpose

        Args:
            file_data: Source code file data to analyse.

        Returns:
            List of processing purpose findings for this file.

        """
        lines = file_data.raw_content.splitlines()
        file_path = file_data.file_path

        # Group matches by purpose (rule.name)
        # Structure: {purpose: [MatchInfo, ...]}
        purpose_matches: dict[str, list[MatchInfo]] = {}

        # Collect matches from processing purpose rules
        for rule in self._processing_purposes_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                purpose = rule.name
                if purpose not in purpose_matches:
                    purpose_matches[purpose] = []
                purpose_matches[purpose].append(
                    MatchInfo(
                        pattern=pattern,
                        line_number=line_idx + 1,
                        rule_type="processing_purpose",
                        purpose_category=rule.purpose_category,
                    )
                )

        # Collect matches from service integration rules
        for rule in self._service_integrations_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                purpose = rule.name
                if purpose not in purpose_matches:
                    purpose_matches[purpose] = []
                purpose_matches[purpose].append(
                    MatchInfo(
                        pattern=pattern,
                        line_number=line_idx + 1,
                        rule_type="service_integration",
                        purpose_category=rule.purpose_category,
                        service_category=rule.service_category,
                    )
                )

        # Collect matches from data collection rules
        for rule in self._data_collection_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                purpose = rule.name
                if purpose not in purpose_matches:
                    purpose_matches[purpose] = []
                purpose_matches[purpose].append(
                    MatchInfo(
                        pattern=pattern,
                        line_number=line_idx + 1,
                        rule_type="data_collection",
                        purpose_category="operational",
                        collection_type=rule.collection_type,
                        data_source=rule.data_source,
                    )
                )

        # Create one finding per purpose (grouped)
        findings: list[ProcessingPurposeFindingModel] = []

        for purpose, matches in purpose_matches.items():
            # Count pattern occurrences (preserve order using dict)
            pattern_counts: dict[str, int] = {}
            for match in matches:
                pattern_counts[match.pattern] = pattern_counts.get(match.pattern, 0) + 1

            # Build PatternMatchDetail objects with counts
            matched_patterns = [
                PatternMatchDetail(pattern=p, match_count=c)
                for p, c in pattern_counts.items()
            ]

            # Use first match for evidence, line number, and extra fields
            first_match = matches[0]
            first_line_idx = first_match.line_number - 1
            evidence = self._create_evidence(first_line_idx, lines)

            finding = ProcessingPurposeFindingModel(
                purpose=purpose,
                purpose_category=first_match.purpose_category,
                matched_patterns=matched_patterns,
                evidence=evidence,
                metadata=ProcessingPurposeFindingMetadata(
                    source=file_path,
                    line_number=first_match.line_number,
                ),
                service_category=first_match.service_category,
                collection_type=first_match.collection_type,
                data_source=first_match.data_source,
            )
            findings.append(finding)

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
