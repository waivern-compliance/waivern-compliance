#!/bin/bash

# Generate JSON schema from Pydantic model for data_subject_finding
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating data_subject_finding JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_data_subject_analyser.schemas import DataSubjectFindingOutput

output_path = Path('src/waivern_data_subject_analyser/schemas/json_schemas/data_subject_finding/1.0.0/data_subject_finding.json')
DataSubjectFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
