"""Handler for data subject detection in source code.

Uses authoritative Pydantic models from waivern-source-code-analyser.
"""

from collections.abc import Generator, Sequence

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import PatternMatcher, RulesetManager
from waivern_core.schemas import BaseFindingEvidence
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_source_code_analyser import SourceCodeDataModel
from waivern_source_code_analyser.schemas.source_code import SourceCodeFileDataModel

from .confidence_scorer import DataSubjectConfidenceScorer
from .schemas.types import DataSubjectIndicatorMetadata, DataSubjectIndicatorModel
from .types import SourceCodeContextWindow

# Context window sizes (lines before/after match)
CONTEXT_WINDOW_SIZES: dict[SourceCodeContextWindow, int | None] = {
    "small": 3,  # ±3 lines
    "medium": 15,  # ±15 lines
    "large": 50,  # ±50 lines
    "full": None,  # Entire file
}


class SourceCodeSchemaInputHandler:
    """Handler for data subject detection in source code.

    Processes source_code schema data using authoritative Pydantic models
    from waivern-source-code-analyser.
    """

    def __init__(
        self,
        config: PatternMatchingConfig,
        context_window: SourceCodeContextWindow = "small",
    ) -> None:
        """Initialise the handler with configuration.

        Args:
            config: Pattern matching configuration (contains ruleset path).
            context_window: Size of context to include around matches.
                'small' = ±3 lines, 'medium' = ±15 lines,
                'large' = ±50 lines, 'full' = entire file.

        """
        self._config = config
        self._context_window: SourceCodeContextWindow = context_window
        self._ruleset_manager = RulesetManager()
        self._confidence_scorer = DataSubjectConfidenceScorer()
        self._pattern_matcher = PatternMatcher()

    def analyse(self, data: object) -> list[DataSubjectIndicatorModel]:
        """Analyse input data for data subject patterns.

        Args:
            data: Source code data (expected to be SourceCodeDataModel from reader).

        Returns:
            List of data subject indicators.

        Raises:
            TypeError: If data is not a SourceCodeDataModel instance.

        """
        if not isinstance(data, SourceCodeDataModel):
            raise TypeError(f"Expected SourceCodeDataModel, got {type(data).__name__}")

        return self._analyse_validated_data(data)

    def _analyse_validated_data(
        self, data: SourceCodeDataModel
    ) -> list[DataSubjectIndicatorModel]:
        """Analyse validated source code data (internal, type-safe).

        Args:
            data: Validated SourceCodeDataModel instance.

        Returns:
            List of data subject indicators.

        """
        indicators: list[DataSubjectIndicatorModel] = []

        for file_data in data.data:
            indicators.extend(self._analyse_file_data(file_data))

        return indicators

    def _analyse_file_data(
        self, file_data: SourceCodeFileDataModel
    ) -> list[DataSubjectIndicatorModel]:
        """Analyse a single source code file for data subject patterns.

        Orchestrates the analysis flow:
        1. Load rules from ruleset
        2. Filter rules to source_code context
        3. Find pattern matches line-by-line
        4. Group matches by category
        5. Calculate confidence and create indicators

        Args:
            file_data: Source code file data to analyse.

        Returns:
            List of data subject indicators for this file.

        """
        # Load rules using config-driven ruleset
        rules = self._ruleset_manager.get_rules(
            self._config.ruleset, DataSubjectIndicatorRule
        )

        # Filter to rules applicable in source_code context
        source_code_rules = [r for r in rules if "source_code" in r.applicable_contexts]

        lines = file_data.raw_content.splitlines()
        file_path = file_data.file_path

        # Track matches grouped by category
        # Structure: {category: [(rule, matched_patterns, line_number), ...]}
        category_matches: dict[
            str, list[tuple[DataSubjectIndicatorRule, list[str], int]]
        ] = {}

        # Find pattern matches line-by-line
        for rule in source_code_rules:
            for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
                category = rule.subject_category
                line_number = line_idx + 1  # Convert to 1-based

                if category not in category_matches:
                    category_matches[category] = []
                category_matches[category].append((rule, [pattern], line_number))

        # Create one indicator per category (grouped)
        indicators: list[DataSubjectIndicatorModel] = []

        for category, matches in category_matches.items():
            # Collect all rules for confidence scoring
            matched_rules = [match[0] for match in matches]

            # Collect unique matched patterns (preserve order using dict)
            seen_patterns: dict[str, None] = {}
            for _, patterns, _ in matches:
                for pattern in patterns:
                    seen_patterns[pattern] = None
            all_patterns = list(seen_patterns.keys())

            # Use first match for evidence and line number
            first_line_number = matches[0][2]
            first_line_idx = first_line_number - 1

            evidence = self._create_evidence(first_line_idx, lines)
            confidence = self._confidence_scorer.calculate_confidence(matched_rules)

            indicator = DataSubjectIndicatorModel(
                subject_category=category,
                confidence_score=confidence,
                evidence=evidence,
                matched_patterns=all_patterns,
                metadata=DataSubjectIndicatorMetadata(
                    source=file_path,
                    line_number=first_line_number,
                ),
            )
            indicators.append(indicator)

        return indicators

    def _find_pattern_matches(
        self, lines: list[str], patterns: Sequence[str]
    ) -> Generator[tuple[int, str], None, None]:
        """Find all pattern matches in source code lines.

        Uses word boundary-aware matching (via PatternMatcher) to reduce
        false positives from partial matches.

        Args:
            lines: Source code lines to search.
            patterns: Patterns to match.

        Yields:
            Tuples of (line_index, matched_pattern).

        """
        for i, line in enumerate(lines):
            for pattern in patterns:
                if self._pattern_matcher.matches(line, pattern):
                    yield (i, pattern)

    def _create_evidence(
        self,
        line_index: int,
        lines: list[str],
    ) -> list[BaseFindingEvidence]:
        """Create evidence for a pattern match with context window.

        Args:
            line_index: Zero-based index of the matched line.
            lines: All lines in the file (for context extraction).

        Returns:
            List containing a single BaseFindingEvidence item with context.

        """
        window_size = CONTEXT_WINDOW_SIZES[self._context_window]

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
