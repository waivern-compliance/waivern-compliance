"""Data collection ruleset.

This module defines patterns for detecting data collection mechanisms
in source code, such as HTTP form data, cookies, sessions, and API endpoints.
All patterns use simple string matching for human readability and easy maintenance.
"""

import logging
from pathlib import Path
from typing import Final

import yaml
from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RulesetData

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "data_collection"


class DataCollectionRuleset(Ruleset):
    """Ruleset for detecting data collection patterns in source code."""

    def __init__(self) -> None:
        """Initialise the data collection patterns ruleset."""
        super().__init__()
        self.rules: tuple[Rule, ...] | None = None
        logger.debug(f"Initialised {self.name} ruleset version {self.version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return _RULESET_NAME

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return _RULESET_DATA_VERSION

    @override
    def get_rules(self) -> tuple[Rule, ...]:
        """Get the data collection patterns rules.

        Returns:
            Immutable tuple of Rule objects containing all data collection patterns

        """
        if self.rules is None:
            # Load from YAML file with Pydantic validation
            yaml_file = (
                Path(__file__).parent
                / "data"
                / _RULESET_NAME
                / _RULESET_DATA_VERSION
                / f"{_RULESET_NAME}.yaml"
            )
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            ruleset_data = RulesetData.model_validate(data)
            self.rules = ruleset_data.to_rules()
            logger.debug(f"Loaded {len(self.rules)} data collection ruleset data")

        return self.rules
