"""Tests for JavaScriptLanguageSupport protocol implementation."""

from waivern_source_code_analyser.languages.javascript import JavaScriptLanguageSupport
from waivern_source_code_analyser.languages.protocols import LanguageSupport
from waivern_source_code_analyser.languages.registry import LanguageRegistry


class TestJavaScriptLanguageSupportProperties:
    """Tests for JavaScriptLanguageSupport properties."""

    def test_name_returns_javascript(self) -> None:
        """Test that name property returns 'javascript'."""
        js = JavaScriptLanguageSupport()

        assert js.name == "javascript"

    def test_file_extensions_returns_javascript_extensions(self) -> None:
        """Test that file_extensions returns all JavaScript extensions."""
        js = JavaScriptLanguageSupport()

        extensions = js.file_extensions

        # Should include common JavaScript extensions
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".mjs" in extensions
        assert ".cjs" in extensions


class TestJavaScriptLanguageSupportProtocol:
    """Tests for protocol conformance."""

    def test_implements_language_support_protocol(self) -> None:
        """Test that JavaScriptLanguageSupport satisfies the LanguageSupport protocol."""
        js = JavaScriptLanguageSupport()

        # Should pass isinstance check due to @runtime_checkable
        assert isinstance(js, LanguageSupport)

    def test_registered_via_entry_point(self) -> None:
        """Test that JavaScriptLanguageSupport is discoverable via entry points."""
        # Save and restore state to avoid test pollution
        original_state = LanguageRegistry.snapshot_state()

        try:
            registry = LanguageRegistry()
            registry.clear()
            registry.discover()

            # JavaScript should be registered after discovery
            assert registry.is_registered("javascript")

            # Should be able to retrieve it
            js = registry.get("javascript")
            assert js.name == "javascript"

        finally:
            LanguageRegistry.restore_state(original_state)
