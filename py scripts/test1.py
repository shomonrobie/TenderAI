import sqlite3
conn = sqlite3.connect(r'D:\iTender\data\tender_system.db')
cursor = conn.cursor()
cursor.execute('SELECT id, username, password, is_active, is_approved, role FROM users')
users = cursor.fetchall()
print('--- USERS IN DATABASE ---')
for u in users:
    print(f'ID: {u[0]} | User: {u[1]} | Pass: {u[2]} | Active: {u[3]} | Approved: {u[4]}')
if not users:
    print('⚠️ DATABASE IS EMPTY! No users found.')
conn.close()