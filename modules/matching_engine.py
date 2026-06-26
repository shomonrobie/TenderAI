# modules/matching_engine.py
import streamlit as st
import sqlite3
import difflib
import pandas as pd
from streamlit import secrets
from database.unified_db_manager import UnifiedDatabaseManager
from utils.data_sanitizer import sanitize_text

#DB_PATH = secrets.get("database_path", "tenderai.db")
#DB_PATH = "data/tender_system.db"
db = UnifiedDatabaseManager()
DB_PATH = db.db_path 

def search_best_pwd_match(item_code, user_description, zone="Dhaka"):
    """
    Tries an exact code match first. 
    If missing, evaluates token sequences using native Gestalt error metrics.
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Pipeline 1: Exact Item Code Match
    if pd.notna(item_code) and str(item_code).strip().lower() != 'n/a':
        clean_code = str(item_code).strip()
        query = """
            SELECT child.pwd_code, parent.specification_text as p_text, child.specification_text as c_text, child.measurement_unit, rate.unit_rate
            FROM pwd_items child
            LEFT JOIN pwd_items parent ON child.parent_code = parent.pwd_code
            LEFT JOIN pwd_rates rate ON child.pwd_code = rate.pwd_code
            WHERE child.pwd_code = ? AND rate.zone_name = ?
        """
        df = pd.read_sql_query(query, conn, params=(clean_code, zone))
        if not df.empty:
            conn.close()
            p_desc = df.iloc[0]['p_text']
            c_desc = df.iloc[0]['c_text']
            combined = f"{p_desc}\n\n{c_desc}" if pd.notna(p_desc) else c_desc
            return df.iloc[0]['pwd_code'], combined, df.iloc[0]['measurement_unit'], float(df.iloc[0]['unit_rate']), 1
    # Pipeline 2: Fuzzy Logic Fallback via Description Extraction
    if pd.notna(user_description) and len(str(user_description).strip()) > 10:
        # 🔥 Sanitize the incoming query string to maximize scoring efficiency
        clean_user_desc = sanitize_text(user_description)[:50].lower()
        
        query = """
            SELECT child.pwd_code, child.specification_text, child.measurement_unit, rate.unit_rate
            FROM pwd_items child
            JOIN pwd_rates rate ON child.pwd_code = rate.pwd_code
            WHERE rate.zone_name = ?
        """
        candidates = pd.read_sql_query(query, conn, params=(zone,))
        conn.close()
        
        if not candidates.empty:
            # Sanitize database candidates on the fly for an accurate baseline comparison
            candidates['similarity'] = candidates['specification_text'].apply(
                lambda x: difflib.SequenceMatcher(None, clean_user_desc, sanitize_text(x)[:50].lower()).ratio()
            )
            best_match = candidates.sort_values(by='similarity', ascending=False).iloc[0]
            
            if best_match['similarity'] > 0.45:
                return best_match['pwd_code'], best_match['specification_text'], best_match['measurement_unit'], float(best_match['unit_rate']), 1

    conn.close()
    return "N/A", user_description, "N/A", 0.00, 0
