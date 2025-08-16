#!/bin/bash

# Development quality checks with auto-fix
# Runs all quality checks and tests with automatic fixing where possible

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Format code (auto-fix)
echo "Formatting code..."
"$SCRIPT_DIR/format.sh"

# Lint with auto-fix
echo "Linting..."
uv run --group dev ruff check --fix .

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

# Run tests
echo "Running tests..."
"$SCRIPT_DIR/test.sh"
