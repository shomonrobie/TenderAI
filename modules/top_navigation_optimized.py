import streamlit as st

GROUPS = {
    "Tenders & Analysis": [
        ("📋 Tenders", "frontend/tender_management"),
        ("📊 Analysis", "frontend/admin_analytics"),
        ("📈 History", "frontend/analysis_history"),
    ],
    "BOQ & Bid": [
        ("📊 BOQ", "frontend/boq_generator"),
        ("🎯 Optimizer", "frontend/advanced_bid_optimizer"),
        ("💡 Quick Bid", "frontend/quick_bid"),
        ("🤖 AI Advisor", "frontend/ai_advisor"),
    ],
    "Rates & Data": [
        ("💰 Rate Mgmt", "frontend/rate_management"),
        ("📥 Import", "frontend/import_wizard"),
        ("🏢 Knowledge", "frontend/company_knowledge"),
    ],
    "Admin & System": [
        ("⚙️ Admin", "frontend/admin_dashboard"),
        ("👥 Users", "frontend/user_management"),
        ("💳 Sub", "frontend/subscription"),
        ("🤖 Ext", "frontend/extension_admin"),
    ],
    "Company & Team": [
        ("🏠 Company Dash", "frontend/company_dashboard"),
        ("📊 Analytics", "frontend/company_analytics"),
        ("👤 Profile", "frontend/company_profile_management"),
        ("🚀 Onboarding", "frontend/company_onboarding"),
    ],
}

def render_top_navigation():
    role = st.session_state.get("user_role", "viewer")
    for group_name, items in GROUPS.items():
        with st.expander(group_name, expanded=(group_name in ["Tenders & Analysis", "BOQ & Bid"])):
            cols = st.columns(len(items))
            for col, (label, page) in zip(cols, items):
                col.button(label, key=f"nav_{page}", use_container_width=True)
