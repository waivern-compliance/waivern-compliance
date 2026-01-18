"""Ruleset URI parsing and representation."""

from dataclasses import dataclass
from typing import override

from waivern_rulesets.exceptions import RulesetURIParseError


@dataclass(frozen=True)
class RulesetURI:
    """Parsed ruleset URI with provider, name, and version components.

    URI format: {provider}/{name}/{version}

    Examples:
        - local/personal_data/1.0.0
        - local/processing_purposes/2.1.0

    Providers:
        - local: Bundled rulesets from waivern-rulesets package
        - (future): Remote providers for third-party rulesets

    """

    # Number of expected URI parts: provider/name/version
    _EXPECTED_PARTS = 3

    provider: str
    name: str
    version: str

    @classmethod
    def parse(cls, uri: str) -> "RulesetURI":
        """Parse a ruleset URI string into components.

        Args:
            uri: URI in format {provider}/{name}/{version}

        Returns:
            RulesetURI with parsed components

        Raises:
            RulesetURIParseError: If URI format is invalid

        """
        parts = uri.split("/")

        if len(parts) != cls._EXPECTED_PARTS:
            raise RulesetURIParseError(
                f"Invalid ruleset URI format: '{uri}'. "
                f"Expected format: provider/name/version "
                f"(e.g., 'local/personal_data/1.0.0')"
            )

        provider, name, version = parts

        if not provider or not name or not version:
            raise RulesetURIParseError(
                f"Invalid ruleset URI format: '{uri}'. "
                f"Provider, name, and version cannot be empty."
            )

        return cls(provider=provider, name=name, version=version)

    @override
    def __str__(self) -> str:
        """Return the URI string representation."""
        return f"{self.provider}/{self.name}/{self.version}"
