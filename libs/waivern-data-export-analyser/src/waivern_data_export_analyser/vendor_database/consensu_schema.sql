-- SQLite Schema for Consensu.org TCF Global Vendor List
-- This schema stores TCF (Transparency and Consent Framework) vendor data
-- in a normalized relational structure for efficient querying

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================================
-- METADATA TABLES
-- ============================================================================

-- Store GVL metadata (specification version, update info, etc.)
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY,
    gvl_specification_version INTEGER NOT NULL,
    vendor_list_version INTEGER NOT NULL,
    tcf_policy_version INTEGER NOT NULL,
    last_updated TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- REFERENCE TABLES (Static lookup data)
-- ============================================================================

-- Standard TCF purposes (e.g., "Store and/or access information")
CREATE TABLE purposes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    illustrations TEXT  -- JSON array as text
);

-- Special purposes (security, technical delivery, privacy choices)
CREATE TABLE special_purposes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    illustrations TEXT  -- JSON array as text
);

-- Data processing features (matching, linking devices, etc.)
CREATE TABLE features (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    illustrations TEXT  -- JSON array as text
);

-- Advanced features requiring explicit consent (geolocation, device scanning)
CREATE TABLE special_features (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    illustrations TEXT  -- JSON array as text
);

-- Types of data processed (categories defined by TCF)
CREATE TABLE data_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Predefined combinations of purposes and features
CREATE TABLE stacks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

-- ============================================================================
-- VENDOR TABLES (Main data)
-- ============================================================================

-- Main vendor information
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cookie_max_age_seconds INTEGER,
    uses_cookies BOOLEAN NOT NULL,
    cookie_refresh BOOLEAN NOT NULL,
    uses_non_cookie_access BOOLEAN NOT NULL,
    device_storage_disclosure_url TEXT
);

-- Multi-language privacy and legal URLs for vendors
CREATE TABLE vendor_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL,
    lang_id TEXT NOT NULL,
    privacy_url TEXT,
    leg_int_claim_url TEXT,
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
);

-- Data retention policies per vendor
CREATE TABLE vendor_data_retention (
    vendor_id INTEGER PRIMARY KEY,
    std_retention INTEGER,  -- Standard retention in days
    purposes_retention TEXT,  -- JSON object for purpose-specific retention
    special_purposes_retention TEXT,  -- JSON object for special purpose retention
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
);

-- ============================================================================
-- JUNCTION TABLES (Many-to-many relationships)
-- ============================================================================

-- Vendor declared purposes (consent basis)
CREATE TABLE vendor_purposes (
    vendor_id INTEGER NOT NULL,
    purpose_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, purpose_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
);

-- Vendor legitimate interest purposes
CREATE TABLE vendor_leg_int_purposes (
    vendor_id INTEGER NOT NULL,
    purpose_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, purpose_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
);

-- Vendor flexible purposes (can use either consent or legitimate interest)
CREATE TABLE vendor_flexible_purposes (
    vendor_id INTEGER NOT NULL,
    purpose_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, purpose_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
);

-- Special purposes declared by vendors
CREATE TABLE vendor_special_purposes (
    vendor_id INTEGER NOT NULL,
    special_purpose_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, special_purpose_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (special_purpose_id) REFERENCES special_purposes (id) ON DELETE CASCADE
);

-- Features used by vendors
CREATE TABLE vendor_features (
    vendor_id INTEGER NOT NULL,
    feature_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, feature_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE
);

-- Special features used by vendors
CREATE TABLE vendor_special_features (
    vendor_id INTEGER NOT NULL,
    special_feature_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, special_feature_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (special_feature_id) REFERENCES special_features (id) ON DELETE CASCADE
);

-- Data categories processed by vendors
CREATE TABLE vendor_data_declarations (
    vendor_id INTEGER NOT NULL,
    data_category_id INTEGER NOT NULL,
    PRIMARY KEY (vendor_id, data_category_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
    FOREIGN KEY (data_category_id) REFERENCES data_categories (id) ON DELETE CASCADE
);

-- Purposes included in each stack
CREATE TABLE stack_purposes (
    stack_id INTEGER NOT NULL,
    purpose_id INTEGER NOT NULL,
    PRIMARY KEY (stack_id, purpose_id),
    FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
    FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
);

-- Special features included in each stack
CREATE TABLE stack_special_features (
    stack_id INTEGER NOT NULL,
    special_feature_id INTEGER NOT NULL,
    PRIMARY KEY (stack_id, special_feature_id),
    FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
    FOREIGN KEY (special_feature_id) REFERENCES special_features (id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Vendor URL indexes
CREATE INDEX idx_vendor_urls_vendor_id ON vendor_urls (vendor_id);
CREATE INDEX idx_vendor_urls_lang_id ON vendor_urls (lang_id);

-- Vendor purposes indexes
CREATE INDEX idx_vendor_purposes_vendor_id ON vendor_purposes (vendor_id);
CREATE INDEX idx_vendor_purposes_purpose_id ON vendor_purposes (purpose_id);

-- Vendor features indexes
CREATE INDEX idx_vendor_features_vendor_id ON vendor_features (vendor_id);
CREATE INDEX idx_vendor_features_feature_id ON vendor_features (feature_id);

-- Vendor search indexes
CREATE INDEX idx_vendors_name ON vendors (name);
CREATE INDEX idx_vendors_uses_cookies ON vendors (uses_cookies);
CREATE INDEX idx_vendors_uses_non_cookie_access ON vendors (uses_non_cookie_access);

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

/*
-- Find all vendors using cookies with their purposes:
SELECT v.id, v.name, p.name as purpose_name
FROM vendors v
JOIN vendor_purposes vp ON v.id = vp.vendor_id
JOIN purposes p ON vp.purpose_id = p.id
WHERE v.uses_cookies = 1
ORDER BY v.name;

-- Get vendor compliance information:
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

-- Find vendors by purpose:
SELECT v.id, v.name
FROM vendors v
JOIN vendor_purposes vp ON v.id = vp.vendor_id
JOIN purposes p ON vp.purpose_id = p.id
WHERE p.name LIKE '%advertising%'
ORDER BY v.name;

-- Count vendors by purpose:
SELECT p.name, COUNT(vp.vendor_id) as vendor_count
FROM purposes p
LEFT JOIN vendor_purposes vp ON p.id = vp.purpose_id
GROUP BY p.id, p.name
ORDER BY vendor_count DESC;
*/
