# Consensu.org TCF Vendor List Database

This directory contains tools to create and populate a SQLite database from the Consensu.org TCF (Transparency and Consent Framework) Global Vendor List JSON file.

## Overview

The TCF Global Vendor List is a comprehensive registry of advertising technology vendors and their data processing declarations, purposes, features, and compliance information. This database schema normalizes the JSON data structure for efficient querying and analysis.

## Files

- `consensu.org.v3.vendor-list.json` - Source JSON file from Consensu.org
- `create_consensu_db.py` - Database schema creation script
- `import_consensu_data.py` - Data import script
- `consensu_schema.sql` - Pure SQL schema definition
- `README.md` - This documentation file

## Database Schema

### Core Tables

#### Metadata
- `metadata` - GVL specification version, vendor list version, policy version, last updated

#### Reference Data (Lookup tables)
- `purposes` - Standard TCF purposes (11 items)
- `special_purposes` - Security/technical purposes (3 items)
- `features` - Data processing features (3 items)
- `special_features` - Advanced features requiring consent (2 items)
- `data_categories` - Types of data processed (11 items)
- `stacks` - Predefined purpose combinations (45 items)

#### Vendor Data
- `vendors` - Main vendor information (1,047+ vendors)
- `vendor_urls` - Multi-language privacy/legal URLs
- `vendor_data_retention` - Data retention policies

### Relationship Tables

The schema uses junction tables to model many-to-many relationships:

- `vendor_purposes` - Vendor declared purposes (consent basis)
- `vendor_leg_int_purposes` - Legitimate interest purposes
- `vendor_flexible_purposes` - Flexible basis purposes
- `vendor_special_purposes` - Special purposes (security, etc.)
- `vendor_features` - Features used by vendors
- `vendor_special_features` - Special features (geolocation, device scanning)
- `vendor_data_declarations` - Data categories processed
- `stack_purposes` - Purposes in each stack
- `stack_special_features` - Special features in stacks

## Usage

### 1. Create Database

```bash
# Create empty database with schema
python create_consensu_db.py --db-path consensu_vendors.db

# Force recreation if database exists
python create_consensu_db.py --db-path consensu_vendors.db --force
```

### 2. Import Data

```bash
# Import JSON data into database
python import_consensu_data.py \
    --json-file consensu.org.v3.vendor-list.json \
    --db-file consensu_vendors.db
```

### 3. Query Database

Connect to the database using any SQLite client:

```bash
sqlite3 consensu_vendors.db
```

## Sample Queries

### Find vendors using cookies with their purposes
```sql
SELECT v.id, v.name, p.name as purpose_name
FROM vendors v
JOIN vendor_purposes vp ON v.id = vp.vendor_id
JOIN purposes p ON vp.purpose_id = p.id
WHERE v.uses_cookies = 1
ORDER BY v.name;
```

### Get vendor compliance information
```sql
SELECT
    v.id,
    v.name,
    v.uses_cookies,
    v.uses_non_cookie_access,
    vu.privacy_url,
    vu.lang_id
FROM vendors v
LEFT JOIN vendor_urls vu ON v.id = vu.vendor_id
WHERE v.id = 1;
```

### Find vendors by purpose
```sql
SELECT DISTINCT v.id, v.name
FROM vendors v
JOIN vendor_purposes vp ON v.id = vp.vendor_id
JOIN purposes p ON vp.purpose_id = p.id
WHERE p.name LIKE '%advertising%'
ORDER BY v.name;
```

### Count vendors by purpose
```sql
SELECT p.name, COUNT(vp.vendor_id) as vendor_count
FROM purposes p
LEFT JOIN vendor_purposes vp ON p.id = vp.purpose_id
GROUP BY p.id, p.name
ORDER BY vendor_count DESC;
```

### Find vendors using precise geolocation
```sql
SELECT v.id, v.name
FROM vendors v
JOIN vendor_special_features vsf ON v.id = vsf.vendor_id
JOIN special_features sf ON vsf.special_feature_id = sf.id
WHERE sf.name LIKE '%precise geolocation%';
```

### Data retention analysis
```sql
SELECT
    COUNT(*) as vendor_count,
    AVG(vdr.std_retention) as avg_retention_days,
    MIN(vdr.std_retention) as min_retention_days,
    MAX(vdr.std_retention) as max_retention_days
FROM vendor_data_retention vdr;
```

## Database Statistics

After import, the database typically contains:

- **1,047+ vendors** from the advertising ecosystem
- **11 standard purposes** (store data, personalised advertising, etc.)
- **3 special purposes** (security, technical delivery, privacy)
- **3 features** (data matching, device linking, identification)
- **2 special features** (precise geolocation, device scanning)
- **11 data categories** (types of data processed)
- **45 stacks** (purpose combinations)
- **Multi-language support** for vendor privacy URLs

## Data Model Benefits

### Normalization
- Eliminates data redundancy from JSON structure
- Enables efficient storage and querying
- Maintains referential integrity with foreign keys

### Performance
- Indexed columns for common queries
- Optimized for filtering by vendor attributes
- Efficient joins between related data

### Compliance Analysis
- Track vendor purposes and legal bases
- Analyze data retention policies
- Monitor special feature usage
- Generate compliance reports

## Integration with WCT

This database can be integrated with the Waivern Compliance Tool (WCT) to:

- **Vendor Analysis** - Identify vendors in use and their declared purposes
- **Consent Management** - Map vendor purposes to consent requirements
- **Privacy Impact Assessment** - Analyze data processing risks
- **Regulatory Reporting** - Generate TCF compliance reports

## Technical Notes

- **SQLite Version**: Compatible with SQLite 3.6+
- **Foreign Keys**: Enabled for referential integrity
- **Character Encoding**: UTF-8 for international vendor names
- **JSON Fields**: Some fields store JSON arrays as TEXT (illustrations, retention policies)
- **Performance**: Indexed on commonly queried columns

## Maintenance

The database should be updated when:
- New TCF vendor list versions are released
- Vendor declarations change
- New purposes or features are added to the TCF framework

Simply re-run the import process with the latest JSON file to refresh the data.
