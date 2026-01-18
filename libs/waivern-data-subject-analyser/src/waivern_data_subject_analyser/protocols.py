"""Protocols for data subject analyser components."""

from typing import Protocol

from .schemas.types import DataSubjectIndicatorModel


class SchemaInputHandler(Protocol):
    """Protocol for schema-specific input handlers.

    All handlers must implement this interface to ensure consistent
    integration with the analyser. The analyser uses this protocol
    to remain schema-agnostic.
    """

    def analyse(self, data: object) -> list[DataSubjectIndicatorModel]:
        """Analyse input data for data subject patterns.

        Args:
            data: Schema-validated input data from the reader.

        Returns:
            List of data subject indicators.

        Raises:
            TypeError: If data is not the expected schema type.

        """
        ...
