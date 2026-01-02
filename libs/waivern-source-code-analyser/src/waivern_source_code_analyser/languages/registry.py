"""Language registry for source code analysis.

Provides singleton registry with entry point discovery for language plugins.
"""

from importlib.metadata import entry_points
from typing import Any, TypedDict

from waivern_source_code_analyser.languages.protocols import LanguageSupport


class LanguageNotFoundError(Exception):
    """Raised when a requested language is not registered."""

    pass


class LanguageAlreadyRegisteredError(Exception):
    """Raised when attempting to register a language that already exists."""

    pass


class LanguageRegistryState(TypedDict):
    """State snapshot for LanguageRegistry (used for test isolation)."""

    registry: dict[str, LanguageSupport]
    extension_map: dict[str, str]
    discovered: bool


class LanguageRegistry:
    """Singleton registry for language support plugins.

    Discovers language plugins via entry points and provides lookup
    by language name or file extension.
    """

    _instance: "LanguageRegistry | None" = None
    _registry: dict[str, LanguageSupport]
    _extension_map: dict[str, str]  # ".ts" → "typescript"
    _discovered: bool

    def __new__(cls, *args: Any, **kwargs: Any) -> "LanguageRegistry":  # noqa: ANN401
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
            cls._instance._extension_map = {}
            cls._instance._discovered = False
        return cls._instance

    def discover(self) -> None:
        """Discover and register language plugins from entry points.

        Entry point group: waivern.source_code_languages

        Languages are validated by calling get_tree_sitter_language() to ensure
        the tree-sitter binding is actually installed. Languages with missing
        bindings are silently skipped.
        """
        if self._discovered:
            return

        eps = entry_points(group="waivern.source_code_languages")
        for ep in eps:
            try:
                language_class = ep.load()
                language = language_class()
                # Validate the tree-sitter binding is available
                # This triggers the deferred import in get_tree_sitter_language()
                language.get_tree_sitter_language()
                self.register(language)
            except ImportError:
                # Language's tree-sitter binding not installed - skip
                pass

        self._discovered = True

    def register(self, language: LanguageSupport) -> None:
        """Register a language support instance.

        Args:
            language: LanguageSupport implementation

        Raises:
            LanguageAlreadyRegisteredError: If language already registered

        """
        if language.name in self._registry:
            raise LanguageAlreadyRegisteredError(
                f"Language '{language.name}' is already registered"
            )

        self._registry[language.name] = language
        for ext in language.file_extensions:
            self._extension_map[ext] = language.name

    def get(self, name: str) -> LanguageSupport:
        """Get a language by name.

        Args:
            name: Canonical language name (e.g., 'php', 'typescript')

        Returns:
            LanguageSupport implementation

        Raises:
            LanguageNotFoundError: If language not registered

        """
        if name not in self._registry:
            raise LanguageNotFoundError(f"Language '{name}' not registered")
        return self._registry[name]

    def get_by_extension(self, extension: str) -> LanguageSupport:
        """Get a language by file extension.

        Args:
            extension: File extension including dot (e.g., '.ts', '.php')

        Returns:
            LanguageSupport implementation

        Raises:
            LanguageNotFoundError: If no language supports the extension

        """
        if extension not in self._extension_map:
            raise LanguageNotFoundError(
                f"No language registered for extension '{extension}'"
            )
        return self._registry[self._extension_map[extension]]

    def list_languages(self) -> list[str]:
        """List all registered language names."""
        return list(self._registry.keys())

    def list_extensions(self) -> list[str]:
        """List all supported file extensions."""
        return list(self._extension_map.keys())

    def is_registered(self, name: str) -> bool:
        """Check if a language is registered."""
        return name in self._registry

    def clear(self) -> None:
        """Clear all registered languages (for testing)."""
        self._registry.clear()
        self._extension_map.clear()
        self._discovered = False

    @classmethod
    def snapshot_state(cls) -> LanguageRegistryState:
        """Capture current state for later restoration (test isolation)."""
        instance = cls()
        return {
            "registry": instance._registry.copy(),
            "extension_map": instance._extension_map.copy(),
            "discovered": instance._discovered,
        }

    @classmethod
    def restore_state(cls, state: LanguageRegistryState) -> None:
        """Restore state from a previously captured snapshot."""
        instance = cls()
        instance._registry = state["registry"].copy()
        instance._extension_map = state["extension_map"].copy()
        instance._discovered = state["discovered"]
