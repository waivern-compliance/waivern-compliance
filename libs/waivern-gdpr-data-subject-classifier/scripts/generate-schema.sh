#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_data_subject
# Usage: bash scripts/generate-schema.sh

echo "Generating gdpr_data_subject JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingOutput

output_path = Path('src/waivern_gdpr_data_subject_classifier/schemas/json_schemas/gdpr_data_subject/1.0.0/gdpr_data_subject.json')
GDPRDataSubjectFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
