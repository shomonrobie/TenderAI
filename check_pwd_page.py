# check_pwd_page.py
import sqlite3
import sys
from pathlib import Path

def main():
    # === CONFIGURE YOUR DATABASE PATH HERE ===
    #db_path = Path("data/app.db")          # ← Change this if your DB is elsewhere
    db_path = Path("data/tender_system.db")

    

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='pwd_chapters'
        """)
        
        if not cursor.fetchone():
            print("❌ Table 'pwd_chapters' does not exist!")
            print("\nAvailable tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for t in tables:
                print(f"  - {t}")
            if not tables:
                print("  (No tables found)")
            return

        # Fetch data
        cursor.execute("""
            SELECT chapter_number, chapter_name, description 
            FROM pwd_chapters 
            ORDER BY CAST(chapter_number AS INTEGER)
        """)

        rows = cursor.fetchall()
        
        print(f"\n✅ Connected to: {db_path.name}")
        print(f"✅ Total rows in 'pwd_chapters': {len(rows)}")
        print("\n" + "-" * 100)
        print(f"{'Chapter':<8} {'Chapter Name':<45} {'Description'}")
        print("-" * 100)

        for row in rows:
            ch_num = str(row[0]) if row[0] is not None else "NULL"
            ch_name = str(row[1]) if row[1] is not None else "NULL"
            desc = str(row[2]) if row[2] is not None else "NULL"

            # Smart truncation
            name_disp = (ch_name[:42] + "...") if len(ch_name) > 42 else ch_name
            desc_disp = (desc[:50] + "...") if len(desc) > 50 else desc

            print(f"{ch_num:<8} {name_disp:<45} {desc_disp}")

    except sqlite3.Error as e:
        print(f"❌ SQLite Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()