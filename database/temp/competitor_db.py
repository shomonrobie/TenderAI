# database/competitor_db.py
import sqlite3
import pandas as pd
from streamlit import secrets
from database.unified_db_manager import UnifiedDatabaseManager
#DB_PATH = secrets.get("database_path", "tenderai.db")
#DB_PATH = "data/tender_system.db"
db = UnifiedDatabaseManager()
DB_PATH = db.db_path 

def init_competitor_tables():
    """Initializes competitive indexing databases linked to main tender workflows."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Competitor Registry
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT,
            competitor_name TEXT NOT NULL,
            total_bid_amount REAL NOT NULL,
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_winner INTEGER DEFAULT 0 CHECK(is_winner IN (0, 1)),
            FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

