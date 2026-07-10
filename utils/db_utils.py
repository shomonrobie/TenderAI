# utils/db_utils.py - Refactored to use unified_db_manager methods

import streamlit as st
import os
from database.unified_db_manager import get_db_manager


def get_system_config(key, default=None):
    """Get system configuration value using db method"""
    db = get_db_manager()
    
    try:
        config = db.get_system_config(key)
        if config:
            return config.get('config_value', default)
        return default
    except Exception as e:
        print(f"Error getting config {key}: {e}")
        return default


def save_system_config(key, value):
    """Save system configuration value using db method"""
    db = get_db_manager()
    
    try:
        return db.update_system_config(key, value)
    except Exception as e:
        print(f"Error saving config {key}: {e}")
        return False


def get_default_api_url():
    """Get default API URL based on environment"""
    # For production
    if os.getenv('STREAMLIT_DEPLOYMENT', '').lower() == 'true':
        return "https://itender-bd.streamlit.app"
    # For local development
    return "http://localhost:8501"


def get_email_settings():
    """Get email configuration settings"""
    db = get_db_manager()
    return db.get_email_config()


def save_email_settings(settings):
    """Save email configuration settings"""
    db = get_db_manager()
    return db.update_email_config(settings)


def get_security_settings():
    """Get security configuration settings"""
    db = get_db_manager()
    return db.get_security_config()


def save_security_settings(settings):
    """Save security configuration settings"""
    db = get_db_manager()
    return db.update_security_config(settings)


def get_system_settings():
    """Get system configuration settings"""
    db = get_db_manager()
    return db.get_system_config_settings()


def save_system_settings(settings):
    """Save system configuration settings"""
    db = get_db_manager()
    return db.update_system_config_settings(settings)


def get_performance_settings():
    """Get performance configuration settings"""
    db = get_db_manager()
    return db.get_performance_config()


def save_performance_settings(settings):
    """Save performance configuration settings"""
    db = get_db_manager()
    return db.update_performance_config(settings)


def get_all_system_configs():
    """Get all system configurations"""
    db = get_db_manager()
    return db.get_all_system_configs()


def clear_cache():
    """Clear system cache"""
    db = get_db_manager()
    return db.clear_system_cache()


def is_maintenance_mode():
    """Check if maintenance mode is enabled"""
    db = get_db_manager()
    return db.get_maintenance_mode()


def is_registration_enabled():
    """Check if registration is enabled"""
    db = get_db_manager()
    return db.get_registration_status()


def get_default_language():
    """Get default language"""
    settings = get_system_settings()
    return settings.get('default_language', 'en')


def get_timezone():
    """Get configured timezone"""
    settings = get_system_settings()
    return settings.get('timezone', 'UTC')


def get_date_format():
    """Get configured date format"""
    settings = get_system_settings()
    return settings.get('date_format', 'YYYY-MM-DD')


def init_system_config():
    """Initialize system config table with defaults"""
    db = get_db_manager()
    return db.init_system_config_table()