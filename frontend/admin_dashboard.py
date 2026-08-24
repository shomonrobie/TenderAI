"""
Admin Dashboard - Main Entry Point
Combines all admin modules into a single dashboard
"""

import streamlit as st
from database.unified_db_manager import get_db_manager

from _pages.admin.components import render_metric_row, render_common_admin_styles
from _pages.admin.user_management import render_user_management
from _pages.admin.company_management import render_company_management
from _pages.admin.subscription_management import render_subscription_management
from _pages.admin.role_management import render_role_management
from _pages.admin.system_config import render_system_configuration
from _pages.admin.database_backup import render_database_backup
from _pages.admin.pwd_management import (
    render_pwd_ingestion_panel,
    render_pwd_verification_tool,
    render_hierarchical_pwd_viewer,
    render_pwd_version_tab
)
from _pages.admin.permission_management import render_permission_management  # ✅ NEW


def render_admin_overview(db):
    """Render system overview with stats"""
    st.markdown("### System Overview")
    
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    metrics = {
        "total_users": len(all_users),
        "active_users": len([u for u in all_users if u.get('is_active', False)]) if all_users else 0,
        "companies": len(set([u.get('company_name', 'N/A') for u in all_users if u.get('company_name') and u.get('company_name') != 'N/A'])) if all_users else 0,
        "paid_subs": len([s for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0,
        "total_analyses": sum([u.get('analyses_count', 0) for u in all_users]) if all_users else 0,
        "revenue": sum([s.get('amount', 0) for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0
    }
    
    render_metric_row(metrics)
    
    # User growth chart
    try:
        user_growth_data = db.get_user_growth(6)
        if user_growth_data and len(user_growth_data) > 0:
            import pandas as pd
            user_growth = pd.DataFrame(user_growth_data)
            if 'month' in user_growth.columns and 'count' in user_growth.columns:
                user_growth['count'] = pd.to_numeric(user_growth['count'], errors='coerce').fillna(0)
                user_growth = user_growth.sort_values('month')
                st.line_chart(user_growth.set_index('month')['count'])
            else:
                st.info("User growth data format is unexpected.")
        else:
            st.info("No user growth data available yet.")
    except Exception as e:
        st.warning(f"Could not load user growth chart: {str(e)}")

def show():
    """Main admin dashboard page"""
    
    db = get_db_manager()
    
    # Render common styles
    render_common_admin_styles()
    
    # Header
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div>
            <h1 style="margin: 0;">👑 Admin Dashboard</h1>
            <p style="margin: 0; color: #64748b;">System-wide administration and monitoring</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================================
    # MAIN TABS - Added Permissions Tab
    # ============================================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "👑 Overview",
        "👥 Users",
        "🏢 Companies",
        "💳 Subscriptions",
        "🔐 Roles",
        "🔑 Permissions",      # ✅ NEW TAB
        "🏗️ Rate Import",
        "⚙️ System Config",
        "💾 Database Backup"
    ])
    
    # ===== TAB 1: OVERVIEW =====
    with tab1:
        render_admin_overview(db)
    
    # ===== TAB 2: USERS =====
    with tab2:
        render_user_management(db)
    
    # ===== TAB 3: COMPANIES =====
    with tab3:
        render_company_management(db)
    
    # ===== TAB 4: SUBSCRIPTIONS =====
    with tab4:
        render_subscription_management(db)
    
    # ===== TAB 5: ROLES =====
    with tab5:
        render_role_management(db)
    
    # ===== TAB 6: PERMISSIONS =====
    with tab6:
        render_permission_management(db)
    
    # ===== TAB 7: RATE IMPORT =====
    with tab7:
        from modules.unified_import_wizard import render_unified_import_wizard
        render_unified_import_wizard(db)
    
    # ===== TAB 8: SYSTEM CONFIG =====
    with tab8:
        render_system_configuration(db)
    
    # ===== TAB 9: DATABASE BACKUP =====
    with tab9:
        render_database_backup()



__all__ = ['show']