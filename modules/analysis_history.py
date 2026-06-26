"""
Analysis History Module - Enhanced with Row Buttons & Detailed Reports
With Role-Based Access Control
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import traceback
from database.unified_db_manager import UnifiedDatabaseManager
from modules.rbac import (
    rbac, can_view_tenders, can_export_data, can_run_analysis,
    render_role_badge, require_permission
)
from utils.helpers import (
    format_currency_bd,
    format_percentage,
    get_compact_css,
    get_bid_status_badge,
    get_risk_indicator,
    render_page_header
)

# Initialize database
db = UnifiedDatabaseManager()


def parse_competitor_bids(competitor_bids_data):
    """Parse competitor bids from various formats"""
    if not competitor_bids_data:
        return []
    
    if isinstance(competitor_bids_data, str):
        try:
            return json.loads(competitor_bids_data)
        except:
            return []
    
    if isinstance(competitor_bids_data, list):
        return competitor_bids_data
    
    return []


@require_permission('can_view_tenders')
def show_analysis_history():
    """Tender analysis history page with row buttons and detailed reports"""
    
    st.markdown(get_compact_css(), unsafe_allow_html=True)

    # Page Header with role badge
    render_page_header(
        "📜 Tender History", 
        "View detailed analysis reports"        
    )
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Get current user's company ID
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    permissions = rbac.get_current_user_permissions()
    
    can_export = permissions.get('can_export_data', False) or user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    can_run_new_analysis = permissions.get('can_run_analysis', False) or user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']
    
    if not company_id:
        st.error("⚠️ Company information not found. Please log in again.")
        return
    
    try:
        # Use the database manager to get analyses
        analyses_df = db.get_user_analyses(
            st.session_state.user_id,
            company_id,
            st.session_state.user_role,
            limit=200
        )
        
        # Show info for viewers
        if user_role == 'viewer':
            st.info("👁️ **Viewer Mode:** You have read-only access to analysis history.")
        
        if analyses_df.empty:
            st.info("📭 No analyses saved yet. Run your first analysis in **Three-Tier Bid Optimization**!")
            
            # Show direct query results for debugging (only for admins)
            if user_role in ['admin', 'system_admin']:
                with st.expander("🔍 Database Debug", expanded=False):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?", (company_id,))
                    count = cursor.fetchone()[0]
                    st.write(f"Direct query count for company_id={company_id}: {count}")
                    
                    if count > 0:
                        cursor.execute("SELECT id, tender_id, tender_title, analysis_date FROM tender_analyses WHERE company_id = ? LIMIT 5", (company_id,))
                        rows = cursor.fetchall()
                        for row in rows:
                            st.write(f"  - ID: {row[0]}, Tender: {row[1]}, Title: {row[2][:50]}, Date: {row[3]}")
                    conn.close()
            
            if can_run_new_analysis:
                if st.button("➕ Run New Analysis", use_container_width=True):
                    st.session_state.page = "new_analysis"
                    st.rerun()
            return
        
        # Convert DataFrame to list of dicts for easier manipulation
        analyses = analyses_df.to_dict('records')
        
        # =========================================================================
        # FILTERS SECTION
        # =========================================================================
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                search_term = st.text_input("Search", placeholder="ID or title", key="search_input")
            
            with col2:
                statuses = list(set([a.get('bid_status', 'draft') for a in analyses if a.get('bid_status')]))
                status_filter = st.selectbox("Status", ["All"] + statuses, key="status_filter")
            
            with col3:
                # Handle analysis_type - could be full string or just tier name
                def get_tier_name(analysis_type):
                    if not analysis_type:
                        return 'BASIC'
                    atype = str(analysis_type).upper()
                    if 'ENHANCED' in atype or 'ML' in atype:
                        return 'ENHANCED'
                    elif 'ADVANCED' in atype or 'PPR' in atype:
                        return 'ADVANCED'
                    else:
                        return 'BASIC'
                
                analysis_types = list(set([get_tier_name(a.get('analysis_type')) for a in analyses]))
                type_filter = st.selectbox("Analysis Type", ["All"] + analysis_types, key="type_filter")
            
            with col4:
                risk_levels = list(set([a.get('risk_level', 'Medium') for a in analyses if a.get('risk_level')]))
                risk_filter = st.selectbox("Risk Level", ["All"] + risk_levels, key="risk_filter")
        
        # Apply filters
        filtered_analyses = analyses.copy()
        
        if search_term:
            search_lower = search_term.lower()
            filtered_analyses = [
                a for a in filtered_analyses 
                if search_lower in str(a.get('tender_id', '')).lower() 
                or search_lower in str(a.get('tender_title', '')).lower()
            ]
        
        if status_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if a.get('bid_status') == status_filter]
        
        if type_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if get_tier_name(a.get('analysis_type')) == type_filter]
        
        if risk_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if a.get('risk_level') == risk_filter]
        
        st.markdown(f"📊 Showing **{len(filtered_analyses)}** of **{len(analyses)}** analyses")
        
        # =============================================================================
        # PAGINATION SETUP
        # =============================================================================
        if 'history_page_num' not in st.session_state:
            st.session_state.history_page_num = 1

        items_per_page = 10
        total_items = len(filtered_analyses)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        if st.session_state.history_page_num > total_pages:
            st.session_state.history_page_num = total_pages

        start_idx = (st.session_state.history_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        current_page_items = filtered_analyses[start_idx:end_idx]

        # Display pagination controls
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            
            with col1:
                if st.button("◀◀ First", use_container_width=True, disabled=(st.session_state.history_page_num == 1)):
                    st.session_state.history_page_num = 1
                    st.rerun()
            
            with col2:
                if st.button("◀ Previous", use_container_width=True, disabled=(st.session_state.history_page_num == 1)):
                    st.session_state.history_page_num -= 1
                    st.rerun()
            
            with col3:
                st.markdown(f"<div style='text-align: center;'>Page {st.session_state.history_page_num} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col4:
                if st.button("Next ▶", use_container_width=True, disabled=(st.session_state.history_page_num == total_pages)):
                    st.session_state.history_page_num += 1
                    st.rerun()
            
            with col5:
                if st.button("Last ▶▶", use_container_width=True, disabled=(st.session_state.history_page_num == total_pages)):
                    st.session_state.history_page_num = total_pages
                    st.rerun()
            
            st.markdown("---")

        st.markdown(f"<span style='font-size:0.8rem; color:#666;'>Showing {start_idx + 1}-{end_idx} of {total_items} analyses</span>", unsafe_allow_html=True)
        st.markdown("---")

        # =========================================================================
        # MAIN TABLE WITH BUTTONS
        # =========================================================================
        if not filtered_analyses:
            st.warning("No analyses match your filters")
            return
        
        if 'selected_analysis_id' not in st.session_state:
            st.session_state.selected_analysis_id = None
        
        header_cols = st.columns([2, 3.5, 2, 1, 1, 1, 0.8])
        headers = ["Tender ID", "Title", "Bid Amount", "Win %", "Risk", "Status", ""]
    
        for col, header in zip(header_cols, headers):
            with col:
                st.markdown(f"**{header}**")
    
        st.markdown("---")
        
        # Display table with buttons
        for idx, analysis in enumerate(current_page_items):
            with st.container():
                cols = st.columns([2, 3.5, 2, 1, 1, 1, 0.8])
                
                with cols[0]:
                    st.markdown(f"**{analysis.get('tender_id', 'N/A')[:20]}**")
                
                with cols[1]:
                    title = str(analysis.get('tender_title', 'Untitled'))[:50]
                    st.markdown(title)
                
                with cols[2]:
                    bid = analysis.get('recommended_bid', 0)
                    st.markdown(format_currency_bd(bid, 3))
                
                with cols[3]:
                    win_prob = analysis.get('success_probability', 0)
                    if win_prob:
                        win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                        st.markdown(f"{win_pct:.0f}%")
                    else:
                        st.markdown("N/A")
                
                with cols[4]:
                    risk = analysis.get('risk_level', 'Unknown')
                    risk_display = get_risk_indicator(risk)
                    st.markdown(risk_display)
                
                with cols[5]:
                    status = analysis.get('bid_status', 'draft')
                    badge = get_bid_status_badge(status)
                    st.markdown(f"{badge} {status.title()}")
                
                with cols[6]:
                    button_key = f"view_{analysis.get('id')}_{idx}"
                    if st.button("📄", key=button_key, help="View details", use_container_width=True):
                        if st.session_state.selected_analysis_id == analysis.get('id'):
                            st.session_state.selected_analysis_id = None
                        else:
                            st.session_state.selected_analysis_id = analysis.get('id')
                        st.rerun()
                
                st.markdown("---")
        
        # =========================================================================
        # DETAILED REPORT SECTION (Matches Tender Analysis Page)
        # =========================================================================
        if st.session_state.selected_analysis_id:
            selected = next((a for a in filtered_analyses if a.get('id') == st.session_state.selected_analysis_id), None)
            
            if selected:
                st.markdown("---")
                st.markdown("## 📋 Detailed Analysis Report")
                
                # Show report (same as before)
                official_est = selected.get('official_estimate', 1)
                recommended_bid = selected.get('recommended_bid', 0)
                slt_threshold = selected.get('slt_threshold')
                if slt_threshold is None:
                    slt_threshold = official_est * 0.80
                
                win_prob = selected.get('success_probability', 0.65)
                confidence = selected.get('confidence_score', 0.70)
                risk_level = selected.get('risk_level', 'MEDIUM')
                nppi_factor = selected.get('nppi_factor', 0.92)
                weighted_avg = selected.get('weighted_average', 0)
                
                risk_color = '🟢' if risk_level == 'LOW' else ('🟡' if risk_level == 'MEDIUM' else '🔴')
                
                comparison = {
                    'basic': {
                        'method': 'Basic - Simple Average',
                        'optimal_bid': round(recommended_bid * 0.95, 3),
                        'bid_ratio': round((recommended_bid * 0.95) / official_est, 4),
                        'win_probability': round(win_prob * 0.95, 4),
                        'confidence_score': 0.65,
                        'risk_level': 'MEDIUM',
                        'risk_color': '🟡',
                        'slt_threshold': slt_threshold
                    },
                    'advanced': {
                        'method': 'Advanced - PPR 2025',
                        'optimal_bid': round(recommended_bid, 3),
                        'bid_ratio': round(recommended_bid / official_est, 4),
                        'win_probability': round(win_prob, 4),
                        'confidence_score': round(confidence, 4),
                        'risk_level': risk_level,
                        'risk_color': risk_color,
                        'slt_threshold': slt_threshold,
                        'nppi_factor': nppi_factor,
                        'weighted_average': weighted_avg
                    },
                    'enhanced': {
                        'method': 'Enhanced - ML Analysis',
                        'optimal_bid': round(recommended_bid * 1.02, 3),
                        'bid_ratio': round((recommended_bid * 1.02) / official_est, 4),
                        'win_probability': round(min(0.95, win_prob * 1.1), 4),
                        'confidence_score': 0.70,
                        'risk_level': 'LOW',
                        'risk_color': '🟢',
                        'slt_threshold': slt_threshold
                    }
                }
                
                competitor_bids_data = selected.get('competitor_bids')
                parsed_competitor_bids = parse_competitor_bids(competitor_bids_data)
                
                analysis_record = {
                    'tender_id': selected.get('tender_id', 'N/A'),
                    'tender_title': selected.get('tender_title', 'N/A'),
                    'procuring_entity': selected.get('procuring_entity', 'N/A'),
                    'official_estimate': official_est,
                    'division': selected.get('division', 'N/A'),
                    'district': selected.get('district', 'N/A'),
                    'thana': selected.get('thana', 'N/A'),
                    'procurement_type': selected.get('construction_type', 'works'),
                    'competitor_bids': parsed_competitor_bids,
                    'risk_tolerance': selected.get('risk_strategy', 'moderate')
                }
                
                user_info = {
                    'full_name': st.session_state.get('full_name', 'N/A'),
                    'company_name': st.session_state.get('company_name', 'N/A')
                }
                
                from modules.report_generator import generate_unified_report
                
                generate_unified_report(
                    analysis_record=analysis_record,
                    comparison=comparison,
                    user_info=user_info,
                    format='html'
                )
                
                st.markdown("---")
                st.markdown("### 📄 Export Options")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("📑 Generate PDF Report", use_container_width=True, type="secondary", key="history_gen_pdf"):
                        with st.spinner("Generating PDF..."):
                            pdf_buffer = generate_unified_report(
                                analysis_record=analysis_record,
                                comparison=comparison,
                                user_info=user_info,
                                format='pdf'
                            )
                            if pdf_buffer and pdf_buffer.getbuffer().nbytes > 0:
                                safe_tid = str(selected.get('tender_id', 'report')).replace('/', '_')
                                filename = f"Babui_TenderAI_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                                st.session_state.history_pdf_buffer = pdf_buffer
                                st.session_state.history_pdf_filename = filename
                                st.success("✅ PDF generated! Scroll down to download.")
                                st.rerun()
                            else:
                                st.error("PDF generation failed")
                
                with col2:
                    export_rows = []
                    for tier, result in comparison.items():
                        comp_slt = result.get('slt_threshold', 0)
                        export_rows.append({
                            'Tier': tier.upper(),
                            'Method': result.get('method', ''),
                            'Optimal_Bid_BDT': result.get('optimal_bid', 0),
                            'Win_Probability_%': round(result.get('win_probability', 0) * 100, 1),
                            'Confidence_%': round(result.get('confidence_score', 0.7) * 100, 1),
                            'PPR_Compliant': 'Yes' if result.get('optimal_bid', 0) >= comp_slt else 'No'
                        })
                    csv = pd.DataFrame(export_rows).to_csv(index=False)
                    st.download_button(
                        "📥 Export CSV",
                        data=csv,
                        file_name=f"analysis_{selected.get('tender_id', 'export')}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col3:
                    export_data = {k: v for k, v in selected.items() if v is not None}
                    if 'competitor_bids' in export_data:
                        try:
                            if isinstance(export_data['competitor_bids'], str):
                                export_data['competitor_bids'] = json.loads(export_data['competitor_bids'])
                        except:
                            export_data['competitor_bids'] = []
                    export_json = json.dumps(export_data, default=str, indent=2)
                    st.download_button(
                        "💾 Export JSON",
                        export_json,
                        f"analysis_{selected.get('tender_id', 'export')}.json",
                        "application/json",
                        use_container_width=True
                    )
                
                with col4:
                    if st.button("❌ Close Report", use_container_width=True):
                        st.session_state.selected_analysis_id = None
                        st.rerun()
                
                # PDF Download Button
                if st.session_state.get('history_pdf_buffer') and st.session_state.get('history_pdf_filename'):
                    st.markdown("---")
                    st.info(f"📄 **PDF Report Ready:** `{st.session_state.history_pdf_filename}`")
                    col_d1, col_d2, col_d3 = st.columns([3, 1, 1])
                    with col_d2:
                        st.download_button(
                            "💾 Download PDF",
                            data=st.session_state.history_pdf_buffer,
                            file_name=st.session_state.history_pdf_filename,
                            mime="application/pdf",
                            use_container_width=True,
                            key="history_download_pdf"
                        )
                    with col_d3:
                        if st.button("🗑️ Clear", key="history_clear_pdf", use_container_width=True):
                            st.session_state.pop('history_pdf_buffer', None)
                            st.session_state.pop('history_pdf_filename', None)
                            st.rerun()
                    
    except Exception as e:
        st.error(f"Error loading analysis history: {str(e)}")
        print(f"ERROR: {e}")
        traceback.print_exc()


# Alternative entry point without decorator (for direct calls)
def show_analysis_history_page():
    """Wrapper function for analysis history page"""
    show_analysis_history()