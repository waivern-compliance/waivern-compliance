#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_personal_data
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating gdpr_personal_data JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_personal_data_classifier.schemas import GDPRPersonalDataFindingOutput

output_path = Path('src/waivern_gdpr_personal_data_classifier/schemas/json_schemas/gdpr_personal_data/1.0.0/gdpr_personal_data.json')
GDPRPersonalDataFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
