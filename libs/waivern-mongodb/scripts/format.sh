#!/bin/bash

# Run code formatting for waivern-mongodb package
# Usage: bash scripts/format.sh [files...]
# Formats code using Ruff

uv run --group dev ruff format "$@"
