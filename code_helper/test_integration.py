# test_integration.py
import sqlite3
import sys
import os

# Instruct Python interpreter to clear internal object-caching buffers
sys.dont_write_bytecode = True

try:
    from database.db_manager import DatabaseManager
    print("📋 Class module imported successfully...")
except ImportError as e:
    print(f"❌ Import Failure: {e}")
    sys.exit(1)

try:
    # Initialize your Object class instance (forcing table construction hooks)
    db = DatabaseManager()
    
    # Read the active table registry mapping out of SQLite master schemas
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Evaluate explicit targets
    required = ['tenders_boq_meta', 'tender_boq_items', 'price_change_logs', 'competitor_bids']
    missing = [t for t in required if t not in existing_tables]
    
    if missing:
        print(f"❌ Verification Failure: Missing tables -> {missing}")
        print(f"💡 Detected tables in database file: {existing_tables}")
    else:
        print(f"✅ Success! All advanced tracking and audit schemas are active inside '{db.db_path}'.")
except Exception as e:
    print(f"❌ Critical runtime crash detected: {str(e)}")
