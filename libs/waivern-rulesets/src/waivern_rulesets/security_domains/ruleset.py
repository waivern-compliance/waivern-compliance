"""Security domains vocabulary ruleset.

A flat vocabulary declaration ruleset — one rule per SecurityDomain enum value
(defined in waivern-core). Its sole consumer is DocumentEvidenceExtractor, which
reads the domain names to build the LLM classification prompt. It is not a
detection ruleset (no patterns) and not a classification ruleset (no framework
mapping).
"""

from typing import ClassVar

from pydantic import Field
from waivern_core import ClassificationRule, RulesetData, SecurityDomain

from waivern_rulesets.core.base import YAMLRuleset


class SecurityDomainRule(ClassificationRule):
    """A rule representing a single security domain in the classification vocabulary.

    The security_domain field is validated by Pydantic against the SecurityDomain
    enum at load time — any YAML value not in the enum is rejected immediately.
    """

    security_domain: SecurityDomain = Field(
        description="The security domain this rule declares"
    )


class SecurityDomainsRulesetData(RulesetData[SecurityDomainRule]):
    """Security domains ruleset data.

    No extra data fields beyond the standard rules list. Pydantic validates each
    rule's security_domain against the SecurityDomain enum; RulesetData validates
    unique rule names and minimum one rule.
    """

    pass


class SecurityDomainsRuleset(YAMLRuleset[SecurityDomainRule]):
    """Security domains vocabulary ruleset.

    Declares the complete set of security domain labels used by
    DocumentEvidenceExtractor when classifying documents via LLM. Referenced in
    runbooks via: domain_ruleset: local/security_domains/1.0.0
    """

    ruleset_name: ClassVar[str] = "security_domains"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[SecurityDomainsRulesetData]
    ] = SecurityDomainsRulesetData
