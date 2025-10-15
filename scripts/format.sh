#!/bin/bash

# Format code using Ruff formatter
# Usage: bash scripts/format.sh [files/directories]
# Orchestrates formatting across all packages using their own scripts

set -e

# Format each package using its own scripts
(cd apps/wct && ./scripts/format.sh "$@")
(cd libs/waivern-core && ./scripts/format.sh "$@")
