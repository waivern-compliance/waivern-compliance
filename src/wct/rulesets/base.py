"""Base classes and utilities for rulesets."""

import abc
from typing import Any

from wct.logging import get_ruleset_logger


class Ruleset(abc.ABC):
    """Base class for all rulesets with logging support.

    This provides a common interface for rulesets and automatic
    logger initialisation following WCT logging conventions.
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


class RulesetLoader:
    """Loads rulesets from Python modules in the rulesets package."""

    @classmethod
    def load_ruleset(cls, ruleset_name: str) -> dict[str, Any]:
        """Load a ruleset from a Python module.

        Args:
            ruleset_name: Name of the ruleset module (e.g., "personal_data_gdpr")

        Returns:
            Dictionary containing the ruleset data
        """
        try:
            module_path = f"wct.rulesets.{ruleset_name}"
            module = __import__(module_path, fromlist=[ruleset_name])

            # Look for a Ruleset class implementation
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

            raise RulesetNotFoundError(
                f"No Ruleset class found in module {ruleset_name}"
            )

        except ImportError as e:
            raise RulesetNotFoundError(
                f"Ruleset module {ruleset_name} not found"
            ) from e
