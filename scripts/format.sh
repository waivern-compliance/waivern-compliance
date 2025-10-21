#!/bin/bash

# Format code using Ruff formatter
# Usage: bash scripts/format.sh [files/directories]
# Orchestrates formatting across all packages using their own scripts

set -e

# Format each package using its own scripts (in dependency order)
(cd libs/waivern-core && ./scripts/format.sh "$@")
(cd libs/waivern-llm && ./scripts/format.sh "$@")
(cd libs/waivern-connectors-database && ./scripts/format.sh "$@")
(cd libs/waivern-mysql && ./scripts/format.sh "$@")
(cd libs/waivern-rulesets && ./scripts/format.sh "$@")
(cd libs/waivern-analysers-shared && ./scripts/format.sh "$@")
(cd libs/waivern-community && ./scripts/format.sh "$@")
(cd apps/wct && ./scripts/format.sh "$@")
