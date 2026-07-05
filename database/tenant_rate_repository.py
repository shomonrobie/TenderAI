# database/tenant_rate_repository.py

from database.unified_db_manager import get_db_manager
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TenantRateRepository:
    """Repository for tenant rate management"""
    
    def __init__(self, db=None):
        """Initialize with optional db instance"""
        self.db = db or get_db_manager()
    
    def get_connection(self):
        """Get database connection"""
        return self.db.get_connection()
    
    def get_cursor(self, conn):
        """Get cursor from connection"""
        return self.db.get_cursor(conn)
    
    # ========== RATE BOOKS ==========
    
    def create_rate_book(self, data: Dict[str, Any]) -> int:
        """Create a new rate book"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            cursor.execute("""
                INSERT INTO tenant_rate_books (
                    tenant_id, tenant_type, name, source_type, 
                    source_version_id, description, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('tenant_id'),
                data.get('tenant_type', 'company'),
                data.get('name'),
                data.get('source_type'),
                data.get('source_version_id'),
                data.get('description'),
                data.get('created_by'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            book_id = cursor.lastrowid
            conn.close()
            
            return book_id
            
        except Exception as e:
            logger.error(f"Error creating rate book: {e}")
            raise
    
    def get_rate_books_by_tenant(
        self, 
        tenant_id: int, 
        tenant_type: str = 'company',
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Get rate books for a tenant"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            query = """
                SELECT 
                    id, tenant_id, tenant_type, name, source_type, 
                    source_version_id, description, is_active, is_archived,
                    is_demo, created_by, created_at, updated_at
                FROM tenant_rate_books
                WHERE tenant_id = ? AND tenant_type = ?
            """
            params = [tenant_id, tenant_type]
            
            if not include_archived:
                query += " AND is_archived = 0"
            
            query += " ORDER BY name"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows] if rows else []
            
        except Exception as e:
            logger.error(f"Error getting rate books: {e}")
            return []
    
    # ========== VERSIONS ==========
    
    def create_rate_version(self, data: Dict[str, Any]) -> int:
        """Create a new rate version"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            # If this is set as current, unset others
            if data.get('is_current', False):
                cursor.execute("""
                    UPDATE tenant_rate_versions 
                    SET is_current = 0 
                    WHERE rate_book_id = ?
                """, (data.get('rate_book_id'),))
            
            cursor.execute("""
                INSERT INTO tenant_rate_versions (
                    rate_book_id, version_name, version_number, 
                    effective_from, is_current, notes, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('rate_book_id'),
                data.get('version_name', 'Version 1'),
                1,  # version_number - you might want to calculate this
                data.get('effective_from', datetime.now().date().isoformat()),
                1 if data.get('is_current', False) else 0,
                data.get('notes'),
                data.get('created_by'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            version_id = cursor.lastrowid
            conn.close()
            
            return version_id
            
        except Exception as e:
            logger.error(f"Error creating rate version: {e}")
            raise
    
    def get_versions_for_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a rate book"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            cursor.execute("""
                SELECT 
                    id, rate_book_id, version_name, version_number,
                    effective_from, is_current, notes, created_by, created_at
                FROM tenant_rate_versions
                WHERE rate_book_id = ?
                ORDER BY version_number DESC
            """, (book_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows] if rows else []
            
        except Exception as e:
            logger.error(f"Error getting versions: {e}")
            return []
    
    def set_current_version(self, version_id: int) -> bool:
        """Set a version as current"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            # Get the book_id for this version
            cursor.execute(
                "SELECT rate_book_id FROM tenant_rate_versions WHERE id = ?",
                (version_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False
            
            book_id = row['rate_book_id']
            
            # Unset current for all versions of this book
            cursor.execute("""
                UPDATE tenant_rate_versions 
                SET is_current = 0 
                WHERE rate_book_id = ?
            """, (book_id,))
            
            # Set this version as current
            cursor.execute("""
                UPDATE tenant_rate_versions 
                SET is_current = 1 
                WHERE id = ?
            """, (version_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting current version: {e}")
            return False
    
    # ========== ITEMS ==========
    
    def get_rate_items_by_book(
        self, 
        book_id: int, 
        version_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get items for a rate book"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            query = """
                SELECT 
                    tri.id, tri.item_code, tri.item_description, 
                    tri.unit, tri.is_active, tri.is_archived,
                    trp.pricing_level, trp.price, trp.effective_from
                FROM tenant_rate_items tri
                LEFT JOIN tenant_rate_pricing trp ON tri.id = trp.item_id
                WHERE tri.rate_book_id = ?
            """
            params = [book_id]
            
            if version_id:
                query += " AND trp.version_id = ?"
                params.append(version_id)
            
            if active_only:
                query += " AND tri.is_active = 1 AND tri.is_archived = 0"
            
            query += " ORDER BY tri.item_code"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows] if rows else []
            
        except Exception as e:
            logger.error(f"Error getting rate items: {e}")
            return []
    
    def get_item_pricing(self, item_id: int, version_id: int) -> Dict[str, Any]:
        """Get pricing for an item"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            cursor.execute("""
                SELECT 
                    pricing_level, price, effective_from,
                    created_by, created_at
                FROM tenant_rate_pricing
                WHERE item_id = ? AND version_id = ?
                ORDER BY pricing_level
            """, (item_id, version_id))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Group by pricing level
            pricing = {}
            for row in rows:
                level = row.get('pricing_level', 'MARKET')
                if level not in pricing:
                    pricing[level] = []
                pricing[level].append(dict(row))
            
            return pricing
            
        except Exception as e:
            logger.error(f"Error getting item pricing: {e}")
            return {}
    
    def update_pricing(
        self,
        version_id: int,
        item_id: int,
        pricing_level: str,
        price: float,
        user_id: int
    ) -> bool:
        """Update pricing for an item"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            # Check if pricing exists
            cursor.execute("""
                SELECT id FROM tenant_rate_pricing
                WHERE version_id = ? AND item_id = ? AND pricing_level = ?
            """, (version_id, item_id, pricing_level))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE tenant_rate_pricing
                    SET price = ?, updated_by = ?, updated_at = ?
                    WHERE version_id = ? AND item_id = ? AND pricing_level = ?
                """, (price, user_id, datetime.now().isoformat(), version_id, item_id, pricing_level))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO tenant_rate_pricing (
                        version_id, item_id, pricing_level, price,
                        created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (version_id, item_id, pricing_level, price, user_id, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating pricing: {e}")
            return False
    
    # ========== AUDIT ==========
    
    def get_audit_log(
        self,
        book_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit log"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            query = """
                SELECT 
                    id, book_id, version_id, action, 
                    details, user_id, created_at
                FROM tenant_rate_audit
                WHERE 1=1
            """
            params = []
            
            if book_id:
                query += " AND book_id = ?"
                params.append(book_id)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows] if rows else []
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []
    
    def clone_pwd_master(
        self, 
        book_id: int, 
        version_id: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clone PWD master rates to tenant book"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            # This is a placeholder - implement the actual clone logic
            # based on your database schema
            
            # Example: Copy items from PWD master to tenant book
            query = """
                INSERT INTO tenant_rate_items (
                    rate_book_id, item_code, item_description, unit, 
                    created_by, created_at
                )
                SELECT 
                    ?, pwd_code, description, unit,
                    ?, ?
                FROM pwd_children
                WHERE version_id = ?
            """
            params = [book_id, 1, datetime.now().isoformat(), version_id]
            
            if filters:
                if filters.get('chapter'):
                    query += " AND pwd_code LIKE ?"
                    params.append(f"{filters['chapter']}%")
                
                if filters.get('category'):
                    query += " AND category = ?"
                    params.append(filters['category'])
            
            cursor.execute(query, params)
            conn.commit()
            
            # Get count
            count = cursor.rowcount
            
            conn.close()
            
            return {
                'success': True,
                'count': count,
                'message': f'Cloned {count} items from PWD master'
            }
            
        except Exception as e:
            logger.error(f"Error cloning PWD master: {e}")
            return {'success': False, 'error': str(e)}
    
    def clone_lged_master(
        self, 
        book_id: int, 
        version_id: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clone LGED master rates to tenant book"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor(conn)
            
            # This is a placeholder - implement the actual clone logic
            # based on your database schema
            
            query = """
                INSERT INTO tenant_rate_items (
                    rate_book_id, item_code, item_description, unit, 
                    created_by, created_at
                )
                SELECT 
                    ?, code, description, unit,
                    ?, ?
                FROM lged_children
                WHERE version_id = ?
            """
            params = [book_id, 1, datetime.now().isoformat(), version_id]
            
            if filters:
                if filters.get('chapter'):
                    query += " AND code LIKE ?"
                    params.append(f"{filters['chapter']}%")
            
            cursor.execute(query, params)
            conn.commit()
            
            count = cursor.rowcount
            conn.close()
            
            return {
                'success': True,
                'count': count,
                'message': f'Cloned {count} items from LGED master'
            }
            
        except Exception as e:
            logger.error(f"Error cloning LGED master: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_connection(self):
        """Get database connection"""
        return self.db.get_connection()