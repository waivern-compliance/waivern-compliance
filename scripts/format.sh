#!/bin/bash

# Format code using Ruff formatter
# Usage: bash scripts/format.sh [files/directories]
# Applies automatic code formatting to specified files or entire project

uv run --group dev \
	ruff format "$@"
