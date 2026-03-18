#!/bin/bash

# Run type checking for waivern-gdpr-processing-purpose-classifier package
# Usage: bash scripts/type-check.sh
# Checks types using basedpyright

uv run --group dev basedpyright src/
