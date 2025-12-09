#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_ROOT="$(cd "$PACKAGE_DIR/../.." && pwd)"

cd "$PACKAGE_DIR"

echo "Formatting..."
./scripts/format.sh

echo "Linting..."
./scripts/lint.sh --fix

echo "Type checking..."
./scripts/type-check.sh

echo "Running tests..."
cd "$WORKSPACE_ROOT"
uv run pytest apps/wct/tests -v

echo "All checks passed!"
