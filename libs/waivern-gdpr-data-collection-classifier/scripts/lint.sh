#!/bin/bash

# Run code linting checks for waivern-gdpr-data-collection-classifier package
# Usage: bash scripts/lint.sh [--fix]
# Checks code for style and quality issues using Ruff

uv run --group dev ruff check "$@"
