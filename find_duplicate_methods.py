"""
find_duplicate_methods.py
Script to find and remove duplicate methods from crud_operations.py
that have been moved to crud_tender.py
"""

import ast
import os
from pathlib import Path
from typing import Set, List, Dict, Tuple
import re


class MethodAnalyzer:
    """Analyze and find duplicate methods between two Python files"""
    
    def __init__(self, crud_operations_path: str, crud_tender_path: str):
        self.crud_operations_path = Path(crud_operations_path)
        self.crud_tender_path = Path(crud_tender_path)
        
    def extract_method_names(self, file_path: Path) -> Set[str]:
        """Extract all method names from a Python file"""
        method_names = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file
            tree = ast.parse(content)
            
            # Find all class definitions and their methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_names.add(item.name)
                elif isinstance(node, ast.FunctionDef):
                    # Top-level functions
                    if node.name not in ['__init__', '__new__']:
                        method_names.add(node.name)
        
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
        
        return method_names
    
    def find_duplicate_methods(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """Find duplicate methods between the two files"""
        print("🔍 Analyzing files for duplicate methods...")
        
        # Extract method names from both files
        methods_in_operations = self.extract_method_names(self.crud_operations_path)
        methods_in_tender = self.extract_method_names(self.crud_tender_path)
        
        print(f"📊 Found {len(methods_in_operations)} methods in crud_operations.py")
        print(f"📊 Found {len(methods_in_tender)} methods in crud_tender.py")
        
        # Find duplicates
        duplicates = methods_in_operations.intersection(methods_in_tender)
        
        # Methods only in operations (not in tender)
        only_in_operations = methods_in_operations - methods_in_tender
        
        # Methods only in tender (not in operations)
        only_in_tender = methods_in_tender - methods_in_operations
        
        # Filter out common methods that should remain
        keep_methods = {
            '__init__', '__new__', 'query', 'query_one', 'execute', 
            'execute_many', 'get_connection', 'get_table_columns', 
            'table_exists', 'is_supabase', 'get_db_type'
        }
        
        # Remove keep_methods from duplicates
        duplicates_to_remove = duplicates - keep_methods
        
        return duplicates_to_remove, only_in_operations, only_in_tender
    
    def generate_removal_report(self, duplicates: Set[str]) -> None:
        """Generate a report of methods to remove"""
        print("\n" + "="*80)
        print("📋 DUPLICATE METHODS TO REMOVE FROM crud_operations.py")
        print("="*80)
        
        if not duplicates:
            print("✅ No duplicate methods found!")
            return
        
        print(f"Found {len(duplicates)} duplicate methods that should be removed:\n")
        
        # Sort alphabetically for better readability
        for method in sorted(duplicates):
            print(f"  ❌ def {method}()")
        
        print("\n" + "="*80)
        print(f"Total: {len(duplicates)} methods to remove")
        print("="*80)
    
    def generate_import_statement(self) -> str:
        """Generate import statement for the tender module"""
        return "from database.crud_tender import TenderCRUD"
    
    def generate_removal_script(self, duplicates: Set[str], output_file: str = "remove_duplicates.py"):
        """Generate a Python script to remove duplicate methods"""
        
        script_content = f''''"""
remove_duplicates.py
Script to remove duplicate methods from crud_operations.py
Generated automatically by find_duplicate_methods.py
"""

import re
import os
from pathlib import Path


def remove_duplicate_methods():
    """Remove duplicate methods from crud_operations.py"""
    
    file_path = Path("database/crud_operations.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {{file_path}}")
        return False
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Methods to remove
    methods_to_remove = {duplicates}
    
    # Pattern to match method definitions
    # This matches def method_name(...
    pattern = r'(?m)^\s*def\s+(' + '|'.join(methods_to_remove) + r')\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:\n(?:[^\n]|(?:\n(?!\S)))*)+'
    
    # Remove the methods
    modified_content = content
    removed_count = 0
    
    for method in methods_to_remove:
        # Pattern for this specific method
        method_pattern = rf'(?m)^\s*def\s+{method}\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:\n(?:[^\n]|(?:\n(?!\S)))*)+'
        
        # Check if method exists
        if re.search(method_pattern, modified_content):
            # Remove the method
            modified_content = re.sub(method_pattern, '', modified_content)
            removed_count += 1
            print(f"✅ Removed method: {{method}}")
        else:
            print(f"⚠️ Method not found: {{method}}")
    
    # Add import for TenderCRUD if not already present
    import_line = "from database.crud_tender import TenderCRUD"
    if import_line not in modified_content:
        # Find the last import statement
        import_pattern = r'(?m)^(from|import)\s+\S+.*$'
        imports = list(re.finditer(import_pattern, modified_content))
        
        if imports:
            last_import = imports[-1]
            insert_pos = last_import.end()
            modified_content = (
                modified_content[:insert_pos] + 
                "\\n" + import_line + 
                modified_content[insert_pos:]
            )
            print(f"✅ Added import: {{import_line}}")
    
    # Also ensure the class inherits from TenderCRUD
    class_pattern = r'class\s+UnifiedDatabaseManager\s*\(([^)]*)\)'
    match = re.search(class_pattern, modified_content)
    if match:
        current_parents = match.group(1).strip()
        if 'TenderCRUD' not in current_parents:
            new_parents = f"TenderCRUD, {current_parents}" if current_parents else "TenderCRUD"
            modified_content = re.sub(class_pattern, f'class UnifiedDatabaseManager({new_parents})', modified_content)
            print(f"✅ Added TenderCRUD to class inheritance")
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"\\n✅ Removed {{removed_count}} duplicate methods from {{file_path}}")
    return True


if __name__ == "__main__":
    print("="*80)
    print("🔄 Removing duplicate methods from crud_operations.py")
    print("="*80)
    remove_duplicate_methods()
    print("\\n✅ Done!")
"""'''
        
        # Write the script
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"\n📝 Generated removal script: {output_file}")
        print(f"   Run it with: python {output_file}")
    
    def create_backup(self) -> bool:
        """Create a backup of crud_operations.py"""
        backup_path = self.crud_operations_path.with_suffix('.py.bak')
        try:
            import shutil
            shutil.copy2(self.crud_operations_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False


def main():
    """Main function to run the duplicate finder"""
    
    print("="*80)
    print("🔍 DUPLICATE METHOD FINDER")
    print("="*80)
    
    # Paths to the files
    crud_operations_path = "database/crud_operations.py"
    crud_tender_path = "database/crud_tender.py"
    
    # Check if files exist
    if not os.path.exists(crud_operations_path):
        print(f"❌ File not found: {crud_operations_path}")
        return
    
    if not os.path.exists(crud_tender_path):
        print(f"❌ File not found: {crud_tender_path}")
        return
    
    # Initialize analyzer
    analyzer = MethodAnalyzer(crud_operations_path, crud_tender_path)
    
    # Find duplicates
    duplicates, only_in_operations, only_in_tender = analyzer.find_duplicate_methods()
    
    # Generate report
    analyzer.generate_removal_report(duplicates)
    
    # Show methods only in operations (potential missing methods)
    if only_in_operations:
        print("\n" + "="*80)
        print("📊 METHODS ONLY IN crud_operations.py (NOT in crud_tender.py)")
        print("="*80)
        print("These methods are only in crud_operations.py and may need to be moved:\n")
        for method in sorted(only_in_operations):
            print(f"  🔄 def {method}()")
        print(f"\nTotal: {len(only_in_operations)} methods")
    
    # Show methods only in tender (new methods)
    if only_in_tender:
        print("\n" + "="*80)
        print("📊 METHODS ONLY IN crud_tender.py (NOT in crud_operations.py)")
        print("="*80)
        print("These methods are new in crud_tender.py:\n")
        for method in sorted(only_in_tender):
            print(f"  ✨ def {method}()")
        print(f"\nTotal: {len(only_in_tender)} methods")
    
    # Ask user if they want to remove duplicates
    if duplicates:
        print("\n" + "="*80)
        response = input("🔄 Do you want to remove these duplicate methods? (y/n): ")
        
        if response.lower() == 'y':
            # Create backup
            print("\n📁 Creating backup...")
            analyzer.create_backup()
            
            # Generate removal script
            analyzer.generate_removal_script(duplicates)
            
            print("\n⚠️ Please review the generated script before running it!")
            print("   The script will: ")
            print("   1. Remove duplicate methods from crud_operations.py")
            print("   2. Add import for TenderCRUD")
            print("   3. Update class inheritance")
            print("\n📝 To run the script: python remove_duplicates.py")
        else:
            print("\n❌ No changes made.")
    else:
        print("\n✅ No duplicates found - your code is clean!")


if __name__ == "__main__":
    main()