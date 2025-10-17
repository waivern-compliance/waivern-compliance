"""Ruleset management utility for analysers."""

import logging
from typing import Any

from waivern_community.rulesets import RulesetLoader
from waivern_community.rulesets.types import BaseRule

logger = logging.getLogger(__name__)


class RulesetManager:
    """Utility for loading rulesets with type safety and caching."""

    _cache: dict[str, tuple[Any, ...]] = {}

    @classmethod
    def get_rules[T: BaseRule](
        cls, ruleset_name: str, rule_type: type[T]
    ) -> tuple[T, ...]:
        """Get rules from ruleset with full type safety and caching.

        Args:
            ruleset_name: Name of the ruleset to load
            rule_type: The expected rule type for validation

        Returns:
            Tuple of rule objects loaded from the ruleset

        """
        cache_key = f"{ruleset_name}:{rule_type.__name__}"

        if cache_key not in cls._cache:
            logger.debug(
                f"Loading ruleset: {ruleset_name} (type: {rule_type.__name__})"
            )
            rules = RulesetLoader.load_ruleset(ruleset_name, rule_type)
            cls._cache[cache_key] = rules
        else:
            logger.debug(
                f"Using cached ruleset: {ruleset_name} (type: {rule_type.__name__})"
            )

        return cls._cache[cache_key]  # type: ignore[return-value]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the ruleset cache."""
        cls._cache.clear()
        logger.debug("Ruleset cache cleared")
