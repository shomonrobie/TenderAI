# modules/tender_management.py
"""
Complete Tender Management Module
Track tender participation, bid submission, deadlines, and winner tracking

Refactored for:
- e-GP style dashboard with table view
- Tender-specific detail pages
- Proper session state management
- Clean separation of concerns
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import numpy as np
import logging
from typing import Optional, Dict, List, Any, Tuple
from database.unified_db_manager import UnifiedDatabaseManager

DEBUG_MODE = True
logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()

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
        tender_data = db_instance.get_tender_by_id(cached_state['selected_tender_id'], company_id)
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
                new_tender_data = db_instance.get_tender_by_id(new_tender_id, company_id)
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
        tender_data = db_instance.get_tender_by_id(tender_id, company_id)
        tender_selector_manager.update_selection(tender_id, tender_data, search_term)
    
    return result


# =============================================================================
# 🗄️ DATABASE METHODS
# =============================================================================

def create_tender(company_id: int, tender_data: Dict[str, Any], created_by: int) -> Optional[int]:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id FROM company_tenders WHERE company_id = ? AND tender_id = ? AND is_active = 1
        ''', (company_id, tender_data.get('tender_id', '')))
        if cursor.fetchone():
            conn.close()
            return None
        
        columns = [
            'company_id', 'tender_id', 'tender_title', 'procuring_entity', 'division',
            'district', 'thana', 'country', 'procurement_type', 'official_estimate',
            'submission_deadline', 'tender_security', 'document_fee', 'evaluation_type',
            'mode_of_payment', 'eligibility_criteria', 'invitation_ref_no', 'package_no',
            'project_code', 'project_name', 'inviting_official_name', 'inviting_official_designation',
            'inviting_official_phone', 'inviting_official_email', 'inviting_official_address', 
            'inviting_official_city', 'inviting_official_thana', 'inviting_official_district', 
            'notes', 'created_by', 'is_locked', 'is_copy', 'original_tender_id', 'is_active',
            'app_id', 'procuring_entity_code', 'procurement_nature', 'event_type', 
            'budget_type', 'source_of_funds', 'category', 'tender_publication_date',
            'document_selling_end_date', 'pre_bid_meeting_start', 'pre_bid_meeting_end',
            'bid_opening_date', 'security_submission_deadline', 'security_valid_upto',
            'tender_valid_upto'
        ]
        
        defaults = {
            'tender_id': '', 'tender_title': '', 'procuring_entity': '', 'division': 'Dhaka',
            'district': '', 'thana': '', 'country': 'Bangladesh', 'procurement_type': 'works',
            'official_estimate': 0.0, 'tender_security': 0.0, 'document_fee': 0.0,
            'evaluation_type': 'Lot wise', 'mode_of_payment': 'Payment through Bank',
            'eligibility_criteria': 'As Per Tender Documents', 'invitation_ref_no': '',
            'package_no': '', 'project_code': '', 'project_name': '',
            'inviting_official_name': '', 'inviting_official_designation': '',
            'inviting_official_phone': '', 'inviting_official_email': '',
            'inviting_official_address': '', 'inviting_official_city': '',
            'inviting_official_thana': '', 'inviting_official_district': '', 'notes': '',
            'app_id': '', 'procuring_entity_code': '', 'procurement_nature': 'Works',
            'event_type': 'TENDER', 'budget_type': '', 'source_of_funds': 'Government',
            'category': '', 'submission_deadline': None, 'security_submission_deadline': None
        }
        
        values = []
        for col in columns:
            if col == 'company_id':
                values.append(company_id)
            elif col == 'created_by':
                values.append(created_by)
            elif col == 'is_locked':
                values.append(0)
            elif col == 'is_copy':
                values.append(0)
            elif col == 'original_tender_id':
                values.append(None)
            elif col == 'is_active':
                values.append(1)
            else:
                val = tender_data.get(col, defaults.get(col))
                if col in ['official_estimate', 'tender_security', 'document_fee']:
                    try: val = float(val) if val is not None else 0.0
                    except: val = 0.0
                values.append(val)
                
        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join(columns)
        query = f"INSERT INTO company_tenders ({col_names}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        tender_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        tender_selector_manager.clear_selection()
        return tender_db_id
        
    except Exception as e:
        logger.error(f"Failed to create tender: {e}", exc_info=True)
        return None


def update_tender(tender_id: int, tender_data: Dict[str, Any], updated_by: int) -> bool:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id FROM company_tenders WHERE id = ? AND company_id = ? AND is_active = 1
        ''', (tender_id, st.session_state.company_id))
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        updatable_columns = [
            'tender_id', 'tender_title', 'procuring_entity', 'division',
            'district', 'thana', 'country', 'procurement_type', 'official_estimate',
            'submission_deadline', 'tender_security', 'document_fee', 'evaluation_type',
            'mode_of_payment', 'eligibility_criteria', 'invitation_ref_no', 'package_no',
            'project_code', 'project_name', 'inviting_official_name',
            'inviting_official_designation', 'inviting_official_phone',
            'inviting_official_email', 'inviting_official_address',
            'inviting_official_city', 'inviting_official_thana',
            'inviting_official_district', 'notes', 'app_id', 'procuring_entity_code',
            'procurement_nature', 'event_type', 'budget_type', 'source_of_funds',
            'category', 'tender_publication_date', 'document_selling_end_date',
            'pre_bid_meeting_start', 'pre_bid_meeting_end', 'bid_opening_date',
            'security_submission_deadline', 'security_valid_upto', 'tender_valid_upto'
        ]
        
        update_fields = []
        update_values = []
        
        for col in updatable_columns:
            if col in tender_data and tender_data[col] is not None:
                update_fields.append(f"{col} = ?")
                update_values.append(tender_data[col])
        
        if not update_fields:
            conn.close()
            return False
        
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now())
        update_values.append(tender_id)
        
        query = f"UPDATE company_tenders SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(query, update_values)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            logger.info(f"Tender {tender_id} updated by user {updated_by}")
            tender_selector_manager.clear_selection()
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to update tender: {e}", exc_info=True)
        return False


def get_company_tenders(company_id: int, status_filter: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
            t.division, t.district, t.thana, t.country, t.procurement_type,
            t.official_estimate, t.submission_deadline, t.tender_security,
            t.document_fee, t.evaluation_type, t.mode_of_payment,
            t.eligibility_criteria, t.invitation_ref_no, t.package_no,
            t.project_code, t.project_name, t.inviting_official_name,
            t.inviting_official_designation, t.inviting_official_phone,
            t.inviting_official_email, t.inviting_official_address,
            t.inviting_official_city, t.inviting_official_thana,
            t.inviting_official_district, t.our_bid_amount, t.bid_submitted_by,
            t.bid_submission_date, t.bid_status, t.evaluation_status,
            t.winning_bid_amount, t.winning_competitor, t.our_rank,
            t.total_bidders, t.award_date, t.notes, t.created_by,
            t.created_at, t.updated_at,
            t.is_locked, t.locked_at, t.locked_by,
            t.is_copy, t.original_tender_id,
            t.is_active, t.deleted_at, t.deleted_by,
            u.full_name as submitted_by_name,
            t.app_id, t.procuring_entity_code, t.procurement_nature,
            t.event_type, t.budget_type, t.source_of_funds, t.category,
            t.tender_publication_date, t.document_selling_end_date,
            t.pre_bid_meeting_start, t.pre_bid_meeting_end,
            t.bid_opening_date, t.security_submission_deadline,
            t.security_valid_upto, t.tender_valid_upto
        FROM company_tenders t
        LEFT JOIN users u ON t.bid_submitted_by = u.id
        WHERE t.company_id = ? AND t.is_active = 1
        '''
        params = [company_id]
        
        if status_filter:
            query += " AND t.bid_status = ?"
            params.append(status_filter)
        
        query += " ORDER BY t.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch company tenders: {e}", exc_info=True)
        return pd.DataFrame()


def get_tender_by_id(tender_id: str, company_id: int) -> Optional[Dict]:
    """Get tender by ID as a dictionary"""
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM company_tenders 
                WHERE tender_id = ? AND company_id = ? AND is_active = 1
            """, (tender_id, company_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Error getting tender by ID: {e}")
        return None


def update_tender_bid(tender_id: int, bid_amount: float, updated_by: int) -> bool:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT our_bid_amount FROM company_tenders WHERE id = ?', (tender_id,))
        current = cursor.fetchone()
        
        if current and current[0] is not None and current[0] != bid_amount:
            cursor.execute('SELECT COALESCE(MAX(revision_number), 0) + 1 FROM bid_revisions WHERE tender_id = ?', (tender_id,))
            next_rev = cursor.fetchone()[0]
            
            cursor.execute('''
            INSERT INTO bid_revisions (tender_id, revision_number, bid_amount, revised_by, reason)
            VALUES (?, ?, ?, ?, ?)
            ''', (tender_id, next_rev, bid_amount, updated_by, 'Bid amount updated via UI'))
        
        cursor.execute('''
        UPDATE company_tenders 
        SET our_bid_amount = ?, updated_at = ?
        WHERE id = ?
        ''', (bid_amount, datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender bid: {e}", exc_info=True)
        return False


def submit_bid(tender_id: int, final_bid_amount: float, submitted_by: int) -> bool:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET our_bid_amount = ?, bid_submitted_by = ?, 
            bid_submission_date = ?, bid_status = 'submitted',
            updated_at = ?
        WHERE id = ?
        ''', (final_bid_amount, submitted_by, datetime.now(), datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to submit bid: {e}", exc_info=True)
        return False


def update_tender_result(tender_id: int, winning_bid_amount: float, winning_competitor: str, 
                        our_rank: int, total_bidders: int, award_date: str, bid_status: str) -> bool:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET winning_bid_amount = ?, winning_competitor = ?, our_rank = ?,
            total_bidders = ?, award_date = ?, bid_status = ?,
            evaluation_status = 'completed', updated_at = ?
        WHERE id = ?
        ''', (winning_bid_amount, winning_competitor, our_rank, total_bidders,
              award_date, bid_status, datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        tender_selector_manager.clear_selection()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender result: {e}", exc_info=True)
        return False


def update_competitor_bid(tender_id: str, competitor_name: str, 
                         bid_amount: float, was_winner: bool = False) -> bool:
    try:
        company_id = st.session_state.get('company_id')
        if not company_id:
            return False

        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            
            official_estimate = 1.0
            cursor.execute("SELECT official_estimate FROM company_tenders WHERE tender_id = ?", (tender_id,))
            row = cursor.fetchone()
            if row and row['official_estimate']:
                official_estimate = float(row['official_estimate'])
            
            bid_ratio = bid_amount / official_estimate if official_estimate > 0 else 0.95

            cursor.execute("""
                UPDATE competitor_bid_history 
                SET bid_amount = ?,
                    was_winner = ?,
                    bid_ratio = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tender_id = ? AND competitor_name = ?
            """, (bid_amount, 1 if was_winner else 0, bid_ratio, tender_id, competitor_name))
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO competitor_bid_history 
                    (company_id, competitor_name, tender_id, bid_amount, official_estimate, 
                     bid_ratio, was_winner, bid_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    company_id, competitor_name, tender_id, bid_amount, official_estimate,
                    bid_ratio, 1 if was_winner else 0, datetime.now().date()
                ))
            
            conn.commit()
            db.update_competitor_stats_from_bid(
                company_id=company_id,
                competitor_name=competitor_name,
                bid_ratio=bid_ratio,
                was_winner=was_winner
            )
            return True
            
    except Exception as e:
        print(f"Error in update_competitor_bid: {e}")
        return False


def clear_tender_winner(tender_id: str) -> bool:
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                UPDATE company_tenders 
                SET winning_competitor = NULL, 
                    winning_bid_amount = NULL,
                    evaluation_status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE tender_id = ?
            """, (tender_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error clearing winner for {tender_id}: {e}")
        return False


def delete_tender(tender_id: int, deleted_by: int) -> bool:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET is_active = 0, deleted_at = ?, deleted_by = ?, updated_at = ?
        WHERE id = ?
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            deleted_by,
            datetime.now(),
            tender_id
        ))
        
        conn.commit()
        conn.close()
        tender_selector_manager.clear_selection()
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete tender: {e}", exc_info=True)
        return False

# =============================================================================
# COMPLETE get_tender_team and assign_team_member functions
# =============================================================================

def get_tender_team(tender_id: int) -> List[tuple]:
    """Get team members assigned to a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT u.id, u.full_name, u.role, ta.role as assigned_role, ta.assigned_at
        FROM tender_team_assignments ta
        JOIN users u ON ta.user_id = u.id
        WHERE ta.tender_id = ? AND ta.is_active = 1
        ORDER BY ta.assigned_at DESC
        ''', (tender_id,))
        
        team = cursor.fetchall()
        conn.close()
        return team
        
    except Exception as e:
        logger.error(f"Failed to fetch tender team: {e}", exc_info=True)
        return []


# =============================================================================
# FIXED: assign_team_member - Uses is_active column
# =============================================================================

def assign_team_member(tender_id: int, user_id: int, role: str) -> bool:
    """Assign a team member to a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check for existing active assignment
        cursor.execute('''
        SELECT id FROM tender_team_assignments 
        WHERE tender_id = ? AND user_id = ? AND is_active = 1
        ''', (tender_id, user_id))
        
        if cursor.fetchone():
            conn.close()
            return True  # Already assigned
        
        cursor.execute('''
        INSERT INTO tender_team_assignments (tender_id, user_id, role, assigned_at, is_active)
        VALUES (?, ?, ?, ?, 1)
        ''', (tender_id, user_id, role, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to assign team member: {e}", exc_info=True)
        return False

# =============================================================================
# COMPLETE add_milestone function
# =============================================================================

def add_milestone(tender_id: int, milestone_name: str, due_date: str, 
                 assigned_to: Optional[int], notes: str) -> Optional[int]:
    """Add a milestone/task for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tender_milestones (
            tender_id, milestone_name, due_date, assigned_to, notes, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (tender_id, milestone_name, due_date, assigned_to, notes, datetime.now()))
        
        milestone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return milestone_id
        
    except Exception as e:
        logger.error(f"Failed to add milestone: {e}", exc_info=True)
        return None
# Get tender milestones

def get_tender_milestones(tender_id: int) -> pd.DataFrame:
    """Get milestones for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # The is_active column exists in your table, so use it
        cursor.execute('''
        SELECT m.*, u.full_name as assigned_to_name
        FROM tender_milestones m
        LEFT JOIN users u ON m.assigned_to = u.id
        WHERE m.tender_id = ? AND m.is_active = 1
        ORDER BY m.due_date ASC, m.completed DESC
        ''', (tender_id,))
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch milestones: {e}", exc_info=True)
        return pd.DataFrame()


# =============================================================================
# FIXED: get_all_users - Uses is_active instead of status
# =============================================================================

def get_all_users(company_id: int) -> List[tuple]:
    """Get all users for a company"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Your users table uses is_active, not status
        cursor.execute('''
        SELECT id, username, full_name, email, role, is_active
        FROM users
        WHERE company_id = ? AND is_active = 1
        ORDER BY full_name ASC
        ''', (company_id,))
        
        users = cursor.fetchall()
        conn.close()
        return users
        
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}", exc_info=True)
        return []



def add_bid_revision(tender_id: int, bid_amount: float, revised_by: int, reason: str) -> bool:
    """Add bid revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COALESCE(MAX(revision_number), 0) + 1 FROM bid_revisions WHERE tender_id = ?', (tender_id,))
        next_rev = cursor.fetchone()[0]
        
        cursor.execute('''
        INSERT INTO bid_revisions (tender_id, revision_number, bid_amount, revised_by, reason, revised_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (tender_id, next_rev, bid_amount, revised_by, reason, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to add bid revision: {e}", exc_info=True)
        return False


def get_bid_revisions(tender_id: int) -> List[tuple]:
    """Get bid revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT revision_number, bid_amount, revised_by, reason, revised_at
        FROM bid_revisions 
        WHERE tender_id = ?
        ORDER BY revision_number DESC
        ''', (tender_id,))
        
        revisions = cursor.fetchall()
        conn.close()
        return revisions
        
    except Exception as e:
        logger.error(f"Failed to fetch bid revisions: {e}", exc_info=True)
        return []


def update_tender_lock_status(tender_id: int, locked: bool, locked_by: Optional[int] = None) -> bool:
    """Update the lock status of a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET is_locked = ?, locked_at = ?, locked_by = ?, updated_at = ?
        WHERE id = ?
        ''', (
            1 if locked else 0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if locked else None,
            locked_by,
            datetime.now(),
            tender_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender lock status: {e}", exc_info=True)
        return False

def create_tender_copy(original_tender_id: int, created_by: int) -> Optional[int]:
    """Create a backup copy of a tender with all e-GP fields"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute('PRAGMA table_info(company_tenders)')
        cols = [row[1] for row in cursor.fetchall()]
        
        # Fetch original as dict for safe name-based access
        cursor.execute(f'SELECT {", ".join(cols)} FROM company_tenders WHERE id = ?', (original_tender_id,))
        row = cursor.fetchone()
        if not row: return None
        original = dict(zip(cols, row))
        
        # Prepare insert columns (exclude auto-increment ID)
        insert_cols = [c for c in cols if c != 'id']
        placeholders = ', '.join(['?' for _ in insert_cols])
        
        # Build values list
        values = [original.get(c) for c in insert_cols]
        
        # Helper to safely update values by column name
        def set_val(col_name, new_val):
            if col_name in insert_cols:
                values[insert_cols.index(col_name)] = new_val
        
        # Modify copy-specific fields
        set_val('tender_id', f"{original['tender_id']}_COPY")
        set_val('tender_title', f"{original['tender_title']} (Backup Copy)")
        set_val('is_locked', 0)
        set_val('is_copy', 1)
        set_val('original_tender_id', original_tender_id)
        set_val('created_by', created_by)
        set_val('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        set_val('updated_at', None)
        
        # Reset bid/submission/evaluation fields for the copy
        for field in ['bid_submitted_by', 'bid_status', 'our_bid_amount', 
                      'bid_submission_date', 'evaluation_status', 'winning_bid_amount',
                      'winning_competitor', 'our_rank', 'total_bidders', 'award_date']:
            set_val(field, None)
            
        cursor.execute(f'INSERT INTO company_tenders ({", ".join(insert_cols)}) VALUES ({placeholders})', values)
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_id
        
    except Exception as e:
        logger.error(f"Failed to create tender copy: {e}", exc_info=True)
        return None


# Attach methods to db instance
# =============================================================================
# ATTACH ALL METHODS TO DB INSTANCE
# =============================================================================

# Core CRUD operations
db.create_tender = create_tender
db.get_company_tenders = get_company_tenders
db.update_tender = update_tender
db.delete_tender = delete_tender
db.get_tender_by_id = get_tender_by_id

# Bid operations
db.update_tender_bid = update_tender_bid
db.submit_bid = submit_bid
db.update_tender_result = update_tender_result
db.update_competitor_bid = update_competitor_bid
db.clear_tender_winner = clear_tender_winner

# Team management
db.get_tender_team = get_tender_team
db.assign_team_member = assign_team_member
db.get_all_users = get_all_users

# Milestones
db.add_milestone = add_milestone
db.get_tender_milestones = get_tender_milestones

# Lock and copy
db.update_tender_lock_status = update_tender_lock_status
db.create_tender_copy = create_tender_copy

# Revisions
db.add_bid_revision = add_bid_revision
db.get_bid_revisions = get_bid_revisions


# =============================================================================
# 🎨 E-GP STYLE DASHBOARD
# =============================================================================

def render_tender_dashboard() -> None:
    """Main dashboard with e-GP style table and navigation"""
    
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
    
    # Check if we're viewing a specific tender
    if st.session_state.view_tender_detail:
        _render_tender_detail_page(st.session_state.view_tender_detail)
        return
    
    # Main dashboard
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
    
    # Update stats with JS
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    if not tenders_df.empty:
        total = len(tenders_df)
        active = len(tenders_df[tenders_df['bid_status'] == 'submitted'])
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        win_rate = f"{(won/total*100):.0f}%" if total > 0 else "0%"
        
        st.markdown(f"""
        <script>
        document.getElementById('total-tenders').textContent = '{total}';
        document.getElementById('active-tenders').textContent = '{active}';
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

# =============================================================================
# FIX: Update _render_tender_detail_page function
# =============================================================================

def _render_tender_detail_page_bak(tender_data: Dict[str, Any]):
    """Render e-GP style tender detail page with full options"""
    
    st.markdown("""
    <style>
    .detail-header {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .detail-header h1 {
        color: white;
        margin: 0;
        font-size: 22px;
        font-weight: 600;
    }
    .detail-header .subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    .detail-header .meta-row {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
        margin-top: 12px;
    }
    .detail-header .meta-item {
        background: rgba(255,255,255,0.05);
        padding: 6px 16px;
        border-radius: 8px;
        font-size: 13px;
        color: #94a3b8;
    }
    .detail-header .meta-item strong {
        color: white;
    }
    .detail-tabs {
        background: #1a1a2e;
        padding: 12px 20px;
        border-radius: 10px;
        margin: 15px 0;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link {
        color: #94a3b8;
        text-decoration: none;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 6px;
        transition: all 0.3s;
        cursor: pointer;
    }
    .detail-tabs .tab-link:hover {
        color: white;
        background: rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link.active {
        color: white;
        background: linear-gradient(135deg, #667eea, #764ba2);
    }
    .back-btn {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        padding: 6px 20px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }
    .back-btn:hover {
        background: rgba(102, 126, 234, 0.2) !important;
        color: white !important;
    }
    .action-buttons {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 15px 0;
    }
    .action-buttons .stButton button {
        padding: 8px 20px !important;
        font-size: 14px !important;
        border-radius: 8px !important;
    }
    .action-buttons .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
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
    
    # Back button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Dashboard", key="back_to_dashboard", use_container_width=True):
            st.session_state.view_tender_detail = None
            st.rerun()
    
    # ===== TENDER/PROPOSAL DASHBOARD =====
    st.markdown("---")
    st.markdown("### TENDER/PROPOSAL DASHBOARD")
    
    # Action Buttons Row - All Options
    st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📊 Analysis", use_container_width=True, type="secondary"):
            st.session_state.selected_tender_for_analysis = tender_id
            st.session_state.active_tab = "analysis"
            st.rerun()
    
    with col2:
        if st.button("🏆 Results CRUD", use_container_width=True, type="secondary"):
            st.session_state.selected_tender_for_results = tender_id
            st.session_state.active_tab = "result_crud"
            st.rerun()
    
    with col3:
        if st.button("📥 Import Data", use_container_width=True, type="secondary"):
            st.session_state.selected_tender_for_import = tender_id
            st.session_state.active_tab = "import"
            st.rerun()
    
    with col4:
        if st.button("✏️ Edit Tender", use_container_width=True, type="primary"):
            st.session_state.edit_tender_id = tender_data.get('id')
            st.session_state.extracted_data = tender_data
            st.session_state.edit_mode = True
            st.session_state.active_tab = "edit"
            st.rerun()
    
    with col5:
        if st.button("📑 Reports", use_container_width=True, type="secondary"):
            st.session_state.selected_tender_for_reports = tender_id
            st.session_state.active_tab = "reports"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Get safe values with proper type conversion
    official_estimate = float(tender_data.get('official_estimate', 0) or 0)
    our_bid = tender_data.get('our_bid_amount')
    if our_bid is None:
        our_bid = 0
    else:
        try:
            our_bid = float(our_bid)
        except (ValueError, TypeError):
            our_bid = 0
    
    total_bidders = tender_data.get('total_bidders')
    if total_bidders is None:
        total_bidders = 'N/A'
    
    our_rank = tender_data.get('our_rank')
    if our_rank is None:
        our_rank = 'N/A'
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Official Estimate",
            f"BDT {official_estimate:,.2f}",
            help="Official Cost Estimate"
        )
    with col2:
        if our_bid > 0:
            st.metric(
                "Our Bid",
                f"BDT {our_bid:,.2f}",
                help="Our submitted bid amount"
            )
        else:
            st.metric(
                "Our Bid",
                "Not Set",
                help="Our submitted bid amount"
            )
    with col3:
        st.metric(
            "Total Bidders",
            total_bidders,
            help="Total number of bidders"
        )
    with col4:
        st.metric(
            "Our Rank",
            our_rank,
            help="Our rank among bidders"
        )
    
    # Detail sections
    tab1, tab2, tab3 = st.tabs(["📋 Tender Information", "🏆 Winner Information", "📊 Bid Analysis"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Basic Information")
            st.info(f"**Tender ID:** {tender_data.get('tender_id', 'N/A')}")
            st.markdown(f"**Title:** {tender_data.get('tender_title', 'N/A')}")
            st.markdown(f"**Procuring Entity:** {tender_data.get('procuring_entity', 'N/A')}")
            st.markdown(f"**Division:** {tender_data.get('division', 'N/A')}")
            st.markdown(f"**District:** {tender_data.get('district', 'N/A')}")
            st.markdown(f"**Procurement Type:** {tender_data.get('procurement_type', 'N/A').upper()}")
            
        with col2:
            st.markdown("#### Financial Information")
            st.info(f"**Official Estimate:** BDT {official_estimate:,.2f}")
            st.markdown(f"**Tender Security:** BDT {float(tender_data.get('tender_security', 0) or 0):,.2f}")
            st.markdown(f"**Document Fee:** BDT {float(tender_data.get('document_fee', 0) or 0):,.2f}")
            if our_bid > 0:
                st.markdown(f"**Our Bid:** BDT {our_bid:,.2f}")
            else:
                st.markdown("**Our Bid:** Not set")
        
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
        with col2:
            pub_date = tender_data.get('tender_publication_date')
            if pub_date:
                try:
                    pub_dt = pd.to_datetime(pub_date)
                    st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
                except:
                    st.markdown(f"**Published:** {pub_date}")
        with col3:
            opening_date = tender_data.get('bid_opening_date')
            if opening_date:
                try:
                    opening_dt = pd.to_datetime(opening_date)
                    st.markdown(f"**Opening Date:** {opening_dt.strftime('%d %b %Y %H:%M')}")
                except:
                    st.markdown(f"**Opening Date:** {opening_date}")
            

    with tab2:
        st.markdown("#### Winner Information")
        
        winner = tender_data.get('winning_competitor')
        winner_amount = tender_data.get('winning_bid_amount')
        if winner_amount:
            try:
                winner_amount = float(winner_amount)
            except (ValueError, TypeError):
                winner_amount = None
        
        if winner:
            st.success(f"🏆 **Winner:** {winner}")
            st.info(f"**Winning Bid Amount:** BDT {winner_amount:,.2f}" if winner_amount else "**Winning Bid Amount:** N/A")
            
            # Calculate NPPI
            if official_estimate > 0 and winner_amount:
                nppi = (winner_amount / official_estimate) * 100
                st.metric("NPPI Factor", f"{nppi:.2f}%")
        else:
            st.warning("No winner declared yet for this tender.")
        
        # Bid history
        st.markdown("#### Bid History")
        try:
            with db.get_connection() as conn:
                cursor = db.db_conn.get_cursor(conn)
                cursor.execute("""
                    SELECT competitor_name, bid_amount, was_winner, bid_date
                    FROM competitor_bid_history
                    WHERE tender_id = ? AND company_id = ?
                    ORDER BY bid_amount ASC
                """, (tender_id, st.session_state.company_id))
                rows = cursor.fetchall()
                if rows:
                    bid_data = [dict(row) for row in rows]
                    df = pd.DataFrame(bid_data)
                    df['bid_amount'] = df['bid_amount'].apply(lambda x: f"BDT {x:,.2f}" if x else "N/A")
                    df['was_winner'] = df['was_winner'].apply(lambda x: "🏆 Winner" if x else "")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No bid history available.")
        except Exception as e:
            st.warning(f"Could not load bid history: {e}")
    
    with tab3:
        st.markdown("#### Bid Analysis")
        st.info("Comprehensive analysis available in the Analysis tab above.")
        
        # Quick stats
        if official_estimate > 0 and our_bid > 0:
            nppi = (our_bid / official_estimate) * 100
            st.metric("Our NPPI", f"{nppi:.2f}%", help="Our bid as percentage of OCE")
            
            if nppi < 85:
                st.warning("⚠️ Your bid is significantly below OCE. This may trigger SLT scrutiny.")
            elif nppi > 105:
                st.warning("⚠️ Your bid is above OCE. Consider reviewing your pricing.")
            else:
                st.success("✅ Your bid is within a reasonable range.")
        elif official_estimate > 0 and our_bid == 0:
            st.info("💡 Set your bid amount to see NPPI analysis.")
        else:
            st.warning("⚠️ Official Estimate not set. Please update tender with OCE.")
    
    # Footer
    # render_footer()

# =============================================================================
# COMPLETE _render_tender_detail_page with All Tabs
# =============================================================================

def _render_tender_detail_page(tender_data: Dict[str, Any]):
    """Render e-GP style tender detail page with all tabs"""
    
    st.markdown("""
    <style>
    .detail-header {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .detail-header h1 {
        color: white;
        margin: 0;
        font-size: 22px;
        font-weight: 600;
    }
    .detail-header .subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    .detail-header .meta-row {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
        margin-top: 12px;
    }
    .detail-header .meta-item {
        background: rgba(255,255,255,0.05);
        padding: 6px 16px;
        border-radius: 8px;
        font-size: 13px;
        color: #94a3b8;
    }
    .detail-header .meta-item strong {
        color: white;
    }
    .detail-tabs {
        background: #1a1a2e;
        padding: 12px 20px;
        border-radius: 10px;
        margin: 15px 0;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link {
        color: #94a3b8;
        text-decoration: none;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 6px;
        transition: all 0.3s;
        cursor: pointer;
    }
    .detail-tabs .tab-link:hover {
        color: white;
        background: rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link.active {
        color: white;
        background: linear-gradient(135deg, #667eea, #764ba2);
    }
    .back-btn {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        padding: 6px 20px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }
    .back-btn:hover {
        background: rgba(102, 126, 234, 0.2) !important;
        color: white !important;
    }
    .action-buttons {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 15px 0;
    }
    .action-buttons .stButton button {
        padding: 8px 20px !important;
        font-size: 14px !important;
        border-radius: 8px !important;
    }
    .action-buttons .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .edit-section {
        background: #1a1a2e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(102, 126, 234, 0.1);
        margin-top: 15px;
    }
    .edit-section .stButton button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    
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
    tender_db_id = tender_data.get('id')
    tender_id_str = tender_data.get('tender_id', 'N/A')

    # Back button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Dashboard", key=f"back_to_dashboard_{tender_db_id}", use_container_width=True):
            st.session_state.view_tender_detail = None
            st.rerun()

    # ===== TENDER/PROPOSAL DASHBOARD =====
    st.markdown("---")
    st.markdown("### TENDER/PROPOSAL DASHBOARD")
    
    # Get safe values
    official_estimate = float(tender_data.get('official_estimate', 0) or 0)
    our_bid = tender_data.get('our_bid_amount')
    if our_bid is None:
        our_bid = 0
    else:
        try:
            our_bid = float(our_bid)
        except (ValueError, TypeError):
            our_bid = 0
    
    total_bidders = tender_data.get('total_bidders')
    if total_bidders is None:
        total_bidders = 'N/A'
    
    our_rank = tender_data.get('our_rank')
    if our_rank is None:
        our_rank = 'N/A'
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Official Estimate",
            f"BDT {official_estimate:,.2f}",
            help="Official Cost Estimate"
        )
    with col2:
        if our_bid > 0:
            st.metric(
                "Our Bid",
                f"BDT {our_bid:,.2f}",
                help="Our submitted bid amount"
            )
        else:
            st.metric(
                "Our Bid",
                "Not Set",
                help="Our submitted bid amount"
            )
    with col3:
        st.metric(
            "Total Bidders",
            total_bidders,
            help="Total number of bidders"
        )
    with col4:
        st.metric(
            "Our Rank",
            our_rank,
            help="Our rank among bidders"
        )
    
    
    # ===== ALL TABS =====
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Tender Information", 
        "🏆 Winner Information", 
        "📊 Bid Analysis",
        "📊 Analysis Report",
        "🏆 Tender Results CRUD",
        "📥 Import Tender Data",
        "👥 Team & Milestones"  # NEW TAB
    ])



    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Basic Information")
            st.info(f"**Tender ID:** `{tender_data.get('tender_id', 'N/A')}`")
            st.markdown(f"**Title:** {tender_data.get('tender_title', 'N/A')}")
            st.markdown(f"**Procuring Entity:** {tender_data.get('procuring_entity', 'N/A')}")
            st.markdown(f"**Division:** {tender_data.get('division', 'N/A')}")
            st.markdown(f"**District:** {tender_data.get('district', 'N/A')}")
            st.markdown(f"**Procurement Type:** {tender_data.get('procurement_type', 'N/A').upper()}")
            
        with col2:
            st.markdown("#### Financial Information")
            st.info(f"**Official Estimate:** BDT {official_estimate:,.2f}")
            st.markdown(f"**Tender Security:** BDT {float(tender_data.get('tender_security', 0) or 0):,.2f}")
            st.markdown(f"**Document Fee:** BDT {float(tender_data.get('document_fee', 0) or 0):,.2f}")
            if our_bid > 0:
                st.markdown(f"**Our Bid:** BDT {our_bid:,.2f}")
            else:
                st.markdown("**Our Bid:** Not set")
        
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
        with col2:
            pub_date = tender_data.get('tender_publication_date')
            if pub_date:
                try:
                    pub_dt = pd.to_datetime(pub_date)
                    st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
                except:
                    st.markdown(f"**Published:** {pub_date}")
        with col3:
            opening_date = tender_data.get('bid_opening_date')
            if opening_date:
                try:
                    opening_dt = pd.to_datetime(opening_date)
                    st.markdown(f"**Opening Date:** {opening_dt.strftime('%d %b %Y %H:%M')}")
                except:
                    st.markdown(f"**Opening Date:** {opening_date}")
        
        # ===== ADD TEAM SUMMARY HERE =====
        _add_team_summary_to_information_tab(tender_data)
        
        # ===== EDIT SECTION - USE DATABASE ID FOR KEY =====
        st.markdown("---")
        st.markdown("#### ✏️ Edit Tender")
        if st.button("✏️ Edit This Tender", key=f"edit_tender_{tender_db_id}", use_container_width=True, type="primary"):
            st.session_state.edit_tender_id = tender_db_id
            st.session_state.extracted_data = tender_data
            st.session_state.edit_mode = True
            st.session_state.page = "boq_generator"
            st.rerun()
    
    # ===== TAB 2: WINNER INFORMATION =====
    with tab2:
        st.markdown("#### Winner Information")
        
        winner = tender_data.get('winning_competitor')
        winner_amount = tender_data.get('winning_bid_amount')
        if winner_amount:
            try:
                winner_amount = float(winner_amount)
            except (ValueError, TypeError):
                winner_amount = None
        
        if winner:
            st.success(f"🏆 **Winner:** {winner}")
            st.info(f"**Winning Bid Amount:** BDT {winner_amount:,.2f}" if winner_amount else "**Winning Bid Amount:** N/A")
            
            # Calculate NPPI
            if official_estimate > 0 and winner_amount:
                nppi = (winner_amount / official_estimate) * 100
                st.metric("NPPI Factor", f"{nppi:.2f}%")
        else:
            st.warning("No winner declared yet for this tender.")
            st.info("💡 You can declare a winner in the 'Tender Results CRUD' tab.")
        
        # Bid history
        st.markdown("#### Bid History")
        try:
            with db.get_connection() as conn:
                cursor = db.db_conn.get_cursor(conn)
                cursor.execute("""
                    SELECT competitor_name, bid_amount, was_winner, bid_date
                    FROM competitor_bid_history
                    WHERE tender_id = ? AND company_id = ?
                    ORDER BY bid_amount ASC
                """, (tender_id, st.session_state.company_id))
                rows = cursor.fetchall()
                if rows:
                    bid_data = [dict(row) for row in rows]
                    df = pd.DataFrame(bid_data)
                    df['bid_amount'] = df['bid_amount'].apply(lambda x: f"BDT {x:,.2f}" if x else "N/A")
                    df['was_winner'] = df['was_winner'].apply(lambda x: "🏆 Winner" if x else "")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No bid history available. Import bid data first.")
        except Exception as e:
            st.warning(f"Could not load bid history: {e}")
    
    # ===== TAB 3: BID ANALYSIS (Quick Stats) =====
    with tab3:
        st.markdown("#### Bid Analysis")
        st.info("Comprehensive analysis available in the 'Analysis Report' tab above.")
        
        # Quick stats
        if official_estimate > 0 and our_bid > 0:
            nppi = (our_bid / official_estimate) * 100
            st.metric("Our NPPI", f"{nppi:.2f}%", help="Our bid as percentage of OCE")
            
            if nppi < 85:
                st.warning("⚠️ Your bid is significantly below OCE. This may trigger SLT scrutiny.")
            elif nppi > 105:
                st.warning("⚠️ Your bid is above OCE. Consider reviewing your pricing.")
            else:
                st.success("✅ Your bid is within a reasonable range.")
            
            # Show bid comparison
            st.markdown("#### Bid Comparison")
            try:
                with db.get_connection() as conn:
                    cursor = db.db_conn.get_cursor(conn)
                    cursor.execute("""
                        SELECT competitor_name, bid_amount, was_winner
                        FROM competitor_bid_history
                        WHERE tender_id = ? AND company_id = ?
                        ORDER BY bid_amount ASC
                        LIMIT 10
                    """, (tender_id, st.session_state.company_id))
                    rows = cursor.fetchall()
                    if rows:
                        bid_data = [dict(row) for row in rows]
                        df = pd.DataFrame(bid_data)
                        
                        # Add our bid to comparison
                        our_row = {'competitor_name': '🏢 Our Bid', 'bid_amount': our_bid, 'was_winner': 0}
                        df = pd.concat([df, pd.DataFrame([our_row])], ignore_index=True)
                        df = df.sort_values('bid_amount').reset_index(drop=True)
                        
                        df['bid_amount'] = df['bid_amount'].apply(lambda x: f"BDT {x:,.2f}")
                        df['was_winner'] = df['was_winner'].apply(lambda x: "🏆 Winner" if x else "")
                        
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No competitor data available.")
            except Exception as e:
                st.warning(f"Could not load bid comparison: {e}")
        elif official_estimate > 0 and our_bid == 0:
            st.info("💡 Set your bid amount to see NPPI analysis.")
        else:
            st.warning("⚠️ Official Estimate not set. Please update tender with OCE.")
    
    # ===== TAB 4: ANALYSIS REPORT =====
    with tab4:
        _render_tender_analysis_for_tender(tender_data, tender_id, official_estimate)
    
    # ===== TAB 5: TENDER RESULTS CRUD =====
    with tab5:
        _render_tender_result_crud_for_tender(tender_data, tender_id, official_estimate)
    
    # ===== TAB 6: IMPORT TENDER DATA =====
    with tab6:
        _render_tender_importer_for_tender(tender_data, tender_id, official_estimate)
    
    with tab7:
        _render_team_and_milestones_for_tender(tender_data, tender_id)

    # Footer
    #render_footer()


# =============================================================================
# TAB 4: TENDER ANALYSIS (Full Report)
# =============================================================================

def _render_tender_analysis_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender analysis for a specific tender"""
    
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT • NPPI Analysis • Winner Prediction • Sensitivity*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    if official_estimate <= 0:
        st.warning("⚠️ OCE is required for analysis. Please update the tender with Official Cost Estimate.")
        return
    
    # Load bids
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM competitor_bid_history
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (tender_id, company_id))
            rows = cursor.fetchall()
            bids_df = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching bid history: {str(e)}")
        return
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return
    
    # Summary
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Tender ID", tender_id)
    with col2:
        winner_name = tender_data.get('winning_competitor') or "Not Declared"
        st.metric("Winner", winner_name)
    with col3:
        winner_amount = tender_data.get('winning_bid_amount') or 0
        st.metric("Winning Bid", f"BDT {winner_amount:,.2f}" if winner_amount else "N/A")
    with col4:
        st.metric("OCE", f"BDT {official_estimate:,.2f}" if official_estimate else "Not Set")
    
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
    
    st.markdown("### 🏆 Tender Result CRUD")
    st.caption("Edit bid amounts • Winner selection is **optional**")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return

    st.success(f"✅ Selected: **{tender_data.get('tender_title')}** | OCE: BDT {official_estimate:,.2f}")

    # Load current bids
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT competitor_name, bid_amount, was_winner 
                FROM competitor_bid_history 
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (tender_id, company_id))
            rows = cursor.fetchall()
            bids_data = [dict(row) for row in rows] if rows else []
    except Exception as e:
        st.error(f"Error loading bids: {e}")
        bids_data = []

    if not bids_data:
        st.warning("No bid history found for this tender. Import bid data first.")
        return

    df = pd.DataFrame(bids_data)
    if 'was_winner' not in df.columns:
        df['was_winner'] = False

    st.markdown("#### 📋 Edit Bid Amounts")
    st.caption("**Note:** Selecting a winner is optional. You can save without any winner.")

    # Editable Table
    edited_df = st.data_editor(
        df,
        column_config={
            "competitor_name": st.column_config.TextColumn("Bidder Name", disabled=True),
            "bid_amount": st.column_config.NumberColumn(
                "Bid Amount (BDT)", 
                min_value=0.0, 
                format="%.2f",
                step=1000.0
            ),
            "was_winner": st.column_config.CheckboxColumn(
                "Mark as Winner", 
                default=False,
                help="Only one bidder can be winner"
            )
        },
        hide_index=False,
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
            st.success(f"🏆 Winner: **{w['competitor_name']}** | Bid: BDT {w['bid_amount']:,.2f} | NPPI: **{nppi:.3f}%**")

    # Save Button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True, key=f"save_results_{tender_id}"):
            success_count = 0
            
            for _, row in edited_df.iterrows():
                success = db.update_competitor_bid(
                    tender_id=tender_id,
                    competitor_name=row['competitor_name'],
                    bid_amount=float(row['bid_amount']),
                    was_winner=bool(row['was_winner'])
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
        if st.button("📥 Export Current Bids to CSV", use_container_width=True, key=f"export_{tender_id}"):
            csv = edited_df.to_csv(index=False)
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

def _render_tender_importer_for_tender_bak2(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender data importer for a specific tender with replace option"""
    
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3>📥 Import Tender Opening Report</h3>
        <p style="margin: 0;">Upload Excel file to import competitor bid data</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    st.success(f"✅ Selected: **{tender_data.get('tender_title')}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    # Check if data already exists
    existing_data_count = 0
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT COUNT(*) FROM competitor_bid_history 
                WHERE tender_id = ? AND company_id = ?
            """, (tender_id, company_id))
            existing_data_count = cursor.fetchone()[0]
    except Exception as e:
        st.warning(f"Could not check existing data: {e}")
    
    # Show warning if data exists
    if existing_data_count > 0:
        st.warning(f"⚠️ **{existing_data_count} bid records** already exist for this tender.")
        
        # Replace option
        replace_data = st.checkbox(
            "🔄 Replace existing data (delete current bids and import new)",
            value=False,
            key=f"replace_checkbox_{tender_id}",
            help="If checked, all existing bid data for this tender will be deleted before importing new data."
        )
        
        if replace_data:
            st.error("⚠️ **Warning:** This will delete all existing bid records for this tender. This action cannot be undone!")
    else:
        replace_data = False
        st.info("ℹ️ No existing bid data found for this tender. Import will add new records.")
    
    st.divider()
    st.subheader("Upload Opening Report")
    
    importer = TenderDataImporter(db)
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_uploader_{tender_id}"
    )
    
    if uploaded_file is not None:
        try:
            # Read Excel with header row
            df = pd.read_excel(uploaded_file, header=0)
            
            # Show preview
            st.caption("Preview of parsed data:")
            st.dataframe(df.head(5), use_container_width=True)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report_with_header(df)
            
            if not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Preview table
            display_data = []
            for comp in parsed_data['competitors']:
                display_data.append({
                    'Competitor': comp['name'],
                    'Quoted Amount': f"BDT {comp.get('quoted_amount', 0):,.2f}",
                    'Final Amount': f"BDT {comp.get('final_amount', 0):,.2f}",
                    'Winner': "🏆" if comp.get('is_winner') else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # Check if winner is marked in the data
            has_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
            
            if not has_winner:
                st.info("ℹ️ No winner marked in Excel. The lowest bidder will be used as the winner (optional).")
            
            # Winner selection (optional)
            st.markdown("#### 🏆 Winner Selection")
            st.caption("Select the winner (or leave as lowest bidder). Click 'Skip Winner' if no winner should be declared.")
            
            # Get competitor names
            competitor_names = [comp['name'] for comp in parsed_data['competitors']]
            
            # Find lowest bidder
            lowest_bidder = min(parsed_data['competitors'], key=lambda x: x.get('final_amount', 0))
            default_winner = lowest_bidder['name']
            
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_winner = st.selectbox(
                    "Select Winner (or leave as lowest bidder)",
                    ["-- Skip Winner (No winner declared) --"] + competitor_names,
                    key=f"winner_select_{tender_id}"
                )
            
            with col2:
                if st.button("🏆 Set as Winner", key=f"set_winner_{tender_id}", use_container_width=True):
                    if selected_winner and selected_winner != "-- Skip Winner (No winner declared) --":
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = (comp['name'] == selected_winner)
                        st.success(f"✅ {selected_winner} marked as winner!")
                        st.rerun()
                    else:
                        st.info("ℹ️ No winner selected. You can import without declaring a winner.")
            
            # NPPI Preview
            if official_estimate > 0:
                nppi_data = []
                for comp in parsed_data['competitors']:
                    final_amount = comp.get('final_amount', 0)
                    if final_amount > 0 and official_estimate > 0:
                        nppi_pct = (final_amount / official_estimate) * 100
                        is_winner = "🏆" if comp.get('is_winner') else ""
                        nppi_data.append({
                            'Competitor': comp['name'],
                            'Final Amount': f"BDT {final_amount:,.2f}",
                            'NPPI %': f"{nppi_pct:.2f}%",
                            'Winner': is_winner
                        })
                
                if nppi_data:
                    st.markdown("#### 📊 NPPI Analysis")
                    st.dataframe(pd.DataFrame(nppi_data), use_container_width=True, hide_index=True)
            
            # Import Button with replace option
            col1, col2 = st.columns([2, 1])
            with col1:
                import_label = "🔄 Replace & Import" if replace_data and existing_data_count > 0 else "📥 Import Competitors & Bid Data"
                import_help = "This will delete existing data and import new data" if replace_data else "This will add new bid records"
                
                if st.button(import_label, type="primary", use_container_width=True, key=f"import_{tender_id}", help=import_help):
                    with st.spinner("Importing data into database..."):
                        # Pass replace parameter to importer
                        success, summary = importer.import_tender_data(
                            company_id=company_id,
                            tender_id=tender_id,
                            parsed_data=parsed_data,
                            tender_data=tender_data,
                            replace_existing=replace_data  # Pass replace flag
                        )
                    
                    if success:
                        st.success("✅ Import completed successfully!")
                        st.balloons()
                        tender_selector_manager.clear_selection()
                        if st.button("🔄 Refresh to see imported data", use_container_width=True):
                            st.rerun()
                    else:
                        st.error("❌ Import failed.")
                        if summary.get('errors'):
                            for err in summary['errors']:
                                st.error(err)
            
            with col2:
                if st.button("🔄 Reset Selection", use_container_width=True, key=f"reset_winner_{tender_id}"):
                    for comp in parsed_data['competitors']:
                        comp['is_winner'] = False
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    
    # Help section
    with st.expander("ℹ️ How to use the tender importer"):
        st.markdown("""
        ### 📄 Process Overview
        
        1. **Upload Opening Report**: Upload the Excel file from e-GP
        2. **Review Data**: Check the parsed competitor data
        3. **Select Winner**: Choose the winner (optional)
        4. **Import**: Import competitors and bid history
        
        ### 🔄 Replace Mode
        
        If data already exists for this tender:
        - **Without Replace**: New bid records are added (may create duplicates)
        - **With Replace**: All existing bid data is deleted and replaced with new data
        
        ### 📊 What Gets Imported
        
        - **Competitors**: New competitors added, existing ones updated
        - **Bid History**: All competitor bids recorded
        - **Winner**: Manually selected or skipped
        - **NPPI Factor**: Calculated from winner vs OCE
        
        ### 💡 Tips
        
        - Use **Replace** mode when correcting errors or re-importing corrected data
        - Without Replace, you may create duplicate records
        - Competitor names should be consistent for proper matching
        """)


def _render_tender_detail_page_bak(tender_data: Dict[str, Any]):
    """Render e-GP style tender detail page with Analysis, Results CRUD, and Import tabs"""
    
    st.markdown("""
    <style>
    .detail-header {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .detail-header h1 {
        color: white;
        margin: 0;
        font-size: 22px;
        font-weight: 600;
    }
    .detail-header .subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    .detail-header .meta-row {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
        margin-top: 12px;
    }
    .detail-header .meta-item {
        background: rgba(255,255,255,0.05);
        padding: 6px 16px;
        border-radius: 8px;
        font-size: 13px;
        color: #94a3b8;
    }
    .detail-header .meta-item strong {
        color: white;
    }
    .detail-tabs {
        background: #1a1a2e;
        padding: 12px 20px;
        border-radius: 10px;
        margin: 15px 0;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link {
        color: #94a3b8;
        text-decoration: none;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 6px;
        transition: all 0.3s;
        cursor: pointer;
    }
    .detail-tabs .tab-link:hover {
        color: white;
        background: rgba(102, 126, 234, 0.1);
    }
    .detail-tabs .tab-link.active {
        color: white;
        background: linear-gradient(135deg, #667eea, #764ba2);
    }
    .back-btn {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        padding: 6px 20px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }
    .back-btn:hover {
        background: rgba(102, 126, 234, 0.2) !important;
        color: white !important;
    }
    .action-buttons {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 15px 0;
    }
    .action-buttons .stButton button {
        padding: 8px 20px !important;
        font-size: 14px !important;
        border-radius: 8px !important;
    }
    .action-buttons .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
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
    
    # Back button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Dashboard", key=f"back_to_dashboard_{tender_db_id}", use_container_width=True):
            st.session_state.view_tender_detail = None
            st.rerun()

    
    # ===== TENDER/PROPOSAL DASHBOARD =====
    st.markdown("---")
    st.markdown("### TENDER/PROPOSAL DASHBOARD")
    
    # Get safe values
    official_estimate = float(tender_data.get('official_estimate', 0) or 0)
    our_bid = tender_data.get('our_bid_amount')
    if our_bid is None:
        our_bid = 0
    else:
        try:
            our_bid = float(our_bid)
        except (ValueError, TypeError):
            our_bid = 0
    
    total_bidders = tender_data.get('total_bidders')
    if total_bidders is None:
        total_bidders = 'N/A'
    
    our_rank = tender_data.get('our_rank')
    if our_rank is None:
        our_rank = 'N/A'
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Official Estimate",
            f"BDT {official_estimate:,.2f}",
            help="Official Cost Estimate"
        )
    with col2:
        if our_bid > 0:
            st.metric(
                "Our Bid",
                f"BDT {our_bid:,.2f}",
                help="Our submitted bid amount"
            )
        else:
            st.metric(
                "Our Bid",
                "Not Set",
                help="Our submitted bid amount"
            )
    with col3:
        st.metric(
            "Total Bidders",
            total_bidders,
            help="Total number of bidders"
        )
    with col4:
        st.metric(
            "Our Rank",
            our_rank,
            help="Our rank among bidders"
        )
    
    # ===== THREE TABS =====
    tab1, tab2, tab3 = st.tabs(["📊 Analysis", "🏆 Tender Results CRUD", "📥 Import Tender Data"])
    
    with tab1:
        _render_tender_analysis_for_tender(tender_data, tender_id, official_estimate)
    
    with tab2:
        _render_tender_result_crud_for_tender(tender_data, tender_id, official_estimate)
    
    with tab3:
        _render_tender_importer_for_tender(tender_data, tender_id, official_estimate)
    
    # Footer
    #render_footer()

# =============================================================================
# FIX: Update _render_tenders_table function to use Streamlit buttons properly
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
    .table-header-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        background: #1a1a2e;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1);
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
    </style>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Get filtered tenders
    tenders_df = db.get_company_tenders(company_id)
    
    if tenders_df.empty:
        st.info("📭 No tenders found. Create your first tender entry!")
        return
    
    # Apply filters
    filters = st.session_state.tender_search_filters
    filtered_df = tenders_df.copy()
    
    if filters['procurement_nature'] != 'All':
        filtered_df = filtered_df[filtered_df['procurement_nature'] == filters['procurement_nature']]
    if filters['procurement_type'] != 'All':
        filtered_df = filtered_df[filtered_df['procurement_type'] == filters['procurement_type']]
    if filters['tender_id']:
        filtered_df = filtered_df[filtered_df['tender_id'].str.contains(filters['tender_id'], case=False, na=False)]
    if filters['publishing_date_from']:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['tender_publication_date']) >= pd.to_datetime(filters['publishing_date_from'])]
    if filters['publishing_date_to']:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['tender_publication_date']) <= pd.to_datetime(filters['publishing_date_to'])]
    
    # Header with action buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 📋 Tender/Proposal Search Result")
        st.caption(f"Showing {len(filtered_df)} of {len(tenders_df)} tenders")
    with col2:
        if st.button("➕ Create New Tender", use_container_width=True, type="primary"):
            st.session_state.page = "boq_generator"
            st.rerun()
    
    # Table
    if filtered_df.empty:
        st.info("No tenders match the current filters.")
        return
    
    # Create a container for the table
    with st.container():
        # Prepare table data
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
            
            tender_id = row.get('tender_id', 'N/A')
            title = row.get('tender_title', 'Untitled')
            procuring_entity = row.get('procuring_entity', 'N/A')
            procurement_type = row.get('procurement_type', 'N/A').upper()
            pub_date = row.get('tender_publication_date')
            closing_date = row.get('submission_deadline')
            
            display_data.append({
                'id': row['id'],
                'tender_id': tender_id,
                'title': title,
                'procuring_entity': procuring_entity,
                'procurement_type': procurement_type,
                'status': status,
                'status_display': status_display,
                'status_class': status_class,
                'pub_date': pub_date,
                'closing_date': closing_date
            })
        
        # Display using Streamlit columns (one row at a time with dashboard button)
        for idx, item in enumerate(display_data):
            # Format dates
            pub_date_str = pd.to_datetime(item['pub_date']).strftime('%d-%b-%Y %H:%M:%S') if pd.notna(item['pub_date']) else 'N/A'
            closing_date_str = pd.to_datetime(item['closing_date']).strftime('%d-%b-%Y %H:%M:%S') if pd.notna(item['closing_date']) else 'N/A'
            
            # Use columns to display each row
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 3, 2, 2, 2, 1.2])
            
            with col1:
                st.write(f"{idx + 1}")
            
            with col2:
                st.markdown(f"""
                <div class="tender-id-cell">{item['tender_id']}</div>
                <div class="ref-text">REF: {item['tender_id']}</div>
                <span class="status-badge {item['status_class']}">{item['status_display']}</span>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="tender-title-cell">
                    <span class="title-text">{item['procurement_type']}, {item['title'][:80]}{'...' if len(item['title']) > 80 else ''}</span>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.caption(item['procuring_entity'][:50])
            
            with col5:
                st.write(item['procurement_type'])
                st.caption("LTM")
            
            with col6:
                st.caption(pub_date_str)
                st.caption(closing_date_str)
            
            with col7:
                if st.button("📊", key=f"dash_{item['id']}_{idx}", use_container_width=True):
                    tender_data = get_tender_by_id(item['tender_id'], company_id)
                    if tender_data:
                        # Normalize the data
                        tender_data = _normalize_tender_data(tender_data)
                        st.session_state.view_tender_detail = tender_data
                        st.rerun()
                    else:
                        st.error("Failed to load tender details")
            
            # Add a divider between rows
            st.divider()
    
    # Pagination
    if len(display_data) > 10:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        with col2:
            st.button("« First", use_container_width=True)
        with col3:
            st.button("Go To Page", use_container_width=True)
        with col4:
            st.button("Next »", use_container_width=True)
        with col5:
            st.button("Last »", use_container_width=True)

def _render_tender_analysis_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender analysis for a specific tender"""
    
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT • NPPI Analysis • Winner Prediction • Sensitivity*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    if official_estimate <= 0:
        st.warning("⚠️ OCE is required for analysis. Please update the tender with Official Cost Estimate.")
        return
    
    # Load bids
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM competitor_bid_history
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (tender_id, company_id))
            rows = cursor.fetchall()
            bids_df = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching bid history: {str(e)}")
        return
    
    if bids_df.empty:
        st.warning("No bid history found for this tender. Import bid data first.")
        return
    
    # Summary
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Tender ID", tender_id)
    with col2:
        winner_name = tender_data.get('winning_competitor') or "Not Declared"
        st.metric("Winner", winner_name)
    with col3:
        winner_amount = tender_data.get('winning_bid_amount') or 0
        st.metric("Winning Bid", f"BDT {winner_amount:,.2f}" if winner_amount else "N/A")
    with col4:
        st.metric("OCE", f"BDT {official_estimate:,.2f}" if official_estimate else "Not Set")
    
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
# TAB 2: TENDER RESULTS CRUD
# =============================================================================

def _render_tender_result_crud_for_tender(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender result CRUD for a specific tender"""
    
    st.markdown("### 🏆 Tender Result CRUD")
    st.caption("Edit bid amounts • Winner selection is **optional**")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return

    st.success(f"✅ Selected: **{tender_data.get('tender_title')}** | OCE: BDT {official_estimate:,.2f}")

    # Load current bids
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT competitor_name, bid_amount, was_winner 
                FROM competitor_bid_history 
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (tender_id, company_id))
            rows = cursor.fetchall()
            bids_data = [dict(row) for row in rows] if rows else []
    except Exception as e:
        st.error(f"Error loading bids: {e}")
        bids_data = []

    if not bids_data:
        st.warning("No bid history found for this tender. Import bid data first.")
        return

    df = pd.DataFrame(bids_data)
    if 'was_winner' not in df.columns:
        df['was_winner'] = False

    st.markdown("#### 📋 Edit Bid Amounts")
    st.caption("**Note:** Selecting a winner is optional. You can save without any winner.")

    # Editable Table
    edited_df = st.data_editor(
        df,
        column_config={
            "competitor_name": st.column_config.TextColumn("Bidder Name", disabled=True),
            "bid_amount": st.column_config.NumberColumn(
                "Bid Amount (BDT)", 
                min_value=0.0, 
                format="%.2f",
                step=1000.0
            ),
            "was_winner": st.column_config.CheckboxColumn(
                "Mark as Winner", 
                default=False,
                help="Only one bidder can be winner"
            )
        },
        hide_index=False,
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
            st.success(f"🏆 Winner: **{w['competitor_name']}** | Bid: BDT {w['bid_amount']:,.2f} | NPPI: **{nppi:.3f}%**")

    # Save Button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True, key=f"save_results_{tender_id}"):
            success_count = 0
            
            for _, row in edited_df.iterrows():
                success = db.update_competitor_bid(
                    tender_id=tender_id,
                    competitor_name=row['competitor_name'],
                    bid_amount=float(row['bid_amount']),
                    was_winner=bool(row['was_winner'])
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
        if st.button("📥 Export Current Bids to CSV", use_container_width=True, key=f"export_{tender_id}"):
            csv = edited_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"bid_results_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"download_csv_{tender_id}"
            )


# =============================================================================
# TAB 3: IMPORT TENDER DATA
# =============================================================================
# =============================================================================
# FIX: _render_tender_importer_for_tender - Handle header row and no winner
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
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    st.success(f"✅ Selected: **{tender_data.get('tender_title')}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    # Check if data already exists
    existing_data_count = 0
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT COUNT(*) FROM competitor_bid_history 
                WHERE tender_id = ? AND company_id = ?
            """, (tender_id, company_id))
            existing_data_count = cursor.fetchone()[0]
    except Exception as e:
        st.warning(f"Could not check existing data: {e}")
    
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
    
    importer = TenderDataImporter(db)
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_uploader_{tender_id}"
    )
    
    # Initialize session state for parsed data
    if f"parsed_data_{tender_id}" not in st.session_state:
        st.session_state[f"parsed_data_{tender_id}"] = None
    
    if uploaded_file is not None:
        try:
            # Read Excel with header row
            df = pd.read_excel(uploaded_file, header=0)
            
            # Show preview
            st.caption("Preview of parsed data:")
            st.dataframe(df.head(5), use_container_width=True)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report_with_header(df)
            
            if not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            # Store in session state
            st.session_state[f"parsed_data_{tender_id}"] = parsed_data
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Preview table
            display_data = []
            for comp in parsed_data['competitors']:
                display_data.append({
                    'Competitor': comp['name'],
                    'Quoted Amount': f"BDT {comp.get('quoted_amount', 0):,.2f}",
                    'Final Amount': f"BDT {comp.get('final_amount', 0):,.2f}",
                    'Winner': "🏆" if comp.get('is_winner') else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # ===== WINNER SELECTION SECTION =====
            st.markdown("---")
            st.markdown("#### 🏆 Winner Selection")
            st.caption("Select the winner. Choose 'Skip Winner' if no winner should be declared.")
            
            # Get competitor names
            competitor_names = [comp['name'] for comp in parsed_data['competitors']]
            
            # Find current winner
            current_winner = next((c for c in parsed_data['competitors'] if c.get('is_winner')), None)
            current_winner_name = current_winner['name'] if current_winner else "-- Skip Winner (No winner declared) --"
            
            # Winner selection dropdown
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_winner = st.selectbox(
                    "Select Winner",
                    ["-- Skip Winner (No winner declared) --"] + competitor_names,
                    index=0 if current_winner_name == "-- Skip Winner (No winner declared) --" else competitor_names.index(current_winner_name) + 1,
                    key=f"winner_select_{tender_id}"
                )
            
            with col2:
                if st.button("✅ Apply Winner", key=f"apply_winner_{tender_id}", use_container_width=True):
                    if selected_winner == "-- Skip Winner (No winner declared) --":
                        # Clear winner
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = False
                        parsed_data['winner_info'] = None
                        st.info("ℹ️ No winner selected. All competitors will have was_winner = 0.")
                    else:
                        # Set winner
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = (comp['name'] == selected_winner)
                        winner_comp = next((c for c in parsed_data['competitors'] if c['is_winner']), None)
                        if winner_comp:
                            parsed_data['winner_info'] = {
                                'name': winner_comp['name'],
                                'final_amount': winner_comp['final_amount']
                            }
                        st.success(f"✅ {selected_winner} marked as winner!")
                    
                    # Update session state
                    st.session_state[f"parsed_data_{tender_id}"] = parsed_data
                    st.rerun()
            
            # Show current winner status
            has_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
            if has_winner:
                winner_name = next((c['name'] for c in parsed_data['competitors'] if c.get('is_winner')), None)
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
                            'Competitor': comp['name'],
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
                    tender_selector_manager.clear_selection()
                    
                    # Clear session state
                    if f"parsed_data_{tender_id}" in st.session_state:
                        del st.session_state[f"parsed_data_{tender_id}"]
                    
                    if st.button("🔄 Refresh to see imported data", use_container_width=True):
                        st.rerun()
                else:
                    st.error("❌ Import failed.")
                    if summary.get('errors'):
                        for err in summary['errors']:
                            st.error(err)
        
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
        
def _render_tender_importer_for_tender_bak3(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender data importer for a specific tender"""
    
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3>📥 Import Tender Opening Report</h3>
        <p style="margin: 0;">Upload Excel file to import competitor bid data</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    st.success(f"✅ Selected: **{tender_data.get('tender_title')}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    st.divider()
    st.subheader("Upload Opening Report")
    
    importer = TenderDataImporter(db)
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_uploader_{tender_id}"
    )
    
    if uploaded_file is not None:
        try:
            # Read Excel with header row (skip first row)
            df = pd.read_excel(uploaded_file, header=0)  # Use first row as header
            
            # Debug: Show first few rows
            st.caption("Preview of parsed data:")
            st.dataframe(df.head(5), use_container_width=True)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report_with_header(df)
            
            if not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Preview table
            display_data = []
            for comp in parsed_data['competitors']:
                display_data.append({
                    'Competitor': comp['name'],
                    'Quoted Amount': f"BDT {comp.get('quoted_amount', 0):,.2f}",
                    'Final Amount': f"BDT {comp.get('final_amount', 0):,.2f}",
                    'Winner': "🏆" if comp.get('is_winner') else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # Check if winner is marked in the data
            has_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
            
            if not has_winner:
                st.info("ℹ️ No winner marked in Excel. The lowest bidder will be used as the winner (optional).")
            
            # Winner selection (optional)
            st.markdown("#### 🏆 Winner Selection")
            st.caption("Select the winner (or leave as lowest bidder). Click 'Skip Winner' if no winner should be declared.")
            
            # Get competitor names
            competitor_names = [comp['name'] for comp in parsed_data['competitors']]
            
            # Find lowest bidder
            lowest_bidder = min(parsed_data['competitors'], key=lambda x: x.get('final_amount', 0))
            default_winner = lowest_bidder['name']
            
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_winner = st.selectbox(
                    "Select Winner (or leave as lowest bidder)",
                    ["-- Skip Winner (No winner declared) --"] + competitor_names,
                    key=f"winner_select_{tender_id}"
                )
            
            with col2:
                if st.button("🏆 Set as Winner", key=f"set_winner_{tender_id}", use_container_width=True):
                    if selected_winner and selected_winner != "-- Skip Winner (No winner declared) --":
                        # Update the winner in parsed_data
                        for comp in parsed_data['competitors']:
                            comp['is_winner'] = (comp['name'] == selected_winner)
                        st.success(f"✅ {selected_winner} marked as winner!")
                        st.rerun()
                    else:
                        st.info("ℹ️ No winner selected. You can import without declaring a winner.")
            
            # NPPI Preview
            if official_estimate > 0:
                # Show NPPI for each competitor
                nppi_data = []
                for comp in parsed_data['competitors']:
                    final_amount = comp.get('final_amount', 0)
                    if final_amount > 0 and official_estimate > 0:
                        nppi_pct = (final_amount / official_estimate) * 100
                        is_winner = "🏆" if comp.get('is_winner') else ""
                        nppi_data.append({
                            'Competitor': comp['name'],
                            'Final Amount': f"BDT {final_amount:,.2f}",
                            'NPPI %': f"{nppi_pct:.2f}%",
                            'Winner': is_winner
                        })
                
                if nppi_data:
                    st.markdown("#### 📊 NPPI Analysis")
                    st.dataframe(pd.DataFrame(nppi_data), use_container_width=True, hide_index=True)
            
            # Import Button
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Import Competitors & Bid Data", type="primary", use_container_width=True, key=f"import_{tender_id}"):
                    with st.spinner("Importing data into database..."):
                        # Check if any winner is selected
                        has_selected_winner = any(comp.get('is_winner') for comp in parsed_data['competitors'])
                        
                        # If no winner selected, ensure was_winner = 0 for all
                        if not has_selected_winner:
                            for comp in parsed_data['competitors']:
                                comp['is_winner'] = False
                            st.info("ℹ️ No winner will be marked. All competitors will have was_winner = 0.")
                        
                        success, summary = importer.import_tender_data(
                            company_id=company_id,
                            tender_id=tender_id,
                            parsed_data=parsed_data,
                            tender_data=tender_data
                        )
                    
                    if success:
                        st.success("✅ Import completed successfully!")
                        st.balloons()
                        # Clear shared selector cache
                        tender_selector_manager.clear_selection()
                        if st.button("🔄 Refresh to see imported data", use_container_width=True):
                            st.rerun()
                    else:
                        st.error("❌ Import failed.")
                        if summary.get('errors'):
                            for err in summary['errors']:
                                st.error(err)
            
            with col2:
                if st.button("🔄 Reset Selection", use_container_width=True, key=f"reset_winner_{tender_id}"):
                    # Reset all winners
                    for comp in parsed_data['competitors']:
                        comp['is_winner'] = False
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)    
    
    # Help section
    with st.expander("ℹ️ How to use the tender importer"):
        st.markdown("""
        ### 📄 Process Overview
        
        1. **Upload Opening Report**: Upload the Excel file from e-GP
        2. **Review Data**: Check the parsed competitor data
        3. **Select Winner**: Choose the winner (optional)
        4. **Import**: Import competitors and bid history
        
        ### 📊 What Gets Imported
        
        - **Competitors**: 
          - New competitors are added to the master list
          - Existing competitors are updated with new bid stats
        - **Bid History**: All competitor bids are recorded in `competitor_bid_history`
        - **Winner**: You can select the winner manually (or skip)
        - **NPPI Factor**: Calculated using winner's bid vs OCE from tender
        
        ### 💡 Tips
        
        - Ensure tender has OCE set before importing for NPPI calculation
        - Competitor names should be consistent for proper matching
        - If no winner is selected, all competitors will have `was_winner = 0`
        - You can import opening reports for multiple tenders over time
        """)

def _render_tender_importer_for_tender_bak(tender_data: Dict[str, Any], tender_id: str, official_estimate: float):
    """Render tender data importer for a specific tender"""
    
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3>📥 Import Tender Opening Report</h3>
        <p style="margin: 0;">Upload Excel file to import competitor bid data</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    st.success(f"✅ Selected: **{tender_data.get('tender_title')}**")
    st.caption(f"Tender ID: `{tender_id}` | OCE: BDT {official_estimate:,.2f}")
    
    st.divider()
    st.subheader("Upload Opening Report")
    
    importer = TenderDataImporter(db)
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key=f"opening_report_uploader_{tender_id}"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, header=None)
            
            with st.spinner("Parsing tender opening report..."):
                parsed_data = importer.parse_opening_report(df)
            
            if not parsed_data.get('competitors'):
                st.warning("No competitor data found.")
                return
            
            st.success(f"✅ Parsed {len(parsed_data['competitors'])} competitors")
            
            # Preview table
            display_data = []
            for comp in parsed_data['competitors']:
                display_data.append({
                    'Competitor': comp['name'],
                    'Quoted Amount': f"BDT {comp.get('quoted_amount', 0):,.2f}",
                    'Final Amount': f"BDT {comp.get('final_amount', 0):,.2f}",
                    'Winner': "🏆" if comp.get('is_winner') else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # NPPI Preview
            if parsed_data.get('winner_info') and official_estimate > 0:
                winner = parsed_data['winner_info']
                nppi_pct = (winner['final_amount'] / official_estimate) * 100
                st.metric("Calculated NPPI Factor", f"{nppi_pct:.2f}%")
            
            # Import Button
            if st.button("📥 Import Competitors & Bid Data", type="primary", use_container_width=True, key=f"import_{tender_id}"):
                with st.spinner("Importing data into database..."):
                    success, summary = importer.import_tender_data(
                        company_id=company_id,
                        tender_id=tender_id,
                        parsed_data=parsed_data,
                        tender_data=tender_data
                    )
                
                if success:
                    st.success("✅ Import completed successfully!")
                    st.balloons()
                    # Clear shared selector cache
                    tender_selector_manager.clear_selection()
                    if st.button("🔄 Refresh to see imported data", use_container_width=True):
                        st.rerun()
                else:
                    st.error("❌ Import failed.")
                    if summary.get('errors'):
                        for err in summary['errors']:
                            st.error(err)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)    
    
    # Help section
    with st.expander("ℹ️ How to use the tender importer"):
        st.markdown("""
        ### 📄 Process Overview
        
        1. **Select Tender**: The current tender is pre-selected
        2. **Upload Opening Report**: Upload the Excel file from e-GP
        3. **Review Data**: Check the parsed competitor data
        4. **Import**: Import competitors and bid history
        
        ### 📊 What Gets Imported
        
        - **Competitors**: 
          - New competitors are added to the master list
          - Existing competitors are updated with new bid stats
        - **Bid History**: All competitor bids are recorded in `competitor_bid_history`
        - **Winner**: Automatically detected (lowest final amount)
        - **NPPI Factor**: Calculated using winner's bid vs OCE from tender
        - **Company Tenders**: Updated with winner and total bidders
        - **Historical Tenders**: Record created/updated for analysis
        
        ### 🔗 Data Linking
        
        - All bid history entries are linked to the selected tender via `tender_id`
        - Competitor stats (total bids, wins, win rate) are automatically updated
        - You can later analyze competitor behavior across multiple tenders
        
        ### 💡 Tips
        
        - Ensure tender has OCE set before importing for NPPI calculation
        - Competitor names should be consistent for proper matching
        - The importer handles both e-GP format and similar opening reports
        - You can import opening reports for multiple tenders over time
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
    """
    # Base values based on historical trends in Bangladesh e-GP
    base_nppi = {
        'works': 0.912,      # Works usually have more competition
        'goods': 0.935,      # Goods tend to be closer to OCE
        'services': 0.908,
        'consultancy': 0.885
    }.get(procurement_type.lower(), 0.92)
    
    # Small variation based on date (market conditions)
    month_adjustment = 0
    if tender_date:
        try:
            dt = datetime.strptime(str(tender_date)[:10], '%Y-%m-%d')
            # Slight seasonal/market fluctuation (±2-3%)
            month_adjustment = (dt.month - 6) * 0.003
        except:
            pass
    
    nppi = base_nppi + month_adjustment
    
    # Realistic bounds according to observed e-GP data
    nppi = max(0.82, min(0.99, nppi))
    
    return round(nppi, 3)


def render_tender_management() -> None:
    """Main tender management entry point"""
    
    render_role_badge()
    st.markdown("---")
    
    if not can_view_tenders():
        st.error("🔒 You don't have permission to view tenders.")
        return
    
    # Initialize view state
    if 'view_tender_detail' not in st.session_state:
        st.session_state.view_tender_detail = None
    
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
    
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    
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
    team = db.get_tender_team(tender_id)
    
    if team:
        st.markdown("**Current Team:**")
        for member in team:
            st.markdown(f"- {member[1]} • {member[3]}")
    
    # Add new member
    st.markdown("**Add Member:**")
    users = db.get_all_users(company_id=st.session_state.company_id)
    user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_member = st.selectbox("Member", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_add_member_{tender_id}")
    with col2:
        role = st.selectbox("Role", ["Bid Manager", "Technical Lead", "Financial", "Legal", "Support"], key=f"{key_prefix}_add_role_{tender_id}")
    with col3:
        if st.button("➕ Add", key=f"{key_prefix}_add_btn_{tender_id}"):
            if new_member != "Select" and new_member in user_options:
                if db.assign_team_member(tender_id, user_options[new_member], role):
                    st.success("Member added!")
                    st.rerun()


def _render_milestones(tender_id: int, key_prefix: str) -> None:
    """Render milestone management UI"""
    milestones = db.get_tender_milestones(tender_id)
    
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
            users = db.get_all_users(company_id=st.session_state.company_id)
            user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
            assigned = st.selectbox("Assign To", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_milestone_assign_{tender_id}")
            notes = st.text_area("Notes", key=f"{key_prefix}_milestone_notes_{tender_id}")
        
        if st.button("Add Milestone", key=f"{key_prefix}_milestone_add_{tender_id}"):
            if name and assigned != "Select":
                assigned_id = user_options[assigned] if assigned in user_options else None
                if db.add_milestone(tender_id, name, due.strftime('%Y-%m-%d'), assigned_id, notes):
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
    team = db.get_tender_team(tender_db_id)
    
    if team and len(team) > 0:
        st.markdown("**Current Team Members:**")
        for member in team:
            # member: (user_id, full_name, user_role, assigned_role, assigned_at)
            if len(member) >= 4:
                full_name = member[1]
                assigned_role = member[3]
                user_role = member[2] if len(member) > 2 else 'user'
                st.markdown(f"- **{full_name}** • {assigned_role} • {user_role}")
    else:
        st.info("No team members assigned yet.")
    
    # Add new member
    st.markdown("**Add Team Member:**")
    users = db.get_all_users(company_id=st.session_state.company_id)
    
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
    
    # ========== MILESTONES SECTION ==========
    st.markdown("#### 🎯 Milestones & Tasks")
    
    # Get current milestones
    milestones = db.get_tender_milestones(tender_db_id)
    
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
                            with db.get_connection() as conn:
                                cursor = db.db_conn.get_cursor(conn)
                                cursor.execute("""
                                    UPDATE tender_milestones 
                                    SET completed = 1, completed_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (m['id'],))
                                conn.commit()
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
            users = db.get_all_users(company_id=st.session_state.company_id)
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


def _add_team_summary_to_information_tab_bak(tender_data: Dict[str, Any]):
    """Add a quick team summary to the information tab"""
    
    tender_db_id = tender_data.get('id')
    if not tender_db_id:
        return
    
    st.markdown("#### 👥 Team Summary")
    team = db.get_tender_team(tender_db_id)
    
    # team is a list of tuples, not a DataFrame
    if team and len(team) > 0:
        team_cols = st.columns(min(4, len(team)))
        for i, member in enumerate(team):
            # member is a tuple: (user_id, full_name, user_role, assigned_role, assigned_at)
            if len(member) >= 4:
                full_name = member[1]
                assigned_role = member[3]
                with team_cols[i % len(team_cols)]:
                    st.info(f"**{assigned_role}**\n\n{full_name}")
    else:
        st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")

# =============================================================================
# FIX: _add_team_summary_to_information_tab - Handle DataFrame properly
# =============================================================================

def _add_team_summary_to_information_tab(tender_data: Dict[str, Any]):
    """Add a quick team summary to the information tab"""
    
    tender_db_id = tender_data.get('id')
    if not tender_db_id:
        return
    
    st.markdown("#### 👥 Team Summary")
    team = db.get_tender_team(tender_db_id)
    
    # Check if team is a DataFrame or list and handle accordingly
    if team is not None:
        # If it's a DataFrame
        if hasattr(team, 'empty'):
            if not team.empty:
                # Display team members from DataFrame
                team_cols = st.columns(min(4, len(team)))
                for i, (_, member) in enumerate(team.iterrows()):
                    full_name = member.get('full_name', 'Unknown')
                    assigned_role = member.get('assigned_role', 'Unknown')
                    with team_cols[i % len(team_cols)]:
                        st.info(f"**{assigned_role}**\n\n{full_name}")
            else:
                st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")
        # If it's a list
        elif isinstance(team, list):
            if len(team) > 0:
                team_cols = st.columns(min(4, len(team)))
                for i, member in enumerate(team):
                    if len(member) >= 4:
                        full_name = member[1]
                        assigned_role = member[3]
                        with team_cols[i % len(team_cols)]:
                            st.info(f"**{assigned_role}**\n\n{full_name}")
            else:
                st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")
        else:
            st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")
    else:
        st.caption("No team members assigned. Go to 'Team & Milestones' tab to add members.")


# =============================================================================
# FIX: _render_team_and_milestones_for_tender - Handle DataFrame properly
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
    team = db.get_tender_team(tender_db_id)
    
    if team and len(team) > 0:
        st.markdown("**Current Team Members:**")
        for member in team:
            # member: (user_id, full_name, user_role, assigned_role, assigned_at)
            if len(member) >= 4:
                full_name = member[1]
                assigned_role = member[3]
                user_role = member[2] if len(member) > 2 else 'user'
                st.markdown(f"- **{full_name}** • {assigned_role} • {user_role}")
    else:
        st.info("No team members assigned yet.")
    
    # Add new member
    st.markdown("**Add Team Member:**")
    users = db.get_all_users(company_id=st.session_state.company_id)
    
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
    
    # ========== MILESTONES SECTION ==========
    st.markdown("#### 🎯 Milestones & Tasks")
    
    # Get current milestones
    milestones = db.get_tender_milestones(tender_db_id)
    
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
                            with db.get_connection() as conn:
                                cursor = db.db_conn.get_cursor(conn)
                                cursor.execute("""
                                    UPDATE tender_milestones 
                                    SET completed = 1, completed_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (m['id'],))
                                conn.commit()
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
            users = db.get_all_users(company_id=st.session_state.company_id)
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

# =============================================================================
# FIX: _render_milestone_status_update - Handle DataFrame properly
# =============================================================================

def _render_milestone_status_update(tender_db_id: int):
    """Render a quick milestone status update section"""
    
    milestones = db.get_tender_milestones(tender_db_id)
    
    if milestones is None or not hasattr(milestones, 'empty') or milestones.empty:
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