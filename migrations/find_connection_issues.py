# migrations/find_connection_issues.py
"""Find incorrect usages of get_connection()"""

import re
from pathlib import Path

print("=" * 60)
print("🔍 Finding incorrect get_connection() usages")
print("=" * 60)

crud_path = Path("database/crud_operations.py")

if crud_path.exists():
    with open(crud_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find patterns where get_connection() is used without 'with'
    # Look for lines like: conn = self.get_connection() (not inside with)
    pattern = r'^[^#]*conn\s*=\s*self\.get_connection\(\)(?!\s*as)'
    
    lines = content.split('\n')
    issues = []
    
    for i, line in enumerate(lines):
        if 'get_connection()' in line and 'with' not in line and 'as conn' not in line:
            if 'def ' in lines[max(0, i-5)] or 'def ' in lines[i]:
                issues.append((i+1, line.strip()))
    
    if issues:
        print(f"\n⚠️ Found {len(issues)} potential issues:")
        for line_num, line in issues:
            print(f"   Line {line_num}: {line[:80]}")
    else:
        print("\n✅ No obvious issues found")
    
    print("\n💡 Make sure all database methods use:")
    print("   with self.get_connection() as conn:")
    print("       cursor = conn.cursor()")
else:
    print(f"❌ crud_operations.py not found")