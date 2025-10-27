#!/bin/bash

# Run code linting for waivern-mysql package
# Usage: bash scripts/lint.sh [files...]
# Checks code for style and quality issues using Ruff

uv run --group dev ruff check "$@"
