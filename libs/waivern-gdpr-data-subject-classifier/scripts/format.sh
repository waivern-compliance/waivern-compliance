#!/bin/bash

# Format code for waivern-gdpr-data-subject-classifier package
# Usage: bash scripts/format.sh [files/directories]
# Applies automatic code formatting using Ruff

uv run --group dev ruff format "$@"
