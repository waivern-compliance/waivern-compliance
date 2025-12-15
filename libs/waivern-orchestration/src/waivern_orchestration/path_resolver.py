"""Path resolver for child runbook paths."""

from pathlib import Path

from waivern_orchestration.errors import ChildRunbookNotFoundError, InvalidPathError


def resolve_child_runbook_path(
    path: str,
    parent_runbook_path: Path,
    template_paths: list[str] | None = None,
) -> Path:
    """Resolve child runbook path to absolute path.

    Resolution order:
    1. Validate path security (no absolute, no '..')
    2. Search relative to parent runbook directory
    3. Search in template_paths (in order)

    Args:
        path: The relative path to the child runbook
        parent_runbook_path: Path to the parent runbook file
        template_paths: Optional list of directories to search

    Returns:
        Absolute path to the child runbook file

    Raises:
        InvalidPathError: If path is absolute or contains '..'
        ChildRunbookNotFoundError: If file not found in any location

    """
    if template_paths is None:
        template_paths = []

    # Security check: reject absolute paths
    if Path(path).is_absolute():
        raise InvalidPathError(f"Absolute path not allowed: {path}")

    # Security check: reject parent traversal
    # Check the raw string to catch any '..' regardless of normalisation
    if ".." in path:
        raise InvalidPathError(f"Parent directory traversal not allowed: {path}")

    # Build search locations: parent directory first, then template_paths
    parent_dir = parent_runbook_path.parent
    search_locations = [parent_dir, *[Path(tp) for tp in template_paths]]

    # Normalise path by removing leading "./" if present
    # "./child.yaml" and "child.yaml" should both resolve the same way
    normalised_path = path.lstrip("./") if path.startswith("./") else path

    for base_dir in search_locations:
        candidate = base_dir / normalised_path
        if candidate.exists():
            return candidate.resolve()

    # Not found in any location
    raise ChildRunbookNotFoundError(f"Child runbook not found: {path}")
