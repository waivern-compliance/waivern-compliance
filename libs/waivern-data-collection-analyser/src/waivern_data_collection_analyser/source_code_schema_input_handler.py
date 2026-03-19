"""Handler for data collection detection in source code.

Groups matches by composite key (collection_type, data_source) within
each file to prevent accidental merging of distinct collection types that
share a single field value.
"""

from collections.abc import Generator

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

from .schemas.types import (
    DataCollectionIndicatorMetadata,
    DataCollectionIndicatorModel,
)
from .types import SourceCodeContextWindow

# Context window sizes (lines before/after match)
CONTEXT_WINDOW_SIZES: dict[SourceCodeContextWindow, int | None] = {
    "small": 3,
    "medium": 15,
    "large": 50,
    "full": None,
}


class SourceCodeSchemaInputHandler:
    """Handler for data collection detection in source code.

    Accepts rules via constructor to decouple from ruleset loading.
    The analyser is responsible for loading rules and passing them here.
    """

    def __init__(
        self,
        rules: tuple[DataCollectionRule, ...],
        context_window: SourceCodeContextWindow = "small",
    ) -> None:
        """Initialise the handler with rules and context window.

        Args:
            rules: Data collection detection rules.
            context_window: Size of context to include around matches.

        """
        self._rules = rules
        self._context_window: SourceCodeContextWindow = context_window
        self._dispatcher = RulePatternDispatcher()

    def analyse(self, data: object) -> list[DataCollectionIndicatorModel]:
        """Analyse source code data for data collection patterns.

        Args:
            data: Source code data (expected to be SourceCodeDataModel).

        Returns:
            List of data collection findings.

        Raises:
            TypeError: If data is not a SourceCodeDataModel instance.

        """
        if not isinstance(data, SourceCodeDataModel):
            raise TypeError(f"Expected SourceCodeDataModel, got {type(data).__name__}")

        findings: list[DataCollectionIndicatorModel] = []
        for file_data in data.data:
            findings.extend(self._analyse_file(file_data))
        return findings

    def _analyse_file(
        self, file_data: SourceCodeFileDataModel
    ) -> list[DataCollectionIndicatorModel]:
        """Analyse a single source code file.

        Orchestrates the analysis flow:
        1. Collect matches from all rules
        2. Group by composite key (collection_type, data_source)
        3. Build one finding per group

        Args:
            file_data: Source code file data to analyse.

        Returns:
            List of findings for this file.

        """
        lines = file_data.raw_content.splitlines()
        file_path = file_data.file_path

        # Group matches by composite key: (collection_type, data_source)
        grouped: dict[tuple[str, str], list[_MatchInfo]] = {}

        for rule in self._rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule):
                key = (rule.collection_type, rule.data_source)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(
                    _MatchInfo(pattern=pattern, line_number=line_idx + 1)
                )

        findings: list[DataCollectionIndicatorModel] = []
        for (collection_type, data_source), matches in grouped.items():
            # Count pattern occurrences (preserve order)
            pattern_counts: dict[str, int] = {}
            for match in matches:
                pattern_counts[match.pattern] = pattern_counts.get(match.pattern, 0) + 1

            matched_patterns = [
                PatternMatchDetail(pattern=p, match_count=c)
                for p, c in pattern_counts.items()
            ]

            first_match = matches[0]
            first_line_idx = first_match.line_number - 1
            evidence = self._create_evidence(first_line_idx, lines)

            finding = DataCollectionIndicatorModel(
                collection_type=collection_type,
                data_source=data_source,
                matched_patterns=matched_patterns,
                evidence=evidence,
                metadata=DataCollectionIndicatorMetadata(
                    source=file_path,
                    line_number=first_match.line_number,
                ),
            )
            findings.append(finding)

        return findings

    def _find_pattern_matches(
        self,
        lines: list[str],
        rule: DataCollectionRule,
    ) -> Generator[tuple[int, str], None, None]:
        """Find all pattern matches in source code lines.

        Args:
            lines: Source code lines to search.
            rule: Rule containing patterns to match.

        Yields:
            Tuples of (line_index, matched_pattern).

        """
        for i, line in enumerate(lines):
            matches = self._dispatcher.find_matches(line, rule)
            for match in matches:
                yield (i, match.pattern)

    def _create_evidence(
        self,
        line_index: int,
        lines: list[str],
    ) -> list[BaseFindingEvidence]:
        """Create evidence with context window around a match.

        Args:
            line_index: Zero-based index of the matched line.
            lines: All lines in the file.

        Returns:
            List containing a single evidence item with context.

        """
        window_size = CONTEXT_WINDOW_SIZES[self._context_window]

        if window_size is None:
            start_idx = 0
            end_idx = len(lines)
        else:
            start_idx = max(0, line_index - window_size)
            end_idx = min(len(lines), line_index + window_size + 1)

        context_lines: list[str] = []
        for i in range(start_idx, end_idx):
            line_num = i + 1
            context_lines.append(f"{line_num:4d}  {lines[i].rstrip()}")

        content = "\n".join(context_lines)
        return [BaseFindingEvidence(content=content)]


class _MatchInfo:
    """Lightweight container for a pattern match."""

    __slots__ = ("pattern", "line_number")

    def __init__(self, pattern: str, line_number: int) -> None:
        self.pattern = pattern
        self.line_number = line_number
