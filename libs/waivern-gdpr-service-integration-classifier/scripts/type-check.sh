#!/bin/bash

# Run type checking for waivern-gdpr-service-integration-classifier package
# Usage: bash scripts/type-check.sh
# Checks types using basedpyright

uv run --group dev basedpyright src/
