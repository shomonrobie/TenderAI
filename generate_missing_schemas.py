# generate_missing_schemas.py
"""
Generate CREATE TABLE statements for missing tables in Supabase
"""

import sqlite3

# Tables that are missing in Supabase (from verification)
MISSING_TABLES = [
    'archive_records',
    'company_cost_profiles',
    'company_onboarding_status',
    'demo_data_generation_log',
    'extension_downloads',
    'onboarding_wizard_sessions',
    'pwd_change_log',
    'pwd_child_items',
    'pwd_parent_items',
    'pwd_snapshots',
    'rate_audit_log',
    'rate_change_log',
    'rate_chapters',
    'rate_import_history',
    'rate_sections',
    'rate_snapshots',
    'regional_rates',
    'saved_scenarios',
    'scenario_comments',
    'scenario_shares',
    'schema_migrations',
    'semantic_search_log',
    'social_links',
    'tenant_pricing_levels',
    'tenant_rate_audit',
    'tenant_rate_books',
    'tenant_rate_export_log',
    'tenant_rate_import_log',
    'tenant_rate_items',
    'tenant_rate_versions',
    'tender_boq_items',
    'tender_documents',
    'tender_lots',
    'tender_milestones',
    'tender_notifications',
    'tender_response_template',
    'tender_team_assignments',
    'tenders_boq_meta',
    'user_activity_log',
    'vector_embeddings',
    'verification_history',
    'version_change_log',
    'work_program',
]

def get_create_table_sql(table_name):
    """Get CREATE TABLE SQL for a table"""
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return None

def get_table_columns(table_name):
    """Get columns with types for a table"""
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    
    # Convert SQLite types to PostgreSQL types
    type_mapping = {
        'INTEGER': 'INTEGER',
        'TEXT': 'TEXT',
        'REAL': 'REAL',
        'BLOB': 'BYTEA',
        'BOOLEAN': 'BOOLEAN',
        'TIMESTAMP': 'TIMESTAMP',
        'DATE': 'DATE',
        'DATETIME': 'TIMESTAMP',
    }
    
    col_defs = []
    for col in columns:
        col_name = col[1]
        col_type = col[2].upper()
        col_notnull = col[3]
        col_pk = col[5]
        
        # Map to PostgreSQL type
        pg_type = type_mapping.get(col_type, 'TEXT')
        
        # Build column definition
        col_def = f'"{col_name}" {pg_type}'
        if col_pk:
            col_def += ' PRIMARY KEY'
        if col_notnull:
            col_def += ' NOT NULL'
        col_defs.append(col_def)
    
    return col_defs

# Generate CREATE TABLE statements in PostgreSQL format
print("=" * 70)
print("📋 GENERATING CREATE TABLE STATEMENTS FOR SUPABASE")
print("=" * 70)
print("")
print("-- Run these SQL statements in the Supabase SQL Editor")
print("-- (Supabase Dashboard > SQL Editor)")
print("")

for table in MISSING_TABLES:
    columns = get_table_columns(table)
    if columns:
        print(f"CREATE TABLE IF NOT EXISTS {table} (")
        print("    " + ",\n    ".join(columns))
        print(");")
        print("")
    else:
        print(f"-- Skipping {table} (no columns found)")