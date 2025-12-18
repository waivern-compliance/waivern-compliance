#!/bin/bash

# Run code linting for waivern-mongodb package
# Usage: bash scripts/lint.sh [files...]
# Checks code for style and quality issues using Ruff

uv run --group dev ruff check "$@"
