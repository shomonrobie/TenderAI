# config/settings.py
"""
TenderAI Configuration Settings
Centralized configuration for the entire application
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if exists
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# =============================================================================
# 📐 BASE PATHS
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'tender_system.db'

# Create data directory if not exists
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# 📐 DEBUG & LOGGING
# =============================================================================
DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'

def debug_print(*args, **kwargs):
    """Print debug messages only when DEBUG_MODE is True"""
    if DEBUG_MODE:
        print(*args, **kwargs)

# =============================================================================
# 📐 BID CALCULATION CONSTANTS
# =============================================================================
COST_ESTIMATE_RATIO = float(os.getenv('COST_ESTIMATE_RATIO', '0.85'))
BID_RATIO_DECIMALS = int(os.getenv('BID_RATIO_DECIMALS', '4'))
BID_AMOUNT_DECIMALS = int(os.getenv('BID_AMOUNT_DECIMALS', '3'))

# =============================================================================
# 📐 PPR CONFIGURATION
# =============================================================================
PPR_CONFIG = {
    'nppi_factor': float(os.getenv('PPR_NPPI_FACTOR', '0.920')),
    'weights': {
        'competitor_avg': float(os.getenv('PPR_WEIGHT_COMPETITOR', '0.5')),
        'official_est': float(os.getenv('PPR_WEIGHT_OFFICIAL', '0.2')),
        'nppi': float(os.getenv('PPR_WEIGHT_NPPI', '0.3'))
    },
    'slt_buffer': float(os.getenv('PPR_SLT_BUFFER', '1.0'))
}

# =============================================================================
# 📐 DATABASE CONFIGURATION
# =============================================================================
DATABASE_CONFIG = {
    'path': str(DB_PATH),
    'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
    'timeout': int(os.getenv('DB_TIMEOUT', '30'))
}

# =============================================================================
# 📐 OTP & EMAIL CONFIGURATION (Default - Email OTP always enabled)
# =============================================================================

# Email settings (always available, prints to console if not configured)
EMAIL_CONFIG = {
    'enabled': os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
    'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'smtp_user': os.getenv('SMTP_USER', ''),
    'smtp_password': os.getenv('SMTP_PASSWORD', ''),
    'from_email': os.getenv('SMTP_FROM_EMAIL', 'noreply@tenderai.com'),
    'from_name': os.getenv('SMTP_FROM_NAME', 'TenderAI')
}

# SMS settings (disabled by default - admin can enable)
SMS_CONFIG = {
    'enabled': os.getenv('SMS_ENABLED', 'false').lower() == 'true',
    'test_mode': os.getenv('SMS_TEST_MODE', 'true').lower() == 'true',
    'provider': os.getenv('SMS_PROVIDER', 'test'),
    'ssl_wireless_api_key': os.getenv('SSL_WIRELESS_API_KEY', ''),
    'ssl_wireless_sid': os.getenv('SSL_WIRELESS_SID', ''),
    'twilio_account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
    'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
    'twilio_phone_number': os.getenv('TWILIO_PHONE_NUMBER', '')
}

# OTP settings
OTP_CONFIG = {
    'enabled': os.getenv('OTP_ENABLED', 'true').lower() == 'true',
    'length': int(os.getenv('OTP_LENGTH', '6')),
    'expiry_minutes': int(os.getenv('OTP_EXPIRY_MINUTES', '10')),
    'max_attempts': int(os.getenv('OTP_MAX_ATTEMPTS', '3'))
}

# Login settings
LOGIN_CONFIG = {
    'allow_password': os.getenv('ALLOW_PASSWORD_LOGIN', 'true').lower() == 'true',
    'allow_otp': os.getenv('ALLOW_OTP_LOGIN', 'true').lower() == 'true',
    'require_email_verification': os.getenv('REQUIRE_EMAIL_VERIFICATION', 'true').lower() == 'true',
    'session_timeout_minutes': int(os.getenv('SESSION_TIMEOUT_MINUTES', '30')),
    'remember_me_days': int(os.getenv('REMEMBER_ME_DAYS', '30'))
}

# =============================================================================
# 📐 CONFIGURATION CLASS (for database storage)
# =============================================================================

class Config:
    """
    Configuration class that can be stored in database
    Used by OTP service and other modules
    """
    
    # OTP Settings
    OTP_ENABLED = OTP_CONFIG['enabled']
    OTP_LENGTH = OTP_CONFIG['length']
    OTP_EXPIRY_MINUTES = OTP_CONFIG['expiry_minutes']
    OTP_MAX_ATTEMPTS = OTP_CONFIG['max_attempts']
    DEBUG_OTP_PRINT = True  # ← Add this line

    
    # Email Settings
    EMAIL_ENABLED = EMAIL_CONFIG['enabled']
    SMTP_HOST = EMAIL_CONFIG['smtp_host']
    SMTP_PORT = EMAIL_CONFIG['smtp_port']
    SMTP_USER = EMAIL_CONFIG['smtp_user']
    SMTP_PASSWORD = EMAIL_CONFIG['smtp_password']
    SMTP_FROM_EMAIL = EMAIL_CONFIG['from_email']
    SMTP_FROM_NAME = EMAIL_CONFIG['from_name']
    
    # SMS Settings
    SMS_ENABLED = SMS_CONFIG['enabled']
    SMS_TEST_MODE = SMS_CONFIG['test_mode']
    SMS_PROVIDER = SMS_CONFIG['provider']
    SSL_WIRELESS_API_KEY = SMS_CONFIG['ssl_wireless_api_key']
    SSL_WIRELESS_SID = SMS_CONFIG['ssl_wireless_sid']
    TWILIO_ACCOUNT_SID = SMS_CONFIG['twilio_account_sid']
    TWILIO_AUTH_TOKEN = SMS_CONFIG['twilio_auth_token']
    TWILIO_PHONE_NUMBER = SMS_CONFIG['twilio_phone_number']
    
    # Login Settings
    ALLOW_PASSWORD_LOGIN = LOGIN_CONFIG['allow_password']
    ALLOW_OTP_LOGIN = LOGIN_CONFIG['allow_otp']
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get configuration value by key (for compatibility with database config)"""
        return getattr(cls, key, default)
    
    @classmethod
    def is_otp_login_enabled(cls) -> bool:
        """Check if OTP login is enabled"""
        return cls.ALLOW_OTP_LOGIN and cls.OTP_ENABLED
    
    @classmethod
    def is_sms_available(cls) -> bool:
        """Check if SMS is configured and available"""
        if not cls.SMS_ENABLED:
            return False
        
        if cls.SMS_PROVIDER == 'ssl_wireless':
            return bool(cls.SSL_WIRELESS_API_KEY and cls.SSL_WIRELESS_SID)
        elif cls.SMS_PROVIDER == 'twilio':
            return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN)
        else:
            return cls.SMS_TEST_MODE
    
    @classmethod
    def get_otp_config(cls) -> dict:
        """Get all OTP configuration"""
        return {
            'enabled': cls.OTP_ENABLED,
            'login_enabled': cls.ALLOW_OTP_LOGIN,
            'length': cls.OTP_LENGTH,
            'expiry_minutes': cls.OTP_EXPIRY_MINUTES,
            'max_attempts': cls.OTP_MAX_ATTEMPTS,
            'sms_available': cls.is_sms_available(),
            'test_mode': cls.SMS_TEST_MODE
        }


# =============================================================================
# 📐 HELPER FUNCTIONS
# =============================================================================

def get_db_path() -> str:
    """Get database path"""
    return str(DB_PATH)


def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return DEBUG_MODE


def reload_from_env():
    """Reload configuration from environment variables (useful for admin settings)"""
    global DEBUG_MODE, PPR_CONFIG, OTP_CONFIG, LOGIN_CONFIG
    
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'
    
    PPR_CONFIG = {
        'nppi_factor': float(os.getenv('PPR_NPPI_FACTOR', '0.920')),
        'weights': {
            'competitor_avg': float(os.getenv('PPR_WEIGHT_COMPETITOR', '0.5')),
            'official_est': float(os.getenv('PPR_WEIGHT_OFFICIAL', '0.2')),
            'nppi': float(os.getenv('PPR_WEIGHT_NPPI', '0.3'))
        },
        'slt_buffer': float(os.getenv('PPR_SLT_BUFFER', '1.0'))
    }
    
    OTP_CONFIG = {
        'enabled': os.getenv('OTP_ENABLED', 'true').lower() == 'true',
        'length': int(os.getenv('OTP_LENGTH', '6')),
        'expiry_minutes': int(os.getenv('OTP_EXPIRY_MINUTES', '10')),
        'max_attempts': int(os.getenv('OTP_MAX_ATTEMPTS', '3'))
    }
    
    LOGIN_CONFIG = {
        'allow_password': os.getenv('ALLOW_PASSWORD_LOGIN', 'true').lower() == 'true',
        'allow_otp': os.getenv('ALLOW_OTP_LOGIN', 'true').lower() == 'true',
        'require_email_verification': os.getenv('REQUIRE_EMAIL_VERIFICATION', 'true').lower() == 'true',
        'session_timeout_minutes': int(os.getenv('SESSION_TIMEOUT_MINUTES', '30')),
        'remember_me_days': int(os.getenv('REMEMBER_ME_DAYS', '30'))
    }
    
    # Update Config class
    Config.OTP_ENABLED = OTP_CONFIG['enabled']
    Config.OTP_LENGTH = OTP_CONFIG['length']
    Config.OTP_EXPIRY_MINUTES = OTP_CONFIG['expiry_minutes']
    Config.OTP_MAX_ATTEMPTS = OTP_CONFIG['max_attempts']
    Config.ALLOW_PASSWORD_LOGIN = LOGIN_CONFIG['allow_password']
    Config.ALLOW_OTP_LOGIN = LOGIN_CONFIG['allow_otp']


print(f"✅ Config loaded | Debug: {DEBUG_MODE} | DB: {DB_PATH}")