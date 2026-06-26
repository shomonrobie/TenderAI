# migrations/fix_db_final.py
"""Fix database - properly checks before adding columns"""

import sqlite3

def get_existing_columns(conn, table_name):
    """Get list of existing column names"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}

def add_column_if_not_exists(conn, table_name, column_name, column_type):
    """Add column only if it doesn't exist"""
    existing = get_existing_columns(conn, table_name)
    
    if column_name not in existing:
        cursor = conn.cursor()
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            print(f"  ✅ Added: {table_name}.{column_name}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to add {table_name}.{column_name}: {e}")
            return False
    else:
        print(f"  ⏭️ Already exists: {table_name}.{column_name}")
        return False

def main():
    print("=" * 60)
    print("🔧 FIXING DATABASE - WITH PROPER COLUMN CHECKS")
    print("=" * 60)
    
    conn = sqlite3.connect("data/tender_system.db")
    
    # =========================================================
    # Add missing columns to USERS table
    # =========================================================
    print("\n📝 Checking USERS table...")
    
    users_columns = [
        ('mobile_number', 'TEXT UNIQUE'),
        ('mobile_verified', 'BOOLEAN DEFAULT 0'),
        ('mobile_verified_at', 'TIMESTAMP'),
        ('email_verified', 'BOOLEAN DEFAULT 0'),
        ('email_verified_at', 'TIMESTAMP'),
        ('verification_token', 'TEXT'),
        ('reset_token', 'TEXT'),
        ('reset_token_expires', 'TIMESTAMP'),
    ]
    
    for col_name, col_type in users_columns:
        add_column_if_not_exists(conn, 'users', col_name, col_type)
    
    # =========================================================
    # Add missing columns to COMPANIES table
    # =========================================================
    print("\n📝 Checking COMPANIES table...")
    
    companies_columns = [
        ('mobile_number', 'TEXT UNIQUE'),
        ('mobile_verified', 'BOOLEAN DEFAULT 0'),
        ('mobile_verified_at', 'TIMESTAMP'),
        ('email_verified', 'BOOLEAN DEFAULT 0'),
        ('email_verified_at', 'TIMESTAMP'),
    ]
    
    for col_name, col_type in companies_columns:
        add_column_if_not_exists(conn, 'companies', col_name, col_type)
    
    # =========================================================
    # Create OTP tables
    # =========================================================
    print("\n📝 Creating OTP tables...")
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otp_verification'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE otp_verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                contact_type TEXT NOT NULL,
                contact_value TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                purpose TEXT DEFAULT 'verification',
                expires_at TIMESTAMP NOT NULL,
                attempts INTEGER DEFAULT 0,
                is_used BOOLEAN DEFAULT 0,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✅ Created otp_verification table")
    else:
        print("  ⏭️ otp_verification table already exists")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verification_history'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                contact_type TEXT NOT NULL,
                contact_value TEXT NOT NULL,
                verification_method TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by INTEGER,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        print("  ✅ Created verification_history table")
    else:
        print("  ⏭️ verification_history table already exists")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER
            )
        """)
        print("  ✅ Created system_config table")
    else:
        print("  ⏭️ system_config table already exists")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='password_reset_tokens'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✅ Created password_reset_tokens table")
    else:
        print("  ⏭️ password_reset_tokens table already exists")
    
    # =========================================================
    # Create indexes (drop and recreate to be safe)
    # =========================================================
    print("\n📝 Creating indexes...")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_users_mobile")
        cursor.execute("CREATE INDEX idx_users_mobile ON users(mobile_number) WHERE mobile_number IS NOT NULL")
        print("  ✅ idx_users_mobile")
    except Exception as e:
        print(f"  ⚠️ idx_users_mobile: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_companies_mobile")
        cursor.execute("CREATE INDEX idx_companies_mobile ON companies(mobile_number) WHERE mobile_number IS NOT NULL")
        print("  ✅ idx_companies_mobile")
    except Exception as e:
        print(f"  ⚠️ idx_companies_mobile: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_otp_lookup")
        cursor.execute("CREATE INDEX idx_otp_lookup ON otp_verification(contact_type, contact_value, otp_code, is_used)")
        print("  ✅ idx_otp_lookup")
    except Exception as e:
        print(f"  ⚠️ idx_otp_lookup: {e}")
    
    # =========================================================
    # Set default config values
    # =========================================================
    print("\n📝 Setting default configuration...")
    
    default_configs = [
        ('otp_enabled', 'false'),
        ('allow_otp_login', 'false'),
        ('email_enabled', 'true'),
        ('sms_enabled', 'false'),
        ('otp_length', '6'),
        ('otp_expiry_minutes', '10'),
        ('otp_max_attempts', '3'),
        ('allow_password_login', 'true'),
    ]
    
    for key, value in default_configs:
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)", (key, value))
    print("  ✅ Default config values set")
    
    conn.commit()
    conn.close()
    
    # =========================================================
    # Verify
    # =========================================================
    print("\n" + "=" * 60)
    print("🔍 VERIFYING RESULTS")
    print("=" * 60)
    
    verify_conn = sqlite3.connect("data/tender_system.db")
    verify_cursor = verify_conn.cursor()
    
    verify_cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in verify_cursor.fetchall()]
    
    required = ['mobile_number', 'mobile_verified', 'email_verified', 'reset_token']
    
    for col in required:
        if col in columns:
            print(f"  ✅ {col} exists in users")
        else:
            print(f"  ❌ {col} MISSING in users")
    
    verify_cursor.execute("SELECT COUNT(*) FROM system_config")
    config_count = verify_cursor.fetchone()[0]
    print(f"\n  ✅ system_config has {config_count} settings")
    
    verify_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ DATABASE FIX COMPLETED!")
    print("=" * 60)
    print("\n💡 Now run: streamlit run main.py")

if __name__ == "__main__":
    main()