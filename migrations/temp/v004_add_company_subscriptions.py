# v004_add_company_subscriptions.py

version = "v004"

def up(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("  Adding columns to subscriptions table...")
    
    # Add company_id to subscriptions if not exists
    cursor.execute("PRAGMA table_info(subscriptions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'company_id' not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN company_id INTEGER REFERENCES companies(id)")
        print("    Added company_id column")
    
    if 'max_boq_generations' not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN max_boq_generations INTEGER DEFAULT 5")
        print("    Added max_boq_generations column")
    
    if 'max_bid_optimizations' not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN max_bid_optimizations INTEGER DEFAULT 5")
        print("    Added max_bid_optimizations column")
    
    if 'boq_used' not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN boq_used INTEGER DEFAULT 0")
        print("    Added boq_used column")
    
    if 'bid_optimizations_used' not in columns:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN bid_optimizations_used INTEGER DEFAULT 0")
        print("    Added bid_optimizations_used column")
    
    print("  Creating subscription_plans table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_name TEXT UNIQUE NOT NULL,
            plan_type TEXT DEFAULT 'company',
            monthly_price REAL DEFAULT 0,
            yearly_price REAL DEFAULT 0,
            max_boq_generations INTEGER DEFAULT 5,
            max_bid_optimizations INTEGER DEFAULT 5,
            max_tender_analyses INTEGER DEFAULT 5,
            max_users INTEGER DEFAULT 1,
            can_export_data BOOLEAN DEFAULT 0,
            can_edit_rates BOOLEAN DEFAULT 0,
            can_delete_rates BOOLEAN DEFAULT 0,
            can_create_versions BOOLEAN DEFAULT 0,
            can_manage_team BOOLEAN DEFAULT 0,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default plans
    default_plans = [
        ('free', 'company', 0, 0, 5, 5, 5, 1, 0, 0, 0, 0, 0, 'Free plan with basic features'),
        ('basic', 'company', 4999, 49990, 30, 30, 30, 3, 1, 0, 0, 0, 0, 'Basic plan for small businesses'),
        ('professional', 'company', 14999, 149990, 100, 100, -1, 10, 1, 0, 0, 1, 1, 'Professional plan for growing businesses'),
        ('enterprise', 'company', 49999, 499990, -1, -1, -1, -1, 1, 0, 0, 1, 1, 'Enterprise plan with unlimited features')
    ]
    
    for plan in default_plans:
        cursor.execute("""
            INSERT OR IGNORE INTO subscription_plans (
                plan_name, plan_type, monthly_price, yearly_price,
                max_boq_generations, max_bid_optimizations, max_tender_analyses,
                max_users, can_export_data, can_edit_rates, can_delete_rates,
                can_create_versions, can_manage_team, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, plan)
    
    conn.commit()
    conn.close()
    print("  ✅ Company subscriptions and plans tables created")