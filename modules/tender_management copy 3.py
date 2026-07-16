"""
Complete Tender Management Module
Track tender participation, bid submission, deadlines, and winner tracking

Refactored for:
- e-GP style dashboard with table view
- Tender-specific detail pages
- Proper session state management
- Clean separation of concerns
- Uses CRUD manager for all database operations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import numpy as np
import logging
from typing import Optional, Dict, List, Any, Tuple
from database.unified_db_manager import get_db_manager
import traceback

# Get cached database manager instance
db = get_db_manager()

DEBUG_MODE = True
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, render_protected_button, can_import_tender_data
)

from modules.bid_analysis.bid_core import (
    CostEngine, NPPIEngine, SLTEngine, CompetitorEngine,
    WinProbabilityEngine, OptimumBidEngine, get_config, get_nested_config
)
from modules.tender_data_importer import TenderDataImporter


def debug_print(msg, data=None):
    """Debug print with timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] 🔍 {msg}")
    if data is not None:
        print(f"   └─ {data}")


# =============================================================================
# 🔄 SHARED TENDER SELECTOR INSTANCE
# =============================================================================

class TenderSelectorManager:
    """Singleton manager for tender selector state to ensure one copy across all tabs."""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TenderSelectorManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not TenderSelectorManager._initialized:
            self._selector_state = {
                'selected_tender_id': None,
                'selected_tender_data': None,
                'last_search_term': '',
                'last_context': None
            }
            TenderSelectorManager._initialized = True
    
    def get_selector_state(self, context: str = 'default') -> Dict[str, Any]:
        return {
            'selected_tender_id': self._selector_state.get('selected_tender_id'),
            'selected_tender_data': self._selector_state.get('selected_tender_data'),
            'last_search_term': self._selector_state.get('last_search_term'),
            'context': context
        }
    
    def update_selection(self, tender_id: Optional[str], tender_data: Optional[Dict] = None, search_term: str = ''):
        if tender_data is not None and hasattr(tender_data, 'to_dict'):
            tender_data = tender_data.to_dict()
        self._selector_state['selected_tender_id'] = str(tender_id) if tender_id else None
        self._selector_state['selected_tender_data'] = tender_data
        self._selector_state['last_search_term'] = search_term
    
    def clear_selection(self):
        self._selector_state['selected_tender_id'] = None
        self._selector_state['selected_tender_data'] = None
        self._selector_state['last_search_term'] = ''
    
    def get_selected_tender(self) -> Optional[Dict]:
        return self._selector_state.get('selected_tender_data')
    
    def get_selected_tender_id(self) -> Optional[str]:
        return self._selector_state.get('selected_tender_id')


tender_selector_manager = TenderSelectorManager()


def _normalize_tender_data(tender_data):
    """Convert pandas Series to dict if needed"""
    if tender_data is None:
        return None
    if hasattr(tender_data, 'to_dict'):
        return tender_data.to_dict()
    if isinstance(tender_data, dict):
        return tender_data
    return None


def render_shared_tender_selector(
    db_instance,
    company_id: int,
    search_term: str = "",
    include_manual_entry: bool = True,
    title: str = "🔍 Select Tender",
    show_table: bool = True,
    show_summary: bool = True,
    context: str = "default"
) -> Tuple[Optional[str], Optional[str], float, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Render a shared tender selector that maintains state across tabs."""
    from modules.tender_selector import render_tender_selector
    
    cached_state = tender_selector_manager.get_selector_state(context)
    
    if cached_state.get('selected_tender_id') and cached_state.get('context') == context:
        tender_data = db.get_tender_by_id(cached_state['selected_tender_id'], company_id)
        if tender_data:
            result = render_tender_selector(
                db=db_instance,
                company_id=company_id,
                search_term=search_term or cached_state.get('last_search_term', ''),
                include_manual_entry=include_manual_entry,
                title=title,
                show_table=show_table,
                show_summary=show_summary
            )
            new_tender_id = result[0] if result else None
            if new_tender_id and str(new_tender_id) != str(cached_state['selected_tender_id']):
                new_tender_data = db.get_tender_by_id(new_tender_id, company_id)
                tender_selector_manager.update_selection(new_tender_id, new_tender_data, search_term)
            return result
    
    result = render_tender_selector(
        db=db_instance,
        company_id=company_id,
        search_term=search_term,
        include_manual_entry=include_manual_entry,
        title=title,
        show_table=show_table,
        show_summary=show_summary
    )
    
    if result and result[0]:
        tender_id = result[0]
        tender_data = db.get_tender_by_id(tender_id, company_id)
        tender_selector_manager.update_selection(tender_id, tender_data, search_term)
    
    return result


# =============================================================================
# 🗄️ DATABASE METHODS - DELEGATE TO CRUD MANAGER
# =============================================================================

def create_tender(company_id: int, tender_data: Dict[str, Any], created_by: int) -> Optional[int]:
    """Create a new tender - delegates to CRUD"""
    try:
        # Check if tender already exists
        existing = db.get_tender_by_id(tender_data.get('tender_id', ''), company_id)
        if existing:
            logger.warning(f"Tender {tender_data.get('tender_id')} already exists")
            return None
        
        result = db.create_tender(company_id, tender_data, created_by)
        if result:
            tender_selector_manager.clear_selection()
        return result
    except Exception as e:
        logger.error(f"Failed to create tender: {e}", exc_info=True)
        return None


def update_tender(tender_id: int, tender_data: Dict[str, Any], updated_by: int) -> bool:
    """Update a tender - delegates to CRUD"""
    try:
        # Get company_id from session state
        company_id = st.session_state.get('company_id')
        if not company_id:
            logger.error("No company_id in session state")
            return False
        
        # Add company_id to tender_data for verification
        tender_data['company_id'] = company_id
        
        result = db.update_tender(tender_id, tender_data, updated_by)
        if result:
            logger.info(f"Tender {tender_id} updated by user {updated_by}")
            tender_selector_manager.clear_selection()
        return result
    except Exception as e:
        logger.error(f"Failed to update tender: {e}", exc_info=True)
        return False


def get_company_tenders(company_id: int, status_filter: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
    """Fetch company tenders with submitter name - delegates to CRUD"""
    try:
        results = db.get_company_tenders(company_id, status_filter, limit)
        return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to fetch company tenders: {e}", exc_info=True)
        return pd.DataFrame()


def get_tender_by_id(tender_id: str, company_id: int) -> Optional[Dict]:
    """Get tender by ID - delegates to CRUD"""
    try:
        return db.get_tender_by_id(tender_id, company_id)
    except Exception as e:
        logger.error(f"Error getting tender by ID: {e}")
        return None


def get_tender_by_db_id(tender_db_id: int, company_id: int) -> Optional[Dict]:
    """Get tender by database ID - delegates to CRUD"""
    try:
        return db.get_tender_by_db_id(tender_db_id, company_id)
    except Exception as e:
        logger.error(f"Error getting tender by DB ID: {e}")
        return None


def update_tender_bid(tender_id: int, bid_amount: float, updated_by: int) -> bool:
    """Update tender bid with revision tracking - delegates to CRUD"""
    try:
        return db.update_tender_bid(tender_id, bid_amount, updated_by)
    except Exception as e:
        logger.error(f"Failed to update tender bid: {e}", exc_info=True)
        return False


def submit_bid(tender_id: int, final_bid_amount: float, submitted_by: int) -> bool:
    """Submit a bid - delegates to CRUD"""
    try:
        return db.submit_bid(tender_id, final_bid_amount, submitted_by)
    except Exception as e:
        logger.error(f"Failed to submit bid: {e}", exc_info=True)
        return False


def update_tender_result(tender_id: int, winning_bid_amount: float, winning_competitor: str, 
                        our_rank: int, total_bidders: int, award_date: str, bid_status: str) -> bool:
    """Update tender results - delegates to CRUD"""
    try:
        result = db.update_tender_result(tender_id, winning_bid_amount, winning_competitor,
                                        our_rank, total_bidders, award_date, bid_status)
        if result:
            tender_selector_manager.clear_selection()
        return result
    except Exception as e:
        logger.error(f"Failed to update tender result: {e}", exc_info=True)
        return False


def update_competitor_bid(tender_id: str, competitor_name: str, 
                         bid_amount: float, was_winner: bool = False) -> bool:
    """Update competitor bid - delegates to CRUD"""
    try:
        return db.update_competitor_bid(tender_id, competitor_name, bid_amount, was_winner)
    except Exception as e:
        logger.error(f"Error in update_competitor_bid: {e}", exc_info=True)
        return False


def clear_tender_winner(tender_id: str) -> bool:
    """Clear winner from tender - delegates to CRUD"""
    try:
        return db.clear_tender_winner(tender_id)
    except Exception as e:
        logger.error(f"Error clearing winner for {tender_id}: {e}", exc_info=True)
        return False


def delete_tender(tender_id: int, deleted_by: int) -> bool:
    """Delete a tender - delegates to CRUD"""
    try:
        result = db.delete_tender(tender_id, deleted_by)
        if result:
            tender_selector_manager.clear_selection()
        return result
    except Exception as e:
        logger.error(f"Failed to delete tender: {e}", exc_info=True)
        return False


def get_tender_team(tender_id: int) -> List[tuple]:
    """Get team members assigned to a tender - delegates to CRUD"""
    try:
        results = db.get_tender_team(tender_id)
        # Convert dict results to tuple format for compatibility
        return [(r['id'], r['full_name'], r['role'], r['assigned_role'], r['assigned_at']) for r in results]
    except Exception as e:
        logger.error(f"Failed to fetch tender team: {e}", exc_info=True)
        return []


def assign_team_member(tender_id: int, user_id: int, role: str) -> bool:
    """Assign a team member to a tender - delegates to CRUD"""
    try:
        return db.assign_team_member(tender_id, user_id, role)
    except Exception as e:
        logger.error(f"Failed to assign team member: {e}", exc_info=True)
        return False


def get_all_users(company_id: int) -> List[tuple]:
    """Get all users for a company - delegates to CRUD"""
    try:
        results = db.get_all_users(company_id)
        # Convert dict results to tuple format for compatibility
        return [(r['id'], r['username'], r['full_name'], r['email'], r['role'], r['is_active']) for r in results]
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}", exc_info=True)
        return []


def add_milestone(tender_id: int, milestone_name: str, due_date: str, 
                 assigned_to: Optional[int], notes: str) -> Optional[int]:
    """Add a milestone - delegates to CRUD"""
    try:
        return db.add_milestone(tender_id, milestone_name, due_date, assigned_to, notes)
    except Exception as e:
        logger.error(f"Failed to add milestone: {e}", exc_info=True)
        return None


def get_tender_milestones(tender_id: int) -> pd.DataFrame:
    """Get milestones for a tender - delegates to CRUD"""
    try:
        results = db.get_tender_milestones(tender_id)
        return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to fetch milestones: {e}", exc_info=True)
        return pd.DataFrame()


def add_bid_revision(tender_id: int, bid_amount: float, revised_by: int, reason: str) -> bool:
    """Add bid revision history - delegates to CRUD"""
    try:
        return db.add_bid_revision(tender_id, bid_amount, revised_by, reason)
    except Exception as e:
        logger.error(f"Failed to add bid revision: {e}", exc_info=True)
        return False


def get_bid_revisions(tender_id: int) -> List[tuple]:
    """Get bid revision history - delegates to CRUD"""
    try:
        results = db.get_bid_revisions(tender_id)
        # Convert dict results to tuple format for compatibility
        return [(r['revision_number'], r['bid_amount'], r['revised_by'], r['reason'], r['revised_at']) for r in results]
    except Exception as e:
        logger.error(f"Failed to fetch bid revisions: {e}", exc_info=True)
        return []


def update_tender_lock_status(tender_id: int, locked: bool, locked_by: Optional[int] = None) -> bool:
    """Update lock status - delegates to CRUD"""
    try:
        return db.update_tender_lock_status(tender_id, locked, locked_by)
    except Exception as e:
        logger.error(f"Failed to update tender lock status: {e}", exc_info=True)
        return False


def create_tender_copy(original_tender_id: int, created_by: int) -> Optional[int]:
    """Create a backup copy of a tender - delegates to CRUD"""
    try:
        return db.create_tender_copy(original_tender_id, created_by)
    except Exception as e:
        logger.error(f"Failed to create tender copy: {e}", exc_info=True)
        return None


def get_competitor_bids(tender_id: str, company_id: int) -> pd.DataFrame:
    """Get competitor bids for a tender - delegates to CRUD"""
    try:
        results = db.get_competitor_bids(tender_id, company_id)
        return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to fetch competitor bids: {e}", exc_info=True)
        return pd.DataFrame()


def get_competitor_master_list(company_id: int, active_only: bool = True) -> List[Dict]:
    """Get competitor master list - delegates to CRUD"""
    try:
        return db.get_competitor_master_list(company_id, active_only)
    except Exception as e:
        logger.error(f"Failed to fetch competitor list: {e}", exc_info=True)
        return []


def get_tender_summary_stats(company_id: int) -> Dict[str, Any]:
    """Get tender summary statistics - delegates to CRUD"""
    try:
        return db.get_tender_summary_stats(company_id) or {}
    except Exception as e:
        logger.error(f"Failed to get tender stats: {e}", exc_info=True)
        return {}


# =============================================================================
# 🎨 E-GP STYLE DASHBOARD
# =============================================================================

def render_tender_dashboard() -> None:
    """Main dashboard with e-GP style table and navigation"""
    
    debug_print("render_tender_dashboard() called")
    
    if 'view_tender_detail' not in st.session_state:
        st.session_state.view_tender_detail = None
    if 'tender_search_filters' not in st.session_state:
        st.session_state.tender_search_filters = {
            'procurement_nature': 'All',
            'procurement_type': 'All',
            'procurement_method': 'All',
            'tender_id': '',
            'reference_no': '',
            'publishing_date_from': None,
            'publishing_date_to': None
        }
    
    debug_print(f"view_tender_detail: {st.session_state.view_tender_detail is not None}")
    
    # Check if we're viewing a specific tender
    if st.session_state.view_tender_detail:
        debug_print("Rendering tender detail page...")
        _render_tender_detail_page(st.session_state.view_tender_detail)
        return
    
    # Main dashboard
    debug_print("Rendering main dashboard...")
    _render_dashboard_header()
    _render_search_filters()
    _render_tenders_table()


def _render_dashboard_header():
    """Render dashboard header with e-GP style"""
    st.markdown("""
    <style>
    .dashboard-header {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .dashboard-header h1 {
        color: white;
        margin: 0;
        font-size: 24px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .dashboard-header .subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    .dashboard-header .badge-container {
        display: flex;
        gap: 15px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    .dashboard-header .badge {
        background: rgba(255,255,255,0.1);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 13px;
        color: #e0e0e0;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .dashboard-header .badge strong {
        color: white;
    }
    </style>
    <div class="dashboard-header">
        <h1>📋 My Tenders/Proposals</h1>
        <div class="subtitle">Manage and track all your tender submissions</div>
        <div class="badge-container">
            <span class="badge">📊 Total: <strong id="total-tenders">0</strong></span>
            <span class="badge">🟢 Active: <strong id="active-tenders">0</strong></span>
            <span class="badge">🏆 Won: <strong id="won-tenders">0</strong></span>
            <span class="badge">📈 Win Rate: <strong id="win-rate">0%</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Update stats using CRUD
    company_id = st.session_state.get('company_id')
    if company_id:
        stats = get_tender_summary_stats(company_id)
        total = stats.get('total_tenders', 0)
        won = stats.get('won_count', 0)
        win_rate = f"{(won/total*100):.0f}%" if total > 0 else "0%"
        
        st.markdown(f"""
        <script>
        document.getElementById('total-tenders').textContent = '{total}';
        document.getElementById('active-tenders').textContent = '{stats.get('submitted_count', 0)}';
        document.getElementById('won-tenders').textContent = '{won}';
        document.getElementById('win-rate').textContent = '{win_rate}';
        </script>
        """, unsafe_allow_html=True)


def _render_search_filters():
    """Render e-GP style search filters"""
    st.markdown("""
    <style>
    .filters-container {
        background: #1a1a2e;
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    .filters-container .filter-label {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="filters-container">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown('<span class="filter-label">Procurement Nature</span>', unsafe_allow_html=True)
            nature = st.selectbox(
                "Procurement Nature",
                ["All", "Works", "Goods", "Services"],
                key="filter_nature",
                label_visibility="collapsed"
            )
            
            st.markdown('<span class="filter-label">Procurement Type</span>', unsafe_allow_html=True)
            ptype = st.selectbox(
                "Procurement Type",
                ["All", "NCT", "LTM", "RFQ"],
                key="filter_type",
                label_visibility="collapsed"
            )
            
            st.markdown('<span class="filter-label">Procurement Method</span>', unsafe_allow_html=True)
            method = st.selectbox(
                "Procurement Method",
                ["All", "Open", "Limited", "Direct"],
                key="filter_method",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown('<span class="filter-label">Tender/Proposal ID</span>', unsafe_allow_html=True)
            tender_id = st.text_input("Tender ID", placeholder="Enter ID...", key="filter_tender_id", label_visibility="collapsed")
            
            st.markdown('<span class="filter-label">Reference No</span>', unsafe_allow_html=True)
            ref_no = st.text_input("Reference No", placeholder="Enter reference...", key="filter_ref_no", label_visibility="collapsed")
        
        with col3:
            st.markdown('<span class="filter-label">Publishing Date From</span>', unsafe_allow_html=True)
            date_from = st.date_input("From", value=None, key="filter_date_from", label_visibility="collapsed")
            
            st.markdown('<span class="filter-label">Publishing Date To</span>', unsafe_allow_html=True)
            date_to = st.date_input("To", value=None, key="filter_date_to", label_visibility="collapsed")
        
        # Store filters in session state
        st.session_state.tender_search_filters = {
            'procurement_nature': nature,
            'procurement_type': ptype,
            'procurement_method': method,
            'tender_id': tender_id,
            'reference_no': ref_no,
            'publishing_date_from': date_from,
            'publishing_date_to': date_to
        }
        
        st.markdown('</div>', unsafe_allow_html=True)


def _render_tender_detail_page(tender_data: Dict[str, Any]):
    """Render e-GP style tender detail page with all tabs"""
    
    _render_detail_header(tender_data)
    
    tender_db_id = tender_data.get('id')
    tender_id = tender_data.get('tender_id', 'N/A')
    
    # Back button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Dashboard", key=f"back_to_dashboard_{tender_db_id}", use_container_width=True):
            st.session_state.view_tender_detail = None
            st.session_state.page = "tender_management"
            st.rerun()

    # ===== TENDER/PROPOSAL DASHBOARD =====
    st.markdown("---")
    st.markdown("### TENDER/PROPOSAL DASHBOARD")
    
    # ✅ Get ALL safe values (11 values now)
    (official_estimate, our_bid, total_bidders, our_rank,
     procurement_type, bid_status, evaluation_status,
     tender_title, procuring_entity, division, district) = _get_safe_tender_values(tender_data)
    
    # Summary cards
    _render_summary_cards(official_estimate, our_bid, total_bidders, our_rank)
    
    # ===== ALL TABS =====
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Tender Information", 
        "🏆 Winner Information", 
        "📊 Bid Analysis",
        "📊 Analysis Report",
        "🏆 Tender Results CRUD",
        "📥 Import Tender Data",
        "👥 Team & Milestones"
    ])
    
    with tab1:
        _render_information_tab(tender_data, official_estimate, our_bid, tender_db_id, tender_id)
    
    with tab2:
        _render_winner_tab(tender_data, official_estimate, tender_id)
    
    with tab3:
        _render_bid_analysis_tab(tender_data, official_estimate, our_bid, tender_id)
    
    with tab4:
        _render_tender_analysis_for_tender(tender_data, tender_id, official_estimate)
    
    with tab5:
        _render_tender_result_crud_for_tender(tender_data, tender_id, official_estimate)
    
    with tab6:
        _render_tender_importer_for_tender(tender_data, tender_id, official_estimate)
    
    with tab7:
        _render_team_and_milestones_for_tender(tender_data, tender_id)



# =============================================================================
# HELPER FUNCTIONS FOR _render_tender_detail_page
# =============================================================================

def _render_detail_header(tender_data: Dict[str, Any]):
    """Render the detail page header"""
    debug_print("_render_detail_header")
    tender_id = tender_data.get('tender_id', 'N/A')
    title = tender_data.get('tender_title', 'Untitled')
    procuring_entity = tender_data.get('procuring_entity', 'N/A')
    closing_date = tender_data.get('submission_deadline', 'N/A')
    status = tender_data.get('bid_status', 'draft')
    
    status_display = {
        'won': 'Contract Awarded',
        'submitted': 'Being processed',
        'draft': 'Draft',
        'lost': 'Lost',
        'awarded': 'Contract Awarded'
    }.get(status, status.title())
    
    # Format closing date
    if closing_date and closing_date != 'N/A':
        try:
            closing_date = pd.to_datetime(closing_date).strftime('%d-%b-%Y %H:%M')
        except:
            pass
    
    st.markdown(f"""
    <div class="detail-header">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
            <div>
                <h1>📄 Tender/Proposal Detail</h1>
                <div class="subtitle">{title}</div>
            </div>
            <div>
                <span class="status-badge status-{status}">{status_display}</span>
            </div>
        </div>
        <div class="meta-row">
            <span class="meta-item"><strong>Tender/Proposal ID:</strong> {tender_id}</span>
            <span class="meta-item"><strong>Closing Date:</strong> {closing_date}</span>
            <span class="meta-item"><strong>Procuring Entity:</strong> {procuring_entity[:60]}</span>
            <span class="meta-item"><strong>Status:</strong> {status_display}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _get_safe_tender_values(tender_data: Dict[str, Any]) -> tuple:
    """Extract and normalize tender values safely"""
    debug_print("_get_safe_tender_values")
    
    # ✅ Safely get official_estimate
    official_estimate = tender_data.get('official_estimate')
    if official_estimate is None:
        official_estimate = 0
    try:
        official_estimate = float(official_estimate)
    except (ValueError, TypeError):
        official_estimate = 0
    
    # ✅ Safely get our_bid_amount
    our_bid = tender_data.get('our_bid_amount')
    if our_bid is None:
        our_bid = 0
    try:
        our_bid = float(our_bid)
    except (ValueError, TypeError):
        our_bid = 0
    
    # ✅ Safely get total_bidders
    total_bidders = tender_data.get('total_bidders')
    if total_bidders is None:
        total_bidders = 'N/A'
    else:
        try:
            total_bidders = str(total_bidders)
        except:
            total_bidders = 'N/A'
    
    # ✅ Safely get our_rank
    our_rank = tender_data.get('our_rank')
    if our_rank is None:
        our_rank = 'N/A'
    else:
        try:
            our_rank = str(our_rank)
        except:
            our_rank = 'N/A'
    
    # ✅ SAFELY get procurement_type (this fixes the error)
    procurement_type = tender_data.get('procurement_type')
    if procurement_type is None or procurement_type == '':
        procurement_type = 'N/A'
    else:
        procurement_type = str(procurement_type).upper()
    
    # ✅ Safely get other commonly used fields
    bid_status = tender_data.get('bid_status')
    if bid_status is None or bid_status == '':
        bid_status = 'draft'
    
    evaluation_status = tender_data.get('evaluation_status')
    if evaluation_status is None or evaluation_status == '':
        evaluation_status = 'pending'
    
    tender_title = tender_data.get('tender_title')
    if tender_title is None or tender_title == '':
        tender_title = 'Untitled'
    
    procuring_entity = tender_data.get('procuring_entity')
    if procuring_entity is None or procuring_entity == '':
        procuring_entity = 'N/A'
    
    division = tender_data.get('division')
    if division is None or division == '':
        division = 'N/A'
    
    district = tender_data.get('district')
    if district is None or district == '':
        district = 'N/A'
    
    return (
        official_estimate,
        our_bid,
        total_bidders,
        our_rank,
        procurement_type,        # ✅ Added
        bid_status,              # ✅ Added
        evaluation_status,       # ✅ Added
        tender_title,            # ✅ Added
        procuring_entity,        # ✅ Added
        division,                # ✅ Added
        district                 # ✅ Added
    )

def _render_summary_cards(official_estimate: float, our_bid: float, total_bidders, our_rank):
    """Render summary cards for tender detail view"""
    debug_print("_render_summary_cards")
    
    # ✅ Ensure values are safe
    if official_estimate is None:
        official_estimate = 0
    if our_bid is None:
        our_bid = 0
    
    if total_bidders is None or total_bidders == 'N/A':
        total_bidders_display = 'N/A'
        total_bidders_int = 0
    else:
        try:
            total_bidders_int = int(total_bidders)
            total_bidders_display = str(total_bidders_int)
        except (ValueError, TypeError):
            total_bidders_display = 'N/A'
            total_bidders_int = 0
    
    if our_rank is None or our_rank == 'N/A':
        our_rank_display = 'N/A'
    else:
        try:
            our_rank_display = str(int(our_rank))
        except (ValueError, TypeError):
            our_rank_display = 'N/A'
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Official Estimate", f"BDT {official_estimate:,.2f}")
    with col2:
        st.metric("Our Bid", f"BDT {our_bid:,.2f}" if our_bid > 0 else "Not Set")
    with col3:
        st.metric("Total Bidders", total_bidders_display)
    with col4:
        st.metric("Our Rank", our_rank_display)


def _render_information_tab(tender_data: Dict[str, Any], official_estimate: float, our_bid: float, tender_db_id: int, tender_id: str):
    """Render the Tender Information tab"""
    debug_print("_render_information_tab")
    
    # ✅ Get all safe values (re-use the ones passed in, or call again)
    (official_estimate, our_bid, total_bidders, our_rank,
     procurement_type, bid_status, evaluation_status,
     tender_title, procuring_entity, division, district) = _get_safe_tender_values(tender_data)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basic Information")
        st.info(f"**Tender ID:** `{tender_data.get('tender_id', 'N/A')}`")
        st.markdown(f"**Title:** {tender_title}")
        st.markdown(f"**Procuring Entity:** {procuring_entity}")
        st.markdown(f"**Division:** {division}")
        st.markdown(f"**District:** {district}")
        st.markdown(f"**Procurement Type:** {procurement_type}")
        st.markdown(f"**Bid Status:** {bid_status.upper()}")
        st.markdown(f"**Evaluation Status:** {evaluation_status.upper()}")
        
    with col2:
        st.markdown("#### Financial Information")
        st.info(f"**Official Estimate:** BDT {official_estimate:,.2f}")
        
        # ✅ SAFELY get tender_security
        tender_security = tender_data.get('tender_security')
        if tender_security is None:
            tender_security = 0
        try:
            tender_security = float(tender_security)
        except (ValueError, TypeError):
            tender_security = 0
        st.markdown(f"**Tender Security:** BDT {tender_security:,.2f}")
        
        # ✅ SAFELY get document_fee
        document_fee = tender_data.get('document_fee')
        if document_fee is None:
            document_fee = 0
        try:
            document_fee = float(document_fee)
        except (ValueError, TypeError):
            document_fee = 0
        st.markdown(f"**Document Fee:** BDT {document_fee:,.2f}")
        
        if our_bid > 0:
            st.markdown(f"**Our Bid:** BDT {our_bid:,.2f}")
        else:
            st.markdown("**Our Bid:** Not set")
        
        if total_bidders != 'N/A':
            st.markdown(f"**Total Bidders:** {total_bidders}")
        if our_rank != 'N/A':
            st.markdown(f"**Our Rank:** {our_rank}")

    
    st.markdown("#### Important Dates")
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline = tender_data.get('submission_deadline')
        if deadline:
            try:
                deadline_dt = pd.to_datetime(deadline)
                st.markdown(f"**Submission Deadline:** {deadline_dt.strftime('%d %b %Y %H:%M')}")
            except:
                st.markdown(f"**Submission Deadline:** {deadline}")
        else:
            st.markdown("**Submission Deadline:** N/A")
    
    with col2:
        pub_date = tender_data.get('tender_publication_date')
        if pub_date:
            try:
                pub_dt = pd.to_datetime(pub_date)
                st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
            except:
                st.markdown(f"**Published:** {pub_date}")
        else:
            st.markdown("**Published:** N/A")
    
    with col3:
        opening_date = tender_data.get('bid_opening_date')
        if opening_date:
            try:
                opening_dt = pd.to_datetime(opening_date)
                st.markdown(f"**Opening Date:** {opening_dt.strftime('%d %b %Y %H:%M')}")
            except:
                st.markdown(f"**Opening Date:** {opening_date}")
        else:
            st.markdown("**Opening Date:** N/A")
    
    # Team summary
    _add_team_summary_to_information_tab(tender_data)

    # ===== EDIT SECTION =====
    st.markdown("---")
    st.markdown("#### ✏️ Edit Tender")

    from modules.rbac import can_edit_tender
    if can_edit_tender():
        if st.button("✏️ Edit This Tender", key=f"edit_tender_{tender_db_id}", use_container_width=True, type="primary"):
            success = _load_tender_for_edit(tender_db_id)
            if success:
                st.session_state.view_tender_detail = None
                st.session_state.page = "tender_form"
                st.rerun()

def _render_bid_analysis_tab(tender_data: Dict[str, Any], official_estimate: float, our_bid: float, tender_id: str):
    """Render the Bid Analysis tab (quick stats)"""
    debug_print("_render_bid_analysis_tab")
    st.markdown("#### Bid Analysis")
    st.info("Comprehensive analysis available in the 'Analysis Report' tab above.")
    
    # ✅ Safe check for official_estimate and our_bid
    if official_estimate is None:
        official_estimate = 0
    if our_bid is None:
        our_bid = 0
    
    if official_estimate > 0 and our_bid > 0:
        nppi = (our_bid / official_estimate) * 100
        st.metric("Our NPPI", f"{nppi:.2f}%", help="Our bid as percentage of OCE")
        
        if nppi < 85:
            st.warning("⚠️ Your bid is significantly below OCE. This may trigger SLT scrutiny.")
        elif nppi > 105:
            st.warning("⚠️ Your bid is above OCE. Consider reviewing your pricing.")
        else:
            st.success("✅ Your bid is within a reasonable range.")
        
        # Bid comparison using CRUD
        st.markdown("#### Bid Comparison")
        try:
            company_id = st.session_state.get('company_id')
            if company_id:
                bids_df = get_competitor_bids(tender_id, company_id)
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
        except Exception as e:
            st.warning(f"Could not load bid comparison: {e}")
    elif official_estimate > 0 and our_bid == 0:
        st.info("💡 Set your bid amount to see NPPI analysis.")
    else:
        st.warning("⚠️ Official Estimate not set. Please update tender with OCE.")

def _render_bid_analysis_tab(tender_data: Dict[str, Any], official_estimate: float, our_bid: float, tender_id: str):
    """Render the Bid Analysis tab (quick stats)"""
    debug_print("_render_bid_analysis_tab")
    st.markdown("#### Bid Analysis")
    st.info("Comprehensive analysis available in the 'Analysis Report' tab above.")
    
    # ✅ Safe check for official_estimate and our_bid
    if official_estimate is None:
        official_estimate = 0
    if our_bid is None:
        our_bid = 0
    
    if official_estimate > 0 and our_bid > 0:
        nppi = (our_bid / official_estimate) * 100
        st.metric("Our NPPI", f"{nppi:.2f}%", help="Our bid as percentage of OCE")
        
        if nppi < 85:
            st.warning("⚠️ Your bid is significantly below OCE. This may trigger SLT scrutiny.")
        elif nppi > 105:
            st.warning("⚠️ Your bid is above OCE. Consider reviewing your pricing.")
        else:
            st.success("✅ Your bid is within a reasonable range.")
        
        # Bid comparison using CRUD
        st.markdown("#### Bid Comparison")
        try:
            company_id = st.session_state.get('company_id')
            if company_id:
                bids_df = get_competitor_bids(tender_id, company_id)
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
        except Exception as e:
            st.warning(f"Could not load bid comparison: {e}")
    elif official_estimate > 0 and our_bid == 0:
        st.info("💡 Set your bid amount to see NPPI analysis.")
    else:
        st.warning("⚠️ Official Estimate not set. Please update tender with OCE.")


# =============================================================================
# TAB 4: TENDER ANALYSIS (Full Report)
# =============================================================================

def _render_tender_analysis_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender analysis for a specific tender"""
    debug_print("_render_tender_analysis_for_tender")
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT • NPPI Analysis • Winner Prediction • Sensitivity*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # ✅ Safe check for official_estimate
    if official_estimate is None or official_estimate <= 0:
        st.warning("⚠️ OCE is required for analysis. Please update the tender with Official Cost Estimate.")
        return
    
    # Load bids using CRUD
    bids_df = get_competitor_bids(tender_id, company_id)
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return
    
    # ✅ SAFELY get procurement_type and tender_date
    procurement_type = tender_data.get('procurement_type')
    if procurement_type is None or procurement_type == '':
        procurement_type = 'works'
    
    tender_date = tender_data.get('tender_publication_date') or tender_data.get('created_at')
    
    # ✅ SAFELY get winner_name
    winner_name = tender_data.get('winning_competitor')
    if winner_name is None or winner_name == '':
        winner_name = "Not Declared"
    
    # ✅ SAFELY get winner_amount
    winner_amount = tender_data.get('winning_bid_amount')
    if winner_amount is None:
        winner_amount = 0
    try:
        winner_amount = float(winner_amount)
    except (ValueError, TypeError):
        winner_amount = 0
    
    # Summary
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Tender ID", tender_id)
    with col2:
        st.metric("Winner", winner_name)
    with col3:
        st.metric("Winning Bid", f"BDT {winner_amount:,.3f}" if winner_amount > 0 else "N/A")
    with col4:
        st.metric("OCE", f"BDT {official_estimate:,.3f}")

    
    # Prepare bids
    competitor_bids = []
    for _, row in bids_df.iterrows():
        name = row.get('competitor_name', '')
        bid = float(row.get('bid_amount', 0))
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
    
    procurement_type = tender_data.get('procurement_type', 'works')
    tender_date = tender_data.get('tender_publication_date') or tender_data.get('created_at')
    
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
    with col1: st.metric("OCE", f"BDT {official_estimate:,.2f}")
    with col2: st.metric("X_NPPI", f"BDT {x_nppi:,.2f}", f"NPPI: {nppi_factor:.3f}")
    with col3: st.metric("Weighted Avg", f"BDT {wa:,.2f}")
    with col4: st.metric("SLT Lower Limit", f"BDT {slt_lower:,.2f}")
    
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
        nppi_min = st.number_input("NPPI Min", value=0.82, step=0.001, format="%.3f", key="nppi_min")
        nppi_max = st.number_input("NPPI Max", value=0.98, step=0.001, format="%.3f", key="nppi_max")
    with col2:
        if st.button("🔮 Run Prediction", type="primary", use_container_width=True, key="run_prediction"):
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
    if st.button("📄 Generate Professional HTML Report", type="primary", use_container_width=True, key="generate_report"):
        html_content = _generate_html_report(
            tender_data=tender_data,
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
            key="download_report"
        )


# =============================================================================
# TAB 5: TENDER RESULTS CRUD
# =============================================================================

def _render_tender_result_crud_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender result CRUD for a specific tender"""
    debug_print("_render_tender_result_crud_for_tender")
    st.markdown("### 🏆 Tender Result CRUD")
    st.caption("Edit bid amounts • Winner selection is **optional**")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return

    # ✅ SAFELY get tender_title
    tender_title = tender_data.get('tender_title')
    if tender_title is None or tender_title == '':
        tender_title = 'Untitled'

    # ✅ SAFE check for official_estimate
    if official_estimate is None:
        official_estimate = 0

    st.success(f"✅ Selected: **{tender_title}** | OCE: BDT {official_estimate:,.2f}")

    # Load current bids using CRUD
    bids_df = get_competitor_bids(tender_id, company_id)
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return

    # Ensure proper types
    if 'was_winner' not in bids_df.columns:
        bids_df['was_winner'] = False
    
    # Ensure bid_amount is float with full precision
    bids_df['bid_amount'] = bids_df['bid_amount'].astype(float)
    
    # Format for display
    bids_df['bid_amount'] = bids_df['bid_amount'].apply(lambda x: float(f"{x:.3f}"))


    st.markdown("#### 📋 Edit Bid Amounts")
    st.caption("**Note:** Selecting a winner is optional. You can save without any winner.")

    # Editable Table with proper formatting
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
        key=f"editor_{tender_id}"
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
                
                success = update_competitor_bid(
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
                update_tender_result(
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
                clear_tender_winner(tender_id)
                st.success(f"✅ {success_count} bids saved successfully (No winner marked)")
            
            st.rerun()
    
    with col2:
        if st.button("📥 Export Current Bids to CSV", use_container_width=True, key=f"export_{tender_id}"):
            export_df = edited_df.copy()
            export_df['bid_amount'] = export_df['bid_amount'].apply(lambda x: f"{x:.3f}")
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"bid_results_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"download_csv_{tender_id}"
            )


# =============================================================================
# TAB 6: IMPORT TENDER DATA
# =============================================================================
def _render_tender_importer_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender data importer for a specific tender with replace option"""
    
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3>📥 Import Tender Opening Report</h3>
        <p style="margin: 0;">Upload Excel file to import competitor bid data</p>
    </div>
    """, unsafe_allow_html=True)
    debug_print("_render_tender_importer_for_tender")
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # ✅ SAFELY get tender_title
    tender_title = tender_data.get('tender_title')
    if tender_title is None or tender_title == '':
        tender_title = 'Untitled'
    
    # ✅ SAFE check for official_estimate
    if official_estimate is None:
        official_estimate = 0
    
    st.success(f"✅ Selected: **{tender_title}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    # Check if data already exists using CRUD
    bids_df = get_competitor_bids(tender_id, company_id)
    existing_data_count = len(bids_df) if bids_df is not None else 0
    
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
    
    # ✅ Initialize importer only if needed
    try:
        from modules.tender_data_importer import TenderDataImporter
        importer = TenderDataImporter(db)
    except ImportError:
        st.error("❌ TenderDataImporter module not found. Please check your imports.")
        return
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_uploader_{tender_id}"
    )
    
    # Initialize session state for parsed data
    parsed_data_key = f"parsed_data_{tender_id}"
    if parsed_data_key not in st.session_state:
        st.session_state[parsed_data_key] = None
    
    if uploaded_file is not None:
        try:
            # Read Excel with header row
            df = pd.read_excel(uploaded_file, header=0)
            
            # Show preview
            st.caption("Preview of parsed data:")
            st.dataframe(df.head(5), use_container_width=True)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report_with_header(df)
            
            if not parsed_data or not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            # Store in session state
            st.session_state[parsed_data_key] = parsed_data
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Show debug info (optional)
            with st.expander("🔍 Debug Information"):
                st.write("Parsed Data Structure:")
                for i, comp in enumerate(parsed_data['competitors'][:5]):  # Show first 5 only
                    st.write(f"Competitor {i+1}: {comp.get('name', 'Unknown')}")
                    st.write(f"  Quoted Amount: {comp.get('quoted_amount', 0)}")
                    st.write(f"  Discount %: {comp.get('discount_percentage', 0)}")
                    st.write(f"  Discount Amount: {comp.get('discount_amount', 0)}")
                    st.write(f"  Final Amount: {comp.get('final_amount', 0)}")
                    st.write("---")

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
            
            # ===== WINNER SELECTION SECTION =====
            st.markdown("---")
            st.markdown("#### 🏆 Winner Selection")
            st.caption("Select the winner. Choose 'Skip Winner' if no winner should be declared.")
            
            # Get competitor names
            competitor_names = [comp.get('name', f'Competitor {i+1}') for i, comp in enumerate(parsed_data['competitors'])]
            
            # Find current winner
            current_winner = next((c for c in parsed_data['competitors'] if c.get('is_winner')), None)
            current_winner_name = current_winner.get('name') if current_winner else None
            
            # Winner selection dropdown
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
                        # Clear winner
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = False
                        parsed_data['winner_info'] = None
                        st.info("ℹ️ No winner selected. All competitors will have was_winner = 0.")
                    else:
                        # Set winner
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = (comp.get('name') == selected_winner)
                        winner_comp = next((c for c in parsed_data['competitors'] if c.get('is_winner')), None)
                        if winner_comp:
                            parsed_data['winner_info'] = {
                                'name': winner_comp.get('name'),
                                'final_amount': winner_comp.get('final_amount', 0)
                            }
                        st.success(f"✅ {selected_winner} marked as winner!")
                    
                    # Update session state
                    st.session_state[parsed_data_key] = parsed_data
                    st.rerun()
            
            # Show current winner status
            has_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
            if has_winner:
                winner_name = next((c.get('name') for c in parsed_data['competitors'] if c.get('is_winner')), None)
                st.success(f"🏆 Currently selected winner: **{winner_name}**")
            else:
                st.info("ℹ️ No winner currently selected. All competitors will have was_winner = 0.")
            
            # ===== NPPI ANALYSIS =====
            if official_estimate > 0:
                st.markdown("---")
                st.markdown("#### 📊 NPPI Analysis")
                
                nppi_data = []
                for comp in parsed_data['competitors']:
                    final_amount = comp.get('final_amount', 0)
                    if final_amount > 0 and official_estimate > 0:
                        nppi_pct = (final_amount / official_estimate) * 100
                        is_winner = "🏆" if comp.get('is_winner') else ""
                        nppi_data.append({
                            'Competitor': comp.get('name', 'Unknown'),
                            'Final Amount': f"BDT {final_amount:,.2f}",
                            'NPPI %': f"{nppi_pct:.2f}%",
                            'Winner': is_winner
                        })
                
                if nppi_data:
                    st.dataframe(pd.DataFrame(nppi_data), use_container_width=True, hide_index=True)
            
            # ===== IMPORT BUTTON =====
            st.markdown("---")
            import_label = "🔄 Replace & Import" if replace_data and existing_data_count > 0 else "📥 Import Competitors & Bid Data"
            import_help = "This will delete existing data and import new data" if replace_data else "This will add new bid records"
            
            if st.button(import_label, type="primary", use_container_width=True, key=f"import_{tender_id}", help=import_help):
                # Check if winner is selected
                has_selected_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
                
                if not has_selected_winner:
                    # Ensure all competitors have is_winner = False
                    for comp in parsed_data['competitors']:
                        comp['is_winner'] = False
                    parsed_data['winner_info'] = None
                    st.info("ℹ️ No winner will be marked. All competitors will have was_winner = 0.")
                
                with st.spinner("Importing data into database..."):
                    success, summary = importer.import_tender_data(
                        company_id=company_id,
                        tender_id=tender_id,
                        parsed_data=parsed_data,
                        tender_data=tender_data,
                        replace_existing=replace_data
                    )
                
                if success:
                    st.success("✅ Import completed successfully!")
                    st.balloons()
                    
                    # ✅ Clear session state
                    if parsed_data_key in st.session_state:
                        del st.session_state[parsed_data_key]
                    
                    if st.button("🔄 Refresh to see imported data", use_container_width=True):
                        st.rerun()
                else:
                    st.error("❌ Import failed.")
                    if summary and summary.get('errors'):
                        for err in summary['errors']:
                            st.error(err)
                    else:
                        st.error("Please check the data format and try again.")
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    
    # Help section
    with st.expander("ℹ️ How to use the tender importer"):
        st.markdown("""
        ### 📄 Process Overview
        
        1. **Upload Opening Report**: Upload the Excel file from e-GP
        2. **Review Data**: Check the parsed competitor data
        3. **Select Winner**: Choose the winner (or skip)
        4. **Import**: Import competitors and bid history
        
        ### 🏆 Winner Selection
        
        - **Select Winner**: Choose the winning bidder from the dropdown
        - **Skip Winner**: No winner will be marked (all `was_winner = 0`)
        - The winner selection is **optional** - you can import without declaring a winner
        
        ### 🔄 Replace Mode
        
        If data already exists for this tender:
        - **Without Replace**: New bid records are added (skips duplicates)
        - **With Replace**: All existing bid data is deleted and replaced with new data
        
        ### 📊 What Gets Imported
        
        - **Competitors**: New competitors added, existing ones updated
        - **Bid History**: All competitor bids recorded
        - **Winner**: Only if manually selected
        - **NPPI Factor**: Calculated from winner vs OCE
        
        ### 💡 Tips
        
        - Use **Replace** mode when correcting errors or re-importing corrected data
        - Without Replace, duplicate bids for the same competitor are skipped
        - Competitor names should be consistent for proper matching
        """)

# =============================================================================
# 🏗️ FOOTER
# =============================================================================

def render_footer():
    """Render e-GP style footer with gradient matching login page"""
    try:
        from version import __version__, __version_date__
    except ImportError:
        __version__ = "1.0.0"
        __version_date__ = datetime.now().strftime("%Y")
    
    st.markdown(f"""
    <style>
    .footer {{
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
        color: #94a3b8;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 2.5rem;
        text-align: center;
        font-size: 0.82rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}
    .footer .links {{
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 10px;
        font-size: 0.78rem;
    }}
    .footer .links a {{
        color: #94a3b8;
        text-decoration: none;
        transition: color 0.3s;
    }}
    .footer .links a:hover {{
        color: #667eea;
    }}
    .footer .divider {{
        color: #2d3748;
        margin: 0 4px;
    }}
    .footer strong {{
        color: #e0e0e0;
    }}
    .footer .highlight {{
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .footer .version-info {{
        font-size: 0.7rem;
        color: #4a5568;
        margin-top: 8px;
    }}
    .footer .copyright {{
        font-size: 0.7rem;
        color: #4a5568;
        margin-top: 4px;
    }}
    </style>
    <div class="footer">
        <div class="links">
            <a href="#">Home</a>
            <span class="divider">|</span>
            <a href="#">About e-GP</a>
            <span class="divider">|</span>
            <a href="#">Contact Us</a>
            <span class="divider">|</span>
            <a href="#">RSS Feed</a>
            <span class="divider">|</span>
            <a href="#">Terms and Conditions</a>
            <span class="divider">|</span>
            <a href="#">Service Level</a>
            <span class="divider">|</span>
            <a href="#">Disclaimer and Privacy Policy</a>
            <span class="divider">|</span>
            <a href="#">New Features</a>
        </div>
        <div style="font-size:0.7rem; color:#4a5568; margin-bottom:6px;">
            Best viewed in 1024 x 768 and above resolution. Browsers Tested & Certified by BPPA: 
            Microsoft Edge 109.x or above and Mozilla Firefox 113.x or above and Google Chrome 109.x or above
        </div>
        <div class="copyright">
            Copyright © 2011 Bangladesh Public Procurement Authority (BPPA). All Rights Reserved.
        </div>
        <div class="version-info">
            <span class="highlight">TenderAI</span> v{__version__} • {__version_date__} • 
            Powered by <span class="highlight">Bangladesh's First AI-Powered Tender Intelligence Platform</span>
        </div>
        <div style="font-size:0.65rem; color:#2d3748; margin-top:4px;">
            IMED, Ministry of Planning, Government of the People's Republic of Bangladesh
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# 🚀 MAIN ENTRY POINT
# =============================================================================
def _get_simulated_nppi(procurement_type: str, tender_date: str = None) -> float:
    """
    Simulate realistic NPPI based on PPR 2025 rules.
    NPPI is dynamic and derived from recent awarded tenders.
    
    Args:
        procurement_type: Type of procurement ('works', 'goods', 'services', 'consultancy')
        tender_date: Optional date string for seasonal adjustment
    
    Returns:
        float: Simulated NPPI factor between 0.82 and 0.99
    """
    debug_print("_get_simulated_nppi")
    
    # ✅ SAFELY get procurement_type
    if procurement_type is None or procurement_type == '':
        procurement_type = 'works'
    else:
        procurement_type = str(procurement_type).lower()
    
    # Base values based on historical trends in Bangladesh e-GP
    base_nppi = {
        'works': 0.912,      # Works usually have more competition
        'goods': 0.935,      # Goods tend to be closer to OCE
        'services': 0.908,
        'consultancy': 0.885
    }.get(procurement_type, 0.92)
    
    # Small variation based on date (market conditions)
    month_adjustment = 0.0
    if tender_date:
        try:
            # ✅ Handle different date formats
            if isinstance(tender_date, (datetime, pd.Timestamp)):
                dt = tender_date
            elif isinstance(tender_date, str):
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%b-%Y', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(str(tender_date)[:10], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format matches, try to parse as timestamp
                    try:
                        dt = datetime.fromtimestamp(float(tender_date))
                    except (ValueError, TypeError):
                        dt = datetime.now()
            else:
                dt = datetime.now()
            
            # Slight seasonal/market fluctuation (±2-3%)
            month_adjustment = (dt.month - 6) * 0.003
            # Additional: year-to-year trend (slight increase in competitiveness)
            year_adjustment = (dt.year - 2020) * 0.001
            month_adjustment += year_adjustment
            
        except Exception as e:
            # If date parsing fails, use no adjustment
            debug_print(f"Date parsing warning: {e}")
            pass
    
    nppi = base_nppi + month_adjustment
    
    # Realistic bounds according to observed e-GP data
    nppi = max(0.82, min(0.99, nppi))
    
    return round(nppi, 3)

def render_tender_management() -> None:
    """Main tender management entry point"""
    
    # Check if we need to show the tender form
    if st.session_state.get('page') == "tender_form":
        from modules.tender_form import render_tender_form
        render_tender_form()
        return
    debug_print("render_tender_management() called")
    render_role_badge()
    st.markdown("---")
    
    if not can_view_tenders():
        st.error("🔒 You don't have permission to view tenders.")
        return
    
    # Initialize view state
    if 'view_tender_detail' not in st.session_state:
        st.session_state.view_tender_detail = None
    
    # Initialize active tab
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "📊 Dashboard"
    
    # Render the dashboard
    render_tender_dashboard()


def _generate_html_report(tender_data, competitor_bids_sorted, official_estimate, 
                         nppi_factor, slt_lower, wa, wsd, winner_bid_obj=None, 
                         avg_nppi=None, predicted_winner=None, sensitivity_data=None):
    """Generate beautiful HTML report supporting both awarded and non-awarded tenders"""
    
    tender_id = tender_data.get('tender_id', 'N/A')
    tender_title = tender_data.get('tender_title', 'Untitled')
    procurement_type = tender_data.get('procurement_type', 'Works').title()
    current_date = datetime.now().strftime("%d %B %Y")
    
    display_nppi = avg_nppi if avg_nppi is not None else nppi_factor
    
    # Determine winner display
    if winner_bid_obj:
        winner_name = winner_bid_obj.get('name', 'N/A')
        winning_bid = winner_bid_obj.get('bid', 0)
        winner_label = "Declared Winner"
        is_awarded = True
    elif predicted_winner:
        winner_name = predicted_winner
        winning_bid = 0
        winner_label = "Predicted Winner"
        is_awarded = False
    else:
        winner_name = "Not Declared"
        winning_bid = 0
        winner_label = "No Winner"
        is_awarded = False

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TenderAI Report - {tender_id}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 35px; border-radius: 12px; margin-bottom: 30px; }}
            .logo {{ font-size: 32px; font-weight: bold; display: flex; align-items: center; gap: 15px; }}
            .container {{ max-width: 1100px; margin: auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
            h1, h2, h3 {{ color: #1e3a8a; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f1f5f9; font-weight: 600; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 25px 0; }}
            .metric {{ background: #f8fafc; padding: 18px; border-radius: 10px; text-align: center; }}
            .prediction {{ background: #f0f9ff; padding: 20px; border-radius: 10px; border-left: 6px solid #3b82f6; }}
            .sensitivity {{ background: #f8f9fa; padding: 20px; border-radius: 10px; }}
            footer {{ text-align: center; margin-top: 60px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">
                    🏛️ <span>TenderAI</span>
                </div>
                <h1>Tender Analysis Report</h1>
                <p><strong>Tender ID:</strong> {tender_id} &nbsp;&nbsp; | &nbsp;&nbsp; <strong>Date:</strong> {current_date}</p>
            </div>

            <h2>Tender Summary</h2>
            <div class="metric-grid">
                <div class="metric"><strong>Tender Title</strong><br>{tender_title}</div>
                <div class="metric"><strong>{winner_label}</strong><br>{winner_name}</div>
                <div class="metric"><strong>OCE</strong><br>BDT {official_estimate:,.2f}</div>
                <div class="metric"><strong>Type</strong><br>{procurement_type}</div>
            </div>

            <h2>Official PPR 2025 SLT Analysis</h2>
            <table>
                <tr><th>Parameter</th><th>Value</th></tr>
                <tr><td>Weighted Average (WA)</td><td>BDT {wa:,.2f}</td></tr>
                <tr><td>Weighted Std Dev (WSD)</td><td>BDT {wsd:,.2f}</td></tr>
                <tr><td><strong>SLT Lower Limit</strong></td><td><strong>BDT {slt_lower:,.2f}</strong></td></tr>
                <tr><td>Simulated NPPI Factor</td><td>{nppi_factor:.3f}</td></tr>
            </table>

    """

    # NPPI Section
    if winner_bid_obj:
        html += f"""
            <h2>Reverse-Engineered NPPI Factor</h2>
            <p><strong>Most Likely NPPI Used by e-GP System:</strong> 
               <span style="font-size:1.45em; color:#1e40af; font-weight:bold;">{display_nppi:.3f}</span></p>
        """
    elif predicted_winner:
        html += f"""
            <div class="prediction">
                <h3>🔮 Winner Prediction Result</h3>
                <p><strong>Most Likely Winner:</strong> {predicted_winner}</p>
                <p><strong>Based on NPPI Range Analysis</strong></p>
            </div>
        """

    # Bid Comparison Table
    html += """
            <h2>Bid Comparison Table</h2>
            <table>
                <tr>
                    <th>Rank</th>
                    <th>Competitor</th>
                    <th>Bid Amount</th>
                    <th>Evaluated Price (NPPI)</th>
                    <th>Status</th>
                </tr>
    """
    
    for i, b in enumerate(competitor_bids_sorted, 1):
        eval_price = b['bid'] * display_nppi
        status = "🏆 Winner" if b.get('is_winner') else "Competitor"
        if predicted_winner and b['name'] == predicted_winner:
            status = "🔮 Predicted Winner"
        html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{b['name']}</td>
                    <td>BDT {b['bid']:,.2f}</td>
                    <td>BDT {eval_price:,.2f}</td>
                    <td>{status}</td>
                </tr>
        """
    
    html += f"""
            </table>

            <div class="sensitivity">
                <h3>📈 NPPI Sensitivity Analysis</h3>
                <p>Shows how different NPPI factors affect the lowest evaluated price.</p>
            </div>

            <div style="margin-top: 40px; padding: 25px; background: #f0f9ff; border-radius: 10px;">
                <h3>Key Insights</h3>
                <ul>
                    <li>Analysis based on Official Cost Estimate: BDT {official_estimate:,.2f}</li>
                    <li>Simulated NPPI Factor: {nppi_factor:.3f}</li>
    """
    
    if winner_bid_obj:
        html += f"<li>Winner's bid represents <strong>{(winner_bid_obj['bid'] / official_estimate * 100):.1f}%</strong> of OCE</li>"
    elif predicted_winner:
        html += f"<li>Prediction based on NPPI range analysis</li>"
    
    html += """
                </ul>
            </div>

            <footer>
                Generated by <strong>TenderAI</strong> • Intelligent e-GP Analysis Platform<br>
                Report generated on {current_date} • Confidential
            </footer>
        </div>
    </body>
    </html>
    """
    return html


def _render_tender_reports() -> None:
    """Generate reports for tenders"""
    st.markdown("### 📊 Tender Reports")
    debug_print("_render_tender_reports");
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    tenders_df = get_company_tenders(company_id)
    
    if tenders_df.empty:
        st.info("📭 No data available")
        return
    
    # Summary statistics
    st.markdown("#### 📈 Performance Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        lost = len(tenders_df[tenders_df['bid_status'] == 'lost'])
        pending = len(tenders_df[tenders_df['bid_status'] == 'submitted'])
        
        if won + lost + pending > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Won', 'Lost', 'Pending'],
                values=[won, lost, pending],
                marker_colors=['#22c55e', '#ef4444', '#f97316'],
                hole=0.3
            )])
            fig.update_layout(title="Bid Status", height=280, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Monthly trend
        if 'bid_submission_date' in tenders_df.columns and not tenders_df['bid_submission_date'].isna().all():
            tenders_df_copy = tenders_df.copy()
            tenders_df_copy['month'] = pd.to_datetime(tenders_df_copy['bid_submission_date']).dt.to_period('M').astype(str)
            monthly = tenders_df_copy.groupby('month').size().reset_index(name='count')
            
            if not monthly.empty:
                fig = go.Figure(data=[go.Bar(
                    x=monthly['month'], 
                    y=monthly['count'], 
                    marker_color='#667eea',
                    text=monthly['count'],
                    textposition='auto'
                )])
                fig.update_layout(title="Monthly Submissions", height=280, margin=dict(t=30, b=0, l=0, r=0), xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        # Win rate by division
        if 'division' in tenders_df.columns:
            div_stats = tenders_df.groupby('division').agg({
                'bid_status': lambda x: (x == 'won').sum(),
                'id': 'count'
            }).reset_index()
            div_stats['win_rate'] = (div_stats['bid_status'] / div_stats['id'] * 100).fillna(0)
            
            if not div_stats.empty:
                fig = go.Figure(data=[go.Bar(
                    x=div_stats['division'], 
                    y=div_stats['win_rate'], 
                    marker_color='#22c55e',
                    text=div_stats['win_rate'].round(1).astype(str) + '%',
                    textposition='auto'
                )])
                fig.update_layout(title="Win Rate by Division", height=280, margin=dict(t=30, b=0, l=0, r=0), yaxis_range=[0, 100], yaxis_title="Win Rate (%)")
                st.plotly_chart(fig, use_container_width=True)
    
    # Export report
    st.markdown("#### 📥 Export Report")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Summary (CSV)", use_container_width=True):
            csv = tenders_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"tender_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        total = len(tenders_df)
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        win_rate = (won / total * 100) if total > 0 else 0
        st.info(f"📊 Total: {total} | Won: {won} | Win Rate: {win_rate:.1f}%")


def _render_team_management(tender_id: int, key_prefix: str) -> None:
    """Render team assignment UI in expander"""
    debug_print("_render_team_management")
    team = get_tender_team(tender_id)
    
    if team:
        st.markdown("**Current Team:**")
        for member in team:
            st.markdown(f"- {member[1]} • {member[3]}")
    
    # Add new member
    st.markdown("**Add Member:**")
    users = get_all_users(company_id=st.session_state.company_id)
    user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_member = st.selectbox("Member", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_add_member_{tender_id}")
    with col2:
        role = st.selectbox("Role", ["Bid Manager", "Technical Lead", "Financial", "Legal", "Support"], key=f"{key_prefix}_add_role_{tender_id}")
    with col3:
        if st.button("➕ Add", key=f"{key_prefix}_add_btn_{tender_id}"):
            if new_member != "Select" and new_member in user_options:
                if assign_team_member(tender_id, user_options[new_member], role):
                    st.success("Member added!")
                    st.rerun()


def _render_milestones(tender_id: int, key_prefix: str) -> None:
    """Render milestone management UI"""
    debug_print("_render_milestones")
    milestones = get_tender_milestones(tender_id)
    
    if not milestones.empty:
        st.markdown("**Milestones:**")
        for _, m in milestones.iterrows():
            icon = "✅" if m.get('completed') else "⏳"
            color = "green" if m.get('completed') else "orange"
            st.markdown(f"- {icon} <span style='color:{color}'>{m['milestone_name']}</span> • Due: {m['due_date'][:10]}", unsafe_allow_html=True)
    
    # Add milestone
    with st.expander("➕ Add Milestone"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Milestone Name", key=f"{key_prefix}_milestone_name_{tender_id}")
            due = st.date_input("Due Date", value=datetime.now() + timedelta(days=7), key=f"{key_prefix}_milestone_due_{tender_id}")
        with col2:
            users = get_all_users(company_id=st.session_state.company_id)
            user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
            assigned = st.selectbox("Assign To", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_milestone_assign_{tender_id}")
            notes = st.text_area("Notes", key=f"{key_prefix}_milestone_notes_{tender_id}")
        
        if st.button("Add Milestone", key=f"{key_prefix}_milestone_add_{tender_id}"):
            if name and assigned != "Select":
                assigned_id = user_options[assigned] if assigned in user_options else None
                if add_milestone(tender_id, name, due.strftime('%Y-%m-%d'), assigned_id, notes):
                    st.success("Milestone added!")
                    st.rerun()


# =============================================================================
# FIX: _render_team_and_milestones_for_tender
# =============================================================================

def _render_team_and_milestones_for_tender(tender_data: Dict[str, Any], tender_id: str):
    """Render team management and milestones for a specific tender"""
    
    st.markdown("### 👥 Team Management & Milestones")
    
    # Get tender ID from data
    tender_db_id = tender_data.get('id')
    if not tender_db_id:
        st.warning("Tender ID not found for team management.")
        return
    
    # ========== MILESTONE PROGRESS ==========
    _render_milestone_status_update(tender_db_id)
    
    st.markdown("---")
    
    # ========== TEAM MANAGEMENT SECTION ==========
    st.markdown("#### 👥 Team Assignment")
    
    # Get current team - returns list of tuples
    team = get_tender_team(tender_db_id)
    
    if team and len(team) > 0:
        st.markdown("**Current Team Members:**")
        for member in team:
            if len(member) >= 4:
                full_name = member[1]
                assigned_role = member[3]
                user_role = member[2] if len(member) > 2 else 'user'
                st.markdown(f"- **{full_name}** • {assigned_role} • {user_role}")
    else:
        st.info("No team members assigned yet.")
    
    # Add new member
    st.markdown("**Add Team Member:**")
    users = get_all_users(company_id=st.session_state.company_id)
    
    # users is list of tuples: (id, username, full_name, email, role, is_active)
    if users:
        user_options = {}
        for user in users:
            if len(user) >= 3:
                user_id = user[0]
                full_name = user[2]
                user_options[f"{full_name} ({user[1]})"] = user_id
        
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
                    if assign_team_member(tender_db_id, user_options[new_member], role):
                        st.success(f"✅ {new_member} added as {role}!")
                        st.rerun()
                    else:
                        st.error("Failed to add team member.")
                else:
                    st.warning("Please select a valid member.")
    else:
        st.warning("No users found for this company. Please add users first.")
    
    st.markdown("---")
    
    # ========== MILESTONES SECTION ==========
    st.markdown("#### 🎯 Milestones & Tasks")
    
    # Get current milestones
    milestones = get_tender_milestones(tender_db_id)
    
    if milestones is not None and not milestones.empty:
        st.markdown("**Current Milestones:**")
        for _, m in milestones.iterrows():
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
            # Get users for assignment
            users = get_all_users(company_id=st.session_state.company_id)
            if users:
                user_options = {}
                for user in users:
                    if len(user) >= 3:
                        user_id = user[0]
                        full_name = user[2]
                        user_options[f"{full_name} ({user[1]})"] = user_id
                
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
                milestone_id = add_milestone(
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


# =============================================================================
# FIX: _add_team_summary_to_information_tab
# =============================================================================

def _add_team_summary_to_information_tab(tender_data: Dict[str, Any]):
    """Add a quick team summary to the information tab"""
    
    tender_db_id = tender_data.get('id')
    if not tender_db_id:
        return
    
    st.markdown("#### 👥 Team Summary")
    team = get_tender_team(tender_db_id)
    
    if team and len(team) > 0:
        team_cols = st.columns(min(4, len(team)))
        for i, member in enumerate(team):
            if len(member) >= 4:
                full_name = member[1]
                assigned_role = member[3]
                with team_cols[i % len(team_cols)]:
                    st.info(f"**{assigned_role}**\n\n{full_name}")
    else:
        st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")


# =============================================================================
# FIX: _render_milestone_status_update
# =============================================================================

def _render_milestone_status_update(tender_db_id: int):
    """Render a quick milestone status update section"""
    
    milestones = get_tender_milestones(tender_db_id)
    
    if milestones is None or milestones.empty:
        st.caption("No milestones created yet.")
        return
    
    st.markdown("#### 📊 Milestone Progress")
    
    total = len(milestones)
    completed = len(milestones[milestones['completed'] == 1])
    progress = (completed / total * 100) if total > 0 else 0
    
    st.progress(progress / 100, text=f"{progress:.0f}% Complete ({completed}/{total})")
    
    # Show upcoming milestones
    upcoming = milestones[milestones['completed'] != 1].sort_values('due_date').head(3)
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


def _load_tender_for_edit(tender_id: int) -> bool:
    """Helper to load tender data and prepare for editing"""
    
    debug_print(f"_load_tender_for_edit() called with tender_id: {tender_id}")
    
    try:
        company_id = st.session_state.get('company_id')
        if not company_id:
            debug_print("No company_id in session state")
            return False
        
        # Use CRUD to get tender
        tender_data = get_tender_by_db_id(tender_id, company_id)
        
        debug_print(f"Query executed. Row found: {tender_data is not None}")
        if tender_data:
            debug_print(f"Row data: {tender_data}")
            
            # Store in session state
            st.session_state.extracted_data = tender_data
            st.session_state.skip_review = True
            st.session_state.edit_tender_id = tender_id
            st.session_state.edit_mode = True
            
            debug_print("Session state after loading data:", {
                'extracted_data': st.session_state.extracted_data is not None,
                'skip_review': st.session_state.skip_review,
                'edit_tender_id': st.session_state.edit_tender_id,
                'edit_mode': st.session_state.edit_mode
            })
            
            # Clear stale form state
            keys_to_clear = [k for k in list(st.session_state.keys()) 
                           if k.startswith('form_') or k in ('_form_submitting', '_form_reset', '_tender_pdf_upload')]
            debug_print(f"Clearing form keys: {keys_to_clear}")
            for k in keys_to_clear:
                del st.session_state[k]
            
            return True
        else:
            debug_print("No row found for tender_id!")
            return False
            
    except Exception as e:
        debug_print(f"Exception in _load_tender_for_edit: {str(e)}")
        debug_print(traceback.format_exc())
        st.error(f"❌ Failed to load tender: {str(e)}")
        return False


# =============================================================================
# RENDER TENDERS TABLE
# =============================================================================

def _render_tenders_table():
    """Render e-GP style tenders table with dashboard buttons"""
    
    st.markdown("""
    <style>
    .table-container {
        background: #0f0f23;
        border-radius: 12px;
        border: 1px solid rgba(102, 126, 234, 0.1);
        overflow: hidden;
        margin-top: 10px;
    }
    .tender-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .tender-table thead th {
        background: #1a1a3e;
        color: #94a3b8;
        padding: 10px 12px;
        text-align: left;
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 2px solid rgba(102, 126, 234, 0.15);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .tender-table tbody tr {
        border-bottom: 1px solid rgba(255,255,255,0.03);
        transition: background 0.2s;
    }
    .tender-table tbody tr:hover {
        background: rgba(102, 126, 234, 0.05);
    }
    .tender-table tbody td {
        padding: 10px 12px;
        vertical-align: top;
        color: #e0e0e0;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
    }
    .status-awarded { background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }
    .status-submitted { background: #f59e0b20; color: #f59e0b; border: 1px solid #f59e0b40; }
    .status-draft { background: #64748b20; color: #94a3b8; border: 1px solid #64748b40; }
    .status-won { background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }
    .status-lost { background: #ef444420; color: #ef4444; border: 1px solid #ef444440; }
    .status-processing { background: #3b82f620; color: #3b82f6; border: 1px solid #3b82f640; }
    .tender-id-cell {
        font-weight: 600;
        color: #667eea;
    }
    .ref-text {
        font-size: 11px;
        color: #64748b;
    }
    .tender-title-cell {
        max-width: 300px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .title-text {
        display: block;
        font-weight: 500;
        color: #e0e0e0;
    }
    .pagination-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        padding: 15px 0;
        flex-wrap: wrap;
    }
    .pagination-container .page-info {
        color: #94a3b8;
        font-size: 13px;
    }
    .pagination-container .page-btn {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        padding: 4px 12px !important;
        font-size: 13px !important;
        border-radius: 4px !important;
    }
    .pagination-container .page-btn:hover:not(:disabled) {
        background: rgba(102, 126, 234, 0.2) !important;
        color: white !important;
    }
    .pagination-container .page-btn:disabled {
        opacity: 0.3;
        cursor: not-allowed;
    }
    .pagination-container .page-number {
        display: flex;
        gap: 4px;
    }
    .pagination-container .page-number button {
        padding: 4px 10px !important;
        font-size: 13px !important;
        border-radius: 4px !important;
        min-width: 32px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Get filtered tenders using CRUD
    tenders_df = get_company_tenders(company_id)
    
    if tenders_df.empty:
        st.info("📭 No tenders found. Create your first tender entry!")
        return
    
    # Apply filters
    filtered_df = _apply_filters(tenders_df)
    
    # Header with action buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 📋 Tender/Proposal Search Result")
        st.caption(f"Showing {len(filtered_df)} of {len(tenders_df)} tenders")
    
    with col2:
        if st.button("➕ Create New Tender", key="create_new_tender", use_container_width=True, type="primary"):
            st.session_state.edit_mode = False
            st.session_state.edit_tender_id = None
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
            st.session_state.page = "tender_form"
            st.rerun()
    
    if filtered_df.empty:
        st.info("No tenders match the current filters.")
        return
    debug_print("_render_tenders_table")
    # Prepare display data
    display_data = _prepare_tender_display_data(filtered_df)
    
    # Render table with pagination
    _render_tender_table_rows(display_data, company_id)


def _apply_filters(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Apply search filters to tender data"""
    filters = st.session_state.tender_search_filters
    filtered_df = tenders_df.copy()
    
    if filters.get('procurement_nature') and filters['procurement_nature'] != 'All':
        filtered_df = filtered_df[filtered_df['procurement_nature'] == filters['procurement_nature']]
    if filters.get('procurement_type') and filters['procurement_type'] != 'All':
        filtered_df = filtered_df[filtered_df['procurement_type'] == filters['procurement_type']]
    if filters.get('tender_id'):
        filtered_df = filtered_df[filtered_df['tender_id'].str.contains(filters['tender_id'], case=False, na=False)]
    if filters.get('publishing_date_from'):
        filtered_df = filtered_df[pd.to_datetime(filtered_df['tender_publication_date']) >= pd.to_datetime(filters['publishing_date_from'])]
    if filters.get('publishing_date_to'):
        filtered_df = filtered_df[pd.to_datetime(filtered_df['tender_publication_date']) <= pd.to_datetime(filters['publishing_date_to'])]
    
    return filtered_df

def _prepare_tender_display_data(filtered_df: pd.DataFrame) -> List[Dict]:
    """Prepare tender data for display"""
    
    debug_print("_prepare_tender_display_data")
    display_data = []
    for _, row in filtered_df.iterrows():
        status = row.get('bid_status', 'draft')
        status_display = {
            'won': 'Contract Awarded',
            'submitted': 'Being processed',
            'draft': 'Draft',
            'lost': 'Lost',
            'awarded': 'Contract Awarded'
        }.get(status, status.title())
        
        status_class = {
            'won': 'status-awarded',
            'submitted': 'status-processing',
            'draft': 'status-draft',
            'lost': 'status-lost',
            'awarded': 'status-awarded'
        }.get(status, 'status-draft')
        
        # ✅ SAFELY get procurement_type with fallback
        procurement_type = row.get('procurement_type')
        if procurement_type is None:
            procurement_type = 'N/A'
        else:
            procurement_type = str(procurement_type).upper()
        
        display_data.append({
            'id': row['id'],
            'tender_id': row.get('tender_id', 'N/A'),
            'title': row.get('tender_title', 'Untitled'),
            'procuring_entity': row.get('procuring_entity', 'N/A'),
            'procurement_type': procurement_type,  # ✅ Safe value
            'status': status,
            'status_display': status_display,
            'status_class': status_class,
            'pub_date': row.get('tender_publication_date'),
            'closing_date': row.get('submission_deadline')
        })
    
    return display_data


def _render_tender_table_rows(display_data: List[Dict], company_id: int):
    """Render table rows with pagination and search"""
    debug_print("_render_tender_table_rows")
    
    # Search bar
    search = st.text_input(
        "🔍 Search Tenders", 
        placeholder="Search by tender ID, reference, title, or procuring entity...",
        key="tender_search_input"
    )
    
    # Apply search filter
    filtered_data = display_data
    if search:
        search_lower = search.lower()
        filtered_data = [
            item for item in display_data
            if (search_lower in str(item.get('tender_id', '')).lower() or
                search_lower in str(item.get('title', '')).lower() or
                search_lower in str(item.get('procuring_entity', '')).lower() or
                search_lower in str(item.get('procurement_type', '')).lower())
        ]
    
    # Pagination
    if 'tender_page' not in st.session_state:
        st.session_state.tender_page = 1
    
    items_per_page = 10
    total_items = len(filtered_data)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    
    if st.session_state.tender_page < 1:
        st.session_state.tender_page = 1
    elif st.session_state.tender_page > total_pages:
        st.session_state.tender_page = total_pages
    
    start_idx = (st.session_state.tender_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_items = filtered_data[start_idx:end_idx]
    
    st.caption(f"Showing {len(page_items)} of {total_items} tenders")
    
    # Table header
    st.markdown("""
    <div style="display:grid; grid-template-columns: 0.5fr 2.5fr 2.5fr 2fr 1.5fr 1.5fr 1fr; gap:0; padding:10px 12px; background:#1a1a3e; border-radius:8px 8px 0 0; border-bottom:2px solid rgba(102,126,234,0.2);">
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">S.No</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">Tender/Proposal ID, Reference No., Status</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">Procurement Nature, Title</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">PE</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">Type, Method</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">Publishing Date, Closing Date</div>
        <div style="color:#94a3b8; font-size:11px; font-weight:500; text-transform:uppercase;">Dashboard</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Render rows
    for idx, item in enumerate(page_items, start=start_idx + 1):
        # ✅ SAFELY format dates
        pub_date = item.get('pub_date')
        if pub_date and pd.notna(pub_date):
            try:
                pub_date_str = pd.to_datetime(pub_date).strftime('%d-%b-%Y %H:%M:%S')
            except:
                pub_date_str = 'N/A'
        else:
            pub_date_str = 'N/A'
        
        closing_date = item.get('closing_date')
        if closing_date and pd.notna(closing_date):
            try:
                closing_date_str = pd.to_datetime(closing_date).strftime('%d-%b-%Y %H:%M:%S')
            except:
                closing_date_str = 'N/A'
        else:
            closing_date_str = 'N/A'
        
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 2.5, 2.5, 2, 1.5, 1.5, 1], gap="small")
        
        with col1:
            st.write(f"{idx}")
        with col2:
            st.markdown(f"""
            <div class="tender-id-cell">{item['tender_id']}</div>
            <div class="ref-text">REF: {item['tender_id']}</div>
            <span class="status-badge {item['status_class']}">{item['status_display']}</span>
            """, unsafe_allow_html=True)
        with col3:
            # ✅ SAFELY get title and procurement_type
            title = item.get('title', 'Untitled')
            proc_type = item.get('procurement_type', 'N/A')
            display_title = f"{proc_type}, {title[:80]}{'...' if len(title) > 80 else ''}"
            st.markdown(f"""
            <div class="tender-title-cell">
                <span class="title-text">{display_title}</span>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.caption(item.get('procuring_entity', 'N/A')[:50])
        with col5:
            st.write(item.get('procurement_type', 'N/A'))
            st.caption("LTM")
        with col6:
            st.caption(pub_date_str)
            st.caption(closing_date_str)
        with col7:
            tender_id = item.get('tender_id')
            if st.button("🔍", key=f"dash_{item['id']}_{idx}", use_container_width=True):
                if tender_id:
                    tender_data = get_tender_by_id(tender_id, company_id)
                    if tender_data:
                        tender_data = _normalize_tender_data(tender_data)
                        st.session_state.view_tender_detail = tender_data
                        st.rerun()
                    else:
                        st.error("Failed to load tender details")
                else:
                    st.error("Invalid tender ID")
        
        st.divider()
    
    # Pagination
    if total_pages > 1:
        _render_pagination(total_pages)



def _render_pagination(total_pages: int):
    """Render pagination controls"""
    
    st.markdown('<div class="pagination-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        st.markdown(f"""
        <div class="page-info">
            Page <strong>{st.session_state.tender_page}</strong> of <strong>{total_pages}</strong>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        nav_cols = st.columns([1, 1, 3, 1, 1])
        
        with nav_cols[0]:
            if st.button("«", key="first_page", use_container_width=True, disabled=(st.session_state.tender_page == 1)):
                st.session_state.tender_page = 1
                st.rerun()
        
        with nav_cols[1]:
            if st.button("‹", key="prev_page", use_container_width=True, disabled=(st.session_state.tender_page == 1)):
                st.session_state.tender_page -= 1
                st.rerun()
        
        with nav_cols[2]:
            page_cols = st.columns(min(total_pages, 5))
            start_page = max(1, st.session_state.tender_page - 2)
            end_page = min(total_pages, start_page + 4)
            
            for i, p in enumerate(range(start_page, end_page + 1)):
                with page_cols[i]:
                    if st.button(str(p), key=f"page_{p}", use_container_width=True, 
                                type="primary" if p == st.session_state.tender_page else "secondary"):
                        st.session_state.tender_page = p
                        st.rerun()
        
        with nav_cols[3]:
            if st.button("›", key="next_page", use_container_width=True, disabled=(st.session_state.tender_page == total_pages)):
                st.session_state.tender_page += 1
                st.rerun()
        
        with nav_cols[4]:
            if st.button("»", key="last_page", use_container_width=True, disabled=(st.session_state.tender_page == total_pages)):
                st.session_state.tender_page = total_pages
                st.rerun()
    
    with col3:
        go_to_page = st.number_input(
            "Go to",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.tender_page,
            step=1,
            key="go_to_page_input",
            label_visibility="collapsed"
        )
        if go_to_page != st.session_state.tender_page:
            st.session_state.tender_page = go_to_page
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_competitor_list():
    """Display the main competitor dashboard with the UI shown"""
    
    company_id = st.session_state.get('company_id')
    
    # ============================================================================
    # HEADER SECTION WITH 4 KPI CARDS
    # ============================================================================
    st.markdown("### 📊 Competitor Intelligence Dashboard")
    
    # Get summary stats using CRUD
    competitors = get_competitor_master_list(company_id, active_only=True)
    
    if not competitors:
        st.info("No competitors found. Add your first competitor using the form above.")
        return
    
    comp_df = pd.DataFrame(competitors)
    
    # Calculate KPIs
    total_competitors = len(comp_df)
    active_competitors = len([c for c in competitors if c.get('is_active', True)])
    
    total_bids = comp_df['total_bids'].sum()
    total_wins = comp_df['total_wins'].sum()
    win_rate = (total_wins / total_bids * 100) if total_bids > 0 else 0
    
    avg_ratio = comp_df['avg_bid_ratio'].mean()
    if pd.isna(avg_ratio):
        avg_ratio = 0.0
    
    # Display 4 KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Competitors", total_competitors)
    with col2:
        st.metric("Active Competitors", active_competitors)
    with col3:
        st.metric("Win Rate (All)", f"{win_rate:.1f}%")
    with col4:
        st.metric("Avg Bid Ratio", f"{avg_ratio:.3f}")
    
    st.divider()
    
    # ============================================================================
    # CHARTS SECTION
    # ============================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        if len(comp_df) > 0 and comp_df['total_bids'].sum() > 0:
            st.markdown("#### Bid Distribution")
            fig = go.Figure(data=[go.Histogram(
                x=comp_df['total_bids'],
                nbinsx=20,
                marker_color='blue'
            )])
            fig.update_layout(
                title='Competitor Bid Distribution',
                xaxis_title='Number of Bids',
                height=280,
                margin=dict(t=30, b=0, l=0, r=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No bid data available for chart")
    
    with col2:
        if len(comp_df) > 0 and comp_df['total_bids'].sum() > 0:
            st.markdown("#### Win Rate by Competitor")
            comp_df['Win Rate'] = comp_df.apply(
                lambda x: (x['total_wins'] / x['total_bids'] * 100) if x['total_bids'] > 0 else 0, 
                axis=1
            )
            top_competitors = comp_df.nlargest(10, 'total_bids')
            fig = go.Figure(data=[go.Bar(
                x=top_competitors['competitor_name'],
                y=top_competitors['Win Rate'],
                marker_color=top_competitors['Win Rate'],
                marker_colorscale='Blues',
                text=top_competitors['Win Rate'].round(1).astype(str) + '%',
                textposition='auto'
            )])
            fig.update_layout(
                title='Top 10 Competitors by Win Rate',
                xaxis_title='Competitor',
                yaxis_title='Win Rate (%)',
                height=280,
                margin=dict(t=30, b=0, l=0, r=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No win rate data available for chart")
    
    st.divider()
    
    # ============================================================================
    # COMPETITOR LIST TABLE
    # ============================================================================
    st.markdown("### 📋 Competitor List")
    
    # Search bar
    search = st.text_input(
        "🔍 Search Competitor",
        placeholder="Enter competitor name, type, or strategy...",
        key="competitor_search_input"
    )
    
    # Apply search filter
    filtered_competitors = competitors.copy()
    if search:
        search_lower = search.lower()
        filtered_competitors = [
            c for c in competitors
            if (search_lower in str(c.get('competitor_name', '')).lower() or
                search_lower in str(c.get('business_type', '')).lower() or
                search_lower in str(c.get('preferred_strategy', '')).lower() or
                search_lower in str(c.get('contact_person', '')).lower())
        ]
    
    # Sorting
    if 'competitor_sort' not in st.session_state:
        st.session_state.competitor_sort = "Name"
    
    sort_options = {
        "Name": "competitor_name",
        "Total Bids": "total_bids",
        "Win Rate": "win_percentage",
        "Last Seen": "last_seen"
    }
    
    sort_by = st.selectbox(
        "Sort by", 
        list(sort_options.keys()),
        key="competitor_sort_selector"
    )
    
    sort_key = sort_options.get(sort_by, "competitor_name")
    if sort_key == "win_percentage":
        for c in filtered_competitors:
            c['win_percentage'] = (c.get('total_wins', 0) / c.get('total_bids', 1) * 100) if c.get('total_bids', 0) > 0 else 0
        filtered_competitors.sort(key=lambda x: x.get('win_percentage', 0), reverse=True)
    elif sort_key == "last_seen":
        filtered_competitors.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
    elif sort_key == "total_bids":
        filtered_competitors.sort(key=lambda x: x.get('total_bids', 0), reverse=True)
    else:
        filtered_competitors.sort(key=lambda x: x.get('competitor_name', ''))
    
    st.caption(f"Showing {len(filtered_competitors)} competitors")
    
    # Pagination
    page_size = 10
    total_pages = (len(filtered_competitors) - 1) // page_size + 1 if filtered_competitors else 1
    
    if 'competitor_page' not in st.session_state:
        st.session_state.competitor_page = 1
    
    if st.session_state.competitor_page < 1:
        st.session_state.competitor_page = 1
    elif st.session_state.competitor_page > total_pages:
        st.session_state.competitor_page = total_pages
    
    page = st.session_state.competitor_page
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(filtered_competitors))
    page_competitors = filtered_competitors[start_idx:end_idx]
    
    # Display table
    if page_competitors:
        cols = st.columns([3, 2, 2, 2, 1])
        cols[0].write("**Competitor Name**")
        cols[1].write("**Type**")
        cols[2].write("**First Seen**")
        cols[3].write("**Last Seen**")
        cols[4].write("**Details**")
        
        st.divider()
        
        for idx, comp in enumerate(page_competitors, start=start_idx + 1):
            cols = st.columns([3, 2, 2, 2, 1])
            
            cols[0].write(f"**{comp.get('competitor_name', 'Unknown')}**")
            cols[1].write(comp.get('business_type', 'N/A'))
            
            first_seen = comp.get('first_seen')
            if first_seen and isinstance(first_seen, str):
                try:
                    first_seen = datetime.strptime(first_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    first_seen = 'N/A'
            elif first_seen:
                first_seen = first_seen.strftime('%Y-%m-%d')
            else:
                first_seen = 'N/A'
            cols[2].write(first_seen)
            
            last_seen = comp.get('last_seen')
            if last_seen and isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    last_seen = 'N/A'
            elif last_seen:
                last_seen = last_seen.strftime('%Y-%m-%d')
            else:
                last_seen = 'N/A'
            cols[3].write(last_seen)
            
            comp_id = comp.get('id')
            if cols[4].button(
                "🔍",
                key=f"view_comp_{comp_id}_{idx}",
                help=f"View full intelligence profile for {comp.get('competitor_name')}"
            ):
                st.session_state.competitor_id = comp_id
                st.session_state.page = "competitor_profile"
                st.rerun()
        
        # Pagination controls
        st.divider()
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if page > 1:
                if st.button("◀ Previous", key="comp_prev_page"):
                    st.session_state.competitor_page = page - 1
                    st.rerun()
        
        with col2:
            st.caption(f"Page {page} of {total_pages} | Showing {len(page_competitors)} of {len(filtered_competitors)} competitors")
        
        with col3:
            if page < total_pages:
                if st.button("Next ▶", key="comp_next_page"):
                    st.session_state.competitor_page = page + 1
                    st.rerun()
    else:
        st.info("No competitors match your search criteria")

def _render_winner_tab(tender_data: Dict[str, Any], official_estimate: float, tender_id: str):
    """Render the Winner Information tab"""
    debug_print("_render_winner_tab")
    st.markdown("#### Winner Information")
    
    # ✅ Safe get winner
    winner = tender_data.get('winning_competitor')
    if winner is None or winner == '':
        winner = None
    
    # ✅ Safe get winner_amount
    winner_amount = tender_data.get('winning_bid_amount')
    if winner_amount is None:
        winner_amount = 0
    try:
        winner_amount = float(winner_amount)
    except (ValueError, TypeError):
        winner_amount = 0
    
    if winner and winner_amount > 0:
        st.success(f"🏆 **Winner:** {winner}")
        st.info(f"**Winning Bid Amount:** BDT {winner_amount:,.2f}")
        
        if official_estimate > 0 and winner_amount > 0:
            nppi = (winner_amount / official_estimate) * 100
            st.metric("NPPI Factor", f"{nppi:.2f}%")
    else:
        st.warning("No winner declared yet for this tender.")
        st.info("💡 You can declare a winner in the 'Tender Results CRUD' tab.")
    
    # Bid history - using CRUD
    st.markdown("#### Bid History")
    try:
        company_id = st.session_state.get('company_id')
        if company_id:
            bids_df = get_competitor_bids(tender_id, company_id)
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
    except Exception as e:
        st.warning(f"Could not load bid history: {e}")
