"""Waivern Compliance Framework - Core Abstractions.

This package provides the base abstractions that all Waivern components must implement,
including dependency injection infrastructure for service management.
"""

__version__ = "0.1.0"

from waivern_core.base_analyser import Analyser
from waivern_core.base_connector import Connector
from waivern_core.base_ruleset import BaseRuleset, RulesetError
from waivern_core.component_factory import ComponentConfig, ComponentFactory
from waivern_core.errors import (
    AnalyserConfigError,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
    ConnectorConfigError,
    ConnectorError,
    ConnectorExtractionError,
    MessageValidationError,
    WaivernError,
)
from waivern_core.message import Message
from waivern_core.ruleset_types import BaseRule, RuleComplianceData, RulesetData
from waivern_core.schemas import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
)
from waivern_core.services import (
    BaseComponentConfiguration,
    BaseServiceConfiguration,
    ComponentRegistry,
    ServiceContainer,
    ServiceDescriptor,
    ServiceFactory,
    ServiceProvider,
)
from waivern_core.testing import AnalyserContractTests, ComponentFactoryContractTests
from waivern_core.types import InputRequirement
from waivern_core.utils import update_analyses_chain

__all__ = [
    # Version
    "__version__",
    # Base classes
    "Analyser",
    "BaseRuleset",
    "Connector",
    "Message",
    "Schema",
    # Schema utilities
    "SchemaLoader",
    "JsonSchemaLoader",
    # Ruleset types
    "BaseRule",
    "RuleComplianceData",
    "RulesetData",
    # Dependency Injection
    "AnalyserContractTests",
    "BaseComponentConfiguration",
    "BaseServiceConfiguration",
    "ComponentConfig",
    "ComponentFactory",
    "ComponentFactoryContractTests",
    "ComponentRegistry",
    "ServiceContainer",
    "ServiceDescriptor",
    "ServiceFactory",
    "ServiceProvider",
    # Types
    "InputRequirement",
    # Utilities
    "update_analyses_chain",
    # Errors
    "WaivernError",
    "AnalyserConfigError",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "ConnectorError",
    "ConnectorConfigError",
    "ConnectorExtractionError",
    "MessageValidationError",
    "RulesetError",
    "SchemaLoadError",
]
