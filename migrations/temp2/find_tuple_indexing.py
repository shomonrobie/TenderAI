# migrations/find_tuple_indexing.py
"""Find all tuple indexing patterns that need to be converted to dict access"""

import re
from pathlib import Path
from collections import defaultdict

# Patterns to search for
PATTERNS = {
    'row_indexing': r'\b(\w+)\[(\d+)\]',  # variable[0], variable[1], etc.
    'len_check': r'len\((\w+)\)\s*>\s*\d+',  # len(var) > 2
    'subscription_plan': r's\[2\]',  # s[2] for plan
    'subscription_status': r's\[3\]',  # s[3] for status
    'tuple_unpacking': r'\((\w+),\s*(\w+),\s*(\w+)\)\s*=\s*(\w+)',  # a, b, c = row
}

# Skip these directories
SKIP_DIRS = ['migrations', 'venv', '__pycache__', 'temp', 'backup', '.git']


def find_tuple_indexing(project_root="."):
    """Find all files with tuple indexing patterns"""
    
    project_path = Path(project_root).resolve()
    results = defaultdict(list)
    
    print("=" * 70)
    print("🔍 SCANNING FOR TUPLE INDEXING PATTERNS")
    print("=" * 70)
    print(f"Scanning: {project_path}\n")
    
    # Track counts
    total_files = 0
    files_with_issues = 0
    
    for py_file in project_path.rglob("*.py"):
        # Skip unwanted directories
        if any(skip in str(py_file) for skip in SKIP_DIRS):
            continue
        
        total_files += 1
        file_issues = []
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check each pattern
            for line_num, line in enumerate(lines, 1):
                # Check for variable[index] patterns
                matches = re.findall(PATTERNS['row_indexing'], line)
                if matches:
                    for var_name, index in matches:
                        # Skip if it's a dictionary access like row['key']
                        if "'" not in line and '"' not in line:
                            file_issues.append({
                                'line': line_num,
                                'code': line.strip(),
                                'pattern': f'{var_name}[{index}]',
                                'var': var_name,
                                'index': int(index)
                            })
                
                # Check for len(var) > X patterns (often used with tuples)
                if re.search(PATTERNS['len_check'], line):
                    if 'len(' in line and '>' in line:
                        file_issues.append({
                            'line': line_num,
                            'code': line.strip(),
                            'pattern': 'len_check',
                            'var': re.search(r'len\((\w+)\)', line).group(1) if re.search(r'len\((\w+)\)', line) else 'unknown'
                        })
            
            if file_issues:
                files_with_issues += 1
                results[str(py_file.relative_to(project_path))] = file_issues
                
        except Exception as e:
            print(f"⚠️ Error reading {py_file}: {e}")
    
    # Print results
    print(f"\n📊 SCAN RESULTS:")
    print(f"   Total Python files: {total_files}")
    print(f"   Files with tuple indexing: {files_with_issues}")
    
    if results:
        print("\n" + "=" * 70)
        print("📋 FILES WITH TUPLE INDEXING ISSUES")
        print("=" * 70)
        
        for filepath, issues in sorted(results.items()):
            print(f"\n📄 {filepath}")
            print(f"   Issues found: {len(issues)}")
            
            # Show first 5 issues per file
            for issue in issues[:5]:
                print(f"   Line {issue['line']}: {issue['code'][:80]}")
                print(f"        → Pattern: {issue.get('pattern', issue.get('var', 'unknown'))}")
            
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more issues")
    
    return results


def find_specific_patterns():
    """Find specific problematic patterns"""
    
    project_path = Path(".").resolve()
    
    patterns = {
        's[2] (subscription plan)': r's\[2\]',
        's[3] (subscription status)': r's\[3\]',
        'user[0] (user id)': r'user\[0\]',
        'user[1] (username)': r'user\[1\]',
        'parent[0]': r'parent\[0\]',
        'parent[1]': r'parent\[1\]',
        'parent[2]': r'parent\[2\]',
        'child[0]': r'child\[0\]',
        'row[0]': r'row\[0\]',
        'len(s) > 2': r'len\(s\)\s*>\s*2',
    }
    
    print("\n" + "=" * 70)
    print("🎯 SEARCHING FOR SPECIFIC PATTERNS")
    print("=" * 70)
    
    all_matches = defaultdict(list)
    
    for py_file in project_path.rglob("*.py"):
        if any(skip in str(py_file) for skip in SKIP_DIRS):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for pattern_name, pattern in patterns.items():
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        all_matches[pattern_name].append({
                            'file': str(py_file.relative_to(project_path)),
                            'line': line_num,
                            'code': line.strip()
                        })
        except:
            pass
    
    for pattern_name, matches in all_matches.items():
        print(f"\n🔍 {pattern_name}: {len(matches)} occurrences")
        for match in matches[:3]:
            print(f"   📁 {match['file']}:{match['line']}")
            print(f"      {match['code'][:80]}")
        if len(matches) > 3:
            print(f"   ... and {len(matches) - 3} more")


def generate_fix_report(results):
    """Generate a fix report with suggested replacements"""
    
    print("\n" + "=" * 70)
    print("🔧 SUGGESTED FIXES")
    print("=" * 70)
    
    fixes = {
        'row[0]': 'row.get(\'id\')',
        'row[1]': 'row.get(\'username\')',
        'row[2]': 'row.get(\'email\')',
        'row[3]': 'row.get(\'full_name\')',
        'row[4]': 'row.get(\'phone\')',
        'row[5]': 'row.get(\'role\')',
        'row[6]': 'row.get(\'is_active\')',
        'parent[0]': 'parent.get(\'pwd_code\') or parent[0]',
        'parent[1]': 'parent.get(\'description\') or parent[1]',
        'parent[2]': 'parent.get(\'chapter_number\') or parent[2]',
        'child[0]': 'child.get(\'pwd_code\') or child[0]',
        'child[3]': 'child.get(\'zone_name\') or child[3]',
        'child[4]': 'child.get(\'unit_rate\') or child[4]',
        's[2]': 's.get(\'plan\')',
        's[3]': 's.get(\'status\')',
        'len(s) > 2 and s[2]': 's.get(\'plan\')',
    }
    
    print("\n📝 Replace tuple indexing with dict access:\n")
    for old, new in fixes.items():
        print(f"   {old:30} → {new}")
    
    print("\n" + "=" * 70)
    print("💡 QUICK FIX FOR admin_dashboard.py")
    print("=" * 70)
    print("""
    Change:
        paid_subs = len([s for s in all_subs if len(s) > 2 and s[2] not in ['free', 'trial']]) if all_subs else 0
    
    To:
        paid_subs = len([s for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0
    """)


if __name__ == "__main__":
    # Find all tuple indexing
    results = find_tuple_indexing()
    
    # Find specific patterns
    find_specific_patterns()
    
    # Generate fix report
    generate_fix_report(results)
    
    # Save results to file
    output_file = Path("data/tuple_indexing_report.txt")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("TUPLE INDEXING SCAN REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        for filepath, issues in results.items():
            f.write(f"\n📄 {filepath}\n")
            for issue in issues:
                f.write(f"   Line {issue['line']}: {issue['code']}\n")
    
    print(f"\n📄 Full report saved to: {output_file}")