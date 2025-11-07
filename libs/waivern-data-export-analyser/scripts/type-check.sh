#!/bin/bash

# Run static type checking for waivern-personal-data-analyser package
# Usage: bash scripts/type-check.sh [files...]
# Performs type checking using basedpyright with package configuration

# If specific files are provided, check those
# Otherwise check everything in the package directory
if [ $# -gt 0 ]; then
    uv run --group dev basedpyright "$@"
else
    uv run --group dev basedpyright .
fi
