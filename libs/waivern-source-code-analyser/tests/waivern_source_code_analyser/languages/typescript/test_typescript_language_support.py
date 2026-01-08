"""Tests for TypeScriptLanguageSupport protocol implementation."""

from waivern_source_code_analyser.languages.protocols import LanguageSupport
from waivern_source_code_analyser.languages.registry import LanguageRegistry
from waivern_source_code_analyser.languages.typescript import TypeScriptLanguageSupport


class TestTypeScriptLanguageSupportProperties:
    """Tests for TypeScriptLanguageSupport properties."""

    def test_name_returns_typescript(self) -> None:
        """Test that name property returns 'typescript'."""
        ts = TypeScriptLanguageSupport()

        assert ts.name == "typescript"

    def test_file_extensions_returns_typescript_extensions(self) -> None:
        """Test that file_extensions returns all TypeScript extensions."""
        ts = TypeScriptLanguageSupport()

        extensions = ts.file_extensions

        # Should include common TypeScript extensions
        assert ".ts" in extensions
        assert ".tsx" in extensions
        assert ".mts" in extensions
        assert ".cts" in extensions


class TestTypeScriptLanguageSupportProtocol:
    """Tests for protocol conformance."""

    def test_implements_language_support_protocol(self) -> None:
        """Test that TypeScriptLanguageSupport satisfies the LanguageSupport protocol."""
        ts = TypeScriptLanguageSupport()

        # Should pass isinstance check due to @runtime_checkable
        assert isinstance(ts, LanguageSupport)

    def test_registered_via_entry_point(self) -> None:
        """Test that TypeScriptLanguageSupport is discoverable via entry points."""
        # Save and restore state to avoid test pollution
        original_state = LanguageRegistry.snapshot_state()

        try:
            registry = LanguageRegistry()
            registry.clear()
            registry.discover()

            # TypeScript should be registered after discovery
            assert registry.is_registered("typescript")

            # Should be able to retrieve it
            ts = registry.get("typescript")
            assert ts.name == "typescript"

        finally:
            LanguageRegistry.restore_state(original_state)
