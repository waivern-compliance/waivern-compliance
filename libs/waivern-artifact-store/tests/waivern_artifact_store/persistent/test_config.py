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

# =============================================================================
# Discriminated Union Tests (type-based config selection)
# =============================================================================


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
        from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore

        config = StoreConfig.model_validate({"type": "memory"})

        store = config.create_store()

        assert isinstance(store, AsyncInMemoryStore)


# =============================================================================
# MemoryStoreConfig Tests (in-memory store for testing)
# =============================================================================


class TestMemoryStoreConfig:
    """Test MemoryStoreConfig behaviour."""

    def test_create_store_returns_async_in_memory_store(self) -> None:
        from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore

        config = MemoryStoreConfig()

        store = config.create_store()

        assert isinstance(store, AsyncInMemoryStore)


# =============================================================================
# FilesystemStoreConfig Tests (local filesystem store)
# =============================================================================


class TestFilesystemStoreConfig:
    """Test FilesystemStoreConfig behaviour."""

    def test_base_path_defaults_to_waivern(self) -> None:
        config = FilesystemStoreConfig()

        assert config.base_path == Path(".waivern")

    def test_create_store_returns_local_filesystem_store(self) -> None:
        from waivern_artifact_store.persistent.filesystem import LocalFilesystemStore

        config = FilesystemStoreConfig()

        store = config.create_store()

        assert isinstance(store, LocalFilesystemStore)
        assert store.base_path == Path(".waivern")


# =============================================================================
# RemoteStoreConfig Tests (remote HTTP store - not yet implemented)
# =============================================================================


class TestRemoteStoreConfig:
    """Test RemoteStoreConfig behaviour."""

    def test_endpoint_url_is_required(self) -> None:
        with pytest.raises(ValidationError, match="endpoint_url"):
            RemoteStoreConfig()  # type: ignore[call-arg]

    def test_create_store_raises_not_implemented(self) -> None:
        config = RemoteStoreConfig(endpoint_url="https://example.com")

        with pytest.raises(NotImplementedError, match="RemoteHttpArtifactStore"):
            config.create_store()
