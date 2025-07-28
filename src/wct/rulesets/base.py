"""Base classes and utilities for rulesets."""

import abc
from typing import Any
from wct.logging import get_ruleset_logger


class Ruleset(abc.ABC):
    """Base class for all rulesets with logging support.

    This provides a common interface for rulesets and automatic
    logger initialization following WCT logging conventions.
    """

    def __init__(self, ruleset_name: str) -> None:
        """Initialize the ruleset with a configured logger.

        Args:
            ruleset_name: The name of the ruleset for logging purposes
        """
        self.ruleset_name = ruleset_name
        self.logger = get_ruleset_logger(ruleset_name)

    @abc.abstractmethod
    def get_patterns(self) -> dict[str, Any]:
        """Get the patterns defined by this ruleset.

        Returns:
            Dictionary containing the ruleset patterns
        """


class RulesetError(Exception):
    """Base exception for ruleset-related errors."""

    pass


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

    pass


class RulesetLoader(abc.ABC):
    """Abstract base class for loading rulesets from different sources."""

    @abc.abstractmethod
    def load_ruleset(self, ruleset_name: str) -> dict[str, Any]:
        """Load a ruleset by name.

        Args:
            ruleset_name: Name of the ruleset to load

        Returns:
            Dictionary containing the ruleset data

        Raises:
            RulesetNotFoundError: If the ruleset cannot be found
        """


class ModuleRulesetLoader(RulesetLoader):
    """Loads rulesets from Python modules in the rulesets package."""

    def load_ruleset(self, ruleset_name: str) -> dict[str, Any]:
        """Load a ruleset from a Python module.

        Args:
            ruleset_name: Name of the ruleset module (e.g., "personal_data_gdpr")

        Returns:
            Dictionary containing the ruleset data
        """
        try:
            module_path = f"wct.rulesets.{ruleset_name}"
            module = __import__(module_path, fromlist=[ruleset_name])

            # First, look for a Ruleset class implementation
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Ruleset)
                    and attr is not Ruleset
                ):
                    # Found a Ruleset subclass, instantiate it
                    ruleset_instance = attr(ruleset_name)
                    return ruleset_instance.get_patterns()

            # Fallback: Look for a patterns dictionary in the module
            for attr_name in dir(module):
                if attr_name.endswith("_PATTERNS") and not attr_name.startswith("_"):
                    return getattr(module, attr_name)

            raise RulesetNotFoundError(
                f"No patterns found in ruleset module {ruleset_name}"
            )

        except ImportError as e:
            raise RulesetNotFoundError(
                f"Ruleset module {ruleset_name} not found"
            ) from e


def get_ruleset(
    ruleset_name: str, loader: RulesetLoader | None = None
) -> dict[str, Any]:
    """Get a ruleset using the specified loader.

    Args:
        ruleset_name: Name of the ruleset to load
        loader: RulesetLoader instance (defaults to ModuleRulesetLoader)

    Returns:
        Dictionary containing the ruleset data
    """
    if loader is None:
        loader = ModuleRulesetLoader()

    return loader.load_ruleset(ruleset_name)
