#!/bin/bash

# Pre-commit wrapper for linting
# Auto-discovers packages and groups files by package
# Usage: Called by pre-commit with list of changed files

set -e

# Auto-discover all packages
declare -A package_files
packages=()

for dir in libs/* apps/*; do
    if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ] && [ -f "$dir/scripts/lint.sh" ]; then
        packages+=("$dir")
        package_files["$dir"]=""
    fi
done

# Group changed files by package
for file in "$@"; do
    for package in "${packages[@]}"; do
        if [[ "$file" == "$package"/* ]]; then
            # Remove package prefix to get relative path within package
            relative_file="${file#$package/}"
            if [ -z "${package_files[$package]}" ]; then
                package_files["$package"]="$relative_file"
            else
                package_files["$package"]+=" $relative_file"
            fi
            break
        fi
    done
done

# Run linting for packages with changed files
for package in "${packages[@]}"; do
    if [ -n "${package_files[$package]}" ]; then
        # Convert space-separated string back to array for proper quoting
        read -ra files <<< "${package_files[$package]}"
        (cd "$package" && ./scripts/lint.sh "${files[@]}")
    fi
done
