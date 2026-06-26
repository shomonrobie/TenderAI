# migrations/fix_db_final.py
"""Fix database - properly adds UNIQUE columns to existing tables"""

import sqlite3
import random

def get_existing_columns(conn, table_name):
    """Get list of existing column names"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}

def add_column_if_not_exists(conn, table_name, column_name, column_type, is_unique=False):
    """Add column only if it doesn't exist"""
    existing = get_existing_columns(conn, table_name)
    
    if column_name not in existing:
        cursor = conn.cursor()
        try:
            # Remove UNIQUE from type for initial add if needed
            add_type = column_type.replace(' UNIQUE', '') if is_unique else column_type
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {add_type}")
            print(f"  ✅ Added: {table_name}.{column_name}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to add {table_name}.{column_name}: {e}")
            return False
    else:
        print(f"  ⏭️ Already exists: {table_name}.{column_name}")
        return False

def add_unique_constraint(conn, table_name, column_name):
    """Add UNIQUE constraint using index (SQLite doesn't support ALTER TABLE ADD CONSTRAINT)"""
    cursor = conn.cursor()
    try:
        # Create unique index to enforce uniqueness
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_{column_name} ON {table_name}({column_name})")
        print(f"  ✅ Added UNIQUE constraint on {table_name}.{column_name}")
        return True
    except Exception as e:
        print(f"  ⚠️ Could not add UNIQUE constraint on {table_name}.{column_name}: {e}")
        return False

def populate_mobile_numbers(conn, table_name):
    """Populate mobile numbers for existing rows"""
    cursor = conn.cursor()
    
    # Get rows where mobile_number is NULL
    cursor.execute(f"SELECT id FROM {table_name} WHERE mobile_number IS NULL")
    rows = cursor.fetchall()
    
    if rows:
        print(f"  📱 Populating {len(rows)} rows with unique mobile numbers...")
        
        # Get existing mobile numbers to avoid duplicates
        cursor.execute(f"SELECT mobile_number FROM {table_name} WHERE mobile_number IS NOT NULL")
        existing_numbers = {row[0] for row in cursor.fetchall()}
        
        for row in rows:
            row_id = row[0]
            # Generate unique mobile number
            while True:
                # Generate random 10-digit number starting with 01
                random_num = f"01{random.randint(100000000, 999999999)}"
                if random_num not in existing_numbers:
                    existing_numbers.add(random_num)
                    break
            
            cursor.execute(f"UPDATE {table_name} SET mobile_number = ? WHERE id = ?", (random_num, row_id))
        
        conn.commit()
        print(f"  ✅ Populated {len(rows)} mobile numbers")
    else:
        print("  ✅ All rows already have mobile numbers")

def main():
    print("=" * 60)
    print("🔧 FIXING DATABASE - WITH PROPER COLUMN CHECKS")
    print("=" * 60)
    
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # =========================================================
    # Add missing columns to USERS table (without UNIQUE first)
    # =========================================================
    print("\n📝 Checking USERS table...")
    
    # Add mobile_number WITHOUT UNIQUE first
    existing = get_existing_columns(conn, 'users')
    if 'mobile_number' not in existing:
        cursor.execute("ALTER TABLE users ADD COLUMN mobile_number TEXT")
        print("  ✅ Added: users.mobile_number (without UNIQUE)")
        
        # Populate with unique values
        populate_mobile_numbers(conn, 'users')
        
        # Add UNIQUE constraint via index
        add_unique_constraint(conn, 'users', 'mobile_number')
    else:
        print("  ⏭️ users.mobile_number already exists")
    
    # Add other columns
    other_columns = [
        ('mobile_verified', 'BOOLEAN DEFAULT 0'),
        ('mobile_verified_at', 'TIMESTAMP'),
        ('email_verified', 'BOOLEAN DEFAULT 0'),
        ('email_verified_at', 'TIMESTAMP'),
        ('verification_token', 'TEXT'),
        ('reset_token', 'TEXT'),
        ('reset_token_expires', 'TIMESTAMP'),
    ]
    
    for col_name, col_type in other_columns:
        add_column_if_not_exists(conn, 'users', col_name, col_type, is_unique=False)
    
    # =========================================================
    # Add missing columns to COMPANIES table
    # =========================================================
    print("\n📝 Checking COMPANIES table...")
    
    existing = get_existing_columns(conn, 'companies')
    if 'mobile_number' not in existing:
        cursor.execute("ALTER TABLE companies ADD COLUMN mobile_number TEXT")
        print("  ✅ Added: companies.mobile_number (without UNIQUE)")
        
        # Populate with unique values
        populate_mobile_numbers(conn, 'companies')
        
        # Add UNIQUE constraint via index
        add_unique_constraint(conn, 'companies', 'mobile_number')
    else:
        print("  ⏭️ companies.mobile_number already exists")
    
    companies_columns = [
        ('mobile_verified', 'BOOLEAN DEFAULT 0'),
        ('mobile_verified_at', 'TIMESTAMP'),
        ('email_verified', 'BOOLEAN DEFAULT 0'),
        ('email_verified_at', 'TIMESTAMP'),
    ]
    
    for col_name, col_type in companies_columns:
        add_column_if_not_exists(conn, 'companies', col_name, col_type, is_unique=False)
    
    # =========================================================
    # Create OTP tables if not exist
    # =========================================================
    print("\n📝 Creating OTP tables...")
    
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
    
    # system_config and password_reset_tokens already exist
    print("  ⏭️ system_config table already exists")
    print("  ⏭️ password_reset_tokens table already exists")
    
    # =========================================================
    # Create indexes
    # =========================================================
    print("\n📝 Creating indexes...")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_users_mobile")
        cursor.execute("CREATE UNIQUE INDEX idx_users_mobile ON users(mobile_number) WHERE mobile_number IS NOT NULL")
        print("  ✅ idx_users_mobile (UNIQUE)")
    except Exception as e:
        print(f"  ⚠️ idx_users_mobile: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_companies_mobile")
        cursor.execute("CREATE UNIQUE INDEX idx_companies_mobile ON companies(mobile_number) WHERE mobile_number IS NOT NULL")
        print("  ✅ idx_companies_mobile (UNIQUE)")
    except Exception as e:
        print(f"  ⚠️ idx_companies_mobile: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_otp_lookup")
        cursor.execute("CREATE INDEX idx_otp_lookup ON otp_verification(contact_type, contact_value, otp_code, is_used)")
        print("  ✅ idx_otp_lookup")
    except Exception as e:
        print(f"  ⚠️ idx_otp_lookup: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_users_email")
        cursor.execute("CREATE INDEX idx_users_email ON users(email)")
        print("  ✅ idx_users_email")
    except Exception as e:
        print(f"  ⚠️ idx_users_email: {e}")
    
    # =========================================================
    # Set default config values if not exist
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
    # Verify results
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
    
    # Check if mobile_number has values
    verify_cursor.execute("SELECT COUNT(*) FROM users WHERE mobile_number IS NOT NULL")
    user_count = verify_cursor.fetchone()[0]
    verify_cursor.execute("SELECT COUNT(*) FROM users")
    total_users = verify_cursor.fetchone()[0]
    print(f"\n  📱 Users with mobile numbers: {user_count}/{total_users}")
    
    verify_cursor.execute("SELECT COUNT(*) FROM companies WHERE mobile_number IS NOT NULL")
    company_count = verify_cursor.fetchone()[0]
    verify_cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = verify_cursor.fetchone()[0]
    print(f"  📱 Companies with mobile numbers: {company_count}/{total_companies}")
    
    verify_cursor.execute("SELECT COUNT(*) FROM system_config")
    config_count = verify_cursor.fetchone()[0]
    print(f"  ⚙️ system_config has {config_count} settings")
    
    verify_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ DATABASE FIX COMPLETED!")
    print("=" * 60)
    print("\n💡 Now run: streamlit run main.py")

if __name__ == "__main__":
    main()