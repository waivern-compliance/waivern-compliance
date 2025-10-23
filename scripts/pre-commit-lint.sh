#!/bin/bash

# Pre-commit wrapper for linting
# Auto-discovers packages and groups files by package
# Usage: Called by pre-commit with list of changed files
# Compatible with bash 3.2+ (no associative arrays)

set -e

# Auto-discover all packages
packages=()

for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/lint.sh" ]; then
        packages+=("$dir")
    fi
done

# Run linting for each package with its changed files
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

    # Run lint script if this package has changed files
    if [ ${#package_files[@]} -gt 0 ]; then
        (cd "$package" && ./scripts/lint.sh "${package_files[@]}")
    fi
done
