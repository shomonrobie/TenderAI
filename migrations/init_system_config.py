# migrations/init_system_config.py

import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.unified_db_manager import db


def init_system_config():
    """Initialize system configuration with defaults"""
    
    # Email OTP enabled by default (SMS disabled)
    default_configs = {
        # Email settings (working by default in test mode)
        'email_enabled': 'true',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': '587',
        'smtp_user': '',
        'smtp_password': '',
        'smtp_from_email': 'noreply@tenderai.com',
        'smtp_from_name': 'TenderAI',
        
        # SMS settings (disabled by default)
        'sms_enabled': 'false',
        'sms_test_mode': 'true',
        'sms_provider': 'test',
        
        # OTP settings
        'otp_enabled': 'true',
        'otp_length': '6',
        'otp_expiry_minutes': '10',
        'otp_max_attempts': '3',
        
        # Login settings
        'allow_password_login': 'true',
        'allow_otp_login': 'true',
        'require_email_verification': 'true',
        
        # General settings
        'system_name': 'TenderAI',
        'system_timezone': 'Asia/Dhaka',
    }
    
    for key, value in default_configs.items():
        existing = db.query_one("SELECT 1 FROM system_config WHERE key = ?", (key,))
        if not existing:
            db.execute("INSERT INTO system_config (key, value) VALUES (?, ?)", (key, value))
            print(f"✅ Config added: {key} = {value}")
        else:
            print(f"⏭️ Config already exists: {key}")
    
    print("\n✅ System configuration initialized!")


if __name__ == "__main__":
    init_system_config()