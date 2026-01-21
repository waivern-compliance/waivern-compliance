"""Pattern matching components.

This package provides composable pattern matchers:
- WordBoundaryMatcher: Matches patterns at word boundaries
- RegexMatcher: Matches using regex patterns directly
- RulePatternDispatcher: Routes DetectionRule patterns to appropriate matchers
"""

from waivern_analysers_shared.matching.regex import RegexMatcher
from waivern_analysers_shared.matching.rule_pattern_dispatcher import (
    RulePatternDispatcher,
)
from waivern_analysers_shared.matching.word_boundary import WordBoundaryMatcher

__all__ = [
    "RegexMatcher",
    "RulePatternDispatcher",
    "WordBoundaryMatcher",
]
