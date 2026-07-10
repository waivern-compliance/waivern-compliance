#!/bin/bash

# Format code for waivern-http package
# Usage: bash scripts/format.sh [files/directories]
# Applies automatic code formatting using Ruff

uv run --group dev ruff format "$@"
