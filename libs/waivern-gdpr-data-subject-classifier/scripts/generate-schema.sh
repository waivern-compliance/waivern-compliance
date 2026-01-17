#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_data_subject
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating gdpr_data_subject JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingOutput

output_path = Path('src/waivern_gdpr_data_subject_classifier/schemas/json_schemas/gdpr_data_subject/1.0.0/gdpr_data_subject.json')
GDPRDataSubjectFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
