#!/bin/bash

# Lightweight development quality checks with auto-fix
# Same as dev-checks.sh but skips slow tests (subprocess-based CLI tests)
# Use this for fast iteration; run full dev-checks.sh before submitting PRs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Format code (auto-fix)
echo "Formatting code..."
"$SCRIPT_DIR/format.sh"

# Lint with auto-fix
echo "Linting..."
"$SCRIPT_DIR/lint.sh" --fix

# Type check
echo "Type checking..."
"$SCRIPT_DIR/type-check.sh"

# Basic file checks with auto-fix
echo "File quality checks..."
uv run --group dev pre-commit run check-yaml --all-files
uv run --group dev pre-commit run check-toml --all-files
uv run --group dev pre-commit run check-json --all-files
uv run --group dev pre-commit run end-of-file-fixer --all-files
uv run --group dev pre-commit run trailing-whitespace --all-files

# Run tests (excluding slow subprocess-based CLI tests)
echo "Running tests (skipping slow)..."
"$SCRIPT_DIR/test.sh" -m "not integration and not batch and not slow"
