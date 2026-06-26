# run_migration_now.py
import sqlite3

def run_migration():
    conn = sqlite3.connect('data/tender_system.db')
    cursor = conn.cursor()
    
    # Check if is_active exists in tender_milestones
    cursor.execute('PRAGMA table_info(tender_milestones)')
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'is_active' not in columns:
        print('Adding is_active column...')
        cursor.execute('ALTER TABLE tender_milestones ADD COLUMN is_active INTEGER DEFAULT 1')
        print('✅ Added is_active')
    
    if 'completed_at' not in columns:
        print('Adding completed_at column...')
        cursor.execute('ALTER TABLE tender_milestones ADD COLUMN completed_at TIMESTAMP')
        print('✅ Added completed_at')
    
    # Check tender_team_assignments table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tender_team_assignments'")
    if not cursor.fetchone():
        print('Creating tender_team_assignments table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tender_team_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print('✅ Created tender_team_assignments')
    
    conn.commit()
    conn.close()
    print('✅ Migration completed!')

if __name__ == "__main__":
    run_migration()