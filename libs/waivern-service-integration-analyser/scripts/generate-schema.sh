#!/bin/bash

# Generate JSON schema from Pydantic model for service_integration_indicator
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating service_integration_indicator JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_service_integration_analyser.schemas import ServiceIntegrationIndicatorOutput

output_path = Path('src/waivern_service_integration_analyser/schemas/json_schemas/service_integration_indicator/1.0.0/service_integration_indicator.json')
ServiceIntegrationIndicatorOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
