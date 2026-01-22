"""Abstract base class for LLM validation strategies."""

from abc import ABC, abstractmethod

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .models import LLMValidationOutcome


class LLMValidationStrategy[T: Finding](ABC):
    """Abstract base class for LLM validation strategies.

    Defines the interface that all validation strategies must implement.
    Concrete implementations handle batching and LLM interaction differently.

    Type parameter T uses the ``Finding`` protocol bound (not ``BaseFindingModel``)
    because protocols provide structural typing that avoids generic invariance
    issues. A ``BaseFindingModel[ChildMetadata]`` is NOT a subtype of
    ``BaseFindingModel[BaseMetadata]`` due to invariance, but any finding class
    satisfies the ``Finding`` protocol regardless of its metadata type parameter.
    """

    @abstractmethod
    def validate_findings(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> LLMValidationOutcome[T]:
        """Validate findings using LLM.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            LLMValidationOutcome with detailed breakdown of validation results.

        """
        ...
