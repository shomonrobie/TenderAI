# migrations/v012_update_user_profile.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV012:
    """Migration v012: Update user profile with avatar, bio, location, website and social links"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v012: Update user profile")
        
        try:
            # 1. Add columns to users table
            self._add_user_profile_columns()
            
            # 2. Create social_links table
            self._create_social_links_table()
            
            # 3. Create user_activity_log table
            self._create_user_activity_log_table()
            
            # 4. Create indexes
            self._create_indexes()
            
            # 5. Create view for user profile
            self._create_user_profile_view()
            
            logger.info("✅ Migration v012 completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration v012 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v012")
        
        try:
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                db_type = self.db.get_db_type()
                
                # Drop tables (cascade handles foreign keys)
                tables_to_drop = ['user_activity_log', 'social_links']
                for table in tables_to_drop:
                    if self.db.table_exists(table):
                        if db_type == 'sqlite':
                            cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        elif db_type in ['postgresql', 'cockroachdb']:
                            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                        else:
                            cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        logger.info(f"  ✅ Dropped table: {table}")
                
                # Drop view
                cursor.execute("DROP VIEW IF EXISTS v_user_profile")
                logger.info("  ✅ Dropped view: v_user_profile")
                
                # Note: Can't easily drop columns in SQLite, but we can ignore them
                logger.info("  ℹ️ Columns in users table will remain (SQLite doesn't support DROP COLUMN)")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def _add_user_profile_columns(self):
        """Add profile columns to users table"""
        columns_to_add = [
            ('avatar_url', 'TEXT'),
            ('bio', 'TEXT'),
            ('location', 'TEXT'),
            ('website', 'TEXT'),
        ]
        
        with self.db.get_connection() as conn:
            cursor = self.db.db_conn.get_cursor(conn)
            db_type = self.db.get_db_type()
            
            for col_name, col_type in columns_to_add:
                if not self.db.column_exists('users', col_name):
                    try:
                        if db_type == 'sqlite':
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                        elif db_type in ['postgresql', 'cockroachdb']:
                            sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        elif db_type == 'mysql':
                            sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        else:
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                        
                        cursor.execute(sql)
                        logger.info(f"  ✅ Added column: {col_name} ({col_type})")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Could not add column {col_name}: {e}")
                else:
                    logger.info(f"  ℹ️ Column already exists: {col_name}")
    
    def _create_social_links_table(self):
        """Create social_links table"""
        with self.db.get_connection() as conn:
            cursor = self.db.db_conn.get_cursor(conn)
            db_type = self.db.get_db_type()
            
            if not self.db.table_exists('social_links'):
                # Define table schema based on database type
                if db_type == 'sqlite':
                    sql = """
                        CREATE TABLE IF NOT EXISTS social_links (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            platform TEXT NOT NULL,
                            url TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT 1,
                            is_public BOOLEAN DEFAULT 1,
                            icon TEXT,
                            display_order INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            UNIQUE(user_id, platform)
                        )
                    """
                elif db_type in ['postgresql', 'cockroachdb']:
                    sql = """
                        CREATE TABLE IF NOT EXISTS social_links (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            platform TEXT NOT NULL,
                            url TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT true,
                            is_public BOOLEAN DEFAULT true,
                            icon TEXT,
                            display_order INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, platform)
                        )
                    """
                elif db_type == 'mysql':
                    sql = """
                        CREATE TABLE IF NOT EXISTS social_links (
                            id INTEGER PRIMARY KEY AUTO_INCREMENT,
                            user_id INTEGER NOT NULL,
                            platform TEXT NOT NULL,
                            url TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT 1,
                            is_public BOOLEAN DEFAULT 1,
                            icon TEXT,
                            display_order INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            UNIQUE KEY unique_user_platform (user_id, platform)
                        )
                    """
                else:
                    raise ValueError(f"Unsupported database type: {db_type}")
                
                cursor.execute(sql)
                logger.info("  ✅ Created table: social_links")
            else:
                logger.info("  ℹ️ Table already exists: social_links")
                
                # Check for missing columns
                columns_to_add = [
                    ('is_public', 'BOOLEAN DEFAULT 1'),
                    ('icon', 'TEXT'),
                    ('display_order', 'INTEGER DEFAULT 0'),
                ]
                
                for col_name, col_type in columns_to_add:
                    if not self.db.column_exists('social_links', col_name):
                        try:
                            if db_type == 'sqlite':
                                cursor.execute(f"ALTER TABLE social_links ADD COLUMN {col_name} {col_type}")
                            elif db_type in ['postgresql', 'cockroachdb']:
                                cursor.execute(f"ALTER TABLE social_links ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                            elif db_type == 'mysql':
                                cursor.execute(f"ALTER TABLE social_links ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                            logger.info(f"  ✅ Added column: {col_name} to social_links")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Could not add column {col_name}: {e}")
    
    def _create_user_activity_log_table(self):
        """Create user_activity_log table"""
        with self.db.get_connection() as conn:
            cursor = self.db.db_conn.get_cursor(conn)
            db_type = self.db.get_db_type()
            
            if not self.db.table_exists('user_activity_log'):
                if db_type == 'sqlite':
                    sql = """
                        CREATE TABLE IF NOT EXISTS user_activity_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            action TEXT NOT NULL,
                            details TEXT,
                            ip_address TEXT,
                            user_agent TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """
                elif db_type in ['postgresql', 'cockroachdb']:
                    sql = """
                        CREATE TABLE IF NOT EXISTS user_activity_log (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            action TEXT NOT NULL,
                            details TEXT,
                            ip_address TEXT,
                            user_agent TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                elif db_type == 'mysql':
                    sql = """
                        CREATE TABLE IF NOT EXISTS user_activity_log (
                            id INTEGER PRIMARY KEY AUTO_INCREMENT,
                            user_id INTEGER NOT NULL,
                            action TEXT NOT NULL,
                            details TEXT,
                            ip_address TEXT,
                            user_agent TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """
                else:
                    raise ValueError(f"Unsupported database type: {db_type}")
                
                cursor.execute(sql)
                logger.info("  ✅ Created table: user_activity_log")
            else:
                logger.info("  ℹ️ Table already exists: user_activity_log")
    
    def _create_indexes(self):
        """Create indexes for better performance"""
        with self.db.get_connection() as conn:
            cursor = self.db.db_conn.get_cursor(conn)
            db_type = self.db.get_db_type()
            
            # Social links indexes
            indexes = [
                ("idx_social_links_user_id", "social_links", "user_id"),
                ("idx_social_links_platform", "social_links", "platform"),
                ("idx_social_links_active", "social_links", "is_active"),
                ("idx_user_activity_log_user_id", "user_activity_log", "user_id"),
                ("idx_user_activity_log_action", "user_activity_log", "action"),
                ("idx_user_activity_log_created_at", "user_activity_log", "created_at DESC"),
            ]
            
            for idx_name, table, column in indexes:
                if db_type == 'sqlite':
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
                elif db_type in ['postgresql', 'cockroachdb']:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
                elif db_type == 'mysql':
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
                
                try:
                    cursor.execute(sql)
                    logger.info(f"  ✅ Created index: {idx_name}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not create index {idx_name}: {e}")
    
    def _create_user_profile_view(self):
        """Create view for user profile with social links aggregated"""
        with self.db.get_connection() as conn:
            cursor = self.db.db_conn.get_cursor(conn)
            db_type = self.db.get_db_type()
            
            # Drop view if exists (to recreate with updated schema)
            cursor.execute("DROP VIEW IF EXISTS v_user_profile")
            
            if db_type == 'sqlite':
                sql = """
                    CREATE VIEW v_user_profile AS
                    SELECT 
                        u.id,
                        u.username,
                        u.email,
                        u.full_name,
                        u.phone,
                        u.mobile_number,
                        u.mobile_verified,
                        u.role,
                        u.is_active,
                        u.account_type,
                        u.specialization,
                        u.years_experience,
                        u.avatar_url,
                        u.bio,
                        u.location,
                        u.website,
                        u.created_at,
                        u.last_login,
                        u.company_id,
                        c.company_name,
                        GROUP_CONCAT(sl.platform || ':' || sl.url) as social_links,
                        COUNT(DISTINCT sl.id) as social_links_count
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    LEFT JOIN social_links sl ON u.id = sl.user_id AND sl.is_active = 1
                    GROUP BY u.id
                """
            elif db_type in ['postgresql', 'cockroachdb']:
                sql = """
                    CREATE VIEW v_user_profile AS
                    SELECT 
                        u.id,
                        u.username,
                        u.email,
                        u.full_name,
                        u.phone,
                        u.mobile_number,
                        u.mobile_verified,
                        u.role,
                        u.is_active,
                        u.account_type,
                        u.specialization,
                        u.years_experience,
                        u.avatar_url,
                        u.bio,
                        u.location,
                        u.website,
                        u.created_at,
                        u.last_login,
                        u.company_id,
                        c.company_name,
                        STRING_AGG(sl.platform || ':' || sl.url, ',') as social_links,
                        COUNT(DISTINCT sl.id) as social_links_count
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    LEFT JOIN social_links sl ON u.id = sl.user_id AND sl.is_active = true
                    GROUP BY u.id, c.company_name
                """
            elif db_type == 'mysql':
                sql = """
                    CREATE VIEW v_user_profile AS
                    SELECT 
                        u.id,
                        u.username,
                        u.email,
                        u.full_name,
                        u.phone,
                        u.mobile_number,
                        u.mobile_verified,
                        u.role,
                        u.is_active,
                        u.account_type,
                        u.specialization,
                        u.years_experience,
                        u.avatar_url,
                        u.bio,
                        u.location,
                        u.website,
                        u.created_at,
                        u.last_login,
                        u.company_id,
                        c.company_name,
                        GROUP_CONCAT(CONCAT(sl.platform, ':', sl.url)) as social_links,
                        COUNT(DISTINCT sl.id) as social_links_count
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    LEFT JOIN social_links sl ON u.id = sl.user_id AND sl.is_active = 1
                    GROUP BY u.id
                """
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            cursor.execute(sql)
            logger.info("  ✅ Created view: v_user_profile")