#!/bin/bash

# Run code linting checks
# Usage: bash scripts/lint.sh [--fix] [files/directories]
# Checks code for style and quality issues using Ruff

uv run --group dev \
	ruff check "$@"
