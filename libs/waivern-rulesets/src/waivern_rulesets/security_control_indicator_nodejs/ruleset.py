"""Security control indicator Node.js extension ruleset.

Node.js/Express-specific security control patterns with binary polarity.
Reuses SecurityControlIndicatorRule and SecurityControlIndicatorRulesetData
from the universal security_control_indicator ruleset — only the YAML data
and ruleset name differ.

Extension ruleset contract
--------------------------
Extension rulesets MUST only reference security domains already declared
in the SecurityDomain enum in waivern-core. This is enforced at
load time by SecurityControlIndicatorRulesetData.validate_rules(), which
cross-checks every rule's security_domain against the security_domains list
declared in this ruleset's own YAML.

Why this extension is needed
-----------------------------
The generic security_control_indicator ruleset uses language-agnostic patterns
(bcrypt, argon2, shell_exec) but misses Node.js/Express idioms entirely:
- JWT verification is jwt.verify() not jwt_verify
- Security headers are set via the helmet() middleware
- Rate limiting is rateLimit() from express-rate-limit
- HTML escaping uses escapeHtml() / sanitizeInput() rather than htmlspecialchars
- Shell execution surfaces as require('child_process') not shell_exec

YAML data path
--------------
YAMLRuleset._get_data_file_path() resolves the YAML path from the concrete
subclass's module directory (not the base class), using ruleset_name as the
filename. This class's YAML therefore lives at:
    security_control_indicator_nodejs/data/1.0.0/security_control_indicator_nodejs.yaml
"""

from typing import ClassVar

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.security_control_indicator.ruleset import (
    SecurityControlIndicatorRule,
    SecurityControlIndicatorRulesetData,
)


class SecurityControlIndicatorNodejsRuleset(YAMLRuleset[SecurityControlIndicatorRule]):
    """Security control indicator Node.js extension ruleset.

    Node.js/Express-specific vocabulary for security controls already defined
    in the universal security_control_indicator ruleset's domain taxonomy.
    """

    ruleset_name: ClassVar[str] = "security_control_indicator_nodejs"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[SecurityControlIndicatorRulesetData]
    ] = SecurityControlIndicatorRulesetData
