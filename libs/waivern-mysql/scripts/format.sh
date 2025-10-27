#!/bin/bash

# Run code formatting for waivern-mysql package
# Usage: bash scripts/format.sh [files...]
# Applies automatic code formatting using Ruff

uv run --group dev ruff format "$@"
