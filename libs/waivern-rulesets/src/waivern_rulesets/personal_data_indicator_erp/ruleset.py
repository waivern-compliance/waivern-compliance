"""Personal data indicator ERP extension ruleset.

Dolibarr/ERP-specific patterns for existing personal data indicator categories.
Reuses PersonalDataIndicatorRule and PersonalDataIndicatorRulesetData from the
universal personal_data_indicator ruleset — only the YAML data and ruleset
name differ.

Extension ruleset contract
--------------------------
Extension rulesets MUST only reference categories already declared in the
universal personal_data_indicator ruleset. This is enforced at load time by
PersonalDataIndicatorRulesetData.validate_rule_categories(), which cross-checks
every rule's `category` against the `categories` list declared in this
ruleset's own YAML.

YAML data path
--------------
YAMLRuleset._get_data_file_path() resolves the YAML path from the concrete
subclass's module directory (not the base class), using ruleset_name as the
filename. This class's YAML therefore lives at:
    personal_data_indicator_erp/data/1.0.0/personal_data_indicator_erp.yaml
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
