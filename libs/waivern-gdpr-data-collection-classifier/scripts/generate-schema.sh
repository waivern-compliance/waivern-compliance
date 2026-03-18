#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_data_collection
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating gdpr_data_collection JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_data_collection_classifier.schemas import GDPRDataCollectionFindingOutput

output_path = Path('src/waivern_gdpr_data_collection_classifier/schemas/json_schemas/gdpr_data_collection/1.0.0/gdpr_data_collection.json')
GDPRDataCollectionFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
