# _pages/extension_usage.py - REFACTORED VERSION
# Using only CRUD methods, no raw SQL

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import get_db_manager


def show():
    """Extension Usage Dashboard for Company Admins"""
    
    if st.session_state.user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("🔒 Access denied. Company admin privileges required.")
        return
    
    company_id = st.session_state.company_id
    
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Extension Usage Dashboard</h1>
        <p>Monitor and manage Chrome extension auto-fill usage for your company</p>
    </div>
    """, unsafe_allow_html=True)
    
    db = get_db_manager()
    
    # Get usage stats using CRUD methods
    this_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    
    # Get subscription plan
    sub = db.get_company_subscription(company_id)
    plan = sub.get('plan', 'free')
    plan_limits = {'free': 5, 'basic': 30, 'professional': 100, 'enterprise': -1}
    limit = plan_limits.get(plan, 5)
    
    # Get usage count using query method (no raw SQL)
    # Check if table exists by trying to query it
    try:
        usage_result = db.query_one("""
            SELECT COUNT(*) as count 
            FROM extension_auto_fill_log 
            WHERE company_id = ? AND filled_at >= ?
        """, (company_id, this_month))
        used_this_month = usage_result.get('count', 0) if usage_result else 0
    except Exception:
        # Table might not exist yet
        used_this_month = 0
    
    # Display usage
    st.markdown("### 📊 Monthly Usage")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Plan", plan.capitalize())
    
    with col2:
        if limit == -1:
            st.metric("Auto-Fills Used", f"{used_this_month} (Unlimited)")
        else:
            st.metric("Auto-Fills Used", f"{used_this_month} / {limit}")
    
    with col3:
        if limit != -1:
            remaining = max(0, limit - used_this_month)
            pct_used = (used_this_month / limit) * 100 if limit > 0 else 0
            st.metric("Remaining", remaining)
            st.progress(min(1.0, pct_used / 100))
    
    # Usage history - Monthly trend
    st.markdown("### 📈 Usage History")
    
    # Get monthly trend using query
    try:
        monthly_trend_data = db.query("""
            SELECT 
                strftime('%Y-%m', filled_at) as month,
                COUNT(*) as fills
            FROM extension_auto_fill_log
            WHERE company_id = ?
            GROUP BY strftime('%Y-%m', filled_at)
            ORDER BY month DESC
            LIMIT 12
        """, (company_id,))
        
        if monthly_trend_data:
            monthly_trend = pd.DataFrame(monthly_trend_data)
            if not monthly_trend.empty:
                st.bar_chart(monthly_trend.set_index('month'))
    except Exception:
        st.info("No usage data available yet.")
    
    # Recent activity
    st.markdown("### 📋 Recent Activity")
    
    try:
        recent_data = db.query("""
            SELECT 
                filled_at,
                user_id,
                field_label,
                confidence_score,
                page_url
            FROM extension_auto_fill_log
            WHERE company_id = ?
            ORDER BY filled_at DESC
            LIMIT 50
        """, (company_id,))
        
        if recent_data:
            recent = pd.DataFrame(recent_data)
            recent['filled_at'] = pd.to_datetime(recent['filled_at']).dt.strftime('%Y-%m-%d %H:%M')
            recent['confidence_score'] = recent['confidence_score'].apply(
                lambda x: f"{x*100:.0f}%" if x and x is not None else "N/A"
            )
            
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No extension activity yet.")
    except Exception:
        st.info("No extension activity yet. Install the Chrome extension to start auto-filling forms.")
    
    # Installation instructions
    with st.expander("📥 Chrome Extension Installation Guide"):
        st.markdown("""
        ### Install TenderAI Chrome Extension
        
        1. **Download the extension** from the admin panel
        2. Open Chrome and go to `chrome://extensions/`
        3. Enable **Developer mode** (toggle in top right)
        4. Click **Load unpacked**
        5. Select the extension folder
        6. Pin the extension for easy access
        
        ### How to Use
        
        1. Log in to TenderAI in your browser
        2. Navigate to any tender form (e-GP, e-Procurement, etc.)
        3. The extension will automatically detect form fields
        4. Fields are auto-filled based on your company data
        5. Review and adjust as needed
        """)
    
    # Upgrade prompt if needed
    if limit != -1 and used_this_month >= limit:
        st.warning(f"⚠️ You've reached your monthly limit of {limit} auto-fills.")
        if st.button("💳 Upgrade Plan for More Auto-Fills"):
            st.session_state.page = "subscription"
            st.rerun()