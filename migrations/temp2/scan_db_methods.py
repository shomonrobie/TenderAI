# migrations/scan_db_methods.py - Fixed version

import re
import ast
import inspect
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List, Tuple

# Configuration
SKIP_DIRS = {'migrations', 'venv', '__pycache__', 'temp', 'backup', '.git', 'data', 'logs'}
SKIP_FILES = {'scan_db_methods.py', 'fix_tuple_indexing.py', 'audit_db_manager.py'}

# Database instance patterns to look for
DB_PATTERNS = [
    r'db\.(\w+)\(',
    r'db_manager\.(\w+)\(',
    r'unified_db_manager\.(\w+)\(',
    r'self\.db\.(\w+)\(',
    r'self\.db_manager\.(\w+)\(',
]

# Methods that typically return tuples (need indexing)
TUPLE_METHODS = {
    'get_all_users', 'get_all_subscriptions', 'get_all_companies',
    'get_pending_users', 'get_system_users', 'get_company_users',
    'get_all_users_filtered', 'get_all_companies_filtered'
}

# Methods that return dicts (use .get() or keys)
DICT_METHODS = {
    'authenticate_user', 'get_user_by_id', 'get_user_by_email', 'get_user_by_mobile',
    'get_company_by_id', 'get_company_profile', 'get_company_stats',
    'get_competitor_by_id', 'get_personnel_by_id', 'get_equipment_by_id',
    'get_experience_by_id', 'get_scenario_by_id', 'get_boq'
}

# Methods that return DataFrames
DF_METHODS = {
    'get_user_analyses', 'get_historical_tenders', 'get_competitor_master_list',
    'get_pwd_chapters', 'get_lged_chapters', 'get_pwd_children',
    'get_lged_parents', 'get_lged_children', 'get_tender_analyses_by_company'
}


class DatabaseMethodScanner:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.crud_path = self.project_root / "database" / "crud_operations.py"
        self.used_methods: Dict[str, List[Dict]] = defaultdict(list)
        self.crud_methods: Set[str] = set()
        self.method_issues: Dict[str, List[str]] = defaultdict(list)
        
    def get_crud_methods(self) -> Set[str]:
        """Extract all method names from crud_operations.py"""
        if not self.crud_path.exists():
            print(f"❌ crud_operations.py not found at {self.crud_path}")
            return set()
        
        with open(self.crud_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all method definitions
        pattern = r'def\s+(\w+)\(self'
        methods = set(re.findall(pattern, content))
        
        # Also find methods with @staticmethod
        pattern_static = r'@staticmethod\s+def\s+(\w+)\('
        methods.update(re.findall(pattern_static, content, re.DOTALL))
        
        # Also find methods with @classmethod
        pattern_class = r'@classmethod\s+def\s+(\w+)\('
        methods.update(re.findall(pattern_class, content, re.DOTALL))
        
        print(f"📚 Found {len(methods)} methods in crud_operations.py")
        return methods
    
    def scan_file_for_methods(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """Scan a single file for database method calls"""
        methods_found = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                content = ''.join(lines)
        except Exception as e:
            return []
        
        for pattern in DB_PATTERNS:
            for match in re.finditer(pattern, content):
                method_name = match.group(1)
                # Calculate line number correctly
                line_num = content[:match.start()].count('\n') + 1
                
                # Get the line content safely
                line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                
                methods_found.append((method_name, line_num, line_content))
        
        return methods_found
    
    def analyze_usage_pattern(self, file_path: Path, line_num: int, line_content: str, method_name: str) -> Dict:
        """Analyze how a method is being used"""
        result = {
            'method': method_name,
            'file': str(file_path.relative_to(self.project_root)),
            'line': line_num,
            'code': line_content[:100],
            'usage_type': 'unknown',
            'needs_fix': False,
            'fix_suggestion': ''
        }
        
        # Check for tuple indexing after the method call
        # Look for patterns like .[0], .[1], s[2], row[0]
        if re.search(r'\[\d+\]', line_content):
            result['usage_type'] = 'tuple_indexing'
            result['needs_fix'] = True
            result['fix_suggestion'] = f"Change {method_name}() to return tuple or use dict access"
        
        # Check for .get() usage (dict access)
        elif re.search(r'\.get\(', line_content):
            result['usage_type'] = 'dict_access'
            result['needs_fix'] = False
        
        # Check for dictionary key access ['key']
        elif re.search(r"\[\'[\w]+\'\]|\[\"[\w]+\"\]", line_content):
            result['usage_type'] = 'dict_key_access'
            result['needs_fix'] = False
        
        # Check for attribute access .key
        elif re.search(r'\.\w+', line_content):
            result['usage_type'] = 'attribute_access'
            result['needs_fix'] = False
        
        # Check if assigned to variable then used later
        else:
            result['usage_type'] = 'assignment_only'
            result['needs_fix'] = 'check_usage_context'
        
        return result
    
    def scan_project(self):
        """Scan entire project for database method usage"""
        print("\n" + "=" * 70)
        print("🔍 SCANNING PROJECT FOR DATABASE METHOD USAGE")
        print("=" * 70)
        
        total_files = 0
        files_with_methods = 0
        
        for py_file in self.project_root.rglob("*.py"):
            # Skip unwanted directories
            if any(skip in str(py_file) for skip in SKIP_DIRS):
                continue
            if py_file.name in SKIP_FILES:
                continue
            
            total_files += 1
            methods = self.scan_file_for_methods(py_file)
            
            if methods:
                files_with_methods += 1
                for method_name, line_num, line_content in methods:
                    # Analyze usage pattern
                    usage = self.analyze_usage_pattern(py_file, line_num, line_content, method_name)
                    self.used_methods[method_name].append(usage)
        
        print(f"\n📊 Scan Statistics:")
        print(f"   Total Python files: {total_files}")
        print(f"   Files with DB calls: {files_with_methods}")
        print(f"   Unique DB methods called: {len(self.used_methods)}")
    
    def check_method_existence(self):
        """Check if used methods exist in crud_operations.py"""
        print("\n" + "=" * 70)
        print("🔍 CHECKING METHOD EXISTENCE")
        print("=" * 70)
        
        self.crud_methods = self.get_crud_methods()
        
        missing_methods = []
        existing_methods = []
        
        for method in self.used_methods.keys():
            if method in self.crud_methods:
                existing_methods.append(method)
            else:
                missing_methods.append(method)
        
        print(f"\n✅ Existing methods: {len(existing_methods)}")
        print(f"❌ Missing methods: {len(missing_methods)}")
        
        if missing_methods:
            print("\n⚠️ METHODS CALLED IN CODE BUT MISSING IN crud_operations.py:")
            for method in sorted(missing_methods)[:20]:  # Limit to 20
                print(f"   - {method}")
                # Show where it's used
                for usage in self.used_methods[method][:2]:
                    print(f"       Called in: {usage['file']}:{usage['line']}")
            if len(missing_methods) > 20:
                print(f"   ... and {len(missing_methods) - 20} more")
        
        return missing_methods, existing_methods
    
    def analyze_return_type_issues(self):
        """Analyze potential return type mismatches"""
        print("\n" + "=" * 70)
        print("🔍 ANALYZING RETURN TYPE ISSUES")
        print("=" * 70)
        
        issues = []
        
        for method_name, usages in self.used_methods.items():
            for usage in usages:
                if usage.get('needs_fix'):
                    # Check if this method should return tuple
                    if method_name in TUPLE_METHODS:
                        issues.append({
                            'method': method_name,
                            'file': usage['file'],
                            'line': usage['line'],
                            'code': usage['code'],
                            'issue': 'Tuple indexing used - method should return tuple',
                            'fix': f"Modify {method_name}() to return tuple, or change code to use dict access"
                        })
                    elif method_name in DICT_METHODS:
                        issues.append({
                            'method': method_name,
                            'file': usage['file'],
                            'line': usage['line'],
                            'code': usage['code'],
                            'issue': 'Tuple indexing used on dict method',
                            'fix': f"Change line to use .get() or ['key'] instead of [index]"
                        })
                    else:
                        issues.append({
                            'method': method_name,
                            'file': usage['file'],
                            'line': usage['line'],
                            'code': usage['code'],
                            'issue': f'Tuple indexing used on {method_name}()',
                            'fix': 'Verify return type and adjust access method'
                        })
        
        print(f"\n📋 Found {len(issues)} potential issues")
        
        if issues:
            print("\n⚠️ ISSUES DETECTED:")
            for issue in issues[:20]:  # Limit output
                print(f"\n   📄 {issue['file']}:{issue['line']}")
                print(f"      Method: {issue['method']}()")
                print(f"      Code: {issue['code'][:80]}")
                print(f"      Issue: {issue['issue']}")
                print(f"      Fix: {issue['fix']}")
            
            if len(issues) > 20:
                print(f"\n   ... and {len(issues) - 20} more issues")
        
        return issues
    
    def generate_report(self):
        """Generate comprehensive report"""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE REPORT")
        print("=" * 70)
        
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("DATABASE METHOD USAGE REPORT")
        report_lines.append("=" * 70)
        report_lines.append("")
        
        # Summary
        report_lines.append(f"Total methods used in project: {len(self.used_methods)}")
        report_lines.append(f"Methods found in crud_operations.py: {len(self.crud_methods)}")
        report_lines.append("")
        
        # Missing methods
        missing = set(self.used_methods.keys()) - self.crud_methods
        if missing:
            report_lines.append("❌ MISSING METHODS (Need to be added):")
            for method in sorted(missing):
                report_lines.append(f"  - {method}")
                for usage in self.used_methods[method][:2]:
                    report_lines.append(f"      Used in: {usage['file']}:{usage['line']}")
            report_lines.append("")
        
        # Methods that need fix
        report_lines.append("🔧 METHODS THAT NEED ATTENTION:")
        for method_name, usages in self.used_methods.items():
            tuple_index_usage = [u for u in usages if u.get('needs_fix')]
            if tuple_index_usage:
                report_lines.append(f"\n  📌 {method_name}() - {len(tuple_index_usage)} tuple indexing usage(s)")
                for usage in tuple_index_usage[:3]:
                    report_lines.append(f"      {usage['file']}:{usage['line']}")
                    report_lines.append(f"      Code: {usage['code']}")
                    if method_name in DICT_METHODS:
                        report_lines.append(f"      FIX: Change to dict access (.get() or ['key'])")
                    elif method_name in TUPLE_METHODS:
                        report_lines.append(f"      FIX: Make {method_name}() return tuple")
        
        # Save report
        report_path = self.project_root / "data" / "db_methods_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        return report_lines
    
    def run(self):
        """Run complete scan"""
        self.scan_project()
        missing, existing = self.check_method_existence()
        issues = self.analyze_return_type_issues()
        self.generate_report()
        
        # Summary
        print("\n" + "=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)
        print(f"   Methods used: {len(self.used_methods)}")
        print(f"   Methods in CRUD: {len(self.crud_methods)}")
        print(f"   Missing methods: {len(missing)}")
        print(f"   Potential issues: {len(issues)}")
        
        return {
            'used_methods': self.used_methods,
            'crud_methods': self.crud_methods,
            'missing_methods': missing,
            'issues': issues
        }


def main():
    scanner = DatabaseMethodScanner(".")
    results = scanner.run()
    
    # Print quick fixes for common issues
    print("\n" + "=" * 70)
    print("💡 QUICK FIXES FOR COMMON ISSUES")
    print("=" * 70)
    print("""
    1. For tuple indexing errors (s[2], row[0], etc.):
       - If method should return dict: Change code to use .get('key')
       - If method should return tuple: Modify crud_operations.py to return tuple
    
    2. For missing methods:
       - Add the method to crud_operations.py
       - Or change the calling code to use existing method
    
    3. For return type mismatches:
       - Ensure get_all_subscriptions() returns tuple (for s[2] access)
       - Ensure get_all_users() returns tuple (for user[0] access)
       - Ensure get_all_companies() returns tuple (for company[0] access)
    """)


if __name__ == "__main__":
    main()