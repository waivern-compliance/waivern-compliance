#!/bin/bash

# Initialize project environment
# Usage: bash scripts/init.sh
# Installs all dependencies and sets up pre-commit hooks

# Install dependencies
uv sync --all-groups --all-extras

# Install pre-commit hooks
uv run --group dev \
	pre-commit install
