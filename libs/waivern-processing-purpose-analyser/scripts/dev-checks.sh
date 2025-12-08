#!/bin/bash

# Run all development checks for waivern-processing-purpose-analyser package
# Usage: bash scripts/dev-checks.sh
# Runs format, lint, type-check, and tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Formatting..."
./scripts/format.sh

echo "Linting..."
./scripts/lint.sh

echo "Type checking..."
./scripts/type-check.sh

echo "Running tests..."
uv run pytest tests/ -v

echo "All checks passed!"
