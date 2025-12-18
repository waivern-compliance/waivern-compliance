#!/bin/bash

# Run type checking for waivern-mongodb package
# Usage: bash scripts/type-check.sh
# Checks code for type errors using basedpyright

uv run --group dev basedpyright
