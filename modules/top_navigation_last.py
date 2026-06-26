# modules/top_navigation.py

import streamlit as st
from modules.subscription import get_current_user_plan_name, is_premium_plan, get_plan
from modules.access_control import access_control
from modules.rbac import get_current_user_role


def render_top_navigation():
    """Render top navigation bar for authenticated users with role-based access"""
    
    current_page = st.session_state.get('page', 'dashboard')
    user_role = get_current_user_role()
    is_premium = is_premium_plan(get_current_user_plan_name())
    
    # Get accessible pages from access control
    accessible_pages = access_control.get_accessible_pages()
    
    # Define all possible navigation items with their page keys
    all_nav_items = [
        {"label": "🏠 Dashboard", "page": "dashboard", "group": "core"},
        {"label": "📊 Analytics", "page": "admin_analytics", "group": "admin"},
        {"label": "📊 Company Analytics", "page": "company_analytics", "group": "company"},
        {"label": "📝 Rate Management", "page": "rate_management", "group": "rates"},
        {"label": "📝 Company Rate Management", "page": "render_company_rate_management", "group": "rates"},
        
        {"label": "📊 Rate Viewer", "page": "rate_viewer", "group": "rates"},
        {"label": "📥 Import Wizard", "page": "import_wizard", "group": "rates"},
        {"label": "📋 Tenders", "page": "tender_management", "group": "tenders"},
        {"label": "📊 BOQ Generator", "page": "boq_generator", "group": "tenders"},
        {"label": "📈 Basic Optimizer", "page": "basic_bid_optimizer", "group": "optimization", "badge": "🆓"},
        {"label": "🎯 Advanced Optimizer", "page": "new_analysis", "group": "optimization", "badge": "⭐"},
        {"label": "🔮 Competitive Simulator", "page": "competitive_bid_simulator", "group": "optimization", "badge": "⭐"},
        {"label": "📈 Reports", "page": "analysis_history", "group": "analytics"},
        {"label": "👥 Competitor Tracking", "page": "competitor_tracking", "group": "analytics"},
        {"label": "🗂️ Competitor Master", "page": "competitor_master", "group": "analytics"},
        {"label": "🏢 Knowledge Repo", "page": "company_knowledge", "group": "company"},
        {"label": "📋 Post-Evaluation", "page": "post_evaluation", "group": "analytics"},
        {"label": "🧠 AI Suggestions", "page": "intelligent_suggestions", "group": "analytics"},
        {"label": "👥 Team Management", "page": "user_management", "group": "management"},
        {"label": "👥 User Approvals", "page": "user_approval", "group": "admin"},
        {"label": "🔐 Role Permissions", "page": "role_management", "group": "admin"},
        {"label": "🏢 All Companies", "page": "company_management", "group": "admin"},
        {"label": "📊 Admin Dashboard", "page": "admin_dashboard", "group": "admin"},
        {"label": "📊 BOQ Report", "page": "boq_admin_report", "group": "admin"},
        {"label": "🤖 Extension Admin", "page": "extension_admin", "group": "admin"},
        {"label": "🤖 Extension Usage", "page": "extension_usage", "group": "extensions"},
        {"label": "📥 Download Extension", "page": "extension_download", "group": "extensions"},
        {"label": "💳 Subscription", "page": "subscription", "group": "account"},
        {"label": "👤 Profile", "page": "profile", "group": "account"},
        {"label": "📖 Tutorial", "page": "tutorial", "group": "help"},
        {"label": "📦 Version Management", "page": "version_management", "group": "admin"},
        {"label": "🔄 Rollback Management", "page": "rollback_management", "group": "admin"},
        {"label": "🏗️ e-GP BOQ Workspace", "page": "egp_boq_workspace", "group": "tenders"},
    ]
    
    # Filter nav items based on accessible pages
    nav_items = [item for item in all_nav_items if item["page"] in accessible_pages]
    
    # =========================================================================
    # CSS
    # =========================================================================
    st.markdown("""
    <style>
    .top-nav-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 0.5rem 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .top-nav-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        justify-content: center;
    }
    .user-info {
        color: white;
        font-size: 0.8rem;
        text-align: right;
        padding: 0.3rem 0;
    }
    .premium-badge {
        background: #ffd700;
        color: #1e3c72;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 0.7rem;
        margin-left: 5px;
    }
    .free-badge {
        background: #6c757d;
        color: white;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 0.7rem;
        margin-left: 5px;
    }
    .nav-badge {
        font-size: 0.6rem;
        padding: 1px 6px;
        border-radius: 10px;
        margin-left: 3px;
    }
    .badge-premium {
        background: #ffd700;
        color: #1e3c72;
    }
    .badge-free {
        background: #6c757d;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # NAVIGATION BAR
    # =========================================================================
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Group navigation items
    grouped_items = _group_nav_items(nav_items, current_page)
    
    # Render groups
    for group_name, group_items in grouped_items.items():
        if group_items:
            # Create a row for each group
            cols = st.columns(len(group_items) + 1)  # +1 for separator
            
            # Group label
            with cols[0]:
                st.markdown(f"""
                <span style="color: rgba(255,255,255,0.5); font-size: 0.65rem; 
                             font-weight: 600; text-transform: uppercase; 
                             letter-spacing: 0.5px;">
                    {group_name}
                </span>
                """, unsafe_allow_html=True)
            
            # Nav buttons
            for idx, item in enumerate(group_items):
                with cols[idx + 1]:
                    is_active = current_page == item["page"]
                    
                    # Build button label with badge
                    label = item["label"]
                    badge = item.get("badge", "")
                    
                    if badge:
                        badge_class = "badge-premium" if "⭐" in badge else "badge-free"
                        label = f"{label} <span class='nav-badge {badge_class}'>{badge}</span>"
                    
                    if st.button(
                        label,
                        key=f"top_nav_{item['page']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                    ):
                        st.session_state.page = item["page"]
                        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =========================================================================
    # USER INFO BAR
    # =========================================================================
    _render_user_info_bar(user_role, is_premium)


def _group_nav_items(nav_items, current_page):
    """Group navigation items by category"""
    
    # Define group order and display names
    group_map = {
        "core": "Core",
        "tenders": "Tenders",
        "optimization": "Optimization",
        "analytics": "Analytics",
        "company": "Company",
        "rates": "Rates",
        "management": "Management",
        "admin": "Admin",
        "extensions": "Extensions",
        "account": "Account",
        "help": "Help"
    }
    
    grouped = {}
    for item in nav_items:
        group = item.get("group", "other")
        group_display = group_map.get(group, group.title())
        if group_display not in grouped:
            grouped[group_display] = []
        grouped[group_display].append(item)
    
    return grouped


def _render_user_info_bar(user_role, is_premium):
    """Render user info bar with role and premium status"""
    
    full_name = st.session_state.get('full_name', 'User')
    company_name = st.session_state.get('company_name', 'N/A')
    
    role_display = {
        'system_admin': '👑 SysAdmin',
        'admin': '👑 Admin',
        'company_admin': '🏢 Company Admin',
        'manager': '📊 Manager',
        'analyst': '📈 Analyst',
        'viewer': '👁️ Viewer'
    }.get(user_role, '👤 User')
    
    premium_text = "✨ PREMIUM" if is_premium else "🔓 FREE"
    premium_color = "#ffd700" if is_premium else "#6c757d"
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; 
                padding: 0.3rem 0; margin-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.1);">
        <div style="color: white; font-size: 0.8rem;">
            👋 {full_name} | {company_name}
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <span style="color: white; font-size: 0.8rem;">{role_display}</span>
            <span style="background: {premium_color}20; color: {premium_color}; 
                       border-radius: 12px; padding: 2px 10px; font-size: 0.7rem; 
                       font-weight: 600; border: 1px solid {premium_color};">
                {premium_text}
            </span>
            <button onclick="window.location.href='?page=subscription'" 
                    style="background: transparent; border: 1px solid rgba(255,255,255,0.3); 
                           color: white; border-radius: 4px; padding: 2px 12px; 
                           font-size: 0.7rem; cursor: pointer;">
                💳
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)