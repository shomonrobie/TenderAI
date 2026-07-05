# database/crud_rates.py - Complete Rate CRUD with all methods

"""
CRUD Operations for Rate Management Module
All database operations for rates, zones, chapters, parents, children, and versions
"""

from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import logging
import json
from database.connection import is_supabase, get_db_type

logger = logging.getLogger(__name__)


class RateCRUD:
    """Rate-specific CRUD operations - Single source of truth for rate data"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def test_method(self):
        """Test method to verify binding"""
        return "RateCRUD is working!"
    
    def _get_db(self):
        """
        Get the database manager - works both as standalone and when bound to DatabaseCRUD
        """
        # If this instance has the methods directly (bound to DatabaseCRUD)
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        # Otherwise use the stored db_manager
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()


    
    # =========================================================================
    # RATE BOOK OPERATIONS
    # =========================================================================
    
    # database/crud_rates.py - Using direct Supabase client

    def create_rate_book(self, data: Dict[str, Any]) -> int:
        """Create a new rate book using direct Supabase client"""
        db = self._get_db()
        
        try:
            # ✅ Use the supabase client directly if available
            if hasattr(db, 'supabase') and db.supabase:
                print(f"🔍 Using direct Supabase client")
                
                # ✅ DO NOT include 'id' - let Supabase auto-generate it
                insert_data = {
                    'tenant_id': data.get('tenant_id'),
                    'tenant_type': data.get('tenant_type', 'company'),
                    'name': data.get('name'),
                    'source_type': data.get('source_type'),
                    'source_version_id': data.get('source_version_id'),
                    'description': data.get('description'),
                    'created_by': data.get('created_by'),
                    'created_at': datetime.now().isoformat(),
                    'is_active': 1 if data.get('is_active', True) else 0,
                    'is_archived': 0
                }
                
                print(f"🔍 Insert data (without id): {insert_data}")
                
                response = db.supabase.table('tenant_rate_books').insert(insert_data).execute()
                
                print(f"🔍 Response: {response}")
                print(f"🔍 Response data: {response.data if hasattr(response, 'data') else 'No data'}")
                
                if response.data:
                    book_id = response.data[0].get('id')
                    print(f"✅ Created rate book with ID: {book_id}")
                    
                    # ✅ Create a version for this book (also without id)
                    version_data = {
                        'rate_book_id': book_id,
                        'version_name': 'Initial Version',
                        'version_number': 1,
                        'is_current': True,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    version_response = db.supabase.table('tenant_rate_versions').insert(version_data).execute()
                    print(f"🔍 Version response: {version_response}")
                    
                    return book_id
                else:
                    print(f"❌ No data returned from insert")
                    return None
            
            # ✅ Fallback to SQLite
            else:
                print(f"🔍 Using SQLite")
                db.execute("""
                    INSERT INTO tenant_rate_books (
                        tenant_id, tenant_type, name, source_type, 
                        source_version_id, description, created_by, created_at,
                        is_active, is_archived
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('tenant_id'),
                    data.get('tenant_type', 'company'),
                    data.get('name'),
                    data.get('source_type'),
                    data.get('source_version_id'),
                    data.get('description'),
                    data.get('created_by'),
                    datetime.now().isoformat(),
                    1 if data.get('is_active', True) else 0,
                    0
                ))
                
                # Get the inserted ID
                result = db.query_one(
                    "SELECT id FROM tenant_rate_books WHERE name = ? AND tenant_id = ? ORDER BY created_at DESC LIMIT 1",
                    (data.get('name'), data.get('tenant_id'))
                )
                
                return result.get('id') if result else None
                
        except Exception as e:
            print(f"❌ Error creating rate book: {e}")
            import traceback
            traceback.print_exc()
            return None


    
    def get_rate_books_by_tenant(
        self, 
        tenant_id: int, 
        tenant_type: str = 'company',
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Get rate books for a tenant"""
        db = self._get_db()
        
        try:
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
            
            results = db.query(query, tuple(params))
            
            # Normalize boolean values
            for row in results:
                row['is_active'] = bool(row.get('is_active', False))
                row['is_archived'] = bool(row.get('is_archived', False))
                row['is_demo'] = bool(row.get('is_demo', False))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting rate books: {e}")
            return []
    
    def get_rate_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a single rate book by ID"""
        db = self._get_db()
        
        try:
            result = db.query_one("""
                SELECT 
                    id, tenant_id, tenant_type, name, source_type, 
                    source_version_id, description, is_active, is_archived,
                    is_demo, created_by, created_at, updated_at
                FROM tenant_rate_books
                WHERE id = ?
            """, (book_id,))
            
            if result:
                result['is_active'] = bool(result.get('is_active', False))
                result['is_archived'] = bool(result.get('is_archived', False))
                result['is_demo'] = bool(result.get('is_demo', False))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting rate book: {e}")
            return None
    
    def archive_rate_book(self, book_id: int) -> bool:
        """Archive a rate book"""
        db = self._get_db()
        
        try:
            db.execute("""
                UPDATE tenant_rate_books 
                SET is_archived = 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), book_id))
            return True
        except Exception as e:
            logger.error(f"Error archiving rate book: {e}")
            return False
    
    def get_item_count(self, book_id: int) -> int:
        """Get count of items in a rate book"""
        db = self._get_db()
        
        try:
            result = db.query_one("""
                SELECT COUNT(*) as count FROM tenant_rate_items 
                WHERE rate_book_id = ? AND is_archived = 0
            """, (book_id,))
            return result.get('count', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting item count: {e}")
            return 0
    
    def delete_items_for_book(self, book_id: int) -> bool:
        """Delete all items and pricing for a rate book"""
        db = self._get_db()
        
        try:
            print(f"🗑️ Deleting items for book {book_id}")
            
            # ✅ Get the current version
            version = db.query_one("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = TRUE
            """, (book_id,))
            
            if version:
                version_id = version.get('id')
                print(f"✅ Found version: {version_id}")
                
                # ✅ Delete pricing levels for this version
                db.execute("""
                    DELETE FROM tenant_pricing_levels 
                    WHERE rate_version_id = ?
                """, (version_id,))
                print(f"🗑️ Deleted pricing levels")
            
            # ✅ Delete items
            db.execute("""
                DELETE FROM tenant_rate_items 
                WHERE rate_book_id = ?
            """, (book_id,))
            print(f"🗑️ Deleted items")
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting items for book {book_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    
    # =========================================================================
    # VERSION OPERATIONS
    # =========================================================================
    
    def create_rate_version(self, data: Dict[str, Any]) -> int:
        """Create a new rate version"""
        db = self._get_db()
        
        try:
            # Get current max version number
            max_version = db.query_one("""
                SELECT MAX(version_number) as max_num 
                FROM tenant_rate_versions 
                WHERE rate_book_id = ?
            """, (data.get('rate_book_id'),))
            
            next_version = (max_version.get('max_num') or 0) + 1
            
            # If this is set as current, unset others
            if data.get('is_current', False):
                db.execute("""
                    UPDATE tenant_rate_versions 
                    SET is_current = 0 
                    WHERE rate_book_id = ?
                """, (data.get('rate_book_id'),))
            
            db.execute("""
                INSERT INTO tenant_rate_versions (
                    rate_book_id, version_name, version_number, 
                    effective_from, is_current, notes, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('rate_book_id'),
                data.get('version_name', f'Version {next_version}'),
                next_version,
                data.get('effective_from', datetime.now().date().isoformat()),
                1 if data.get('is_current', False) else 0,
                data.get('notes'),
                data.get('created_by'),
                datetime.now().isoformat()
            ))
            
            # Get the inserted ID
            result = db.query_one("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND version_number = ?
            """, (data.get('rate_book_id'), next_version))
            
            return result.get('id') if result else None
            
        except Exception as e:
            logger.error(f"Error creating rate version: {e}")
            raise
    
    def get_versions_for_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a rate book"""
        db = self._get_db()
        
        try:
            results = db.query("""
                SELECT 
                    id, rate_book_id, version_name, version_number,
                    effective_from, is_current, notes, created_by, created_at
                FROM tenant_rate_versions
                WHERE rate_book_id = ?
                ORDER BY version_number DESC
            """, (book_id,))
            
            # Normalize boolean
            for row in results:
                row['is_current'] = bool(row.get('is_current', False))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting versions: {e}")
            return []
    
    def set_current_version(self, version_id: int) -> bool:
        """Set a version as current"""
        db = self._get_db()
        
        try:
            # Get the book_id for this version
            result = db.query_one(
                "SELECT rate_book_id FROM tenant_rate_versions WHERE id = ?",
                (version_id,)
            )
            
            if not result:
                return False
            
            book_id = result.get('rate_book_id')
            
            # Unset current for all versions of this book
            db.execute("""
                UPDATE tenant_rate_versions 
                SET is_current = 0 
                WHERE rate_book_id = ?
            """, (book_id,))
            
            # Set this version as current
            db.execute("""
                UPDATE tenant_rate_versions 
                SET is_current = 1 
                WHERE id = ?
            """, (version_id,))
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting current version: {e}")
            return False
    
    def get_active_master_version(self, source_type: str) -> Optional[Dict[str, Any]]:
        """Get active master version for a source type"""
        db = self._get_db()
        
        try:
            return db.query_one("""
                SELECT id, version_name, edition_year, is_active
                FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC LIMIT 1
            """, (source_type,))
        except Exception as e:
            logger.error(f"Error getting active master version: {e}")
            return None
    
    # =========================================================================
    # ITEM OPERATIONS
    # =========================================================================
    
    def create_rate_item(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new rate item"""
        db = self._get_db()
        
        try:
            db.execute("""
                INSERT INTO tenant_rate_items (
                    rate_book_id, item_code, item_description, unit, 
                    is_custom, is_active, is_archived, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('rate_book_id'),
                data.get('item_code'),
                data.get('item_description'),
                data.get('unit', ''),
                1 if data.get('is_custom', False) else 0,
                1,
                0,
                data.get('created_by'),
                datetime.now().isoformat()
            ))
            
            # Get the inserted ID
            result = db.query_one("""
                SELECT id FROM tenant_rate_items 
                WHERE rate_book_id = ? AND item_code = ?
                ORDER BY created_at DESC LIMIT 1
            """, (data.get('rate_book_id'), data.get('item_code')))
            
            return result.get('id') if result else None
            
        except Exception as e:
            logger.error(f"Error creating rate item: {e}")
            return None
    
    def get_rate_items_by_book(
        self, 
        book_id: int, 
        version_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get items for a rate book - FIXED table name"""
        db = self._get_db()
        
        try:
            query = """
                SELECT 
                    tri.id, tri.item_code, tri.item_description, 
                    tri.unit, tri.is_custom, tri.is_active, tri.is_archived,
                    trp.pricing_level, trp.price, trp.effective_from
                FROM tenant_rate_items tri
                LEFT JOIN tenant_pricing_levels trp ON tri.id = trp.rate_item_id
                WHERE tri.rate_book_id = ?
            """
            params = [book_id]
            
            if version_id:
                query += " AND trp.rate_version_id = ?"
                params.append(version_id)
            
            if active_only:
                query += " AND tri.is_active = 1 AND tri.is_archived = 0"
            
            query += " ORDER BY tri.item_code"
            
            results = db.query(query, tuple(params))
            
            # Normalize boolean
            for row in results:
                row['is_custom'] = bool(row.get('is_custom', False))
                row['is_active'] = bool(row.get('is_active', False))
                row['is_archived'] = bool(row.get('is_archived', False))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting rate items: {e}")
            return []

    
    def get_rate_items_with_pricing(self, book_id: int, version_id: int) -> List[Dict[str, Any]]:
        """Get items with their pricing grouped by level - FIXED table name"""
        db = self._get_db()
        
        try:
            # ✅ Get items without pricing
            items = db.query("""
                SELECT 
                    id, item_code, item_description, unit, is_custom
                FROM tenant_rate_items 
                WHERE rate_book_id = ? AND is_active = 1 AND is_archived = 0
                ORDER BY item_code
            """, (book_id,))
            
            if not items:
                return []
            
            # ✅ Get pricing for these items
            item_ids = [item['id'] for item in items]
            placeholders = ','.join(['?' for _ in item_ids])
            
            pricing = db.query(f"""
                SELECT 
                    rate_item_id, pricing_level, price
                FROM tenant_pricing_levels
                WHERE rate_version_id = ? 
                AND rate_item_id IN ({placeholders})
            """, (version_id, *item_ids))
            
            # ✅ Group pricing by item
            pricing_by_item = {}
            for p in pricing:
                item_id = p.get('rate_item_id')
                if item_id not in pricing_by_item:
                    pricing_by_item[item_id] = {}
                pricing_by_item[item_id][p.get('pricing_level')] = {
                    'price': p.get('price', 0)
                }
            
            # ✅ Combine items with pricing
            result = []
            for item in items:
                item_id = item.get('id')
                item['pricing'] = pricing_by_item.get(item_id, {})
                result.append(item)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting items with pricing: {e}")
            return []

    
    def update_rate_item(self, item_id: int, updates: Dict[str, Any]) -> bool:
        """Update a rate item"""
        db = self._get_db()
        
        try:
            allowed_fields = ['item_code', 'item_description', 'unit', 'is_custom', 'is_active', 'is_archived']
            
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(item_id)
            
            db.execute(f"""
                UPDATE tenant_rate_items 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, tuple(params))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating rate item: {e}")
            return False
    
    def delete_rate_item(self, item_id: int) -> bool:
        """Delete a rate item (soft delete)"""
        db = self._get_db()
        
        try:
            db.execute("""
                UPDATE tenant_rate_items 
                SET is_archived = 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), item_id))
            return True
        except Exception as e:
            logger.error(f"Error deleting rate item: {e}")
            return False
    
    # =========================================================================
    # PRICING OPERATIONS
    # =========================================================================
    
    def get_item_pricing(self, item_id: int, version_id: int) -> Dict[str, Any]:
        """Get pricing for an item - FIXED table name"""
        db = self._get_db()
        
        try:
            results = db.query("""
                SELECT 
                    pricing_level, price, effective_from,
                    created_by, created_at
                FROM tenant_pricing_levels
                WHERE rate_item_id = ? AND rate_version_id = ?
                ORDER BY pricing_level
            """, (item_id, version_id))
            
            # Group by pricing level
            pricing = {}
            for row in results:
                level = row.get('pricing_level', 'MARKET')
                if level not in pricing:
                    pricing[level] = []
                pricing[level].append(row)
            
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
        """Update pricing for an item - FIXED table name"""
        db = self._get_db()
        
        try:
            # ✅ Check if pricing exists
            existing = db.query_one("""
                SELECT id FROM tenant_pricing_levels
                WHERE rate_version_id = ? AND rate_item_id = ? AND pricing_level = ?
            """, (version_id, item_id, pricing_level))
            
            if existing:
                # Update existing
                db.execute("""
                    UPDATE tenant_pricing_levels
                    SET price = ?, updated_by = ?, updated_at = ?
                    WHERE rate_version_id = ? AND rate_item_id = ? AND pricing_level = ?
                """, (price, user_id, datetime.now().isoformat(), version_id, item_id, pricing_level))
            else:
                # Insert new
                db.execute("""
                    INSERT INTO tenant_pricing_levels (
                        rate_version_id, rate_item_id, pricing_level, price,
                        created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (version_id, item_id, pricing_level, price, user_id, datetime.now().isoformat()))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating pricing: {e}")
            return False

    
    # =========================================================================
    # CLONE OPERATIONS
    # =========================================================================
    
    # database/crud_rates.py - Fixed clone_master_to_company

    def clone_master_to_company(
        self, 
        book_id: int, 
        source_type: str,
        version_id: int, 
        user_id: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clone master rates to company rate book - using direct Supabase client"""
        db = self._get_db()
        
        try:
            print(f"🔍 Cloning {source_type} master rates to book {book_id}")
            print(f"🔍 Version ID: {version_id}")
            
            # ✅ Check if we're using Supabase
            is_supabase = False
            if hasattr(db, '_use_supabase'):
                is_supabase = db._use_supabase
            elif hasattr(db, 'supabase'):
                is_supabase = db.supabase is not None
            
            # ✅ Get source items using direct Supabase client if available
            if is_supabase and hasattr(db, 'supabase') and db.supabase:
                print(f"🔍 Using direct Supabase client")
                
                # Build query
                if source_type == 'PWD':
                    query = db.supabase.table('pwd_children')\
                        .select('pwd_code, description, unit')\
                        .eq('version_id', version_id)
                    
                    if filters and filters.get('chapter'):
                        query = query.like('pwd_code', f"{filters['chapter']}%")
                    
                    query = query.order('pwd_code')
                    
                else:  # LGED
                    query = db.supabase.table('lged_children')\
                        .select('code, description, unit')\
                        .eq('version_id', version_id)
                    
                    if filters and filters.get('chapter'):
                        query = query.like('code', f"{filters['chapter']}%")
                    
                    query = query.order('code')
                
                response = query.execute()
                source_items = response.data if response.data else []
                print(f"🔍 Found {len(source_items)} items from {source_type} master via direct Supabase")
                
            else:
                # Fallback to wrapper
                print(f"🔍 Using wrapper for query")
                
                if source_type == 'PWD':
                    source_query = """
                        SELECT 
                            pwd_code, 
                            description, 
                            unit
                        FROM pwd_children
                        WHERE version_id = ?
                    """
                    params = [version_id]
                    
                    if filters and filters.get('chapter'):
                        source_query += " AND pwd_code LIKE ?"
                        params.append(f"{filters['chapter']}%")
                    
                    source_query += " ORDER BY pwd_code"
                    
                else:  # LGED
                    source_query = """
                        SELECT 
                            code, 
                            description, 
                            unit
                        FROM lged_children
                        WHERE version_id = ?
                    """
                    params = [version_id]
                    
                    if filters and filters.get('chapter'):
                        source_query += " AND code LIKE ?"
                        params.append(f"{filters['chapter']}%")
                    
                    source_query += " ORDER BY code"
                
                source_items = db.query(source_query, tuple(params))
                print(f"🔍 Found {len(source_items)} items from {source_type} master via wrapper")
            
            # ✅ DEBUG: Print first few items
            if source_items:
                print(f"🔍 First item: {source_items[0] if source_items else 'None'}")
            
            if not source_items:
                return {'success': False, 'error': f'No items found in {source_type} master rates'}
            
            # ✅ Clear existing items for this book
            db.execute("DELETE FROM tenant_rate_items WHERE rate_book_id = ?", (book_id,))
            print(f"🗑️ Deleted existing items for book {book_id}")
            
            # ✅ Insert items into tenant rate book
            inserted = 0
            errors = []
            
            for item in source_items:
                try:
                    # ✅ Get item_code based on source type
                    if source_type == 'PWD':
                        item_code = item.get('pwd_code')
                    else:
                        item_code = item.get('code')
                    
                    # ✅ Skip items with None or empty item_code
                    if not item_code:
                        print(f"⚠️ Skipping item with no code: {str(item)[:50]}...")
                        continue
                    
                    description = item.get('description', '')
                    unit = item.get('unit', '')
                    
                    # ✅ Insert item
                    db.execute("""
                        INSERT INTO tenant_rate_items (
                            rate_book_id, item_code, item_description, unit, 
                            is_custom, is_active, is_archived, created_by, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        book_id,
                        str(item_code).strip(),
                        str(description).strip(),
                        str(unit).strip(),
                        0,  # is_custom
                        1,  # is_active
                        0,  # is_archived
                        user_id,
                        datetime.now().isoformat()
                    ))
                    inserted += 1
                    
                    if inserted % 10 == 0:
                        print(f"   Inserted {inserted} items...")
                        
                except Exception as e:
                    error_msg = f"Error inserting {item_code if 'item_code' in locals() else 'unknown'}: {e}"
                    errors.append(error_msg)
                    print(f"⚠️ {error_msg}")
            
            print(f"✅ Inserted {inserted} items, {len(errors)} errors")
            
            # ✅ Add pricing levels for the items
            if inserted > 0:
                print(f"🔍 Adding pricing levels for {inserted} items...")
                self.add_pricing_levels_for_book(book_id, user_id)
            
            return {
                'success': True,
                'items_created': inserted,
                'errors': errors,
                'message': f'Cloned {inserted} items from {source_type} master'
            }
            
        except Exception as e:
            logger.error(f"Error cloning master: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
        
    def add_pricing_levels_for_book(self, book_id: int, user_id: int):
        """Add pricing levels for all items in a rate book"""
        db = self._get_db()
        
        try:
            # ✅ Get the current version for this book
            version = db.query_one("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = TRUE
            """, (book_id,))
            
            if not version:
                print(f"⚠️ No current version found for book {book_id}")
                return
            
            version_id = version.get('id')
            print(f"🔍 Version ID: {version_id}")
            
            # ✅ Get all items in this book
            items = db.query("""
                SELECT id, item_code FROM tenant_rate_items 
                WHERE rate_book_id = ? AND is_active = TRUE AND item_code IS NOT NULL
            """, (book_id,))
            
            if not items:
                print(f"⚠️ No items found for book {book_id}")
                return
            
            print(f"🔍 Adding pricing for {len(items)} items")
            
            inserted = 0
            errors = []
            
            for item in items:
                try:
                    item_code = item.get('item_code')
                    
                    if not item_code:
                        continue
                    
                    # ✅ Get PWD official rate (try direct Supabase first)
                    base_price = 1000.0
                    
                    if hasattr(db, 'supabase') and db.supabase:
                        # Use direct Supabase
                        rate_response = db.supabase.table('pwd_rates')\
                            .select('unit_rate')\
                            .eq('pwd_code', item_code)\
                            .eq('zone_name', 'Zone-A')\
                            .limit(1)\
                            .execute()
                        
                        if rate_response.data:
                            base_price = float(rate_response.data[0].get('unit_rate', 1000.0))
                    else:
                        # Use wrapper
                        pwd_rate = db.query_one("""
                            SELECT unit_rate FROM pwd_rates 
                            WHERE pwd_code = ? AND zone_name = 'Zone-A'
                            LIMIT 1
                        """, (item_code,))
                        
                        if pwd_rate:
                            base_price = float(pwd_rate.get('unit_rate', 1000.0))
                    
                    # ✅ Insert pricing levels
                    pricing_levels = [
                        ('PWD_OFFICIAL', base_price),
                        ('COMPETITIVE', base_price * 0.82),
                        ('AGGRESSIVE', base_price * 0.75),
                        ('STANDARD', base_price * 0.90)
                    ]
                    
                    for level, price in pricing_levels:
                        try:
                            # ✅ Check if pricing already exists
                            existing = db.query_one("""
                                SELECT id FROM tenant_pricing_levels 
                                WHERE rate_item_id = ? AND rate_version_id = ? AND pricing_level = ?
                            """, (item.get('id'), version_id, level))
                            
                            if existing:
                                # Update existing pricing
                                db.execute("""
                                    UPDATE tenant_pricing_levels
                                    SET price = ?, updated_by = ?, updated_at = ?
                                    WHERE rate_item_id = ? AND rate_version_id = ? AND pricing_level = ?
                                """, (round(price, 2), user_id, datetime.now().isoformat(), 
                                    item.get('id'), version_id, level))
                            else:
                                # Insert new pricing
                                db.execute("""
                                    INSERT INTO tenant_pricing_levels (
                                        rate_item_id, rate_version_id, pricing_level, price, created_by, created_at
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                """, (item.get('id'), version_id, level, round(price, 2), user_id, datetime.now().isoformat()))
                            inserted += 1
                        except Exception as e:
                            errors.append(f"Error adding {level} for {item_code}: {e}")
                            
                except Exception as e:
                    errors.append(f"Error processing {item_code}: {e}")
                    print(f"⚠️ Error adding pricing for {item.get('item_code')}: {e}")
            
            print(f"✅ Added {inserted} pricing levels, errors: {len(errors)}")
            
        except Exception as e:
            print(f"⚠️ Error adding pricing levels: {e}")
            import traceback
            traceback.print_exc()




    # =========================================================================
    # AUDIT OPERATIONS
    # =========================================================================
    
    def log_audit(
        self,
        rate_book_id: Optional[int] = None,
        rate_item_id: Optional[int] = None,
        pricing_level_id: Optional[int] = None,
        action: str = None,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ) -> bool:
        """Log an audit entry - matches actual table schema"""
        db = self._get_db()
        
        try:
            db.execute("""
                INSERT INTO tenant_rate_audit (
                    rate_book_id, rate_item_id, pricing_level_id,
                    action, field_name, old_value, new_value,
                    user_id, ip_address, user_agent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rate_book_id,
                rate_item_id,
                pricing_level_id,
                action,
                field_name,
                old_value,
                new_value,
                user_id,
                ip_address,
                user_agent,
                datetime.now().isoformat()
            ))
            return True
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
            return False

    def get_audit_log(
            self,
            book_id: Optional[int] = None,
            user_id: Optional[int] = None,
            action: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            limit: int = 500,
            offset: int = 0
        ) -> List[Dict[str, Any]]:
        """Get audit log with filters - matches actual table schema"""
        db = self._get_db()
        
        try:
            query = """
                SELECT 
                    tra.id, 
                    tra.rate_book_id, 
                    tra.rate_item_id,
                    tra.pricing_level_id,
                    tra.action, 
                    tra.field_name, 
                    tra.old_value, 
                    tra.new_value,
                    tra.user_id, 
                    tra.ip_address,
                    tra.user_agent,
                    tra.created_at,
                    rb.name as book_name,
                    rb.source_type as book_source,
                    u.username, 
                    u.full_name as user_name
                FROM tenant_rate_audit tra
                LEFT JOIN tenant_rate_books rb ON tra.rate_book_id = rb.id
                LEFT JOIN users u ON tra.user_id = u.id
                WHERE 1=1
            """
            params = []
            
            if book_id:
                query += " AND tra.rate_book_id = ?"
                params.append(book_id)
            
            if user_id:
                query += " AND tra.user_id = ?"
                params.append(user_id)
            
            if action:
                query += " AND tra.action = ?"
                params.append(action)
            
            if date_from:
                query += " AND DATE(tra.created_at) >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(tra.created_at) <= ?"
                params.append(date_to)
            
            query += " ORDER BY tra.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            return db.query(query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []

    
    # =========================================================================
    # COMPANY STATUS
    # =========================================================================
    
    def get_company_status(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company status information"""
        db = self._get_db()
        
        try:
            return db.query_one("""
                SELECT environment_mode, onboarding_status
                FROM companies WHERE id = ?
            """, (company_id,))
        except Exception as e:
            logger.error(f"Error getting company status: {e}")
            return None
    
    # =========================================================================
    # ZONE OPERATIONS (from rate_crud_forms.py helpers)
    # =========================================================================
    
    def get_zones(self, source: str) -> List[Dict]:
        """Get zones from database"""
        db = self._get_db()
        
        if source == "PWD":
            # PWD zones are predefined
            return [
                {'code': 'Dhaka', 'name': 'Dhaka & Mymensingh Division', 'description': 'Capital region', 
                 'divisions': 'Dhaka, Mymensingh', 'accessibility_bonus': 0},
                {'code': 'Chattogram', 'name': 'Chattogram & Sylhet Division', 'description': 'Port city region', 
                 'divisions': 'Chattogram, Sylhet', 'accessibility_bonus': 0},
                {'code': 'Khulna', 'name': 'Khulna & Barishal Division', 'description': 'South-western region', 
                 'divisions': 'Khulna, Barishal', 'accessibility_bonus': 0},
                {'code': 'Rajshahi', 'name': 'Rajshahi & Rangpur Division', 'description': 'Northern region', 
                 'divisions': 'Rajshahi, Rangpur', 'accessibility_bonus': 0}
            ]
        else:  # LGED
            results = db.query("""
                SELECT zone_code as code, zone_name as name, divisions, 
                       accessibility_bonus, description
                FROM lged_zone_mapping 
                ORDER BY zone_code
            """)
            
            zones = []
            for row in results:
                zones.append({
                    'code': row.get('code'),
                    'name': row.get('name'),
                    'divisions': row.get('divisions', ''),
                    'accessibility_bonus': row.get('accessibility_bonus', 0),
                    'description': row.get('description', '')
                })
            return zones
    
    def save_zone(self, source: str, code: str, name: str, description: str, 
                  divisions: str, bonus: float) -> bool:
        """Save zone to database"""
        db = self._get_db()
        
        if source == "PWD":
            # PWD zones are predefined - can't save
            return False
        else:  # LGED
            try:
                db.execute("""
                    INSERT OR REPLACE INTO lged_zone_mapping 
                    (zone_code, zone_name, divisions, accessibility_bonus, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, name, divisions, bonus, description))
                return True
            except Exception as e:
                logger.error(f"Error saving zone: {e}")
                return False
    
    def update_zone(self, source: str, code: str, name: str, description: str,
                    divisions: str, bonus: float) -> bool:
        """Update zone"""
        db = self._get_db()
        
        if source == "LGED":
            try:
                db.execute("""
                    UPDATE lged_zone_mapping 
                    SET zone_name = ?, divisions = ?, accessibility_bonus = ?, description = ?
                    WHERE zone_code = ?
                """, (name, divisions, bonus, description, code))
                return True
            except Exception as e:
                logger.error(f"Error updating zone: {e}")
                return False
        return False
    
    # =========================================================================
    # CHAPTER OPERATIONS
    # =========================================================================
    
    def get_chapters(self, source: str) -> List[Dict]:
        """Get chapters from database"""
        db = self._get_db()
        
        table = "pwd_chapters" if source == "PWD" else "lged_chapters"
        
        # Use simple ORDER BY without casting - works in both databases
        results = db.query(f"""
            SELECT chapter_number, chapter_name, description 
            FROM {table} 
            ORDER BY chapter_number
        """)
        
        # Ensure chapter_number is string for display
        for result in results:
            if 'chapter_number' in result:
                result['chapter_number'] = str(result['chapter_number'])
        
        return results
    
    def save_chapter(self, source: str, chapter_num: str, chapter_name: str) -> bool:
        """Save chapter to database"""
        db = self._get_db()
        
        table = "pwd_chapters" if source == "PWD" else "lged_chapters"
        
        try:
            # Check if chapter already exists
            existing = db.query_one(
                f"SELECT chapter_number FROM {table} WHERE chapter_number = ?",
                (chapter_num,)
            )
            
            if existing:
                # Update existing chapter
                db.execute(f"""
                    UPDATE {table} 
                    SET chapter_name = ?
                    WHERE chapter_number = ?
                """, (chapter_name, chapter_num))
            else:
                # Insert new chapter
                db.execute(f"""
                    INSERT INTO {table} (chapter_number, chapter_name, created_at)
                    VALUES (?, ?, ?)
                """, (chapter_num, chapter_name, datetime.now().isoformat()))
            
            return True
        except Exception as e:
            logger.error(f"Error saving chapter: {e}")
            return False
    
    def update_chapter(self, source: str, chapter_num: str, new_name: str) -> bool:
        """Update chapter name"""
        db = self._get_db()
        
        table = "pwd_chapters" if source == "PWD" else "lged_chapters"
        try:
            db.execute(f"""
                UPDATE {table} 
                SET chapter_name = ?
                WHERE chapter_number = ?
            """, (new_name, chapter_num))
            return True
        except Exception as e:
            logger.error(f"Error updating chapter: {e}")
            return False
    
    # =========================================================================
    # SECTION OPERATIONS (LGED only)
    # =========================================================================
    
    def get_sections_for_chapter(self, chapter_num: str) -> List[Dict]:
        """Get sections for a specific LGED chapter"""
        db = self._get_db()
        
        try:
            results = db.query("""
                SELECT id, section_number, section_name, description, display_order
                FROM lged_sections 
                WHERE chapter_number = ?
                ORDER BY display_order, section_number
            """, (chapter_num,))
            
            sections = []
            for row in results:
                sections.append({
                    'id': row.get('id'),
                    'section_number': str(row.get('section_number', '')),
                    'section_name': row.get('section_name', ''),
                    'description': row.get('description', ''),
                    'display_order': row.get('display_order', 0)
                })
            
            return sections
            
        except Exception as e:
            logger.error(f"Error getting sections for chapter {chapter_num}: {e}")
            return []
    
    def save_section(self, chapter_num: str, section_number: str, section_name: str,
                     description: str, display_order: int) -> bool:
        """Save section to lged_sections table"""
        db = self._get_db()
        
        try:
            # Check if section exists
            existing = db.query_one(
                "SELECT id FROM lged_sections WHERE chapter_number = ? AND section_number = ?",
                (chapter_num, section_number)
            )
            
            if existing:
                # Update existing section
                db.execute("""
                    UPDATE lged_sections 
                    SET section_name = ?, description = ?, display_order = ?
                    WHERE chapter_number = ? AND section_number = ?
                """, (section_name, description, display_order, chapter_num, section_number))
            else:
                # Insert new section
                db.execute("""
                    INSERT INTO lged_sections 
                    (chapter_number, section_number, section_name, description, display_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (chapter_num, section_number, section_name, description, display_order, datetime.now().isoformat()))
            
            return True
        except Exception as e:
            logger.error(f"Error saving section: {e}")
            return False
    
    def update_section(self, chapter_num: str, section_number: str, section_name: str,
                       description: str, display_order: int) -> bool:
        """Update section in lged_sections table"""
        db = self._get_db()
        
        try:
            db.execute("""
                UPDATE lged_sections 
                SET section_name = ?, description = ?, display_order = ?
                WHERE chapter_number = ? AND section_number = ?
            """, (section_name, description, display_order, chapter_num, section_number))
            return True
        except Exception as e:
            logger.error(f"Error updating section: {e}")
            return False
    
    def delete_section(self, chapter_num: str, section_number: str) -> bool:
        """Delete section from lged_sections table"""
        db = self._get_db()
        
        try:
            db.execute("""
                DELETE FROM lged_sections 
                WHERE chapter_number = ? AND section_number = ?
            """, (chapter_num, section_number))
            return True
        except Exception as e:
            logger.error(f"Error deleting section: {e}")
            return False
    
    def get_next_section_number(self, chapter_num: str) -> str:
        """Generate next available section number for LGED"""
        db = self._get_db()
        
        try:
            result = db.query_one("""
                SELECT section_number 
                FROM lged_sections 
                WHERE chapter_number = ?
                ORDER BY display_order DESC, section_number DESC
                LIMIT 1
            """, (chapter_num,))
            
            if result:
                last_section = result.get('section_number', '')
                if '.' in last_section:
                    parts = last_section.split('.')
                    if len(parts) == 2:
                        try:
                            last_num = int(parts[1])
                            next_num = last_num + 1
                            if next_num > 99:
                                next_num = 99
                            return f"{chapter_num}.{next_num:02d}"
                        except ValueError:
                            pass
            
            return f"{chapter_num}.01"
            
        except Exception as e:
            logger.error(f"Error getting next section number: {e}")
            return f"{chapter_num}.01"
    
    # =========================================================================
    # PARENT OPERATIONS
    # =========================================================================
    
    def get_parents(self, source: str) -> List[Dict]:
        """Get parent items from database"""
        db = self._get_db()
        
        if source == "PWD":
            results = db.query("""
                SELECT pwd_code as code, description, chapter_number
                FROM pwd_parents 
                ORDER BY pwd_code
            """)
        else:  # LGED
            results = db.query("""
                SELECT code, description, chapter_number, section_number
                FROM lged_parents 
                ORDER BY code
            """)
        
        return results
    
    def save_parent(self, source: str, parent_code: str, description: str,
                    chapter: str, section: str = '') -> bool:
        """Save parent to database"""
        db = self._get_db()
        
        try:
            if source == "PWD":
                db.execute("""
                    INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number)
                    VALUES (?, ?, ?)
                """, (parent_code, description, chapter))
            else:  # LGED
                db.execute("""
                    INSERT OR REPLACE INTO lged_parents (code, description, chapter_number, section_number)
                    VALUES (?, ?, ?, ?)
                """, (parent_code, description, chapter, section))
            return True
        except Exception as e:
            logger.error(f"Error saving parent: {e}")
            return False
    
    def update_parent(self, source: str, parent_code: str, description: str,
                      chapter: str, section: str = '') -> bool:
        """Update parent in database"""
        db = self._get_db()
        
        try:
            if source == "PWD":
                db.execute("""
                    UPDATE pwd_parents 
                    SET chapter_number = ?, description = ?
                    WHERE pwd_code = ?
                """, (chapter, description, parent_code))
            else:  # LGED
                db.execute("""
                    UPDATE lged_parents 
                    SET chapter_number = ?, section_number = ?, description = ?
                    WHERE code = ?
                """, (chapter, section, description, parent_code))
            return True
        except Exception as e:
            logger.error(f"Error updating parent: {e}")
            return False
    
    # =========================================================================
    # CHILD OPERATIONS
    # =========================================================================
    
    def get_children(self, source: str) -> List[Dict]:
        """Get children with their rates from database"""
        db = self._get_db()
        
        children = []
        
        if source == "PWD":
            # Get children first
            children_results = db.query("""
                SELECT pwd_code as code, parent_code, description, unit
                FROM pwd_children 
                ORDER BY pwd_code
            """)
            
            # Get rates separately
            for child in children_results:
                code = child.get('code')
                rates_result = db.query("""
                    SELECT zone_name, unit_rate
                    FROM pwd_rates 
                    WHERE pwd_code = ?
                """, (code,))
                
                child['rates'] = {}
                for rate in rates_result:
                    child['rates'][rate.get('zone_name')] = rate.get('unit_rate', 0)
                
                children.append(child)
            
        else:  # LGED
            # Get children first
            children_results = db.query("""
                SELECT code, parent_code, description, unit
                FROM lged_children 
                ORDER BY code
            """)
            
            # Get rates separately
            for child in children_results:
                code = child.get('code')
                # Get child_id first
                child_id_result = db.query_one(
                    "SELECT id FROM lged_children WHERE code = ?",
                    (code,)
                )
                child_id = child_id_result.get('id') if child_id_result else None
                
                if child_id:
                    rates_result = db.query("""
                        SELECT zone_name, unit_rate
                        FROM lged_zone_rates 
                        WHERE child_id = ?
                    """, (child_id,))
                    
                    child['rates'] = {}
                    for rate in rates_result:
                        child['rates'][rate.get('zone_name')] = rate.get('unit_rate', 0)
                else:
                    child['rates'] = {}
                
                children.append(child)
        
        return children
    
    def save_child(self, source: str, child_code: str, parent_code: str,
                   description: str, unit: str, edition_year: int, rates: Dict) -> bool:
        """Save child with rates to database"""
        db = self._get_db()
        
        try:
            if source == "PWD":
                db.execute("""
                    INSERT OR REPLACE INTO pwd_children 
                    (pwd_code, parent_code, description, unit, edition_year)
                    VALUES (?, ?, ?, ?, ?)
                """, (child_code, parent_code, description, unit, edition_year))
                
                for zone, rate in rates.items():
                    if rate and rate > 0:
                        db.execute("""
                            INSERT OR REPLACE INTO pwd_rates 
                            (pwd_code, zone_name, unit_rate, edition_year)
                            VALUES (?, ?, ?, ?)
                        """, (child_code, zone, float(rate), edition_year))
                    else:
                        db.execute("""
                            DELETE FROM pwd_rates 
                            WHERE pwd_code = ? AND zone_name = ?
                        """, (child_code, zone))
            else:  # LGED
                db.execute("""
                    INSERT OR REPLACE INTO lged_children 
                    (code, parent_code, description, unit, edition_year)
                    VALUES (?, ?, ?, ?, ?)
                """, (child_code, parent_code, description, unit, edition_year))
                
                # Get child_id
                child_result = db.query_one(
                    "SELECT id FROM lged_children WHERE code = ?",
                    (child_code,)
                )
                child_id = child_result.get('id') if child_result else None
                
                if child_id:
                    for zone, rate in rates.items():
                        if rate and rate > 0:
                            db.execute("""
                                INSERT OR REPLACE INTO lged_zone_rates 
                                (child_id, zone_name, unit_rate)
                                VALUES (?, ?, ?)
                            """, (child_id, zone, float(rate)))
                        else:
                            db.execute("""
                                DELETE FROM lged_zone_rates 
                                WHERE child_id = ? AND zone_name = ?
                            """, (child_id, zone))
            
            return True
        except Exception as e:
            logger.error(f"Error saving child: {e}")
            return False
    
    # =========================================================================
    # VERSION OPERATIONS (from rate_crud_forms.py helpers)
    # =========================================================================
    
    def get_versions(self, source: str) -> List[Dict]:
        """Get versions from database"""
        db = self._get_db()
        
        results = db.query("""
            SELECT id, version_name, edition_year, effective_from, 
                   is_active, release_date, created_by
            FROM rate_versions 
            WHERE source = ?
            ORDER BY edition_year DESC
        """, (source,))
        
        # Normalize boolean values
        for result in results:
            if 'is_active' in result:
                is_active = result.get('is_active')
                if isinstance(is_active, bool):
                    result['is_active'] = is_active
                else:
                    result['is_active'] = bool(is_active) if is_active is not None else False
        
        return results
    
    def save_version(self, source: str, version_name: str, edition_year: int,
                     effective_date: str, is_active: bool, created_by: str) -> bool:
        """Save version to database"""
        db = self._get_db()
        
        try:
            # Check if version exists
            existing = db.query_one(
                "SELECT id FROM rate_versions WHERE source = ? AND edition_year = ?",
                (source, edition_year)
            )
            
            if existing:
                return False  # Version already exists
            
            # If active, deactivate others
            if is_active:
                db.execute("UPDATE rate_versions SET is_active = ? WHERE source = ?", (False, source))
            
            db.execute("""
                INSERT INTO rate_versions 
                (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, version_name, edition_year, effective_date, is_active, 
                  datetime.now().isoformat(), created_by))
            
            return True
        except Exception as e:
            logger.error(f"Error saving version: {e}")
            return False
    # database/crud_rates.py - Add these methods to RateCRUD class

    def init_version_tables(self) -> bool:
        """Initialize unified version tracking tables"""
        db = self._get_db()
        
        try:
            # Check if table exists
            if db.table_exists('rate_versions'):
                return True
            
            # Create tables using raw SQL (this is acceptable for schema creation)
            # Tables created once during initialization
            return True
        except Exception as e:
            print(f"Error initializing version tables: {e}")
            return False

    def get_all_versions(self, source=None) -> List[Dict]:
        """Get all versions, optionally filtered by source"""
        db = self._get_db()
        
        if source:
            results = db.query("""
                SELECT * FROM rate_versions 
                WHERE source = ?
                ORDER BY edition_year DESC
            """, (source,))
        else:
            results = db.query("""
                SELECT * FROM rate_versions 
                ORDER BY source, edition_year DESC
            """)
        
        # ✅ Ensure each row is a dict
        return [dict(row) for row in results] if results else []

    def get_active_version(self, source=None) -> List[Dict]:
        """Get active version for a source or all active versions"""
        db = self._get_db()
        
        if source:
            results = db.query("""
                SELECT * FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC
                LIMIT 1
            """, (source,))
        else:
            results = db.query("""
                SELECT * FROM rate_versions 
                WHERE is_active = 1
                ORDER BY source, edition_year DESC
            """)
        
        # ✅ Ensure each row is a dict
        return [dict(row) for row in results] if results else []

    def activate_version(self, version_id: int, activated_by: str) -> bool:
        """Activate a specific version (deactivate others of same source)"""
        db = self._get_db()
        
        try:
            # Get the source of this version
            version = db.query_one("SELECT source FROM rate_versions WHERE id = ?", (version_id,))
            if not version:
                return False
            
            source = version.get('source')
            
            # Deactivate all versions of the same source
            db.execute("UPDATE rate_versions SET is_active = 0 WHERE source = ?", (source,))
            
            # Activate the selected version
            db.execute("""
                UPDATE rate_versions 
                SET is_active = 1, released_by = ?, release_date = ?
                WHERE id = ?
            """, (activated_by, datetime.now().isoformat(), version_id))
            
            # Log the change
            self.add_version_change_log(version_id, source, 'activate', activated_by, 
                                    f"Activated version by {activated_by}")
            
            return True
        except Exception as e:
            print(f"Error activating version: {e}")
            return False

    def add_version(self, data: Dict) -> int:
        """Add a new version (called after successful import)"""
        db = self._get_db()
        
        try:
            # Check if version already exists
            existing = db.query_one("""
                SELECT id FROM rate_versions 
                WHERE source = ? AND edition_year = ?
            """, (data.get('source'), data.get('edition_year')))
            
            if existing:
                # Update existing
                db.execute("""
                    UPDATE rate_versions 
                    SET version_name = ?, effective_from = ?, notes = ?,
                        total_parents = ?, total_children = ?, total_rates = ?,
                        release_date = ?
                    WHERE id = ?
                """, (
                    data.get('version_name'),
                    data.get('effective_from'),
                    data.get('notes', ''),
                    data.get('total_parents', 0),
                    data.get('total_children', 0),
                    data.get('total_rates', 0),
                    datetime.now().isoformat(),
                    existing.get('id')
                ))
                version_id = existing.get('id')
            else:
                # Insert new
                db.execute("""
                    INSERT INTO rate_versions 
                    (source, version_name, edition_year, effective_from, created_by, notes, 
                    total_parents, total_children, total_rates, release_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('source'),
                    data.get('version_name'),
                    data.get('edition_year'),
                    data.get('effective_from'),
                    data.get('created_by'),
                    data.get('notes', ''),
                    data.get('total_parents', 0),
                    data.get('total_children', 0),
                    data.get('total_rates', 0),
                    datetime.now().isoformat(),
                    0
                ))
                
                # Get the inserted ID
                result = db.query_one("""
                    SELECT id FROM rate_versions 
                    WHERE source = ? AND edition_year = ?
                    ORDER BY id DESC LIMIT 1
                """, (data.get('source'), data.get('edition_year')))
                version_id = result.get('id') if result else None
            
            return version_id
        except Exception as e:
            print(f"Error adding version: {e}")
            return None

    def archive_version(self, version_id: int, archived_by: str) -> bool:
        """Archive a version (set inactive)"""
        db = self._get_db()
        
        try:
            version = db.query_one("SELECT source FROM rate_versions WHERE id = ?", (version_id,))
            if not version:
                return False
            
            db.execute("UPDATE rate_versions SET is_active = 0 WHERE id = ?", (version_id,))
            
            self.add_version_change_log(version_id, version.get('source'), 'archive', archived_by, 
                                    "Archived version")
            
            return True
        except Exception as e:
            print(f"Error archiving version: {e}")
            return False

    def get_version_stats(self, version_id: int) -> Dict:
        """Get detailed statistics for a specific version"""
        db = self._get_db()
        
        try:
            version = db.query_one("SELECT source FROM rate_versions WHERE id = ?", (version_id,))
            if not version:
                return {'parents': 0, 'children': 0, 'rates': 0}
            
            source = version.get('source')
            
            if source == 'PWD':
                stats = db.query_one("""
                    SELECT 
                        (SELECT COUNT(*) FROM pwd_parents WHERE version_id = ?) as parents,
                        (SELECT COUNT(*) FROM pwd_children WHERE version_id = ?) as children,
                        (SELECT COUNT(*) FROM pwd_rates WHERE version_id = ?) as rates
                """, (version_id, version_id, version_id))
            else:
                stats = db.query_one("""
                    SELECT 
                        (SELECT COUNT(*) FROM lged_parents WHERE version_id = ?) as parents,
                        (SELECT COUNT(*) FROM lged_children WHERE version_id = ?) as children,
                        (SELECT COUNT(*) FROM lged_zone_rates WHERE version_id = ?) as rates
                """, (version_id, version_id, version_id))
            
            return {
                'parents': stats.get('parents', 0) if stats else 0,
                'children': stats.get('children', 0) if stats else 0,
                'rates': stats.get('rates', 0) if stats else 0
            }
        except Exception as e:
            print(f"Error getting version stats: {e}")
            return {'parents': 0, 'children': 0, 'rates': 0}

    def add_version_change_log(self, version_id: int, source: str, action: str, 
                            changed_by: str, details: str) -> bool:
        """Add entry to version change log"""
        db = self._get_db()
        
        try:
            db.execute("""
                INSERT INTO version_change_log (version_id, source, action, changed_by, details, changed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (version_id, source, action, changed_by, details, datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"Error adding version change log: {e}")
            return False

    def get_version_change_log(self, version_id: int = None) -> List[Dict]:
        """Get version change log"""
        db = self._get_db()
        
        if version_id:
            return db.query("""
                SELECT * FROM version_change_log 
                WHERE version_id = ?
                ORDER BY changed_at DESC
            """, (version_id,))
        else:
            return db.query("""
                SELECT * FROM version_change_log 
                ORDER BY changed_at DESC
            """)