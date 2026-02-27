#!/bin/bash
set -e
cd "$(dirname "$0")/.."
uv run ruff check src/ tests/
