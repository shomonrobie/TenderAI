# check_backup.py
import sqlite3
import os

# Check if backup exists
backup_file = "data/backup/tender_system_dump_20260614_085255.sql"
if os.path.exists(backup_file):
    size = os.path.getsize(backup_file)
    print(f"✅ Backup found: {backup_file}")
    print(f"   Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
    
    # Read first few lines to verify it's a valid SQL dump
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[:10]
        print("\n📄 First few lines of backup:")
        for line in lines:
            print(f"   {line[:100]}...")
else:
    print("❌ No backup file found")