"""Tests for artifact store error types."""

from __future__ import annotations

from waivern_core.errors import ServiceConfigError

from waivern_artifact_store.errors import ArtifactStoreConfigError, ArtifactStoreError


class TestArtifactStoreConfigError:
    """ArtifactStoreConfigError sits on both the domain and category axes."""

    def test_is_service_config_error_subclass(self) -> None:
        assert isinstance(ArtifactStoreConfigError("bad config"), ServiceConfigError)

    def test_is_artifact_store_error_subclass(self) -> None:
        assert isinstance(ArtifactStoreConfigError("bad config"), ArtifactStoreError)
