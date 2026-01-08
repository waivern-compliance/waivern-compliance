"""Tests for PHPLanguageSupport protocol implementation."""

from waivern_source_code_analyser.languages.php import PHPLanguageSupport
from waivern_source_code_analyser.languages.protocols import LanguageSupport
from waivern_source_code_analyser.languages.registry import LanguageRegistry


class TestPHPLanguageSupportProperties:
    """Tests for PHPLanguageSupport properties."""

    def test_name_returns_php(self) -> None:
        """Test that name property returns 'php'."""
        php = PHPLanguageSupport()

        assert php.name == "php"

    def test_file_extensions_returns_php_extensions(self) -> None:
        """Test that file_extensions returns all PHP extensions."""
        php = PHPLanguageSupport()

        extensions = php.file_extensions

        # Should include common PHP extensions
        assert ".php" in extensions
        assert ".php3" in extensions
        assert ".php4" in extensions
        assert ".php5" in extensions
        assert ".phtml" in extensions


class TestPHPLanguageSupportProtocol:
    """Tests for protocol conformance."""

    def test_implements_language_support_protocol(self) -> None:
        """Test that PHPLanguageSupport satisfies the LanguageSupport protocol."""
        php = PHPLanguageSupport()

        # Should pass isinstance check due to @runtime_checkable
        assert isinstance(php, LanguageSupport)

    def test_registered_via_entry_point(self) -> None:
        """Test that PHPLanguageSupport is discoverable via entry points."""
        # Save and restore state to avoid test pollution
        original_state = LanguageRegistry.snapshot_state()

        try:
            registry = LanguageRegistry()
            registry.clear()
            registry.discover()

            # PHP should be registered after discovery
            assert registry.is_registered("php")

            # Should be able to retrieve it
            php = registry.get("php")
            assert php.name == "php"

        finally:
            LanguageRegistry.restore_state(original_state)
