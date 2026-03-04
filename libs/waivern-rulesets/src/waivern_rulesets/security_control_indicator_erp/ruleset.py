"""Security control indicator ERP extension ruleset.

Dolibarr-specific security control patterns with binary polarity.
Reuses SecurityControlIndicatorRule and SecurityControlIndicatorRulesetData
from the universal security_control_indicator ruleset — only the YAML data
and ruleset name differ.

Extension ruleset contract
--------------------------
Extension rulesets MUST only reference security domains already declared
in the SecurityDomain enum in waivern-security-evidence. This is enforced at
load time by SecurityControlIndicatorRulesetData.validate_rules(), which
cross-checks every rule's security_domain against the security_domains list
declared in this ruleset's own YAML.

Why all-positive polarity
--------------------------
The ERP extension's purpose is to recognise Dolibarr-proprietary security
mechanisms as positive signals. The generic security_control_indicator ruleset
already covers negative patterns (shell_exec, passthru, TLS disabled, etc.).
The negative patterns found in the Thrive ERP codebase are either covered by
the generic ruleset or too ambiguous to match reliably as simple substrings
(e.g. CURLOPT_SSL_VERIFYPEER appears for both secure and insecure assignments).

YAML data path
--------------
YAMLRuleset._get_data_file_path() resolves the YAML path from the concrete
subclass's module directory (not the base class), using ruleset_name as the
filename. This class's YAML therefore lives at:
    security_control_indicator_erp/data/1.0.0/security_control_indicator_erp.yaml
"""

from typing import ClassVar

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.security_control_indicator.ruleset import (
    SecurityControlIndicatorRule,
    SecurityControlIndicatorRulesetData,
)


class SecurityControlIndicatorERPRuleset(YAMLRuleset[SecurityControlIndicatorRule]):
    """Security control indicator ERP extension ruleset.

    Sector-specific Dolibarr vocabulary for security controls already defined
    in the universal security_control_indicator ruleset's domain taxonomy.
    """

    ruleset_name: ClassVar[str] = "security_control_indicator_erp"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[SecurityControlIndicatorRulesetData]
    ] = SecurityControlIndicatorRulesetData
