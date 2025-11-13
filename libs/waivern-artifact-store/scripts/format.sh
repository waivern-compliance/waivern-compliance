#!/bin/bash

# Format code for waivern-llm package
# Usage: bash scripts/format.sh [files/directories]
# Applies automatic code formatting using Ruff

uv run --group dev ruff format "$@"
