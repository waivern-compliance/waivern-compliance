#!/bin/bash

# Run all development checks for waivern-mysql package
# Usage: bash scripts/dev-checks.sh
# Runs format, lint, type-check, and tests

echo "Formatting..."
./scripts/format.sh

echo "Linting..."
./scripts/lint.sh

echo "Type checking..."
./scripts/type-check.sh

echo "Running tests..."
uv run pytest tests/ -v

echo "All checks passed!"
