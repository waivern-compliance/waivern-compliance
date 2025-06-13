from typing import Any

from waivern_analyser.config.base import Config


class RulesetConfig(Config):
    """Configuration for a ruleset."""

    type: str
    properties: dict[str, Any]
