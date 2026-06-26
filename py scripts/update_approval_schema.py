# update_approval_schema.py
import sqlite3

def update_approval_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add approval-related columns to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 0")
        print("✓ Added is_approved column")
    except sqlite3.OperationalError:
        print("⚠ is_approved column already exists")
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN approved_by INTEGER")
        print("✓ Added approved_by column")
    except sqlite3.OperationalError:
        print("⚠ approved_by column already exists")
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN approved_at TIMESTAMP")
        print("✓ Added approved_at column")
    except sqlite3.OperationalError:
        print("⚠ approved_at column already exists")
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN registration_complete BOOLEAN DEFAULT 0")
        print("✓ Added registration_complete column")
    except sqlite3.OperationalError:
        print("⚠ registration_complete column already exists")
    
    # Update admin user to be auto-approved
    cursor.execute("UPDATE users SET is_approved = 1, registration_complete = 1 WHERE role = 'admin'")
    
    conn.commit()
    conn.close()
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    update_approval_schema()
