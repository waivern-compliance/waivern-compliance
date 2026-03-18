#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_processing_purpose
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating gdpr_processing_purpose JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_processing_purpose_classifier.schemas import GDPRProcessingPurposeFindingOutput

output_path = Path('src/waivern_gdpr_processing_purpose_classifier/schemas/json_schemas/gdpr_processing_purpose/1.0.0/gdpr_processing_purpose.json')
GDPRProcessingPurposeFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
