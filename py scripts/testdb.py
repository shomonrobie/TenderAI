import sqlite3
conn = sqlite3.connect('data/tender_system.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(tender_analyses)')
columns = cursor.fetchall()
print('Columns in tender_analyses:')
for col in columns:
    print(f'  {col[1]}: {col[2]}')
conn.close()