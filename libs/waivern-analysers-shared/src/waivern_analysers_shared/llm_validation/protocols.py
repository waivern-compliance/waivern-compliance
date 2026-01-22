"""Protocols for generic LLM validation strategies.

These protocols define the contracts that analysers must implement to use
the shared validation infrastructure. Concrete implementations live in
individual analyser packages.

Example implementations:
    - ProcessingPurposeSourceProvider (in waivern-processing-purpose-analyser)
    - PersonalDataConcernProvider (in waivern-personal-data-analyser)
"""

from typing import Protocol

from waivern_core import Finding


class SourceProvider[T: Finding](Protocol):
    """Provides source identification and content for validation context.

    Implementations extract source information from findings and provide
    access to the full source content when available.

    Type parameter T is the finding type.

    Example:
        class ProcessingPurposeSourceProvider:
            def __init__(self, file_content_map: dict[str, str]) -> None:
                self._files = file_content_map

            def get_source_id(self, finding: ProcessingPurposeFindingModel) -> str:
                return finding.metadata.source  # File path

            def get_source_content(self, source_id: str) -> str | None:
                return self._files.get(source_id)

    """

    def get_source_id(self, finding: T) -> str:
        """Extract source identifier from a finding.

        The source identifier is used for grouping findings by origin
        (e.g., file path, table name, API endpoint).

        Args:
            finding: The finding to extract source from.

        Returns:
            Source identifier string.

        """
        ...

    def get_source_content(self, source_id: str) -> str | None:
        """Return the content of the source.

        Used to include full source context in validation prompts
        when grouping by source.

        Args:
            source_id: The source identifier from get_source_id().

        Returns:
            Source content if available, None otherwise.

        """
        ...


class ConcernProvider[T: Finding](Protocol):
    """Defines what the 'compliance concern' is for an analyser.

    The concern is the attribute used for grouping findings during
    sampling-based validation (e.g., purpose, data_category, subject_type).

    Type parameter T is the finding type.

    Example:
        class ProcessingPurposeConcernProvider:
            @property
            def concern_key(self) -> str:
                return "purpose"

            def get_concern(self, finding: ProcessingPurposeFindingModel) -> str:
                return finding.purpose  # e.g., "Payment Processing"

    """

    @property
    def concern_key(self) -> str:
        """The attribute name for output metadata.

        Used in validation summaries and removed groups reporting.

        Returns:
            Attribute name (e.g., "purpose", "data_category", "subject_type").

        """
        ...

    def get_concern(self, finding: T) -> str:
        """Extract the concern value from a finding.

        May be a simple attribute access or derived from multiple attributes.
        Used for grouping findings during validation.

        Args:
            finding: The finding to extract concern from.

        Returns:
            Concern value (e.g., "Payment Processing", "Email Address").

        """
        ...
