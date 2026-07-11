# database/crud_system_rates.py - Complete Rate CRUD with all methods

"""
CRUD Operations for Rate Management Module
All database operations for rates, zones, chapters, parents, children, and versions
"""

from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import logging
import json
from database.connection import is_supabase, get_db_type
import pandas as pd

logger = logging.getLogger(__name__)


class SystemRateCRUD:
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
     
    # =========================================================
    # PWD METHODS - Refactored to Unified Pattern
    # =========================================================
    
    # ---------- PWD Chapters ----------
    def get_pwd_chapters(self) -> pd.DataFrame:
        """Get PWD chapters as DataFrame"""
        db = self._get_db()
        results = db.query("""
            SELECT chapter_number, chapter_name, description 
            FROM pwd_chapters 
            ORDER BY CAST(chapter_number AS INTEGER)
        """)
        return pd.DataFrame(results) if results else pd.DataFrame()
    def get_pwd_chapters_dict(self) -> List[Dict]:
        """Get PWD chapters as list of dictionaries"""
        try:
            db = self._get_db()
            
            # Use db.query which handles both SQLite and Supabase
            result = db.query("""
                SELECT chapter_number, chapter_name, description 
                FROM pwd_chapters 
                ORDER BY chapter_number
            """)
            
            return result if result else []
            
        except Exception as e:
            print(f"❌ Error getting PWD chapters: {e}")
            return []

    # ---------- PWD Parents ----------
    def get_pwd_parents(self, chapter_number: str = None) -> pd.DataFrame:
        """Get PWD parents as DataFrame"""
        db = self._get_db()
        query = """
            SELECT pwd_code, description, chapter_number
            FROM pwd_parents
        """
        params = None
        if chapter_number:
            query += " WHERE chapter_number = ?"
            params = (chapter_number,)
        query += " ORDER BY pwd_code"
        
        results = db.query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_parents_dict(self, chapter_number: str = None) -> List[Dict]:
        """Get PWD parents as list of dictionaries"""
        db = self._get_db()
        query = """
            SELECT pwd_code, description, chapter_number
            FROM pwd_parents
        """
        params = None
        if chapter_number:
            query += " WHERE chapter_number = ?"
            params = (chapter_number,)
        query += " ORDER BY pwd_code"
        
        try:
            result = db.query(query, params)
            return result if result else []
        except Exception as e:
            print(f"Error getting PWD parents: {e}")
            return []

    
    # ---------- PWD Children ----------
    def get_pwd_children(self, parent_code: str = None, limit: int = 100) -> pd.DataFrame:
        """Get PWD children as DataFrame"""
        db = self._get_db()
        
        if parent_code:
            query = """
                SELECT c.pwd_code, c.description, c.unit, c.parent_code,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code
                LIMIT ?
            """
            params = (parent_code, limit)
        else:
            query = """
                SELECT c.pwd_code, c.description, c.unit, c.parent_code,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                ORDER BY c.pwd_code
                LIMIT ?
            """
            params = (limit,)
        
        results = db.query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_children_dict(self, parent_code: str = None, limit: int = 100) -> List[Dict]:
        """Get PWD children as list of dictionaries"""
        db = self._get_db()
        
        if parent_code:
            query = """
                SELECT c.pwd_code, c.description, c.unit, c.parent_code,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code
                LIMIT ?
            """
            params = (parent_code, limit)
        else:
            query = """
                SELECT c.pwd_code, c.description, c.unit, c.parent_code,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                ORDER BY c.pwd_code
                LIMIT ?
            """
            params = (limit,)
        
        return db.query(query, params)
    
    # ---------- PWD Rates ----------
    def get_pwd_rates(self, pwd_code: str = None, zone: str = None) -> pd.DataFrame:
        """Get PWD rates as DataFrame"""
        db = self._get_db()
        query = """
            SELECT pwd_code, zone_name, unit_rate, edition_year
            FROM pwd_rates
            WHERE 1=1
        """
        params = []
        if pwd_code:
            query += " AND pwd_code = ?"
            params.append(pwd_code)
        if zone:
            query += " AND zone_name = ?"
            params.append(zone)
        query += " ORDER BY pwd_code, zone_name"
        
        results = db.query(query, tuple(params) if params else None)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_rates_dict(self, pwd_code: str = None, zone: str = None) -> List[Dict]:
        """Get PWD rates as list of dictionaries"""
        db = self._get_db()
        query = """
            SELECT pwd_code, zone_name, unit_rate, edition_year
            FROM pwd_rates
            WHERE 1=1
        """
        params = []
        if pwd_code:
            query += " AND pwd_code = ?"
            params.append(pwd_code)
        if zone:
            query += " AND zone_name = ?"
            params.append(zone)
        query += " ORDER BY pwd_code, zone_name"
        
        return db.query(query, tuple(params) if params else None)
    
    def get_pwd_stats_v1(self, chapter_code: str = None) -> Dict:
        """Get statistics for PWD schedule"""
        db = self._get_db()
        
        query = """
            SELECT COUNT(*) as total_items,
                   AVG(rate_bdt) as avg_rate,
                   MIN(rate_bdt) as min_rate,
                   MAX(rate_bdt) as max_rate
            FROM pwd_chapters
            WHERE rate_bdt IS NOT NULL
        """
        params = None
        if chapter_code:
            query += " AND chapter_code = ?"
            params = (chapter_code,)
        
        result = db.query_one(query, params)
        return result or {}
    def update_pwd_chapter(self, version_id: int, chapter_num: str, hierarchy: Dict,
                      edition_year: int, notes: str, updated_by: str) -> Dict:
        """Update a specific chapter in an existing version"""
        db = self._get_db()
        
        try:
            # Delete existing data for this chapter
            # Delete rates
            db.execute("""
                DELETE FROM pwd_rates 
                WHERE pwd_code IN (
                    SELECT pwd_code FROM pwd_children 
                    WHERE version_id = ? AND chapter_number = ?
                )
            """, (version_id, chapter_num))
            
            # Delete children
            db.execute("""
                DELETE FROM pwd_children 
                WHERE version_id = ? AND chapter_number = ?
            """, (version_id, chapter_num))
            
            # Delete parents
            db.execute("""
                DELETE FROM pwd_parents 
                WHERE version_id = ? AND chapter_number = ?
            """, (version_id, chapter_num))
            
            # Save parents
            parents_saved = 0
            for parent in hierarchy.get('parents', []):
                db.execute("""
                    INSERT OR REPLACE INTO pwd_parents 
                    (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (parent['code'], parent.get('description', ''), chapter_num, version_id))
                parents_saved += 1
            
            # Save children and rates
            children_saved = 0
            rates_saved = 0
            
            for child in hierarchy.get('children', []):
                code = child.get('pwd_code') or child.get('code')
                if not code:
                    continue
                
                parent_code = child.get('parent_code') or code
                
                db.execute("""
                    INSERT OR REPLACE INTO pwd_children (
                        pwd_code, parent_code, description, unit,
                        edition_year, version_id, chapter_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (code, parent_code, child.get('description', ''),
                    child.get('unit', ''), edition_year, version_id, chapter_num))
                children_saved += 1
                
                for zone, rate in child.get('rates', {}).items():
                    db.execute("""
                        INSERT OR REPLACE INTO pwd_rates 
                        (pwd_code, zone_name, unit_rate, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (code, zone, float(rate), edition_year, version_id))
                    rates_saved += 1
            
            # Log the change
            db.execute("""
                INSERT INTO version_change_log (version_id, source, action, changed_by, details)
                VALUES (?, 'PWD', 'update_chapter', ?, ?)
            """, (version_id, updated_by, f"Updated Chapter {chapter_num}: {notes}"))
            
            return {
                'success': True,
                'message': f"Chapter {chapter_num} updated successfully",
                'stats': {
                    'parents': parents_saved,
                    'children': children_saved,
                    'rates': rates_saved
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating PWD chapter: {e}")
            return {'success': False, 'message': str(e)}
    # ---------- PWD Hierarchy Save ----------
    def save_pwd_hierarchy_enhanced(self, hierarchy, version_name, edition_year,
                                    effective_date=None, selected_chapters=None):
        """
        Save PWD hierarchy with robust version handling and safe inserts.
        """
        from datetime import date
        import json
        import datetime as dt
        
        db = self._get_db()
        
        effective_date = effective_date or date.today()
        
        try:
            # Get next version number
            max_result = db.query_one("""
                SELECT MAX(version_number) as max_num 
                FROM rate_versions
                WHERE source = 'PWD' AND edition_year = ?
            """, (edition_year,))
            
            max_val = max_result.get('max_num') if max_result else None
            next_version = 1 if max_val is None else int(max_val) + 1
            
            # Deactivate current active version
            db.execute("""
                UPDATE rate_versions
                SET is_active = 0, updated_at = ?
                WHERE source = 'PWD' AND edition_year = ? AND is_active = 1
            """, (dt.datetime.now().isoformat(), edition_year))
            
            # Create new version record
            version_id = db.execute("""
                INSERT INTO rate_versions (
                    source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, created_by,
                    has_sections, created_at
                ) VALUES ('PWD', ?, ?, ?, ?, 1, ?, ?, 0, ?)
            """, (version_name, edition_year, next_version, 
                  effective_date.isoformat() if hasattr(effective_date, 'isoformat') else effective_date,
                  dt.datetime.now().isoformat(), 'system', dt.datetime.now().isoformat()))
            
            # Note: version_id is rowcount, not the actual ID
            # Get the inserted ID
            version_record = db.query_one("""
                SELECT id FROM rate_versions 
                WHERE source = 'PWD' AND version_number = ? AND edition_year = ?
            """, (next_version, edition_year))
            
            version_id = version_record.get('id') if version_record else None
            
            # Save chapters
            chapter_ids = {}
            if selected_chapters:
                for chapter_num, chapter_info in selected_chapters.items():
                    db.execute("""
                        INSERT INTO rate_chapters (
                            source, version_id, chapter_number,
                            chapter_name, description, display_order
                        ) VALUES ('PWD', ?, ?, ?, ?, ?)
                    """, (version_id, chapter_num,
                          chapter_info.get('name', f'Chapter {chapter_num}'),
                          chapter_info.get('description', ''),
                          int(str(chapter_num)) if str(chapter_num).isdigit() else 999))
            
            # Save parents
            parents_saved = 0
            for parent in hierarchy.get('parents', []):
                ch_num = parent.get('chapter_number') or parent.get('chapter') or ''
                db.execute("""
                    INSERT OR REPLACE INTO pwd_parents 
                    (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (parent['code'], parent.get('description', ''), ch_num, version_id))
                parents_saved += 1
            
            # Save children and rates
            children_saved = 0
            rates_saved = 0
            
            for child in hierarchy.get('children', []):
                code = child.get('pwd_code') or child.get('code')
                if not code:
                    continue
                
                parent_code = child.get('parent_code') or code
                ch_num = child.get('chapter_number') or ''
                
                db.execute("""
                    INSERT OR REPLACE INTO pwd_children (
                        pwd_code, parent_code, description, unit,
                        edition_year, version_id, chapter_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (code, parent_code, child.get('description', ''),
                      child.get('unit', ''), edition_year, version_id, ch_num))
                children_saved += 1
                
                # Save rates
                for zone, rate in child.get('rates', {}).items():
                    db.execute("""
                        INSERT OR REPLACE INTO pwd_rates 
                        (pwd_code, zone_name, unit_rate, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (code, zone, float(rate), edition_year, version_id))
                    rates_saved += 1
            
            # Update version statistics
            db.execute("""
                UPDATE rate_versions
                SET total_parents = ?, total_children = ?, total_rates = ?,
                    chapter_numbers = ?
                WHERE id = ?
            """, (parents_saved, children_saved, rates_saved,
                  json.dumps(list(chapter_ids.keys())), version_id))
            
            return version_id
            
        except Exception as e:
            logger.error(f"Error saving PWD hierarchy: {e}")
            raise
    
    # ---------- PWD Parent/Child Methods for Admin Dashboard ----------
    def get_pwd_parents_filtered(self, chapter: Optional[str] = None, search: Optional[str] = None) -> List[Dict]:
        """Get PWD parents with filters (for admin dashboard)"""
        db = self._get_db()
        
        query = "SELECT pwd_code, description, chapter_number FROM pwd_parents"
        params = []
        conditions = []
        
        if chapter and chapter != "All":
            conditions.append("chapter_number = ?")
            params.append(chapter)
        
        if search:
            conditions.append("(pwd_code LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY pwd_code"
        
        return db.query(query, tuple(params) if params else None)
    
    def get_pwd_children_by_parent(self, parent_code: str) -> List[Dict]:
        """Get PWD children and rates for a specific parent"""
        db = self._get_db()
        
        try:
            result = db.query("""
                SELECT c.pwd_code, c.description, c.unit,
                    cr.zone_name, cr.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates cr ON c.pwd_code = cr.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code, cr.zone_name
            """, (parent_code,))
            return result if result else []
        except Exception as e:
            print(f"Error getting PWD children: {e}")
            return []
    # =========================================================
    # LGED METHODS - Refactored to Unified Pattern
    # =========================================================
    
    # ---------- LGED Chapters ----------
    def get_lged_chapters(self) -> pd.DataFrame:
        """Get LGED chapters as DataFrame"""
        db = self._get_db()
        results = db.query("""
            SELECT chapter_number, chapter_name, description 
            FROM lged_chapters 
            ORDER BY CAST(chapter_number AS INTEGER)
        """)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_chapters_dict(self) -> List[Dict]:
        """Get LGED chapters as list of dictionaries"""
        db = self._get_db()
        return db.query("""
            SELECT chapter_number, chapter_name, description 
            FROM lged_chapters 
            ORDER BY CAST(chapter_number AS INTEGER)
        """)
    
    # ---------- LGED Sections ----------
    def get_lged_sections(self, chapter_number: str = None) -> pd.DataFrame:
        """Get LGED sections as DataFrame"""
        db = self._get_db()
        if chapter_number:
            query = """
                SELECT section_number, section_name, description
                FROM lged_sections
                WHERE chapter_number = ?
                ORDER BY section_number
            """
            params = (chapter_number,)
        else:
            query = """
                SELECT chapter_number, section_number, section_name, description
                FROM lged_sections
                ORDER BY chapter_number, section_number
            """
            params = None
        
        results = db.query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_sections_dict(self, chapter_number: str = None) -> List[Dict]:
        """Get LGED sections as list of dictionaries"""
        db = self._get_db()
        if chapter_number:
            query = """
                SELECT section_number, section_name, description
                FROM lged_sections
                WHERE chapter_number = ?
                ORDER BY section_number
            """
            params = (chapter_number,)
        else:
            query = """
                SELECT chapter_number, section_number, section_name, description
                FROM lged_sections
                ORDER BY chapter_number, section_number
            """
            params = None
        
        return db.query(query, params)
    
    # ---------- LGED Parents ----------
    def get_lged_parents(self, chapter_number: str = None, section_number: str = None) -> pd.DataFrame:
        """Get LGED parents as DataFrame"""
        db = self._get_db()
        query = """
            SELECT code, description, chapter_number, section_number, 
                parent_type, has_children, unit
            FROM lged_parents
            WHERE 1=1
        """
        params = []
        if chapter_number:
            query += " AND chapter_number = ?"
            params.append(chapter_number)
        if section_number:
            query += " AND section_number = ?"
            params.append(section_number)
        query += " ORDER BY code"
        
        results = db.query(query, tuple(params) if params else None)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_parents_dict(self, chapter_number: str = None, section_number: str = None) -> List[Dict]:
        """Get LGED parents as list of dictionaries"""
        db = self._get_db()
        query = """
            SELECT code, description, chapter_number, section_number, 
                parent_type, has_children, unit
            FROM lged_parents
            WHERE 1=1
        """
        params = []
        if chapter_number:
            query += " AND chapter_number = ?"
            params.append(chapter_number)
        if section_number:
            query += " AND section_number = ?"
            params.append(section_number)
        query += " ORDER BY code"
        
        return db.query(query, tuple(params) if params else None)
    
    # ---------- LGED Children ----------
    def get_lged_children(self, parent_code: str = None, chapter_number: str = None, limit: int = 100) -> pd.DataFrame:
        """Get LGED children as DataFrame"""
        db = self._get_db()
        query = """
            SELECT code, parent_code, description, unit,
                chapter_number, section_number,
                zone_a, zone_b, zone_c, zone_d
            FROM lged_children
            WHERE 1=1
        """
        params = []
        if parent_code:
            query += " AND parent_code = ?"
            params.append(parent_code)
        if chapter_number:
            query += " AND chapter_number = ?"
            params.append(chapter_number)
        query += " ORDER BY code LIMIT ?"
        params.append(limit)
        
        results = db.query(query, tuple(params))
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_children_dict(self, parent_code: str = None, chapter_number: str = None, limit: int = 100) -> List[Dict]:
        """Get LGED children as list of dictionaries"""
        db = self._get_db()
        query = """
            SELECT code, parent_code, description, unit,
                chapter_number, section_number,
                zone_a, zone_b, zone_c, zone_d
            FROM lged_children
            WHERE 1=1
        """
        params = []
        if parent_code:
            query += " AND parent_code = ?"
            params.append(parent_code)
        if chapter_number:
            query += " AND chapter_number = ?"
            params.append(chapter_number)
        query += " ORDER BY code LIMIT ?"
        params.append(limit)
        
        return db.query(query, tuple(params))
    
    # ---------- LGED Zone Rates ----------
    def get_lged_zone_rates(self, child_id: int = None) -> pd.DataFrame:
        """Get LGED zone rates as DataFrame"""
        db = self._get_db()
        if child_id:
            query = """
                SELECT zone_name, unit_rate
                FROM lged_zone_rates
                WHERE child_id = ?
                ORDER BY zone_name
            """
            params = (child_id,)
        else:
            query = """
                SELECT child_id, zone_name, unit_rate
                FROM lged_zone_rates
                ORDER BY child_id, zone_name
            """
            params = None
        
        results = db.query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_zone_rates_dict(self, child_id: int = None) -> List[Dict]:
        """Get LGED zone rates as list of dictionaries"""
        db = self._get_db()
        if child_id:
            query = """
                SELECT zone_name, unit_rate
                FROM lged_zone_rates
                WHERE child_id = ?
                ORDER BY zone_name
            """
            params = (child_id,)
        else:
            query = """
                SELECT child_id, zone_name, unit_rate
                FROM lged_zone_rates
                ORDER BY child_id, zone_name
            """
            params = None
        
        return db.query(query, params)
    
    # ---------- LGED Zone Mapping ----------
    def get_lged_zone_mapping(self) -> pd.DataFrame:
        """Get LGED zone mapping as DataFrame"""
        db = self._get_db()
        results = db.query("""
            SELECT zone_code, zone_name, divisions, accessibility_bonus, description
            FROM lged_zone_mapping
            ORDER BY zone_code
        """)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_zone_mapping_dict(self) -> List[Dict]:
        """Get LGED zone mapping as list of dictionaries"""
        db = self._get_db()
        return db.query("""
            SELECT zone_code, zone_name, divisions, accessibility_bonus, description
            FROM lged_zone_mapping
            ORDER BY zone_code
        """)
    
    # ---------- LGED Hierarchy Save ----------
    def save_lged_hierarchy_enhanced(self, hierarchy, version_name, edition_year, 
                                      effective_date=None, selected_chapters=None, 
                                      selected_sections=None):
        """
        Save LGED hierarchy with support for section headers and leaf items.
        """
        from datetime import date
        import json
        
        db = self._get_db()
        effective_date = effective_date or date.today()
        has_sections = selected_sections is not None and len(selected_sections) > 0
        
        try:
            # Create version record
            version_id = db.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, 
                                        is_active, release_date, created_by, has_sections)
                VALUES ('LGED', ?, ?, ?, 1, ?, ?, ?)
            """, (version_name, edition_year, 
                  effective_date.isoformat() if hasattr(effective_date, 'isoformat') else effective_date,
                  datetime.now().isoformat(), 'system', 1 if has_sections else 0))
            
            # Get the inserted ID
            version_record = db.query_one("""
                SELECT id FROM rate_versions 
                WHERE source = 'LGED' AND version_name = ? AND edition_year = ?
                ORDER BY id DESC LIMIT 1
            """, (version_name, edition_year))
            
            version_id = version_record.get('id') if version_record else None
            
            # Save section headers
            section_headers = hierarchy.get('section_headers', [])
            leaf_items = hierarchy.get('leaf_items', [])
            children = hierarchy.get('children', [])
            
            # Save section headers
            for header in section_headers:
                db.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', ''), 
                      header.get('chapter_number', ''), header.get('section_number', ''),
                      1 if header.get('has_children') else 0, version_id))
            
            # Save leaf items
            for leaf in leaf_items:
                db.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, unit, version_id)
                    VALUES (?, ?, ?, ?, 'leaf_item', 0, ?, ?)
                """, (leaf['code'], leaf.get('description', ''), 
                      leaf.get('chapter_number', ''), leaf.get('section_number', ''),
                      leaf.get('unit', ''), version_id))
                
                # Save rates for leaf items
                for zone, rate in leaf.get('rates', {}).items():
                    db.execute("""
                        INSERT INTO lged_zone_rates (parent_id, zone_name, unit_rate, version_id)
                        VALUES (?, ?, ?, ?)
                    """, (leaf['code'], zone, rate, version_id))
            
            # Save child items
            for child in children:
                db.execute("""
                    INSERT INTO lged_children (code, parent_code, description, unit, 
                                            chapter_number, section_number,
                                            zone_a, zone_b, zone_c, zone_d,
                                            edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (child['code'], child.get('parent_code', ''), child.get('description', ''), 
                      child.get('unit', ''),
                      child.get('chapter_number', ''), child.get('section_number', ''),
                      child.get('zone_a'), child.get('zone_b'), 
                      child.get('zone_c'), child.get('zone_d'),
                      edition_year, version_id))
            
            # Update version statistics
            db.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?
                WHERE id = ?
            """, (len(section_headers) + len(leaf_items), len(children), 
                  len(leaf_items) + len(children), version_id))
            
            return version_id
            
        except Exception as e:
            logger.error(f"Error saving LGED hierarchy: {e}")
            raise
    
    def save_lged_hierarchy(self, hierarchy, version_name, edition_year, effective_date=None):
        """Save LGED hierarchy to database"""
        from datetime import date
        
        db = self._get_db()
        effective_date = effective_date or date.today()
        
        # Create version record
        version_id = db.execute("""
            INSERT INTO rate_versions (source, version_name, edition_year, effective_from, 
                                    is_active, release_date, created_by)
            VALUES ('LGED', ?, ?, ?, 1, ?, ?)
        """, (version_name, edition_year, 
              effective_date.isoformat() if hasattr(effective_date, 'isoformat') else effective_date,
              datetime.now().isoformat(), 'system'))
        
        # Get the inserted ID
        version_record = db.query_one("""
            SELECT id FROM rate_versions 
            WHERE source = 'LGED' AND version_name = ? AND edition_year = ?
            ORDER BY id DESC LIMIT 1
        """, (version_name, edition_year))
        
        version_id = version_record.get('id') if version_record else None
        
        # Insert parents
        parents_saved = 0
        for parent in hierarchy.get('parents', []):
            db.execute("""
                INSERT INTO lged_parents (code, description, chapter_number, version_id)
                VALUES (?, ?, ?, ?)
            """, (parent['code'], parent.get('description', ''), 
                  parent.get('chapter', ''), version_id))
            parents_saved += 1
        
        # Insert children
        children_saved = 0
        rates_saved = 0
        
        for child in hierarchy.get('children', []):
            db.execute("""
                INSERT INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (child['code'], child.get('parent_code', ''), child.get('description', ''), 
                  child.get('unit', ''), edition_year, version_id))
            children_saved += 1
            
            # Insert zone rates
            for zone, rate in child.get('rates', {}).items():
                db.execute("""
                    INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                    VALUES (?, ?, ?, ?)
                """, (child['code'], zone, rate, version_id))
                rates_saved += 1
        
        # Update version statistics
        db.execute("""
            UPDATE rate_versions 
            SET total_parents = ?, total_children = ?, total_rates = ?
            WHERE id = ?
        """, (parents_saved, children_saved, rates_saved, version_id))
        
        return version_id
    
    # =========================================================
    # RATE VERSIONS METHODS - Refactored to Unified Pattern
    # =========================================================
    
    def get_rate_versions(self, source: str = None) -> pd.DataFrame:
        """Get rate versions as DataFrame"""
        db = self._get_db()
        if source:
            query = """
                SELECT id, source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, notes,
                    total_parents, total_children, total_rates
                FROM rate_versions
                WHERE source = ?
                ORDER BY edition_year DESC, version_number DESC
            """
            params = (source,)
        else:
            query = """
                SELECT id, source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, notes,
                    total_parents, total_children, total_rates
                FROM rate_versions
                ORDER BY source, edition_year DESC, version_number DESC
            """
            params = None
        
        results = db.query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_rate_versions_dict(self, source: str = None) -> List[Dict]:
        """Get rate versions as list of dictionaries"""
        db = self._get_db()
        if source:
            query = """
                SELECT id, source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, notes,
                    total_parents, total_children, total_rates
                FROM rate_versions
                WHERE source = ?
                ORDER BY edition_year DESC, version_number DESC
            """
            params = (source,)
        else:
            query = """
                SELECT id, source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, notes,
                    total_parents, total_children, total_rates
                FROM rate_versions
                ORDER BY source, edition_year DESC, version_number DESC
            """
            params = None
        
        return db.query(query, params)
    
    def create_rate_version_system(self, data: Dict[str, Any]) -> Optional[int]:
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
    
    def get_rate_by_item_code(self, schedule_type: str, item_code: str) -> Optional[Dict]:
        """Get rate by item code from specified schedule"""
        if schedule_type == 'pwd':
            db = self._get_db()
            return db.query_one("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM pwd_chapters
                WHERE item_code = ?
            """, (item_code,))
        else:
            db = self._get_db()
            return db.query_one("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM lged_schedule
                WHERE item_code = ?
            """, (item_code,))
