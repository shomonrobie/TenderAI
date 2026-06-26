# config/database.py
"""Database configuration - supports multiple databases"""

import os
from urllib.parse import urlparse

# Database settings from environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/tender_system.db')
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # sqlite, postgresql, mysql, cockroachdb

# Parse DATABASE_URL
def parse_database_url(url: str):
    """Parse database URL and return connection parameters"""
    
    if url.startswith('sqlite://'):
        # SQLite
        db_path = url.replace('sqlite:///', '')
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

DB_CONFIG = parse_database_url(DATABASE_URL)

# Connection pool settings
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))