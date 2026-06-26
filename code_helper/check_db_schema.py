import sqlite3
import os

db_path = r"D:\itender\data\tender_system.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tender_analyses table structure
    cursor.execute("PRAGMA table_info(tender_analyses)")
    columns = cursor.fetchall()
    
    print("=== tender_analyses table columns ===")
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - Nullable: {col[3]}, Default: {col[4]}")
    
    # Check if any records exist
    cursor.execute("SELECT COUNT(*) FROM tender_analyses")
    count = cursor.fetchone()[0]
    print(f"\nTotal records in tender_analyses: {count}")
    
    # Get the last 5 records to see structure
    if count > 0:
        cursor.execute("SELECT id, tender_title, analysis_type, analysis_date FROM tender_analyses ORDER BY id DESC LIMIT 5")
        print("\nLast 5 records:")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Title: {row[1]}, Type: {row[2]}, Date: {row[3]}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")