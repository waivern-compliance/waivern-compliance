"""Tests for language support protocols."""

from unittest.mock import MagicMock

from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.models import LanguageExtractionResult
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

            def get_tree_sitter_language(self) -> Language:
                return MagicMock(spec=Language)

            def extract(
                self, root_node: Node, source_code: str
            ) -> LanguageExtractionResult:
                return LanguageExtractionResult()

        valid = ValidLanguage()
        assert isinstance(valid, LanguageSupport)

    def test_incomplete_implementation_fails_check(self) -> None:
        """Test that a class missing required methods fails the protocol check."""

        class IncompleteLanguage:
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing: file_extensions, get_tree_sitter_language, extract

        incomplete = IncompleteLanguage()
        assert not isinstance(incomplete, LanguageSupport)
