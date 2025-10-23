#!/bin/bash

# Format code using Ruff formatter
# Usage: bash scripts/format.sh [files/directories]
# Auto-discovers and formats all packages in parallel

set -e

# Auto-discover all packages with pyproject.toml
packages=()
for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/format.sh" ]; then
        packages+=("$dir")
    fi
done

# Run formatting in parallel for all packages
pids=()
failed_packages=()

for package in "${packages[@]}"; do
    (cd "$package" && ./scripts/format.sh "$@") &
    pids+=($!)
done

# Wait for all packages to complete and collect failures
for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
        failed_packages+=("${packages[$i]}")
    fi
done

# Report failures if any
if [ ${#failed_packages[@]} -gt 0 ]; then
    echo "Formatting failed in: ${failed_packages[*]}"
    exit 1
fi
