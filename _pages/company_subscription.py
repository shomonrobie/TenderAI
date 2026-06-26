# _pages/company_subscription.py

import streamlit as st
from modules.subscription_manager import SubscriptionManager
from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription import get_plan, get_plans, is_premium_plan
from modules.subscription_ui import render_subscription_card
from typing import List, Union, Dict, Callable, Optional
db = UnifiedDatabaseManager()


def show():
    """Show company subscription management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>💳 Company Subscription</h1>
        <p>Manage your plan, billing, and team access</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    # Get subscription using unified method
    current_sub = db.get_company_subscription(company_id)
    
    # Get plan details from database
    plan_name = current_sub.get('subscription_tier', 'free')
    plan_config = get_plan(plan_name)
    
    # =========================================================================
    # SUBSCRIPTION CARD
    # =========================================================================
    render_subscription_card(
        subscription=current_sub,
        company_id=company_id,
        show_update=False,  # Updates handled by admin
        show_cancel=False,
        title="📋 Current Subscription"
    )
    
    # =========================================================================
    # PLAN FEATURES
    # =========================================================================
    st.markdown("### 📋 Plan Features")
    
    features = [
        ("📊 BOQ Generations", _format_limit(current_sub.get('max_boq_generations', 5))),
        ("🎯 Bid Optimizations", _format_limit(current_sub.get('max_bid_optimizations', 5))),
        ("📈 Tender Analyses", _format_limit(current_sub.get('max_projects', 5))),
        ("👥 Team Members", _format_limit(current_sub.get('max_users', 1))),
        ("🤖 Extension Auto-Fills", _format_limit(current_sub.get('extension_auto_fills', 5))),
        ("📤 Export Data", "✅" if current_sub.get('can_export_data', False) else "❌"),
        ("✏️ Edit Rates", "✅" if current_sub.get('can_edit_rates', False) else "❌"),
        ("🗑️ Delete Rates", "✅" if current_sub.get('can_delete_rates', False) else "❌"),
        ("🔧 Create Versions", "✅" if current_sub.get('can_create_versions', False) else "❌"),
        ("👥 Manage Team", "✅" if current_sub.get('can_manage_team', False) else "❌"),
    ]
    
    col1, col2 = st.columns(2)
    for i, (feature, value) in enumerate(features):
        with col1 if i % 2 == 0 else col2:
            st.markdown(f"**{feature}:** {value}")
    
    # =========================================================================
    # USAGE PROGRESS
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📊 Current Usage")
    
    _render_usage_progress(current_sub, company_id)
    
    # =========================================================================
    # UPGRADE OPTIONS
    # =========================================================================
    can_manage = user_role in ['admin', 'system_admin', 'company_admin']
    
    if can_manage and plan_name != 'enterprise':
        st.markdown("---")
        st.markdown("### 🚀 Upgrade Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📈 Upgrade to Professional", use_container_width=True):
                st.session_state.page = "subscription"
                st.rerun()
        
        with col2:
            if st.button("👑 Enterprise Plan", use_container_width=True):
                st.info("📧 Contact us at sales@tenderai.com for enterprise pricing")
        
        with col3:
            if st.button("📞 Contact Sales", use_container_width=True):
                st.info("📧 sales@tenderai.com | 📞 +880 1234 567890")
    
    # =========================================================================
    # WARNINGS
    # =========================================================================
    _render_usage_warnings(current_sub)


def _format_limit(value: int) -> str:
    """Format limit value for display"""
    if value == -1:
        return "Unlimited"
    return str(value)


def _render_usage_progress(sub: Dict, company_id: int):
    """Render usage progress bars"""
    
    # BOQ Usage
    max_boq = sub.get('max_boq_generations', 5)
    boq_used = sub.get('boq_used', 0)
    
    if max_boq != -1:
        boq_percent = (boq_used / max_boq) * 100 if max_boq > 0 else 0
        st.progress(min(boq_percent / 100, 1.0))
        st.caption(f"BOQ Usage: {boq_used} / {max_boq} ({boq_percent:.0f}%)")
    else:
        st.progress(0)
        st.caption("BOQ Usage: Unlimited")
    
    # Analysis Usage
    max_analyses = sub.get('max_projects', 5)
    analyses_used = sub.get('analyses_used', 0)
    
    if max_analyses != -1:
        analysis_percent = (analyses_used / max_analyses) * 100 if max_analyses > 0 else 0
        st.progress(min(analysis_percent / 100, 1.0))
        st.caption(f"Analyses Usage: {analyses_used} / {max_analyses} ({analysis_percent:.0f}%)")
    else:
        st.progress(0)
        st.caption("Analyses Usage: Unlimited")
    
    # Team usage
    max_users = sub.get('max_users', 1)
    if max_users != -1:
        try:
            sub_manager = SubscriptionManager(db)
            current_users = sub_manager._get_company_user_count(company_id)
            user_percent = (current_users / max_users) * 100 if max_users > 0 else 0
            st.progress(min(user_percent / 100, 1.0))
            st.caption(f"Team Members: {current_users} / {max_users} ({user_percent:.0f}%)")
        except:
            st.caption(f"Team Members: Up to {max_users} users")
    else:
        st.progress(0)
        st.caption("Team Members: Unlimited")


def _render_usage_warnings(sub: Dict):
    """Render warnings for near-limit usage"""
    
    max_boq = sub.get('max_boq_generations', 5)
    boq_used = sub.get('boq_used', 0)
    
    max_analyses = sub.get('max_projects', 5)
    analyses_used = sub.get('analyses_used', 0)
    
    warnings_shown = False
    
    if max_boq != -1 and boq_used >= max_boq * 0.8:
        st.warning(f"⚠️ You have used {boq_used}/{max_boq} BOQ generations. Consider upgrading for more capacity.")
        warnings_shown = True
    
    if max_analyses != -1 and analyses_used >= max_analyses * 0.8:
        st.warning(f"⚠️ You have used {analyses_used}/{max_analyses} analyses. Consider upgrading for more capacity.")
        warnings_shown = True
    
    if max_boq != -1 and boq_used >= max_boq:
        st.error(f"❌ BOQ limit reached ({max_boq}). Please upgrade to continue.")
        warnings_shown = True
    
    if max_analyses != -1 and analyses_used >= max_analyses:
        st.error(f"❌ Analyses limit reached ({max_analyses}). Please upgrade to continue.")
        warnings_shown = True
    
    if not warnings_shown and boq_used > 0 and max_boq != -1:
        remaining_boq = max_boq - boq_used
        remaining_analyses = max_analyses - analyses_used if max_analyses != -1 else "unlimited"
        
        if remaining_boq > 0:
            st.success(f"✅ You have {remaining_boq} BOQ generations and {remaining_analyses} analyses remaining.")