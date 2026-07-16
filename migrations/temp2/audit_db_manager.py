# migrations/audit_db_manager.py
"""Audit Unified Database Manager to identify all functions and missing ones"""

import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Set
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_all_functions_from_module(module_name: str, class_name: str = None):
    """Get all public methods from a module/class"""
    
    try:
        module = importlib.import_module(module_name)
        
        if class_name:
            cls = getattr(module, class_name)
            # Get all methods (excluding private)
            methods = [name for name, _ in inspect.getmembers(cls, inspect.isfunction) 
                      if not name.startswith('_')]
            return set(methods)
        else:
            # Get all functions in module
            functions = [name for name, obj in inspect.getmembers(module, inspect.isfunction)
                        if not name.startswith('_')]
            return set(functions)
    except Exception as e:
        print(f"Error loading {module_name}: {e}")
        return set()

def get_methods_from_py_file(file_path: Path) -> Set[str]:
    """Extract method names from a Python file"""
    methods = set()
    
    if not file_path.exists():
        return methods
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find all method definitions (def method_name(self,
        pattern = r'def\s+(\w+)\(self'
        found = re.findall(pattern, content)
        methods.update(found)
    
    return methods


def get_all_methods_from_instance(instance):
    """Get all callable methods from an instance"""
    methods = []
    for name in dir(instance):
        if not name.startswith('_'):
            try:
                attr = getattr(instance, name)
                if callable(attr):
                    methods.append(name)
            except:
                pass
    return set(methods)


def compare_methods(original_methods: Set[str], new_methods: Set[str], name: str):
    """Compare two sets of methods"""
    
    missing = original_methods - new_methods
    extra = new_methods - original_methods
    common = original_methods & new_methods
    
    print(f"\n{'='*70}")
    print(f"📊 {name} COMPARISON")
    print(f"{'='*70}")
    print(f"Original methods: {len(original_methods)}")
    print(f"New methods:      {len(new_methods)}")
    print(f"Common methods:   {len(common)}")
    print(f"Missing methods:  {len(missing)}")
    print(f"Extra methods:    {len(extra)}")
    
    if missing:
        print(f"\n❌ MISSING METHODS ({len(missing)}):")
        for method in sorted(missing):
            print(f"   - {method}")
    
    if extra:
        print(f"\n✨ EXTRA METHODS IN NEW ({len(extra)}):")
        for method in sorted(extra):
            print(f"   - {method}")
    
    return missing, extra, common


def get_original_db_methods():
    """Get methods from original db_manager.py and enhanced_db_manager.py"""
    
    original_methods = set()
    
    # Try to load original db_manager
    try:
        old_db_path = Path(__file__).parent.parent / "database" / "db_manager.py"
        if old_db_path.exists():
            print(f"Found original db_manager.py at {old_db_path}")
            # Parse the file for method definitions
            with open(old_db_path, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                methods = re.findall(r'def\s+(\w+)\(self', content)
                original_methods.update(methods)
                print(f"  Found {len(methods)} methods in db_manager.py")
    except Exception as e:
        print(f"Could not parse db_manager.py: {e}")
    
    # Try to load original enhanced_db_manager
    try:
        enhanced_path = Path(__file__).parent.parent / "database" / "enhanced_db_manager.py"
        if enhanced_path.exists():
            print(f"Found enhanced_db_manager.py at {enhanced_path}")
            with open(enhanced_path, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                methods = re.findall(r'def\s+(\w+)\(self', content)
                original_methods.update(methods)
                print(f"  Found {len(methods)} methods in enhanced_db_manager.py")
    except Exception as e:
        print(f"Could not parse enhanced_db_manager.py: {e}")
    
    return original_methods


def scan_project_for_db_calls():
    """Scan project files for database method calls"""
    
    project_root = Path(__file__).parent.parent
    db_calls = set()
    
    # Patterns to look for
    patterns = [
        r'db\.(\w+)\(',
        r'db_manager\.(\w+)\(',
        r'unified_db_manager\.(\w+)\(',
        r'self\.(\w+)\(',
    ]
    
    import re
    
    for py_file in project_root.rglob("*.py"):
        if 'migrations' in str(py_file) or 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    db_calls.update(matches)
        except:
            pass
    
    # Filter out common Python builtins
    builtins = {'__init__', '__str__', '__repr__', 'format', 'join', 'split', 'strip', 'len', 'str', 'int', 'dict', 'list', 'set', 'tuple'}
    db_calls = {call for call in db_calls if call not in builtins and not call.startswith('_')}
    
    return db_calls


def run_audit():
    """Run complete audit"""
    
    print("="*70)
    print("🔍 UNIFIED DATABASE MANAGER AUDIT")
    print("="*70)
    
    # 1. Get methods from current UnifiedDatabaseManager
    print("\n📖 Loading current UnifiedDatabaseManager...")
    from database.unified_db_manager import UnifiedDatabaseManager
    db_instance = UnifiedDatabaseManager()
    current_methods = get_all_methods_from_instance(db_instance)
    print(f"   Found {len(current_methods)} methods in UnifiedDatabaseManager")
    
    # 2. Get methods from original db_manager files in temp folder
    print("\n📖 Analyzing original db_manager files in database/temp/...")
    
    original_methods = set()
    
    # Look for files in database/temp/
    temp_dir = Path(__file__).parent.parent / "database" / "temp"
    
    if temp_dir.exists():
        for py_file in temp_dir.glob("*.py"):
            if 'db_manager' in py_file.name.lower():
                methods = get_methods_from_py_file(py_file)
                original_methods.update(methods)
                print(f"   Found {len(methods)} methods in {py_file.name}")
    else:
        print(f"   ⚠️ Temp folder not found at {temp_dir}")
        
        # Also check for original files in database/ folder
        db_dir = Path(__file__).parent.parent / "database"
        for py_file in db_dir.glob("*db_manager*.py"):
            if 'unified' not in py_file.name.lower():
                methods = get_methods_from_py_file(py_file)
                original_methods.update(methods)
                print(f"   Found {len(methods)} methods in {py_file.name}")
    
    print(f"   Total original methods: {len(original_methods)}")
    
    # 3. Compare
    missing = original_methods - current_methods
    extra = current_methods - original_methods
    common = original_methods & current_methods
    
    print(f"\n{'='*70}")
    print(f"📊 COMPARISON: ORIGINAL vs CURRENT")
    print(f"{'='*70}")
    print(f"Original methods: {len(original_methods)}")
    print(f"Current methods:  {len(current_methods)}")
    print(f"Common methods:   {len(common)}")
    print(f"Missing methods:  {len(missing)}")
    print(f"Extra methods:    {len(extra)}")
    
    if missing:
        print(f"\n❌ MISSING METHODS ({len(missing)}):")
        for method in sorted(missing)[:200]:
            print(f"   - {method}")
        if len(missing) > 200:
            print(f"   ... and {len(missing) - 50} more")
    
    if extra:
        print(f"\n✨ EXTRA METHODS IN NEW ({len(extra)}):")
        for method in sorted(extra):
            print(f"   - {method}")
    
    # 4. Scan project for actual usage
    print("\n📖 Scanning project for database method calls...")
    used_methods = scan_project_for_db_calls()
    print(f"   Found {len(used_methods)} unique method calls in project")
    
    # 5. Check which used methods are missing
    missing_used = used_methods - current_methods
    if missing_used:
        print(f"\n⚠️ CRITICAL: Methods called in code but missing from UnifiedDatabaseManager ({len(missing_used)}):")
        for method in sorted(missing_used)[:200]:
            print(f"   - {method}")
        if len(missing_used) > 200:
            print(f"   ... and {len(missing_used) - 200} more")
    
    # 6. Generate report file
    report_path = Path("data/audit_report.txt")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("UNIFIED DATABASE MANAGER AUDIT REPORT\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"CURRENT METHODS ({len(current_methods)}):\n")
        for m in sorted(current_methods):
            f.write(f"  ✅ {m}\n")
        
        f.write(f"\n\nORIGINAL METHODS ({len(original_methods)}):\n")
        for m in sorted(original_methods):
            f.write(f"  📦 {m}\n")
        
        f.write(f"\n\nMISSING METHODS ({len(missing)}):\n")
        for m in sorted(missing):
            f.write(f"  ❌ {m}\n")
        
        f.write(f"\n\nMETHODS CALLED IN PROJECT BUT MISSING ({len(missing_used)}):\n")
        for m in sorted(missing_used):
            f.write(f"  ⚠️ {m}\n")
    
    print(f"\n📄 Full report saved to: {report_path}")
    
    # 7. Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"✅ Implemented: {len(current_methods)} methods")
    print(f"📦 Original:    {len(original_methods)} methods")
    print(f"❌ Missing:     {len(missing)} methods")
    print(f"⚠️ Critical:    {len(missing_used)} methods called in code but missing")
    
    return {
        'current_methods': current_methods,
        'original_methods': original_methods,
        'missing_methods': missing,
        'extra_methods': extra,
        'used_methods_missing': missing_used
    }



def generate_method_template(method_name: str):
    """Generate a template for a missing method"""
    
    return f'''
    def {method_name}(self, *args, **kwargs):
        """TODO: Implement {method_name}"""
        # Delegate to crud or implement here
        return self.crud.{method_name}(*args, **kwargs)
'''


def create_missing_methods_file(missing_methods: List[str]):
    """Create a file with templates for missing methods"""
    
    file_path = Path("migrations/missing_methods_template.py")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("# Missing methods to add to UnifiedDatabaseManager\n")
        f.write("# Copy these methods into database/unified_db_manager.py\n\n")
        
        for method in sorted(missing_methods):
            f.write(f"    def {method}(self, *args, **kwargs):\n")
            f.write(f'        """TODO: Implement {method}"""\n')
            f.write(f"        return self.crud.{method}(*args, **kwargs)\n\n")
    
    print(f"\n📝 Template file created: {file_path}")
    print("   Copy the methods from this file into UnifiedDatabaseManager")


if __name__ == "__main__":
    result = run_audit()
    
    if result['missing_methods']:
        print("\n" + "="*70)
        response = input("Generate template file for missing methods? (y/N): ")
        if response.lower() == 'y':
            create_missing_methods_file(result['missing_methods'])