"""Tests for child runbook path resolution."""

from pathlib import Path

import pytest

from waivern_orchestration.errors import ChildRunbookNotFoundError, InvalidPathError
from waivern_orchestration.path_resolver import resolve_child_runbook_path


class TestPathResolutionRelative:
    """Tests for relative path resolution."""

    def test_resolve_path_relative_to_parent(self, tmp_path: Path) -> None:
        """Child runbook path resolved relative to parent runbook directory."""
        # Create parent runbook and child runbook files
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()
        child_runbook = parent_dir / "child.yaml"
        child_runbook.touch()

        # Resolve child path relative to parent
        result = resolve_child_runbook_path(
            path="./child.yaml",
            parent_runbook_path=parent_runbook,
        )

        assert result == child_runbook
        assert result.is_absolute()

    def test_resolve_path_in_subdirectory(self, tmp_path: Path) -> None:
        """Child runbook in subdirectory of parent is resolved correctly."""
        # Create parent runbook and child in subdirectory
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()

        child_dir = parent_dir / "children"
        child_dir.mkdir()
        child_runbook = child_dir / "child.yaml"
        child_runbook.touch()

        # Resolve child path in subdirectory
        result = resolve_child_runbook_path(
            path="./children/child.yaml",
            parent_runbook_path=parent_runbook,
        )

        assert result == child_runbook


class TestPathResolutionTemplatePaths:
    """Tests for template path fallback resolution."""

    def test_resolve_path_from_template_paths(self, tmp_path: Path) -> None:
        """Child runbook found in template_paths when not in parent directory."""
        # Create parent directory (without child)
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()

        # Create template directory with child runbook
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        child_runbook = template_dir / "shared_child.yaml"
        child_runbook.touch()

        # Resolve from template_paths
        result = resolve_child_runbook_path(
            path="shared_child.yaml",
            parent_runbook_path=parent_runbook,
            template_paths=[str(template_dir)],
        )

        assert result == child_runbook

    def test_resolve_path_parent_takes_precedence(self, tmp_path: Path) -> None:
        """Parent directory is searched before template_paths."""
        # Create parent directory with child
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()
        parent_child = parent_dir / "child.yaml"
        parent_child.write_text("parent version")

        # Create template directory with same-named child
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_child = template_dir / "child.yaml"
        template_child.write_text("template version")

        # Should resolve to parent directory version
        result = resolve_child_runbook_path(
            path="child.yaml",
            parent_runbook_path=parent_runbook,
            template_paths=[str(template_dir)],
        )

        assert result == parent_child
        assert result.read_text() == "parent version"

    def test_resolve_path_empty_template_paths(self, tmp_path: Path) -> None:
        """Path resolution works with no template paths configured."""
        # Create parent runbook and child
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()
        child_runbook = parent_dir / "child.yaml"
        child_runbook.touch()

        # Resolve without template_paths
        result = resolve_child_runbook_path(
            path="child.yaml",
            parent_runbook_path=parent_runbook,
            template_paths=[],
        )

        assert result == child_runbook

    def test_resolve_path_multiple_template_paths_order(self, tmp_path: Path) -> None:
        """Template paths are searched in order, first match wins."""
        # Create parent directory (without child)
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()

        # Create two template directories with same-named child
        template_dir_1 = tmp_path / "templates_1"
        template_dir_1.mkdir()
        child_1 = template_dir_1 / "child.yaml"
        child_1.write_text("template 1 version")

        template_dir_2 = tmp_path / "templates_2"
        template_dir_2.mkdir()
        child_2 = template_dir_2 / "child.yaml"
        child_2.write_text("template 2 version")

        # Should resolve to first template directory
        result = resolve_child_runbook_path(
            path="child.yaml",
            parent_runbook_path=parent_runbook,
            template_paths=[str(template_dir_1), str(template_dir_2)],
        )

        assert result == child_1
        assert result.read_text() == "template 1 version"


class TestPathResolutionSecurity:
    """Tests for path resolution security constraints."""

    def test_resolve_path_absolute_rejected(self, tmp_path: Path) -> None:
        """Absolute paths raise InvalidPathError."""
        parent_runbook = tmp_path / "parent.yaml"
        parent_runbook.touch()

        with pytest.raises(InvalidPathError) as exc_info:
            resolve_child_runbook_path(
                path="/etc/passwd",
                parent_runbook_path=parent_runbook,
            )

        assert "absolute" in str(exc_info.value).lower()

    def test_resolve_path_parent_traversal_rejected(self, tmp_path: Path) -> None:
        """Paths containing '..' raise InvalidPathError."""
        parent_runbook = tmp_path / "parent.yaml"
        parent_runbook.touch()

        with pytest.raises(InvalidPathError) as exc_info:
            resolve_child_runbook_path(
                path="../sibling/child.yaml",
                parent_runbook_path=parent_runbook,
            )

        assert ".." in str(exc_info.value)

    def test_resolve_path_hidden_parent_traversal_rejected(
        self, tmp_path: Path
    ) -> None:
        """Paths with embedded '..' are rejected even if normalised."""
        parent_runbook = tmp_path / "parent.yaml"
        parent_runbook.touch()

        with pytest.raises(InvalidPathError) as exc_info:
            resolve_child_runbook_path(
                path="./subdir/../../../etc/passwd",
                parent_runbook_path=parent_runbook,
            )

        assert ".." in str(exc_info.value)


class TestPathResolutionErrors:
    """Tests for path resolution error handling."""

    def test_resolve_path_not_found(self, tmp_path: Path) -> None:
        """Non-existent path raises ChildRunbookNotFoundError."""
        parent_runbook = tmp_path / "parent.yaml"
        parent_runbook.touch()

        with pytest.raises(ChildRunbookNotFoundError) as exc_info:
            resolve_child_runbook_path(
                path="nonexistent.yaml",
                parent_runbook_path=parent_runbook,
            )

        assert "nonexistent.yaml" in str(exc_info.value)

    def test_resolve_path_not_found_with_template_paths(self, tmp_path: Path) -> None:
        """ChildRunbookNotFoundError when not found in any location."""
        parent_dir = tmp_path / "runbooks"
        parent_dir.mkdir()
        parent_runbook = parent_dir / "parent.yaml"
        parent_runbook.touch()

        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        with pytest.raises(ChildRunbookNotFoundError) as exc_info:
            resolve_child_runbook_path(
                path="missing.yaml",
                parent_runbook_path=parent_runbook,
                template_paths=[str(template_dir)],
            )

        assert "missing.yaml" in str(exc_info.value)
