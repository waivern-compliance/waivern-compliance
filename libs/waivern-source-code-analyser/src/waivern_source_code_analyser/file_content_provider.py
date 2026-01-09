"""File content provider for source_code schema data."""

from waivern_analysers_shared.llm_validation.file_content import FileInfo
from waivern_analysers_shared.llm_validation.token_estimation import estimate_tokens

from .schemas.source_code import SourceCodeDataModel


class SourceCodeFileContentProvider:
    """File content provider for source_code schema data.

    Extracts file content from SourceCodeDataModel structure,
    building an index for efficient lookups.
    """

    def __init__(self, source_data: SourceCodeDataModel) -> None:
        """Initialise provider with source code schema data.

        Args:
            source_data: Pydantic model conforming to source_code schema v1.0.0.

        """
        self._file_index: dict[str, FileInfo] = {}
        self._build_index(source_data)

    def _build_index(self, source_data: SourceCodeDataModel) -> None:
        """Build file index from source data for O(1) lookups."""
        for file_data in source_data.data:
            file_path = file_data.file_path
            content = file_data.raw_content
            self._file_index[file_path] = FileInfo(
                file_path=file_path,
                content=content,
                estimated_tokens=estimate_tokens(content),
            )

    def get_file_content(self, file_path: str) -> str | None:
        """Get content for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            File content if found, None otherwise.

        """
        file_info = self._file_index.get(file_path)
        return file_info.content if file_info else None

    def get_all_files(self) -> dict[str, FileInfo]:
        """Get all files with their content and token estimates.

        Returns:
            Dict mapping file paths to FileInfo objects.

        """
        return self._file_index
