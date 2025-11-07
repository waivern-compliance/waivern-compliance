"""Tests for standard_input v1.0.0 producer."""

from pathlib import Path


class _MockStat:
    """Mock os.stat result for testing."""

    def __init__(self, size: int) -> None:
        """Initialize mock stat with size."""
        self.st_size = size


class TestStandardInputProducer:
    """Tests for standard_input schema v1.0.0 producer module."""

    def test_produce_transforms_single_file_data_to_schema(self) -> None:
        """Test producer transforms single file data with all required fields."""
        from waivern_community.connectors.filesystem.schema_producers import (
            standard_input_1_0_0,
        )

        # Arrange: Data structure from connector (matches _collect_file_data output)
        test_path = Path("/test/file.txt")

        all_file_data = [
            {
                "path": test_path,
                "content": "Test file content",
                "stat": _MockStat(17),
            }
        ]

        # Config data needed for transformation
        config_data = {
            "path": test_path,
            "encoding": "utf-8",
            "exclude_patterns": [],
            "is_file": True,
        }

        schema_version = "1.0.0"

        # Act
        result = standard_input_1_0_0.produce(
            schema_version=schema_version,
            all_file_data=all_file_data,
            config_data=config_data,
        )

        # Assert: Validate standard_input schema structure
        assert result["schemaVersion"] == "1.0.0"
        assert result["name"] == "standard_input_from_file.txt"
        assert result["description"] == "Content from file file.txt"
        assert result["contentEncoding"] == "utf-8"
        assert result["source"] == str(test_path)
        assert result["metadata"]["file_count"] == 1
        assert result["metadata"]["total_size_bytes"] == 17
        assert result["metadata"]["source_type"] == "file"
        assert result["metadata"]["exclude_patterns"] == []
        assert len(result["data"]) == 1
        assert result["data"][0]["content"] == "Test file content"
        assert "metadata" in result["data"][0]
        assert result["data"][0]["metadata"]["file_path"] == str(test_path)
        assert result["data"][0]["metadata"]["connector_type"] == "filesystem_connector"

    def test_produce_transforms_multiple_files_to_schema(self) -> None:
        """Test producer transforms directory/multi-file data correctly."""
        from waivern_community.connectors.filesystem.schema_producers import (
            standard_input_1_0_0,
        )

        # Arrange: Multiple files from a directory
        test_dir = Path("/test/mydir")

        all_file_data = [
            {
                "path": test_dir / "file1.txt",
                "content": "Content of file 1",
                "stat": _MockStat(18),
            },
            {
                "path": test_dir / "file2.txt",
                "content": "Content of file 2",
                "stat": _MockStat(18),
            },
            {
                "path": test_dir / "subdir" / "file3.txt",
                "content": "Content of file 3",
                "stat": _MockStat(18),
            },
        ]

        config_data = {
            "path": test_dir,
            "encoding": "utf-8",
            "exclude_patterns": ["*.log"],
            "is_file": False,
        }

        schema_version = "1.0.0"

        # Act
        result = standard_input_1_0_0.produce(
            schema_version=schema_version,
            all_file_data=all_file_data,
            config_data=config_data,
        )

        # Assert: Directory-specific structure
        assert result["schemaVersion"] == "1.0.0"
        assert result["name"] == "standard_input_from_mydir_directory"
        assert result["description"] == "Content from directory mydir (3 files)"
        assert result["contentEncoding"] == "utf-8"
        assert result["source"] == str(test_dir)
        assert result["metadata"]["file_count"] == 3
        assert result["metadata"]["total_size_bytes"] == 54  # 18 + 18 + 18
        assert result["metadata"]["source_type"] == "directory"
        assert result["metadata"]["exclude_patterns"] == ["*.log"]
        assert len(result["data"]) == 3

        # Verify all files included
        file_contents = [item["content"] for item in result["data"]]
        assert "Content of file 1" in file_contents
        assert "Content of file 2" in file_contents
        assert "Content of file 3" in file_contents

        # Verify each data entry has metadata
        for data_entry in result["data"]:
            assert "metadata" in data_entry
            assert data_entry["metadata"]["connector_type"] == "filesystem_connector"
            assert "file_path" in data_entry["metadata"]
