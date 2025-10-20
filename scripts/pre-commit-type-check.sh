#!/bin/bash

# Pre-commit wrapper for type checking
# Groups files by package and runs each package's type-check script
# Usage: Called by pre-commit with list of changed files

set -e

# Group files by package
wct_files=()
core_files=()
llm_files=()
connectors_database_files=()
mysql_files=()
community_files=()

for file in "$@"; do
    if [[ "$file" == apps/wct/* ]]; then
        # Remove package prefix to get relative path within package
        wct_files+=("${file#apps/wct/}")
    elif [[ "$file" == libs/waivern-core/* ]]; then
        core_files+=("${file#libs/waivern-core/}")
    elif [[ "$file" == libs/waivern-llm/* ]]; then
        llm_files+=("${file#libs/waivern-llm/}")
    elif [[ "$file" == libs/waivern-connectors-database/* ]]; then
        connectors_database_files+=("${file#libs/waivern-connectors-database/}")
    elif [[ "$file" == libs/waivern-mysql/* ]]; then
        mysql_files+=("${file#libs/waivern-mysql/}")
    elif [[ "$file" == libs/waivern-community/* ]]; then
        community_files+=("${file#libs/waivern-community/}")
    fi
done

# Type check each package's files using its own script (in dependency order)
if [ ${#core_files[@]} -gt 0 ]; then
    (cd libs/waivern-core && ./scripts/type-check.sh "${core_files[@]}")
fi

if [ ${#llm_files[@]} -gt 0 ]; then
    (cd libs/waivern-llm && ./scripts/type-check.sh "${llm_files[@]}")
fi

if [ ${#connectors_database_files[@]} -gt 0 ]; then
    (cd libs/waivern-connectors-database && ./scripts/type-check.sh "${connectors_database_files[@]}")
fi

if [ ${#mysql_files[@]} -gt 0 ]; then
    (cd libs/waivern-mysql && ./scripts/type-check.sh "${mysql_files[@]}")
fi

if [ ${#community_files[@]} -gt 0 ]; then
    (cd libs/waivern-community && ./scripts/type-check.sh "${community_files[@]}")
fi

if [ ${#wct_files[@]} -gt 0 ]; then
    (cd apps/wct && ./scripts/type-check.sh "${wct_files[@]}")
fi
