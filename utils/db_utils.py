# Add these to your module or create a new file: utils/db_utils.py

import streamlit as st
from database.unified_db_manager import db


def get_system_config(key, default=None):
    """Get system configuration value (database agnostic)"""
    if not table_exists('system_config'):
        return default
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default
    except Exception as e:
        print(f"Error getting config {key}: {e}")
        return default


def save_system_config(key, value):
    """Save system configuration value (database agnostic)"""
    if not table_exists('system_config'):
        return False
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            return True
    except Exception as e:
        print(f"Error saving config {key}: {e}")
        return False


def get_default_api_url():
    """Get default API URL based on environment"""
    import os
    # For production
    if os.getenv('STREAMLIT_DEPLOYMENT', '').lower() == 'true':
        return "https://itender-bd.streamlit.app"
    # For local development
    return "http://localhost:8501"