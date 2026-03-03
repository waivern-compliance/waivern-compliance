"""Personal data indicator ERP extension ruleset.

Dolibarr/ERP-specific patterns for existing personal data indicator categories.
Reuses PersonalDataIndicatorRule and PersonalDataIndicatorRulesetData from the
universal personal_data_indicator ruleset — only the YAML data and ruleset
name differ.
"""

from typing import ClassVar

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.personal_data_indicator.ruleset import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRulesetData,
)


class PersonalDataIndicatorERPRuleset(YAMLRuleset[PersonalDataIndicatorRule]):
    """Personal data indicator ERP extension ruleset.

    Sector-specific Dolibarr vocabulary for categories already defined
    in the universal personal_data_indicator ruleset.
    """

    ruleset_name: ClassVar[str] = "personal_data_indicator_erp"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[PersonalDataIndicatorRulesetData]
    ] = PersonalDataIndicatorRulesetData
