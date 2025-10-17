#!/bin/bash

# Run type checking for waivern-community package
# Usage: bash scripts/type-check.sh [PATH]
# Checks types using basedpyright with strict mode
# Defaults to checking src directory (excluding tests)

uv run --group dev basedpyright --level error "${@:-src}"
