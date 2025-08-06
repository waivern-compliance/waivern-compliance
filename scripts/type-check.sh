#!/bin/bash

# Run static type checking
# Usage: bash scripts/type-check.sh [files/directories]
# Performs type checking using mypy on specified files or entire project

uv run --group dev \
	basedpyright \
	--level error \
	"$@"
