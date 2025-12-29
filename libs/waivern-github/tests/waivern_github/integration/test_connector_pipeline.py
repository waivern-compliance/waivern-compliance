"""Integration tests for the full GitHubConnector extraction pipeline."""

import pytest
from waivern_core import Schema

from waivern_github import GitHubConnector
from waivern_github.config import GitHubConnectorConfig

from .conftest import TEST_REPO


class TestConnectorPipeline:
    """Integration tests for the complete extraction pipeline."""

    @pytest.mark.integration
    def test_full_extraction_pipeline(self, require_git_and_network):
        """Test the complete extraction pipeline with a real repository."""
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "minimal",
            }
        )

        connector = GitHubConnector(config)
        schema = Schema("standard_input", "1.0.0")

        message = connector.extract(schema)

        # Verify message structure
        assert message.schema.name == "standard_input"
        assert message.schema.version == "1.0.0"

        # Verify content has expected structure
        content = message.content
        assert isinstance(content, dict)
        assert "data" in content
        assert isinstance(content["data"], list)
        assert len(content["data"]) > 0

        # Verify README was extracted
        data_items = content["data"]
        file_paths = [item["metadata"]["file_path"] for item in data_items]
        assert "README" in file_paths

        # Verify README content is present
        readme_item = next(
            item for item in data_items if item["metadata"]["file_path"] == "README"
        )
        assert "Hello World" in readme_item["content"]
