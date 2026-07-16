# quick_check.py
import sqlite3
import requests
import json
# USE SERVICE ROLE KEY (from Supabase Dashboard > Project Settings > API)
SUPABASE_URL = "https://jraddelrfescykkiwtql.supabase.co"
# Replace with your service_role key (found in Project Settings > API)
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyYWRkZWxyZmVzY3lra2l3dHFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTMxNzUzNywiZXhwIjoyMDk2ODkzNTM3fQ.PV4CcR48mShFepwREOC7aGjiK-NWBTUicIFAejG2-xs"  # <-- REPLACE THIS!



def get_sqlite_count(table_name):
    """Get row count from SQLite"""
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        conn.close()
        return 0

def get_supabase_count(table_name):
    """Get row count from Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return len(data) if isinstance(data, list) else 0
        else:
            return -1
    except Exception as e:
        return -1

def verify_table(table_name):
    """Verify a single table"""
    sqlite_count = get_sqlite_count(table_name)
    supabase_count = get_supabase_count(table_name)
    
    if supabase_count == -1:
        status = "❌ Table not found"
    elif sqlite_count == supabase_count:
        status = "✅"
    else:
        status = "⚠️"
    
    return {
        'table': table_name,
        'sqlite': sqlite_count,
        'supabase': supabase_count,
        'status': status
    }

# ============================================================================
# MAIN
# ============================================================================

def verify_all():
    """Verify all tables"""
    
    print("=" * 70)
    print("🔍 VERIFYING MIGRATION")
    print("=" * 70)
    print("")
    
    # Get all tables from SQLite
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE 'fts_%'
        AND name NOT LIKE '%_config'
        AND name NOT LIKE '%_content'
        AND name NOT LIKE '%_data'
        AND name NOT LIKE '%_docsize'
        AND name NOT LIKE '%_idx'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Tables to skip
    skip_tables = ['oauth_providers', 'extension_auto_fill_log']
    tables_to_check = [t for t in tables if t not in skip_tables]
    
    print(f"📊 Checking {len(tables_to_check)} tables...")
    print("")
    
    results = []
    mismatches = []
    missing = []
    
    for table in tables_to_check:
        result = verify_table(table)
        results.append(result)
        
        if result['status'] == '❌':
            missing.append(table)
        elif result['status'] == '⚠️':
            mismatches.append(table)
        
        # Print progress
        print(f"{result['status']} {table}: SQLite={result['sqlite']}, Supabase={result['supabase']}")
    
    # Summary
    print("")
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    total_matched = len([r for r in results if r['status'] == '✅'])
    total_mismatched = len(mismatches)
    total_missing = len(missing)
    total_tables = len(results)
    
    print(f"✅ Matched: {total_matched}/{total_tables}")
    print(f"⚠️ Mismatched: {total_mismatched}/{total_tables}")
    print(f"❌ Missing: {total_missing}/{total_tables}")
    
    if mismatches:
        print("\n⚠️ Tables with row count mismatches:")
        for table in mismatches:
            result = next(r for r in results if r['table'] == table)
            print(f"  - {table}: SQLite={result['sqlite']}, Supabase={result['supabase']}")
    
    if missing:
        print("\n❌ Tables missing in Supabase:")
        for table in missing:
            print(f"  - {table}")
    
    print("")
    print("=" * 70)
    print("🎉 VERIFICATION COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    verify_all()