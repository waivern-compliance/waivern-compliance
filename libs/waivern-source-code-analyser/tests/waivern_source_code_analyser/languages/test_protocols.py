"""Tests for language support protocols."""

from waivern_source_code_analyser.languages.protocols import LanguageSupport


class TestLanguageSupportProtocol:
    """Tests for LanguageSupport protocol."""

    def test_language_support_is_runtime_checkable(self) -> None:
        """Test that LanguageSupport protocol supports isinstance checks."""
        # If not @runtime_checkable, this would raise TypeError
        result = isinstance(object(), LanguageSupport)
        assert result is False

    def test_valid_implementation_passes_check(self) -> None:
        """Test that a class implementing all methods satisfies the protocol."""

        class ValidLanguage:
            @property
            def name(self) -> str:
                return "test"

            @property
            def file_extensions(self) -> list[str]:
                return [".test"]

        valid = ValidLanguage()
        assert isinstance(valid, LanguageSupport)

    def test_incomplete_implementation_fails_check(self) -> None:
        """Test that a class missing required methods fails the protocol check."""

        class IncompleteLanguage:
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing: file_extensions

        incomplete = IncompleteLanguage()
        assert not isinstance(incomplete, LanguageSupport)
