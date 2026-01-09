"""Protocols for processing purpose analyser components."""

from typing import Protocol

from .schemas.types import ProcessingPurposeFindingModel


class SchemaInputHandler(Protocol):
    """Protocol for schema-specific input handlers.

    All handlers must implement this interface to ensure consistent
    integration with the analyser. The analyser uses this protocol
    to remain schema-agnostic.
    """

    def analyse(self, data: object) -> list[ProcessingPurposeFindingModel]:
        """Analyse input data for processing purpose patterns.

        Args:
            data: Schema-validated input data from the reader.

        Returns:
            List of processing purpose findings.

        Raises:
            TypeError: If data is not the expected schema type.

        """
        ...
