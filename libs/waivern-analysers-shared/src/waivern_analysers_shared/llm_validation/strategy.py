"""Abstract base class for LLM validation strategies."""

from abc import ABC, abstractmethod

from waivern_core.schemas import BaseFindingModel
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig


class LLMValidationStrategy[T: BaseFindingModel](ABC):
    """Abstract base class for LLM validation strategies.

    Defines the interface that all validation strategies must implement.
    Concrete implementations handle batching and LLM interaction differently.

    Type parameter T is the finding type, must be a BaseFindingModel subclass.
    """

    @abstractmethod
    def validate_findings(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> tuple[list[T], bool]:
        """Validate findings using LLM.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            Tuple of (validated findings, all_succeeded flag).

        """
        ...
