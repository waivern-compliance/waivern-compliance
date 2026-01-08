"""Tests for LanguageRegistry."""

from unittest.mock import MagicMock, patch

import pytest

from waivern_source_code_analyser.languages.registry import (
    LanguageAlreadyRegisteredError,
    LanguageNotFoundError,
    LanguageRegistry,
)


def _make_mock_language(name: str, extensions: list[str]) -> MagicMock:
    """Create a mock LanguageSupport implementation."""
    lang = MagicMock()
    lang.name = name
    lang.file_extensions = extensions
    return lang


@pytest.fixture
def clean_registry() -> LanguageRegistry:
    """Provide a clean registry for testing.

    Note: State isolation is handled by the autouse fixture in conftest.py.
    This fixture just provides a cleared registry as a starting point.
    """
    registry = LanguageRegistry()
    registry.clear()
    return registry


class TestLanguageRegistrySingleton:
    """Tests for LanguageRegistry singleton behaviour."""

    def test_registry_is_singleton(self) -> None:
        """Test that LanguageRegistry always returns the same instance."""
        registry1 = LanguageRegistry()
        registry2 = LanguageRegistry()

        assert registry1 is registry2


class TestLanguageRegistration:
    """Tests for language registration."""

    def test_register_language(self, clean_registry: LanguageRegistry) -> None:
        """Test that a language can be registered."""
        lang = _make_mock_language("php", [".php"])

        clean_registry.register(lang)

        assert clean_registry.is_registered("php")

    def test_register_duplicate_raises_error(
        self, clean_registry: LanguageRegistry
    ) -> None:
        """Test that registering a duplicate language raises an error."""
        lang1 = _make_mock_language("php", [".php"])
        lang2 = _make_mock_language("php", [".php"])

        clean_registry.register(lang1)

        with pytest.raises(LanguageAlreadyRegisteredError) as exc_info:
            clean_registry.register(lang2)

        assert "php" in str(exc_info.value)


class TestLanguageLookup:
    """Tests for language lookup methods."""

    def test_get_by_name(self, clean_registry: LanguageRegistry) -> None:
        """Test retrieving a language by its canonical name."""
        lang = _make_mock_language("typescript", [".ts", ".tsx"])
        clean_registry.register(lang)

        result = clean_registry.get("typescript")

        assert result is lang

    def test_get_by_name_not_found(self, clean_registry: LanguageRegistry) -> None:
        """Test that getting an unregistered language raises an error."""
        with pytest.raises(LanguageNotFoundError) as exc_info:
            clean_registry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_get_by_extension(self, clean_registry: LanguageRegistry) -> None:
        """Test retrieving a language by file extension."""
        lang = _make_mock_language("typescript", [".ts", ".tsx"])
        clean_registry.register(lang)

        result = clean_registry.get_by_extension(".tsx")

        assert result is lang

    def test_get_by_extension_not_found(self, clean_registry: LanguageRegistry) -> None:
        """Test that getting by unsupported extension raises an error."""
        with pytest.raises(LanguageNotFoundError) as exc_info:
            clean_registry.get_by_extension(".unknown")

        assert ".unknown" in str(exc_info.value)

    def test_is_registered(self, clean_registry: LanguageRegistry) -> None:
        """Test checking if a language is registered."""
        lang = _make_mock_language("php", [".php"])

        assert clean_registry.is_registered("php") is False

        clean_registry.register(lang)

        assert clean_registry.is_registered("php") is True


class TestLanguageListing:
    """Tests for listing languages and extensions."""

    def test_list_languages(self, clean_registry: LanguageRegistry) -> None:
        """Test listing all registered language names."""
        lang1 = _make_mock_language("php", [".php"])
        lang2 = _make_mock_language("typescript", [".ts", ".tsx"])
        clean_registry.register(lang1)
        clean_registry.register(lang2)

        result = clean_registry.list_languages()

        assert set(result) == {"php", "typescript"}

    def test_list_extensions(self, clean_registry: LanguageRegistry) -> None:
        """Test listing all supported file extensions."""
        lang1 = _make_mock_language("php", [".php"])
        lang2 = _make_mock_language("typescript", [".ts", ".tsx"])
        clean_registry.register(lang1)
        clean_registry.register(lang2)

        result = clean_registry.list_extensions()

        assert set(result) == {".php", ".ts", ".tsx"}


class TestLanguageRegistryState:
    """Tests for registry state management."""

    def test_clear_removes_all(self, clean_registry: LanguageRegistry) -> None:
        """Test that clear removes all registered languages."""
        lang = _make_mock_language("php", [".php"])
        clean_registry.register(lang)

        clean_registry.clear()

        assert clean_registry.is_registered("php") is False
        assert clean_registry.list_languages() == []
        assert clean_registry.list_extensions() == []

    def test_snapshot_and_restore_state(self) -> None:
        """Test that state can be captured and restored for test isolation."""
        registry = LanguageRegistry()
        original_state = LanguageRegistry.snapshot_state()

        # Modify the registry
        lang = _make_mock_language("test_lang", [".test"])
        registry.clear()
        registry.register(lang)

        assert registry.is_registered("test_lang")

        # Restore original state
        LanguageRegistry.restore_state(original_state)

        # test_lang should be gone, original state restored
        assert registry.is_registered("test_lang") is False

    def test_snapshot_and_restore_preserves_discovery_state(self) -> None:
        """Test that discovery state is preserved through snapshot/restore.

        If discover() was called before snapshot, it should not re-run
        entry point loading after restore.
        """
        registry = LanguageRegistry()
        original_state = LanguageRegistry.snapshot_state()

        mock_lang = _make_mock_language("discovered", [".disc"])
        mock_lang_class = MagicMock(return_value=mock_lang)
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_lang_class

        with patch(
            "waivern_source_code_analyser.languages.registry.entry_points"
        ) as mock_entry_points:
            mock_entry_points.return_value = [mock_ep]

            # Clear and run discovery
            registry.clear()
            registry.discover()

            # Snapshot after discovery
            post_discovery_state = LanguageRegistry.snapshot_state()

            # Clear again (resets discovered flag)
            registry.clear()

            # Restore post-discovery state
            LanguageRegistry.restore_state(post_discovery_state)

            # Reset the mock call count
            mock_entry_points.reset_mock()

            # discover() should NOT call entry_points again
            registry.discover()
            mock_entry_points.assert_not_called()

        # Cleanup
        LanguageRegistry.restore_state(original_state)


class TestLanguageDiscovery:
    """Tests for entry point discovery."""

    def test_discover_loads_entry_points(
        self, clean_registry: LanguageRegistry
    ) -> None:
        """Test that discover loads languages from entry points."""
        mock_lang = _make_mock_language("discovered", [".disc"])
        mock_lang_class = MagicMock(return_value=mock_lang)

        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_lang_class

        with patch(
            "waivern_source_code_analyser.languages.registry.entry_points"
        ) as mock_entry_points:
            mock_entry_points.return_value = [mock_ep]

            clean_registry.discover()

        assert clean_registry.is_registered("discovered")
