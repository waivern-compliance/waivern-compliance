# waivern-data-export-analyser

**Status:** Work in Progress

Data export analyser for the Waivern Compliance Framework. This package is currently under development and not yet functional as a WCF analyser.

## Current Status

This package currently hosts vendor database tooling for TCF (Transparency and Consent Framework) compliance analysis:

- **Vendor Database**: TCF Global Vendor List database utilities in `src/waivern_data_export_analyser/vendor_database/`
- **Analyser Stub**: Empty analyser implementation for future development
- **Tests**: Vendor database protection tests

## Vendor Database Tooling

The vendor database directory contains:
- `consensu.org.v3.vendor-list.json` - TCF Global Vendor List (1,047+ advertising vendors)
- `create_consensu_db.py` - Database schema creation script
- `import_consensu_data.py` - Data import script
- `consensu_db.db` - SQLite database
- `consensu_schema.sql` - SQL schema definition
- `README.md` - Detailed vendor database documentation

See `src/waivern_data_export_analyser/vendor_database/README.md` for usage instructions.

## Future Development

The analyser implementation will:
- Analyse data export practices using the TCF vendor database
- Identify compliance risks in vendor data handling
- Validate data export declarations against actual usage

## Installation

```bash
# Development installation
cd libs/waivern-data-export-analyser
uv pip install -e .
```

## Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=waivern_data_export_analyser
```

## Entry Points

This package registers with WCF via entry points:
- `waivern.analysers`: `data_export` → `DataExportAnalyserFactory`
- `waivern.schemas`: `data_export` → `register_schemas`

Note: The analyser is not yet functional and will raise `NotImplementedError` if used.
