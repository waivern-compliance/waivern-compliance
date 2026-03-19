#!/bin/bash

# Generate JSON schema from Pydantic model for gdpr_service_integration
# Usage: bash scripts/generate-schema.sh

echo "Generating gdpr_service_integration JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_gdpr_service_integration_classifier.schemas import GDPRServiceIntegrationFindingOutput

output_path = Path('src/waivern_gdpr_service_integration_classifier/schemas/json_schemas/gdpr_service_integration/1.0.0/gdpr_service_integration.json')
GDPRServiceIntegrationFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
