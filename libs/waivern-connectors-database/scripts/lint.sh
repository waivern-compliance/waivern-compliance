#!/bin/bash

# Run code linting checks for waivern-connectors-database package
# Usage: bash scripts/lint.sh [--fix]
# Checks code for style and quality issues using Ruff

uv run --group dev ruff check "$@"
