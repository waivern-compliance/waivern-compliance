#!/bin/bash

# Run code formatting for waivern-security-control-analyser package
# Usage: bash scripts/format.sh [--check]
# Formats code using Ruff formatter

uv run --group dev ruff format "$@"
