#!/bin/bash

# Run code linting checks
# Usage: bash scripts/lint.sh [--fix]
# Orchestrates linting across all packages using their own scripts

set -e

# Lint each package using its own scripts
(cd apps/wct && ./scripts/lint.sh "$@")
(cd libs/waivern-core && ./scripts/lint.sh "$@")
(cd libs/waivern-llm && ./scripts/lint.sh "$@")
(cd libs/waivern-community && ./scripts/lint.sh "$@")
