"""Processing purposes ERP extension ruleset.

Dolibarr/ERP-specific patterns for existing processing purpose slugs.
Reuses ProcessingPurposeRule and ProcessingPurposesRulesetData from the
universal processing_purposes ruleset — only the YAML data and ruleset
name differ.
"""

from typing import ClassVar

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.processing_purposes.ruleset import (
    ProcessingPurposeRule,
    ProcessingPurposesRulesetData,
)


class ProcessingPurposesERPRuleset(YAMLRuleset[ProcessingPurposeRule]):
    """Processing purposes ERP extension ruleset.

    Sector-specific Dolibarr vocabulary for purpose slugs already defined
    in the universal processing_purposes ruleset.
    """

    ruleset_name: ClassVar[str] = "processing_purposes_erp"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ProcessingPurposesRulesetData]
    ] = ProcessingPurposesRulesetData
