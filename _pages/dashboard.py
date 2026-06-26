# _pages/dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime

from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription import get_plan, get_current_user_plan, get_current_user_plan_name, is_premium_plan
from modules.subscription import render_simple_subscription_status
from modules.access_control import access_control

db = UnifiedDatabaseManager()


def show():
    """User dashboard page with role-based views"""
    
    # Get user info
    user_role = st.session_state.get('user_role', 'viewer')
    user_id = st.session_state.get('user_id')
    company_id = st.session_state.get('company_id')
    full_name = st.session_state.get('full_name', 'User')
    company_name = st.session_state.get('company_name', 'N/A')
    
    # Get subscription info
    current_plan = get_current_user_plan_name()
    plan_config = get_plan(current_plan)
    is_premium = is_premium_plan(current_plan)
    
    # =========================================================================
    # HEADER
    # =========================================================================
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome, {full_name}! 👋</h1>
        <p>{company_name} | <span style="color: {plan_config.get('color', '#6c757d')};">{plan_config.get('name', current_plan.upper())} Plan</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Subscription status badge
    render_simple_subscription_status(db.get_company_subscription(company_id) if company_id else {})
    
    # =========================================================================
    # KEY METRICS
    # =========================================================================
    stats = db.get_company_stats(company_id) if company_id else {}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Total Analyses",
            stats.get('total_analyses', 0),
            help="Total number of tender analyses performed"
        )
    
    with col2:
        win_rate = stats.get('win_rate', 0)
        st.metric(
            "🏆 Win Rate",
            f"{win_rate:.0f}%",
            help="Percentage of won bids based on tracked data"
        )
    
    with col3:
        st.metric(
            "👥 Team Members",
            stats.get('total_users', 1),
            help="Active users in your company"
        )
    
    with col4:
        # Get remaining analyses from subscription
        sub = db.get_user_subscription(user_id) if user_id else {}
        analyses_limit = sub.get('max_projects', 5)
        analyses_used = sub.get('analyses_used', 0)
        
        if analyses_limit == -1:
            remaining = "♾️"
        else:
            remaining = max(0, analyses_limit - analyses_used)
        
        st.metric(
            "📈 Analyses Left",
            remaining,
            help=f"{analyses_used} used of {analyses_limit if analyses_limit != -1 else 'unlimited'}"
        )
    
    # =========================================================================
    # EXTENSION STATUS
    # =========================================================================
    _render_extension_status(company_id, is_premium)
    
    # =========================================================================
    # QUICK ACTIONS
    # =========================================================================
    _render_quick_actions(user_role)
    
    # =========================================================================
    # RECENT ANALYSES
    # =========================================================================
    _render_recent_analyses(user_id, company_id, user_role)
    
    # =========================================================================
    # SUBSCRIPTION ALERTS
    # =========================================================================
    _render_subscription_alerts(user_id)


def _render_extension_status(company_id: int, is_premium: bool):
    """Render extension status section"""
    
    st.markdown("### 🤖 Extension Status")
    
    try:
        usage = db.get_extension_fill_usage(company_id) if company_id else {}
        is_unlimited = usage.get('is_unlimited', False)
        remaining_fills = usage.get('remaining', 0)
        limit = usage.get('limit', 5)
        used = usage.get('used', 0)
    except Exception as e:
        print(f"Error getting extension usage: {e}")
        is_unlimited = False
        remaining_fills = 0
        limit = 5
        used = 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_unlimited:
            st.info("🎯 **Extension Auto-Fill**: Unlimited")
        else:
            remaining = remaining_fills if remaining_fills > 0 else 0
            if remaining > 0:
                st.success(f"🎯 **Extension Auto-Fill**: {remaining} fills remaining")
            else:
                st.warning(f"🎯 **Extension Auto-Fill**: 0 fills remaining - Upgrade to continue")
            
            # Progress bar
            if limit > 0:
                progress = min(used / limit, 1.0)
                st.progress(progress)
                st.caption(f"{used} of {limit} used")
    
    with col2:
        if st.button("📥 Get Chrome Extension", use_container_width=True):
            st.info("Contact admin for extension download link")
    
    with col3:
        if not is_unlimited and remaining_fills == 0:
            if st.button("💳 Upgrade for More", use_container_width=True):
                st.session_state.page = "subscription"
                st.rerun()


def _render_quick_actions(user_role: str):
    """Render quick action buttons"""
    
    st.markdown("### 🚀 Quick Actions")
    
    is_admin = user_role in ['admin', 'system_admin']
    is_company_admin = user_role in ['admin', 'system_admin', 'company_admin']
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Tenders", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    
    with col2:
        if st.button("📊 New Analysis", use_container_width=True):
            st.session_state.page = "boq_bid_optimizer"
            st.rerun()
    
    with col3:
        if st.button("📜 View History", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    
    with col4:
        if is_company_admin:
            if st.button("👥 Team Management", use_container_width=True):
                st.session_state.page = "user_management"
                st.rerun()
        else:
            st.button("🔒 Team Management", disabled=True, use_container_width=True,
                     help="Only company admins can manage team")
    
    with col5:
        if st.button("💳 Upgrade Plan", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()


def _render_recent_analyses(user_id: int, company_id: int, user_role: str):
    """Render recent analyses section"""
    
    try:
        analyses_df = db.get_user_analyses(
            user_id=user_id,
            company_id=company_id,
            role=user_role,
            limit=10
        )
    except Exception as e:
        print(f"Error getting analyses: {e}")
        analyses_df = pd.DataFrame()
    
    st.markdown("### 📋 Recent Analyses")
    
    if analyses_df is not None and len(analyses_df) > 0:
        # Select columns to display
        display_cols = ['tender_id', 'tender_title', 'procuring_entity', 'recommended_bid', 'bid_status']
        available_cols = [col for col in display_cols if col in analyses_df.columns]
        
        if available_cols:
            # Format bid amounts
            if 'recommended_bid' in available_cols:
                analyses_df['recommended_bid'] = analyses_df['recommended_bid'].apply(
                    lambda x: f"BDT {x:,.2f}" if x and x > 0 else 'N/A'
                )
            
            st.dataframe(
                analyses_df[available_cols].head(10),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No analysis data available")
    else:
        st.info("No analyses yet. Create your first analysis!")


def _render_subscription_alerts(user_id: int):
    """Render subscription alerts"""
    
    try:
        sub = db.get_user_subscription(user_id) if user_id else {}
        status = sub.get('status', '')
        end_date = sub.get('end_date')
        
        if status == 'trial' and end_date:
            try:
                if isinstance(end_date, str):
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_date_obj = end_date
                days_left = (end_date_obj - datetime.now().date()).days
                
                if 0 < days_left <= 7:
                    st.warning(f"⚠️ Your trial ends in {days_left} days. Upgrade to continue using premium features!")
                elif days_left <= 0:
                    st.error("⚠️ Your trial has ended. Please upgrade to continue using premium features!")
            except Exception as e:
                print(f"Error checking subscription trial: {e}")
        
        # Show usage warnings
        analyses_limit = sub.get('max_projects', 5)
        analyses_used = sub.get('analyses_used', 0)
        
        if analyses_limit != -1 and analyses_used >= analyses_limit:
            st.error(f"❌ You have used all {analyses_limit} analyses. Please upgrade to continue.")
        elif analyses_limit != -1 and analyses_used >= analyses_limit * 0.8:
            remaining = analyses_limit - analyses_used
            st.warning(f"⚠️ Only {remaining} analyses remaining. Consider upgrading for more capacity.")
            
    except Exception as e:
        print(f"Error checking subscription: {e}")


# =============================================================================
# ROLE-BASED DASHBOARD REDIRECTS
# =============================================================================

def show_role_dashboard():
    """Show the appropriate dashboard based on user role"""
    
    user_role = st.session_state.get('user_role', 'viewer')
    
    if user_role in ['admin', 'system_admin']:
        # Admins see the admin dashboard
        from _pages.admin_dashboard import show as admin_dashboard
        admin_dashboard()
    elif user_role == 'company_admin':
        # Company admins see the company analytics dashboard
        from _pages.company_analytics_dashboard import show as company_analytics
        company_analytics()
    else:
        # Regular users see the user dashboard
        show()