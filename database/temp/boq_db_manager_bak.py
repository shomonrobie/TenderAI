# database/boq_db_manager.py
import sqlite3
import pandas as pd
from streamlit import secrets

# Dynamically link to your existing database engine
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()
DB_PATH = db.db_path 

def init_boq_subsystem_tables():
    """Builds relational structural scopes over your existing iTender tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Extend or track state for ingested e-GP Tenders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenders_boq_meta (
            tender_id TEXT PRIMARY KEY,
            ministry_or_agency TEXT,
            selected_zone TEXT,
            workflow_status TEXT CHECK(workflow_status IN ('Draft', 'Pending Approval', 'Approved')) DEFAULT 'Draft',
            official_budget_cap REAL DEFAULT 0.0,
            created_by TEXT,
            approved_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Store individual financial line items tied contextually to the Tender
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tender_boq_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT,
            item_no TEXT,
            group_name TEXT,
            item_code TEXT,
            description TEXT,
            unit TEXT,
            quantity REAL,
            unit_rate REAL,
            last_modified_by TEXT,
            FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Dedicated Audit Trail Log System
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_change_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT,
            item_code TEXT,
            item_no TEXT,
            old_rate REAL,
            new_rate REAL,
            modified_by TEXT,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Competitor Bids Registry
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