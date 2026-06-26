# utils/db_helpers.py

import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

@st.cache_data(ttl=300)
def get_company_tenders_cached(company_id: int) -> pd.DataFrame:
    """Cached helper to fetch company tenders as DataFrame"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
            t.division, t.district, t.thana, t.country, t.procurement_type,
            t.official_estimate, t.submission_deadline, t.tender_security,
            t.document_fee, t.evaluation_type,
            t.is_locked, t.is_copy, t.original_tender_id, t.is_active,
            t.created_at, t.updated_at
        FROM company_tenders t
        WHERE t.company_id = ? 
        ORDER BY t.created_at DESC
        ''', (company_id,))
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        print(f"Failed to fetch cached tenders: {e}")
        return pd.DataFrame()