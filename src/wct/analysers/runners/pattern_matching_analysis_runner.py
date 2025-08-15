"""Pattern analysis runner."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from typing_extensions import override

from wct.analysers.runners.base import AnalysisRunner, AnalysisRunnerError
from wct.analysers.runners.types import (
    PatternMatcherContext,
    PatternMatchingRunnerConfig,
)
from wct.analysers.utilities import EvidenceExtractor
from wct.rulesets import RulesetLoader
from wct.rulesets.types import Rule

logger = logging.getLogger(__name__)

# Type variable for pattern matcher findings
ResultT = TypeVar("ResultT")


# Analysis runner identifier
_ANALYSIS_RUNNER_TYPE = "pattern_matching"

# Type alias for pattern matcher function
PatternMatcherFn = Callable[
    [str, str, dict[str, Any], PatternMatcherContext], ResultT | None
]


class PatternMatchingAnalysisRunner(
    AnalysisRunner[ResultT, PatternMatchingRunnerConfig]
):
    """Generic pattern-matching analysis runner that delegates specific matching logic to analysers.

    This runner provides the infrastructure for pattern matching (ruleset loading,
    evidence extraction, caching) and requires a typed pattern matcher function
    that defines how patterns are matched and how findings are structured.
    """

    def __init__(self, pattern_matcher: PatternMatcherFn[ResultT]) -> None:
        """Initialise the pattern matching runner.

        Args:
            pattern_matcher: Function that defines how to match patterns and create findings.

        """
        self.evidence_extractor = EvidenceExtractor()
        self._patterns_cache: dict[str, tuple[Rule, ...]] = {}  # Cache loaded rulesets
        self.pattern_matcher = pattern_matcher

    @override
    def get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return _ANALYSIS_RUNNER_TYPE

    @override
    def run_analysis(
        self,
        input_data: str,
        metadata: dict[str, Any],
        config: PatternMatchingRunnerConfig,
    ) -> list[ResultT]:
        """Run pattern matching analysis on content.

        Args:
            input_data: Text content to analyse
            metadata: Metadata about the content source
            config: Configuration for pattern matching analysis

        Returns:
            List of typed findings created by the pattern matcher function

        Raises:
            AnalysisRunnerError: If pattern matching fails

        """
        try:
            ruleset_name = config.ruleset_name

            logger.debug(f"Running pattern analysis with ruleset: {ruleset_name}")

            rules = self._get_rules(ruleset_name)
            if not rules:
                logger.warning(f"No rules found in ruleset: {ruleset_name}")
                return []

            return self._find_patterns_in_content(input_data, rules, metadata, config)

        except Exception as e:
            raise AnalysisRunnerError(
                _ANALYSIS_RUNNER_TYPE, f"Pattern matching failed: {e}", e
            ) from e

    def _find_patterns_in_content(
        self,
        content: str,
        rules: tuple[Rule, ...],
        metadata: dict[str, Any],
        config: PatternMatchingRunnerConfig,
    ) -> list[ResultT]:
        """Find all pattern matches in content using the provided rules.

        Args:
            content: Text content to analyze
            rules: List of rules to match against
            metadata: Content metadata
            config: Analysis configuration

        Returns:
            List of findings from pattern matching

        """
        findings: list[ResultT] = []
        content_lower = content.lower()

        for rule in rules:
            for pattern in rule.patterns:
                if pattern.lower() in content_lower:
                    finding = self._create_finding(
                        content, pattern, rule, metadata, config
                    )
                    if finding is not None:
                        findings.append(finding)
                        logger.debug(f"Found pattern '{pattern}' in rule '{rule.name}'")

        return findings

    def _create_finding(
        self,
        content: str,
        pattern: str,
        rule: Rule,
        metadata: dict[str, Any],
        config: PatternMatchingRunnerConfig,
    ) -> ResultT | None:
        """Create a finding using the pattern matcher function.

        Args:
            content: Original content
            pattern: Matched pattern
            rule: Rule that matched
            metadata: Content metadata
            config: Analysis configuration

        Returns:
            Typed finding or None if no finding should be created

        """
        context = self._build_pattern_context(rule, metadata, config)
        return self.pattern_matcher(content, pattern, rule.metadata, context)

    def _build_pattern_context(
        self, rule: Rule, metadata: dict[str, Any], config: PatternMatchingRunnerConfig
    ) -> PatternMatcherContext:
        """Build typed context object for pattern matcher function.

        Args:
            rule: Rule being processed
            metadata: Content metadata
            config: Analysis configuration

        Returns:
            Strongly typed context object with rule info and utilities

        """
        return PatternMatcherContext(
            rule_name=rule.name,
            rule_description=rule.description,
            risk_level=rule.risk_level,
            metadata=metadata,
            config=config,
            evidence_extractor=self.evidence_extractor,
        )

    def _get_rules(self, ruleset_name: str) -> tuple[Rule, ...]:
        """Get rules from ruleset, using cache when possible.

        Args:
            ruleset_name: Name of the ruleset to load

        Returns:
            Tuple of Rule objects loaded from the ruleset

        """
        if ruleset_name not in self._patterns_cache:
            self._patterns_cache[ruleset_name] = RulesetLoader.load_ruleset(
                ruleset_name
            )
            logger.info(f"Loaded ruleset: {ruleset_name}")

        return self._patterns_cache[ruleset_name]

    def clear_cache(self) -> None:
        """Clear the patterns cache.

        Useful for testing or when rulesets are updated.
        """
        self._patterns_cache.clear()
        logger.debug("Pattern cache cleared")
