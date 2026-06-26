# migrations/v001_initial_schema.py

version = "v001"

def up(db_path):
    """Create initial database schema"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            registration_number TEXT,
            vat_number TEXT,
            address TEXT,
            district TEXT,
            division TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    """)
    
    # Subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_id INTEGER,
            plan TEXT DEFAULT 'free',
            status TEXT DEFAULT 'active',
            start_date DATE,
            end_date DATE,
            analyses_used INTEGER DEFAULT 0,
            analyses_limit INTEGER DEFAULT 5,
            payment_method TEXT,
            transaction_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    """)
    
    conn.commit()
    conn.close()