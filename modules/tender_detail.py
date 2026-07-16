"""
Tender Detail Components - Refactored
State-Driven View Router Pattern with st.dataframe
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

from database.unified_db_manager import get_db_manager
from utils.helpers import debug_print

logger = logging.getLogger(__name__)

db = get_db_manager()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _ensure_dataframe(data):
    """Convert list of dicts to DataFrame if needed"""
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, list):
        return pd.DataFrame(data) if data else pd.DataFrame()
    else:
        return pd.DataFrame()


def _get_simulated_nppi(procurement_type: str, tender_date: str = None) -> float:
    """Simulate realistic NPPI based on PPR 2025 rules."""
    
    procurement_type = str(procurement_type).lower() if procurement_type else 'works'
    
    base_nppi = {
        'works': 0.912,
        'goods': 0.935,
        'services': 0.908,
        'consultancy': 0.885
    }.get(procurement_type, 0.92)
    
    month_adjustment = 0.0
    if tender_date:
        try:
            if isinstance(tender_date, (datetime, pd.Timestamp)):
                dt = tender_date
            elif isinstance(tender_date, str):
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%b-%Y', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(str(tender_date)[:10], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            month_adjustment = (dt.month - 6) * 0.003
            year_adjustment = (dt.year - 2020) * 0.001
            month_adjustment += year_adjustment
        except:
            pass
    
    nppi = base_nppi + month_adjustment
    nppi = max(0.82, min(0.99, nppi))
    
    return round(nppi, 3)


def _generate_html_report(tender_data, competitor_bids_sorted, official_estimate, 
                         nppi_factor, slt_lower, wa, wsd, winner_bid_obj=None, 
                         avg_nppi=None, predicted_winner=None):
    """Generate HTML report for tender analysis"""
    
    tender_id = tender_data.get('tender_id', 'N/A')
    tender_title = tender_data.get('tender_title', 'Untitled')
    procurement_type = tender_data.get('procurement_type', 'Works').title()
    current_date = datetime.now().strftime("%d %B %Y")
    
    display_nppi = avg_nppi if avg_nppi is not None else nppi_factor
    
    if winner_bid_obj:
        winner_name = winner_bid_obj.get('name', 'N/A')
        winning_bid = winner_bid_obj.get('bid', 0)
        winner_label = "Declared Winner"
    elif predicted_winner:
        winner_name = predicted_winner
        winning_bid = 0
        winner_label = "Predicted Winner"
    else:
        winner_name = "Not Declared"
        winning_bid = 0
        winner_label = "No Winner"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>TenderAI Report - {tender_id}</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; padding: 30px; background: #f8f9fa; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 30px; border-radius: 12px; }}
            .container {{ max-width: 1100px; margin: auto; background: white; padding: 30px; border-radius: 12px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f1f5f9; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .metric {{ background: #f8fafc; padding: 15px; border-radius: 8px; text-align: center; }}
            .prediction {{ background: #f0f9ff; padding: 20px; border-radius: 10px; border-left: 6px solid #3b82f6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TenderAI Analysis Report</h1>
                <p><strong>Tender ID:</strong> {tender_id} | <strong>Date:</strong> {current_date}</p>
            </div>
            
            <h2>Tender Summary</h2>
            <div class="metric-grid">
                <div class="metric"><strong>Title</strong><br>{tender_title}</div>
                <div class="metric"><strong>{winner_label}</strong><br>{winner_name}</div>
                <div class="metric"><strong>OCE</strong><br>BDT {official_estimate:,.2f}</div>
                <div class="metric"><strong>Type</strong><br>{procurement_type}</div>
            </div>
            
            <h2>SLT Analysis</h2>
            <table>
                <tr><th>Parameter</th><th>Value</th></tr>
                <tr><td>Weighted Average (WA)</td><td>BDT {wa:,.2f}</td></tr>
                <tr><td>Weighted Std Dev (WSD)</td><td>BDT {wsd:,.2f}</td></tr>
                <tr><td><strong>SLT Lower Limit</strong></td><td><strong>BDT {slt_lower:,.2f}</strong></td></tr>
                <tr><td>Simulated NPPI Factor</td><td>{nppi_factor:.3f}</td></tr>
            </table>
            
            <h2>Bid Comparison</h2>
            <table>
                <tr><th>Rank</th><th>Competitor</th><th>Bid Amount</th><th>Status</th></tr>
    """
    
    for i, b in enumerate(competitor_bids_sorted, 1):
        status = "🏆 Winner" if b.get('is_winner') else "Competitor"
        html += f"""
                <tr><td>{i}</td><td>{b['name']}</td><td>BDT {b['bid']:,.2f}</td><td>{status}</td></tr>
        """
    
    html += f"""
            </table>
            
            <div class="prediction">
                <h3>Key Insights</h3>
                <ul>
                    <li>Analysis based on Official Cost Estimate: BDT {official_estimate:,.2f}</li>
                    <li>Simulated NPPI Factor: {nppi_factor:.3f}</li>
                </ul>
            </div>
            
            <footer style="text-align:center; margin-top:40px; color:#64748b;">
                Generated by <strong>TenderAI</strong> • {current_date}
            </footer>
        </div>
    </body>
    </html>
    """
    
    return html

def render_tender_grid_view():
    """Render e-GP style grid view with st.dataframe"""
    
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role')

    if st.session_state.get('debug_mode', False):
        st.sidebar.write(f"Company ID: {company_id}")
        st.sidebar.write(f"User Role: {user_role}")
    # if not company_id or user_role !='individual':
    #     st.warning(f"Please select a company first. Your role is : {user_role} and your Company ID is {company_id}")
    #     return
    
    st.markdown("### 📋 My Tenders/Proposals")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1])
    
    with col1:
        if st.button("➕ Create New Tender X", key="tender_add_btn", type="primary", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_tender_id = None
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
            st.session_state.page = "render_tender_form"
            st.rerun()
    
    with col2:
        st.session_state.tender_search = st.text_input(
            "🔍 Search",
            placeholder="Tender ID, title, or entity...",
            value=st.session_state.tender_search,
            key="tender_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        status_options = ["All", "draft", "submitted", "under_review", "evaluated", "won", "lost"]
        st.session_state.tender_status_filter = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(st.session_state.tender_status_filter) if st.session_state.tender_status_filter in status_options else 0,
            key="tender_status_filter_select",
            label_visibility="collapsed"
        )
    
    with col4:
        st.session_state.tender_per_page = st.selectbox(
            "Rows",
            options=[5, 10, 25, 50],
            index=[5, 10, 25, 50].index(st.session_state.tender_per_page) if st.session_state.tender_per_page in [5, 10, 25, 50] else 1,
            key="tender_per_page_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH TENDERS =====
    try:
        status = None if st.session_state.tender_status_filter == "All" else st.session_state.tender_status_filter
        tenders = db.get_company_tenders(company_id, status_filter=status, limit=100)
    except Exception as e:
        st.error(f"Error loading tenders: {e}")
        return
    
    if not tenders:
        st.info("No tenders found. Click 'Create New Tender' to get started.")
        return
    
    # ===== FILTER BY SEARCH =====
    if st.session_state.tender_search:
        search_lower = st.session_state.tender_search.lower()
        tenders = [
            t for t in tenders
            if search_lower in str(t.get('tender_id', '')).lower()
            or search_lower in str(t.get('tender_title', '')).lower()
            or search_lower in str(t.get('procuring_entity', '')).lower()
        ]
    
    if not tenders:
        st.info("No tenders match the search criteria")
        return
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tenders", len(tenders))
    with col2:
        submitted = len([t for t in tenders if t.get('bid_status') == 'submitted'])
        st.metric("Submitted", submitted)
    with col3:
        won = len([t for t in tenders if t.get('bid_status') == 'won'])
        st.metric("Won", won)
    with col4:
        lost = len([t for t in tenders if t.get('bid_status') == 'lost'])
        st.metric("Lost", lost)
    
    st.markdown("---")
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, tender in enumerate(tenders):
        status_display = tender.get('bid_status', 'draft').title()
        status_class = {
            'draft': 'tender-status-draft',
            'submitted': 'tender-status-submitted',
            'under_review': 'tender-status-under_review',
            'evaluated': 'tender-status-processing',
            'won': 'tender-status-won',
            'lost': 'tender-status-lost',
            'awarded': 'tender-status-awarded'
        }.get(tender.get('bid_status', 'draft'), 'tender-status-draft')
        
        df_data.append({
            'id': tender.get('id'),
            'tender_id': tender.get('tender_id', 'N/A'),
            'tender_title': str(tender.get('tender_title', ''))[:60],
            'procuring_entity': str(tender.get('procuring_entity', ''))[:30],
            'official_estimate': tender.get('official_estimate'),
            'status': status_display,
            'status_class': status_class,
            'status_raw': tender.get('bid_status', 'draft'),
            'submission_deadline': str(tender.get('submission_deadline', ''))[:10] if tender.get('submission_deadline') else '',
            'created_at': str(tender.get('created_at', ''))[:10] if tender.get('created_at') else '',
            '_record': tender
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['tender_id', 'tender_title', 'procuring_entity', 'official_estimate', 'status', 'submission_deadline']
    
    # Style the status column
    def color_status(val):
        if 'Won' in str(val) or 'Awarded' in str(val):
            return 'color: #065f46; background-color: #d1fae5;'
        elif 'Lost' in str(val):
            return 'color: #991b1b; background-color: #fee2e2;'
        elif 'Submitted' in str(val):
            return 'color: #0369a1; background-color: #e0f2fe;'
        elif 'Under Review' in str(val):
            return 'color: #92400e; background-color: #fef3c7;'
        elif 'Draft' in str(val):
            return 'color: #475569; background-color: #f1f5f9;'
        return ''
    
    styled_df = df[display_columns].style.map(color_status, subset=['status'])
    
    event = st.dataframe(
        styled_df,
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "tender_id": st.column_config.Column("Tender ID", width="medium"),
            "tender_title": st.column_config.Column("Title", width="large"),
            "procuring_entity": st.column_config.Column("Entity", width="medium"),
            "official_estimate": st.column_config.Column("Estimate (BDT)", width="medium"),
            "status": st.column_config.Column("Status", width="small"),
            "submission_deadline": st.column_config.Column("Deadline", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            tender_id = row_data.get('id')
            if tender_id:
                st.session_state.tender_selected_id = tender_id
                st.session_state.tender_view = "detail"
                st.rerun()
    
    # ===== PAGINATION =====
    per_page = st.session_state.tender_per_page
    total = len(tenders)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (st.session_state.tender_page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    
    with col1:
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} tenders")
    
    with col2:
        if st.button("◀ Prev", key="tender_prev", disabled=(st.session_state.tender_page <= 1), use_container_width=True):
            st.session_state.tender_page -= 1
            st.rerun()
    
    with col3:
        if st.button("Next ▶", key="tender_next", disabled=(st.session_state.tender_page >= total_pages), use_container_width=True):
            st.session_state.tender_page += 1
            st.rerun()
    
    with col4:
        jump_to = st.number_input(
            "Jump to page",
            min_value=1,
            max_value=total_pages if total_pages > 0 else 1,
            value=st.session_state.tender_page,
            step=1,
            key="tender_jump_to",
            label_visibility="collapsed"
        )
        if jump_to != st.session_state.tender_page and 1 <= jump_to <= total_pages:
            st.session_state.tender_page = jump_to
            st.rerun()

def render_tender_detail_page(tender_db_id: int):
    """Render full-page detail view for a tender using database ID"""
    
    print(f"🔍 render_tender_detail_page() called with tender_db_id: {tender_db_id}")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    from database.unified_db_manager import get_db_manager
    db = get_db_manager()
    
    try:
        tender = db.get_tender_by_db_id(tender_db_id, company_id)
        print(f"🔍 tender found: {tender is not None}")
        if tender:
            print(f"🔍 tender_id: {tender.get('tender_id')}")
            print(f"🔍 tender_title: {tender.get('tender_title')}")
    except Exception as e:
        print(f"❌ Error getting tender: {e}")
        import traceback
        traceback.print_exc()
        st.error("Error loading tender details")
        return
    
    if not tender:
        st.error("Tender not found")
        if st.button("← Back to Tender List", key="tender_back_not_found"):
            st.session_state.tender_view = "grid"
            st.session_state.tender_selected_id = None
            st.rerun()
        return
    
    # ✅ Debug: Log before rendering
    print("🔍 Rendering tender detail header...")
    
    st.markdown('<div class="tender-detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    try:
        tender_id_display = tender.get('tender_id', 'N/A')
        title = tender.get('tender_title', 'Untitled')
        status = tender.get('bid_status', 'draft')
        print(f"🔍 Header values: tender_id={tender_id_display}, title={title}, status={status}")
    except Exception as e:
        print(f"❌ Error getting header values: {e}")
        st.error("Error displaying tender header")
        return
    
    status_display = {
        'won': 'Contract Awarded',
        'submitted': 'Being processed',
        'draft': 'Draft',
        'lost': 'Lost',
        'awarded': 'Contract Awarded',
        'under_review': 'Under Review'
    }.get(status, status.title())
    
    status_class = {
        'won': 'tender-status-won',
        'submitted': 'tender-status-submitted',
        'draft': 'tender-status-draft',
        'lost': 'tender-status-lost',
        'awarded': 'tender-status-awarded',
        'under_review': 'tender-status-under_review'
    }.get(status, 'tender-status-draft')
    
    st.markdown(f"""
    <div class="tender-detail-header">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
            <div>
                <h1>📄 Tender/Proposal Detail</h1>
                <div class="subtitle">{title}</div>
            </div>
            <div>
                <span class="tender-status-badge {status_class}">{status_display}</span>
            </div>
        </div>
        <div class="meta-row">
            <span class="meta-item"><strong>Tender/Proposal ID:</strong> {tender_id_display}</span>
            <span class="meta-item"><strong>Closing Date:</strong> {tender.get('submission_deadline', 'N/A')}</span>
            <span class="meta-item"><strong>Procuring Entity:</strong> {tender.get('procuring_entity', 'N/A')[:60]}</span>
            <span class="meta-item"><strong>Status:</strong> {status_display}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== BACK BUTTON =====
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Tender List", key="tender_back_to_grid", use_container_width=True):
            st.session_state.tender_view = "grid"
            st.session_state.tender_selected_id = None
            st.rerun()
    
    st.divider()
    
    # ===== TENDER DETAIL TABS =====
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Information",
        "🏆 Winner",
        "📊 Bid Analysis",
        "📊 Analysis Report",
        "🏆 Results CRUD",
        "📥 Import Data",
        "👥 Team & Milestones"
    ])
    
    with tab1:
        render_information_tab(tender)
    
    with tab2:
        render_winner_tab(tender)
    
    with tab3:
        render_bid_analysis_tab(tender)
    
    with tab4:
        render_analysis_report_tab(tender)
    
    with tab5:
        render_results_crud_tab(tender)
    
    with tab6:
        render_import_tab(tender)
    
    with tab7:
        render_team_milestones_tab(tender)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_information_tab(tender: Dict[str, Any]):
    """Render the Information tab"""
    st.markdown("### 📋 Tender Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basic Information")
        st.info(f"**Tender ID:** `{tender.get('tender_id', 'N/A')}`")
        st.markdown(f"**Title:** {tender.get('tender_title', 'N/A')}")
        st.markdown(f"**Procuring Entity:** {tender.get('procuring_entity', 'N/A')}")
        st.markdown(f"**Division:** {tender.get('division', 'N/A')}")
        st.markdown(f"**District:** {tender.get('district', 'N/A')}")
        st.markdown(f"**Procurement Type:** {tender.get('procurement_type', 'N/A')}")
        st.markdown(f"**Bid Status:** {tender.get('bid_status', 'N/A')}")
        st.markdown(f"**Evaluation Status:** {tender.get('evaluation_status', 'N/A')}")
    
    with col2:
        st.markdown("#### Financial Information")
        official_estimate = tender.get('official_estimate', 0) or 0  # ✅ Handle None
        st.info(f"**Official Estimate:** BDT {float(official_estimate):,.2f}" if official_estimate else "**Official Estimate:** N/A")
        
        tender_security = tender.get('tender_security', 0) or 0  # ✅ Handle None
        st.markdown(f"**Tender Security:** BDT {float(tender_security):,.2f}" if tender_security else "**Tender Security:** N/A")
        
        document_fee = tender.get('document_fee', 0) or 0  # ✅ Handle None
        st.markdown(f"**Document Fee:** BDT {float(document_fee):,.2f}" if document_fee else "**Document Fee:** N/A")
        
        our_bid = tender.get('our_bid_amount', 0) or 0  # ✅ Handle None
        if our_bid > 0:
            st.markdown(f"**Our Bid:** BDT {float(our_bid):,.2f}")
        else:
            st.markdown("**Our Bid:** Not set")
    
    st.markdown("#### Important Dates")
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline = tender.get('submission_deadline')
        st.markdown(f"**Submission Deadline:** {deadline if deadline else 'N/A'}")
    with col2:
        pub_date = tender.get('tender_publication_date')
        st.markdown(f"**Published:** {pub_date if pub_date else 'N/A'}")
    with col3:
        opening_date = tender.get('bid_opening_date')
        st.markdown(f"**Opening Date:** {opening_date if opening_date else 'N/A'}")


def render_winner_tab(tender: Dict[str, Any]):
    """Render the Winner tab"""
    st.markdown("### 🏆 Winner Information")
    
    winner = tender.get('winning_competitor')
    winner_amount = tender.get('winning_bid_amount', 0) or 0
    official_estimate = tender.get('official_estimate', 0) or 0
    tender_id = tender.get('tender_id')
    company_id = st.session_state.get('company_id')
    
    if winner and winner_amount > 0:
        st.success(f"🏆 **Winner:** {winner}")
        st.info(f"**Winning Bid Amount:** BDT {float(winner_amount):,.2f}")
        
        if official_estimate > 0 and winner_amount > 0:
            nppi = (float(winner_amount) / float(official_estimate)) * 100
            st.metric("NPPI Factor", f"{nppi:.2f}%")
    else:
        st.warning("No winner declared yet for this tender.")
        st.info("💡 You can declare a winner in the 'Results CRUD' tab.")
    
    # ✅ Bid history - with DataFrame conversion
    if company_id and tender_id:
        bids_list = db.get_competitor_bids(tender_id, company_id)
        bids_df = _ensure_dataframe(bids_list)
        
        if not bids_df.empty:
            bids_df['bid_amount'] = bids_df['bid_amount'].apply(
                lambda x: f"BDT {x:,.2f}" if x and x > 0 else "N/A"
            )
            bids_df['was_winner'] = bids_df['was_winner'].apply(
                lambda x: "🏆 Winner" if x else ""
            )
            st.dataframe(bids_df, use_container_width=True, hide_index=True)
        else:
            st.info("No bid history available. Import bid data first.")

def render_bid_analysis_tab(tender: Dict[str, Any]):
    """Render the Bid Analysis tab"""
    st.markdown("### 📊 Bid Analysis")
    st.info("Comprehensive analysis available in the 'Analysis Report' tab.")
    
    official_estimate = tender.get('official_estimate', 0) or 0
    our_bid = tender.get('our_bid_amount', 0) or 0
    tender_id = tender.get('tender_id')
    company_id = st.session_state.get('company_id')
    
    if official_estimate > 0 and our_bid > 0:
        nppi = (float(our_bid) / float(official_estimate)) * 100
        st.metric("Our NPPI", f"{nppi:.2f}%")
        
        if nppi < 85:
            st.warning("⚠️ Your bid is significantly below OCE. This may trigger SLT scrutiny.")
        elif nppi > 105:
            st.warning("⚠️ Your bid is above OCE. Consider reviewing your pricing.")
        else:
            st.success("✅ Your bid is within a reasonable range.")
        
        # ✅ Bid comparison - with DataFrame conversion
        if company_id and tender_id:
            bids_list = db.get_competitor_bids(tender_id, company_id)
            bids_df = _ensure_dataframe(bids_list)
            
            if not bids_df.empty:
                # Add our bid to comparison
                our_row = {'competitor_name': '🏢 Our Bid', 'bid_amount': our_bid, 'was_winner': 0}
                bids_df = pd.concat([bids_df, pd.DataFrame([our_row])], ignore_index=True)
                bids_df = bids_df.sort_values('bid_amount').reset_index(drop=True)
                
                bids_df['bid_amount'] = bids_df['bid_amount'].apply(
                    lambda x: f"BDT {x:,.2f}" if x and x > 0 else "N/A"
                )
                bids_df['was_winner'] = bids_df['was_winner'].apply(
                    lambda x: "🏆 Winner" if x else ""
                )
                
                st.dataframe(bids_df, use_container_width=True, hide_index=True)
            else:
                st.info("No competitor data available.")
    else:
        st.info("💡 Set your bid amount and OCE to see NPPI analysis.")
                    
def render_analysis_report_tab(tender: Dict[str, Any]):
    """Render the Analysis Report tab with full PPR 2025 compliant analysis"""
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT • NPPI Analysis • Winner Prediction • Sensitivity*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    tender_id = tender.get('tender_id')
    tender_title = tender.get('tender_title', 'Untitled')
    official_estimate = tender.get('official_estimate', 0) or 0
    
    
    
    if official_estimate <= 0:
        st.warning("⚠️ OCE is required for analysis. Please update the tender with Official Cost Estimate.")
        return
    
    tender_id = tender.get('tender_id')
    procurement_type = tender.get('procurement_type', 'works') or 'works'
    tender_date = tender.get('tender_publication_date') or tender.get('created_at')
    st.success(f"✅ Selected: **{tender_title}** | OCE: BDT {official_estimate:,.2f}")

    # ✅ Load bids - returns List[Dict]
    bids_list = db.get_competitor_bids(tender_id, company_id)
    bids_df = _ensure_dataframe(bids_list)
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return

    if 'was_winner' not in bids_df.columns:
        bids_df['was_winner'] = False
    
    # Ensure bid_amount is float
    bids_df['bid_amount'] = bids_df['bid_amount'].astype(float)

    # Prepare bids
    competitor_bids = []
    for _, row in bids_df.iterrows():
        name = row.get('competitor_name', '')
        bid = float(row.get('bid_amount', 0)) if row.get('bid_amount') else 0
        is_winner = row.get('was_winner', 0) == 1
        if bid > 0:
            competitor_bids.append({'name': name, 'bid': bid, 'is_winner': is_winner})
    
    competitor_bids_sorted = sorted(competitor_bids, key=lambda x: x['bid'])
    
    if len(competitor_bids_sorted) < 2:
        st.warning("At least 2 bids required for analysis.")
        return
    
    # ===================== OFFICIAL SLT =====================
    st.markdown("---")
    st.markdown("### 🎯 Official PPR 2025 SLT Analysis")
    
    nppi_factor = _get_simulated_nppi(procurement_type, tender_date)
    x_nppi = official_estimate * nppi_factor
    n = len(competitor_bids_sorted)
    bid_amounts = [b['bid'] for b in competitor_bids_sorted]
    avg_quoted = sum(bid_amounts) / n
    
    wa = (0.20 * official_estimate) + (0.30 * x_nppi) + (0.50 * avg_quoted)
    variance = sum((b - wa) ** 2 for b in bid_amounts) / n
    wsd = variance ** 0.5
    slt_lower = wa - wsd
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("OCE", f"BDT {official_estimate:,.2f}")
    with col2: 
        st.metric("X_NPPI", f"BDT {x_nppi:,.2f}", f"NPPI: {nppi_factor:.3f}")
    with col3: 
        st.metric("Weighted Avg", f"BDT {wa:,.2f}")
    with col4: 
        st.metric("SLT Lower Limit", f"BDT {slt_lower:,.2f}")
    
    # ===================== NPPI SENSITIVITY ANALYSIS =====================
    st.markdown("---")
    st.markdown("### 📈 NPPI Sensitivity Analysis")
    
    nppi_range = np.arange(0.80, 1.00, 0.005)
    sensitivity_data = []
    
    for nppi in nppi_range:
        evaluated = [b['bid'] * nppi for b in competitor_bids_sorted]
        sorted_eval = sorted(evaluated)
        lowest = sorted_eval[0]
        second_lowest = sorted_eval[1] if len(sorted_eval) > 1 else lowest
        margin = second_lowest - lowest
        
        sensitivity_data.append({
            'NPPI': round(nppi, 3),
            'Lowest Evaluated': round(lowest, 2),
            'Margin to 2nd': round(margin, 2),
            'Potential Winner': competitor_bids_sorted[0]['name'] if lowest == competitor_bids_sorted[0]['bid'] * nppi else "Changes"
        })
    
    sens_df = pd.DataFrame(sensitivity_data)
    
    # Visualization
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sens_df['NPPI'],
        y=sens_df['Lowest Evaluated'],
        mode='lines+markers',
        name='Lowest Evaluated Price',
        line=dict(color='#1f77b4', width=3)
    ))
    fig.add_trace(go.Scatter(
        x=sens_df['NPPI'],
        y=sens_df['Margin to 2nd'],
        mode='lines',
        name='Margin to 2nd Lowest',
        line=dict(color='#ff7f0e', dash='dash')
    ))
    fig.update_layout(
        title="NPPI Sensitivity Analysis",
        xaxis_title="NPPI Factor",
        yaxis_title="Price (BDT)",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(sens_df.style.format({
        'NPPI': '{:.3f}',
        'Lowest Evaluated': 'BDT {:,.2f}',
        'Margin to 2nd': 'BDT {:,.2f}'
    }), use_container_width=True, hide_index=True)
    
    # ===================== WINNER PREDICTION =====================
    st.markdown("---")
    st.markdown("### 🔮 Winner Prediction (NPPI Range + SLT)")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        nppi_min = st.number_input("NPPI Min", value=0.82, step=0.001, format="%.3f", key="nppi_min_analysis")
        nppi_max = st.number_input("NPPI Max", value=0.98, step=0.001, format="%.3f", key="nppi_max_analysis")
    with col2:
        if st.button("🔮 Run Prediction", type="primary", use_container_width=True, key="run_prediction_analysis"):
            predictions = []
            nppi_values = np.arange(nppi_min, nppi_max + 0.001, 0.001)
            
            for nppi in nppi_values:
                evaluated = []
                for b in competitor_bids_sorted:
                    eval_price = b['bid'] * nppi
                    x_nppi_test = official_estimate * nppi
                    wa_test = (0.20 * official_estimate) + (0.30 * x_nppi_test) + (0.50 * avg_quoted)
                    var_test = sum((b['bid'] - wa_test) ** 2 for b in competitor_bids_sorted) / n
                    wsd_test = var_test ** 0.5
                    slt_test = wa_test - wsd_test
                    
                    final_score = eval_price if b['bid'] >= slt_test else eval_price * 1.4
                    evaluated.append({'name': b['name'], 'final_score': final_score})
                
                sorted_eval = sorted(evaluated, key=lambda x: x['final_score'])
                predictions.append({
                    'nppi': round(nppi, 3),
                    'predicted_winner': sorted_eval[0]['name'],
                    'evaluated_price': round(sorted_eval[0]['final_score'], 2)
                })
            
            pred_df = pd.DataFrame(predictions)
            most_likely = pred_df['predicted_winner'].mode()[0]
            
            st.success(f"**Most Likely Winner:** {most_likely}")
            st.dataframe(pred_df.style.format({
                'nppi': '{:.3f}',
                'evaluated_price': 'BDT {:,.2f}'
            }), use_container_width=True, hide_index=True)
    
    # ===================== REVERSE ENGINEERING =====================
    winner_bid_obj = next((b for b in competitor_bids_sorted if b['is_winner']), None)
    
    if winner_bid_obj:
        st.markdown("---")
        st.markdown("#### 🔍 Reverse-Engineered NPPI Factor")
        
        nppi_range = np.arange(0.75, 1.05, 0.001)
        results = []
        winner_name = winner_bid_obj['name']
        
        for nppi_test in nppi_range:
            evaluated = [{'name': b['name'], 'price': b['bid'] * nppi_test} for b in competitor_bids_sorted]
            sorted_eval = sorted(evaluated, key=lambda x: x['price'])
            is_correct = sorted_eval[0]['name'] == winner_name
            rank = next((i+1 for i, x in enumerate(sorted_eval) if x['name'] == winner_name), None)
            
            results.append({'nppi': nppi_test, 'is_correct': is_correct, 'rank': rank})
        
        correct_nppi = [r for r in results if r['is_correct']]
        if correct_nppi:
            avg_nppi = sum(r['nppi'] for r in correct_nppi) / len(correct_nppi)
            st.success(f"**Most Likely NPPI Used by e-GP: {avg_nppi:.3f}**")
            
            correct_values = [r['nppi'] for r in correct_nppi]
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=correct_values, nbinsx=30, name="Successful NPPI", marker_color="green"))
            fig.update_layout(title="Distribution of NPPI Values That Make Winner #1", xaxis_title="NPPI Factor", yaxis_title="Frequency", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not find exact NPPI. Showing closest match.")
    
    # ===================== HTML REPORT =====================
    st.markdown("---")
    if st.button("📄 Generate Professional HTML Report", type="primary", use_container_width=True, key="generate_report_analysis"):
        html_content = _generate_html_report(
            tender_data=tender,
            competitor_bids_sorted=competitor_bids_sorted,
            official_estimate=official_estimate,
            nppi_factor=nppi_factor,
            slt_lower=slt_lower,
            wa=wa,
            wsd=wsd,
            winner_bid_obj=winner_bid_obj,
            avg_nppi=avg_nppi if 'avg_nppi' in locals() else None,
            predicted_winner=most_likely if 'most_likely' in locals() else None
        )
        
        st.download_button(
            "⬇️ Download HTML Report",
            html_content,
            f"TenderAI_Report_{tender_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            "text/html",
            use_container_width=True,
            key="download_report_analysis"
        )

def render_results_crud_tab(tender: Dict[str, Any]):
    """Render the Results CRUD tab with editable bid amounts"""
    st.markdown("### 🏆 Tender Results CRUD")
    st.caption("Edit bid amounts • Winner selection is **optional**")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    tender_id = tender.get('tender_id')
    tender_title = tender.get('tender_title', 'Untitled')
    official_estimate = tender.get('official_estimate', 0) or 0
    
    st.success(f"✅ Selected: **{tender_title}** | OCE: BDT {official_estimate:,.2f}")
    
    # ✅ Load current bids - returns List[Dict]
    bids_list = db.get_competitor_bids(tender_id, company_id)
    bids_df = _ensure_dataframe(bids_list)
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return
    
    # Ensure proper types
    if 'was_winner' not in bids_df.columns:
        bids_df['was_winner'] = False
    
    # Ensure bid_amount is float
    bids_df['bid_amount'] = bids_df['bid_amount'].astype(float)

    
    st.markdown("#### 📋 Edit Bid Amounts")
    st.caption("**Note:** Selecting a winner is optional. You can save without any winner.")
    
    # Editable Table
    edited_df = st.data_editor(
        bids_df,
        column_config={
            "competitor_name": st.column_config.TextColumn("Bidder Name", disabled=True),
            "bid_amount": st.column_config.NumberColumn(
                "Bid Amount (BDT)", 
                min_value=0.0, 
                format="%.3f",
                step=1.0
            ),
            "was_winner": st.column_config.CheckboxColumn(
                "Mark as Winner", 
                default=False,
                help="Only one bidder can be winner"
            ),
            "bid_date": st.column_config.DateColumn("Bid Date", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"editor_results_{tender_id}"
    )
    
    # Winner status
    winners = edited_df[edited_df['was_winner'] == True]
    if len(winners) > 1:
        st.error("⚠️ Only **one** winner is allowed.")
    elif len(winners) == 1:
        w = winners.iloc[0]
        if official_estimate > 0:
            nppi = (float(w['bid_amount']) / official_estimate) * 100
            st.success(f"🏆 Winner: **{w['competitor_name']}** | Bid: BDT {w['bid_amount']:,.3f} | NPPI: **{nppi:.3f}%**")
    
    # Save Button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True, key=f"save_results_{tender_id}"):
            success_count = 0
            
            for _, row in edited_df.iterrows():
                bid_amount = float(row['bid_amount'])
                was_winner = bool(row['was_winner'])
                
                success = db.update_competitor_bid(
                    tender_id=tender_id,
                    competitor_name=row['competitor_name'],
                    bid_amount=bid_amount,
                    was_winner=was_winner
                )
                if success:
                    success_count += 1
            
            # Update main tender result if winner is selected
            if len(winners) == 1:
                w = winners.iloc[0]
                db.update_tender_result(
                    tender_id=tender_id,
                    winning_bid_amount=float(w['bid_amount']),
                    winning_competitor=w['competitor_name'],
                    our_rank=1,
                    total_bidders=len(edited_df),
                    award_date=datetime.now().strftime('%Y-%m-%d'),
                    bid_status='awarded'
                )
                st.success("✅ All changes saved and **winner updated**!")
            else:
                # Clear winner from tender record
                db.clear_tender_winner(tender_id)
                st.success(f"✅ {success_count} bids saved successfully (No winner marked)")
            
            st.rerun()
    
    with col2:
        if st.button("📥 Export Current Bids to CSV", use_container_width=True, key=f"export_results_{tender_id}"):
            export_df = edited_df.copy()
            export_df['bid_amount'] = export_df['bid_amount'].apply(lambda x: f"{x:.3f}")
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"bid_results_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"download_results_{tender_id}"
            )

def render_import_tab(tender: Dict[str, Any]):
    """Render the Import Data tab"""
    st.markdown("### 📥 Import Tender Opening Report")
    st.caption("Upload Excel file to import competitor bid data")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    tender_id = tender.get('tender_id')
    tender_title = tender.get('tender_title', 'Untitled')
    official_estimate = tender.get('official_estimate', 0) or 0
    
    st.success(f"✅ Selected: **{tender_title}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    # ✅ Check if data already exists - with DataFrame conversion
    bids_list = db.get_competitor_bids(tender_id, company_id)
    bids_df = _ensure_dataframe(bids_list)
    existing_data_count = len(bids_df)

    
    # Show warning if data exists
    replace_data = False
    if existing_data_count > 0:
        st.warning(f"⚠️ **{existing_data_count} bid records** already exist for this tender.")
        
        replace_data = st.checkbox(
            "🔄 Replace existing data (delete current bids and import new)",
            value=False,
            key=f"replace_checkbox_{tender_id}",
            help="If checked, all existing bid data for this tender will be deleted before importing new data."
        )
        
        if replace_data:
            st.error("⚠️ **Warning:** This will delete all existing bid records for this tender. This action cannot be undone!")
    else:
        st.info("ℹ️ No existing bid data found for this tender. Import will add new records.")
    
    st.divider()
    st.subheader("Upload Opening Report")
    
    try:
        from modules.tender_data_importer import TenderDataImporter
        importer = TenderDataImporter(db)
    except ImportError:
        st.error("❌ TenderDataImporter module not found. Please check your imports.")
        return
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_{tender_id}"
    )
    
    # Initialize session state for parsed data
    parsed_data_key = f"parsed_data_{tender_id}"
    if parsed_data_key not in st.session_state:
        st.session_state[parsed_data_key] = None
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, header=0)
            
            st.caption("Preview of parsed data:")
            st.dataframe(df.head(5), use_container_width=True)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report_with_header(df)
            
            if not parsed_data or not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            st.session_state[parsed_data_key] = parsed_data
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Preview table
            display_data = []
            for comp in parsed_data['competitors']:
                final_amount = comp.get('final_amount', 0)
                display_data.append({
                    'Competitor': comp.get('name', 'Unknown'),
                    'Quoted Amount': f"BDT {comp.get('quoted_amount', 0):,.2f}" if comp.get('quoted_amount') else "N/A",
                    'Final Amount': f"BDT {final_amount:,.2f}" if final_amount > 0 else "N/A",
                    'Winner': "🏆" if comp.get('is_winner') else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # Winner Selection
            st.markdown("---")
            st.markdown("#### 🏆 Winner Selection")
            st.caption("Select the winner. Choose 'Skip Winner' if no winner should be declared.")
            
            competitor_names = [comp.get('name', f'Competitor {i+1}') for i, comp in enumerate(parsed_data['competitors'])]
            
            current_winner = next((c for c in parsed_data['competitors'] if c.get('is_winner')), None)
            current_winner_name = current_winner.get('name') if current_winner else None
            
            skip_winner_label = "-- Skip Winner (No winner declared) --"
            options = [skip_winner_label] + competitor_names
            
            if current_winner_name and current_winner_name in competitor_names:
                default_index = competitor_names.index(current_winner_name) + 1
            else:
                default_index = 0
            
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_winner = st.selectbox(
                    "Select Winner",
                    options,
                    index=default_index,
                    key=f"winner_select_{tender_id}"
                )
            
            with col2:
                if st.button("✅ Apply Winner", key=f"apply_winner_{tender_id}", use_container_width=True):
                    if selected_winner == skip_winner_label:
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = False
                        parsed_data['winner_info'] = None
                        st.info("ℹ️ No winner selected. All competitors will have was_winner = 0.")
                    else:
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = (comp.get('name') == selected_winner)
                        winner_comp = next((c for c in parsed_data['competitors'] if c.get('is_winner')), None)
                        if winner_comp:
                            parsed_data['winner_info'] = {
                                'name': winner_comp.get('name'),
                                'final_amount': winner_comp.get('final_amount', 0)
                            }
                        st.success(f"✅ {selected_winner} marked as winner!")
                    
                    st.session_state[parsed_data_key] = parsed_data
                    st.rerun()
            
            # Import Button
            st.markdown("---")
            import_label = "🔄 Replace & Import" if replace_data and existing_data_count > 0 else "📥 Import Competitors & Bid Data"
            
            if st.button(import_label, type="primary", use_container_width=True, key=f"import_{tender_id}"):
                has_selected_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
                
                if not has_selected_winner:
                    for comp in parsed_data['competitors']:
                        comp['is_winner'] = False
                    parsed_data['winner_info'] = None
                    st.info("ℹ️ No winner will be marked. All competitors will have was_winner = 0.")
                
                with st.spinner("Importing data into database..."):
                    success, summary = importer.import_tender_data(
                        company_id=company_id,
                        tender_id=tender_id,
                        parsed_data=parsed_data,
                        tender_data=tender,
                        replace_existing=replace_data
                    )
                
                if success:
                    st.success("✅ Import completed successfully!")
                    st.balloons()
                    
                    if parsed_data_key in st.session_state:
                        del st.session_state[parsed_data_key]
                    
                    if st.button("🔄 Refresh to see imported data", use_container_width=True):
                        st.rerun()
                else:
                    st.error("❌ Import failed.")
                    if summary and summary.get('errors'):
                        for err in summary['errors']:
                            st.error(err)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)


def render_team_milestones_tab(tender: Dict[str, Any]):
    """Render the Team & Milestones tab"""
    st.markdown("### 👥 Team & Milestones")
    
    tender_db_id = tender.get('id')
    if not tender_db_id:
        st.warning("Tender ID not found for team management.")
        return
    
    # ========== MILESTONE PROGRESS ==========
    render_milestone_status_update(tender_db_id)
    
    st.markdown("---")
    
    # ========== TEAM MANAGEMENT ==========
    st.markdown("#### 👥 Team Assignment")
    
    # Get team - returns List[Dict]
    team = db.get_tender_team(tender_db_id)
    
    if team and len(team) > 0:
        st.markdown("**Current Team Members:**")
        for member in team:
            full_name = member.get('full_name', 'Unknown')
            assigned_role = member.get('assigned_role', 'N/A')
            user_role = member.get('role', 'user')
            st.markdown(f"- **{full_name}** • {assigned_role} • {user_role}")
    else:
        st.info("No team members assigned yet.")
    
    # Add new member
    st.markdown("**Add Team Member:**")
    # ✅ Use the bound UserCRUD method - returns List[Dict]
    users = db.get_all_users(company_id=st.session_state.company_id)
    
    if users:
        user_options = {}
        for user in users:
            # ✅ User is already a dict
            user_id = user.get('id')
            full_name = user.get('full_name', 'Unknown')
            username = user.get('username', '')
            user_options[f"{full_name} ({username})"] = user_id
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_member = st.selectbox(
                "Select Member", 
                ["Select"] + list(user_options.keys()), 
                key=f"team_member_select_{tender_db_id}"
            )
        with col2:
            role = st.selectbox(
                "Role", 
                ["Bid Manager", "Technical Lead", "Financial", "Legal", "Support", "QA/QC", "Procurement"], 
                key=f"team_role_select_{tender_db_id}"
            )
        with col3:
            if st.button("➕ Add Member", key=f"add_team_member_{tender_db_id}", use_container_width=True):
                if new_member != "Select" and new_member in user_options:
                    if db.assign_team_member(tender_db_id, user_options[new_member], role):
                        st.success(f"✅ {new_member} added as {role}!")
                        st.rerun()
                    else:
                        st.error("Failed to add team member.")
                else:
                    st.warning("Please select a valid member.")
    else:
        st.warning("No users found for this company. Please add users first.")
    
    st.markdown("---")
    
    # ========== MILESTONES ==========
    st.markdown("#### 🎯 Milestones & Tasks")
    
    # Get milestones - returns List[Dict]
    milestones_list = db.get_tender_milestones(tender_db_id)
    milestones_df = _ensure_dataframe(milestones_list)
    
    if not milestones_df.empty:
        st.markdown("**Current Milestones:**")
        for _, m in milestones_df.iterrows():
            icon = "✅" if m.get('completed') else "⏳"
            
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"{icon} **{m['milestone_name']}**")
                if m.get('notes'):
                    st.caption(f"📝 {m['notes'][:50]}")
            with col2:
                due_date = m.get('due_date', 'N/A')
                if due_date and due_date != 'N/A':
                    try:
                        due_dt = pd.to_datetime(due_date)
                        st.caption(f"📅 Due: {due_dt.strftime('%d %b %Y')}")
                    except:
                        st.caption(f"📅 Due: {due_date}")
                if m.get('assigned_to_name'):
                    st.caption(f"👤 Assigned to: {m['assigned_to_name']}")
            with col3:
                if not m.get('completed'):
                    if st.button("✅ Complete", key=f"complete_milestone_{m['id']}", use_container_width=True):
                        try:
                            if db.complete_milestone(m['id']):
                                st.success("✅ Milestone completed!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to complete milestone: {e}")
    else:
        st.info("No milestones created yet.")
    
    # Add new milestone
    with st.expander("➕ Add New Milestone"):
        col1, col2 = st.columns(2)
        with col1:
            milestone_name = st.text_input(
                "Milestone Name *", 
                key=f"milestone_name_{tender_db_id}"
            )
            due_date = st.date_input(
                "Due Date", 
                value=datetime.now() + timedelta(days=7), 
                key=f"milestone_due_{tender_db_id}"
            )
        with col2:
            # ✅ Use the bound UserCRUD method - returns List[Dict]
            users = db.get_all_users(company_id=st.session_state.company_id)
            if users:
                user_options = {}
                for user in users:
                    # ✅ User is already a dict
                    user_id = user.get('id')
                    full_name = user.get('full_name', 'Unknown')
                    username = user.get('username', '')
                    user_options[f"{full_name} ({username})"] = user_id
                
                assigned_to = st.selectbox(
                    "Assign To", 
                    ["Select"] + list(user_options.keys()), 
                    key=f"milestone_assign_{tender_db_id}"
                )
            else:
                assigned_to = "Select"
                user_options = {}
                st.warning("No users available for assignment")
            
            notes = st.text_area(
                "Notes", 
                placeholder="Optional notes about this milestone...",
                key=f"milestone_notes_{tender_db_id}"
            )
        
        if st.button("📌 Add Milestone", key=f"add_milestone_{tender_db_id}", type="primary", use_container_width=True):
            if not milestone_name:
                st.error("❌ Milestone name is required.")
            else:
                assigned_id = user_options.get(assigned_to) if assigned_to in user_options else None
                milestone_id = db.add_milestone(
                    tender_db_id, 
                    milestone_name, 
                    due_date.strftime('%Y-%m-%d'), 
                    assigned_id, 
                    notes
                )
                if milestone_id:
                    st.success(f"✅ Milestone '{milestone_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add milestone.")

def render_milestone_status_update(tender_db_id: int):
    """Render a quick milestone status update section"""
    
    # ✅ Get milestones - returns List[Dict]
    milestones_list = db.get_tender_milestones(tender_db_id)
    milestones_df = _ensure_dataframe(milestones_list)
    
    if milestones_df.empty:
        st.caption("No milestones created yet.")
        return
    
    st.markdown("#### 📊 Milestone Progress")
    
    total = len(milestones_df)
    completed = len(milestones_df[milestones_df['completed'] == 1])
    progress = (completed / total * 100) if total > 0 else 0
    
    st.progress(progress / 100, text=f"{progress:.0f}% Complete ({completed}/{total})")
    
    # Show upcoming milestones
    upcoming = milestones_df[milestones_df['completed'] != 1].sort_values('due_date').head(3)
    if not upcoming.empty:
        st.markdown("**Upcoming Milestones:**")
        for _, m in upcoming.iterrows():
            due_date = m.get('due_date', 'N/A')
            if due_date and due_date != 'N/A':
                try:
                    due_dt = pd.to_datetime(due_date)
                    days_left = (due_dt - pd.Timestamp.now()).days
                    st.caption(f"• {m['milestone_name']} - Due in {days_left} days")
                except:
                    st.caption(f"• {m['milestone_name']} - Due: {due_date}")
# =============================================================================
# COMPANY DASHBOARD WRAPPER
# =============================================================================

def render_tender_detail_page_with_back(tender_data: Dict[str, Any], back_to: str = "company_dashboard"):
    """Render tender detail page with custom back button"""
    
    # Store the tender in session state if not already
    if tender_data:
        # Set the selected tender ID (database ID)
        st.session_state.tender_selected_id = tender_data.get('id')
        st.session_state.tender_view = "detail"
        
        # Render the detail page
        render_tender_detail_page(tender_data.get('id'))
        
        # Add custom back button at the bottom
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            back_label = "Company Dashboard" if back_to == "company_dashboard" else "Tender List"
            if st.button(f"← Back to {back_label}", key=f"back_to_{back_to}_from_tender", use_container_width=True, type="primary"):
                # Clear tender detail state
                st.session_state.tender_view = "grid"
                st.session_state.tender_selected_id = None
                if back_to == "company_dashboard":
                    st.session_state.page = "company_dashboard"
                else:
                    st.session_state.page = "tender_management"
                st.rerun()


# Export functions
__all__ = [
    'render_tender_grid_view',
    'render_tender_detail_page',
    'render_tender_detail_page_with_back'
]