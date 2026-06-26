# modules/top_navigation.py
import streamlit as st
# modules/top_navigation.py - Fix the button syntax

def render_top_navigation():
    """Compact responsive top navigation"""
    
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    
    is_system_admin = user_role == 'system_admin'
    is_regular_admin = user_role == 'admin'
    is_company_admin = user_role == 'company_admin'
    is_manager = user_role == 'manager'
    is_analyst = user_role == 'analyst'
    is_viewer = user_role == 'viewer'
    
    sub = st.session_state.get('subscription', {})
    plan = sub.get('plan', 'free')
    is_premium = plan in ['professional', 'enterprise'] or is_system_admin or is_regular_admin

    # ==================== CSS ====================
    st.markdown("""
    <style>
    .top-nav-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 0.7rem 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .nav-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ==================== NAV ITEMS ====================
    if is_system_admin:
        nav_items = [
            ("🏠 Dash", "dashboard"), ("📊 Analytics", "admin_analytics"),
            ("📝 Rates", "rate_management"), ("📥 Import", "import_wizard"),
            ("📋 Tenders", "tender_management"), ("📊 BOQ", "boq_generator"),
            ("📈 Basic", "quick_bid"), ("🎯 Adv Opt", "advanced_bid"), ("🎯 AI Advisor", "ai_advisor"), 
            ("🔮 Simulator", "competitive_intel"), ("🏢 Knowledge", "company_knowledge"),
            ("🤖 Ext", "extension_admin"), ("💳 Subs", "subscription"),
            ("🤖 CompetitorMan", "competitor_master"),
            ("⚙️ Admin", "admin_dashboard"), 
            ("🚀 Onboarding", "company_onboarding"), 
            ("⚙️ Rate Mgmt", "company_rate_management"),
            ("📖 Tutorial", "tutorial")
        ]
    elif is_regular_admin:
        nav_items = [
            ("🏠 Dash", "dashboard"), ("📝 Rates", "rate_management"),
            ("📥 Import", "import_wizard"), ("📋 Tenders", "tender_management"),
            ("📊 BOQ", "boq_generator"), ("📈 Basic", "quick_bid"),
            ("🎯 Adv Opt", "advanced_bid"), ("🔮 Simulator", "competitive_intel"), ("🎯 AI Advisor", "ai_advisor"), 
            ("🏢 Knowledge", "company_knowledge"), ("🤖 Ext", "extension_usage"),
            ("🤖 CompetitorMan", "competitor_master"),
            ("💳 Subs", "subscription"), ("⚙️ Admin", "admin_dashboard"),
            ("🚀 Onboarding", "company_onboarding"), 
            ("⚙️ Rate Mgmt", "company_rate_management"),
            ("📖 Tutorial", "tutorial")
        ]
    elif is_company_admin:
        nav_items = [
            ("🏠 Dash", "dashboard"), ("📊 Analytics", "company_analytics"),
            ("📋 Tenders", "tender_management"), ("📊 Rates", "rate_viewer"),
            ("📊 BOQ", "boq_generator"), ("📈 Basic", "quick_bid"),
            ("🎯 Adv Opt", "advanced_bid"), ("🔮 Simulator", "competitive_intel"), ("🎯 AI Advisor", "ai_advisor"), 
            ("🏢 Knowledge", "company_knowledge"), ("📥 Ext", "extension_download"),
            ("🤖 Extension", "extension_usage"),("🤖 CompetitorMan", "competitor_master"), ("📈 Reports", "analysis_history"),
            ("👥 Team", "user_management"), ("💳 Plan", "subscription"),
            ("🚀 Onboarding", "company_onboarding"),             
            ("⚙️ Rate Mgmt", "company_rate_management"),
            ("📖 Tutorial", "tutorial")
        ]
    elif is_manager or is_analyst:
        nav_items = [
            ("🏠 Dash", "dashboard"), ("📋 Tenders", "tender_management"),
            ("📊 Rates", "rate_viewer"), ("📊 BOQ", "boq_generator"),
            ("📈 Basic", "quick_bid")
        ]
        if is_premium:
            nav_items += [
            ("🎯 Adv Opt", "advanced_bid"), 
                 ("🔮 Simulator", "competitive_intel"), ("🎯 AI Advisor", "ai_advisor"), 
                ("🏢 Knowledge", "company_knowledge"), ("🤖 Extension", "extension_usage")
            ]
        nav_items += [
            ("📥 Ext", "extension_download"), ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription"), 
            ("⚙️ Rate Mgmt", "company_rate_management"),
            ("📖 Tutorial", "tutorial")
        ]
    else:  # viewer + default
        nav_items = [
            ("🏠 Dash", "dashboard"), ("📋 Tenders", "tender_management"),
            ("📊 Rates", "rate_viewer"), ("📈 Basic", "quick_bid"),
            ("📥 Ext", "extension_download"), ("🏢 Knowledge", "company_knowledge"),
            ("📈 Reports", "analysis_history"), 
            ("📖 Tutorial", "tutorial")
        ]

    # ==================== RENDER NAV ====================
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)

    # Use columns with wrapping
    num_items = len(nav_items)
    cols_per_row = 8 if num_items > 12 else 6
    
    for i in range(0, num_items, cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (label, page) in enumerate(nav_items[i:i+cols_per_row]):
            with cols[j]:
                is_active = current_page == page
                
                display_label = label
                if page in ["extension_admin", "extension_usage"]:
                    ext_used = st.session_state.get('extension_fills_used', 0)
                    ext_limit = st.session_state.get('extension_fills_limit', 5)
                    rem = "∞" if ext_limit == -1 else max(0, ext_limit - ext_used)
                    display_label = f"{label} ({rem})"
                
                # ✅ FIX: Properly formatted button with correct syntax
                if st.button(
                    display_label,
                    key=f"top_nav_{page}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.page = page
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")