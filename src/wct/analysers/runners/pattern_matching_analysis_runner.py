"""Pattern analysis runner."""

import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel
from typing_extensions import override

from wct.analysers.runners.base import AnalysisRunner, AnalysisRunnerError
from wct.analysers.runners.types import PatternMatchingConfig
from wct.rulesets import RulesetLoader
from wct.rulesets.types import Rule

logger = logging.getLogger(__name__)

# Type variable for pattern matcher findings
ResultT = TypeVar("ResultT")


# Analysis runner identifier
_ANALYSIS_RUNNER_TYPE = "pattern_matching_runner"


class PatternMatcher(Protocol[ResultT]):
    """Protocol for pattern matcher classes."""

    def match_patterns(
        self,
        rule: Rule,
        content: str,
        content_metadata: BaseModel,
    ) -> list[ResultT]:
        """Match patterns in content and return findings."""
        ...


class PatternMatchingAnalysisRunner(AnalysisRunner[ResultT, PatternMatchingConfig]):
    """Generic pattern-matching analysis runner that delegates specific matching logic to analysers.

    This runner provides the infrastructure for pattern matching (ruleset loading,
    evidence extraction, caching) and requires a typed pattern matcher function
    that defines how patterns are matched and how findings are structured.
    """

    def __init__(self, pattern_matcher: PatternMatcher[ResultT]) -> None:
        """Initialise the pattern matching runner.

        Args:
            pattern_matcher: Pattern matcher object that defines how to match patterns and create findings.

        """
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
        metadata: BaseModel,
        config: PatternMatchingConfig,
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
            ruleset_name = config.ruleset

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
        metadata: BaseModel,
        config: PatternMatchingConfig,
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

        for rule in rules:
            rule_findings = self.pattern_matcher.match_patterns(
                rule,
                content,
                metadata,
            )

            if rule_findings:
                findings.extend(rule_findings)
                logger.debug(
                    f"Found {len(rule_findings)} findings for rule '{rule.name}'"
                )

        return findings

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
