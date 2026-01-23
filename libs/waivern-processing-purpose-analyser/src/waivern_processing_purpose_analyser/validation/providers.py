"""Provider implementations for LLM validation.

These providers implement the shared protocols from waivern-analysers-shared,
adapting them to ProcessingPurposeAnalyser's domain.

Provider naming convention:
- Schema-specific providers: prefixed with schema name (e.g., SourceCode*)
- Domain-specific providers: prefixed with domain name (e.g., ProcessingPurpose*)

Testing rationale:
    The ConcernProvider classes have NO dedicated unit tests because:

    1. They implement trivial behaviour (simple attribute access)
    2. The type checker validates protocol compliance with ConcernProvider[T]
    3. The grouping logic that uses these providers is tested in
       waivern-analysers-shared/tests/llm_validation/test_grouping.py

    SourceProvider implementations MAY warrant tests if they have non-trivial
    logic (e.g., error handling for missing metadata, content transformation).
"""

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)


class SourceCodeSourceProvider:
    """Provides source ID and content for source_code schema findings.

    Specific to the source_code schema - extracts file paths from finding
    metadata and looks up file content from a pre-built map.

    For other schemas (e.g., database, API), different SourceProvider
    implementations would be needed.

    Note: The shared ExtendedContextLLMValidationStrategy handles missing
    source IDs and content gracefully by marking those findings as "skipped".
    """

    def __init__(self, file_contents: dict[str, str]) -> None:
        """Initialise with file content map.

        Args:
            file_contents: Map of file paths to their content.

        """
        self._file_contents = file_contents

    def get_source_id(self, finding: ProcessingPurposeIndicatorModel) -> str:
        """Extract file path from finding metadata.

        Args:
            finding: The finding to extract source from.

        Returns:
            File path from the finding's metadata.source field.

        """
        return finding.metadata.source

    def get_source_content(self, source_id: str) -> str | None:
        """Return file content for the given path.

        Args:
            source_id: File path from get_source_id().

        Returns:
            File content if available, None otherwise.

        """
        return self._file_contents.get(source_id)


class ProcessingPurposeConcernProvider:
    """Groups findings by processing purpose.

    The 'concern' for processing purpose analysis is the purpose itself
    (e.g., "Payment Processing", "User Authentication").
    """

    @property
    def concern_key(self) -> str:
        """Return the attribute name for grouping."""
        return "purpose"

    def get_concern(self, finding: ProcessingPurposeIndicatorModel) -> str:
        """Extract purpose from finding.

        Args:
            finding: The finding to extract purpose from.

        Returns:
            The purpose name.

        """
        return finding.purpose
