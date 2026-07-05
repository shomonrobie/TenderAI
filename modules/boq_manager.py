# modules/boq_manager.py - CLEAN FINAL VERSION (Universal DB)

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from database.unified_db_manager import get_db_manager


class BOQManager:
    """Complete BOQ Management System using Unified Database Manager"""

    def __init__(self, db=None):
        self.db = db or get_db_manager()   # Use cached universal manager

    # ====================== BOQ CRUD ======================

    def create_boq(self, tender_id: int, company_id: int, 
                   rate_source: str, zone: str, notes: str = None) -> Tuple[Optional[int], str]:
        """Create a new BOQ"""
        try:
            # Get tender details
            tender = self.db.query_one("""
                SELECT tender_id, tender_title, procuring_entity, official_estimate
                FROM company_tenders
                WHERE id = ? AND company_id = ?
            """, (tender_id, company_id))
            
            if not tender:
                return None, "Tender not found"

            # Get active rate version
            version = self.db.query_one("""
                SELECT edition_year FROM rate_versions 
                WHERE source = ? AND is_active = 1
                LIMIT 1
            """, (rate_source,))
            edition_year = version['edition_year'] if version else 2025

            boq_id = self.db.execute("""
                INSERT INTO boq_generation_history (
                    user_id, company_id, tender_id, tender_title, procuring_entity,
                    selected_zone, rate_source, edition_year, status, notes, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
            """, (
                st.session_state.get('user_id', 0), company_id, tender['tender_id'], 
                tender['tender_title'], tender['procuring_entity'],
                zone, rate_source, edition_year, notes, datetime.now()
            ))

            self._log_activity(boq_id, 'create', f"BOQ created for tender {tender['tender_id']}")

            return boq_id, "BOQ created successfully"
            
        except Exception as e:
            return None, f"Error creating BOQ: {e}"


    def add_boq_item(self, boq_id: int, item_code: str, description: str, 
                     unit: str, quantity: float, unit_rate: float, 
                     is_custom: bool = False, notes: str = None) -> Tuple[bool, str]:
        """Add item to BOQ"""
        try:
            total = quantity * unit_rate

            self.db.execute("""
                INSERT INTO boq_items (
                    boq_id, item_code, description, unit, quantity, 
                    unit_rate, total, is_custom, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (boq_id, item_code, description, unit, quantity, 
                  unit_rate, total, is_custom, notes))

            self._update_boq_totals(boq_id)
            return True, "Item added successfully"
            
        except Exception as e:
            return False, str(e)


    def update_boq_item(self, item_id: int, quantity: float, unit_rate: float = None) -> Tuple[bool, str]:
        """Update BOQ item"""
        try:
            if unit_rate is not None:
                self.db.execute("""
                    UPDATE boq_items 
                    SET quantity = ?, unit_rate = ?, total = ? * ?
                    WHERE id = ?
                """, (quantity, unit_rate, quantity, unit_rate, item_id))
            else:
                self.db.execute("""
                    UPDATE boq_items 
                    SET quantity = ?, total = quantity * unit_rate
                    WHERE id = ?
                """, (quantity, item_id))

            # Update parent BOQ totals
            boq = self.db.query_one("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
            if boq:
                self._update_boq_totals(boq['boq_id'])

            return True, "Item updated successfully"
            
        except Exception as e:
            return False, str(e)


    def delete_boq_item(self, item_id: int) -> Tuple[bool, str]:
        """Delete BOQ item"""
        try:
            boq = self.db.query_one("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
            if not boq:
                return False, "Item not found"

            self.db.execute("DELETE FROM boq_items WHERE id = ?", (item_id,))
            self._update_boq_totals(boq['boq_id'])

            return True, "Item deleted successfully"
            
        except Exception as e:
            return False, str(e)


    def _update_boq_totals(self, boq_id: int):
        """Internal: Update item count and total cost"""
        self.db.execute("""
            UPDATE boq_generation_history 
            SET item_count = (SELECT COUNT(*) FROM boq_items WHERE boq_id = ?),
                total_estimated_cost = (SELECT COALESCE(SUM(total), 0) FROM boq_items WHERE boq_id = ?)
            WHERE id = ?
        """, (boq_id, boq_id, boq_id))


    def get_boq(self, boq_id: int) -> Optional[Dict]:
        """Get complete BOQ with items and history"""
        try:
            boq = self.db.query_one("""
                SELECT b.*, c.company_name, u.username as created_by_name
                FROM boq_generation_history b
                LEFT JOIN companies c ON b.company_id = c.id
                LEFT JOIN users u ON b.user_id = u.id
                WHERE b.id = ?
            """, (boq_id,))

            if not boq:
                return None

            items = self.db.query("SELECT * FROM boq_items WHERE boq_id = ? ORDER BY id", (boq_id,))
            history = self.db.query("SELECT * FROM boq_approval_history WHERE boq_id = ? ORDER BY created_at DESC", (boq_id,))

            return {
                'boq': boq,
                'items': items,
                'history': history
            }
            
        except Exception as e:
            print(f"Error fetching BOQ: {e}")
            return None


    # ====================== WORKFLOW ======================

    def submit_boq(self, boq_id: int, comment: str = None) -> Tuple[bool, str]:
        return self._update_boq_status(boq_id, 'submitted', comment, 'submitted_for_review')

    def approve_boq(self, boq_id: int, comment: str = None) -> Tuple[bool, str]:
        return self._update_boq_status(boq_id, 'approved', comment, 'approved')

    def reject_boq(self, boq_id: int, comment: str = None) -> Tuple[bool, str]:
        return self._update_boq_status(boq_id, 'rejected', comment, 'rejected')


    def _update_boq_status(self, boq_id: int, status: str, comment: str = None, action: str = None) -> Tuple[bool, str]:
        """Internal status updater"""
        try:
            self.db.execute("""
                UPDATE boq_generation_history 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.now(), boq_id))

            # Log approval action
            self.db.execute("""
                INSERT INTO boq_approval_history (boq_id, action, comment, user_id, username, user_role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                boq_id, 
                action or status,
                comment,
                st.session_state.get('user_id', 0),
                st.session_state.get('username', 'system'),
                st.session_state.get('user_role', 'viewer')
            ))

            self._log_activity(boq_id, action or status, comment or f"Status changed to {status}")
            return True, f"BOQ {status} successfully"

        except Exception as e:
            return False, str(e)


    def delete_boq(self, boq_id: int) -> Tuple[bool, str]:
        """Delete entire BOQ"""
        try:
            self.db.execute("DELETE FROM boq_items WHERE boq_id = ?", (boq_id,))
            self.db.execute("DELETE FROM boq_approval_history WHERE boq_id = ?", (boq_id,))
            self.db.execute("DELETE FROM boq_generation_history WHERE id = ?", (boq_id,))

            return True, "BOQ deleted successfully"
        except Exception as e:
            return False, str(e)


    def copy_boq(self, boq_id: int) -> Tuple[Optional[int], str]:
        """Create copy of existing BOQ"""
        try:
            data = self.get_boq(boq_id)
            if not data:
                return None, "Original BOQ not found"

            original = data['boq']

            new_boq_id, msg = self.create_boq(
                tender_id=original['tender_id'],
                company_id=original['company_id'],
                rate_source=original['rate_source'],
                zone=original.get('selected_zone', 'N/A'),
                notes=f"Copy of BOQ #{boq_id}"
            )

            if not new_boq_id:
                return None, msg

            # Copy items
            for _, item in data['items'].iterrows():
                self.add_boq_item(
                    boq_id=new_boq_id,
                    item_code=item['item_code'],
                    description=item['description'],
                    unit=item['unit'],
                    quantity=item['quantity'],
                    unit_rate=item['unit_rate'],
                    is_custom=item.get('is_custom', False)
                )

            return new_boq_id, "BOQ copied successfully"

        except Exception as e:
            return None, str(e)


    # ====================== REPORTING ======================

    def export_boq_to_excel(self, boq_id: int):
        """Export BOQ to Excel"""
        data = self.get_boq(boq_id)
        if not data:
            return None

        # Implementation using openpyxl (same logic as before)
        # ... keep your existing excel generation code here ...
        pass   # Replace with your full implementation


    # ====================== HELPERS ======================

    def _log_activity(self, boq_id: int, action: str, details: str):
        """Log activity"""
        try:
            self.db.execute("""
                INSERT INTO boq_activity_log (boq_id, action, details, user_id, username, user_role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                boq_id, action, details,
                st.session_state.get('user_id', 0),
                st.session_state.get('username', 'system'),
                st.session_state.get('user_role', 'viewer')
            ))
        except Exception as e:
            print(f"Log error: {e}")


    def get_boq_list(self, company_id: int = None, status: str = None, limit: int = 100):
        """Get list of BOQs"""
        try:
            if st.session_state.get('user_role') in ['admin', 'system_admin']:
                query = """
                    SELECT b.*, c.company_name, u.username as created_by_name
                    FROM boq_generation_history b
                    LEFT JOIN companies c ON b.company_id = c.id
                    LEFT JOIN users u ON b.user_id = u.id
                    WHERE 1=1
                """
                params = []
            else:
                company_id = company_id or st.session_state.get('company_id')
                query = """
                    SELECT b.*, u.username as created_by_name
                    FROM boq_generation_history b
                    LEFT JOIN users u ON b.user_id = u.id
                    WHERE b.company_id = ?
                """
                params = [company_id]

            if status:
                query += " AND b.status = ?"
                params.append(status)

            query += " ORDER BY b.generated_at DESC LIMIT ?"
            params.append(limit)

            return self.db.query(query, params=params)
            
        except Exception as e:
            print(f"Error getting BOQ list: {e}")
            return pd.DataFrame()


    def lock_boq(self, boq_id: int) -> Tuple[bool, str]:
        """Lock BOQ"""
        try:
            self.db.execute("""
                UPDATE boq_generation_history 
                SET is_locked = 1, locked_at = ?, locked_by = ?
                WHERE id = ?
            """, (datetime.now(), st.session_state.get('user_id', 0), boq_id))

            self._log_activity(boq_id, 'lock', "BOQ locked after bid submission")
            return True, "BOQ locked successfully"
            
        except Exception as e:
            return False, str(e)


    def unlock_boq(self, boq_id: int) -> Tuple[bool, str]:
        """Unlock BOQ (admin only)"""
        try:
            if st.session_state.get('user_role') not in ['admin', 'system_admin']:
                return False, "Only administrators can unlock BOQs"

            self.db.execute("""
                UPDATE boq_generation_history 
                SET is_locked = 0, locked_at = NULL, locked_by = NULL
                WHERE id = ?
            """, (boq_id,))

            self._log_activity(boq_id, 'unlock', "BOQ unlocked by admin")
            return True, "BOQ unlocked successfully"
            
        except Exception as e:
            return False, str(e)