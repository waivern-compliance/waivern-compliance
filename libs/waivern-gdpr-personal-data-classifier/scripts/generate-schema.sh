#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_personal_data
# Usage: bash scripts/generate-schema.sh

echo "Generating gdpr_personal_data JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_personal_data_classifier.schemas import GDPRPersonalDataFindingOutput

output_path = Path('src/waivern_gdpr_personal_data_classifier/schemas/json_schemas/gdpr_personal_data/1.0.0/gdpr_personal_data.json')
GDPRPersonalDataFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
