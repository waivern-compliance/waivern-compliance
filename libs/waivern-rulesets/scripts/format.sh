#!/bin/bash

# Format code for waivern-rulesets package
# Usage: bash scripts/format.sh [files/directories]
# Applies automatic code formatting using Ruff

uv run --group dev ruff format "$@"
