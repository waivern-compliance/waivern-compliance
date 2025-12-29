"""GitHub connector for extracting source code from repositories."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import override

from waivern_core import Schema
from waivern_core.base_connector import Connector
from waivern_core.errors import ConnectorExtractionError
from waivern_core.message import Message
from waivern_core.schemas import FilesystemMetadata, StandardInputDataItemModel

from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations

logger = logging.getLogger(__name__)

_CONNECTOR_NAME = "github"
_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]


class GitHubConnector(Connector):
    """GitHub connector for extracting source code files.

    This connector clones a GitHub repository and extracts file contents,
    transforming them into the standard_input schema format for compliance analysis.
    """

    def __init__(self, config: GitHubConnectorConfig) -> None:
        """Initialise GitHub connector with validated configuration.

        Args:
            config: Validated GitHub connector configuration

        """
        self._config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return _CONNECTOR_NAME

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Extract source code from GitHub repository.

        Args:
            output_schema: WCT schema for data validation

        Returns:
            Message containing extracted data in WCF schema format

        Raises:
            ConnectorExtractionError: If extraction fails or schema unsupported

        """
        # Validate output schema
        if not any(
            s.name == output_schema.name and s.version == output_schema.version
            for s in _SUPPORTED_OUTPUT_SCHEMAS
        ):
            raise ConnectorExtractionError(
                f"Unsupported output schema: {output_schema.name} {output_schema.version}"
            )

        clone_dir: str | None = None
        try:
            # Create temporary directory for clone
            clone_dir = tempfile.mkdtemp(prefix="waivern_github_")
            clone_path = Path(clone_dir)

            # Clone repository
            git_ops = GitOperations()
            git_ops.clone(self._config, clone_path)

            # Apply sparse checkout if patterns configured
            if self._config.include_patterns:
                git_ops.sparse_checkout(clone_path, self._config.include_patterns)

            # Collect files
            files = git_ops.collect_files(
                repo_dir=clone_path,
                include_patterns=self._config.include_patterns,
                exclude_patterns=self._config.exclude_patterns,
                max_files=self._config.max_files,
            )

            # Extract data items from files
            data_items = self._extract_files(files, clone_path)

            # Build output content
            content = self._build_output(output_schema, data_items)

            return Message(
                id=f"GitHub source from {self._config.repository}@{self._config.ref}",
                content=content,
                schema=output_schema,
            )

        except ConnectorExtractionError:
            raise
        except Exception as e:
            logger.exception("GitHub extraction failed")
            raise ConnectorExtractionError(str(e)) from e
        finally:
            # Clean up temporary directory
            if clone_dir:
                shutil.rmtree(clone_dir, ignore_errors=True)

    def _extract_files(
        self,
        files: list[Path],
        repo_dir: Path,
    ) -> list[StandardInputDataItemModel[FilesystemMetadata]]:
        """Extract data items from collected files.

        Args:
            files: List of file paths to extract
            repo_dir: Root directory of the cloned repository

        Returns:
            List of data items with file contents and metadata

        """
        data_items: list[StandardInputDataItemModel[FilesystemMetadata]] = []

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Skip binary files
                logger.debug("Skipping binary file: %s", file_path)
                continue
            except Exception as e:
                logger.warning("Failed to read file %s: %s", file_path, e)
                continue

            relative_path = file_path.relative_to(repo_dir)
            source = (
                f"github://{self._config.repository}@{self._config.ref}/{relative_path}"
            )

            metadata = FilesystemMetadata(
                source=source,
                connector_type=_CONNECTOR_NAME,
                file_path=str(relative_path),
            )

            data_items.append(
                StandardInputDataItemModel(
                    content=content,
                    metadata=metadata,
                )
            )

        return data_items

    def _build_output(
        self,
        schema: Schema,
        data_items: list[StandardInputDataItemModel[FilesystemMetadata]],
    ) -> dict[str, object]:
        """Build output content dictionary.

        Args:
            schema: Output schema
            data_items: List of extracted data items

        Returns:
            Dictionary conforming to standard_input schema

        """
        return {
            "schemaVersion": schema.version,
            "name": f"github_source_{self._config.repository.replace('/', '_')}",
            "description": f"Source code from GitHub: {self._config.repository}@{self._config.ref}",
            "contentEncoding": "utf-8",
            "source": f"github://{self._config.repository}@{self._config.ref}",
            "metadata": {
                "connector_type": _CONNECTOR_NAME,
                "repository": self._config.repository,
                "ref": self._config.ref,
                "clone_strategy": self._config.clone_strategy,
                "total_files": len(data_items),
            },
            "data": [item.model_dump() for item in data_items],
        }
