# modules/navigation.py

import streamlit as st
from utils.helpers import navigate_to

def render_top_navigation():
    """Render top navigation bar for all authenticated pages"""
    
    # Get user role
    user_role = st.session_state.get('user_role', 'viewer')
    is_admin = user_role in ['admin', 'system_admin']
    current_page = st.session_state.get('page', 'dashboard')
    
    # Define navigation items
    if is_admin:
        nav_items = [
            {"label": "🏠 Dashboard", "page": "dashboard", "icon": "🏠"},
            {"label": "📝 Rate Mgmt", "page": "rate_management", "icon": "📝"},
            {"label": "📥 Import", "page": "import_wizard", "icon": "📥"},
            {"label": "👥 Users", "page": "user_management", "icon": "👥"},
            {"label": "📋 Tenders", "page": "tender_management", "icon": "📋"},
            {"label": "💳 Subscriptions", "page": "subscription", "icon": "💳"},
            {"label": "⚙️ Admin", "page": "admin_dashboard", "icon": "⚙️"}
        ]
    else:
        nav_items = [
            {"label": "🏠 Dashboard", "page": "dashboard", "icon": "🏠"},
            {"label": "📋 Tenders", "page": "tender_management", "icon": "📋"},
            {"label": "📊 BOQ", "page": "boq_generator", "icon": "📊"},
            {"label": "🎯 Optimizer", "page": "boq_bid_optimizer", "icon": "🎯"},
            {"label": "📈 Reports", "page": "analysis_history", "icon": "📈"},
            {"label": "👥 Team", "page": "user_management", "icon": "👥"},
            {"label": "💳 Plan", "page": "subscription", "icon": "💳"}
        ]
    
    # CSS for top navigation
    st.markdown("""
    <style>
    .top-nav {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 0.5rem 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
    }
    .nav-buttons {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
    }
    .nav-btn {
        background: rgba(255,255,255,0.1);
        border: none;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        color: white;
        cursor: pointer;
        font-size: 0.85rem;
        transition: all 0.2s;
    }
    .nav-btn:hover {
        background: rgba(255,255,255,0.25);
    }
    .nav-btn-active {
        background: #22c55e;
        color: white;
    }
    .user-info {
        color: white;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .logout-btn {
        background: #ef4444;
        border: none;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        color: white;
        cursor: pointer;
        font-size: 0.85rem;
    }
    .logout-btn:hover {
        background: #dc2626;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create columns for navigation buttons
    cols = st.columns(len(nav_items) + 2)  # +2 for user info and logout
    
    # Navigation buttons
    for i, item in enumerate(nav_items):
        with cols[i]:
            button_style = "primary" if current_page == item['page'] else "secondary"
            if st.button(item["label"], key=f"nav_{item['page']}", use_container_width=True, type=button_style):
                st.session_state.page = item["page"]
                st.rerun()
    
    # User info
    with cols[-2]:
        full_name = st.session_state.get('full_name', 'User')[:15]
        st.markdown(f"<div style='text-align: right; color: white; padding: 0.3rem;'>👋 {full_name}</div>", unsafe_allow_html=True)
    
    # Logout button
    with cols[-1]:
        if st.button("🚪 Logout", key="top_logout", use_container_width=True):
            # Clear session
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode']:
                    del st.session_state[key]
            st.session_state.logged_in = False
            st.session_state.page = "home"
            st.rerun()
    
    st.markdown("---")


def render_page_header(title, description=None):
    """Render page header with consistent styling"""
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                padding: 1.2rem 1.5rem; 
                border-radius: 12px; 
                margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1e3c72;">{title}</h1>
        {f'<p style="margin: 0.5rem 0 0 0; color: #555;">{description}</p>' if description else ''}
    </div>
    """, unsafe_allow_html=True)