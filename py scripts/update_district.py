# update_analysis_columns.py
import sqlite3

def update_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add is_final_submitted column if not exists
    try:
        cursor.execute("ALTER TABLE companies ADD COLUMN district TEXT")
        
        print("✓ Added district column")
    except:
        print("⚠ district already exists")
    
    # Add final_submitted_bid column if not exists
    try:
        cursor.execute("UPDATE companies SET district = city WHERE city IS NOT NULL")
        print("✓ Updated district column with city values")
    except:
        print("⚠ Error updating district column")

    try:
        cursor.execute("DROP COLUMN city")
        print("✓ city column removed")
    except:
        print("⚠ Error removing city column")
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    update_columns()