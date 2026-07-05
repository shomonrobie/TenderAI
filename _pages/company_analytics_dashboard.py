# _pages/company_analytics_dashboard.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database.unified_db_manager import get_db_manager
from modules.rbac import render_role_badge
from modules.rbac import _rbac

# Cache TTL in seconds
CACHE_TTL = 300

_db = None

def get_db():
    """Get database manager instance (singleton)"""
    global _db
    if _db is None:
        _db = get_db_manager()
    return _db

def show():
    """Company Admin Analytics Dashboard"""
    
    # Get role and user info
    user_role = _rbac.get_current_user_role()
    user_id = st.session_state.get('user_id')
    
    # Verify company admin access
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("🔒 Access denied. Company admin privileges required.")
        return
    
    company_id = st.session_state.company_id
    company_name = st.session_state.company_name
    
    if not company_id:
        st.error("No company associated with this account.")
        return
    
    # Get db instance
    db = get_db()
    
    # Header
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
    
    # SECTION 1: COMPANY PERFORMANCE KPIs
    st.markdown("## 📈 Company Performance")
    perf_metrics = db.get_company_performance_metrics(company_id)
    render_performance_metrics(perf_metrics)
    
    st.markdown("---")
    
    # SECTION 2: AI VALUE METRICS
    st.markdown("## 🤖 AI Value Generated")
    st.caption("How much time and money TenderAI has saved your company")
    ai_metrics = db.get_company_ai_metrics(company_id)
    render_ai_metrics(ai_metrics)
    render_company_time_savings(company_id)
    
    st.markdown("---")
    
    # SECTION 3: TENDER PERFORMANCE
    st.markdown("## 📋 Tender Performance")
    col1, col2 = st.columns(2)
    with col1:
        render_tender_status_chart(company_id)
    with col2:
        render_win_rate_trend(company_id)
    render_tender_performance_table(company_id)
    
    st.markdown("---")
    
    # SECTION 4: BID OPTIMIZATION METRICS
    st.markdown("## 🎯 Bid Optimization Metrics")
    bid_metrics = db.get_bid_optimization_metrics(company_id)
    render_bid_metrics(bid_metrics)
    render_bid_optimization_chart(company_id)
    
    st.markdown("---")
    
    # SECTION 5: TEAM PERFORMANCE
    st.markdown("## 👥 Team Performance")
    col1, col2 = st.columns(2)
    with col1:
        render_team_activity_chart(company_id)
    with col2:
        render_top_performers_table(company_id)
    
    st.markdown("---")
    
    # SECTION 6: EXTENSION USAGE
    st.markdown("## 🤖 Extension Auto-Fill Usage")
    ext_metrics = db.get_extension_usage_metrics(company_id)
    render_extension_metrics(ext_metrics)
    render_extension_usage_trend(company_id)
    
    st.markdown("---")
    
    # SECTION 7: RECENT ACTIVITY & INSIGHTS
    st.markdown("## 📝 Recent Activity & Insights")
    col1, col2 = st.columns(2)
    with col1:
        render_recent_analyses(company_id)
    with col2:
        render_ai_recommendations(company_id)


# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def render_performance_metrics(metrics):
    """Render performance metrics KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tenders", metrics.get('total_tenders', 0),
                  delta=f"{metrics.get('tenders_this_month', 0)} this month")
    with col2:
        st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%",
                  delta=f"{metrics.get('win_rate_change', 0):+.1f}% vs last month")
    with col3:
        st.metric("Total Analyses", metrics.get('total_analyses', 0),
                  delta=f"{metrics.get('analyses_this_month', 0)} this month")
    with col4:
        st.metric("Active Team Members", metrics.get('active_team_members', 0),
                  help="Users who logged in within last 30 days")


def render_ai_metrics(metrics):
    """Render AI metrics KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💡 Hours Saved", f"{metrics.get('hours_saved', 0):,.0f} hrs")
    with col2:
        st.metric("💰 Cost Savings", f"BDT {metrics.get('cost_savings', 0):,.0f}")
    with col3:
        st.metric("⚡ Time per Tender", f"{metrics.get('avg_time_per_tender', 0):.0f} min")
    with col4:
        st.metric("📊 ROI", f"{metrics.get('roi', 0):.0f}x")


def render_bid_metrics(metrics):
    """Render bid optimization metrics KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Recommended Bid", f"BDT {metrics.get('avg_recommended_bid', 0):,.0f}",
                  f"{metrics.get('avg_bid_ratio', 0):.1f}% of OCE")
    with col2:
        st.metric("Avg Win Probability", f"{metrics.get('avg_win_probability', 0):.1f}%")
    with col3:
        st.metric("Expected Savings", f"BDT {metrics.get('total_expected_savings', 0):,.0f}")
    with col4:
        st.metric("Bid Accuracy", f"{metrics.get('bid_accuracy', 0):.1f}%")


def render_extension_metrics(metrics):
    """Render extension usage metrics KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Auto-Fills", metrics.get('total_auto_fills', 0),
                  delta=f"{metrics.get('auto_fills_this_month', 0)} this month")
    with col2:
        remaining = metrics.get('limit', 0) - metrics.get('used', 0)
        st.metric("Remaining Fills", remaining if metrics.get('limit', 0) != -1 else "∞",
                  help=f"Monthly limit: {metrics.get('limit', 0) if metrics.get('limit', 0) != -1 else 'Unlimited'}")
    with col3:
        st.metric("Avg Confidence", f"{metrics.get('avg_confidence', 0):.1f}%")
    with col4:
        st.metric("Time Saved", f"{metrics.get('time_saved_auto_fill', 0):.0f} hrs")


def safe_dataframe(data, required_columns):
    """Safely convert data to DataFrame and check required columns"""
    if not data or len(data) == 0:
        return None
    
    try:
        df = pd.DataFrame(data)
    except Exception as e:
        print(f"Error converting to DataFrame: {e}")
        return None
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"Missing columns: {missing}")
        print(f"Available columns: {df.columns.tolist()}")
        return None
    
    return df


@st.cache_data(ttl=CACHE_TTL)
def get_cached_data(data_func, company_id):
    """Generic cached data fetcher"""
    db = get_db()
    return data_func(db, company_id)


def render_tender_status_chart(company_id):
    """Render tender status pie chart"""
    db = get_db()
    data = db.get_tender_status_data(company_id)
    df = safe_dataframe(data, ['status', 'count'])
    
    if df is None or df.empty:
        st.info("No tender data available")
        return
    
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


def render_win_rate_trend(company_id):
    """Render win rate trend line chart"""
    db = get_db()
    data = db.get_win_rate_trend_data(company_id)
    df = safe_dataframe(data, ['month', 'win_rate'])
    
    if df is None or df.empty:
        st.info("No win rate data available")
        return
    
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
    fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="50% Baseline")
    fig.update_layout(
        title="Win Rate Trend",
        xaxis_title="Month",
        yaxis_title="Win Rate (%)",
        yaxis_range=[0, 100],
        height=350,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bid_optimization_chart(company_id):
    """Render bid optimization comparison chart"""
    db = get_db()
    data = db.get_bid_optimization_data(company_id)
    df = safe_dataframe(data, ['official_estimate', 'recommended_bid', 'actual_bid'])
    
    if df is None or df.empty:
        st.info("No bid optimization data available")
        return
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Official Estimate', x=df.index, y=df['official_estimate'], marker_color='#6b7280'))
    fig.add_trace(go.Bar(name='Recommended Bid', x=df.index, y=df['recommended_bid'], marker_color='#667eea'))
    fig.add_trace(go.Bar(name='Actual Bid', x=df.index, y=df['actual_bid'], marker_color='#10b981'))
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


def render_team_activity_chart(company_id):
    """Render team activity bar chart"""
    db = get_db()
    data = db.get_team_activity_data(company_id)
    df = safe_dataframe(data, ['full_name', 'analyses', 'tenders'])
    
    if df is None or df.empty:
        st.info("No team activity data available")
        return
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Analyses', x=df['full_name'], y=df['analyses'], 
                         marker_color='#667eea', text=df['analyses'], textposition='auto'))
    fig.add_trace(go.Bar(name='Tenders', x=df['full_name'], y=df['tenders'], 
                         marker_color='#10b981', text=df['tenders'], textposition='auto'))
    fig.update_layout(
        title="Team Activity",
        xaxis_title="Team Member",
        yaxis_title="Count",
        barmode='group',
        height=350,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_top_performers_table(company_id):
    """Render top performers table"""
    db = get_db()
    data = db.get_top_performers_data(company_id)
    df = safe_dataframe(data, ['full_name', 'role', 'analyses', 'avg_confidence', 'last_active'])
    
    if df is None or df.empty:
        st.info("No performer data available")
        return
    
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


def render_company_time_savings(company_id):
    """Render time savings trend chart"""
    db = get_db()
    data = db.get_time_savings_data(company_id)
    df = safe_dataframe(data, ['month', 'hours_saved'])
    
    if df is None or df.empty:
        st.info("No time savings data available")
        return
    
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


def render_extension_usage_trend(company_id):
    """Render extension usage trend chart"""
    db = get_db()
    data = db.get_extension_usage_data(company_id)
    df = safe_dataframe(data, ['date', 'fills', 'avg_confidence'])
    
    if df is None or df.empty:
        st.info("No extension usage data available")
        return
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Auto-Fills', x=df['date'], y=df['fills'], 
                         marker_color='#667eea', yaxis='y'))
    fig.add_trace(go.Scatter(name='Confidence Score', x=df['date'], y=df['avg_confidence'],
                             mode='lines+markers', marker_color='#f59e0b', 
                             line=dict(color='#f59e0b', width=2), yaxis='y2'))
    fig.update_layout(
        title="Extension Usage (Last 30 Days)",
        xaxis_title="Date",
        yaxis_title="Auto-Fills",
        yaxis2=dict(title="Confidence Score (%)", overlaying='y', side='right', range=[0, 100]),
        height=350,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_tender_performance_table(company_id):
    """Render tender performance table"""
    db = get_db()
    data = db.get_tender_performance_data(company_id)
    df = safe_dataframe(data, ['tender_id', 'tender_title', 'official_estimate', 'our_bid', 
                               'winning_bid', 'status', 'our_rank', 'total_bidders'])
    
    if df is None or df.empty:
        st.info("No tender data available")
        return
    
    # Calculate bid difference
    df['bid_diff'] = df['our_bid'] - df['winning_bid']
    
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

def render_recent_analyses(company_id):
    """Render recent analyses with better organization"""
    db = get_db()
    data = db.get_recent_analyses_data(company_id)
    
    if not data or len(data) == 0:
        st.info("No recent analyses")
        return
    
    st.markdown("#### 📋 Recent Analyses")
    
    # Group by tender title to remove duplicates
    grouped = {}
    for row in data:
        title = row.get('tender_title', 'Unknown')
        if title not in grouped:
            grouped[title] = {
                'title': title,
                'recommended_bid': row.get('recommended_bid', 0),
                'win_probability': row.get('win_probability', 0),
                'analysis_date': row.get('analysis_date', datetime.now()),
                'count': 1,
                'analyses': [row]
            }
        else:
            grouped[title]['analyses'].append(row)
            grouped[title]['count'] += 1
            # Keep the most recent
            if row.get('analysis_date', datetime.now()) > grouped[title]['analysis_date']:
                grouped[title]['recommended_bid'] = row.get('recommended_bid', 0)
                grouped[title]['win_probability'] = row.get('win_probability', 0)
                grouped[title]['analysis_date'] = row.get('analysis_date', datetime.now())
    
    # Sort by date
    sorted_items = sorted(grouped.values(), 
                         key=lambda x: x['analysis_date'], 
                         reverse=True)
    
    # Display with expandable sections
    for idx, item in enumerate(sorted_items[:10]):
        with st.expander(f"{item['title'][:50]}...", expanded=(idx < 3)):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.metric("Recommended Bid", f"BDT {item['recommended_bid']:,.0f}")
            with col2:
                win_prob = item['win_probability']
                color = "green" if win_prob >= 70 else "orange" if win_prob >= 40 else "red"
                st.metric("Win Probability", f"{win_prob:.0f}%", 
                         delta_color="normal" if win_prob >= 40 else "inverse")
            with col3:
                st.metric("Analyses", item['count'])
            
            st.caption(f"📅 Last analyzed: {pd.to_datetime(item['analysis_date']).strftime('%B %d, %Y at %I:%M %p')}")
            
            # Show analysis history
            if item['count'] > 1:
                with st.expander("📊 Analysis History"):
                    try:
                        history_df = pd.DataFrame(item['analyses'])
                        history_df['analysis_date'] = pd.to_datetime(history_df['analysis_date'])
                        history_df = history_df.sort_values('analysis_date', ascending=False)
                        
                        # Check if win_probability column exists
                        if 'win_probability' in history_df.columns:
                            history_df['win_probability'] = history_df['win_probability'].round(1)
                            st.dataframe(
                                history_df[['analysis_date', 'recommended_bid', 'win_probability']],
                                hide_index=True,
                                column_config={
                                    "analysis_date": "Date",
                                    "recommended_bid": st.column_config.NumberColumn("Recommended Bid", format="BDT %.0f"),
                                    "win_probability": st.column_config.NumberColumn("Win Probability", format="%.1f%%")
                                }
                            )
                        else:
                            # Fallback if win_probability is missing
                            st.dataframe(
                                history_df[['analysis_date', 'recommended_bid']],
                                hide_index=True,
                                column_config={
                                    "analysis_date": "Date",
                                    "recommended_bid": st.column_config.NumberColumn("Recommended Bid", format="BDT %.0f")
                                }
                            )
                    except Exception as e:
                        st.warning(f"Could not display history: {str(e)}")

                 
def render_ai_recommendations(company_id):
    """Render AI recommendations based on company data"""
    db = get_db()
    data = db.get_ai_recommendations_data(company_id)
    recent_data = db.get_recent_analyses_data(company_id)
    
    st.markdown("#### 💡 AI Recommendations")
    
    # Show quick stats
    if recent_data and len(recent_data) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            # Safely calculate average win probability
            win_probs = [r.get('win_probability', 0) for r in recent_data[:10] if r.get('win_probability') is not None]
            avg_win = sum(win_probs) / len(win_probs) if win_probs else 0
            st.metric("Avg Win Probability", f"{avg_win:.1f}%")
        with col2:
            # Safely calculate average bid
            bids = [r.get('recommended_bid', 0) for r in recent_data[:10] if r.get('recommended_bid') is not None]
            avg_bid = sum(bids) / len(bids) if bids else 0
            st.metric("Avg Recommended Bid", f"BDT {avg_bid:,.0f}")
        with col3:
            st.metric("Total Analyses", len(recent_data))
    
    st.markdown("---")
    
    recommendations = []
    
    # Check if data exists and has the expected keys
    recent_losses = data.get('recent_losses', 0) if data else 0
    scenarios_used = data.get('scenarios_used', 0) if data else 0
    competitors_added = data.get('competitors_added', 0) if data else 0
    
    # Priority 1: No analyses yet
    if not recent_data or len(recent_data) == 0:
        recommendations.append(("🔴 HIGH", "🚀 Start analyzing tenders to get AI-powered recommendations for your business."))
    
    # Priority 2: Recent losses
    if recent_losses > 3:
        recommendations.append(("🔴 HIGH", f"📉 You've lost {recent_losses} tenders in the last 3 months. Consider using the Competitive Bid Simulator."))
    
    # Priority 3: Low win probability
    if recent_data and len(recent_data) > 0:
        low_win_count = sum(1 for r in recent_data if r.get('win_probability', 0) < 30 and r.get('win_probability') is not None)
        if low_win_count > 3:
            recommendations.append(("🟡 MEDIUM", f"⚠️ {low_win_count} tenders have low win probability (<30%). Review your bidding strategy."))
    
    # Priority 4: Missing features
    if scenarios_used == 0:
        recommendations.append(("🟡 MEDIUM", "🎲 Generate scenarios using the Competitive Bid Simulator to discover optimal bidding ranges."))
    
    if competitors_added < 3:
        recommendations.append(("🟢 LOW", "👥 Add competitor data to improve win probability predictions by up to 25%."))
    
    # Display recommendations
    if recommendations:
        for priority, rec in recommendations:
            if "🔴 HIGH" in priority:
                st.error(rec)
            elif "🟡 MEDIUM" in priority:
                st.warning(rec)
            else:
                st.info(rec)
    else:
        st.success("✅ Great job! Your company is using TenderAI effectively. Keep up the good work!")
    
    # Show action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎲 Open Bid Simulator", use_container_width=True):
            st.session_state.page = "bid_simulator"
            st.rerun()
    with col2:
        if st.button("👥 Manage Competitors", use_container_width=True):
            st.session_state.page = "competitors"
            st.rerun()
    with col3:
        if st.button("📊 View All Analyses", use_container_width=True):
            st.session_state.page = "analyses"
            st.rerun()