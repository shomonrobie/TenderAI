# code_helper/restore_crud.py
"""
Restore crud_operations.py from latest backup
"""

import shutil
from pathlib import Path


def restore_crud():
    """Restore from latest backup"""
    
    latest_path = Path("database/crud_operations_backup_latest.py")
    
    if not latest_path.exists():
        print(f"❌ Latest backup not found: {latest_path}")
        return
    
    crud_path = Path("database/crud_operations.py")
    
    # Restore
    shutil.copy2(latest_path, crud_path)
    print(f"✅ Restored from: {latest_path}")
    print(f"✅ Restored to: {crud_path}")


if __name__ == "__main__":
    print("=" * 70)
    print("🔄 RESTORING crud_operations.py FROM BACKUP")
    print("=" * 70)
    
    response = input("\n⚠️  This will overwrite crud_operations.py! Continue? (y/N): ")
    if response.lower() == 'y':
        restore_crud()
        print("\n✅ Restore complete!")
    else:
        print("❌ Cancelled")