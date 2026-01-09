"""File content provider protocol for token-aware batching.

Defines the contract for accessing file content from schema data structures.
Concrete implementations live in consumer packages (e.g., processing-purpose-analyser).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class FileInfo:
    """File metadata for batching decisions."""

    file_path: str
    content: str
    estimated_tokens: int


class FileContentProvider(Protocol):
    """Protocol for accessing file content from schema data.

    Implementations extract file content from different schema structures
    (e.g., source_code, database schemas) for use in batched validation.
    """

    def get_file_content(self, file_path: str) -> str | None:
        """Get content for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            File content if found, None otherwise.

        """
        ...

    def get_all_files(self) -> dict[str, FileInfo]:
        """Get all files with their content and token estimates.

        Returns:
            Dict mapping file paths to FileInfo objects.

        """
        ...
