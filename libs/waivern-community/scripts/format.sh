#!/bin/bash

# Run code formatting for waivern-community package
# Usage: bash scripts/format.sh [file1 file2 ...]
# Formats code using Ruff's formatter

uv run --group dev ruff format "$@"
