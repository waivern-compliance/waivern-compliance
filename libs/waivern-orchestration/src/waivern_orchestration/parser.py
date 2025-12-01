"""YAML parser for artifact-centric runbooks.

This module provides functions to parse runbook YAML files into validated
Pydantic models.
"""

import os
import re
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import ValidationError

from waivern_orchestration.errors import RunbookParseError
from waivern_orchestration.models import Runbook

# Pattern for environment variable substitution: ${VAR_NAME}
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def parse_runbook(path: Path) -> Runbook:
    """Parse a runbook from a YAML file with environment variable substitution.

    Reads the YAML file, substitutes ${VAR_NAME} patterns with values from
    os.environ, and validates the result into a Runbook model.

    Args:
        path: Path to the runbook YAML file.

    Returns:
        Validated Runbook model.

    Raises:
        RunbookParseError: If the file cannot be read, YAML is invalid,
            environment variables are missing, or validation fails.

    """
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise RunbookParseError(f"Runbook file not found: {path}") from e
    except yaml.YAMLError as e:
        raise RunbookParseError(f"Invalid YAML in {path}: {e}") from e
    except OSError as e:
        raise RunbookParseError(f"Cannot read runbook file {path}: {e}") from e

    # Substitute environment variables
    data = _substitute_env_vars(data, path)

    return parse_runbook_from_dict(data)


def _substitute_env_vars(value: Any, path: Path) -> Any:  # noqa: ANN401
    """Recursively substitute ${VAR_NAME} patterns with environment variable values.

    Args:
        value: The value to process (string, dict, list, or other).
        path: The runbook file path (for error messages).

    Returns:
        The value with all ${VAR_NAME} patterns substituted.

    Raises:
        RunbookParseError: If an environment variable is not defined.

    """
    if isinstance(value, str):
        return _substitute_string(value, path)
    if isinstance(value, dict):
        dict_value = cast(dict[str, Any], value)
        return {k: _substitute_env_vars(v, path) for k, v in dict_value.items()}
    if isinstance(value, list):
        list_value = cast(list[Any], value)
        return [_substitute_env_vars(item, path) for item in list_value]
    # Numbers, booleans, None - return unchanged
    return value


def _substitute_string(value: str, path: Path) -> str:
    """Substitute ${VAR_NAME} patterns in a string.

    Args:
        value: The string to process.
        path: The runbook file path (for error messages).

    Returns:
        The string with all ${VAR_NAME} patterns substituted.

    Raises:
        RunbookParseError: If an environment variable is not defined.

    """

    def replace_match(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise RunbookParseError(
                f"Environment variable '{var_name}' is not defined "
                f"(referenced in {path})"
            )
        return env_value

    return _ENV_VAR_PATTERN.sub(replace_match, value)


def parse_runbook_from_dict(data: dict[str, Any]) -> Runbook:
    """Parse a runbook directly from a dictionary.

    This function performs direct Pydantic validation WITHOUT environment
    variable substitution. Any ${VAR_NAME} strings in the dict will remain
    as literal strings.

    Use this for testing or when you have a pre-processed dict where
    environment variables have already been substituted (or are not needed).

    Args:
        data: Dictionary containing runbook configuration.

    Returns:
        Validated Runbook model.

    Raises:
        RunbookParseError: If the dict structure is invalid.

    """
    try:
        return Runbook.model_validate(data)
    except ValidationError as e:
        raise RunbookParseError(f"Invalid runbook structure: {e}") from e
