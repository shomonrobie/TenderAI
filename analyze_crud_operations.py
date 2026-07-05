# analyze_crud_operations.py
"""
Analyze DatabaseCRUD class:
- Count total methods
- Find duplicate method names (if any)
- Show method list with line numbers
"""

import ast
import os
from collections import defaultdict

def analyze_file(file_path="database/crud_operations.py"):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)
    
    methods = []
    method_count = defaultdict(list)  # method_name -> list of line numbers
    
    class DatabaseCRUD:
        pass  # placeholder for detection

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "DatabaseCRUD":
            for body_node in node.body:
                if isinstance(body_node, ast.FunctionDef):
                    method_name = body_node.name
                    line_no = body_node.lineno
                    methods.append((method_name, line_no))
                    method_count[method_name].append(line_no)
    
    # Results
    print("="*60)
    print(f"📊 ANALYSIS OF DatabaseCRUD in: {file_path}")
    print("="*60)
    print(f"Total methods found: {len(methods)}\n")
    
    # Show duplicates
    duplicates = {name: lines for name, lines in method_count.items() if len(lines) > 1}
    
    if duplicates:
        print("⚠️  DUPLICATE METHOD NAMES FOUND:")
        print("-" * 40)
        for name, lines in duplicates.items():
            print(f"   • {name}()  →  appears {len(lines)} times at lines: {lines}")
    else:
        print("✅ No duplicate method names found.")
    
    # List all methods (sorted)
    print("\n📋 All Methods (sorted alphabetically):")
    print("-" * 50)
    for name, line in sorted(methods):
        print(f"   {name:35} (line {line})")
    
    print(f"\nTotal unique methods: {len(method_count)}")
    print(f"Total method definitions: {len(methods)}")


if __name__ == "__main__":
    analyze_file("database/crud_operations.py")
    # analyze_file("database/unified_db_manager.py")  # Uncomment if you want to check this too