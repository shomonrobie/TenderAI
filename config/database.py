# config/database.py
"""Database configuration - supports multiple databases"""

import os
from urllib.parse import urlparse


# Check if Supabase is enabled
USE_SUPABASE = os.getenv("USE_SUPABASE", "False").lower() == "true"

# Also check Streamlit secrets
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            USE_SUPABASE = True
        if "SUPABASE_URL" in st.secrets:
            USE_SUPABASE = True
except:
    pass

if USE_SUPABASE:
    DB_TYPE = 'supabase'
    print("✅ Using Supabase database")
else:
    DB_TYPE = 'sqlite'
    print(f"✅ Using SQLite database")

# Database config
DB_CONFIG = {
    'type': DB_TYPE,
    'path': 'data/tender_system.db'  # Fallback for SQLite
}
print(f"✅ Using {DB_TYPE} database")


def parse_database_url(url: str):
    """Parse database URL and return connection parameters"""
    
    if url.startswith('sqlite://'):
        # SQLite
        db_path = url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            # Relative path - ensure data directory exists
            os.makedirs(os.path.dirname(db_path) or 'data', exist_ok=True)
        return {
            'type': 'sqlite',
            'path': db_path
        }
    else:
        # PostgreSQL, MySQL, CockroachDB
        parsed = urlparse(url)
        return {
            'type': parsed.scheme,
            'host': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password
        }


# Parse database URL for non-Supabase databases
if DB_TYPE != 'supabase':
    DB_CONFIG = parse_database_url(DATABASE_URL)
else:
    # Supabase configuration
    DB_CONFIG = {
        'type': 'supabase',
        'url': os.getenv('SUPABASE_URL', ''),
        'key': os.getenv('SUPABASE_KEY', ''),
    }
    
    # Override from Streamlit secrets if available
    try:
        import streamlit as st
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            supabase_config = st.secrets["connections"]["supabase"]
            DB_CONFIG['url'] = supabase_config.get('SUPABASE_URL', DB_CONFIG['url'])
            DB_CONFIG['key'] = supabase_config.get('SUPABASE_KEY', DB_CONFIG['key'])
    except:
        pass
    
    print(f"🔗 Supabase URL: {DB_CONFIG['url'][:30]}...")

# Connection pool settings
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))

# Database-specific settings
DB_SETTINGS = {
    'sqlite': {
        'timeout': 30,
        'check_same_thread': False,
    },
    'postgresql': {
        'sslmode': 'require' if os.getenv('DB_SSL', 'false').lower() == 'true' else 'disable',
        'connect_timeout': 10,
    },
    'supabase': {
        'sslmode': 'require',
        'connect_timeout': 30,
    }
}

def get_db_settings():
    """Get database-specific settings"""
    return DB_SETTINGS.get(DB_TYPE, {})