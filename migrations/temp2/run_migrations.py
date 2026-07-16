# migrations/run_migrations.py - COMPLETE FIXED VERSION

import sys
import os
from pathlib import Path
import logging
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.crud_operations import DatabaseCRUD
from migrations.v012_update_user_profile import MigrationV012
from migrations.v013_tenant_rate_management import MigrationV013
from migrations.v014_demo_data_framework import MigrationV014
from migrations.v015_archive_framework import MigrationV015
from migrations.v016_company_onboarding_wizard import MigrationV016
from migrations.v017_add_step_data_column import MigrationV017
from migrations.v018_add_custom_source_column import MigrationV018
from migrations.v019_add_version_id_to_boq import MigrationV019  # ✅ ADDED
from migrations.v020_rename_cost_levels import MigrationV020
from migrations.v022_company_config import MigrationV022
from migrations.v023_add_quick_boq import MigrationV023  # ✅ ADD THIS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self.db = DatabaseCRUD(db_path)
    
    # ========== v012 Migration ==========
    def run_migration_v012(self) -> bool:
        migration = MigrationV012(self.db)
        return migration.up()
    
    def rollback_migration_v012(self) -> bool:
        migration = MigrationV012(self.db)
        return migration.down()
    
    # ========== v013 Migration ==========
    def run_migration_v013(self) -> bool:
        migration = MigrationV013(self.db)
        return migration.up()
    
    def rollback_migration_v013(self) -> bool:
        migration = MigrationV013(self.db)
        return migration.down()
    
    # ========== v014 Migration ==========
    def run_migration_v014(self) -> bool:
        migration = MigrationV014(self.db)
        return migration.up()
    
    def rollback_migration_v014(self) -> bool:
        migration = MigrationV014(self.db)
        return migration.down()
    
    # ========== v015 Migration ==========
    def run_migration_v015(self) -> bool:
        migration = MigrationV015(self.db)
        return migration.up()
    
    def rollback_migration_v015(self) -> bool:
        migration = MigrationV015(self.db)
        return migration.down()
    
    # ========== v016 Migration ==========
    def run_migration_v016(self) -> bool:
        migration = MigrationV016(self.db)
        return migration.up()
    
    def rollback_migration_v016(self) -> bool:
        migration = MigrationV016(self.db)
        return migration.down()
    
    # ========== v017 Migration ==========
    def run_migration_v017(self) -> bool:
        migration = MigrationV017(self.db)
        return migration.up()
    
    def rollback_migration_v017(self) -> bool:
        migration = MigrationV017(self.db)
        return migration.down()
    
    # ========== v018 Migration ==========
    def run_migration_v018(self) -> bool:
        migration = MigrationV018(self.db)
        return migration.up()
    
    # ========== v019 Migration ==========
    def run_migration_v019(self) -> bool:
        """Run v019 migration - Add rate_book_id and version_id to boq_generation_history"""
        migration = MigrationV019(self.db)
        return migration.up()
    
    def run_migration_v020(self) -> bool:
        migration = MigrationV020(self.db)
        return migration.up()

    def rollback_migration_v018(self) -> bool:
        migration = MigrationV018(self.db)
        return migration.down()
    
    def run_migration_v022(self) -> bool:
        migration = MigrationV022(self.db)
        return migration.up()
    
    def run_migration_v023(self) -> bool:
        migration = MigrationV023(self.db)
        return migration.up()

    def rollback_migration_v022(self) -> bool:
        migration = MigrationV022(self.db)
        return migration.down()

    # ========== Run All Migrations ==========
    def run_all_migrations(self) -> bool:
        """Run all migrations in order"""
        migrations = [
            self.run_migration_v012,
            self.run_migration_v013,
            self.run_migration_v014,
            self.run_migration_v015,
            self.run_migration_v016,
            self.run_migration_v017,
            self.run_migration_v018,
            self.run_migration_v019,  # ✅ ADDED
            self.run_migration_v020,  # NEW
            self.run_migration_v022,  # ✅ ADDED
            self.run_migration_v023,  # ✅ ADDED

        ]
        
        success = True
        for migration in migrations:
            if not migration():
                success = False
                break
        
        if success:
            logger.info("✅ All migrations completed successfully!")
        else:
            logger.error("❌ Some migrations failed!")
        
        return success
    
    # ========== Migration Status ==========
    def get_migration_status(self) -> dict:
        """Get status of all migrations"""
        status = {
            'v012_update_user_profile': {
                'table_social_links': self.db.table_exists('social_links'),
                'table_activity_log': self.db.table_exists('user_activity_log'),
                'view_profile': self.db.table_exists('v_user_profile'),
                'columns_added': [
                    col for col in ['avatar_url', 'bio', 'location', 'website']
                    if self.db.column_exists('users', col)
                ],
                'is_migrated': self.db.table_exists('social_links')
            },
            'v013_tenant_rate_management': {
                'table_rate_books': self.db.table_exists('tenant_rate_books'),
                'table_rate_versions': self.db.table_exists('tenant_rate_versions'),
                'table_rate_items': self.db.table_exists('tenant_rate_items'),
                'table_pricing_levels': self.db.table_exists('tenant_pricing_levels'),
                'table_rate_audit': self.db.table_exists('tenant_rate_audit'),
                'is_migrated': self.db.table_exists('tenant_rate_books')
            },
            'v014_demo_data_framework': {
                'table_demo_log': self.db.table_exists('demo_data_generation_log'),
                'table_onboarding_status': self.db.table_exists('company_onboarding_status'),
                'columns_added': [
                    col for col in ['is_demo', 'environment_mode', 'data_source_type']
                    if self.db.column_exists('tenant_rate_books', col)
                ],
                'is_migrated': self.db.table_exists('demo_data_generation_log')
            },
            'v015_archive_framework': {
                'table_archive_records': self.db.table_exists('archive_records'),
                'table_archive_metadata': self.db.table_exists('archive_metadata'),
                'columns_added': [
                    col for col in ['is_archived', 'archived_at', 'archived_by']
                    if self.db.column_exists('tenant_rate_books', col)
                ],
                'is_migrated': self.db.table_exists('archive_records')
            },
            'v016_company_onboarding_wizard': {
                'table_wizard_sessions': self.db.table_exists('onboarding_wizard_sessions'),
                'table_cost_profiles': self.db.table_exists('company_cost_profiles'),
                'columns_added': [
                    col for col in ['onboarding_completed', 'onboarding_step']
                    if self.db.column_exists('users', col)
                ],
                'is_migrated': self.db.table_exists('onboarding_wizard_sessions')
            },
            'v017_add_step_data_column': {
                'column_step_data': self.db.column_exists('company_onboarding_status', 'step_data'),
                'is_migrated': self.db.column_exists('company_onboarding_status', 'step_data')
            },
            'v018_add_custom_source_column': {
                'column_custom_source': self.db.column_exists('tenant_rate_books', 'custom_source'),
                'column_version_notes': self.db.column_exists('tenant_rate_books', 'version_notes'),
                'is_migrated': self.db.column_exists('tenant_rate_books', 'custom_source')
            },
            'v019_add_version_id_to_boq': {
                'column_rate_book_id': self.db.column_exists('boq_generation_history', 'rate_book_id'),
                'column_version_id': self.db.column_exists('boq_generation_history', 'version_id'),
                'is_migrated': self.db.column_exists('boq_generation_history', 'rate_book_id')
            },
            'v020_cost_management': {
                'table_cost_profiles': self.db.table_exists('company_cost_profiles'),
                'table_cost_definitions': self.db.table_exists('cost_level_definitions'),
                'table_scenario_results': self.db.table_exists('cost_scenario_results'),
                'is_migrated': self.db.table_exists('company_cost_profiles')
            },
            'v022_company_config': {
                'table_company_config': self.db.table_exists('company_config'),
                'is_migrated': self.db.table_exists('company_config')
            },        
            
            'v023_add_is_quick_boq_to_boq': {
                'column_is_quick_boq': self.db.column_exists('boq_generation_history', 'is_quick_boq')
            },            
        }
        
        return status
    
    # ========== Individual Migration Runner ==========
    def run_specific_migration(self, version: str) -> bool:
        """Run a specific migration by version"""
        migration_map = {
            'v012': self.run_migration_v012,
            'v013': self.run_migration_v013,
            'v014': self.run_migration_v014,
            'v015': self.run_migration_v015,
            'v016': self.run_migration_v016,
            'v017': self.run_migration_v017,
            'v018': self.run_migration_v018,
            'v019': self.run_migration_v019,
            'v020': self.run_migration_v020,
        }
        
        if version not in migration_map:
            logger.error(f"❌ Unknown migration version: {version}")
            logger.info(f"Available versions: {', '.join(migration_map.keys())}")
            return False
        
        logger.info(f"▶️ Running migration {version}...")
        result = migration_map[version]()
        
        if result:
            logger.info(f"✅ Migration {version} completed successfully!")
        else:
            logger.error(f"❌ Migration {version} failed!")
        
        return result
    
    def rollback_specific_migration(self, version: str) -> bool:
        """Rollback a specific migration by version"""
        rollback_map = {
            'v012': self.rollback_migration_v012,
            'v013': self.rollback_migration_v013,
            'v014': self.rollback_migration_v014,
            'v015': self.rollback_migration_v015,
            'v016': self.rollback_migration_v016,
            'v017': self.rollback_migration_v017,
            'v018': self.rollback_migration_v018,
            'v019': self.rollback_migration_v019,
            'v020': self.rollback_migration_v020,
        }
        
        if version not in rollback_map:
            logger.error(f"❌ Unknown migration version: {version}")
            logger.info(f"Available versions: {', '.join(rollback_map.keys())}")
            return False
        
        logger.info(f"◀️ Rolling back migration {version}...")
        result = rollback_map[version]()
        
        if result:
            logger.info(f"✅ Rollback of {version} completed successfully!")
        else:
            logger.error(f"❌ Rollback of {version} failed!")
        
        return result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Database Migration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a specific migration
  python -m migrations.run_migrations up --version v018
  
  # Rollback a specific migration
  python -m migrations.run_migrations down --version v018
  
  # Run all migrations
  python -m migrations.run_migrations all
  
  # Check status
  python -m migrations.run_migrations status
  
  # Run v012 only
  python -m migrations.run_migrations up --version v012
        """
    )
    
    parser.add_argument(
        "command",
        choices=["up", "down", "status", "all"],
        help="Migration command: up (run migration), down (rollback migration), status (check status), all (run all migrations)"
    )
    
    parser.add_argument(
        "--version",
        default=None,
        help="Migration version to run/rollback (e.g., v012, v013, v018). If not specified, runs latest."
    )
    
    parser.add_argument(
        "--db-path",
        default="data/tender_system.db",
        help="Path to database file"
    )
    
    args = parser.parse_args()
    
    manager = MigrationManager(args.db_path)
    
    # ========== UP (Run Migration) ==========
    if args.command == "up":
        if args.version:
            # Run specific migration
            if manager.run_specific_migration(args.version):
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            # Run all migrations
            logger.info("▶️ Running all migrations...")
            if manager.run_all_migrations():
                sys.exit(0)
            else:
                sys.exit(1)
    
    # ========== DOWN (Rollback Migration) ==========
    elif args.command == "down":
        if args.version:
            # Rollback specific migration
            if manager.rollback_specific_migration(args.version):
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            # Rollback latest migration (v018)
            logger.info("◀️ Rolling back latest migration (v018)...")
            if manager.rollback_migration_v018():
                sys.exit(0)
            else:
                sys.exit(1)
    
    # ========== STATUS ==========
    elif args.command == "status":
        status = manager.get_migration_status()
        logger.info("📊 Migration Status:")
        logger.info("=" * 60)
        
        for name, info in status.items():
            logger.info(f"\n📦 {name}:")
            for key, value in info.items():
                if key == 'is_migrated':
                    status_icon = "✅" if value else "❌"
                    logger.info(f"    {status_icon} {key}: {value}")
                elif isinstance(value, bool):
                    status_icon = "✅" if value else "❌"
                    logger.info(f"    {status_icon} {key}: {value}")
                elif isinstance(value, list):
                    if value:
                        logger.info(f"    ✅ {key}: {', '.join(value)}")
                    else:
                        logger.info(f"    ❌ {key}: None")
                else:
                    logger.info(f"    - {key}: {value}")
        
        logger.info("\n" + "=" * 60)
        
        # Summary
        total_migrations = len(status)
        applied_migrations = sum(
            1 for s in status.values() 
            if s.get('is_migrated', False)
        )
        
        logger.info(f"📈 Summary: {applied_migrations}/{total_migrations} migrations applied")
        
        if applied_migrations < total_migrations:
            logger.info("⚠️ Some migrations are pending. Run 'python -m migrations.run_migrations up' to apply.")
    
    # ========== ALL ==========
    elif args.command == "all":
        logger.info("▶️ Running all migrations...")
        if manager.run_all_migrations():
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()