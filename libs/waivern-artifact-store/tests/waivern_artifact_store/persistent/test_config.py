"""Tests for persistent store configuration classes."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from waivern_artifact_store.persistent.config import (
    FilesystemStoreConfig,
    MemoryStoreConfig,
    RemoteStoreConfig,
    StoreConfig,
)


class TestStoreConfigDiscriminatedUnion:
    """Test that discriminated union correctly selects config class based on type."""

    def test_memory_type_returns_memory_store_config(self) -> None:
        config = StoreConfig.model_validate({"type": "memory"})

        assert isinstance(config.root, MemoryStoreConfig)

    def test_filesystem_type_returns_filesystem_store_config(self) -> None:
        config = StoreConfig.model_validate({"type": "filesystem"})

        assert isinstance(config.root, FilesystemStoreConfig)

    def test_remote_type_returns_remote_store_config(self) -> None:
        config = StoreConfig.model_validate(
            {"type": "remote", "endpoint_url": "https://example.com"}
        )

        assert isinstance(config.root, RemoteStoreConfig)

    def test_invalid_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            StoreConfig.model_validate({"type": "invalid"})

    def test_create_store_delegates_to_inner_config(self) -> None:
        config = StoreConfig.model_validate({"type": "memory"})

        # Should raise NotImplementedError from inner MemoryStoreConfig
        with pytest.raises(NotImplementedError, match="AsyncInMemoryStore"):
            config.create_store(run_id="test-run")


class TestMemoryStoreConfig:
    """Test MemoryStoreConfig behaviour."""

    def test_type_defaults_to_memory(self) -> None:
        config = MemoryStoreConfig()

        assert config.type == "memory"

    def test_create_store_raises_not_implemented(self) -> None:
        config = MemoryStoreConfig()

        with pytest.raises(NotImplementedError, match="AsyncInMemoryStore"):
            config.create_store(run_id="test-run")


class TestFilesystemStoreConfig:
    """Test FilesystemStoreConfig behaviour."""

    def test_type_defaults_to_filesystem(self) -> None:
        config = FilesystemStoreConfig()

        assert config.type == "filesystem"

    def test_base_path_defaults_to_waivern(self) -> None:
        config = FilesystemStoreConfig()

        assert config.base_path == Path(".waivern")

    def test_base_path_accepts_custom_path(self) -> None:
        config = FilesystemStoreConfig(base_path=Path("/custom/path"))

        assert config.base_path == Path("/custom/path")

    def test_create_store_raises_not_implemented(self) -> None:
        config = FilesystemStoreConfig()

        with pytest.raises(NotImplementedError, match="LocalFilesystemStore"):
            config.create_store(run_id="test-run")


class TestRemoteStoreConfig:
    """Test RemoteStoreConfig behaviour."""

    def test_type_defaults_to_remote(self) -> None:
        config = RemoteStoreConfig(endpoint_url="https://example.com")

        assert config.type == "remote"

    def test_endpoint_url_is_required(self) -> None:
        with pytest.raises(ValidationError, match="endpoint_url"):
            RemoteStoreConfig()  # type: ignore[call-arg]

    def test_api_key_is_optional(self) -> None:
        config = RemoteStoreConfig(endpoint_url="https://example.com")

        assert config.api_key is None

    def test_api_key_can_be_provided(self) -> None:
        config = RemoteStoreConfig(
            endpoint_url="https://example.com",
            api_key="secret-key",
        )

        assert config.api_key == "secret-key"

    def test_create_store_raises_not_implemented(self) -> None:
        config = RemoteStoreConfig(endpoint_url="https://example.com")

        with pytest.raises(NotImplementedError, match="RemoteHttpArtifactStore"):
            config.create_store(run_id="test-run")
