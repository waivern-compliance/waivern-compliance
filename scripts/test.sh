#!/bin/bash

# Run project tests
# Usage: bash scripts/test.sh [pytest-options] [files/directories]
# Executes pytest with optional additional arguments

uv run --group dev \
	pytest "$@"