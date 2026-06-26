# database/tenant_rate_repository.py

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

class TenantRateRepository:
    """Repository for tenant rate management"""
    
    def __init__(self, db_path: str = "data/tender_system.db"):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========== RATE BOOKS ==========
    
    def create_rate_book(self, data: Dict[str, Any]) -> int:
        """Create a new rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ✅ Include all fields including is_demo
            cursor.execute("""
                INSERT INTO tenant_rate_books (
                    tenant_id, tenant_type, name, source_type, source_version_id,
                    description, is_active, is_archived, is_demo, environment_mode,
                    data_source_type, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['tenant_id'],
                data['tenant_type'],
                data['name'],
                data['source_type'],
                data.get('source_version_id'),
                data.get('description'),
                data.get('is_active', 1),
                data.get('is_archived', 0),
                data.get('is_demo', 0),  # ✅ Ensure is_demo is set
                data.get('environment_mode', 'DEMO'),
                data.get('data_source_type', 'DEMO'),
                data.get('created_by')
            ))
            
            book_id = cursor.lastrowid
            conn.commit()
            return book_id

    
    def get_rate_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a rate book by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rb.*,
                    u.full_name as creator_name,
                    rv.version_name as source_version_name
                FROM tenant_rate_books rb
                LEFT JOIN users u ON rb.created_by = u.id
                LEFT JOIN rate_versions rv ON rb.source_version_id = rv.id
                WHERE rb.id = ?
            """, (book_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_rate_books_by_tenant(
        self, 
        tenant_id: int, 
        tenant_type: str = 'company',
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all rate books for a tenant"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    rb.*,
                    COUNT(DISTINCT ri.id) as item_count,
                    COUNT(DISTINCT rv.id) as version_count,
                    u.full_name as creator_name
                FROM tenant_rate_books rb
                LEFT JOIN tenant_rate_items ri ON rb.id = ri.rate_book_id
                LEFT JOIN tenant_rate_versions rv ON rb.id = rv.rate_book_id
                LEFT JOIN users u ON rb.created_by = u.id
                WHERE rb.tenant_id = ? AND rb.tenant_type = ?
            """
            params = [tenant_id, tenant_type]
            
            if not include_archived:
                query += " AND rb.is_archived = 0"
            
            query += " GROUP BY rb.id ORDER BY rb.created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def update_rate_book(self, book_id: int, data: Dict[str, Any]) -> bool:
        """Update a rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            params = []
            
            allowed_fields = ['name', 'description', 'is_active', 'is_archived']
            for field in allowed_fields:
                if field in data:
                    fields.append(f"{field} = ?")
                    params.append(data[field])
            
            if not fields:
                return False
            
            params.append(datetime.now().isoformat())
            params.append(book_id)
            
            query = f"""
                UPDATE tenant_rate_books 
                SET {', '.join(fields)}, updated_at = ?
                WHERE id = ?
            """
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def archive_rate_book(self, book_id: int) -> bool:
        """Archive a rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tenant_rate_books 
                SET is_archived = 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), book_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_rate_book(self, book_id: int) -> bool:
        """Delete a rate book (cascade will handle child records)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM tenant_rate_books WHERE id = ?", (book_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========== RATE VERSIONS ==========
    
    def create_rate_version(self, data: Dict[str, Any]) -> int:
        """Create a new version of a rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current max version
            cursor.execute("""
                SELECT MAX(version_number) as max_version 
                FROM tenant_rate_versions 
                WHERE rate_book_id = ?
            """, (data['rate_book_id'],))
            
            result = cursor.fetchone()
            next_version = (result['max_version'] or 0) + 1
            
            # Set current version as not current
            if data.get('is_current', False):
                cursor.execute("""
                    UPDATE tenant_rate_versions 
                    SET is_current = 0 
                    WHERE rate_book_id = ?
                """, (data['rate_book_id'],))
            
            cursor.execute("""
                INSERT INTO tenant_rate_versions (
                    rate_book_id, version_number, version_name,
                    effective_from, effective_to, is_current,
                    notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['rate_book_id'],
                next_version,
                data.get('version_name', f"Version {next_version}"),
                data.get('effective_from'),
                data.get('effective_to'),
                data.get('is_current', 1 if next_version == 1 else 0),
                data.get('notes'),
                data.get('created_by')
            ))
            
            version_id = cursor.lastrowid
            conn.commit()
            return version_id
    
    def get_rate_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        """Get a rate version by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rv.*,
                    rb.name as rate_book_name,
                    u.full_name as creator_name
                FROM tenant_rate_versions rv
                JOIN tenant_rate_books rb ON rv.rate_book_id = rb.id
                LEFT JOIN users u ON rv.created_by = u.id
                WHERE rv.id = ?
            """, (version_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_versions_for_book(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rv.*,
                    u.full_name as creator_name,
                    COUNT(DISTINCT pl.id) as pricing_count
                FROM tenant_rate_versions rv
                LEFT JOIN users u ON rv.created_by = u.id
                LEFT JOIN tenant_pricing_levels pl ON rv.id = pl.rate_version_id
                WHERE rv.rate_book_id = ?
                GROUP BY rv.id
                ORDER BY rv.version_number DESC
            """, (book_id,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def set_current_version(self, version_id: int) -> bool:
        """Set a version as the current version"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the book ID
            cursor.execute("SELECT rate_book_id FROM tenant_rate_versions WHERE id = ?", (version_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            book_id = result['rate_book_id']
            
            # Set all versions for this book as not current
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
            return True
    
    # ========== RATE ITEMS ==========
    
    def create_rate_item(self, data: Dict[str, Any]) -> int:
        """Create a rate item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tenant_rate_items (
                    rate_book_id, master_reference_id, master_reference_type,
                    item_code, item_description, unit, is_custom,
                    is_active, display_order, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['rate_book_id'],
                data.get('master_reference_id'),
                data.get('master_reference_type'),
                data['item_code'],
                data['item_description'],
                data.get('unit'),
                data.get('is_custom', 0),
                data.get('is_active', 1),
                data.get('display_order', 0),
                data.get('created_by')
            ))
            
            item_id = cursor.lastrowid
            
            # If this is the first version, create default pricing
            cursor.execute("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = 1
            """, (data['rate_book_id'],))
            
            version = cursor.fetchone()
            
            if version and not data.get('skip_pricing', False):
                # Create default pricing levels
                for level in ['ECONOMY', 'MARKET', 'PREMIUM']:
                    cursor.execute("""
                        INSERT INTO tenant_pricing_levels (
                            rate_version_id, rate_item_id, pricing_level,
                            price, currency, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        version['id'],
                        item_id,
                        level,
                        0.0,
                        'BDT',
                        data.get('created_by')
                    ))
            
            conn.commit()
            return item_id
    
    def get_rate_items_by_book(
        self, 
        book_id: int, 
        version_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all rate items for a book, optionally with pricing for a specific version"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    ri.*,
                    GROUP_CONCAT(pl.pricing_level || ':' || pl.price) as pricing_data
                FROM tenant_rate_items ri
            """
            
            if version_id:
                query += """
                    LEFT JOIN tenant_pricing_levels pl 
                    ON ri.id = pl.rate_item_id AND pl.rate_version_id = ?
                """
            else:
                query += """
                    LEFT JOIN tenant_pricing_levels pl 
                    ON ri.id = pl.rate_item_id
                """
            
            query += " WHERE ri.rate_book_id = ?"
            
            if active_only:
                query += " AND ri.is_active = 1"
            
            query += " GROUP BY ri.id ORDER BY ri.display_order, ri.item_code"
            
            params = [version_id, book_id] if version_id else [book_id]
            cursor.execute(query, params)
            
            results = cursor.fetchall()
            items = []
            
            for row in results:
                item = dict(row)
                if item.get('pricing_data'):
                    # Parse pricing data
                    pricing = {}
                    for p in item['pricing_data'].split(','):
                        if ':' in p:
                            level, price = p.split(':', 1)
                            pricing[level] = float(price) if price else None
                    item['pricing'] = pricing
                    del item['pricing_data']
                
                items.append(item)
            
            return items
    
    def update_rate_item(self, item_id: int, data: Dict[str, Any]) -> bool:
        """Update a rate item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            params = []
            
            allowed_fields = ['item_code', 'item_description', 'unit', 'is_active', 'display_order']
            for field in allowed_fields:
                if field in data:
                    fields.append(f"{field} = ?")
                    params.append(data[field])
            
            if not fields:
                return False
            
            params.append(datetime.now().isoformat())
            params.append(item_id)
            
            query = f"""
                UPDATE tenant_rate_items 
                SET {', '.join(fields)}, updated_at = ?
                WHERE id = ?
            """
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_rate_item(self, item_id: int) -> bool:
        """Delete a rate item (cascade will handle pricing)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM tenant_rate_items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========== PRICING LEVELS ==========
    
    def update_pricing(
        self, 
        version_id: int, 
        item_id: int, 
        pricing_level: str, 
        price: float,
        user_id: int
    ) -> bool:
        """Update pricing for a specific item and version"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current pricing for audit
            cursor.execute("""
                SELECT price FROM tenant_pricing_levels 
                WHERE rate_version_id = ? AND rate_item_id = ? AND pricing_level = ?
            """, (version_id, item_id, pricing_level))
            
            old_result = cursor.fetchone()
            old_price = old_result['price'] if old_result else None
            
            # Update or insert
            if old_result:
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET price = ?, updated_at = ?
                    WHERE rate_version_id = ? AND rate_item_id = ? AND pricing_level = ?
                """, (price, datetime.now().isoformat(), version_id, item_id, pricing_level))
            else:
                cursor.execute("""
                    INSERT INTO tenant_pricing_levels (
                        rate_version_id, rate_item_id, pricing_level,
                        price, currency, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (version_id, item_id, pricing_level, price, 'BDT', user_id))
            
            # Audit log
            cursor.execute("""
                INSERT INTO tenant_rate_audit (
                    rate_item_id, pricing_level_id, action,
                    field_name, old_value, new_value, user_id
                ) VALUES (
                    ?, 
                    (SELECT id FROM tenant_pricing_levels 
                     WHERE rate_version_id = ? AND rate_item_id = ? AND pricing_level = ?),
                    'UPDATE', 'price', ?, ?, ?
                )
            """, (item_id, version_id, item_id, pricing_level, 
                  str(old_price) if old_price is not None else None, 
                  str(price), user_id))
            
            conn.commit()
            return True
    
    def get_item_pricing(
        self, 
        item_id: int, 
        version_id: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get all pricing for an item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    pl.pricing_level,
                    pl.price,
                    pl.currency,
                    pl.effective_from,
                    pl.effective_to,
                    pl.notes,
                    rv.version_number,
                    rv.is_current
                FROM tenant_pricing_levels pl
                JOIN tenant_rate_versions rv ON pl.rate_version_id = rv.id
                WHERE pl.rate_item_id = ?
            """
            params = [item_id]
            
            if version_id:
                query += " AND pl.rate_version_id = ?"
                params.append(version_id)
            
            query += " ORDER BY rv.version_number DESC, pl.pricing_level"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            pricing = {}
            for row in results:
                level = row['pricing_level']
                if level not in pricing:
                    pricing[level] = []
                pricing[level].append(dict(row))
            
            return pricing
    
    # ========== CLONE FROM MASTER ==========
    
    def clone_pwd_master(
        self, 
        rate_book_id: int, 
        version_id: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clone PWD master rates to a tenant rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the rate book
            cursor.execute("""
                SELECT * FROM tenant_rate_books WHERE id = ?
            """, (rate_book_id,))
            
            book = cursor.fetchone()
            if not book:
                return {'success': False, 'error': 'Rate book not found'}
            
            # Get PWD rates to clone
            query = """
                SELECT 
                    pc.pwd_code as item_code,
                    pc.description as item_description,
                    pc.unit,
                    pc.edition_year,
                    pp.chapter_number,
                    pr.zone_name,
                    pr.unit_rate
                FROM pwd_children pc
                JOIN pwd_parents pp ON pc.parent_code = pp.pwd_code
                LEFT JOIN pwd_rates pr ON pc.pwd_code = pr.pwd_code
                WHERE 1=1
            """
            params = []
            
            if filters:
                if filters.get('chapter_number'):
                    query += " AND pp.chapter_number = ?"
                    params.append(filters['chapter_number'])
                if filters.get('edition_year'):
                    query += " AND pc.edition_year = ?"
                    params.append(filters['edition_year'])
            
            cursor.execute(query, params)
            master_items = cursor.fetchall()
            
            items_created = 0
            
            for master in master_items:
                # Check if item already exists
                cursor.execute("""
                    SELECT id FROM tenant_rate_items 
                    WHERE rate_book_id = ? AND item_code = ?
                """, (rate_book_id, master['item_code']))
                
                existing = cursor.fetchone()
                
                if not existing:
                    # Create item
                    cursor.execute("""
                        INSERT INTO tenant_rate_items (
                            rate_book_id, master_reference_id, master_reference_type,
                            item_code, item_description, unit, is_custom
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rate_book_id,
                        None,  # We don't track specific PWD reference ID
                        'PWD',
                        master['item_code'],
                        master['item_description'],
                        master['unit'],
                        0
                    ))
                    
                    item_id = cursor.lastrowid
                    
                    # Create pricing from master rates
                    if master['unit_rate']:
                        # Use PWD rate as MARKET price
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'MARKET',
                            master['unit_rate'],
                            'BDT'
                        ))
                        
                        # ECONOMY = market * 0.85
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'ECONOMY',
                            master['unit_rate'] * 0.85,
                            'BDT'
                        ))
                        
                        # PREMIUM = market * 1.15
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'PREMIUM',
                            master['unit_rate'] * 1.15,
                            'BDT'
                        ))
                    
                    items_created += 1
            
            conn.commit()
            return {
                'success': True, 
                'items_created': items_created,
                'message': f'Cloned {items_created} items from PWD master rates'
            }
    
    def clone_lged_master(
        self, 
        rate_book_id: int, 
        version_id: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clone LGED master rates to a tenant rate book"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get LGED rates to clone
            query = """
                SELECT 
                    lc.code as item_code,
                    lc.description as item_description,
                    lc.unit,
                    lc.edition_year,
                    lp.chapter_number,
                    lp.section_number,
                    lzr.zone_name,
                    lzr.unit_rate
                FROM lged_children lc
                JOIN lged_parents lp ON lc.parent_code = lp.code
                LEFT JOIN lged_zone_rates lzr ON lc.id = lzr.child_id
                WHERE 1=1
            """
            params = []
            
            if filters:
                if filters.get('chapter_number'):
                    query += " AND lp.chapter_number = ?"
                    params.append(filters['chapter_number'])
                if filters.get('section_number'):
                    query += " AND lp.section_number = ?"
                    params.append(filters['section_number'])
                if filters.get('edition_year'):
                    query += " AND lc.edition_year = ?"
                    params.append(filters['edition_year'])
            
            cursor.execute(query, params)
            master_items = cursor.fetchall()
            
            items_created = 0
            
            for master in master_items:
                # Check if item already exists
                cursor.execute("""
                    SELECT id FROM tenant_rate_items 
                    WHERE rate_book_id = ? AND item_code = ?
                """, (rate_book_id, master['item_code']))
                
                existing = cursor.fetchone()
                
                if not existing:
                    # Create item
                    cursor.execute("""
                        INSERT INTO tenant_rate_items (
                            rate_book_id, master_reference_id, master_reference_type,
                            item_code, item_description, unit, is_custom
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rate_book_id,
                        None,
                        'LGED',
                        master['item_code'],
                        master['item_description'],
                        master['unit'],
                        0
                    ))
                    
                    item_id = cursor.lastrowid
                    
                    # Create pricing from master rates
                    if master['unit_rate']:
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'MARKET',
                            master['unit_rate'],
                            'BDT'
                        ))
                        
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'ECONOMY',
                            master['unit_rate'] * 0.85,
                            'BDT'
                        ))
                        
                        cursor.execute("""
                            INSERT INTO tenant_pricing_levels (
                                rate_version_id, rate_item_id, pricing_level,
                                price, currency
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            version_id,
                            item_id,
                            'PREMIUM',
                            master['unit_rate'] * 1.15,
                            'BDT'
                        ))
                    
                    items_created += 1
            
            conn.commit()
            return {
                'success': True,
                'items_created': items_created,
                'message': f'Cloned {items_created} items from LGED master rates'
            }
    
    # ========== AUDIT ==========
    
    def get_audit_log(
        self,
        book_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    tra.*,
                    u.full_name as user_name,
                    rb.name as rate_book_name,
                    ri.item_code,
                    ri.item_description
                FROM tenant_rate_audit tra
                LEFT JOIN users u ON tra.user_id = u.id
                LEFT JOIN tenant_rate_books rb ON tra.rate_book_id = rb.id
                LEFT JOIN tenant_rate_items ri ON tra.rate_item_id = ri.id
                WHERE 1=1
            """
            params = []
            
            if book_id:
                query += " AND tra.rate_book_id = ?"
                params.append(book_id)
            
            if user_id:
                query += " AND tra.user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY tra.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    # ========== IMPORT/EXPORT ==========
    
    def log_import(self, data: Dict[str, Any]) -> int:
        """Log an import operation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tenant_rate_import_log (
                    rate_book_id, file_name, import_type,
                    total_records, successful_records, failed_records,
                    error_log, imported_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['rate_book_id'],
                data['file_name'],
                data['import_type'],
                data.get('total_records', 0),
                data.get('successful_records', 0),
                data.get('failed_records', 0),
                data.get('error_log'),
                data.get('imported_by')
            ))
            
            log_id = cursor.lastrowid
            conn.commit()
            return log_id
    
    def log_export(self, data: Dict[str, Any]) -> int:
        """Log an export operation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tenant_rate_export_log (
                    rate_book_id, file_name, export_type,
                    total_records, exported_by
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                data['rate_book_id'],
                data['file_name'],
                data['export_type'],
                data.get('total_records', 0),
                data.get('exported_by')
            ))
            
            log_id = cursor.lastrowid
            conn.commit()
            return log_id