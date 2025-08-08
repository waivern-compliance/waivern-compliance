"""Pattern matching analysis runner."""

from collections.abc import Callable
from typing import Any

from wct.analysers.runners.base import AnalysisRunner, AnalysisRunnerError
from wct.analysers.utilities import EvidenceExtractor
from wct.logging import get_analyser_logger
from wct.rulesets import RulesetLoader

# Type alias for pattern matcher function
PatternMatcherFn = Callable[
    [str, str, dict[str, Any], dict[str, Any]], dict[str, Any] | None
]


class PatternMatchingRunner(AnalysisRunner[dict[str, Any]]):
    """Generic pattern matching runner that delegates specific matching logic to analysers.

    This runner provides the infrastructure for pattern matching (ruleset loading,
    evidence extraction, caching) but allows each analyser to define how patterns
    are matched and how findings are structured.
    """

    def __init__(self, pattern_matcher: PatternMatcherFn | None = None):
        """Initialize the pattern matching runner.

        Args:
            pattern_matcher: Function that defines how to match patterns and create findings.
                           If None, a default implementation will be used.
        """
        self.evidence_extractor = EvidenceExtractor()
        self._patterns_cache = {}  # Cache loaded rulesets
        self.logger = get_analyser_logger("pattern_matching_runner")
        self.pattern_matcher = (
            pattern_matcher
            if pattern_matcher is not None
            else self._default_pattern_matcher
        )

    def get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "pattern_matching"

    def run_analysis(
        self, input_data: str, metadata: dict[str, Any], config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Run pattern matching analysis on content.

        Args:
            input_data: Text content to analyze
            metadata: Metadata about the content source
            config: Configuration including:
                - ruleset_name: Name of the ruleset to use
                - max_evidence: Maximum evidence snippets per finding (default: 3)
                - context_size: Context size for evidence extraction (default: "small")
                - other analyser-specific config

        Returns:
            List of finding dictionaries created by the pattern matcher function

        Raises:
            AnalysisRunnerError: If pattern matching fails
        """
        try:
            ruleset_name = config.get("ruleset_name", "personal_data")

            self.logger.debug(f"Running pattern analysis with ruleset: {ruleset_name}")

            # Load patterns (with caching)
            patterns = self._get_patterns(ruleset_name)
            if not patterns:
                self.logger.warning(f"No patterns found in ruleset: {ruleset_name}")
                return []

            # Run pattern matching using the provided strategy
            findings = []
            content_lower = input_data.lower()

            for category_name, category_data in patterns.items():
                category_patterns = category_data.get("patterns", [])

                for pattern in category_patterns:
                    if pattern.lower() in content_lower:
                        # Delegate to the analyser-specific pattern matcher
                        finding = self.pattern_matcher(
                            input_data,
                            pattern,
                            category_data,
                            {
                                "category_name": category_name,
                                "metadata": metadata,
                                "config": config,
                                "evidence_extractor": self.evidence_extractor,
                            },
                        )

                        if finding:
                            findings.append(finding)
                            self.logger.debug(
                                f"Found pattern '{pattern}' in category '{category_name}'"
                            )

            self.logger.info(f"Pattern matching completed: {len(findings)} findings")
            return findings

        except Exception as e:
            raise AnalysisRunnerError(
                "pattern_matching", f"Pattern matching failed: {e}", e
            )

    def _default_pattern_matcher(
        self,
        content: str,
        pattern: str,
        category_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Provide default pattern matching implementation.

        # TODO: After migration completion, refactor rulesets to have standardized structure
        # and optimize this default implementation for better consistency and performance.
        # Consider standardizing fields like risk_level, special_category across all rulesets.

        This provides a basic implementation that analysers can override.

        Args:
            content: The content being analyzed
            pattern: The matched pattern
            category_data: Data about the pattern category from ruleset
            context: Additional context including metadata, config, and utilities

        Returns:
            Finding dictionary or None if no finding should be created
        """
        evidence_extractor = context["evidence_extractor"]
        metadata = context["metadata"]
        config = context["config"]
        category_name = context["category_name"]

        max_evidence = config.get("max_evidence", 3)
        context_size = config.get("context_size", "small")

        # Extract evidence for this pattern match
        evidence = evidence_extractor.extract_evidence(
            content, pattern, max_evidence, context_size
        )

        if not evidence:
            return None

        return {
            "type": category_name,
            "risk_level": category_data.get("risk_level", "medium"),
            "matched_pattern": pattern,
            "evidence": evidence,
            "metadata": metadata.copy() if metadata else {},
        }

    def _get_patterns(self, ruleset_name: str) -> dict[str, Any]:
        """Get patterns from ruleset, using cache when possible.

        Args:
            ruleset_name: Name of the ruleset to load

        Returns:
            Dictionary of patterns loaded from the ruleset
        """
        if ruleset_name not in self._patterns_cache:
            try:
                self._patterns_cache[ruleset_name] = RulesetLoader.load_ruleset(
                    ruleset_name
                )
                self.logger.info(f"Loaded ruleset: {ruleset_name}")
            except Exception as e:
                self.logger.error(f"Failed to load ruleset {ruleset_name}: {e}")
                # Return empty dict for graceful degradation
                self._patterns_cache[ruleset_name] = {}

        return self._patterns_cache[ruleset_name]

    def clear_cache(self) -> None:
        """Clear the patterns cache.

        Useful for testing or when rulesets are updated.
        """
        self._patterns_cache.clear()
        self.logger.debug("Pattern cache cleared")
