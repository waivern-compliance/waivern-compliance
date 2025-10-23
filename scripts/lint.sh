#!/bin/bash

# Run code linting checks
# Usage: bash scripts/lint.sh [--fix]
# Auto-discovers and lints all packages in parallel

set -e

# Auto-discover all packages with pyproject.toml
packages=()
for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/lint.sh" ]; then
        packages+=("$dir")
    fi
done

# Run linting in parallel for all packages
pids=()
failed_packages=()

for package in "${packages[@]}"; do
    (cd "$package" && ./scripts/lint.sh "$@") &
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
    echo "Linting failed in: ${failed_packages[*]}"
    exit 1
fi
