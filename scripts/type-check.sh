#!/bin/bash

# Run static type checking
# Usage: bash scripts/type-check.sh
# Auto-discovers and type checks all packages in parallel

set -e

# Auto-discover all packages with pyproject.toml
packages=()
for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/type-check.sh" ]; then
        packages+=("$dir")
    fi
done

# Run type checking in parallel for all packages
pids=()
failed_packages=()

for package in "${packages[@]}"; do
    (cd "$package" && ./scripts/type-check.sh) &
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
    echo "Type checking failed in: ${failed_packages[*]}"
    exit 1
fi
