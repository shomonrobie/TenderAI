# delete_tenant_data.py - Delete all data from tenant rate tables

import sqlite3

DB_PATH = "data/tender_system.db"
COMPANY_ID = 3351  # Your company ID

def delete_tenant_rate_data(company_id):
    """Delete all data from tenant rate tables for a specific company"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🗑️ DELETING TENANT RATE DATA")
    print("=" * 60)
    print(f"Company ID: {company_id}")
    print()
    
    # Get all rate book IDs for this company
    cursor.execute("SELECT id FROM tenant_rate_books WHERE tenant_id = ?", (company_id,))
    book_ids = [row[0] for row in cursor.fetchall()]
    
    if not book_ids:
        print("⚠️ No rate books found for this company.")
        conn.close()
        return
    
    print(f"📚 Found {len(book_ids)} rate books:")
    cursor.execute("SELECT id, name, source_type FROM tenant_rate_books WHERE tenant_id = ?", (company_id,))
    books = cursor.fetchall()
    for book in books:
        print(f"  - ID: {book[0]}, Name: {book[1]}, Source: {book[2]}")
    
    print()
    confirm = input(f"Delete ALL data for {len(book_ids)} rate books? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Operation cancelled.")
        conn.close()
        return
    
    try:
        # 1. Delete pricing levels
        cursor.execute("""
            DELETE FROM tenant_pricing_levels 
            WHERE rate_item_id IN (
                SELECT id FROM tenant_rate_items 
                WHERE rate_book_id IN ({})
            )
        """.format(','.join(['?'] * len(book_ids))), book_ids)
        print(f"  ✅ Deleted {cursor.rowcount} pricing levels")
        
        # 2. Delete items
        cursor.execute("""
            DELETE FROM tenant_rate_items 
            WHERE rate_book_id IN ({})
        """.format(','.join(['?'] * len(book_ids))), book_ids)
        print(f"  ✅ Deleted {cursor.rowcount} items")
        
        # 3. Delete versions
        cursor.execute("""
            DELETE FROM tenant_rate_versions 
            WHERE rate_book_id IN ({})
        """.format(','.join(['?'] * len(book_ids))), book_ids)
        print(f"  ✅ Deleted {cursor.rowcount} versions")
        
        # 4. Delete books
        cursor.execute("DELETE FROM tenant_rate_books WHERE tenant_id = ?", (company_id,))
        print(f"  ✅ Deleted {cursor.rowcount} books")
        
        # 5. Delete audit records
        cursor.execute("""
            DELETE FROM tenant_rate_audit 
            WHERE rate_book_id IN ({})
        """.format(','.join(['?'] * len(book_ids))), book_ids)
        print(f"  ✅ Deleted {cursor.rowcount} audit records")
        
        # 6. Reset onboarding status for this company
        cursor.execute("""
            UPDATE company_onboarding_status 
            SET demo_generated = 0,
                demo_generated_at = NULL,
                onboarding_step = 3,
                step_data = NULL
            WHERE company_id = ?
        """, (company_id,))
        print(f"  ✅ Reset onboarding status")
        
        conn.commit()
        print("\n✅ All tenant rate data deleted successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    company_id = 3351  # Default
    if len(sys.argv) > 1:
        try:
            company_id = int(sys.argv[1])
        except:
            pass
    
    delete_tenant_rate_data(company_id)
    print("\n" + "=" * 60)
    print("✅ DELETE COMPLETE!")
    print("=" * 60)