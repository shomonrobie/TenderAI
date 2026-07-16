# fix_rate_sections.py
"""
Export the missing rate_sections data
"""

import sqlite3
import requests
import json


# USE SERVICE ROLE KEY (from Supabase Dashboard > Project Settings > API)
SUPABASE_URL = "https://jraddelrfescykkiwtql.supabase.co"
# Replace with your service_role key (found in Project Settings > API)
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyYWRkZWxyZmVzY3lra2l3dHFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTMxNzUzNywiZXhwIjoyMDk2ODkzNTM3fQ.PV4CcR48mShFepwREOC7aGjiK-NWBTUicIFAejG2-xs"  # <-- REPLACE THIS!
# export_all_data.py


def export_rate_sections():
    """Export rate_sections data to Supabase"""
    
    print("=" * 70)
    print("🔧 FIXING rate_sections TABLE")
    print("=" * 70)
    print("")
    
    # Get data from SQLite
    conn = sqlite3.connect("data/tender_system.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM rate_sections")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error reading table: {e}")
        conn.close()
        return
    
    conn.close()
    
    print(f"📦 Found {len(data)} rows in rate_sections")
    
    if not data:
        print("ℹ️ No data to export")
        return
    
    # Show the data
    print("\n📋 Data to export:")
    for row in data:
        print(f"  {row}")
    
    # Prepare headers
    url = f"{SUPABASE_URL}/rest/v1/rate_sections"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates"
    }
    
    # Insert the data
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"\n✅ Successfully exported {len(data)} rows to rate_sections")
        else:
            print(f"\n❌ Error: {response.status_code} - {response.text}")
            
            # Try to insert one by one to find the issue
            print("\n🔄 Trying one by one...")
            success = 0
            for row in data:
                try:
                    resp = requests.post(url, json=[row], headers=headers)
                    if resp.status_code in [200, 201]:
                        success += 1
                    else:
                        print(f"  ❌ Failed row: {row} - {resp.text}")
                except Exception as e:
                    print(f"  ❌ Exception: {e}")
            
            print(f"\n✅ Inserted {success} out of {len(data)} rows")
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")

def check_rate_sections():
    """Check rate_sections in both databases"""
    
    # SQLite count
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM rate_sections")
        sqlite_count = cursor.fetchone()[0]
    except:
        sqlite_count = 0
    conn.close()
    
    # Supabase count
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/rate_sections", headers=headers)
        if response.status_code == 200:
            supabase_count = len(response.json()) if response.json() else 0
        else:
            supabase_count = -1
    except:
        supabase_count = -1
    
    print("\n📊 Verification:")
    print(f"  SQLite: {sqlite_count} rows")
    print(f"  Supabase: {supabase_count} rows")
    
    if sqlite_count == supabase_count:
        print("  ✅ MATCHED!")
    else:
        print("  ⚠️ Still mismatched!")

if __name__ == "__main__":
    export_rate_sections()
    check_rate_sections()