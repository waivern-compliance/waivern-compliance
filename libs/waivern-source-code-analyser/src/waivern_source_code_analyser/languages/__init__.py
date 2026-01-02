"""Language plugin system for source code analysis."""

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
    is_trivial_node,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    LanguageExtractionResult,
    MemberModel,
    ParameterModel,
    TypeDefinitionModel,
)
from waivern_source_code_analyser.languages.protocols import LanguageSupport
from waivern_source_code_analyser.languages.registry import (
    LanguageAlreadyRegisteredError,
    LanguageNotFoundError,
    LanguageRegistry,
)

__all__ = [
    # Base utilities
    "find_child_by_type",
    "find_children_by_type",
    "find_nodes_by_type",
    "get_node_text",
    "is_trivial_node",
    # Models
    "CallableModel",
    "LanguageExtractionResult",
    "MemberModel",
    "ParameterModel",
    "TypeDefinitionModel",
    # Protocol
    "LanguageSupport",
    # Registry
    "LanguageAlreadyRegisteredError",
    "LanguageNotFoundError",
    "LanguageRegistry",
]
