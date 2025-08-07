#!/bin/bash

# CI quality checks script
# This script runs the essential code quality checks for CI/CD pipeline
# Uses the same individual scripts as pre-commit hooks for consistency

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running CI code quality checks..."

echo "📝 Formatting check..."
"$SCRIPT_DIR/format.sh" --check

echo "🔍 Linting..."
"$SCRIPT_DIR/lint.sh"

echo "🔧 Type checking..."
"$SCRIPT_DIR/type-check.sh"

echo "✅ All CI checks passed!"
