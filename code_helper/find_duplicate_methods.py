# migrations/find_duplicate_methods.py
"""
Find duplicate methods in crud_operations.py
"""

import re
from pathlib import Path
from collections import defaultdict


def find_duplicate_methods(file_path: str = "database/crud_operations.py"):
    """Find duplicate method definitions in a Python file"""
    
    print("=" * 70)
    print("🔍 FINDING DUPLICATE METHODS")
    print("=" * 70)
    print(f"Scanning: {file_path}\n")
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all method definitions
    # Pattern: def method_name(self, ...) or def method_name(self, ...):
    pattern = r'def\s+(\w+)\(self'
    matches = re.findall(pattern, content)
    
    # Count occurrences
    method_counts = defaultdict(list)
    for i, method in enumerate(matches):
        method_counts[method].append(i)
    
    # Find duplicates
    duplicates = {method: positions for method, positions in method_counts.items() if len(positions) > 1}
    
    if duplicates:
        print(f"📋 Found {len(duplicates)} duplicate methods:\n")
        
        # Get line numbers for each duplicate
        lines = content.split('\n')
        for method, positions in sorted(duplicates.items()):
            print(f"  ❌ {method}() - {len(positions)} occurrences")
            
            # Find line numbers
            line_numbers = []
            for pos in positions:
                # Find the line number of each occurrence
                # We need to find the line containing this method definition
                for i, line in enumerate(lines, 1):
                    if f"def {method}(self" in line and i not in line_numbers:
                        # Check if this is the right occurrence
                        if len(line_numbers) == 0 or i > line_numbers[-1]:
                            line_numbers.append(i)
                            break
            
            for i, line_num in enumerate(line_numbers[:5], 1):
                print(f"      Occurrence {i}: Line {line_num}")
                if line_num <= len(lines):
                    print(f"        {lines[line_num-1][:80]}")
            
            if len(line_numbers) > 5:
                print(f"      ... and {len(line_numbers) - 5} more")
            print()
        
        print(f"📊 Total duplicate methods: {len(duplicates)}")
        
        # Save to file
        report_path = Path("data/duplicate_methods_report.txt")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("DUPLICATE METHODS REPORT\n")
            f.write("=" * 70 + "\n\n")
            
            for method, positions in sorted(duplicates.items()):
                f.write(f"❌ {method}() - {len(positions)} occurrences\n")
                for i, pos in enumerate(positions[:5], 1):
                    f.write(f"   Occurrence {i}: Position {pos}\n")
                if len(positions) > 5:
                    f.write(f"   ... and {len(positions) - 5} more\n")
                f.write("\n")
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
    else:
        print("✅ No duplicate methods found!")
    
    # Also list all methods for reference
    print("\n" + "=" * 70)
    print("📊 ALL METHODS FOUND")
    print("=" * 70)
    
    all_methods = sorted(set(matches))
    print(f"Total unique methods: {len(all_methods)}")
    
    # Group by prefix for easier reading
    groups = defaultdict(list)
    for method in all_methods:
        prefix = method.split('_')[0] if '_' in method else method[:4]
        groups[prefix].append(method)
    
    for prefix, methods in sorted(groups.items()):
        print(f"\n  {prefix.upper()}:")
        for method in sorted(methods)[:10]:
            print(f"    - {method}()")
        if len(methods) > 10:
            print(f"    ... and {len(methods) - 10} more")
    
    return duplicates


def find_duplicate_methods_in_directory(directory: str = "."):
    """Find duplicate methods across multiple Python files"""
    
    print("=" * 70)
    print("🔍 FINDING DUPLICATE METHODS ACROSS FILES")
    print("=" * 70)
    
    directory = Path(directory)
    all_methods = defaultdict(list)
    
    for py_file in directory.rglob("*.py"):
        # Skip certain directories
        if 'venv' in str(py_file) or '__pycache__' in str(py_file) or 'migrations' in str(py_file):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            pattern = r'def\s+(\w+)\(self'
            matches = re.findall(pattern, content)
            
            for method in matches:
                all_methods[method].append(str(py_file))
                
        except Exception as e:
            print(f"⚠️ Error reading {py_file}: {e}")
    
    # Find duplicates (methods appearing in more than one file)
    duplicates = {method: files for method, files in all_methods.items() if len(files) > 1}
    
    if duplicates:
        print(f"\n📋 Found {len(duplicates)} methods that appear in multiple files:\n")
        for method, files in sorted(duplicates.items()):
            print(f"  ❌ {method}() - appears in {len(files)} files:")
            for file in files[:5]:
                print(f"      - {file}")
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more")
            print()
    else:
        print("\n✅ No duplicate methods across files found!")
    
    return duplicates


def find_duplicate_methods_by_signature(file_path: str = "database/crud_operations.py"):
    """Find methods with the same name but different signatures"""
    
    print("=" * 70)
    print("🔍 FINDING METHODS WITH DUPLICATE NAMES BUT DIFFERENT SIGNATURES")
    print("=" * 70)
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all method definitions with their full signature
    pattern = r'def\s+(\w+)\(([^)]*)\)'
    matches = re.findall(pattern, content)
    
    # Group by method name
    methods = defaultdict(list)
    for method_name, signature in matches:
        methods[method_name].append(signature.strip())
    
    # Find methods with different signatures
    different_signatures = {}
    for method_name, signatures in methods.items():
        if len(set(signatures)) > 1:
            different_signatures[method_name] = list(set(signatures))
    
    if different_signatures:
        print(f"\n📋 Found {len(different_signatures)} methods with different signatures:\n")
        for method_name, signatures in sorted(different_signatures.items()):
            print(f"  ❌ {method_name}() - {len(signatures)} different signatures:")
            for sig in signatures[:3]:
                print(f"      - def {method_name}({sig})")
            if len(signatures) > 3:
                print(f"      ... and {len(signatures) - 3} more")
            print()
    else:
        print("\n✅ No methods with different signatures found!")
    
    return different_signatures


def generate_cleanup_recommendations(duplicates):
    """Generate recommendations for cleaning up duplicates"""
    
    print("\n" + "=" * 70)
    print("💡 CLEANUP RECOMMENDATIONS")
    print("=" * 70)
    
    for method, positions in sorted(duplicates.items()):
        print(f"\n📌 {method}() - {len(positions)} occurrences")
        print(f"   → Keep ONE version (preferably the one with most features)")
        print(f"   → Delete the other {len(positions) - 1} version(s)")
        
        # Suggest which one to keep based on common patterns
        if method in ['get_user_subscription', 'get_company_subscription', 'get_all_subscriptions']:
            print(f"   → Keep the version with: JOIN with subscription_plans, more columns")
        elif method in ['update_subscription']:
            print(f"   → DELETE this method entirely - it uses wrong tables")
        elif method in ['get_all_users', 'get_all_companies']:
            print(f"   → Keep the version that returns DICT (not tuple)")


if __name__ == "__main__":
    # Scan crud_operations.py for duplicate methods
    duplicates = find_duplicate_methods("database/crud_operations.py")
    
    # Find methods with different signatures
    different_sigs = find_duplicate_methods_by_signature("database/crud_operations.py")
    
    # Generate cleanup recommendations
    if duplicates:
        generate_cleanup_recommendations(duplicates)
    
    # Optional: Scan entire project for duplicate methods across files
    print("\n" + "=" * 70)
    print("📌 To scan across all files, run:")
    print("   find_duplicate_methods_in_directory('.')")
    print("=" * 70)