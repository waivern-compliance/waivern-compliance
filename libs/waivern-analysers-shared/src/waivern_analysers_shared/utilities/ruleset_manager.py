"""Ruleset management utility for analysers."""

import logging
from typing import Any

from waivern_core import Rule
from waivern_rulesets import (
    RulesetLoader,
    RulesetURI,
    RulesetURIParseError,
    UnsupportedProviderError,
)

# Re-export for backward compatibility
__all__ = [
    "RulesetManager",
    "RulesetURI",
    "RulesetURIParseError",
    "UnsupportedProviderError",
]

logger = logging.getLogger(__name__)


class RulesetManager:
    """Caching layer for RulesetLoader with type safety.

    Provides caching on top of RulesetLoader to avoid reloading
    the same ruleset multiple times during analysis.

    Supports URI format: {provider}/{name}/{version}

    Currently supported providers:
        - local: Loads from bundled waivern-rulesets package

    """

    _cache: dict[str, tuple[Any, ...]] = {}

    @classmethod
    def get_rules[T: Rule](cls, ruleset_uri: str, rule_type: type[T]) -> tuple[T, ...]:
        """Get rules from ruleset using URI with type safety and caching.

        Args:
            ruleset_uri: URI in format provider/name/version
                         (e.g., 'local/personal_data/1.0.0')
            rule_type: The expected rule type for validation

        Returns:
            Tuple of rule objects loaded from the ruleset

        Raises:
            RulesetURIParseError: If URI format is invalid
            UnsupportedProviderError: If provider is not supported

        """
        # Use full URI as cache key to distinguish versions
        cache_key = f"{ruleset_uri}:{rule_type.__name__}"

        if cache_key not in cls._cache:
            logger.debug(f"Loading ruleset: {ruleset_uri} (type: {rule_type.__name__})")
            rules = RulesetLoader.load_ruleset(ruleset_uri, rule_type)
            cls._cache[cache_key] = rules
        else:
            logger.debug(
                f"Using cached ruleset: {ruleset_uri} (type: {rule_type.__name__})"
            )

        return cls._cache[cache_key]  # type: ignore[return-value]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the ruleset cache."""
        cls._cache.clear()
        logger.debug("Ruleset cache cleared")
