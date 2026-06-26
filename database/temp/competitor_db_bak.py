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

def calculate_win_probability(tender_id, user_total_cost):
    """
    Evaluates historical competitor price ranges for the same tender 
    to calculate a statistical win probability percentage.
    """
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT total_bid_amount FROM competitor_bids WHERE tender_id = ?"
    df_comp = pd.read_sql_query(query, conn, params=(tender_id,))
    conn.close()
    
    if df_comp.empty:
        return None, "No data available"
        
    all_bids = df_comp['total_bid_amount'].tolist()
    all_bids.append(user_total_cost)
    all_bids.sort()
    
    # Find rank index positioning (Lower price is preferred in e-GP L1 procurement formats)
    rank = all_bids.index(user_total_cost) + 1
    total_bidders = len(all_bids)
    
    # Calculate probability: higher ranking position results in a stronger win margin
    probability = ((total_bidders - rank) / total_bidders) * 100
    return round(probability, 1), f"Rank {rank} of {total_bidders}"
