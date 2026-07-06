# config/database.py
"""Database configuration - supports multiple databases"""

import os
from pathlib import Path
from urllib.parse import urlparse

# Try to get config from settings first
try:
    from config.settings import DATABASE_CONFIG, USE_SUPABASE
    print(f"✅ Using database config from settings.py")
except ImportError:
    # Fallback to direct environment reading
    print("⚠️ Could not import settings, reading from environment directly")
    USE_SUPABASE = os.getenv("USE_SUPABASE", "False").lower() == "true"
    
    # Check Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            if "USE_SUPABASE" in st.secrets:
                USE_SUPABASE = st.secrets["USE_SUPABASE"].lower() == "true"
            if "SUPABASE_URL" in st.secrets:
                USE_SUPABASE = True
    except:
        pass
    
    if USE_SUPABASE:
        # Get credentials
        supabase_url = os.getenv('SUPABASE_URL', '')
        supabase_key = os.getenv('SUPABASE_KEY', '')
        
        # Override from Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                if 'SUPABASE_URL' in st.secrets:
                    supabase_url = st.secrets['SUPABASE_URL']
                if 'SUPABASE_KEY' in st.secrets:
                    supabase_key = st.secrets['SUPABASE_KEY']
                if 'connections' in st.secrets and 'supabase' in st.secrets['connections']:
                    supabase_config = st.secrets['connections']['supabase']
                    supabase_url = supabase_config.get('SUPABASE_URL', supabase_url)
                    supabase_key = supabase_config.get('SUPABASE_KEY', supabase_key)
        except:
            pass
        
        DATABASE_CONFIG = {
            'type': 'supabase',
            'url': supabase_url,
            'key': supabase_key,
        }
    else:
        DATABASE_CONFIG = {
            'type': 'sqlite',
            'path': 'data/tender_system.db'
        }

# Set DB_TYPE
DB_TYPE = DATABASE_CONFIG.get('type', 'sqlite')

if DB_TYPE == 'supabase':
    print(f"✅ Using Supabase database")
    print(f"🔗 Supabase URL: {DATABASE_CONFIG.get('url', '')[:30] if DATABASE_CONFIG.get('url') else 'MISSING'}...")
else:
    print(f"✅ Using SQLite database at: {DATABASE_CONFIG.get('path', 'data/tender_system.db')}")

# Export for use in other modules
DB_CONFIG = DATABASE_CONFIG