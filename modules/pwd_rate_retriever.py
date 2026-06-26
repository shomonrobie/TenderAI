# modules/pwd_rate_retriever.py

import pandas as pd
import streamlit as st
from database.unified_db_manager import UnifiedDatabaseManager

class PWDRateRetriever:
    """Helper to retrieve PWD rates from active version"""
    
    def __init__(self, db_instance):
        self.db = db_instance
    
    def get_active_version(self):
        """Get the active PWD version"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, version_name, edition_year 
            FROM rate_versions 
            WHERE is_active = 1 
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        return {'id': result[0], 'name': result[1], 'year': result[2]} if result else None
    
    def get_rate(self, pwd_code, zone="Dhaka"):
        """Get rate for a specific item code from active version"""
        active = self.get_active_version()
        if not active:
            return None
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cr.unit_rate 
            FROM pwd_rates cr
            JOIN pwd_children c ON cr.pwd_code = c.pwd_code
            WHERE c.pwd_code = ? 
            AND cr.zone_name = ?
            AND cr.version_id = ?
            LIMIT 1
        """, (pwd_code, zone, active['id']))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def search_items(self, search_term, limit=50):
        """Search for items in active version"""
        active = self.get_active_version()
        if not active:
            return pd.DataFrame()
        
        conn = self.db.get_connection()
        query = """
            SELECT pwd_code, description, unit 
            FROM pwd_children 
            WHERE version_id = ? 
            AND (pwd_code LIKE ? OR description LIKE ?)
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(active['id'], f"%{search_term}%", f"%{search_term}%", limit))
        conn.close()
        return df
