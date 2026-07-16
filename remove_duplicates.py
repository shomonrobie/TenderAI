"""
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
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Methods to remove
    methods_to_remove = {
        'assign_team_member', 'create_tender', 'create_tender_copy', 
        'delete_tender', 'get_all_users', 'get_company_tenders', 
        'get_competitor_master_list', 'get_tender_by_id', 'get_tender_team',
        'get_user_by_id', 'update_competitor_bid', 'update_competitor_stats_from_bid',
        'update_tender', 'update_tender_lock_status'
    }
    
    # Remove the methods
    modified_content = content
    removed_count = 0
    
    for method in methods_to_remove:
        # Pattern to match method definition with its entire body
        # This handles methods with docstrings, decorators, and nested code
        pattern = rf'(?m)^\s*def\s+{method}\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:\n(?:[^\n]|(?:\n(?!\S)))*)+'
        
        # Check if method exists
        if re.search(pattern, modified_content):
            # Remove the method
            modified_content = re.sub(pattern, '', modified_content)
            removed_count += 1
            print(f"✅ Removed method: {method}")
        else:
            # Try alternative pattern - might have decorators
            alt_pattern = rf'(?m)^(\s*@\w+\s*\n)*\s*def\s+{method}\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:\n(?:[^\n]|(?:\n(?!\S)))*)+'
            if re.search(alt_pattern, modified_content):
                modified_content = re.sub(alt_pattern, '', modified_content)
                removed_count += 1
                print(f"✅ Removed method (with decorators): {method}")
            else:
                print(f"⚠️ Method not found: {method}")
    
    # Clean up extra blank lines (more than 2 consecutive)
    modified_content = re.sub(r'\n{3,}', '\n\n', modified_content)
    
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
                "\n" + import_line + 
                modified_content[insert_pos:]
            )
            print(f"✅ Added import: {import_line}")
    
    # Also ensure the class inherits from TenderCRUD
    class_pattern = r'class\s+UnifiedDatabaseManager\s*\(([^)]*)\)'
    match = re.search(class_pattern, modified_content)
    if match:
        current_parents = match.group(1).strip()
        if 'TenderCRUD' not in current_parents:
            # Clean up current parents
            parents_list = [p.strip() for p in current_parents.split(',') if p.strip()]
            if 'TenderCRUD' not in parents_list:
                parents_list.insert(0, 'TenderCRUD')
                new_parents = ', '.join(parents_list)
                modified_content = re.sub(class_pattern, f'class UnifiedDatabaseManager({new_parents})', modified_content)
                print(f"✅ Added TenderCRUD to class inheritance")
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"\n✅ Removed {removed_count} duplicate methods from {file_path}")
    return True


if __name__ == "__main__":
    print("="*80)
    print("🔄 Removing duplicate methods from crud_operations.py")
    print("="*80)
    remove_duplicate_methods()
    print("\n✅ Done!")