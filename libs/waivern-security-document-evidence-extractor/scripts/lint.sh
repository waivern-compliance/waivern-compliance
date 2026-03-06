#!/bin/bash

# Run code linting checks for waivern-security-document-evidence-extractor package
# Usage: bash scripts/lint.sh [--fix]
# Checks code for style and quality issues using Ruff

uv run --group dev ruff check "$@"
