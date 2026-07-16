# migrations/v013_tenant_rate_management.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV013:
    """Migration v013: Add tenant rate management tables"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v013: Tenant Rate Management")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create all tables
                self._create_tables(cursor)
                self._create_indexes(cursor)
                
                # Update RBAC permissions
                self._update_rbac_permissions(cursor)
                
                conn.commit()
                logger.info("✅ Migration v013 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v013 failed: {e}")
            return False
    
    def _create_tables(self, cursor):
        """Create all tenant rate management tables"""
        
        # 1. tenant_rate_books
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                tenant_type TEXT NOT NULL,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_version_id INTEGER,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_archived BOOLEAN DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_version_id) REFERENCES rate_versions(id) ON DELETE SET NULL
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_books")
        
        # 2. tenant_rate_versions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_book_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                version_name TEXT,
                effective_from DATE,
                effective_to DATE,
                is_current BOOLEAN DEFAULT 0,
                notes TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_book_id) REFERENCES tenant_rate_books(id) ON DELETE CASCADE,
                UNIQUE(rate_book_id, version_number)
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_versions")
        
        # 3. tenant_rate_items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_book_id INTEGER NOT NULL,
                master_reference_id INTEGER,
                master_reference_type TEXT,
                item_code TEXT NOT NULL,
                item_description TEXT NOT NULL,
                unit TEXT,
                is_custom BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_book_id) REFERENCES tenant_rate_books(id) ON DELETE CASCADE,
                UNIQUE(rate_book_id, item_code)
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_items")
        
        # 4. tenant_pricing_levels
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_pricing_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_version_id INTEGER NOT NULL,
                rate_item_id INTEGER NOT NULL,
                pricing_level TEXT NOT NULL,
                price REAL,
                currency TEXT DEFAULT 'BDT',
                notes TEXT,
                effective_from DATE,
                effective_to DATE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_version_id) REFERENCES tenant_rate_versions(id) ON DELETE CASCADE,
                FOREIGN KEY (rate_item_id) REFERENCES tenant_rate_items(id) ON DELETE CASCADE,
                UNIQUE(rate_version_id, rate_item_id, pricing_level)
            )
        """)
        logger.info("  ✅ Created table: tenant_pricing_levels")
        
        # 5. tenant_rate_audit
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_book_id INTEGER,
                rate_item_id INTEGER,
                pricing_level_id INTEGER,
                action TEXT NOT NULL,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_book_id) REFERENCES tenant_rate_books(id) ON DELETE CASCADE,
                FOREIGN KEY (rate_item_id) REFERENCES tenant_rate_items(id) ON DELETE CASCADE,
                FOREIGN KEY (pricing_level_id) REFERENCES tenant_pricing_levels(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_audit")
        
        # 6. tenant_rate_import_log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_import_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_book_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                import_type TEXT NOT NULL,
                total_records INTEGER,
                successful_records INTEGER,
                failed_records INTEGER,
                error_log TEXT,
                imported_by INTEGER,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_book_id) REFERENCES tenant_rate_books(id) ON DELETE CASCADE,
                FOREIGN KEY (imported_by) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_import_log")
        
        # 7. tenant_rate_export_log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_rate_export_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_book_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                export_type TEXT NOT NULL,
                total_records INTEGER,
                exported_by INTEGER,
                exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rate_book_id) REFERENCES tenant_rate_books(id) ON DELETE CASCADE,
                FOREIGN KEY (exported_by) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: tenant_rate_export_log")
    
    def _create_indexes(self, cursor):
        """Create performance indexes"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_trb_tenant ON tenant_rate_books(tenant_id, tenant_type)",
            "CREATE INDEX IF NOT EXISTS idx_trb_source ON tenant_rate_books(source_type, source_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_trb_active ON tenant_rate_books(is_active, is_archived)",
            
            "CREATE INDEX IF NOT EXISTS idx_trv_book ON tenant_rate_versions(rate_book_id, is_current)",
            "CREATE INDEX IF NOT EXISTS idx_trv_dates ON tenant_rate_versions(effective_from, effective_to)",
            
            "CREATE INDEX IF NOT EXISTS idx_tri_book ON tenant_rate_items(rate_book_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_tri_code ON tenant_rate_items(item_code)",
            "CREATE INDEX IF NOT EXISTS idx_tri_reference ON tenant_rate_items(master_reference_id, master_reference_type)",
            
            "CREATE INDEX IF NOT EXISTS idx_tpl_rate_item ON tenant_pricing_levels(rate_version_id, rate_item_id)",
            "CREATE INDEX IF NOT EXISTS idx_tpl_level ON tenant_pricing_levels(pricing_level)",
            
            "CREATE INDEX IF NOT EXISTS idx_tra_book ON tenant_rate_audit(rate_book_id)",
            "CREATE INDEX IF NOT EXISTS idx_tra_user ON tenant_rate_audit(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tra_action ON tenant_rate_audit(action)",
            "CREATE INDEX IF NOT EXISTS idx_tra_created ON tenant_rate_audit(created_at)",
        ]
        
        for idx in indexes:
            try:
                cursor.execute(idx)
                logger.info(f"  ✅ Created index: {idx.split('ON')[1].strip().split('(')[0]}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not create index: {e}")
    
    def _update_rbac_permissions(self, cursor):
        """Update role permissions for rate management"""
        
        # Check if permissions need updating
        cursor.execute("SELECT permissions FROM role_permissions WHERE role = 'system_admin'")
        result = cursor.fetchone()
        
        if result:
            import json
            permissions = json.loads(result[0])
            
            # Add rate management permissions
            permissions['manage_system_rates'] = True
            permissions['manage_tenant_rates'] = True
            
            cursor.execute(
                "UPDATE role_permissions SET permissions = ? WHERE role = 'system_admin'",
                (json.dumps(permissions),)
            )
            logger.info("  ✅ Updated system_admin permissions")
        
        # Add company_admin permissions
        cursor.execute("SELECT permissions FROM role_permissions WHERE role = 'company_admin'")
        result = cursor.fetchone()
        
        if result:
            import json
            permissions = json.loads(result[0])
            
            permissions['manage_tenant_rates'] = True
            
            cursor.execute(
                "UPDATE role_permissions SET permissions = ? WHERE role = 'company_admin'",
                (json.dumps(permissions),)
            )
            logger.info("  ✅ Updated company_admin permissions")
        
        # Add manager permissions
        cursor.execute("SELECT permissions FROM role_permissions WHERE role = 'manager'")
        result = cursor.fetchone()
        
        if result:
            import json
            permissions = json.loads(result[0])
            
            permissions['manage_tenant_rates'] = True
            
            cursor.execute(
                "UPDATE role_permissions SET permissions = ? WHERE role = 'manager'",
                (json.dumps(permissions),)
            )
            logger.info("  ✅ Updated manager permissions")
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v013")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                tables = [
                    'tenant_rate_export_log',
                    'tenant_rate_import_log',
                    'tenant_rate_audit',
                    'tenant_pricing_levels',
                    'tenant_rate_items',
                    'tenant_rate_versions',
                    'tenant_rate_books'
                ]
                
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"  ✅ Dropped table: {table}")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False