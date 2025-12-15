"""Shared utilities for waivern-orchestration."""

import uuid

from waivern_core.schemas import Schema

# =============================================================================
# Schema Utilities
# =============================================================================


def parse_schema_string(schema_str: str) -> Schema:
    """Parse a schema string into a Schema object.

    Supports formats:
    - "schema_name" (defaults to version 1.0.0)
    - "schema_name/1.0.0" (explicit version)

    Args:
        schema_str: Schema string from runbook (e.g., "standard_input/1.0.0").

    Returns:
        Schema object with name and version.

    Examples:
        >>> parse_schema_string("standard_input")
        Schema(name='standard_input', version='1.0.0')
        >>> parse_schema_string("finding/2.0.0")
        Schema(name='finding', version='2.0.0')

    """
    if "/" in schema_str:
        name, version = schema_str.rsplit("/", 1)
    else:
        name = schema_str
        version = "1.0.0"
    return Schema(name, version)


# =============================================================================
# Namespace Utilities
# =============================================================================

NAMESPACE_SEPARATOR = "__"
"""Separator used in namespaced artifact IDs.

Namespaced IDs follow the format: {runbook_name}__{uuid}__{artifact_id}
Example: my_child__abc12345__data
"""


def generate_namespace(runbook_name: str) -> str:
    """Generate a unique namespace for child runbook artifacts.

    The namespace combines a sanitised runbook name with a short UUID
    to ensure uniqueness across multiple invocations of the same child.

    Args:
        runbook_name: Name of the child runbook.

    Returns:
        Unique namespace string (e.g., "my_child__abc12345").

    """
    short_uuid = str(uuid.uuid4())[:8]
    # Clean runbook name for use in identifier
    clean_name = runbook_name.replace(" ", "_").replace("-", "_").lower()
    return f"{clean_name}{NAMESPACE_SEPARATOR}{short_uuid}"


def create_namespaced_id(namespace: str, artifact_id: str) -> str:
    """Create a namespaced artifact ID.

    Args:
        namespace: The namespace prefix (from generate_namespace).
        artifact_id: The original artifact ID.

    Returns:
        Namespaced artifact ID (e.g., "my_child__abc12345__data").

    """
    return f"{namespace}{NAMESPACE_SEPARATOR}{artifact_id}"


def parse_namespaced_id(artifact_id: str) -> tuple[str | None, str]:
    """Parse a namespaced artifact ID to extract origin information.

    Args:
        artifact_id: The artifact ID to parse.

    Returns:
        Tuple of (runbook_name, original_artifact_id).
        If not namespaced, returns (None, artifact_id).

    Examples:
        >>> parse_namespaced_id("my_child__abc12345__data")
        ('my_child', 'data')
        >>> parse_namespaced_id("regular_artifact")
        (None, 'regular_artifact')

    """
    if NAMESPACE_SEPARATOR not in artifact_id:
        return None, artifact_id

    parts = artifact_id.split(NAMESPACE_SEPARATOR)
    # Format is: {runbook_name}__{uuid}__{artifact_id}
    # So parts[0] is runbook_name, parts[-1] is artifact_id
    return parts[0], parts[-1]


def is_namespaced(artifact_id: str) -> bool:
    """Check if an artifact ID is namespaced (from a child runbook).

    Args:
        artifact_id: The artifact ID to check.

    Returns:
        True if the ID contains the namespace separator.

    """
    return NAMESPACE_SEPARATOR in artifact_id


def get_origin_from_artifact_id(artifact_id: str) -> str:
    """Determine the origin string for an artifact based on its ID.

    Args:
        artifact_id: The artifact ID to check.

    Returns:
        'parent' for regular artifacts, 'child:{runbook_name}' for namespaced.

    """
    runbook_name, _ = parse_namespaced_id(artifact_id)
    if runbook_name is not None:
        return f"child:{runbook_name}"
    return "parent"
