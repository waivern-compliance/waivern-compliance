#!/bin/bash

# Run all pre-commit hooks manually
# Usage: bash scripts/precommit.sh [files/directories]
# Executes pre-commit checks on specified files or all files with diff output on failures

if [ $# -eq 0 ]; then
    # No files passed, run on all files
    uv run --group dev \
        pre-commit run \
        --all-files \
        --show-diff-on-failure
else
    # Files passed, run on specific files
    uv run --group dev \
        pre-commit run \
        --files "$@" \
        --show-diff-on-failure
fi
