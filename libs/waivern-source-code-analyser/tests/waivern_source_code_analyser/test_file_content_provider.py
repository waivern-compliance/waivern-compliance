"""Tests for SourceCodeFileContentProvider."""

from waivern_source_code_analyser import (
    SourceCodeDataModel,
    SourceCodeFileContentProvider,
)
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)


class TestSourceCodeFileContentProvider:
    """Tests for SourceCodeFileContentProvider.

    Business behaviour: Provides efficient access to file content from
    source_code schema data, with token estimates for batching decisions.
    """

    def test_returns_content_for_existing_file(self) -> None:
        """Should return file content when file exists in source data."""
        source_data = _make_source_data(
            [
                {"file_path": "src/app.py", "raw_content": "print('hello')"},
            ]
        )
        provider = SourceCodeFileContentProvider(source_data)

        content = provider.get_file_content("src/app.py")

        assert content == "print('hello')"

    def test_returns_none_for_missing_file(self) -> None:
        """Should return None when file doesn't exist in source data."""
        source_data = _make_source_data(
            [
                {"file_path": "src/app.py", "raw_content": "print('hello')"},
            ]
        )
        provider = SourceCodeFileContentProvider(source_data)

        content = provider.get_file_content("src/nonexistent.py")

        assert content is None

    def test_get_all_files_includes_token_estimates(self) -> None:
        """Should return FileInfo with token estimates for batching decisions."""
        source_data = _make_source_data(
            [
                {"file_path": "src/app.py", "raw_content": "a" * 100},
                {"file_path": "src/utils.py", "raw_content": "b" * 200},
            ]
        )
        provider = SourceCodeFileContentProvider(source_data)

        files = provider.get_all_files()

        # Larger files should have proportionally larger token estimates
        assert (
            files["src/app.py"].estimated_tokens
            < files["src/utils.py"].estimated_tokens
        )


def _make_source_data(files: list[dict[str, str]]) -> SourceCodeDataModel:
    """Create SourceCodeDataModel for testing.

    Args:
        files: List of dicts with file_path and raw_content keys.

    Returns:
        SourceCodeDataModel instance.

    """
    return SourceCodeDataModel(
        schemaVersion="1.0.0",
        name="test",
        description="test data",
        source="test",
        metadata=SourceCodeAnalysisMetadataModel(
            total_files=len(files),
            total_lines=0,
            analysis_timestamp="2025-01-01T00:00:00Z",
        ),
        data=[
            SourceCodeFileDataModel(
                file_path=f["file_path"],
                language="python",
                raw_content=f["raw_content"],
                metadata=SourceCodeFileMetadataModel(
                    file_size=len(f["raw_content"]),
                    line_count=1,
                ),
            )
            for f in files
        ],
    )
