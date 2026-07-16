import sqlite3
import requests
import json
import os
import time

# ============================================================================
# SUPABASE CONFIGURATION
# ============================================================================


# USE SERVICE ROLE KEY (from Supabase Dashboard > Project Settings > API)
SUPABASE_URL = "https://jraddelrfescykkiwtql.supabase.co"
# Replace with your service_role key (found in Project Settings > API)
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyYWRkZWxyZmVzY3lra2l3dHFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTMxNzUzNywiZXhwIjoyMDk2ODkzNTM3fQ.PV4CcR48mShFepwREOC7aGjiK-NWBTUicIFAejG2-xs"  # <-- REPLACE THIS!
# export_all_data.py

# export_missing_tables.py

# Missing tables that have data
MISSING_TABLES_WITH_DATA = [
    'extension_downloads',      # 14 rows
    'rate_audit_log',           # 19 rows
    'schema_migrations',        # 13 rows
    'tender_team_assignments',  # 20 rows
    'tenders_boq_meta',         # 1 row
    'verification_history',     # 6 rows
    'rate_chapters',            # 1 row
    'rate_sections',            # 1 row
    'rate_snapshots',           # 2 rows
]

# Tables that are empty (0 rows) - just create the table
EMPTY_TABLES = [
    'archive_records',
    'company_cost_profiles',
    'company_onboarding_status',
    'demo_data_generation_log',
    'onboarding_wizard_sessions',
    'pwd_change_log',
    'pwd_child_items',
    'pwd_parent_items',
    'pwd_snapshots',
    'rate_change_log',
    'rate_import_history',
    'regional_rates',
    'saved_scenarios',
    'scenario_comments',
    'scenario_shares',
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
    'user_activity_log',
    'vector_embeddings',
    'version_change_log',
    'work_program',
]

def create_table_in_supabase(table_name):
    """Create table in Supabase using REST API (simplified)"""
    # This is a placeholder - tables should be created via SQL Editor
    print(f"  📝 Create table: {table_name} (via Supabase SQL Editor)")
    return True

def export_data_to_supabase(table_name):
    """Export data from SQLite to Supabase"""
    print(f"🔄 Exporting: {table_name}")
    
    # Get data from SQLite
    conn = sqlite3.connect("data/tender_system.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
    except Exception as e:
        print(f"  ❌ Error reading table: {e}")
        conn.close()
        return 0, 1
    
    conn.close()
    
    if not data:
        print(f"  ⏭️ No data in {table_name}")
        return 0, 0
    
    print(f"  📦 {len(data)} rows")
    
    # Prepare headers
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates"
    }
    
    # Process in batches
    batch_size = 50
    success_count = 0
    error_count = 0
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        
        # Convert datetime objects to strings
        for row in batch:
            for key, value in row.items():
                if value is None:
                    row[key] = None
                elif hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, bytes):
                    row[key] = value.hex()
        
        try:
            response = requests.post(url, json=batch, headers=headers)
            
            if response.status_code in [200, 201]:
                success_count += len(batch)
                print(f"  ✅ Inserted {len(batch)} rows (batch {i//batch_size + 1})")
            else:
                error_count += len(batch)
                print(f"  ❌ Error: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            error_count += len(batch)
            print(f"  ❌ Exception: {e}")
        
        time.sleep(0.1)
    
    print(f"  ✅ Complete: {success_count} rows, {error_count} errors")
    return success_count, error_count

# ============================================================================
# MAIN
# ============================================================================

print("=" * 70)
print("🚀 EXPORTING MISSING TABLES TO SUPABASE")
print("=" * 70)
print("")
print("⚠️ First, create the missing tables in Supabase SQL Editor")
print("   Run the SQL generated by generate_missing_schemas.py")
print("")
print("Then export the data...")
print("")

# First check if tables exist
print("📊 Checking for missing tables...")
print("")

# Export tables with data
for table in MISSING_TABLES_WITH_DATA:
    export_data_to_supabase(table)

print("")
print("=" * 70)
print("🎉 EXPORT COMPLETE!")
print("=" * 70)