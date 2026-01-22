"""Protocol definitions for schema handling."""

from typing import Any, Protocol

from waivern_core.schemas import BaseFindingModel


class SchemaReader[T](Protocol):
    """Protocol for schema reader modules.

    Schema readers are modules that transform raw message content into typed
    Pydantic models. Each analyser has reader modules for each supported schema
    version (e.g., schema_readers/standard_input_1_0_0.py).

    This protocol enables type-safe dynamic module loading - analysers can use
    importlib to load readers while maintaining proper type inference.

    Type parameter T is the return type of read() (e.g., StandardInputDataModel).
    """

    def read(self, content: dict[str, Any]) -> T:
        """Transform raw content to typed model.

        Args:
            content: Raw message content dictionary.

        Returns:
            Typed Pydantic model for the schema.

        """
        ...


class SchemaInputHandler[T: BaseFindingModel](Protocol):
    """Protocol for schema-specific input handlers.

    All handlers must implement this interface to ensure consistent
    integration with the analyser. The analyser uses this protocol
    to remain schema-agnostic.

    Type parameter T is the finding model type (must extend BaseFindingModel).
    """

    def analyse(self, data: object) -> list[T]:
        """Analyse input data for patterns.

        Args:
            data: Schema-validated input data from the reader.

        Returns:
            List of findings.

        Raises:
            TypeError: If data is not the expected schema type.

        """
        ...
