# check_db_structure.py
import sqlite3

def check_db_structure():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    print("=" * 60)
    print("TENDER_ANALYSES TABLE STRUCTURE")
    print("=" * 60)
    
    cursor.execute("PRAGMA table_info(tender_analyses)")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    print("\n" + "=" * 60)
    print("SAMPLE DATA (last 5 records)")
    print("=" * 60)
    
    # Get all column names first
    cursor.execute("PRAGMA table_info(tender_analyses)")
    col_names = [col[1] for col in cursor.fetchall()]
    
    # Build query with existing columns only
    select_cols = ['id', 'user_id', 'company_id', 'tender_id', 'analysis_date']
    # Add optional columns if they exist
    optional_cols = ['analysis_type', 'bid_status', 'risk_level']
    for col in optional_cols:
        if col in col_names:
            select_cols.append(col)
    
    query = f"SELECT {', '.join(select_cols)} FROM tender_analyses ORDER BY id DESC LIMIT 5"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"  ID: {row[0]}, User: {row[1]}, Company: {row[2]}, Tender: {row[3]}, Date: {row[4]}")
    else:
        print("  No records found")
    
    conn.close()

if __name__ == "__main__":
    check_db_structure()