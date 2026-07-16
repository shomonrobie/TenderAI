# migrations/copy_missing_methods.py
"""
Automatically copy missing methods from old db_manager.py files to a new file
"""

import re
import ast
from pathlib import Path
from typing import Set, Dict, List, Optional

# Configuration
TEMP_FOLDER = Path("database/temp")
OUTPUT_FILE = Path("database/missing_methods_to_add.py")

# Methods that are missing (from scan)
MISSING_METHODS = {
    'add_lged_chapter', 'add_milestone', 'add_pwd_chapter', 'assign_team_member',
    'clear_lged_version_data', 'clear_pwd_version_data', 'create_tender',
    'execute_query', 'get_company_tenders', 'get_knowledge_analytics',
    'get_tender_milestones', 'get_tender_team', 'get_version_history',
    'init_chapters_tables', 'init_lged_tables', 'init_pwd_hierarchical_tables',
    'save_hierarchy', 'update_company_subscription', 'update_competitor_master',
    'update_historical_tender_schema', 'update_lged_chapter_section',
    'update_lged_hierarchy', 'update_role_permissions_for_rates',
    'update_tender_lock_status', 'get_pwd_stats', 'search_pwd_items',
    'get_lged_sections_by_chapter', 'migrate_lged_tables_for_parent_types'
}


class MethodExtractor:
    def __init__(self, temp_folder: Path):
        self.temp_folder = temp_folder
        self.found_methods: Dict[str, Dict] = {}
        
    def extract_method_from_file(self, file_path: Path, method_name: str) -> Optional[str]:
        """Extract a specific method from a file"""
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to find method definition
        # Matches 'def method_name(self' and captures until next 'def' at same indent level
        pattern = rf'(def {method_name}\(self[^)]*\).*?)(?=\n    def |\nclass |\Z)'
        
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try with @staticmethod
        pattern_static = rf'(@staticmethod\s*\n\s*def {method_name}\([^)]*\).*?)(?=\n    def |\nclass |\Z)'
        match_static = re.search(pattern_static, content, re.DOTALL)
        if match_static:
            return match_static.group(1).strip()
        
        # Try with @classmethod
        pattern_class = rf'(@classmethod\s*\n\s*def {method_name}\(cls[^)]*\).*?)(?=\n    def |\nclass |\Z)'
        match_class = re.search(pattern_class, content, re.DOTALL)
        if match_class:
            return match_class.group(1).strip()
        
        return None
    
    def find_method_in_temp_files(self, method_name: str) -> Optional[tuple]:
        """Search for method in all temp db_manager files"""
        temp_files = list(self.temp_folder.glob("*db_manager*.py"))
        
        for file_path in temp_files:
            method_code = self.extract_method_from_file(file_path, method_name)
            if method_code:
                return (file_path.name, method_code)
        
        return None
    
    def extract_all_missing_methods(self) -> Dict[str, Dict]:
        """Extract all missing methods from temp files"""
        print("=" * 70)
        print("🔍 EXTRACTING MISSING METHODS FROM TEMP FILES")
        print("=" * 70)
        print(f"Looking in: {self.temp_folder}")
        print(f"Methods to find: {len(MISSING_METHODS)}\n")
        
        found = 0
        not_found = []
        
        for method_name in MISSING_METHODS:
            result = self.find_method_in_temp_files(method_name)
            if result:
                source_file, method_code = result
                self.found_methods[method_name] = {
                    'source': source_file,
                    'code': method_code
                }
                found += 1
                print(f"  ✅ Found: {method_name} (in {source_file})")
            else:
                not_found.append(method_name)
                print(f"  ❌ Not found: {method_name}")
        
        print(f"\n📊 Results:")
        print(f"   Found: {found}/{len(MISSING_METHODS)}")
        print(f"   Not found: {len(not_found)}")
        
        if not_found:
            print(f"\n⚠️ Methods not found in temp files:")
            for m in not_found:
                print(f"   - {m}")
        
        return self.found_methods
    
    def generate_refactored_code(self, method_code: str, method_name: str) -> str:
        """Refactor old method code to use new connection pattern"""
        # Replace old connection pattern with new one
        # Old: conn = self.get_connection()
        # New: with self.get_connection() as conn:
        
        # This is complex - we'll add TODOs for manual refactoring
        return f"""
    # TODO: Refactor this method for unified DB
    # Source: {self.found_methods[method_name]['source']}
    {method_code}
    
    # REFACTORING NOTES:
    # 1. Change 'conn = self.get_connection()' to 'with self.get_connection() as conn:'
    # 2. Change 'cursor = conn.cursor()' to 'cursor = self.db_conn.get_cursor(conn)'
    # 3. Change 'row[0]' to 'row.get('column_name')'
    # 4. Remove explicit 'conn.close()' (context manager handles it)
    """
    
    def write_output_file(self):
        """Write all found methods to output file"""
        if not self.found_methods:
            print("\n⚠️ No methods found to write")
            return
        
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('"""\n')
            f.write('MISSING METHODS TO ADD TO crud_operations.py\n')
            f.write('Auto-generated from old db_manager.py files\n')
            f.write('Generated by: migrations/copy_missing_methods.py\n')
            f.write('"""\n\n')
            f.write('import logging\n')
            f.write('from typing import Optional, Dict, List, Any\n')
            f.write('from datetime import datetime, timedelta\n')
            f.write('import json\n\n')
            f.write('logger = logging.getLogger(__name__)\n\n\n')
            
            for method_name, method_info in sorted(self.found_methods.items()):
                f.write(f'# =========================================================\n')
                f.write(f'# METHOD: {method_name}\n')
                f.write(f'# Source: {method_info["source"]}\n')
                f.write(f'# TODO: Refactor for unified database\n')
                f.write(f'# =========================================================\n')
                f.write(self.generate_refactored_code(method_info['code'], method_name))
                f.write('\n\n')
        
        print(f"\n✅ Output written to: {OUTPUT_FILE}")
        print(f"   Total methods: {len(self.found_methods)}")
        print(f"\n📝 Next steps:")
        print(f"   1. Review {OUTPUT_FILE}")
        print(f"   2. Manually refactor each method for unified DB")
        print(f"   3. Copy refactored methods to crud_operations.py")


class SimpleMethodCopier:
    """Simpler approach - just copy the original methods without refactoring"""
    
    def __init__(self, temp_folder: Path):
        self.temp_folder = temp_folder
        self.methods = {}
    
    def find_all_methods_in_file(self, file_path: Path) -> Dict[str, str]:
        """Extract ALL methods from a file"""
        methods = {}
        
        if not file_path.exists():
            return methods
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all method definitions
        pattern = r'(def (\w+)\(self[^)]*\).*?)(?=\n    def |\nclass |\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for method_code, method_name in matches:
            methods[method_name] = method_code.strip()
        
        return methods
    
    def copy_all_methods(self) -> Dict[str, Dict]:
        """Copy all methods from all temp files"""
        print("=" * 70)
        print("📋 COPYING ALL METHODS FROM TEMP FILES")
        print("=" * 70)
        
        temp_files = list(self.temp_folder.glob("*db_manager*.py"))
        
        for file_path in temp_files:
            print(f"\n📄 Reading: {file_path.name}")
            methods = self.find_all_methods_in_file(file_path)
            print(f"   Found {len(methods)} methods")
            
            for method_name, method_code in methods.items():
                if method_name not in self.methods:
                    self.methods[method_name] = {
                        'source': file_path.name,
                        'code': method_code
                    }
        
        print(f"\n📊 Total unique methods collected: {len(self.methods)}")
        return self.methods
    
    def write_all_methods(self, output_path: Path):
        """Write all methods to a file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('"""\n')
            f.write('ALL METHODS FROM OLD DB_MANAGER.PY FILES\n')
            f.write(f'Total methods: {len(self.methods)}\n')
            f.write('Generated by: migrations/copy_missing_methods.py\n')
            f.write('"""\n\n')
            
            for method_name, method_info in sorted(self.methods.items()):
                f.write(f'\n# =========================================================\n')
                f.write(f'# {method_name} (from {method_info["source"]})\n')
                f.write(f'# =========================================================\n')
                f.write(method_info['code'])
                f.write('\n')
        
        print(f"\n✅ All methods written to: {output_path}")
        return output_path


def main():
    print("\n" + "=" * 70)
    print("🔧 MISSING METHODS COPIER")
    print("=" * 70)
    
    # Option 1: Copy only missing methods (recommended)
    print("\n📌 OPTION 1: Copy only missing methods (28 methods)")
    extractor = MethodExtractor(TEMP_FOLDER)
    extractor.extract_all_missing_methods()
    extractor.write_output_file()
    
    # Option 2: Copy ALL methods for reference (optional)
    print("\n" + "=" * 70)
    print("📌 OPTION 2: Copy ALL methods for reference")
    copier = SimpleMethodCopier(TEMP_FOLDER)
    copier.copy_all_methods()
    copier.write_all_methods(Path("database/all_old_methods_reference.py"))
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)
    print("""
    Files created:
      1. database/missing_methods_to_add.py - 28 missing methods (needs refactoring)
      2. database/all_old_methods_reference.py - ALL methods for reference
    
    Next steps:
      1. Review missing_methods_to_add.py
      2. Refactor each method for unified DB:
         - Change connection pattern
         - Update row access from tuple to dict
      3. Copy refactored methods to crud_operations.py
    """)


if __name__ == "__main__":
    main()