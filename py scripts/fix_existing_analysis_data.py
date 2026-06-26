# fix_existing_analysis_data.py
import sqlite3
import json

def fix_existing_data():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get all records with competitor_bids that are not NULL
    cursor.execute("SELECT id, competitor_bids FROM tender_analyses WHERE competitor_bids IS NOT NULL")
    rows = cursor.fetchall()
    
    for row in rows:
        analysis_id, competitor_bids = row
        try:
            # Try to parse as JSON
            if isinstance(competitor_bids, str):
                json.loads(competitor_bids)
            elif isinstance(competitor_bids, (int, float)):
                # Convert numeric to NULL
                cursor.execute("UPDATE tender_analyses SET competitor_bids = NULL WHERE id = ?", (analysis_id,))
                print(f"Fixed record {analysis_id}: converted number to NULL")
        except:
            # Invalid JSON, set to NULL
            cursor.execute("UPDATE tender_analyses SET competitor_bids = NULL WHERE id = ?", (analysis_id,))
            print(f"Fixed record {analysis_id}: invalid JSON set to NULL")
    
    conn.commit()
    conn.close()
    print("Data cleanup completed!")

if __name__ == "__main__":
    fix_existing_data()
