#!/bin/bash
set -e
cd "$(dirname "$0")/.."
uv run ruff format src/ tests/
