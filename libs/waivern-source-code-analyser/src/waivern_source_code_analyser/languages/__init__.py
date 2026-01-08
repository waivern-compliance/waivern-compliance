"""Language plugin system for source code analysis."""

from waivern_source_code_analyser.languages.protocols import LanguageSupport
from waivern_source_code_analyser.languages.registry import (
    LanguageAlreadyRegisteredError,
    LanguageNotFoundError,
    LanguageRegistry,
)

__all__ = [
    # Protocol
    "LanguageSupport",
    # Registry
    "LanguageAlreadyRegisteredError",
    "LanguageNotFoundError",
    "LanguageRegistry",
]
