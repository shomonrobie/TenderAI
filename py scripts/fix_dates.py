# fix_dates.py
import sqlite3
from datetime import datetime

def fix_date_format():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get all records
    cursor.execute("SELECT id, analysis_date FROM tender_analyses")
    rows = cursor.fetchall()
    
    for row in rows:
        analysis_id, date_value = row
        if date_value:
            try:
                # Check if it's a string with microseconds
                if isinstance(date_value, str) and '.' in date_value:
                    # Remove microseconds and timezone
                    clean_date = date_value.split('.')[0]
                    cursor.execute("UPDATE tender_analyses SET analysis_date = ? WHERE id = ?", (clean_date, analysis_id))
                    print(f"Fixed date for record {analysis_id}: {date_value} -> {clean_date}")
            except:
                pass
    
    conn.commit()
    conn.close()
    print("Date cleanup completed!")

if __name__ == "__main__":
    fix_date_format()