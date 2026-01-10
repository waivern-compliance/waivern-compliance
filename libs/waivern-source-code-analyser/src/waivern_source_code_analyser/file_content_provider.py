"""File content provider for source_code schema data."""

from waivern_analysers_shared.llm_validation.file_content import FileInfo
from waivern_analysers_shared.llm_validation.token_estimation import estimate_tokens

from .schemas.source_code import SourceCodeDataModel


class SourceCodeFileContentProvider:
    """File content provider for source_code schema data.

    Extracts file content from SourceCodeDataModel structure,
    building an index for efficient lookups. Content is loaded
    lazily via get_file_content() to avoid memory overhead.
    """

    def __init__(self, source_data: SourceCodeDataModel) -> None:
        """Initialise provider with source code schema data.

        Args:
            source_data: Pydantic model conforming to source_code schema v1.0.0.

        """
        self._file_metadata: dict[str, FileInfo] = {}
        self._file_content: dict[str, str] = {}
        self._build_index(source_data)

    def _build_index(self, source_data: SourceCodeDataModel) -> None:
        """Build file index from source data for O(1) lookups."""
        for file_data in source_data.data:
            file_path = file_data.file_path
            content = file_data.raw_content
            self._file_content[file_path] = content
            self._file_metadata[file_path] = FileInfo(
                file_path=file_path,
                estimated_tokens=estimate_tokens(content),
            )

    def get_file_content(self, file_path: str) -> str | None:
        """Get content for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            File content if found, None otherwise.

        """
        return self._file_content.get(file_path)

    def get_all_files(self) -> dict[str, FileInfo]:
        """Get all files with their metadata (path and token estimates).

        Returns:
            Dict mapping file paths to FileInfo objects.
            Use get_file_content() to load actual content.

        """
        return self._file_metadata
