# waivern-schemas

Centralised schema definitions for the Waivern Compliance Framework.

This package owns all analysis schema definitions (Pydantic models and generated JSON schemas) used across the WCF ecosystem. Producers and consumers depend on this single package instead of importing types from each other.

## Usage

```python
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel
from waivern_schemas.connector_types import BaseMetadata
```

## Schema Registration

Schemas are registered automatically via entry points. For tests, call explicitly:

```python
from waivern_schemas import register_schemas
register_schemas()
```

## Versioning

Each schema is a sub-package with directory-based versioning (`v1.py`, `v2.py`, ...). The `__init__.py` re-exports from the current version, so consumers use clean imports without version awareness. To pin a specific version:

```python
from waivern_schemas.personal_data_indicator.v1 import PersonalDataIndicatorModel
```
