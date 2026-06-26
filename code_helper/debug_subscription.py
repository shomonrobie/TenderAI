# code_helper/debug_subscription.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.unified_db_manager import db
from datetime import datetime

print("=" * 70)
print("🧪 TESTING SUBSCRIPTION UPDATE")
print("=" * 70)

company_id = 1  # Babui

# 1. Check current subscription
print("\n📊 CURRENT SUBSCRIPTIONS:")
with db.get_connection() as conn:
    cursor = db.db_conn.get_cursor(conn)
    cursor.execute("""
        SELECT id, plan, status, start_date, end_date, company_id, user_id
        FROM subscriptions 
        WHERE company_id = ? OR user_id IN (SELECT id FROM users WHERE company_id = ?)
        ORDER BY id DESC
    """, (company_id, company_id))
    rows = cursor.fetchall()
    for row in rows:
        print(f"   ID: {row['id']}, Plan: {row['plan']}, Status: {row['status']}, Company: {row['company_id']}, User: {row['user_id']}")

# 2. Update to enterprise
print("\n🔄 UPDATING TO ENTERPRISE...")
success = db.update_company_subscription(
    company_id=company_id,
    plan='enterprise',
    duration='yearly',
    payment_method='test',
    transaction_id=f'TEST_{datetime.now().strftime("%Y%m%d%H%M%S")}'
)
print(f"   Update result: {success}")

# 3. Check after update
print("\n📊 AFTER UPDATE:")
with db.get_connection() as conn:
    cursor = db.db_conn.get_cursor(conn)
    cursor.execute("""
        SELECT id, plan, status, start_date, end_date, company_id, user_id
        FROM subscriptions 
        WHERE company_id = ? OR user_id IN (SELECT id FROM users WHERE company_id = ?)
        ORDER BY id DESC
    """, (company_id, company_id))
    rows = cursor.fetchall()
    for row in rows:
        print(f"   ID: {row['id']}, Plan: {row['plan']}, Status: {row['status']}, Company: {row['company_id']}, User: {row['user_id']}")

# 4. Check if enterprise plan is active
print("\n🔍 VERIFICATION:")
with db.get_connection() as conn:
    cursor = db.db_conn.get_cursor(conn)
    cursor.execute("""
        SELECT * FROM subscriptions 
        WHERE company_id = ? AND plan = 'enterprise' AND status = 'active'
    """, (company_id,))
    enterprise = cursor.fetchone()
    if enterprise:
        print("✅ Enterprise subscription found and active!")
        print(f"   ID: {enterprise['id']}, Start: {enterprise['start_date']}, End: {enterprise['end_date']}")
    else:
        print("❌ No active enterprise subscription found!")