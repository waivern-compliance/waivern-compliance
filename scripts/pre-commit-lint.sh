#!/bin/bash

# Pre-commit wrapper for linting
# Groups files by package and runs each package's lint script
# Usage: Called by pre-commit with list of changed files

set -e

# Group files by package
wct_files=()
core_files=()
llm_files=()

for file in "$@"; do
    if [[ "$file" == apps/wct/* ]]; then
        # Remove package prefix to get relative path within package
        wct_files+=("${file#apps/wct/}")
    elif [[ "$file" == libs/waivern-core/* ]]; then
        core_files+=("${file#libs/waivern-core/}")
    elif [[ "$file" == libs/waivern-llm/* ]]; then
        llm_files+=("${file#libs/waivern-llm/}")
    fi
done

# Lint each package's files using its own script
if [ ${#wct_files[@]} -gt 0 ]; then
    (cd apps/wct && ./scripts/lint.sh "${wct_files[@]}")
fi

if [ ${#core_files[@]} -gt 0 ]; then
    (cd libs/waivern-core && ./scripts/lint.sh "${core_files[@]}")
fi

if [ ${#llm_files[@]} -gt 0 ]; then
    (cd libs/waivern-llm && ./scripts/lint.sh "${llm_files[@]}")
fi
