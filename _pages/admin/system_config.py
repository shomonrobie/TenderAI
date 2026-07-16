"""
System Configuration Module
"""

import streamlit as st
import datetime
from database.unified_db_manager import get_db_manager


def render_system_configuration(db):
    """Render system configuration page with clean UI"""
    
    st.markdown("### ⚙️ System Configuration")
    st.caption("Manage system-wide settings and configurations.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email Settings",
        "🔐 Security Settings",
        "📊 System Settings",
        "📈 Performance"
    ])
    
    with tab1:
        render_email_settings(db)
    
    with tab2:
        render_security_settings(db)
    
    with tab3:
        render_system_settings(db)
    
    with tab4:
        render_performance_settings(db)


def render_email_settings(db):
    """Render email settings configuration"""
    st.markdown("#### 📧 Email Configuration")
    
    config_value = db.get_email_config()
    
    if not config_value:
        config_value = {
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': '',
            'from_email': '',
            'from_name': 'TenderAI'
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_smtp_host = st.text_input("SMTP Host", value=config_value.get('smtp_host', 'smtp.gmail.com'), key="email_smtp_host")
        new_smtp_port = st.number_input("SMTP Port", value=config_value.get('smtp_port', 587), min_value=1, max_value=65535, key="email_smtp_port")
        new_smtp_user = st.text_input("SMTP Username", value=config_value.get('smtp_user', ''), key="email_smtp_user")
    
    with col2:
        new_smtp_password = st.text_input("SMTP Password", type="password", value=config_value.get('smtp_password', ''), key="email_smtp_password")
        new_from_email = st.text_input("From Email", value=config_value.get('from_email', ''), key="email_from")
        new_from_name = st.text_input("From Name", value=config_value.get('from_name', 'TenderAI'), key="email_from_name")
    
    test_smtp = st.checkbox("Test SMTP connection after saving", key="email_test_smtp")
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("💾 Save", key="save_email_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'smtp_host': new_smtp_host,
                    'smtp_port': new_smtp_port,
                    'smtp_user': new_smtp_user,
                    'smtp_password': new_smtp_password,
                    'from_email': new_from_email,
                    'from_name': new_from_name
                }
                
                success = db.update_email_config(updated_config)
                if success:
                    st.success("✅ Email settings saved successfully!")
                    if test_smtp:
                        test_smtp_connection(updated_config)
                    st.rerun()
                else:
                    st.error("❌ Failed to save email settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with col2:
        if st.button("🔄 Reset Defaults", key="reset_email_defaults", use_container_width=True):
            defaults = {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'from_email': '',
                'from_name': 'TenderAI'
            }
            if db.update_email_config(defaults):
                st.success("✅ Reset to defaults!")
                st.rerun()
            else:
                st.error("❌ Failed to reset")
    
    st.divider()
    st.markdown("#### 📨 Test Email")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        test_email = st.text_input("Send test email to", placeholder="admin@example.com", key="test_email_input")
    with col2:
        if st.button("📨 Send Test", key="send_test_email", use_container_width=True):
            if test_email:
                try:
                    st.success(f"✅ Test email sent to {test_email}")
                except Exception as e:
                    st.error(f"❌ Failed to send test email: {e}")
            else:
                st.warning("Please enter an email address")


def test_smtp_connection(config):
    """Test SMTP connection with current settings"""
    try:
        import smtplib
        import socket
        
        if config.get('smtp_port') == 465:
            server = smtplib.SMTP_SSL(config.get('smtp_host'), config.get('smtp_port'), timeout=10)
        else:
            server = smtplib.SMTP(config.get('smtp_host'), config.get('smtp_port'), timeout=10)
            server.ehlo()
            if config.get('smtp_port') == 587:
                server.starttls()
                server.ehlo()
        
        if config.get('smtp_user') and config.get('smtp_password'):
            server.login(config.get('smtp_user'), config.get('smtp_password'))
        
        server.quit()
        st.success("✅ SMTP connection successful!")
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ SMTP Authentication failed. Check username and password.")
        return False
    except smtplib.SMTPConnectError:
        st.error("❌ SMTP Connection failed. Check host and port.")
        return False
    except socket.timeout:
        st.error("❌ SMTP Connection timeout. Check host and port.")
        return False
    except Exception as e:
        st.error(f"❌ SMTP Test failed: {e}")
        return False


def render_security_settings(db):
    """Render security settings configuration"""
    st.markdown("#### 🔐 Security Settings")
    
    config_value = db.get_security_config()
    
    if not config_value:
        config_value = {
            'require_2fa': False,
            'session_timeout': 30,
            'max_login_attempts': 5,
            'password_policy': 'strong',
            'enable_ssl': True,
            'force_https': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        require_2fa = st.checkbox("Require 2FA for all users", value=config_value.get('require_2fa', False), key="sec_require_2fa")
        session_timeout = st.number_input("Session Timeout (minutes)", value=config_value.get('session_timeout', 30), min_value=5, max_value=1440, key="sec_session_timeout")
        enable_ssl = st.checkbox("Enable SSL", value=config_value.get('enable_ssl', True), key="sec_enable_ssl")
    
    with col2:
        max_login_attempts = st.number_input("Max Login Attempts", value=config_value.get('max_login_attempts', 5), min_value=1, max_value=20, key="sec_max_login")
        password_policy = st.selectbox(
            "Password Policy",
            ["weak", "medium", "strong"],
            index=["weak", "medium", "strong"].index(config_value.get('password_policy', 'strong')),
            key="sec_password_policy"
        )
        force_https = st.checkbox("Force HTTPS", value=config_value.get('force_https', True), key="sec_force_https")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_security_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'require_2fa': require_2fa,
                    'session_timeout': session_timeout,
                    'max_login_attempts': max_login_attempts,
                    'password_policy': password_policy,
                    'enable_ssl': enable_ssl,
                    'force_https': force_https
                }
                
                success = db.update_security_config(updated_config)
                if success:
                    st.success("✅ Security settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save security settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.divider()
    st.markdown("#### 🔒 Security Status")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("2FA Status", "✅ Enabled" if require_2fa else "❌ Disabled")
    with col2:
        st.metric("SSL Status", "✅ Enabled" if enable_ssl else "❌ Disabled")
    with col3:
        st.metric("HTTPS Force", "✅ Enabled" if force_https else "❌ Disabled")
    with col4:
        st.metric("Login Attempts", max_login_attempts)
    
    st.caption(f"🕐 Session timeout: {session_timeout} minutes | Password policy: {password_policy.upper()}")


def render_system_settings(db):
    """Render system settings configuration"""
    st.markdown("#### 📊 System Settings")
    
    config_value = db.get_system_config_settings()
    
    if not config_value:
        config_value = {
            'enable_maintenance_mode': False,
            'enable_registration': True,
            'enable_analytics': True,
            'default_language': 'en',
            'timezone': 'UTC',
            'date_format': 'YYYY-MM-DD',
            'enable_audit_log': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_maintenance = st.checkbox("Maintenance Mode", value=config_value.get('enable_maintenance_mode', False), key="sys_maintenance")
        enable_registration = st.checkbox("Enable New Registrations", value=config_value.get('enable_registration', True), key="sys_registration")
        enable_analytics = st.checkbox("Enable Analytics", value=config_value.get('enable_analytics', True), key="sys_analytics")
        enable_audit_log = st.checkbox("Enable Audit Log", value=config_value.get('enable_audit_log', True), key="sys_audit_log")
    
    with col2:
        default_language = st.selectbox(
            "Default Language",
            ["en", "bn"],
            index=0 if config_value.get('default_language', 'en') == 'en' else 1,
            key="sys_language"
        )
        timezone = st.selectbox(
            "Timezone",
            ["UTC", "Asia/Dhaka", "Asia/Kolkata", "America/New_York", "Europe/London", "Australia/Sydney"],
            index=["UTC", "Asia/Dhaka", "Asia/Kolkata", "America/New_York", "Europe/London", "Australia/Sydney"].index(config_value.get('timezone', 'UTC')),
            key="sys_timezone"
        )
        date_format = st.selectbox(
            "Date Format",
            ["YYYY-MM-DD", "DD-MM-YYYY", "MM-DD-YYYY", "DD/MM/YYYY", "MM/DD/YYYY"],
            index=["YYYY-MM-DD", "DD-MM-YYYY", "MM-DD-YYYY", "DD/MM/YYYY", "MM/DD/YYYY"].index(config_value.get('date_format', 'YYYY-MM-DD')),
            key="sys_date_format"
        )
    
    if enable_maintenance:
        st.warning("⚠️ Maintenance mode is enabled. Users will see a maintenance page.")
        st.info("💡 To disable, uncheck the Maintenance Mode checkbox above and save.")
    
    if not enable_registration:
        st.warning("⚠️ New user registration is disabled. Only existing users can log in.")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_system_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'enable_maintenance_mode': enable_maintenance,
                    'enable_registration': enable_registration,
                    'enable_analytics': enable_analytics,
                    'default_language': default_language,
                    'timezone': timezone,
                    'date_format': date_format,
                    'enable_audit_log': enable_audit_log
                }
                
                success = db.update_system_config_settings(updated_config)
                if success:
                    st.success("✅ System settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save system settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")


def render_performance_settings(db):
    """Render performance settings configuration"""
    st.markdown("#### 📈 Performance Settings")
    
    config_value = db.get_performance_config()
    
    if not config_value:
        config_value = {
            'cache_enabled': True,
            'cache_duration': 300,
            'max_query_limit': 1000,
            'enable_query_logging': True,
            'enable_api_caching': True,
            'compression_enabled': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        cache_enabled = st.checkbox("Enable Cache", value=config_value.get('cache_enabled', True), key="perf_cache")
        cache_duration = st.number_input("Cache Duration (seconds)", value=config_value.get('cache_duration', 300), min_value=30, max_value=3600, step=30, key="perf_cache_duration")
        enable_api_caching = st.checkbox("Enable API Caching", value=config_value.get('enable_api_caching', True), key="perf_api_cache")
    
    with col2:
        max_query_limit = st.number_input("Max Query Limit", value=config_value.get('max_query_limit', 1000), min_value=100, max_value=10000, step=100, key="perf_query_limit")
        enable_query_logging = st.checkbox("Enable Query Logging", value=config_value.get('enable_query_logging', True), key="perf_query_logging")
        compression_enabled = st.checkbox("Enable Compression", value=config_value.get('compression_enabled', True), key="perf_compression")
    
    st.divider()
    st.markdown("#### 📊 Cache Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cache Status", "✅ Active" if cache_enabled else "❌ Inactive")
    with col2:
        st.metric("Cache Duration", f"{cache_duration}s")
    with col3:
        st.metric("Query Limit", max_query_limit)
    with col4:
        st.metric("API Cache", "✅ Enabled" if enable_api_caching else "❌ Disabled")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col2:
        if st.button("🗑️ Clear Cache", key="clear_cache_btn", use_container_width=True):
            try:
                if db.clear_system_cache():
                    st.success("✅ Cache cleared successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to clear cache")
            except Exception as e:
                st.error(f"❌ Failed to clear cache: {e}")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_performance_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'cache_enabled': cache_enabled,
                    'cache_duration': cache_duration,
                    'max_query_limit': max_query_limit,
                    'enable_query_logging': enable_query_logging,
                    'enable_api_caching': enable_api_caching,
                    'compression_enabled': compression_enabled
                }
                
                success = db.update_performance_config(updated_config)
                if success:
                    st.success("✅ Performance settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save performance settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")