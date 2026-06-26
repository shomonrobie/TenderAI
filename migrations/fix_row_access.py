# migrations/fix_row_access.py
"""Fix row access from tuple indexing to dict key access - WITH DRY RUN"""

import re
from pathlib import Path

def analyze_file(file_path):
    """Analyze file for tuple indexing patterns"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    patterns = {
        'row[0]': len(re.findall(r'row\[\d+\]', content)),
        'row.get(': len(re.findall(r'row\.get\(', content)),
        'row[\'': len(re.findall(r"row\['\w+'\]", content)),
        'count_result[0]': len(re.findall(r'count_result\[0\]', content)),
        'fetchone()[0]': len(re.findall(r'fetchone\(\)\[0\]', content)),
    }
    
    return patterns, content

def fix_row_access(content, dry_run=True):
    """Replace tuple indexing with dict key access"""
    
    changes = []
    
    # Pattern 1: row[0], row[1], etc. -> row.get('column_name')
    # This is complex because we need column names
    # For now, we'll just report and suggest manual fixes
    
    # Pattern 2: count_result[0] -> count_result.get('COUNT(*)') or list conversion
    def replace_count_result(match):
        changes.append("count_result[0] -> count_result.get('COUNT(*)')")
        return "count_result.get('COUNT(*)') if isinstance(count_result, dict) else (count_result[0] if count_result else 0)"
    
    pattern_count = r'count_result\[0\]'
    new_content = re.sub(pattern_count, replace_count_result, content)
    
    # Pattern 3: fetchone()[0] -> handle properly
    def replace_fetchone(match):
        changes.append("fetchone()[0] -> convert to dict first")
        return "list(cursor.fetchone().values())[0] if cursor.fetchone() else 0"
    
    pattern_fetchone = r'fetchone\(\)\[0\]'
    new_content = re.sub(pattern_fetchone, replace_fetchone, new_content)
    
    if not dry_run:
        return new_content, changes
    return content, changes

def run_dry_run():
    """Run dry run analysis"""
    print("=" * 70)
    print("🔍 DRY RUN - ANALYZING ROW ACCESS PATTERNS")
    print("=" * 70)
    
    crud_path = Path("database/crud_operations.py")
    
    if not crud_path.exists():
        print(f"❌ File not found: {crud_path}")
        return
    
    patterns, content = analyze_file(crud_path)
    
    print(f"\n📄 File: {crud_path}")
    print(f"   Size: {len(content)} characters")
    
    print("\n📊 PATTERN ANALYSIS:")
    print("-" * 40)
    print(f"   row[0] type indexing:     {patterns['row[0]']} occurrences")
    print(f"   row.get() usage:          {patterns['row.get(']} occurrences")
    print(f"   row['column'] usage:      {patterns['row[\'']} occurrences")
    print(f"   count_result[0]:          {patterns['count_result[0]']} occurrences")
    print(f"   fetchone()[0]:            {patterns['fetchone()[0]']} occurrences")
    
    print("\n⚠️  ISSUES FOUND:")
    if patterns['row[0]'] > 0:
        print(f"   - {patterns['row[0]']} instances of tuple indexing (row[0])")
        print("     These need to be converted to dict access (row.get('column_name'))")
    
    if patterns['count_result[0]'] > 0:
        print(f"   - {patterns['count_result[0]']} instances of count_result[0]")
        print("     These need to be converted to dict access")
    
    if patterns['fetchone()[0]'] > 0:
        print(f"   - {patterns['fetchone()[0]']} instances of fetchone()[0]")
        print("     These need to be converted to dict access")
    
    # Find specific lines with issues
    print("\n🔍 SPECIFIC LINES WITH ISSUES:")
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'row[' in line and '.get(' not in line:
            if 'row[0]' in line or 'row[1]' in line or 'row[2]' in line:
                print(f"   Line {i}: {line.strip()[:80]}")
                if i > 30:  # Limit output
                    print(f"   ... and more")
                    break
    
    print("\n" + "=" * 70)
    print("💡 RECOMMENDED FIXES:")
    print("=" * 70)
    print("""
    1. Replace tuple indexing with dict access:
       Before: row[0], row[1], row[2]
       After:  row.get('id'), row.get('username'), row.get('email')
    
    2. Replace count_result[0] with:
       count_result.get('COUNT(*)') if count_result else 0
    
    3. Replace fetchone()[0] with:
       row = cursor.fetchone()
       value = row.get('column_name') if row else 0
    
    4. Make sure all methods use:
       with self.get_connection() as conn:
           cursor = self.db_conn.get_cursor(conn)
    """)
    
    return patterns

def run_fix():
    """Run actual fix (minimal automated fixes)"""
    print("=" * 70)
    print("🔧 APPLYING AUTOMATED FIXES")
    print("=" * 70)
    
    crud_path = Path("database/crud_operations.py")
    
    if not crud_path.exists():
        print(f"❌ File not found: {crud_path}")
        return
    
    with open(crud_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply automated fixes
    new_content, changes = fix_row_access(content, dry_run=False)
    
    if changes:
        with open(crud_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\n✅ Applied {len(changes)} automated fixes:")
        for change in changes:
            print(f"   - {change}")
    else:
        print("\n⚠️ No automated fixes applied")
    
    print("\n📝 MANUAL FIXES STILL NEEDED:")
    print("   - Convert row[0], row[1], etc. to row.get('column_name')")
    print("   - Update all user dictionary creations to use .get()")

def show_manual_fix_example():
    """Show example of how to manually fix"""
    print("\n" + "=" * 70)
    print("📝 MANUAL FIX EXAMPLE")
    print("=" * 70)
    print("""
    BEFORE (WRONG):
    -----------------
    def get_all_users(self, company_id=None, role=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users")
        rows = cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                'id': row[0],           # ❌ Tuple indexing
                'username': row[1],     # ❌ Tuple indexing
                'email': row[2]         # ❌ Tuple indexing
            })
        conn.close()
        return users
    
    AFTER (CORRECT):
    -----------------
    def get_all_users(self, company_id=None, role=None):
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("SELECT id, username, email FROM users")
            rows = cursor.fetchall()
            users = []
            for row in rows:
                users.append({
                    'id': row.get('id'),           # ✅ Dict access
                    'username': row.get('username'), # ✅ Dict access
                    'email': row.get('email')       # ✅ Dict access
                })
            return users
    """)


if __name__ == "__main__":
    import sys
    
    if '--fix' in sys.argv:
        run_fix()
    elif '--example' in sys.argv:
        show_manual_fix_example()
    else:
        # Default: dry run
        run_dry_run()
        print("\n💡 To apply automated fixes, run: python migrations/fix_row_access.py --fix")
        print("   To see manual fix example, run: python migrations/fix_row_access.py --example")