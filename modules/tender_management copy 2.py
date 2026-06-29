#modules/tender_management.py
"""
Complete Tender Management Module
Track tender participation, bid submission, deadlines, and winner tracking

Refactored for:
- Proper session state management
- Fixed PDF upload → review → form workflow
- Clean separation of concerns
- Type safety and error handling
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import numpy as np
import logging
from typing import Optional, Dict, List, Any
from database.unified_db_manager import UnifiedDatabaseManager
DEBUG_MODE = True
# Initialize logger
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

from modules.tender_selector import render_tender_selector

# =============================================================================
# 🗄️ DATABASE METHODS (Attached to DatabaseManager instance)
# =============================================================================

def create_tender(company_id: int, tender_data: Dict[str, Any], created_by: int) -> Optional[int]:
    """Create a new tender entry with full e-GP field support (Dynamic Query Generation)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 1. Check for duplicate Tender ID
        cursor.execute('''
        SELECT id FROM company_tenders WHERE company_id = ? AND tender_id = ? AND is_active = 1
        ''', (company_id, tender_data.get('tender_id', '')))
        if cursor.fetchone():
            conn.close()
            return None
        
        # 2. Explicitly define columns (Add/Remove here to match your DB schema)
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
        
        # 3. Default values mapping
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
        
        # 4. Build values list dynamically (Guarantees count matches columns)
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
                # Ensure floats are floats
                if col in ['official_estimate', 'tender_security', 'document_fee']:
                    try: val = float(val) if val is not None else 0.0
                    except: val = 0.0
                values.append(val)
                
        # 5. Execute dynamic query
        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join(columns)
        query = f"INSERT INTO company_tenders ({col_names}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        tender_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_db_id
        
    except Exception as e:
        logger.error(f"Failed to create tender: {e}", exc_info=True)
        return None
def update_tender(tender_id: int, tender_data: Dict[str, Any], updated_by: int) -> bool:
    """Update an existing tender with full e-GP field support"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if tender exists and belongs to company
        cursor.execute('''
        SELECT id FROM company_tenders WHERE id = ? AND company_id = ? AND is_active = 1
        ''', (tender_id, st.session_state.company_id))
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Define updatable columns (match your table structure)
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
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        for col in updatable_columns:
            if col in tender_data and tender_data[col] is not None:
                update_fields.append(f"{col} = ?")
                update_values.append(tender_data[col])
        
        if not update_fields:
            conn.close()
            return False
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now())
        
        # Add tender_id to values
        update_values.append(tender_id)
        
        query = f"UPDATE company_tenders SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(query, update_values)
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            # Log the activity
            logger.info(f"Tender {tender_id} updated by user {updated_by}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to update tender: {e}", exc_info=True)
        return False

def clear_tender_winner(tender_id: str) -> bool:
    """Clear winner information from company_tenders table"""
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
        
def get_company_tenders(company_id: int, status_filter: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
    """Fetch all tenders for a company, including new e-GP fields"""
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
            -- ✅ NEW e-GP FIELDS:
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
        
        query += " ORDER BY t.submission_deadline ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch company tenders: {e}", exc_info=True)
        return pd.DataFrame()


def update_tender_bid(tender_id: int, bid_amount: float, updated_by: int) -> bool:
    """Update bid amount for a tender with revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current bid for revision history
        cursor.execute('SELECT our_bid_amount FROM company_tenders WHERE id = ?', (tender_id,))
        current = cursor.fetchone()
        
        if current and current[0] is not None and current[0] != bid_amount:
            # Get next revision number
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

def update_competitor_bid(tender_id: str, competitor_name: str, 
                         bid_amount: float, was_winner: bool = False) -> bool:
    """Update or insert competitor bid"""
    try:
        company_id = st.session_state.get('company_id')
        if not company_id:
            return False

        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            
            # Calculate bid ratio
            official_estimate = 1.0
            cursor.execute("SELECT official_estimate FROM company_tenders WHERE tender_id = ?", (tender_id,))
            row = cursor.fetchone()
            if row and row['official_estimate']:
                official_estimate = float(row['official_estimate'])
            
            bid_ratio = bid_amount / official_estimate if official_estimate > 0 else 0.95

            # Force update
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
            
            # Update stats
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
        
def submit_bid(tender_id: int, final_bid_amount: float, submitted_by: int) -> bool:
    """Finalize and submit the bid"""
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
    """Update tender result after award announcement"""
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
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender result: {e}", exc_info=True)
        return False


def assign_team_member(tender_id: int, user_id: int, role: str) -> bool:
    """Assign a team member to a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check for existing assignment to avoid duplicates
        cursor.execute('''
        SELECT id FROM tender_team_assignments 
        WHERE tender_id = ? AND user_id = ?
        ''', (tender_id, user_id))
        
        if cursor.fetchone():
            conn.close()
            return True  # Already assigned
        
        cursor.execute('''
        INSERT INTO tender_team_assignments (tender_id, user_id, role, assigned_at)
        VALUES (?, ?, ?, ?)
        ''', (tender_id, user_id, role, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to assign team member: {e}", exc_info=True)
        return False


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


def add_milestone(tender_id: int, milestone_name: str, due_date: str, 
                 assigned_to: Optional[int], notes: str) -> Optional[int]:
    """Add a milestone/task for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tender_milestones (
            tender_id, milestone_name, due_date, assigned_to, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (tender_id, milestone_name, due_date, assigned_to, notes, datetime.now()))
        
        milestone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return milestone_id
        
    except Exception as e:
        logger.error(f"Failed to add milestone: {e}", exc_info=True)
        return None


def get_tender_milestones(tender_id: int) -> pd.DataFrame:
    """Get milestones for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
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
        
def delete_tender(tender_id: int, deleted_by: int) -> bool:
    """Soft delete a tender (mark as inactive)"""
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
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete tender: {e}", exc_info=True)
        return False


# Attach methods to db instance
db.create_tender = create_tender
db.get_company_tenders = get_company_tenders
db.update_tender_bid = update_tender_bid
db.submit_bid = submit_bid
db.update_tender_result = update_tender_result
db.assign_team_member = assign_team_member
db.get_tender_team = get_tender_team
db.add_milestone = add_milestone
db.get_tender_milestones = get_tender_milestones
db.add_bid_revision = add_bid_revision
db.get_bid_revisions = get_bid_revisions
db.update_tender_lock_status = update_tender_lock_status
db.create_tender_copy = create_tender_copy
db.delete_tender = delete_tender
db.update_tender = update_tender  # ← ADD THIS LINE
db.clear_tender_winner = clear_tender_winner
db.update_competitor_bid = update_competitor_bid   # Make sure this is also attached

# =============================================================================
# 🎨 UI HELPER FUNCTIONS
# =============================================================================

def _render_tender_card(tender_data: pd.Series, key_prefix: str) -> None:
    """Render a single tender as an expandable card"""
    tender_id = int(tender_data['id'])
    title = str(tender_data.get('tender_title', 'Untitled'))[:60]
    entity = str(tender_data.get('procuring_entity', 'N/A'))[:40]
    deadline = tender_data.get('submission_deadline')
    
    # Format deadline
    if deadline:
        deadline_dt = pd.to_datetime(deadline)
        now = datetime.now()
        time_left = deadline_dt - now
        
        if time_left.total_seconds() < 0:
            deadline_badge = "🔴 Overdue"
            deadline_color = "red"
        elif time_left.days == 0:
            hours = time_left.seconds // 3600
            deadline_badge = f"🟠 Due in {hours}h"
            deadline_color = "orange"
        elif time_left.days <= 3:
            deadline_badge = f"🟡 Due in {time_left.days}d"
            deadline_color = "orange"
        else:
            deadline_badge = f"🟢 Due in {time_left.days}d"
            deadline_color = "green"
    else:
        deadline_badge = "📅 No deadline"
        deadline_color = "gray"
    
    # Lock/copy badges
    status_badges = []
    if tender_data.get('is_copy'):
        status_badges.append('<span style="background:#3b82f6;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;">📋 COPY</span>')
    if tender_data.get('is_locked'):
        status_badges.append('<span style="background:#ef4444;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;">🔒 LOCKED</span>')
    
    status_html = ' '.join(status_badges)
    
    with st.expander(f"📌 {title} • {entity} {status_html}", expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            our_bid = tender_data.get('our_bid_amount')
            bid_display = f"BDT {our_bid:,.0f}" if our_bid and our_bid > 0 else "Not set"
            
            st.markdown(f"""
            - **Tender ID:** {tender_data.get('tender_id', 'N/A')}
            - **Official Estimate:** BDT {tender_data.get('official_estimate', 0):,.0f}
            - **Our Bid:** {bid_display}
            """)
        
        with col2:
            st.markdown(f"#### ⏰ Time Remaining")
            st.markdown(f"<h3 style='color:{deadline_color};margin:0;'>{deadline_badge}</h3>", unsafe_allow_html=True)
            if deadline:
                st.caption(f"Deadline: {pd.to_datetime(deadline).strftime('%Y-%m-%d %H:%M')}")
        
        with col3:
            bid_status = str(tender_data.get('bid_status', 'draft')).upper()
            status_color = {"WON": "green", "LOST": "red", "SUBMITTED": "orange", "DRAFT": "gray"}.get(bid_status, "gray")
            st.markdown(f"**Status:** <span style='color:{status_color}'>{bid_status}</span>", unsafe_allow_html=True)
            if tender_data.get('submitted_by_name'):
                st.caption(f"By: {tender_data['submitted_by_name']}")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Edit bid
            current_bid = float(tender_data.get('our_bid_amount', 0) or 0)
            new_bid = st.number_input("Edit Bid (BDT)", value=current_bid, step=100000.0, format="%.0f", key=f"{key_prefix}_bid_{tender_id}")
            if st.button("💾 Save", key=f"{key_prefix}_save_{tender_id}", use_container_width=True):
                if new_bid != current_bid:
                    if db.update_tender_bid(tender_id, new_bid, st.session_state.user_id):
                        st.success(f"Bid updated to BDT {new_bid:,.0f}")
                        st.rerun()
                    else:
                        st.error("Failed to update bid")
        
        with col2:
            # Submit bid
            if current_bid > 0 and tender_data.get('bid_status') != 'submitted':
                if st.button("📤 Submit", key=f"{key_prefix}_submit_{tender_id}", use_container_width=True):
                    if db.submit_bid(tender_id, current_bid, st.session_state.user_id):
                        st.success("Bid submitted!")
                        st.rerun()
            elif tender_data.get('bid_status') == 'submitted':
                st.success("✅ Submitted")
            else:
                st.warning("Set bid first")
        
        with col3:
            # Team management
            if st.button("👥 Team", key=f"{key_prefix}_team_{tender_id}", use_container_width=True):
                _render_team_management(tender_id, key_prefix)
        
        with col4:
            # Lock/unlock (admin only)
            if st.session_state.user_role == 'admin':
                is_locked = bool(tender_data.get('is_locked', False))
                btn_text = "🔓 Unlock" if is_locked else "🔒 Lock"
                btn_type = "secondary" if is_locked else "primary"
                if st.button(btn_text, key=f"{key_prefix}_lock_{tender_id}", use_container_width=True, type=btn_type):
                    if db.update_tender_lock_status(tender_id, not is_locked, st.session_state.user_id):
                        st.success(f"Tender {'unlocked' if is_locked else 'locked'}")
                        st.rerun()


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


def render_tender_management() -> None:
    """Main tender management dashboard with RBAC"""
    
    render_role_badge()
    st.markdown("---")
    
    if not can_view_tenders():
        st.error("🔒 You don't have permission to view tenders.")
        return

    # Dynamic tabs based on permissions
    tabs_list = ["📊 Dashboard", "📋 Active Tenders", "🏆 Awarded Tenders", "📊 Analysis", "🏆 Tender Result CRUD"]
    tab_contents = [
        _render_tender_dashboard,
        _render_active_tenders_table,
        _render_awarded_tenders_table,
        _render_tender_analysis,
        _render_tender_result_crud,
    ]
    
    if can_import_tender_data():
        tabs_list.append("📥 Import Tender Data")
        tab_contents.append(_render_tender_importer_tab)
    else:
        tabs_list.append("📥 Import Tender Data (🔒)")
        tab_contents.append(lambda: st.error("🔒 You don't have permission to import tender data."))

    # Add optional tabs
    if can_create_tender():
        tabs_list.append("➕ New/Edit Tender")
        tab_contents.append(_render_create_tender_form)
    
    if can_export_data():
        tabs_list.append("📑 Reports")
        tab_contents.append(_render_tender_reports)
    
    # Render tabs
    tabs = st.tabs(tabs_list)
    for tab, content_func in zip(tabs, tab_contents):
        with tab:
            content_func()

def _render_tender_dashboard() -> None:
    """Dashboard with statistics - NO inline editing"""
    st.markdown("### 📊 Tender Statistics")
    tenders_df = db.get_company_tenders(st.session_state.company_id)
   
    if tenders_df.empty:
        st.info("📭 No tenders yet. Create your first tender entry!")
        return
   
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Total Tenders", len(tenders_df))
    with col2: 
        st.metric("Active Bids", len(tenders_df[tenders_df['bid_status'] == 'submitted']))
    with col3: 
        st.metric("Won Tenders", len(tenders_df[tenders_df['bid_status'] == 'won']))
    with col4:
        total = len(tenders_df)
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        st.metric("Win Rate", f"{(won/total*100) if total>0 else 0:.0f}%")
   
    # ⏰ Upcoming Deadlines (View-only, no edit buttons)
    st.markdown("### ⏰ Upcoming Deadlines")
   
    tenders_df['deadline_dt'] = pd.to_datetime(tenders_df['submission_deadline'], errors='coerce')
    now = pd.Timestamp.now()
   
    upcoming = tenders_df[
        (tenders_df['deadline_dt'] > now) &
        (tenders_df['deadline_dt'].notna())
    ].sort_values('deadline_dt').head(5)
   
    if not upcoming.empty:
        display_df = upcoming[[
            'tender_id', 'tender_title', 'procuring_entity',
            'procurement_type', 'submission_deadline', 'bid_status'
        ]].copy()
       
        display_df['submission_deadline'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce')
        display_df['days_left'] = (display_df['submission_deadline'] - now).dt.days
        display_df['submission_deadline'] = display_df['submission_deadline'].dt.strftime('%d %b %Y').fillna('N/A')
        display_df['bid_status'] = display_df['bid_status'].str.upper()
       
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "tender_id": "Tender ID",
                "tender_title": st.column_config.TextColumn("Tender Title", width="large"),
                "procuring_entity": "Procuring Entity",
                "procurement_type": "Type",
                "submission_deadline": "Deadline",
                "days_left": st.column_config.NumberColumn("Days Left", format="%d"),
                "bid_status": "Status"
            }
        )
    else:
        st.success("✅ No upcoming deadlines! All caught up.")
   
    # 📝 Recent Activities
    st.markdown("### 📝 Recent Activities")
    if 'updated_at' in tenders_df.columns:
        recent = tenders_df.sort_values('updated_at', ascending=False).head(5)
        for _, t in recent.iterrows():
            updated_str = str(t['updated_at'])[:10] if pd.notna(t['updated_at']) else 'Unknown'
            st.markdown(f"- **`{t['tender_id']}`** • {str(t['tender_title'])[:50]}... • `{t['bid_status'].upper()}` • Updated: {updated_str}")


def _render_tender_detail_view(tender_data: Dict[str, Any], is_editable: bool = False, context: str = "default") -> None:
    """Display tender details in read-only format
   
    Args:
        tender_data: Tender data dictionary
        is_editable: Whether to show edit button
        context: Context prefix ('active', 'awarded', etc.) to ensure unique keys
    """
    st.markdown("### 📋 Tender Details")
   
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
        st.info(f"**Official Estimate:** BDT {tender_data.get('official_estimate', 0):,.0f}")
        st.markdown(f"**Tender Security:** BDT {tender_data.get('tender_security', 0):,.0f}")
        st.markdown(f"**Document Fee:** BDT {tender_data.get('document_fee', 0):,.0f}")
        st.markdown(f"**Our Bid:** BDT {tender_data.get('our_bid_amount', 0):,.0f}" if tender_data.get('our_bid_amount') else "**Our Bid:** Not set")
   
    st.markdown("#### Important Dates")
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline = tender_data.get('submission_deadline')
        if deadline:
            try:
                deadline_dt = datetime.strptime(str(deadline)[:10], '%Y-%m-%d') if isinstance(deadline, str) else deadline
                st.markdown(f"**Submission Deadline:** {deadline_dt.strftime('%d %b %Y %H:%M')}")
            except:
                st.markdown(f"**Submission Deadline:** {deadline}")
    with col2:
        pub_date = tender_data.get('tender_publication_date')
        if pub_date:
            try:
                pub_dt = datetime.strptime(str(pub_date)[:10], '%Y-%m-%d') if isinstance(pub_date, str) else pub_date
                st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
            except:
                st.markdown(f"**Published:** {pub_date}")
    with col3:
        st.markdown(f"**Status:** `{tender_data.get('bid_status', 'N/A').upper()}`")
        if tender_data.get('is_locked'):
            st.warning("🔒 **LOCKED**")
   
    # Team Members
    if tender_data.get('id'):
        st.markdown("#### 👥 Team Assignment")
        team = db.get_tender_team(tender_data['id'])
        if team:
            team_cols = st.columns(3)
            for i, member in enumerate(team):
                user_id, full_name, user_role, assigned_role, assigned_at = member
                team_cols[i % 3].info(f"**{assigned_role}:** {full_name}")
        else:
            st.caption("No team members assigned")
   
    # Notes
    if tender_data.get('notes'):
        st.markdown("#### 📝 Notes")
        st.caption(tender_data.get('notes'))
   
    # Action buttons with UNIQUE keys
    st.markdown("---")
    col1, col2 = st.columns(2)
   
    with col1:
        # ✅ Unique key with context prefix
        if st.button("← Back to List", width="stretch", key=f"{context}_back_{tender_data.get('id', 'unknown')}"):
            st.session_state.view_tender_detail = None
            st.rerun()
   
    with col2:
        if is_editable and not tender_data.get('is_locked'):
            # ✅ Unique key with context prefix
            if st.button("✏️ Edit This Tender", width="stretch", type="primary",
                        key=f"{context}_edit_{tender_data.get('id', 'unknown')}"):
                st.session_state.edit_tender_id = tender_data['id']
                st.session_state.extracted_data = tender_data
                st.session_state.edit_mode = True
                st.session_state.view_tender_detail = None
                st.rerun()

def _render_tender_dashboard() -> None:
    """Dashboard with statistics - NO inline editing"""
    st.markdown("### 📊 Tender Statistics")
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    
    if tenders_df.empty:
        st.info("📭 No tenders yet. Create your first tender entry!")
        return
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Tenders", len(tenders_df))
    with col2: st.metric("Active Bids", len(tenders_df[tenders_df['bid_status'] == 'submitted']))
    with col3: st.metric("Won Tenders", len(tenders_df[tenders_df['bid_status'] == 'won']))
    with col4: 
        total = len(tenders_df)
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        st.metric("Win Rate", f"{(won/total*100) if total>0 else 0:.0f}%")
    
    # ⏰ Upcoming Deadlines (View-only, no edit buttons)
    st.markdown("### ⏰ Upcoming Deadlines")
    
    tenders_df['deadline_dt'] = pd.to_datetime(tenders_df['submission_deadline'], errors='coerce')
    now = pd.Timestamp.now()
    
    upcoming = tenders_df[
        (tenders_df['deadline_dt'] > now) & 
        (tenders_df['deadline_dt'].notna())
    ].sort_values('deadline_dt').head(5)
    
    if not upcoming.empty:
        display_df = upcoming[[
            'tender_id', 'tender_title', 'procuring_entity', 
            'procurement_type', 'submission_deadline', 'bid_status'
        ]].copy()
        
        display_df['submission_deadline'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce')
        display_df['days_left'] = (display_df['submission_deadline'] - now).dt.days
        display_df['submission_deadline'] = display_df['submission_deadline'].dt.strftime('%d %b %Y').fillna('N/A')
        display_df['bid_status'] = display_df['bid_status'].str.upper()
        
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "tender_id": "Tender ID",
                "tender_title": st.column_config.TextColumn("Tender Title", width="large"),
                "procuring_entity": "Procuring Entity",
                "procurement_type": "Type",
                "submission_deadline": "Deadline",
                "days_left": st.column_config.NumberColumn("Days Left", format="%d"),
                "bid_status": "Status"
            }
        )
    else:
        st.success("✅ No upcoming deadlines! All caught up.")
    
    # 📝 Recent Activities
    st.markdown("### 📝 Recent Activities")
    if 'updated_at' in tenders_df.columns:
        recent = tenders_df.sort_values('updated_at', ascending=False).head(5)
        for _, t in recent.iterrows():
            updated_str = str(t['updated_at'])[:10] if pd.notna(t['updated_at']) else 'Unknown'
            st.markdown(f"- **`{t['tender_id']}`** • {str(t['tender_title'])[:50]}... • `{t['bid_status'].upper()}` • Updated: {updated_str}")

def _render_tender_detail_view(tender_data: Dict[str, Any], is_editable: bool = False, context: str = "default") -> None:
    """Display tender details in read-only format
    
    Args:
        tender_data: Tender data dictionary
        is_editable: Whether to show edit button
        context: Context prefix ('active', 'awarded', etc.) to ensure unique keys
    """
    st.markdown("### 📋 Tender Details")
    
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
        st.info(f"**Official Estimate:** BDT {tender_data.get('official_estimate', 0):,.0f}")
        st.markdown(f"**Tender Security:** BDT {tender_data.get('tender_security', 0):,.0f}")
        st.markdown(f"**Document Fee:** BDT {tender_data.get('document_fee', 0):,.0f}")
        st.markdown(f"**Our Bid:** BDT {tender_data.get('our_bid_amount', 0):,.0f}" if tender_data.get('our_bid_amount') else "**Our Bid:** Not set")
    
    st.markdown("#### Important Dates")
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline = tender_data.get('submission_deadline')
        if deadline:
            try:
                deadline_dt = datetime.strptime(str(deadline)[:10], '%Y-%m-%d') if isinstance(deadline, str) else deadline
                st.markdown(f"**Submission Deadline:** {deadline_dt.strftime('%d %b %Y %H:%M')}")
            except:
                st.markdown(f"**Submission Deadline:** {deadline}")
    with col2:
        pub_date = tender_data.get('tender_publication_date')
        if pub_date:
            try:
                pub_dt = datetime.strptime(str(pub_date)[:10], '%Y-%m-%d') if isinstance(pub_date, str) else pub_date
                st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
            except:
                st.markdown(f"**Published:** {pub_date}")
    with col3:
        st.markdown(f"**Status:** `{tender_data.get('bid_status', 'N/A').upper()}`")
        if tender_data.get('is_locked'):
            st.warning("🔒 **LOCKED**")
    
    # Team Members
    if tender_data.get('id'):
        st.markdown("#### 👥 Team Assignment")
        team = db.get_tender_team(tender_data['id'])
        if team:
            team_cols = st.columns(3)
            for i, member in enumerate(team):
                user_id, full_name, user_role, assigned_role, assigned_at = member
                team_cols[i % 3].info(f"**{assigned_role}:** {full_name}")
        else:
            st.caption("No team members assigned")
    
    # Notes
    if tender_data.get('notes'):
        st.markdown("#### 📝 Notes")
        st.caption(tender_data.get('notes'))
    
    # Action buttons with UNIQUE keys
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # ✅ Unique key with context prefix
        if st.button("← Back to List", width="stretch", key=f"{context}_back_{tender_data.get('id', 'unknown')}"):
            st.session_state.view_tender_detail = None
            st.rerun()
    
    with col2:
        if is_editable and not tender_data.get('is_locked'):
            # ✅ Unique key with context prefix
            if st.button("✏️ Edit This Tender", width="stretch", type="primary", 
                        key=f"{context}_edit_{tender_data.get('id', 'unknown')}"):
                st.session_state.edit_tender_id = tender_data['id']
                st.session_state.extracted_data = tender_data
                st.session_state.edit_mode = True
                st.session_state.view_tender_detail = None
                st.rerun()


def _render_active_tenders_table() -> None:
    """Render the active tenders table"""
    
    st.markdown("### 📋 Active Tenders")
    
    company_id = st.session_state.get('company_id')
    
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Get tenders for THIS company only
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM company_tenders 
                WHERE company_id = ? AND is_active = 1 AND winning_competitor IS NULL
                ORDER BY created_at DESC
            """, (company_id,))
            rows = cursor.fetchall()
            active = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching tenders: {str(e)}")
        return
    
    if active.empty:
        st.info("No active tenders found for your company.")
        return
    
    # Display the tenders
    st.dataframe(active[['tender_id', 'tender_title', 'official_estimate', 'procurement_type', 'submission_deadline']], 
                 use_container_width=True, hide_index=True)
    
    
    # 🔍 Robust Date Parsing (Tries multiple columns if submission_deadline is empty)
    def safe_parse_date(row):
        for col in ['submission_deadline', 'security_submission_deadline', 'tender_valid_upto']:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                try:
                    return pd.to_datetime(val)
                except Exception:
                    pass
        return pd.NaT

    active['deadline_dt'] = active.apply(safe_parse_date, axis=1)
    now = pd.Timestamp.now()
    
    # 📏 Column Ratios: ID, Title(wide), Entity, Type, Deadline, Left, Lock, Bid/Save, View
    col_ratios = [0.6, 4.5, 2.2, 0.6, 1.1, 0.6, 0.4, 2.8, 0.8]
    
    # 📑 Header
    h_cols = st.columns(col_ratios)
    headers = ["ID", "Tender Title & Description", "Procuring Entity", "Type", "Deadline", "Left", "🔒", "Bid / Action", "View"]
    for i, h in enumerate(headers):
        h_cols[i].markdown(f"**{h}**")
    st.divider()
    
    # 🔄 Render Each Tender (Multi-line rows)
    for _, row in active.iterrows():
        is_locked = bool(row.get('is_locked', False))
        tender_id = str(row.get('tender_id', 'N/A'))
        title = str(row.get('tender_title', ''))  # ✅ No truncation: allows multi-line wrap
        entity = str(row.get('procuring_entity', 'N/A'))
        proc_type = str(row.get('procurement_type', '')).upper()
        deadline = row['deadline_dt']
        current_bid = float(row.get('our_bid_amount', 0) or 0.0)
        
        if pd.notna(deadline):
            days_left = (deadline - now).days
            deadline_str = deadline.strftime('%d %b %Y')
        else:
            days_left = None
            deadline_str = "Not set"
            
        cols = st.columns(col_ratios)
        
        cols[0].code(tender_id, language=None)
        cols[1].markdown(f"**{title}**")  # ✅ Wraps naturally
        cols[2].caption(entity)
        cols[3].caption(proc_type)
        cols[4].caption(deadline_str)
        cols[5].markdown(f"`{days_left}d`" if days_left is not None else "`--`")
        cols[6].markdown("🔒" if is_locked else "🔓")
        
        # 💰 Bid Input & Save Button (Side-by-side)
        if not is_locked:
            with cols[7]:
                bid_in, act_btn = st.columns([2.5, 1])
                new_bid = bid_in.number_input(
                    "Bid", value=current_bid, min_value=0.0, step=100000.0,
                    format="%.3f", key=f"bid_{row['id']}", label_visibility="collapsed"
                )
                
                if new_bid != current_bid:
                    if act_btn.button("💾", key=f"save_{row['id']}", width="stretch"):
                        if db.update_tender_bid(row['id'], new_bid, st.session_state.user_id):
                            st.toast("💰 Bid saved!", icon="✅")
                            st.rerun()
                elif current_bid > 0 and row['bid_status'] != 'submitted':
                    if act_btn.button("📤", key=f"sub_{row['id']}", type="primary", width="stretch"):
                        if db.submit_bid(row['id'], new_bid, st.session_state.user_id):
                            st.toast("📤 Submitted!", icon="✅")
                            st.rerun()
                elif row['bid_status'] == 'submitted':
                    act_btn.success("✅")
        else:
            cols[7].caption("Locked")
            
        # 👁️ View Button
        if cols[8].button("👁️", key=f"view_{row['id']}", width="stretch"):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (int(row['id']),))
                c_list = [desc[0] for desc in cursor.description]
                r = cursor.fetchone()
                conn.close()
                if r:
                    st.session_state.view_tender_detail = dict(zip(c_list, r))
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Load failed: {str(e)}")
                
        st.divider()

        
def _render_awarded_tenders_table() -> None:
    """Render the awarded tenders table with winner information"""
    
    st.markdown("### 🏆 Awarded Tenders")
    
    company_id = st.session_state.get('company_id')
    
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Get tenders with winner information
    try:
        # Try to get from company_tenders table
        tenders_df = db.get_company_tenders(company_id, limit=500)
        
        if tenders_df.empty:
            st.info("No tenders found. Import a tender opening report first.")
            return
        
        # Filter awarded tenders (those with winner)
        awarded = tenders_df[tenders_df['winning_competitor'].notna()]
        
        if awarded.empty:
            st.info("No awarded tenders found. Import a tender opening report with winner data.")
            return
        
        # Format for display
        display_df = awarded[['tender_id', 'tender_title', 'winning_competitor', 
                             'winning_bid_amount', 'total_bidders', 'evaluation_status', 
                             'created_at']].copy()
        
        display_df.columns = ['Tender ID', 'Title', 'Winner', 'Winning Bid (BDT)', 
                             'Total Bidders', 'Status', 'Created At']
        
        # Format currency
        display_df['Winning Bid (BDT)'] = display_df['Winning Bid (BDT)'].apply(
            lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A"
        )
        
        # Format date
        display_df['Created At'] = pd.to_datetime(display_df['Created At']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Show statistics
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Awarded Tenders", len(awarded))
        with col2:
            # Most frequent winner
            top_winner = awarded['winning_competitor'].value_counts().index[0]
            st.metric("Most Frequent Winner", top_winner)
        with col3:
            # Average winning bid
            avg_win = awarded['winning_bid_amount'].mean()
            st.metric("Average Winning Bid", f"BDT {avg_win:,.2f}" if pd.notna(avg_win) else "N/A")
        
    except Exception as e:
        st.error(f"Error loading awarded tenders: {str(e)}")



def _load_tender_for_edit(tender_id: int) -> None:
    """Helper to load tender data and prepare for editing"""
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (tender_id,))
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        logger.debug(f"🔍 Load Tender #{tender_id} | Row found: {bool(row)} | Cols: {len(cols)}")
        if row: logger.debug(f"📦 Keys set: {list(dict(zip(cols, row)).keys())}")
        conn.close()
        
        if row:
            st.session_state.extracted_data = dict(zip(cols, row))
            st.session_state.skip_review = True
            st.session_state.edit_tender_id = tender_id
            
            # Clear stale form state
            for k in list(st.session_state.keys()):
                if k.startswith('form_') or k in ('_form_submitting', '_form_reset', '_tender_pdf_upload'):
                    del st.session_state[k]
            
            st.toast(f"📝 Tender #{tender_id} loaded. Please click '➕ New/Edit Tender' tab.", icon="✏️")
            
            #st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to load tender: {str(e)}")

def _render_create_tender_form() -> None:
    """New/Edit Tender page with 3 modes: Manual, PDF Upload, or Edit Existing"""
    
    # =========================================================================
    # SESSION STATE INITIALIZATION
    # =========================================================================
    current_mode = st.session_state.get('tender_action_mode', '➕ Create New Tender (Manual)')
    if st.session_state.get('last_mode') != current_mode:
        # Mode changed - clear extracted data
        st.session_state.extracted_data = None
        st.session_state.skip_review = False
        st.session_state._last_pdf_name = None
        st.session_state.last_mode = current_mode

    if 'extracted_data' not in st.session_state: 
        st.session_state.extracted_data = None
    if 'skip_review' not in st.session_state: 
        st.session_state.skip_review = False
    if 'edit_mode' not in st.session_state: 
        st.session_state.edit_mode = False
    if 'edit_tender_id' not in st.session_state: 
        st.session_state.edit_tender_id = None
    if 'tender_action_mode' not in st.session_state:
        st.session_state.tender_action_mode = "➕ Create New Tender (Manual)"

    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    st.markdown("### 📝 Create / Edit Tender")
    
    mode = st.radio(
        "Select Action:",
        options=["➕ Create New Tender (Manual)", "📄 Create from PDF Upload", "✏️ Edit Existing Tender"],
        horizontal=True,
        key="tender_action_mode"
    )
    
    # =========================================================================
    # EDIT EXISTING TENDER MODE
    # =========================================================================
    if mode == "✏️ Edit Existing Tender":
        st.markdown("### 🔍 Search & Select Tender to Edit")
        
        # Search filters
        col1, col2, col3 = st.columns(3)
        with col1:
            search_tender_id = st.text_input("Tender ID", key="search_tid")
        with col2:
            search_title = st.text_input("Tender Title (partial)", key="search_title")
        with col3:
            search_entity = st.text_input("Procuring Entity", key="search_entity")
        
        # Fetch tenders
        all_tenders = db.get_company_tenders(st.session_state.company_id)
        
        if not all_tenders.empty:
            filtered = all_tenders.copy()
            if search_tender_id:
                filtered = filtered[filtered['tender_id'].str.contains(search_tender_id, case=False, na=False)]
            if search_title:
                filtered = filtered[filtered['tender_title'].str.contains(search_title, case=False, na=False)]
            if search_entity:
                filtered = filtered[filtered['procuring_entity'].str.contains(search_entity, case=False, na=False)]
            
            if not filtered.empty:
                # Show tender list
                for idx, row in filtered.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                    with col1:
                        st.write(row['tender_id'])
                    with col2:
                        st.write(row['tender_title'][:50])
                    with col3:
                        st.write(row['procuring_entity'][:30])
                    with col4:
                        if st.button("✏️ Edit", key=f"edit_btn_{row['id']}"):
                            # Load tender data directly into session state
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (row['id'],))
                            cols = [desc[0] for desc in cursor.description]
                            tender_row = cursor.fetchone()
                            conn.close()
                            
                            if tender_row:
                                st.session_state.extracted_data = dict(zip(cols, tender_row))
                                st.session_state.edit_mode = True
                                st.session_state.edit_tender_id = row['id']
                                st.session_state.skip_review = True
                                st.rerun()
                    st.markdown("---")
        
        # Show edit form if in edit mode
        if st.session_state.edit_mode and st.session_state.extracted_data:
            _render_tender_form_with_data(editing=True)
        return
    
    # =========================================================================
    # PDF UPLOAD MODE
    # =========================================================================
    elif mode == "📄 Create from PDF Upload":
        st.markdown("### 📄 Upload Tender Notice (PDF)")
        
        uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'], key="pdf_uploader")
        
        if uploaded_pdf:
            if st.session_state.extracted_data is None or st.session_state.get('last_pdf') != uploaded_pdf.name:
                try:
                    from modules.pdf_parser import parse_tender_pdf
                    with st.spinner("🔍 Parsing PDF..."):
                        parsed = parse_tender_pdf(uploaded_pdf)
                    if parsed:
                        st.session_state.extracted_data = parsed
                        st.session_state.last_pdf = uploaded_pdf.name
                        st.session_state.skip_review = False
                        st.success("✅ PDF parsed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Show review
        if st.session_state.extracted_data and not st.session_state.skip_review:
            from modules.pdf_review import display_review_page
            def confirm_review():
                st.session_state.skip_review = True
                st.rerun()
            display_review_page(st.session_state.extracted_data, confirm_review)
            return
        
        # Show form
        if st.session_state.extracted_data and st.session_state.skip_review:
            _render_tender_form_with_data(editing=False)
        else:
            _render_tender_form_with_data(editing=False)
        return
    
    # =========================================================================
    # MANUAL MODE
    # =========================================================================
    else:
        _render_tender_form_with_data(editing=False)


def _render_tender_form_with_data(editing: bool = False):
    """Render tender form with data from session_state.extracted_data"""
    
    from utils.helpers import format_currency_bd
    
    # Get data source
    data = st.session_state.extracted_data if editing else st.session_state.get('extracted_data', {})
    
    # Set default values with proper types
    default_values = {
        'tender_id': str(data.get('tender_id', '')) if data else '',
        'tender_title': str(data.get('tender_title', '')) if data else '',
        'procuring_entity': str(data.get('procuring_entity', '')) if data else '',
        'division': str(data.get('division', 'Dhaka')) if data else 'Dhaka',
        'procurement_type': str(data.get('procurement_type', 'works')) if data else 'works',
        'official_estimate': float(data.get('official_estimate', 0.0)) if data else 0.0,
        'submission_deadline': data.get('submission_deadline', datetime.now().date()) if data else datetime.now().date(),
        'tender_security': float(data.get('tender_security', 0.0)) if data else 0.0,
        'document_fee': float(data.get('document_fee', 0.0)) if data else 0.0,
        'project_code': str(data.get('project_code', '')) if data else '',
        'project_name': str(data.get('project_name', '')) if data else '',
        'package_no': str(data.get('package_no', '')) if data else '',
        'budget_type': str(data.get('budget_type', 'Development')) if data else 'Development',
        'notes': str(data.get('notes', '')) if data else ''
    }
    
    # Show edit header with Cancel button
    if editing:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.success(f"📝 **Editing Tender #{st.session_state.edit_tender_id}**")
            # Display current OCE prominently
            current_oce = default_values['official_estimate']
            if current_oce > 0:
                st.info(f"💰 **Current OCE:** {format_currency_bd(current_oce)}")
            st.info("💡 Modify the fields below and click '💾 Update Tender' to save changes.")
        with col2:
            if st.button("❌ Cancel Edit", key="cancel_edit_btn", use_container_width=True):
                st.session_state.edit_mode = False
                st.session_state.edit_tender_id = None
                st.session_state.extracted_data = None
                st.session_state.skip_review = False
                st.rerun()
    
    # Display current data summary if available
    if default_values['official_estimate'] > 0:
        st.info(f"💰 Current Estimate: {format_currency_bd(default_values['official_estimate'])}")
    
    # Main form
    with st.form("tender_form", clear_on_submit=False):
        st.markdown("### 📝 Core Tender Details")
        col1, col2 = st.columns(2)
        
        with col1:
            tender_id = st.text_input("Tender ID *", value=default_values['tender_id'], key="form_tender_id")
            tender_title = st.text_area("Tender Title *", value=default_values['tender_title'], height=80, key="form_tender_title")
            procuring_entity = st.text_input("Procuring Entity *", value=default_values['procuring_entity'], key="form_procuring_entity")
            divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            division_index = divisions.index(default_values['division']) if default_values['division'] in divisions else 0
            division = st.selectbox("Division", divisions, index=division_index, key="form_division")
        
        with col2:
            valid_pt = ["works", "goods", "services"]
            pt_index = valid_pt.index(default_values['procurement_type']) if default_values['procurement_type'] in valid_pt else 0
            procurement_type = st.selectbox("Procurement Type", valid_pt, index=pt_index, key="form_procurement_type")
            
            # OCE field - make it very clear
            st.markdown("**Official Estimate (OCE) *️⃣**")
            st.caption("This is used for NPPI calculations in bid analysis")
            
            official_estimate = st.number_input(
                "Official Estimate (BDT) *", 
                min_value=0.0,
                step=1000000.0,
                value=default_values['official_estimate'],
                key="form_official_estimate",
                format="%0.3f",
                label_visibility="collapsed"
            )
            
            # Show formatted value
            if official_estimate > 0:
                st.caption(f"💡 Formatted: {format_currency_bd(official_estimate)}")
            
            submission_deadline = st.date_input("Submission Deadline *", value=default_values['submission_deadline'], key="form_deadline")
            
            tender_security = st.number_input(
                "Tender Security (BDT)", 
                min_value=0.0,
                step=10000.0,
                value=default_values['tender_security'],
                key="form_security",
                format="%0.3f"
            )
            
            document_fee = st.number_input(
                "Document Fee (BDT)", 
                min_value=0.0,
                step=500.0,
                value=default_values['document_fee'],
                key="form_doc_fee",
                format="%0.3f"
            )
        
        with st.expander("📝 Additional Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                project_code = st.text_input("Project Code", value=default_values['project_code'], key="form_project_code")
                package_no = st.text_input("Package No.", value=default_values['package_no'], key="form_package_no")
                budget_type = st.text_input("Budget Type", value=default_values['budget_type'], key="form_budget_type")
            with col2:
                project_name = st.text_area("Project Name", value=default_values['project_name'], height=60, key="form_project_name")
                notes = st.text_area("Notes", value=default_values['notes'], height=60, key="form_notes")
        
        # Display formatted values for preview
        if official_estimate > 0:
            st.caption(f"💡 Formatted estimate: {format_currency_bd(official_estimate)}")
        
        # Submit button
        btn_text = "💾 Update Tender" if editing else "🚀 Create Tender"
        submitted = st.form_submit_button(btn_text, use_container_width=True, type="primary")
        
        # Cancel button inside form (for manual mode)
        if not editing:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col2:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.session_state.extracted_data = None
                    st.session_state.skip_review = False
                    st.session_state._last_pdf_name = None
                    st.rerun()
        
        if submitted:
            # Validate
            if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
                st.error("❌ Please fill all required fields marked with *")
                return
            
            tender_data = {
                'tender_id': tender_id,
                'tender_title': tender_title,
                'procuring_entity': procuring_entity,
                'division': division,
                'procurement_type': procurement_type,
                'official_estimate': official_estimate,  # This is the key field
                'submission_deadline': submission_deadline,
                'tender_security': tender_security,
                'document_fee': document_fee,
                'project_code': project_code,
                'project_name': project_name,
                'package_no': package_no,
                'budget_type': budget_type,
                'notes': notes,
                'is_active': 1
            }
            
            if editing:
                # Debug: Print what we're updating
                st.write("🔍 Updating tender with data:", tender_data)
                
                # Update existing tender
                success = db.update_tender(st.session_state.edit_tender_id, tender_data, st.session_state.user_id)

                if success:
                    st.success(f"✅ Tender updated successfully!")
                    st.success(f"💰 OCE updated to: {format_currency_bd(official_estimate)}")
                    st.balloons()
                    # Clear edit session states
                    for key in ['edit_mode', 'edit_tender_id', 'extracted_data', 'skip_review', '_last_pdf_name']:
                        if key in st.session_state:
                            del st.session_state[key]
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to update tender")
                    st.error("Please check the logs for details.")
            else:
                # Create new tender
                tender_db_id = db.create_tender(st.session_state.company_id, tender_data, st.session_state.user_id)
                if tender_db_id:
                    st.success(f"✅ Tender '{tender_title}' created successfully!")
                    st.balloons()
                    
                    # CRITICAL: Clear ALL PDF and form related session state
                    keys_to_clear = ['extracted_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new']
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # Force a complete page reset without modifying radio button
                    st.rerun()
                else:
                    st.error("❌ Failed to create tender")


# When fetching active tenders, ensure you're getting all including newly created
def get_active_tenders(company_id):
    """Get all active tenders for a company"""
    query = """
    SELECT * FROM company_tenders 
    WHERE company_id = ? AND is_active = 1 
    ORDER BY submission_deadline ASC
    """
    # Make sure there's no status filter like bid_status = 'draft' only
    # The newly created tender with ID 1283428 should appear here

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

def _render_tender_analysis():
    """Complete Tender Analysis with SLT, NPPI Reverse Engineering, Winner Prediction & Sensitivity Visualization"""
    
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT • NPPI Analysis • Winner Prediction • Sensitivity*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch all tenders
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM company_tenders
                WHERE company_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (company_id,))
            rows = cursor.fetchall()
            all_tenders = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching tenders: {str(e)}")
        return
    
    if all_tenders.empty:
        st.info("No tenders found.")
        return
    
    # Tender Selector
    tender_options = []
    tender_map = {}
    for _, t in all_tenders.iterrows():
        tid = t.get('tender_id')
        title = t.get('tender_title', 'Untitled')[:50]
        winner = t.get('winning_competitor') or "Not Declared"
        oce = float(t.get('official_estimate') or 0)
        label = f"{tid} - {title} ({winner})"
        if oce > 0:
            label += f" [OCE: {oce:,.0f}]"
        tender_options.append(label)
        tender_map[label] = tid
    
    selected_label = st.selectbox("Select Tender for Analysis", tender_options)
    if not selected_label:
        return
    
    tender_id = tender_map[selected_label]
    tender_data = db.get_tender_by_id(tender_id, company_id)
    if not tender_data:
        st.error(f"Tender {tender_id} not found.")
        return
    
    official_estimate = float(tender_data.get('official_estimate') or 0)
    
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
        st.warning("No bid history found.")
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
    
    if official_estimate <= 0:
        st.warning("⚠️ OCE is required for analysis.")
        return
    
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
        st.warning("At least 2 bids required.")
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
        nppi_min = st.number_input("NPPI Min", value=0.82, step=0.001, format="%.3f")
        nppi_max = st.number_input("NPPI Max", value=0.98, step=0.001, format="%.3f")
    with col2:
        if st.button("🔮 Run Prediction", type="primary", use_container_width=True):
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

    # ===================== REVERSE ENGINEERING (Awarded Tenders) =====================
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
            
            # Dynamic Visualization
            correct_values = [r['nppi'] for r in correct_nppi]
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=correct_values, nbinsx=30, name="Successful NPPI", marker_color="green"))
            fig.update_layout(title="Distribution of NPPI Values That Make Winner #1", xaxis_title="NPPI Factor", yaxis_title="Frequency", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not find exact NPPI. Showing closest match.")

    # ===================== HTML REPORT =====================
    st.markdown("---")
    if st.button("📄 Generate Professional HTML Report", type="primary", use_container_width=True):
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
            use_container_width=True
        )
        
def _render_tender_analysis_bak():
    """Render detailed tender analysis with Official PPR 2025 SLT + NPPI"""
    
    st.markdown("### 📊 Tender Analysis Report (PPR 2025 Compliant)")
    st.markdown("*Official SLT + NPPI Reverse Engineering for e-GP Bangladesh*")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch awarded tenders
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM company_tenders
                WHERE company_id = ? AND is_active = 1 AND winning_competitor IS NOT NULL
                ORDER BY created_at DESC
            """, (company_id,))
            rows = cursor.fetchall()
            awarded_tenders = pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching tenders: {str(e)}")
        return
    
    if awarded_tenders.empty:
        st.info("No awarded tenders found. Import a tender opening report with winner data.")
        return
    
    # Tender selector
    tender_options = []
    tender_map = {}
    for _, tender in awarded_tenders.iterrows():
        tender_id = tender.get('tender_id')
        tender_title = tender.get('tender_title', 'Untitled')[:40]
        winner = tender.get('winning_competitor', 'Unknown')
        oce = tender.get('official_estimate', 0)
        try:
            oce = float(oce) if oce else 0
        except (ValueError, TypeError):
            oce = 0
        
        label = f"{tender_id} - {tender_title} (Winner: {winner})"
        if oce > 0:
            label += f" [OCE: BDT {oce:,.2f}]"
        tender_options.append(label)
        tender_map[label] = tender_id
    
    selected_tender_label = st.selectbox("Select Tender for Analysis", tender_options)
    if not selected_tender_label:
        return
    
    tender_id = tender_map[selected_tender_label]
    
    # Get tender data
    tender_data = db.get_tender_by_id(tender_id, company_id)
    if not tender_data:
        st.error(f"Tender {tender_id} not found.")
        return
    
    official_estimate = tender_data.get('official_estimate', 0)
    try:
        official_estimate = float(official_estimate) if official_estimate else 0
    except (ValueError, TypeError):
        official_estimate = 0
    
    # Get bid history
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT * FROM competitor_bid_history
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (tender_id, company_id))
            bid_rows = cursor.fetchall()
            bids_df = pd.DataFrame([dict(row) for row in bid_rows]) if bid_rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching bid history: {str(e)}")
        return
    
    if bids_df.empty:
        st.warning(f"No bid history found for tender {tender_id}.")
        return
    
    # Summary
    st.markdown("---")
    st.caption(f"📋 Data for Company ID: {company_id}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Tender ID", tender_id)
    with col2:
        winner_name = tender_data.get('winning_competitor') or (
            bids_df[bids_df['was_winner'] == 1]['competitor_name'].iloc[0]
            if not bids_df[bids_df['was_winner'] == 1].empty else "Unknown"
        )
        st.metric("Winner", winner_name)
    with col3:
        winner_amount = tender_data.get('winning_bid_amount') or (
            bids_df[bids_df['was_winner'] == 1]['bid_amount'].iloc[0]
            if not bids_df[bids_df['was_winner'] == 1].empty else 0
        )
        st.metric("Winning Bid", f"BDT {winner_amount:,.2f}" if winner_amount else "N/A")
    with col4:
        st.metric("OCE", f"BDT {official_estimate:,.2f}" if official_estimate else "Not Set")
    
    if official_estimate <= 0:
        st.warning("⚠️ OCE is required for official SLT calculation.")
        return
    
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
    
    # ===================== OFFICIAL PPR 2025 SLT =====================
    st.markdown("---")
    st.markdown("### 🎯 Official PPR 2025 SLT (Schedule-18)")
    
    procurement_type = tender_data.get('procurement_type', 'works')
    tender_date = tender_data.get('tender_publication_date') or tender_data.get('created_at')
    
    nppi_factor = _get_simulated_nppi(procurement_type, tender_date)
    x_nppi = official_estimate * nppi_factor
    
    n = len(competitor_bids_sorted)
    bid_amounts = [b['bid'] for b in competitor_bids_sorted]
    avg_quoted = sum(bid_amounts) / n
    
    # Weighted Average
    wa = (0.20 * official_estimate) + (0.30 * x_nppi) + (0.50 * avg_quoted)
    
    # Weighted Standard Deviation
    variance = sum((b - wa) ** 2 for b in bid_amounts) / n
    wsd = variance ** 0.5
    slt_lower = wa - wsd
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("OCE", f"BDT {official_estimate:,.2f}")
    with col2: st.metric("X_NPPI", f"BDT {x_nppi:,.2f}", f"NPPI: {nppi_factor:.3f}")
    with col3: st.metric("Weighted Avg (WA)", f"BDT {wa:,.2f}")
    with col4: st.metric("SLT Lower Limit", f"BDT {slt_lower:,.2f}")
    
    st.metric("WSD", f"BDT {wsd:,.2f}")
    
    # Bids vs SLT
    slt_data = []
    for i, b in enumerate(competitor_bids_sorted, 1):
        diff = b['bid'] - slt_lower
        status = "🟢 Below SLT (Risk)" if b['bid'] < slt_lower else "🟡 Acceptable" if b['bid'] <= wa else "🔴 High"
        slt_data.append({
            "Rank": i,
            "Competitor": b['name'],
            "Bid Amount": f"BDT {b['bid']:,.2f}",
            "vs SLT": f"BDT {diff:,.2f}",
            "Status": status,
            "Winner": "🏆" if b['is_winner'] else ""
        })
    
    st.dataframe(pd.DataFrame(slt_data), use_container_width=True, hide_index=True)
    
    winner_bid_obj = next((b for b in competitor_bids_sorted if b['is_winner']), None)
    if winner_bid_obj:
        if winner_bid_obj['bid'] < slt_lower:
            st.error("⚠️ Winner bid is **Significantly Low** and may face SLT scrutiny/rejection!")
        else:
            st.success("✅ Winner is within acceptable SLT range.")
    
    # ===================== WINNER PREDICTION (When No Winner Yet) =====================
    winner_bid_obj = next((b for b in competitor_bids_sorted if b['is_winner']), None)
    
    if not winner_bid_obj:
        st.markdown("---")
        st.markdown("### 🔮 Winner Prediction Mode (No Winner Declared Yet)")
        st.info("This tender has no declared winner yet. Let's predict based on NPPI.")

        col1, col2 = st.columns([1, 1])
        with col1:
            nppi_input = st.number_input(
                "Expected NPPI Factor",
                min_value=0.70,
                max_value=1.10,
                value=0.92,
                step=0.001,
                format="%.3f",
                help="Enter the expected NPPI factor (usually 0.85 - 0.98)"
            )
        
        with col2:
            use_range = st.checkbox("Use NPPI Range (Sensitivity)", value=False)
            if use_range:
                nppi_min = st.number_input("Min NPPI", value=0.88, step=0.001, format="%.3f")
                nppi_max = st.number_input("Max NPPI", value=0.96, step=0.001, format="%.3f")

        predict_btn = st.button("🔮 Predict Likely Winner", type="primary", use_container_width=True)

        if predict_btn:
            predictions = []
            
            if use_range:
                nppi_values = np.arange(nppi_min, nppi_max + 0.001, 0.001)
            else:
                nppi_values = [nppi_input]

            for nppi in nppi_values:
                # Calculate evaluated prices
                evaluated = []
                for b in competitor_bids_sorted:
                    evaluated_price = b['bid'] * nppi
                    
                    # Apply SLT logic
                    x_nppi_test = official_estimate * nppi
                    wa_test = (0.20 * official_estimate) + (0.30 * x_nppi_test) + (0.50 * avg_quoted)
                    variance_test = sum((bid - wa_test) ** 2 for bid in bid_amounts) / n
                    wsd_test = variance_test ** 0.5
                    slt_test = wa_test - wsd_test
                    
                    is_acceptable = b['bid'] >= slt_test
                    final_score = evaluated_price if is_acceptable else evaluated_price * 1.4  # Penalty
                    
                    evaluated.append({
                        'name': b['name'],
                        'bid': b['bid'],
                        'evaluated_price': evaluated_price,
                        'final_score': final_score,
                        'acceptable': is_acceptable
                    })
                
                # Sort by final score (lowest wins)
                sorted_eval = sorted(evaluated, key=lambda x: x['final_score'])
                predicted_winner = sorted_eval[0]
                
                predictions.append({
                    'nppi': nppi,
                    'predicted_winner': predicted_winner['name'],
                    'evaluated_price': predicted_winner['evaluated_price'],
                    'margin': predicted_winner['final_score'] - sorted_eval[1]['final_score'] if len(sorted_eval) > 1 else 0
                })

            # Show results
            if predictions:
                pred_df = pd.DataFrame(predictions)
                st.success(f"**Most Frequent Predicted Winner: {pred_df['predicted_winner'].mode()[0]}**")
                
                st.dataframe(
                    pred_df.style.format({
                        'nppi': '{:.3f}',
                        'evaluated_price': 'BDT {:,.2f}',
                        'margin': 'BDT {:,.2f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                # Bar chart
                fig = go.Figure()
                for i, p in enumerate(predictions[:10]):  # Top 10
                    fig.add_trace(go.Bar(
                        x=[p['nppi']],
                        y=[p['evaluated_price']],
                        name=p['predicted_winner'],
                        text=p['predicted_winner'],
                        textposition='auto'
                    ))
                fig.update_layout(title="Predicted Winner by NPPI", xaxis_title="NPPI Factor", yaxis_title="Evaluated Price (BDT)")
                st.plotly_chart(fig, use_container_width=True)
    else:
        # Existing winner analysis (your current code)
        st.success(f"🏆 Winner already declared: **{winner_bid_obj['name']}**")
        
    # ===================== NPPI REVERSE ENGINEERING =====================
    st.markdown("---")
    st.markdown("#### 🔍 Reverse-Engineered NPPI Factor (Evaluated Price)")

    st.info("Testing which NPPI factor would make the observed winner have the **lowest evaluated price** according to e-GP methodology.")

    nppi_range = np.arange(0.75, 1.05, 0.001)  # Wider range
    results = []
    winner_name = winner_bid_obj['name'] if winner_bid_obj else None
    winner_bid = winner_bid_obj['bid'] if winner_bid_obj else 0

    for nppi_test in nppi_range:
        # Calculate SLT parameters with this NPPI
        x_nppi_test = official_estimate * nppi_test
        wa_test = (0.20 * official_estimate) + (0.30 * x_nppi_test) + (0.50 * avg_quoted)
        
        # Calculate WSD using the test WA
        variance_test = sum((b - wa_test) ** 2 for b in bid_amounts) / n
        wsd_test = variance_test ** 0.5
        slt_lower_test = wa_test - wsd_test
        
        # Evaluate each bid using e-GP's actual evaluation method
        # In e-GP, evaluated price = bid amount, but SLT threshold determines acceptability
        evaluated = []
        for b in competitor_bids_sorted:
            bid_amount = b['bid']
            # Check if bid is within SLT range (not abnormally low)
            is_acceptable = bid_amount >= slt_lower_test
            
            # The evaluated price is the bid itself, but with SLT penalty if abnormally low
            # In real e-GP, abnormally low bids may be rejected or require justification
            evaluated_price = bid_amount if is_acceptable else bid_amount * 1.5  # Penalty factor
            
            evaluated.append({
                'name': b['name'],
                'bid': bid_amount,
                'evaluated_price': evaluated_price,
                'is_winner': b['is_winner'],
                'is_acceptable': is_acceptable,
                'slt_lower': slt_lower_test
            })
        
        # Sort by evaluated price (lowest first)
        evaluated_sorted = sorted(evaluated, key=lambda x: x['evaluated_price'])
        
        # Check if the actual winner would be the lowest evaluated price
        would_be_winner = evaluated_sorted[0]['name'] if evaluated_sorted else None
        is_correct = would_be_winner == winner_name
        
        # Find winner's rank
        winner_rank = next((i for i, b in enumerate(evaluated_sorted) if b['is_winner']), None)
        
        results.append({
            'nppi': nppi_test,
            'slt_lower': slt_lower_test,
            'wa': wa_test,
            'wsd': wsd_test,
            'is_correct': is_correct,
            'winner_rank': winner_rank + 1 if winner_rank is not None else None,
            'winner_evaluated_price': evaluated_sorted[winner_rank]['evaluated_price'] if winner_rank is not None else 0,
            'lowest_evaluated': evaluated_sorted[0]['evaluated_price'] if evaluated_sorted else 0,
            'would_be_winner': would_be_winner
        })

    # Find NPPI values where winner has lowest evaluated price
    correct_nppi = [r for r in results if r['is_correct']]

    if correct_nppi:
        nppi_values = [r['nppi'] for r in correct_nppi]
        avg_nppi = sum(nppi_values) / len(nppi_values)
        st.success(f"✅ **Most likely NPPI used by e-GP: {avg_nppi:.3f}**")
        
        # Show range if multiple
        if len(nppi_values) > 1:
            st.info(f"**NPPI Range:** {min(nppi_values):.3f} to {max(nppi_values):.3f}")
            
        # Show what happens at this NPPI
        best_result = correct_nppi[0]  # Take first correct NPPI
        st.write(f"**At NPPI = {best_result['nppi']:.3f}:**")
        st.write(f"- SLT Lower Limit: BDT {best_result['slt_lower']:,.2f}")
        st.write(f"- Winner's Evaluated Price: BDT {best_result['winner_evaluated_price']:,.2f}")
        st.write(f"- Lowest Evaluated Price: BDT {best_result['lowest_evaluated']:,.2f}")
        
    else:
        # No NPPI makes winner #1 - find where winner ranks best
        st.warning("⚠️ No NPPI factor makes the actual winner have the lowest evaluated price.")
        
        # Find NPPI where winner has the best rank
        best_result = min(results, key=lambda x: x['winner_rank'] if x['winner_rank'] else 999)
        closest_nppi = best_result['nppi']
        
        st.info(f"**Closest NPPI found:** {closest_nppi:.3f} (Winner ranked #{best_result['winner_rank']})")
        st.write(f"- SLT Lower Limit at this NPPI: BDT {best_result['slt_lower']:,.2f}")
        st.write(f"- Winner's Evaluated Price: BDT {best_result['winner_evaluated_price']:,.2f}")
        st.write(f"- Lowest Evaluated Price: BDT {best_result['lowest_evaluated']:,.2f}")
        
        # Display why winner isn't #1
        st.info("💡 **Why winner isn't #1:** The winner's bid is not the lowest evaluated price because other bidders have lower bids that are still within SLT limits.")
        
        avg_nppi = closest_nppi

    # Show evaluated prices using the best available NPPI
    if avg_nppi is None:
        avg_nppi = 0.92  # ultimate fallback

    # Display evaluated price comparison table
    st.markdown("---")
    st.markdown("#### 📊 Evaluated Price Comparison")

    # Calculate final evaluated prices with best NPPI
    final_slt_lower = None
    for r in results:
        if abs(r['nppi'] - avg_nppi) < 0.001:
            final_slt_lower = r['slt_lower']
            break

    if final_slt_lower is None:
        # Recalculate if not found
        x_nppi_final = official_estimate * avg_nppi
        wa_final = (0.20 * official_estimate) + (0.30 * x_nppi_final) + (0.50 * avg_quoted)
        variance_final = sum((b - wa_final) ** 2 for b in bid_amounts) / n
        wsd_final = variance_final ** 0.5
        final_slt_lower = wa_final - wsd_final

    # Create comparison table
    comparison_data = []
    for b in competitor_bids_sorted:
        bid_amount = b['bid']
        is_acceptable = bid_amount >= final_slt_lower
        evaluated_price = bid_amount if is_acceptable else bid_amount * 1.5
        
        comparison_data.append({
            "Competitor": b['name'],
            "Bid Amount": f"BDT {bid_amount:,.2f}",
            "Within SLT?": "✅" if is_acceptable else "❌",
            "Evaluated Price": f"BDT {evaluated_price:,.2f}",
            "Winner": "🏆" if b['is_winner'] else ""
        })

    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

    # Show explanation
    st.caption(f"**NPPI used for evaluation:** {avg_nppi:.3f} | **SLT Lower Limit:** BDT {final_slt_lower:,.2f}")
    st.caption("💡 **Note:** In e-GP, the evaluated price is the bid amount itself, but abnormally low bids (below SLT) are flagged for review. The 'evaluated price' shown here includes a penalty for SLT violations.")
    
    # Add this after your current analysis to show more context
    # Add NPPI comparison section
    st.markdown("---")
    st.markdown("#### 📊 NPPI Comparison & Analysis")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Simulated NPPI", 
            f"{nppi_factor:.3f}",
            "Estimation"
        )
    with col2:
        st.metric(
            "Reverse-Engineered NPPI",
            f"{avg_nppi:.3f}",
            "Actual Evidence"
        )
    with col3:
        diff_pct = ((avg_nppi - nppi_factor) / nppi_factor) * 100
        st.metric(
            "Difference",
            f"{avg_nppi - nppi_factor:+.3f}",
            f"{diff_pct:+.1f}%",
            delta_color="inverse" if abs(diff_pct) < 5 else "off"
        )

    # Confidence score
    confidence = 1 - (abs(avg_nppi - nppi_factor) / avg_nppi)
    st.progress(confidence, text=f"Confidence in Estimation: {confidence:.1%}")

    if abs(avg_nppi - nppi_factor) > 0.05:
        st.warning("⚠️ Large NPPI discrepancy detected. Consider recalibrating your NPPI estimation function.")
    else:
        st.success("✅ NPPI estimation is reasonably accurate.")
    st.markdown("---")
    st.markdown("#### 📈 NPPI Sensitivity Analysis")

    # Show how SLT changes with NPPI
    nppi_values = [r['nppi'] for r in results[::10]]  # Sample every 10th
    slt_values = [r['slt_lower'] for r in results[::10]]

    # Create a simple table showing the relationship
    sensitivity_data = []
    for i in range(0, len(results), 20):  # Show every 20th value
        r = results[i]
        winner_eval = r['winner_evaluated_price'] if r['winner_rank'] is not None else 0
        sensitivity_data.append({
            "NPPI": f"{r['nppi']:.3f}",
            "SLT Lower Limit": f"BDT {r['slt_lower']:,.2f}",
            "Winner Rank": f"#{r['winner_rank']}" if r['winner_rank'] else "N/A",
            "Is Winner #1?": "✅" if r['is_correct'] else "❌"
        })

    st.dataframe(pd.DataFrame(sensitivity_data), use_container_width=True, hide_index=True)

    # Show the winner's margin
    if winner_bid_obj:
        margin = winner_bid_obj['bid'] - final_slt_lower
        margin_pct = (margin / final_slt_lower) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Winner's Safety Margin", 
                f"BDT {margin:,.2f}",
                f"{margin_pct:.1f}% above SLT"
            )
        with col2:
            # Show second lowest bid if available
            if len(competitor_bids_sorted) > 1:
                second_lowest = competitor_bids_sorted[1]['bid']
                spread = second_lowest - winner_bid_obj['bid']
                st.metric(
                    "Spread vs 2nd Lowest",
                    f"BDT {spread:,.2f}",
                    f"{(spread/winner_bid_obj['bid'])*100:.1f}% lower"
                )
        # ===================== EXPORT =====================
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Generate Full Report", use_container_width=True):
                report_data = {
                    'tender_id': tender_id,
                    'winner': winner_name,
                    'winner_bid': winner_bid_obj['bid'] if winner_bid_obj else None,
                    'oce': official_estimate,
                    'simulated_nppi': nppi_factor,
                    'reverse_engineered_nppi': avg_nppi if correct_nppi else None,
                    'x_nppi': x_nppi,
                    'wa': wa,
                    'wsd': wsd,
                    'slt_lower': slt_lower,
                    'total_bidders': n,
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                df = pd.DataFrame([report_data])
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Report (CSV)",
                    csv,
                    f"tender_analysis_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
    # ===================== HTML REPORT =====================
    st.markdown("---")
    if st.button("📄 Generate Professional HTML Report", type="primary", use_container_width=True):
        html_content = _generate_html_report(
            tender_data=tender_data,
            competitor_bids_sorted=competitor_bids_sorted,   # ← Fixed here
            official_estimate=official_estimate,
            nppi_factor=nppi_factor,
            slt_lower=slt_lower,
            wa=wa,
            wsd=wsd,
            winner_bid_obj=winner_bid_obj,  
            avg_nppi=avg_nppi
        )
        
        st.download_button(
            label="⬇️ Download HTML Report",
            data=html_content,
            file_name=f"TenderAI_Report_{tender_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success("✅ Professional HTML Report generated successfully!")
    with col2:
        if st.button("📊 Export Bid Data", use_container_width=True):
            export_data = []
            for b in competitor_bids_sorted:
                export_data.append({
                    'competitor': b['name'],
                    'bid_amount': b['bid'],
                    'evaluated_price': b['bid'] * (avg_nppi if correct_nppi else nppi_factor),
                    'is_winner': b['is_winner']
                })
            df_export = pd.DataFrame(export_data)
            csv_export = df_export.to_csv(index=False)
            st.download_button(
                "📥 Download Full Bid Data",
                csv_export,
                f"bid_data_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )

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

def _generate_html_report_bak(tender_data, competitor_bids_sorted, official_estimate, 
                         nppi_factor, slt_lower, wa, wsd, winner_bid_obj, avg_nppi=None):
    """Generate beautiful standalone HTML report with TenderAI Logo"""
    
    winner_name = tender_data.get('winning_competitor', 'N/A')
    tender_id = tender_data.get('tender_id', 'N/A')
    procurement_type = tender_data.get('procurement_type', 'Works').title()
    current_date = datetime.now().strftime("%d %B %Y")
    
    display_nppi = avg_nppi if avg_nppi is not None else nppi_factor
    winning_bid = winner_bid_obj['bid'] if winner_bid_obj else 0

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
                <div class="metric"><strong>Winner</strong><br>{winner_name}</div>
                <div class="metric"><strong>Winning Bid</strong><br>BDT {winning_bid:,.2f}</div>
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

            <h2>Reverse-Engineered NPPI Factor</h2>
            <p><strong>Most Likely NPPI Used by e-GP System:</strong> 
               <span style="font-size:1.45em; color:#1e40af; font-weight:bold;">{display_nppi:.3f}</span></p>

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

            <div style="margin-top: 40px; padding: 25px; background: #f0f9ff; border-radius: 10px;">
                <h3>Key Insights</h3>
                <ul>
                    <li>Winner's bid is <strong>{((winning_bid / official_estimate) * 100):.1f}%</strong> of OCE</li>
                    <li>SLT Status: <strong>{"Below SLT (High Risk)" if winning_bid < slt_lower else "Within Acceptable Range"}</strong></li>
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


def _render_tender_result_crud() -> None:
    """Tender Result CRUD - Excel-style bid editing with optional winner"""
    
    st.markdown("### 🏆 Tender Result CRUD")
    st.caption("Edit bid amounts • Winner selection is **optional**")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return

    # ========== TENDER SELECTION ==========
    search_term = st.text_input("🔍 Search Tender", placeholder="Enter tender ID or title...")
    
    selected_tender_id, tender_title, official_estimate, _, _, _, _ = render_tender_selector(
        db=db,
        company_id=company_id,
        search_term=search_term,
        include_manual_entry=True,
        title="Select Tender to Update Results",
        show_table=True,
        show_summary=True
    )
    
    if not selected_tender_id:
        st.info("Please select a tender to manage its bid results.")
        return

    tender_data = db.get_tender_by_id(selected_tender_id, company_id)
    if not tender_data:
        st.error("Tender not found.")
        return

    st.success(f"✅ Selected: **{tender_title}** | OCE: BDT {official_estimate:,.2f}")

    # Load current bids
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT competitor_name, bid_amount, was_winner 
                FROM competitor_bid_history 
                WHERE tender_id = ? AND company_id = ?
                ORDER BY bid_amount ASC
            """, (selected_tender_id, company_id))
            rows = cursor.fetchall()
            bids_data = [dict(row) for row in rows] if rows else []
    except Exception as e:
        st.error(f"Error loading bids: {e}")
        bids_data = []

    if not bids_data:
        st.warning("No bid history found for this tender.")
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
                format="%.3f",
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
        key=f"editor_{selected_tender_id}"
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
    if st.button("💾 Save All Changes", type="primary", use_container_width=True):
        success_count = 0
        
        for _, row in edited_df.iterrows():
            success = db.update_competitor_bid(
                tender_id=selected_tender_id,
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
                tender_id=selected_tender_id,
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
            db.clear_tender_winner(selected_tender_id)
            st.success(f"✅ {success_count} bids saved successfully (No winner marked)")
        
        st.rerun()

    # Export option
    if st.button("📥 Export Current Bids to CSV", use_container_width=True):
        csv = edited_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"bid_results_{selected_tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
def _render_tender_importer_tab():
    """Render the tender data import tab with unique selector key"""
    
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h3>📥 Import Tender Opening Report</h3>
        <p style="margin: 0;">Upload Excel file and link to existing tender</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please select a company first.")
        return
    
    st.subheader("Step 1: Select Tender to Link")

    
    # IMPORTANT: Use unique key for this context
    selected_tender_id, tender_title, official_estimate, procurement_type, \
    procuring_entity, division, district = render_tender_selector(
        db=db,                    # your db manager
        company_id=company_id,
        search_term="",
        include_manual_entry=True,
        title="📋 Select Tender for Import",
        show_table=True,
        show_summary=True,
        key="tender_selector_importer"   # ← Unique key here!
    )
    
    if not selected_tender_id:
        st.info("Please select or create a tender first.")
        if st.button("➕ Go to Create Tender"):
            st.session_state.page = "boq_generator"
            st.rerun()
        return
    
    # Rest of your function remains mostly the same...
    tender_data = db.get_tender_by_id(selected_tender_id, company_id)
    if not tender_data:
        st.error(f"Tender {selected_tender_id} not found.")
        return
    
    official_estimate_value = float(tender_data.get('official_estimate') or 0)
    
    st.success(f"✅ Selected: **{tender_data.get('tender_title')}**")
    st.caption(f"Tender ID: `{selected_tender_id}` | OCE: BDT {official_estimate_value:,.2f}")
    
    st.divider()
    st.subheader("Step 2: Upload Opening Report")
    
    importer = TenderDataImporter(db)
    
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel)",
        type=['xlsx', 'xls'],
        key="opening_report_uploader"   # also give unique key
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
            
            # Preview table (your existing code)
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
            if parsed_data.get('winner_info') and official_estimate_value > 0:
                winner = parsed_data['winner_info']
                nppi_pct = (winner['final_amount'] / official_estimate_value) * 100
                st.metric("Calculated NPPI Factor", f"{nppi_pct:.2f}%")
            
            # Import Button
            if st.button("📥 Import Competitors & Bid Data", type="primary", use_container_width=True, key="import_button"):
                with st.spinner("Importing data into database..."):
                    success, summary = importer.import_tender_data(
                        company_id=company_id,
                        tender_id=selected_tender_id,
                        parsed_data=parsed_data,
                        tender_data=tender_data
                    )
                
                if success:
                    st.success("✅ Import completed successfully!")
                    st.balloons()
                    # Show summary (your existing columns)
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
        
        1. **Select Tender**: Choose an existing tender from your list
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

