"""Tests for child runbook path resolution."""


class TestPathResolutionRelative:
    """Tests for relative path resolution."""

    def test_resolve_path_relative_to_parent(self) -> None:
        """Child runbook path resolved relative to parent runbook directory."""
        pass

    def test_resolve_path_in_subdirectory(self) -> None:
        """Child runbook in subdirectory of parent is resolved correctly."""
        pass


class TestPathResolutionTemplatePaths:
    """Tests for template path fallback resolution."""

    def test_resolve_path_from_template_paths(self) -> None:
        """Child runbook found in template_paths when not in parent directory."""
        pass

    def test_resolve_path_parent_takes_precedence(self) -> None:
        """Parent directory is searched before template_paths."""
        pass

    def test_resolve_path_empty_template_paths(self) -> None:
        """Path resolution works with no template paths configured."""
        pass


class TestPathResolutionSecurity:
    """Tests for path resolution security constraints."""

    def test_resolve_path_absolute_rejected(self) -> None:
        """Absolute paths raise InvalidPathError."""
        pass

    def test_resolve_path_parent_traversal_rejected(self) -> None:
        """Paths containing '..' raise InvalidPathError."""
        pass


class TestPathResolutionErrors:
    """Tests for path resolution error handling."""

    def test_resolve_path_not_found(self) -> None:
        """Non-existent path raises ChildRunbookNotFoundError."""
        pass
