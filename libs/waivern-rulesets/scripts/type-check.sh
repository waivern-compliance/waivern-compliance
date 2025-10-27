#!/bin/bash

# Run static type checking for waivern-rulesets package
# Usage: bash scripts/type-check.sh [files...]
# Performs type checking using basedpyright with package configuration

# If specific files are provided, check those
# Otherwise check src directory (excluding tests)
if [ $# -gt 0 ]; then
    uv run --group dev basedpyright "$@"
else
    uv run --group dev basedpyright src/
fi
