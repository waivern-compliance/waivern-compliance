"""WCT Rulesets package for compliance pattern definitions."""

from wct.rulesets.base import (
    RulesetError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)
from wct.rulesets.data_collection import DataCollectionRuleset

# Import and register built-in rulesets automatically
from wct.rulesets.personal_data import PersonalDataRuleset
from wct.rulesets.processing_purposes import ProcessingPurposesRuleset
from wct.rulesets.service_integrations import ServiceIntegrationsRuleset

# Built-in rulesets - internal use only
_BUILTIN_RULESETS = (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    DataCollectionRuleset,
    ServiceIntegrationsRuleset,
)

# Register all built-in rulesets automatically on import
_registry = RulesetRegistry()
for _ruleset_class in _BUILTIN_RULESETS:
    # Use the module name as the ruleset name (e.g., personal_data_code_functions)
    _module_name = _ruleset_class.__module__.split(".")[-1]
    _registry.register(_module_name, _ruleset_class)

__all__ = (
    "RulesetError",
    "RulesetLoader",
    "RulesetNotFoundError",
)
