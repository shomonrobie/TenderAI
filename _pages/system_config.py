# _pages/system_config.py - Admin configuration page

import streamlit as st

def show():
    """System Configuration Page - Admin only"""
    
    if st.session_state.user_role not in ['admin', 'system_admin']:
        st.error("🔒 Access denied. Admin privileges required.")
        return
    
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ System Configuration</h1>
        <p>Manage system-wide settings including extension configuration</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🤖 Extension Settings", "📊 System Info"])
    
    with tab1:
        render_extension_settings()
    
    with tab2:
        render_system_info()

def render_extension_settings():
    """Render extension configuration settings"""
    from _pages.extension_download import get_system_api_url, save_system_api_url
    
    st.markdown("### Extension Configuration")
    
    current_url = get_system_api_url()
    
    st.info(f"Current API URL: **{current_url}**")
    
    new_url = st.text_input(
        "API Base URL",
        value=current_url,
        help="The URL where the TenderAI backend is hosted. The extension will connect to this URL."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            if save_system_api_url(new_url):
                st.success("✅ Configuration saved! Users need to re-download the extension to get the new URL.")
            else:
                st.error("Failed to save configuration")
    
    with col2:
        st.caption("Changes require users to re-download the extension")

def render_system_info():
    """Render system information"""
    import os
    from datetime import datetime
    
    st.markdown("### System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Environment")
        st.write(f"**Python Version:** {os.sys.version}")
        st.write(f"**Working Directory:** {os.getcwd()}")
        
        # Check if running on Streamlit Cloud
        is_cloud = os.environ.get('STREAMLIT_SHARING') or os.environ.get('STREAMLIT_CLOUD')
        st.write(f"**Streamlit Cloud:** {'Yes' if is_cloud else 'No'}")
        
        if is_cloud:
            st.write(f"**App URL:** https://itender-bd.streamlit.app")
    
    with col2:
        st.markdown("#### Database Stats")
        from database.unified_db_manager import UnifiedDatabaseManager
        db = UnifiedDatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Count companies
        cursor.execute("SELECT COUNT(*) FROM companies")
        company_count = cursor.fetchone()[0]
        
        # Count extension downloads
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_downloads'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM extension_downloads")
            download_count = cursor.fetchone()[0]
        else:
            download_count = 0
        
        conn.close()
        
        st.metric("Total Users", user_count)
        st.metric("Total Companies", company_count)
        st.metric("Extension Downloads", download_count)