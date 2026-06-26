# _pages/company_analytics_dashboard.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database.unified_db_manager import db
from modules.rbac import is_company_admin, render_role_badge
from modules.rbac import _rbac

# Refresh RBAC role from database
_rbac.refresh_role()

def show():
    """Company Admin Analytics Dashboard - Company-specific metrics"""
    
    # ✅ Get role from multiple sources
    role_from_session = st.session_state.get('user_role', 'unknown')
    user_role = _rbac.get_current_user_role()
    user_id = st.session_state.get('user_id')
    
    # ✅ DEBUG: Print all role sources
    print(f"🔍 Role from session: {role_from_session}")
    print(f"🔍 Role from RBAC: {user_role}")  # ← Fixed: use user_role
    print(f"🔍 User ID: {user_id}")
    
    # ✅ Get user from database to verify
    if user_id:
        user = db.get_user_by_id(user_id)
        if user:
            print(f"🔍 Database role: {user.get('role')}")
            print(f"🔍 Database company_id: {user.get('company_id')}")
    
    # ✅ Auto-correct role if mismatch
    if user_id:
        user = db.get_user_by_id(user_id)
        if user and user.get('role') == 'company_admin':
            if st.session_state.get('user_role') != 'company_admin':
                st.session_state.user_role = 'company_admin'
                user_role = 'company_admin'
                print(f"✅ Corrected role to: {user_role}")
    
    # ✅ Verify company admin access
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("🔒 Access denied. Company admin privileges required.")
        return
    
    company_id = st.session_state.company_id
    company_name = st.session_state.company_name
    
    # If no company_id, show error
    if not company_id:
        st.error("No company associated with this account.")
        return
    
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 {company_name} - Analytics Dashboard</h1>
        <p>Company performance metrics, bid optimization results, and team analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    render_role_badge()
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 1: COMPANY PERFORMANCE KPIs
    # =========================================================================
    st.markdown("## 📈 Company Performance")
    
    perf_metrics = get_company_performance_metrics(company_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Tenders", 
            perf_metrics.get('total_tenders', 0),
            delta=f"{perf_metrics.get('tenders_this_month', 0)} this month"
        )
    with col2:
        st.metric(
            "Win Rate", 
            f"{perf_metrics.get('win_rate', 0):.1f}%",
            delta=f"{perf_metrics.get('win_rate_change', 0):+.1f}% vs last month"
        )
    with col3:
        st.metric(
            "Total Analyses", 
            perf_metrics.get('total_analyses', 0),
            delta=f"{perf_metrics.get('analyses_this_month', 0)} this month"
        )
    with col4:
        st.metric(
            "Active Team Members", 
            perf_metrics.get('active_team_members', 0),
            help="Users who logged in within last 30 days"
        )
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 2: AI VALUE METRICS (Company-specific)
    # =========================================================================
    st.markdown("## 🤖 AI Value Generated")
    st.caption("How much time and money TenderAI has saved your company")
    
    ai_metrics = get_company_ai_metrics(company_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💡 Hours Saved",
            f"{ai_metrics['hours_saved']:,.0f} hrs",
            help="Manual hours saved by using AI auto-fill and analysis"
        )
    with col2:
        st.metric(
            "💰 Cost Savings",
            f"BDT {ai_metrics['cost_savings']:,.0f}",
            help="Estimated cost savings from reduced manual work"
        )
    with col3:
        st.metric(
            "⚡ Time per Tender",
            f"{ai_metrics['avg_time_per_tender']:.0f} min",
            help="Average time to complete a tender analysis"
        )
    with col4:
        st.metric(
            "📊 ROI",
            f"{ai_metrics['roi']:.0f}x",
            help="Return on investment from using TenderAI"
        )
    
    # Time savings trend
    render_company_time_savings(company_id)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 3: TENDER PERFORMANCE
    # =========================================================================
    st.markdown("## 📋 Tender Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_tender_status_chart(company_id)
    
    with col2:
        render_win_rate_trend(company_id)
    
    # Tender performance table
    render_tender_performance_table(company_id)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 4: BID OPTIMIZATION METRICS
    # =========================================================================
    st.markdown("## 🎯 Bid Optimization Metrics")
    
    bid_metrics = get_bid_optimization_metrics(company_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Avg Recommended Bid",
            f"BDT {bid_metrics['avg_recommended_bid']:,.0f}",
            f"{bid_metrics['avg_bid_ratio']:.1f}% of OCE"
        )
    with col2:
        st.metric(
            "Avg Win Probability",
            f"{bid_metrics['avg_win_probability']:.1f}%",
            help="Average predicted win probability"
        )
    with col3:
        st.metric(
            "Expected Savings",
            f"BDT {bid_metrics['total_expected_savings']:,.0f}",
            help="Total savings from optimal bidding"
        )
    with col4:
        st.metric(
            "Bid Accuracy",
            f"{bid_metrics['bid_accuracy']:.1f}%",
            help="How close our bids were to winning bids"
        )
    
    render_bid_optimization_chart(company_id)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 5: TEAM PERFORMANCE
    # =========================================================================
    st.markdown("## 👥 Team Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_team_activity_chart(company_id)
    
    with col2:
        render_top_performers_table(company_id)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 6: EXTENSION USAGE
    # =========================================================================
    st.markdown("## 🤖 Extension Auto-Fill Usage")
    
    ext_metrics = get_extension_usage_metrics(company_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Auto-Fills",
            ext_metrics['total_auto_fills'],
            delta=f"{ext_metrics['auto_fills_this_month']} this month"
        )
    with col2:
        remaining = ext_metrics['limit'] - ext_metrics['used']
        st.metric(
            "Remaining Fills",
            remaining if ext_metrics['limit'] != -1 else "∞",
            help=f"Monthly limit: {ext_metrics['limit'] if ext_metrics['limit'] != -1 else 'Unlimited'}"
        )
    with col3:
        st.metric(
            "Avg Confidence",
            f"{ext_metrics['avg_confidence']:.1f}%",
            help="Average confidence score of auto-fills"
        )
    with col4:
        st.metric(
            "Time Saved",
            f"{ext_metrics['time_saved_auto_fill']:.0f} hrs",
            help="Time saved from auto-filling forms"
        )
    
    # Extension usage trend
    render_extension_usage_trend(company_id)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 7: RECENT ACTIVITY & INSIGHTS
    # =========================================================================
    st.markdown("## 📝 Recent Activity & Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_recent_analyses(company_id)
    
    with col2:
        render_ai_recommendations(company_id)


def get_company_performance_metrics(company_id):
    """Get company performance metrics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Total tenders
    cursor.execute("""
        SELECT COUNT(*) FROM company_tenders 
        WHERE company_id = ? AND is_active = 1
    """, (company_id,))
    total_tenders = cursor.fetchone()[0] or 0
    
    # Tenders this month
    start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM company_tenders 
        WHERE company_id = ? AND is_active = 1 AND created_at >= ?
    """, (company_id, start_of_month))
    tenders_this_month = cursor.fetchone()[0] or 0
    
    # Win rate
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN bid_status = 'won' THEN 1 END) as won,
            COUNT(*) as total
        FROM company_tenders 
        WHERE company_id = ? AND is_active = 1 AND bid_status IN ('won', 'lost')
    """, (company_id,))
    row = cursor.fetchone()
    won = row[0] or 0
    total = row[1] or 0
    win_rate = (won / total * 100) if total > 0 else 0
    
    # Previous month win rate
    last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN bid_status = 'won' THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM company_tenders 
        WHERE company_id = ? AND created_at >= ? AND created_at < ?
    """, (company_id, last_month_start, start_of_month))
    prev_win_rate = cursor.fetchone()[0] or 0
    
    win_rate_change = win_rate - prev_win_rate
    
    # Total analyses
    cursor.execute("""
        SELECT COUNT(*) FROM tender_analyses 
        WHERE company_id = ?
    """, (company_id,))
    total_analyses = cursor.fetchone()[0] or 0
    
    # Analyses this month
    cursor.execute("""
        SELECT COUNT(*) FROM tender_analyses 
        WHERE company_id = ? AND analysis_date >= ?
    """, (company_id, start_of_month))
    analyses_this_month = cursor.fetchone()[0] or 0
    
    # Active team members (logged in last 30 days)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(DISTINCT u.id)
        FROM users u
        WHERE u.company_id = ? AND u.is_active = 1
        AND (u.last_login >= ? OR u.id IN (
            SELECT DISTINCT user_id FROM tender_analyses WHERE analysis_date >= ?
        ))
    """, (company_id, thirty_days_ago, thirty_days_ago))
    active_team = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_tenders': total_tenders,
        'tenders_this_month': tenders_this_month,
        'win_rate': win_rate,
        'win_rate_change': win_rate_change,
        'total_analyses': total_analyses,
        'analyses_this_month': analyses_this_month,
        'active_team_members': active_team
    }


def get_company_ai_metrics(company_id):
    """Calculate company-specific AI value metrics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get total analyses
    cursor.execute("""
        SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?
    """, (company_id,))
    total_analyses = cursor.fetchone()[0] or 0
    
    # Get total auto-fills
    cursor.execute("""
        SELECT COUNT(*) FROM extension_auto_fill_log WHERE company_id = ?
    """, (company_id,))
    total_auto_fills = cursor.fetchone()[0] or 0
    
    # Average time per tender (from analysis timestamps)
    cursor.execute("""
        SELECT 
            AVG(JULIANDAY(analysis_date) - JULIANDAY(created_at)) * 24 * 60 as minutes
        FROM tender_analyses ta
        JOIN company_tenders ct ON ta.tender_id = ct.tender_id
        WHERE ta.company_id = ? AND ct.created_at IS NOT NULL
    """, (company_id,))
    result = cursor.fetchone()
    avg_time = result[0] if result and result[0] else 45  # Default 45 minutes
    
    # Hours saved (manual 45 min - actual time)
    manual_time = 45  # minutes per tender
    time_saved_per_tender = max(0, manual_time - avg_time)
    hours_saved = (time_saved_per_tender * total_analyses) / 60
    
    # Add auto-fill time savings (2 min per fill)
    auto_fill_hours = (total_auto_fills * 2) / 60
    hours_saved += auto_fill_hours
    
    # Cost savings (BDT 500 per hour)
    hourly_rate = 500
    cost_savings = hours_saved * hourly_rate
    
    # ROI (assuming monthly subscription cost)
    cursor.execute("""
        SELECT 
            CASE 
                WHEN plan = 'basic' THEN 4999
                WHEN plan = 'professional' THEN 14999
                WHEN plan = 'enterprise' THEN 49999
                ELSE 0
            END as monthly_cost
        FROM subscriptions 
        WHERE company_id = ? AND status = 'active'
        LIMIT 1
    """, (company_id,))
    monthly_cost = cursor.fetchone()[0] or 4999
    
    annual_cost = monthly_cost * 12
    roi = cost_savings / annual_cost if annual_cost > 0 else 0
    
    conn.close()
    
    return {
        'hours_saved': hours_saved,
        'cost_savings': cost_savings,
        'avg_time_per_tender': avg_time,
        'roi': roi
    }


def get_bid_optimization_metrics(company_id):
    """Get bid optimization metrics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Average recommended bid
    cursor.execute("""
        SELECT 
            AVG(recommended_bid) as avg_bid,
            AVG(recommended_bid / official_estimate) as avg_ratio
        FROM tender_analyses 
        WHERE company_id = ? AND official_estimate > 0
    """, (company_id,))
    row = cursor.fetchone()
    avg_bid = row[0] or 0
    avg_ratio = (row[1] or 0) * 100
    
    # Average win probability
    cursor.execute("""
        SELECT AVG(success_probability) FROM tender_analyses 
        WHERE company_id = ? AND success_probability IS NOT NULL
    """, (company_id,))
    avg_win_prob = (cursor.fetchone()[0] or 0) * 100
    
    # Total expected savings (difference between OCE and recommended bid)
    cursor.execute("""
        SELECT SUM(official_estimate - recommended_bid) 
        FROM tender_analyses 
        WHERE company_id = ? AND official_estimate > recommended_bid
    """, (company_id,))
    total_savings = cursor.fetchone()[0] or 0
    
    # Bid accuracy (for submitted bids that have results)
    cursor.execute("""
        SELECT 
            AVG(100 - ABS(our_bid_amount - winning_bid_amount) / winning_bid_amount * 100) as accuracy
        FROM company_tenders 
        WHERE company_id = ? AND bid_status = 'won' AND winning_bid_amount > 0 AND our_bid_amount > 0
    """, (company_id,))
    accuracy = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'avg_recommended_bid': avg_bid,
        'avg_bid_ratio': avg_ratio,
        'avg_win_probability': avg_win_prob,
        'total_expected_savings': total_savings,
        'bid_accuracy': accuracy
    }


def get_extension_usage_metrics(company_id):
    """Get extension usage metrics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Total auto-fills
    cursor.execute("""
        SELECT COUNT(*) FROM extension_auto_fill_log WHERE company_id = ?
    """, (company_id,))
    total = cursor.fetchone()[0] or 0
    
    # Auto-fills this month
    start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM extension_auto_fill_log 
        WHERE company_id = ? AND filled_at >= ?
    """, (company_id, start_of_month))
    this_month = cursor.fetchone()[0] or 0
    
    # Average confidence
    cursor.execute("""
        SELECT AVG(confidence_score) FROM extension_auto_fill_log 
        WHERE company_id = ? AND confidence_score > 0
    """, (company_id,))
    avg_conf = (cursor.fetchone()[0] or 0) * 100
    
    # Get plan limit
    usage_metrics = db.get_extension_usage_metrics(company_id)
    limit = usage_metrics.get('extension_auto_fills', 5)

    
    # Time saved (2 min per fill)
    time_saved = (total * 2) / 60
    
    conn.close()
    
    return {
        'total_auto_fills': total,
        'auto_fills_this_month': this_month,
        'avg_confidence': avg_conf,
        'limit': limit,
        'used': this_month,
        'time_saved_auto_fill': time_saved
    }


def render_tender_status_chart(company_id):
    """Render tender status pie chart"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            bid_status as status,
            COUNT(*) as count
        FROM company_tenders
        WHERE company_id = ? AND is_active = 1
        GROUP BY bid_status
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        status_colors = {
            'won': '#10b981',
            'lost': '#ef4444',
            'submitted': '#f59e0b',
            'draft': '#6b7280'
        }
        colors = [status_colors.get(s, '#6b7280') for s in df['status']]
        
        fig = go.Figure(data=[go.Pie(
            labels=df['status'].str.upper(),
            values=df['count'],
            marker_colors=colors,
            hole=0.4,
            textinfo='label+percent',
            textposition='auto'
        )])
        
        fig.update_layout(
            title="Tender Status Distribution",
            height=350,
            annotations=[dict(text=f"Total: {df['count'].sum()}", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tender data available")


def render_win_rate_trend(company_id):
    """Render win rate trend line chart"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(CASE WHEN bid_status = 'won' THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM company_tenders
        WHERE company_id = ? AND is_active = 1 AND bid_status IN ('won', 'lost')
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month
        LIMIT 12
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['month'],
            y=df['win_rate'],
            mode='lines+markers',
            name='Win Rate',
            line=dict(color='#10b981', width=3),
            marker=dict(size=8, color='#059669'),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        ))
        
        fig.add_hline(y=50, line_dash="dash", line_color="red", 
                      annotation_text="50% Baseline")
        
        fig.update_layout(
            title="Win Rate Trend",
            xaxis_title="Month",
            yaxis_title="Win Rate (%)",
            yaxis_range=[0, 100],
            height=350,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No win rate data available")

def render_bid_optimization_chart(company_id):
    """Render bid optimization comparison chart"""
    conn = db.get_connection()
    
    # FIX: Added table aliases (ta. and ct.) to column names
    df = pd.read_sql_query("""
        SELECT 
            ta.official_estimate,
            ta.recommended_bid,
            ct.our_bid_amount as actual_bid
        FROM tender_analyses ta
        LEFT JOIN company_tenders ct ON ta.tender_id = ct.tender_id
        WHERE ta.company_id = ? AND ta.official_estimate > 0
        LIMIT 20
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Official Estimate',
            x=df.index,
            y=df['official_estimate'],
            marker_color='#6b7280'
        ))
        
        fig.add_trace(go.Bar(
            name='Recommended Bid',
            x=df.index,
            y=df['recommended_bid'],
            marker_color='#667eea'
        ))
        
        fig.add_trace(go.Bar(
            name='Actual Bid',
            x=df.index,
            y=df['actual_bid'],
            marker_color='#10b981'
        ))
        
        fig.update_layout(
            title="Bid Comparison (Last 20 Analyses)",
            xaxis_title="Analysis #",
            yaxis_title="Amount (BDT)",
            barmode='group',
            height=400,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No bid optimization data available")


def render_team_activity_chart(company_id):
    """Render team activity bar chart"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            u.full_name,
            COUNT(DISTINCT ta.id) as analyses,
            COUNT(DISTINCT ct.id) as tenders
        FROM users u
        LEFT JOIN tender_analyses ta ON u.id = ta.user_id
        LEFT JOIN company_tenders ct ON u.id = ct.created_by
        WHERE u.company_id = ? AND u.is_active = 1
        GROUP BY u.id
        ORDER BY analyses DESC
        LIMIT 10
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Analyses',
            x=df['full_name'],
            y=df['analyses'],
            marker_color='#667eea',
            text=df['analyses'],
            textposition='auto'
        ))
        
        fig.add_trace(go.Bar(
            name='Tenders',
            x=df['full_name'],
            y=df['tenders'],
            marker_color='#10b981',
            text=df['tenders'],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Team Activity",
            xaxis_title="Team Member",
            yaxis_title="Count",
            barmode='group',
            height=350,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No team activity data available")


def render_top_performers_table(company_id):
    """Render top performers table"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            u.full_name,
            u.role,
            COUNT(DISTINCT ta.id) as analyses,
            ROUND(AVG(ta.success_probability * 100), 1) as avg_confidence,
            MAX(ta.analysis_date) as last_active
        FROM users u
        LEFT JOIN tender_analyses ta ON u.id = ta.user_id
        WHERE u.company_id = ? AND u.is_active = 1
        GROUP BY u.id
        HAVING analyses > 0
        ORDER BY analyses DESC
        LIMIT 10
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        df['last_active'] = pd.to_datetime(df['last_active']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "full_name": "Name",
                "role": "Role",
                "analyses": st.column_config.NumberColumn("Analyses"),
                "avg_confidence": st.column_config.NumberColumn("Avg Confidence", format="%.1f%%"),
                "last_active": "Last Active"
            }
        )
    else:
        st.info("No performer data available")


def render_company_time_savings(company_id):
    """Render time savings trend chart"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            strftime('%Y-%m', analysis_date) as month,
            COUNT(*) * 40 / 60 as hours_saved
        FROM tender_analyses
        WHERE company_id = ?
        GROUP BY strftime('%Y-%m', analysis_date)
        ORDER BY month
        LIMIT 12
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['month'],
            y=df['hours_saved'],
            mode='lines+markers',
            name='Hours Saved',
            line=dict(color='#ef4444', width=3),
            marker=dict(size=8, color='#dc2626'),
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.1)'
        ))
        
        fig.update_layout(
            title="AI Time Savings Trend",
            xaxis_title="Month",
            yaxis_title="Hours Saved",
            height=350,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No time savings data available")


def render_extension_usage_trend(company_id):
    """Render extension usage trend chart"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            strftime('%Y-%m-%d', filled_at) as date,
            COUNT(*) as fills,
            AVG(confidence_score) * 100 as avg_confidence
        FROM extension_auto_fill_log
        WHERE company_id = ? AND filled_at >= date('now', '-30 days')
        GROUP BY strftime('%Y-%m-%d', filled_at)
        ORDER BY date
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Auto-Fills',
            x=df['date'],
            y=df['fills'],
            marker_color='#667eea',
            yaxis='y'
        ))
        
        fig.add_trace(go.Scatter(
            name='Confidence Score',
            x=df['date'],
            y=df['avg_confidence'],
            mode='lines+markers',
            marker_color='#f59e0b',
            line=dict(color='#f59e0b', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="Extension Usage (Last 30 Days)",
            xaxis_title="Date",
            yaxis_title="Auto-Fills",
            yaxis2=dict(
                title="Confidence Score (%)",
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            height=350,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No extension usage data available")


def render_tender_performance_table(company_id):
    """Render tender performance table"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            tender_id,
            tender_title,
            official_estimate,
            our_bid_amount as our_bid,
            winning_bid_amount as winning_bid,
            bid_status as status,
            our_rank,
            total_bidders,
            award_date
        FROM company_tenders
        WHERE company_id = ? AND is_active = 1
        ORDER BY created_at DESC
        LIMIT 20
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        # Calculate bid difference
        df['bid_diff'] = df['our_bid'] - df['winning_bid']
        df['bid_diff_pct'] = (df['bid_diff'] / df['winning_bid'] * 100).fillna(0)
        
        # Format for display
        df['official_estimate'] = df['official_estimate'].apply(lambda x: f"BDT {x:,.0f}" if x else "N/A")
        df['our_bid'] = df['our_bid'].apply(lambda x: f"BDT {x:,.0f}" if x else "Not set")
        df['winning_bid'] = df['winning_bid'].apply(lambda x: f"BDT {x:,.0f}" if x else "N/A")
        df['bid_diff'] = df['bid_diff'].apply(lambda x: f"BDT {abs(x):,.0f} {'higher' if x > 0 else 'lower'}" if x else "N/A")
        df['status'] = df['status'].str.upper()
        
        st.dataframe(
            df[['tender_id', 'tender_title', 'official_estimate', 'our_bid', 
                'winning_bid', 'bid_diff', 'status', 'our_rank', 'total_bidders']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "tender_id": "Tender ID",
                "tender_title": "Title",
                "official_estimate": "Estimate",
                "our_bid": "Our Bid",
                "winning_bid": "Winning Bid",
                "bid_diff": "Difference",
                "status": "Status",
                "our_rank": "Rank",
                "total_bidders": "Total Bidders"
            }
        )
    else:
        st.info("No tender data available")


def render_recent_analyses(company_id):
    """Render recent analyses list"""
    conn = db.get_connection()
    
    df = pd.read_sql_query("""
        SELECT 
            tender_title,
            recommended_bid,
            success_probability * 100 as win_probability,
            analysis_date
        FROM tender_analyses
        WHERE company_id = ?
        ORDER BY analysis_date DESC
        LIMIT 10
    """, conn, params=(company_id,))
    conn.close()
    
    if not df.empty:
        st.markdown("#### 📋 Recent Analyses")
        
        for _, row in df.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="padding: 10px; border-bottom: 1px solid #eee;">
                    <strong>{row['tender_title'][:50]}</strong><br>
                    <small>
                        💰 Recommended: BDT {row['recommended_bid']:,.0f} | 
                        🎯 Win Prob: {row['win_probability']:.0f}% | 
                        📅 {pd.to_datetime(row['analysis_date']).strftime('%Y-%m-%d')}
                    </small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No recent analyses")


def render_ai_recommendations(company_id):
    """Render AI recommendations based on company data"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get low win rate tenders
    cursor.execute("""
        SELECT COUNT(*) FROM company_tenders 
        WHERE company_id = ? AND bid_status = 'lost' AND award_date >= date('now', '-90 days')
    """, (company_id,))
    recent_losses = cursor.fetchone()[0] or 0
    
    # Get underutilized features
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM saved_scenarios WHERE company_id = ?) as scenarios,
            (SELECT COUNT(*) FROM competitor_master WHERE company_id = ?) as competitors
    """, (company_id, company_id))
    row = cursor.fetchone()
    scenarios_used = row[0] or 0
    competitors_added = row[1] or 0
    
    conn.close()
    
    st.markdown("#### 💡 AI Recommendations")
    
    recommendations = []
    
    if recent_losses > 3:
        recommendations.append(f"📉 You've lost {recent_losses} tenders in the last 3 months. Consider using the Competitive Bid Simulator to test different bidding strategies.")
    
    if scenarios_used == 0:
        recommendations.append("🎲 Generate scenarios using the Competitive Bid Simulator to discover optimal bidding ranges.")
    
    if competitors_added < 3:
        recommendations.append("👥 Add competitor data to improve win probability predictions by up to 25%.")
    
    if not recommendations:
        recommendations.append("✅ Great job! Your company is using TenderAI effectively. Keep up the good work!")
    
    for rec in recommendations:
        st.info(rec)