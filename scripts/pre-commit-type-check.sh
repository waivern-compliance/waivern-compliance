#!/bin/bash

# Pre-commit wrapper for type checking
# Auto-discovers packages and groups files by package
# Usage: Called by pre-commit with list of changed files
# Compatible with bash 3.2+ (no associative arrays)

set -e

# Auto-discover all packages
packages=()

for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/type-check.sh" ]; then
        packages+=("$dir")
    fi
done

# Run type checking for each package with its changed files
for package in "${packages[@]}"; do
    # Collect files that belong to this package
    package_files=()
    for file in "$@"; do
        if [[ "$file" == "$package"/* ]]; then
            # Remove package prefix to get relative path within package
            relative_file="${file#$package/}"
            package_files+=("$relative_file")
        fi
    done

    # Run type-check script if this package has changed files
    if [ ${#package_files[@]} -gt 0 ]; then
        (cd "$package" && ./scripts/type-check.sh "${package_files[@]}")
    fi
done
