# code_helper/backup_crud.py
"""
Create a backup of crud_operations.py before making changes
"""

import shutil
from datetime import datetime
from pathlib import Path


def backup_crud_operations():
    """Create a backup of crud_operations.py"""
    
    crud_path = Path("database/crud_operations.py")
    
    if not crud_path.exists():
        print(f"❌ File not found: {crud_path}")
        return
    
    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"database/crud_operations_backup_{timestamp}.py")
    
    # Also keep a latest backup
    latest_path = Path("database/crud_operations_backup_latest.py")
    
    # Copy to timestamped backup
    shutil.copy2(crud_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Copy to latest backup
    shutil.copy2(crud_path, latest_path)
    print(f"✅ Latest backup created: {latest_path}")
    
    # Show backup info
    print(f"\n📊 Backup Info:")
    print(f"   Original: {crud_path} ({crud_path.stat().st_size} bytes)")
    print(f"   Backup: {backup_path} ({backup_path.stat().st_size} bytes)")
    
    return backup_path, latest_path


if __name__ == "__main__":
    print("=" * 70)
    print("📦 CREATING BACKUP OF crud_operations.py")
    print("=" * 70)
    
    backup_path, latest_path = backup_crud_operations()
    
    print("\n✅ Backup complete!")
    print(f"\n📁 To restore from backup:")
    print(f"   cp {latest_path} database/crud_operations.py")