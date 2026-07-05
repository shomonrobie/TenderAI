# modules/boq_admin_report.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.unified_db_manager import get_db_manager

# Cache queries for better performance
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_boq_history(date_from, date_to):
    db = get_db_manager()
    return db.query("""
        SELECT 
            h.id, h.generated_at, h.tender_id, h.tender_title, h.file_name,
            h.item_count, h.total_estimated_cost, h.selected_zone, 
            h.rate_source, h.edition_year, h.status,
            u.username, u.full_name, u.role as user_role,
            c.company_name
        FROM boq_generation_history h
        LEFT JOIN users u ON h.user_id = u.id
        LEFT JOIN companies c ON h.company_id = c.id
        WHERE h.generated_at >= ? AND h.generated_at <= ?
        ORDER BY h.generated_at DESC
    """, params=(date_from, date_to))


@st.cache_data(ttl=300)
def get_bid_submissions():
    db = get_db_manager()
    return db.query("""
        SELECT 
            b.*,
            h.tender_id, h.tender_title, h.total_estimated_cost as boq_estimated_cost,
            h.selected_zone, h.rate_source,
            u.username, u.full_name,
            c.company_name
        FROM bid_submissions b
        JOIN boq_generation_history h ON b.boq_history_id = h.id
        LEFT JOIN users u ON b.submitted_by = u.username
        LEFT JOIN companies c ON b.company_id = c.id
        ORDER BY b.submission_date DESC
    """)


def render_boq_admin_report():
    """Optimized Admin BOQ & Bid Report"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 BOQ & Bid Management Report</h1>
        <p>Comprehensive view of all BOQ generations and bid submissions</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get('user_role') not in ['admin', 'system_admin']:
        st.error("❌ Only administrators can access this report.")
        return

    # Date filters
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
    with col2:
        date_to = st.date_input("To Date", value=datetime.now())

    # Fetch data with caching
    boq_history = get_boq_history(date_from, date_to)
    bid_submissions = get_bid_submissions()

    # Summary Cards (fast - uses cached data)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total BOQ Generations", len(boq_history))
    with col2:
        st.metric("Total Bid Submissions", len(bid_submissions))
    with col3:
        total_value = boq_history['total_estimated_cost'].sum() if not boq_history.empty else 0
        st.metric("Total Estimated Value", f"BDT {total_value:,.2f}")
    with col4:
        st.metric("Unique Tenders", boq_history['tender_id'].nunique() if not boq_history.empty else 0)

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 BOQ Generation Log", "💰 Bid Submissions", 
        "🏢 Company-wise Report", "📊 Tender Analysis"
    ])

    with tab1: render_boq_log(boq_history)
    with tab2: render_bid_submissions(bid_submissions)
    with tab3: render_company_report(boq_history, bid_submissions)
    with tab4: render_tender_analysis(boq_history, bid_submissions)


def render_boq_log(boq_history):
    """Display BOQ generation log"""
    st.markdown("#### 📋 BOQ Generation Log")
    
    if boq_history.empty:
        st.info("No BOQ generations found.")
        return
    
    display_cols = ['generated_at', 'company_name', 'username', 'tender_id', 'item_count', 
                   'total_estimated_cost', 'selected_zone', 'rate_source', 'status']
    
    available_cols = [col for col in display_cols if col in boq_history.columns]
    
    st.dataframe(boq_history[available_cols], use_container_width=True, hide_index=True)
    
    # Export
    csv = boq_history.to_csv(index=False)
    st.download_button(
        "📥 Export BOQ Log to CSV",
        csv,
        f"boq_log_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )


def render_bid_submissions(bid_submissions):
    """Display bid submissions"""
    st.markdown("#### 💰 Bid Submissions")
    
    if bid_submissions.empty:
        st.info("No bid submissions found.")
        return
    
    display_cols = ['submission_date', 'company_name', 'username', 'tender_id', 
                   'boq_estimated_cost', 'submitted_bid_amount', 'status']
    
    available_cols = [col for col in display_cols if col in bid_submissions.columns]
    
    # Calculate variance
    if not bid_submissions.empty:
        bid_submissions = bid_submissions.copy()
        bid_submissions['variance'] = bid_submissions['submitted_bid_amount'] - bid_submissions['boq_estimated_cost']
        bid_submissions['variance_pct'] = (bid_submissions['variance'] / bid_submissions['boq_estimated_cost'] * 100).round(2)
        display_cols.append('variance_pct')
    
    st.dataframe(bid_submissions[available_cols], use_container_width=True, hide_index=True)
    
    csv = bid_submissions.to_csv(index=False)
    st.download_button(
        "📥 Export Bid Submissions to CSV",
        csv,
        f"bid_submissions_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )


def render_company_report(boq_history, bid_submissions):
    """Company-wise BOQ and bid report"""
    st.markdown("#### 🏢 Company-wise Report")
    
    if boq_history.empty:
        st.info("No data available.")
        return
    
    company_stats = boq_history.groupby('company_name').agg({
        'id': 'count',
        'total_estimated_cost': 'sum',
        'tender_id': 'nunique'
    }).rename(columns={'id': 'boq_count', 'total_estimated_cost': 'total_value', 'tender_id': 'unique_tenders'})
    
    if not bid_submissions.empty:
        bid_stats = bid_submissions.groupby('company_name').agg({
            'id': 'count',
            'submitted_bid_amount': 'sum'
        }).rename(columns={'id': 'bid_count', 'submitted_bid_amount': 'total_bid_value'})
        
        company_stats = company_stats.join(bid_stats, how='left').fillna(0)
        company_stats['total_bid_value'] = company_stats['total_bid_value'].apply(lambda x: f"BDT {x:,.2f}")
    
    company_stats['total_value'] = company_stats['total_value'].apply(lambda x: f"BDT {x:,.2f}")
    
    st.dataframe(company_stats, use_container_width=True)
    
    # Chart
    if not boq_history.empty:
        st.markdown("#### 📊 BOQ Generation Trend")
        trend_data = boq_history.groupby(boq_history['generated_at'].dt.date).size().reset_index(name='count')
        trend_data = trend_data.rename(columns={'generated_at': 'Date', 'count': 'BOQ Count'})
        st.line_chart(trend_data.set_index('Date'))


def render_tender_analysis(boq_history, bid_submissions):
    """Tender-wise analysis"""
    st.markdown("#### 📊 Tender Analysis")
    
    if boq_history.empty:
        st.info("No data available.")
        return
    
    tender_summary = boq_history.groupby('tender_id').agg({
        'id': 'count',
        'total_estimated_cost': 'first',
        'company_name': lambda x: ', '.join(set(x.dropna()))
    }).rename(columns={'id': 'boq_versions', 'total_estimated_cost': 'estimated_cost', 'company_name': 'companies'})
    
    if not bid_submissions.empty:
        tender_bids = bid_submissions.groupby('tender_id').agg({
            'submitted_bid_amount': ['min', 'max', 'mean', 'count']
        })
        tender_bids.columns = ['min_bid', 'max_bid', 'avg_bid', 'bid_count']
        tender_summary = tender_summary.join(tender_bids, how='left').fillna(0)
    
    st.dataframe(tender_summary, use_container_width=True)