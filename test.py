from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

# Check OCE for tender 1295058
with db.get_connection() as conn:
    cursor = db.db_conn.get_cursor(conn)
    cursor.execute("""
        SELECT id, tender_id, official_estimate, tender_title 
        FROM company_tenders 
        WHERE tender_id = '1295058'
    """)
    result = cursor.fetchone()
    if result:
        print(f"Tender ID: {result['tender_id']}")
        print(f"OCE: {result['official_estimate']}")
        print(f"ID: {result['id']}")
    else:
        print("Tender not found")