"""Processing purposes ERP extension ruleset.

Dolibarr/ERP-specific patterns for existing processing purpose slugs.
Reuses ProcessingPurposeRule and ProcessingPurposesRulesetData from the
universal processing_purposes ruleset — only the YAML data and ruleset
name differ.

Extension ruleset contract
--------------------------
Extension rulesets MUST only reference purpose slugs already declared
in the universal processing_purposes ruleset. This is enforced at load
time by ProcessingPurposesRulesetData.validate_rules(), which cross-checks
every rule's `name` against the `purposes` list and every rule's `purpose`
against the `purpose_slugs` list — both of which must be declared in this
ruleset's own YAML.

The shared slug vocabulary is what makes the downstream pipeline transparent
to the split: SecurityEvidenceNormaliser routes by slug value, not by which
ruleset produced the finding. audit_logging findings from this ruleset map to
the same security domain as audit_logging findings from the core ruleset.

YAML data path
--------------
YAMLRuleset._get_data_file_path() resolves the YAML path from the concrete
subclass's module directory (not the base class), using ruleset_name as the
filename. This class's YAML therefore lives at:
    processing_purposes_erp/data/1.0.0/processing_purposes_erp.yaml
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
