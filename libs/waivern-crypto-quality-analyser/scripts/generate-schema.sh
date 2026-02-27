#!/bin/bash

# Generate JSON schema from Pydantic model for crypto_quality_indicator
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating crypto_quality_indicator JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_crypto_quality_analyser.schemas import CryptoQualityIndicatorOutput

output_path = Path('src/waivern_crypto_quality_analyser/schemas/json_schemas/crypto_quality_indicator/1.0.0/crypto_quality_indicator.json')
CryptoQualityIndicatorOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
