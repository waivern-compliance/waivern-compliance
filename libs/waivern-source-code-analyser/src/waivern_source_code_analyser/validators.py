"""Shared validation utilities for source code components."""


def validate_and_normalise_language(v: str | None) -> str | None:
    """Validate and normalise language string.

    This function ensures language strings are non-empty and normalises
    them to lowercase for consistent comparison.

    Args:
        v: Language string to validate (or None for auto-detection)

    Returns:
        Normalised lowercase language string with whitespace stripped,
        or None if input was None

    Raises:
        ValueError: If language is empty string or whitespace-only

    Example:
        >>> validate_and_normalise_language("PHP")
        'php'
        >>> validate_and_normalise_language("  python  ")
        'python'
        >>> validate_and_normalise_language(None)
        None
        >>> validate_and_normalise_language("")
        Traceback (most recent call last):
            ...
        ValueError: Language must be a non-empty string if provided

    """
    if v is not None:
        if not v.strip():
            raise ValueError("Language must be a non-empty string if provided")
        return v.strip().lower()
    return v
