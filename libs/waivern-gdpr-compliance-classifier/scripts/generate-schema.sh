#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_compliance_classification
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating gdpr_compliance_classification JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_compliance_classifier.schemas import GDPRComplianceClassificationOutput

output_path = Path('src/waivern_gdpr_compliance_classifier/schemas/json_schemas/gdpr_compliance_classification/1.0.0/gdpr_compliance_classification.json')
GDPRComplianceClassificationOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
