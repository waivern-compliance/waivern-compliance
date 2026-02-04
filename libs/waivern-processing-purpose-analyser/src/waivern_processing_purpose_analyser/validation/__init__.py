"""Validation components for ProcessingPurposeAnalyser.

This package provides LLM validation infrastructure using the shared
waivern-analysers-shared components with analyser-specific implementations.

Naming convention:
- SourceCode* prefix: Components specific to source_code schema input
- ProcessingPurpose* prefix: Components that work across all input schemas
"""

from .extended_context_strategy import SourceCodeValidationStrategy
from .orchestration import create_validation_orchestrator
from .providers import (
    ProcessingPurposeConcernProvider,
    SourceCodeSourceProvider,
)

__all__ = [
    # Schema-specific (source_code)
    "SourceCodeSourceProvider",
    "SourceCodeValidationStrategy",
    # Domain-specific (all schemas)
    "ProcessingPurposeConcernProvider",
    # Factory
    "create_validation_orchestrator",
]
