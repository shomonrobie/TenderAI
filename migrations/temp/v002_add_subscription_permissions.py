# migrations/v002_add_subscription_permissions.py

version = "v002"

def up(db_path):
    """Add subscription permission columns"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(subscriptions)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    new_columns = {
        'max_boq_generations': 'INTEGER DEFAULT 5',
        'max_bid_optimizations': 'INTEGER DEFAULT 5',
        'boq_used': 'INTEGER DEFAULT 0',
        'bid_optimizations_used': 'INTEGER DEFAULT 0',
        'can_edit_rates': 'BOOLEAN DEFAULT 0',
        'can_delete_rates': 'BOOLEAN DEFAULT 0',
        'can_create_versions': 'BOOLEAN DEFAULT 0',
        'can_export_data': 'BOOLEAN DEFAULT 0',
        'can_manage_team': 'BOOLEAN DEFAULT 0',
        'last_reset_date': 'DATE'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE subscriptions ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name}")
    
    # Set default values
    cursor.execute("""
        UPDATE subscriptions 
        SET 
            max_boq_generations = CASE plan 
                WHEN 'free' THEN 5
                WHEN 'basic' THEN 30
                WHEN 'professional' THEN 100
                WHEN 'enterprise' THEN -1
                ELSE 5
            END,
            max_bid_optimizations = CASE plan 
                WHEN 'free' THEN 5
                WHEN 'basic' THEN 30
                WHEN 'professional' THEN 100
                WHEN 'enterprise' THEN -1
                ELSE 5
            END,
            can_edit_rates = CASE plan 
                WHEN 'professional' THEN 1
                WHEN 'enterprise' THEN 1
                ELSE 0
            END,
            can_delete_rates = CASE plan 
                WHEN 'enterprise' THEN 1
                ELSE 0
            END,
            can_create_versions = CASE plan 
                WHEN 'professional' THEN 1
                WHEN 'enterprise' THEN 1
                ELSE 0
            END,
            can_export_data = CASE plan 
                WHEN 'basic' THEN 1
                WHEN 'professional' THEN 1
                WHEN 'enterprise' THEN 1
                ELSE 0
            END,
            can_manage_team = CASE plan 
                WHEN 'professional' THEN 1
                WHEN 'enterprise' THEN 1
                ELSE 0
            END,
            last_reset_date = date('now')
    """)
    
    conn.commit()
    conn.close()