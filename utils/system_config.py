# utils/system_config.py

import json
from datetime import datetime
from typing import Any, Optional
from database.unified_db_manager import db


class SystemConfig:
    """System configuration manager with caching"""
    
    _cache = {}
    _cache_time = None
    
    # Default configuration values
    DEFAULTS = {
        # OTP Settings
        'otp_enabled': False,
        'otp_login_enabled': False,
        'otp_verification_enabled': True,
        'otp_length': 6,
        'otp_expiry_minutes': 10,
        'otp_max_attempts': 3,
        
        # SMS Gateway Settings
        'sms_enabled': False,
        'sms_provider': 'test',  # test, ssl_wireless, twilio
        'sms_test_mode': True,   # Print to console instead of sending
        
        # SSL Wireless (Bangladesh)
        'ssl_wireless_api_key': '',
        'ssl_wireless_sid': '',
        
        # Twilio
        'twilio_account_sid': '',
        'twilio_auth_token': '',
        'twilio_phone_number': '',
        
        # Email Settings
        'email_enabled': False,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_user': '',
        'smtp_password': '',
        'smtp_from_email': 'noreply@tenderai.com',
        'smtp_from_name': 'TenderAI',
        
        # Feature Flags
        'allow_password_login': True,
        'allow_otp_login': False,  # Admin controls this
        'require_mobile_verification': True,
        'require_email_verification': False,
        
        # Security Settings
        'max_login_attempts': 5,
        'session_timeout_minutes': 30,
        'remember_me_days': 30
    }
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        
        # Check cache
        if key in cls._cache:
            return cls._cache[key]
        
        # Query database
        result = db.query_one("SELECT value FROM system_config WHERE key = ?", (key,))
        
        if result:
            value = result['value']
            # Try to parse JSON
            try:
                value = json.loads(value)
            except:
                pass
            cls._cache[key] = value
            return value
        
        # Return default
        default_value = cls.DEFAULTS.get(key, default)
        cls._cache[key] = default_value
        return default_value
    
    @classmethod
    def set(cls, key: str, value: Any, updated_by: int = None) -> bool:
        """Set configuration value"""
        
        # Convert to JSON for complex types
        if isinstance(value, (dict, list, bool)):
            value = json.dumps(value)
        elif isinstance(value, (int, float)):
            value = str(value)
        
        # Upsert
        db.execute("""
            INSERT OR REPLACE INTO system_config (key, value, updated_by, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (key, value, updated_by))
        
        # Clear cache
        cls._cache.pop(key, None)
        
        return True
    
    @classmethod
    def clear_cache(cls):
        """Clear configuration cache"""
        cls._cache = {}
    
    @classmethod
    def is_otp_login_enabled(cls) -> bool:
        """Check if OTP login is enabled"""
        return cls.get('allow_otp_login', False) and cls.get('otp_enabled', False)
    
    @classmethod
    def is_sms_available(cls) -> bool:
        """Check if SMS is configured and available"""
        if not cls.get('sms_enabled', False):
            return False
        
        provider = cls.get('sms_provider', 'test')
        
        if provider == 'ssl_wireless':
            return bool(cls.get('ssl_wireless_api_key')) and bool(cls.get('ssl_wireless_sid'))
        elif provider == 'twilio':
            return bool(cls.get('twilio_account_sid')) and bool(cls.get('twilio_auth_token'))
        else:
            return True  # Test mode always available
    
    @classmethod
    def get_otp_config(cls) -> dict:
        """Get all OTP-related configuration"""
        return {
            'enabled': cls.get('otp_enabled', False),
            'login_enabled': cls.get('allow_otp_login', False),
            'verification_enabled': cls.get('otp_verification_enabled', True),
            'length': cls.get('otp_length', 6),
            'expiry_minutes': cls.get('otp_expiry_minutes', 10),
            'max_attempts': cls.get('otp_max_attempts', 3),
            'sms_available': cls.is_sms_available(),
            'test_mode': cls.get('sms_test_mode', True)
        }


# Initialize default configuration if table is empty
def initialize_system_config():
    """Initialize system configuration with defaults"""
    
    for key, value in SystemConfig.DEFAULTS.items():
        existing = db.query_one("SELECT 1 FROM system_config WHERE key = ?", (key,))
        if not existing:
            if isinstance(value, bool):
                db_value = 'true' if value else 'false'
            elif isinstance(value, (dict, list)):
                db_value = json.dumps(value)
            else:
                db_value = str(value)
            
            db.execute("""
                INSERT INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, db_value))
    
    print("✅ System configuration initialized")