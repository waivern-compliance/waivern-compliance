#!/bin/bash

# Run static type checking
# Usage: bash scripts/type-check.sh
# Orchestrates type checking across all packages using their own scripts

set -e

# Type check each package using its own scripts (in dependency order)
(cd libs/waivern-core && ./scripts/type-check.sh)
(cd libs/waivern-llm && ./scripts/type-check.sh)
(cd libs/waivern-connectors-database && ./scripts/type-check.sh)
(cd libs/waivern-mysql && ./scripts/type-check.sh)
(cd libs/waivern-rulesets && ./scripts/type-check.sh)
(cd libs/waivern-analysers-shared && ./scripts/type-check.sh)
(cd libs/waivern-personal-data-analyser && ./scripts/type-check.sh)
(cd libs/waivern-community && ./scripts/type-check.sh)
(cd apps/wct && ./scripts/type-check.sh)
