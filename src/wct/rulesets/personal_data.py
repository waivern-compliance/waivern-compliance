"""Personal data detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It serves as a base for compliance with GDPR and other privacy regulations.
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
_RULESET_NAME: Final[str] = "personal_data"


class PersonalDataRuleset(Ruleset):
    """Class-based personal data detection ruleset with logging support.

    This class provides structured access to personal data patterns
    with built-in logging capabilities for debugging and monitoring.
    """

    def __init__(self) -> None:
        """Initialise the personal data ruleset."""
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
        """Get the personal data rules.

        Returns:
            Immutable tuple of Rule objects containing all GDPR-compliant personal data patterns

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

            ruleset_data = RulesetData(**data)
            self.rules = ruleset_data.to_rules()
            logger.debug(f"Loaded {len(self.rules)} personal data ruleset data")

        return self.rules
