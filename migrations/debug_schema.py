# migrations/debug_schema.py
"""Debug script to check what's in schema.py"""

import re
from pathlib import Path

schema_path = Path(__file__).parent.parent / "database" / "schema.py"

print(f"Looking for schema.py at: {schema_path}")
print(f"File exists: {schema_path.exists()}\n")

if schema_path.exists():
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters\n")
    
    # Find all CREATE TABLE statements
    print("Searching for CREATE TABLE statements...")
    
    # Method 1: Direct search for "CREATE TABLE"
    create_table_matches = re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)', content, re.IGNORECASE)
    print(f"Found {len(create_table_matches)} table names:")
    for table in create_table_matches[:20]:
        print(f"  - {table}")
    
    # Method 2: Look for cursor.execute with CREATE TABLE
    print("\nSearching for cursor.execute with CREATE TABLE...")
    pattern = r'cursor\.execute\([f"]{0,3}(?:[""]")?\s*CREATE TABLE'
    matches = re.findall(pattern, content, re.IGNORECASE)
    print(f"Found {len(matches)} cursor.execute statements with CREATE TABLE")
    
    # Method 3: Show first 2000 characters
    print("\n" + "="*50)
    print("First 2000 characters of schema.py:")
    print("="*50)
    print(content[:2000])