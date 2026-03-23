#!/usr/bin/env bash
# Generate all JSON schemas from Pydantic Output models.
#
# Usage:
#   bash libs/waivern-schemas/scripts/generate-schemas.sh
#
# Each Output model generates a JSON schema file at:
#   json_schemas/{schema_name}/{version}/{schema_name}.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/../src/waivern_schemas"
JSON_SCHEMAS_DIR="$PACKAGE_DIR/json_schemas"

echo "Generating JSON schemas into $JSON_SCHEMAS_DIR ..."

uv run python -c "
from pathlib import Path

json_schemas_dir = Path('$JSON_SCHEMAS_DIR')

# Each tuple: (import_path, class_name, schema_name)
schemas = [
    ('waivern_schemas.personal_data_indicator.v1', 'PersonalDataIndicatorOutput', 'personal_data_indicator'),
    ('waivern_schemas.processing_purpose_indicator.v1', 'ProcessingPurposeIndicatorOutput', 'processing_purpose_indicator'),
    ('waivern_schemas.data_subject_indicator.v1', 'DataSubjectIndicatorOutput', 'data_subject_indicator'),
    ('waivern_schemas.data_collection_indicator.v1', 'DataCollectionIndicatorOutput', 'data_collection_indicator'),
    ('waivern_schemas.service_integration_indicator.v1', 'ServiceIntegrationIndicatorOutput', 'service_integration_indicator'),
    ('waivern_schemas.crypto_quality_indicator.v1', 'CryptoQualityIndicatorOutput', 'crypto_quality_indicator'),
    ('waivern_schemas.source_code.v1', 'SourceCodeDataModel', 'source_code'),
    ('waivern_schemas.gdpr_personal_data.v1', 'GDPRPersonalDataFindingOutput', 'gdpr_personal_data'),
    ('waivern_schemas.gdpr_processing_purpose.v1', 'GDPRProcessingPurposeFindingOutput', 'gdpr_processing_purpose'),
    ('waivern_schemas.gdpr_data_subject.v1', 'GDPRDataSubjectFindingOutput', 'gdpr_data_subject'),
    ('waivern_schemas.gdpr_data_collection.v1', 'GDPRDataCollectionFindingOutput', 'gdpr_data_collection'),
    ('waivern_schemas.gdpr_service_integration.v1', 'GDPRServiceIntegrationFindingOutput', 'gdpr_service_integration'),
    ('waivern_schemas.security_evidence.v1', 'SecurityEvidenceOutput', 'security_evidence'),
    ('waivern_schemas.security_document_context.v1', 'SecurityDocumentContextOutput', 'security_document_context'),
    ('waivern_schemas.iso27001_assessment.v1', 'ISO27001AssessmentOutput', 'iso27001_assessment'),
]

import importlib

for module_path, class_name, schema_name in schemas:
    module = importlib.import_module(module_path)
    output_cls = getattr(module, class_name)
    version = output_cls.__schema_version__
    output_path = json_schemas_dir / schema_name / version / f'{schema_name}.json'
    output_cls.generate_json_schema(output_path)
    print(f'  {schema_name}/{version}/{schema_name}.json')

print(f'Generated {len(schemas)} JSON schemas.')
"
