# database/crud_boq.py - Fixed version using query/execute methods

"""
CRUD Operations for BOQ (Bill of Quantities) Management
All database operations for BOQ generation, items, and history
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class BOQCRUD:
    """BOQ-specific CRUD operations using query/execute methods"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get the database manager"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()
    
    # =========================================================================
    # RATE BOOK METHODS - Using query/execute
    # =========================================================================
    
    def get_company_rate_books(self, company_id: int) -> List[Dict]:
        """Get all rate books for a company"""
        db = self._get_db()
        
        # ✅ Use query method
        return db.query("""
            SELECT id, name, source_type, custom_source, is_demo, is_active
            FROM tenant_rate_books 
            WHERE tenant_id = ? AND is_archived = 0 AND is_active = 1
            ORDER BY source_type, name
        """, (company_id,))
    
    def get_rate_book_version(self, book_id: int) -> Optional[Dict]:
        """Get current active version"""
        db = self._get_db()
        
        try:
            # ✅ Use correct column names
            result = db.query_one("""
                SELECT id, version_name, version_number, is_current, created_at
                FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = TRUE
                ORDER BY version_number DESC LIMIT 1
            """, (book_id,))
            
            if result:
                # ✅ Ensure version_name is returned
                return {
                    'id': result.get('id'),
                    'name': result.get('version_name', 'Initial Version'),
                    'version_number': result.get('version_number', 1),
                    'is_current': result.get('is_current', False),
                    'created_at': result.get('created_at')
                }
            return None
            
        except Exception as e:
            print(f"Error getting rate book version: {e}")
            return None

    
    def get_rates_from_book(self, book_id: int, version_id: int, pricing_level: str = 'COMPETITIVE') -> List[Dict]:
        """Get rates from specific rate book - with DISTINCT"""
        db = self._get_db()
        
        # ✅ Use DISTINCT to avoid duplicates
        return db.query("""
            SELECT DISTINCT
                ri.item_code,
                ri.item_description as description,
                ri.unit,
                pl.price as rate,
                ri.is_custom
            FROM tenant_rate_items ri
            JOIN tenant_pricing_levels pl ON ri.id = pl.rate_item_id
            WHERE ri.rate_book_id = ? 
            AND pl.rate_version_id = ?
            AND ri.is_active = TRUE
            AND pl.pricing_level = ?
            ORDER BY ri.item_code
        """, (book_id, version_id, pricing_level))

    
    # =========================================================================
    # BOQ METHODS - Using query/execute
    # =========================================================================
    
    def create_boq(self, user_id: int, company_id: int, tender_id: str, 
                   tender_title: str, procuring_entity: str = "", 
                   rate_book_id: int = None, version_id: int = None, 
                   selected_zone: str = "N/A", source_type: str = "",
                   is_quick_boq: bool = False) -> Optional[int]:
        """Create new BOQ record"""
        db = self._get_db()
        
        if not tender_id or tender_id == "N/A":
            tender_id = f"QBOQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            tender_title = tender_title or f"Quick BOQ {datetime.now().strftime('%Y-%m-%d')}"
        
        status = 'draft' if is_quick_boq else 'pending'
        
        # ✅ Use execute method
        db.execute("""
            INSERT INTO boq_generation_history (
                user_id, company_id, tender_id, tender_title, procuring_entity,
                rate_book_id, version_id, selected_zone, rate_source, 
                status, is_quick_boq, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            rate_book_id, version_id, selected_zone, source_type,
            status, 1 if is_quick_boq else 0, datetime.now().isoformat()
        ))
        
        # Get the inserted ID
        result = db.query_one(
            "SELECT id FROM boq_generation_history WHERE tender_id = ? AND company_id = ? ORDER BY generated_at DESC LIMIT 1",
            (tender_id, company_id)
        )
        
        return result.get('id') if result else None
    
    def add_boq_items(self, boq_id: int, items: List[Dict]) -> bool:
        """Add multiple items to a BOQ"""
        db = self._get_db()
        
        if not items:
            return False
        
        # ✅ Use execute method for each item
        for item in items:
            db.execute("""
                INSERT INTO boq_items (
                    boq_id, item_code, description, unit, quantity, 
                    unit_rate, total, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                boq_id,
                item.get('Item Code', ''),
                item.get('Description', ''),
                item.get('Unit', ''),
                item.get('Quantity', 0),
                item.get('Unit Rate', 0),
                item.get('Total', 0),
                1 if item.get('is_custom', False) else 0
            ))
        
        self.update_boq_totals(boq_id)
        return True
    
    def update_boq_totals(self, boq_id: int) -> bool:
        """Update totals after adding items"""
        db = self._get_db()
        
        # ✅ Use execute method
        db.execute("""
            UPDATE boq_generation_history 
            SET item_count = (SELECT COUNT(*) FROM boq_items WHERE boq_id = ?),
                total_estimated_cost = (SELECT COALESCE(SUM(total), 0) FROM boq_items WHERE boq_id = ?)
            WHERE id = ?
        """, (boq_id, boq_id, boq_id))
        return True
    
    def lock_boq(self, boq_id: int, user_id: int) -> bool:
        """Lock BOQ as final"""
        db = self._get_db()
        
        # ✅ Use execute method
        db.execute("""
            UPDATE boq_generation_history 
            SET is_locked = 1, locked_at = ?, locked_by = ?, status = 'locked'
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id, boq_id))
        return True
    
    def get_boq_by_id(self, boq_id: int) -> Optional[Dict]:
        """Get full BOQ with items"""
        db = self._get_db()
        
        # ✅ Use query_one and query methods
        boq = db.query_one("SELECT * FROM boq_generation_history WHERE id = ?", (boq_id,))
        if not boq:
            return None
        
        items = db.query("SELECT * FROM boq_items WHERE boq_id = ? ORDER BY id", (boq_id,))
        
        return {
            'boq': boq,
            'items': items
        }
    
    def get_boq_items(self, boq_id: int) -> List[Dict]:
        """Get all items for a BOQ"""
        db = self._get_db()
        
        # ✅ Use query method
        return db.query("""
            SELECT * FROM boq_items WHERE boq_id = ? ORDER BY id
        """, (boq_id,))
    
    def update_boq_item(self, item_id: int, updates: Dict) -> bool:
        """Update a specific BOQ item"""
        db = self._get_db()
        
        allowed_fields = ['quantity', 'unit_rate', 'total', 'description', 'unit']
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(item_id)
        
        # ✅ Use execute method
        db.execute(f"""
            UPDATE boq_items 
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, tuple(params))
        
        # Update BOQ totals
        boq_result = db.query_one("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
        if boq_result:
            self.update_boq_totals(boq_result.get('boq_id'))
        
        return True
    
    def delete_boq_item(self, item_id: int) -> bool:
        """Delete a BOQ item"""
        db = self._get_db()
        
        boq_result = db.query_one("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
        if boq_result:
            # ✅ Use execute method
            db.execute("DELETE FROM boq_items WHERE id = ?", (item_id,))
            self.update_boq_totals(boq_result.get('boq_id'))
            return True
        
        return False
    
    def get_company_boqs(self, company_id: int, limit: int = 50) -> List[Dict]:
        """Get all BOQs for a company"""
        db = self._get_db()
        
        # ✅ Use query method
        return db.query("""
            SELECT id, tender_id, tender_title, item_count, total_estimated_cost,
                   selected_zone, rate_source, status, generated_at
            FROM boq_generation_history
            WHERE company_id = ?
            ORDER BY generated_at DESC
            LIMIT ?
        """, (company_id, limit))