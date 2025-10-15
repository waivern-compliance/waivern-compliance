#!/bin/bash

# Initialise project environment
# Usage: bash scripts/init.sh
# Installs all dependencies and sets up pre-commit hooks

# Install dependencies (all packages, groups, and extras)
uv sync --all-packages --all-groups --all-extras

# Install pre-commit hooks
uv run --group dev \
	pre-commit install
