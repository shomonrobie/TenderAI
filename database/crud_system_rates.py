"""
CRUD Operations for Rate Management Module - Supabase Only
All database operations use get_db_manager() and db.query() exclusively
"""

from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import logging
import json
import pandas as pd

logger = logging.getLogger(__name__)


class SystemRateCRUD:
    """Rate-specific CRUD operations - Uses db.query() for all operations"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """
        Get the database manager.
        This works both in SystemRateCRUD and when bound to DatabaseCRUD.
        """
        # ✅ FIXED: Check if _db_manager exists before accessing
        if hasattr(self, '_db_manager') and self._db_manager:
            return self._db_manager
        from database.unified_db_manager import get_db_manager
        return get_db_manager()


    # =========================================================
    # PWD CHAPTERS
    # =========================================================
    
    def get_pwd_chapters(self) -> pd.DataFrame:
        """Get PWD chapters as DataFrame"""
        results = self.get_pwd_chapters_dict()
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_chapters_dict(self) -> List[Dict]:
        """Get PWD chapters as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            sql = "SELECT * FROM pwd_chapters ORDER BY chapter_number"
            result = db.query(sql)
            print(f"✅ get_pwd_chapters_dict: found {len(result) if result else 0} chapters")
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting PWD chapters: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # =========================================================
    # PWD PARENTS
    # =========================================================
    
    def get_pwd_parents(self, chapter_number: str = None) -> pd.DataFrame:
        """Get PWD parents as DataFrame"""
        results = self.get_pwd_parents_dict(chapter_number)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_parents_dict(self, chapter_number: str = None) -> List[Dict]:
        """Get PWD parents as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            if chapter_number:
                sql = "SELECT * FROM pwd_parents WHERE chapter_number = ? ORDER BY pwd_code"
                result = db.query(sql, (chapter_number,))
            else:
                sql = "SELECT * FROM pwd_parents ORDER BY pwd_code"
                result = db.query(sql)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting PWD parents: {e}")
            return []
    
    def get_pwd_parents_filtered(self, chapter: Optional[str] = None, search: Optional[str] = None) -> List[Dict]:
        """Get PWD parents with filters using db.query()"""
        try:
            db = self._get_db()
            conditions = []
            params = []
            
            if chapter and chapter != "All":
                conditions.append("chapter_number = ?")
                params.append(chapter)
            
            if search:
                conditions.append("(pwd_code LIKE ? OR description LIKE ?)")
                params.append(f"%{search}%")
                params.append(f"%{search}%")
            
            sql = "SELECT * FROM pwd_parents"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY pwd_code"
            
            result = db.query(sql, tuple(params) if params else None)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting filtered PWD parents: {e}")
            return []
    
    # =========================================================
    # PWD CHILDREN
    # =========================================================
    
    def get_pwd_children(self, parent_code: str = None, limit: int = 100) -> pd.DataFrame:
        """Get PWD children as DataFrame"""
        results = self.get_pwd_children_dict(parent_code, limit)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_children_dict(self, parent_code: str = None, limit: int = 100) -> List[Dict]:
        """Get PWD children as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            if parent_code:
                sql = "SELECT * FROM pwd_children WHERE parent_code = ? ORDER BY pwd_code LIMIT ?"
                result = db.query(sql, (parent_code, limit))
            else:
                sql = "SELECT * FROM pwd_children ORDER BY pwd_code LIMIT ?"
                result = db.query(sql, (limit,))
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting PWD children: {e}")
            return []
    
    def get_pwd_children_by_parent(self, parent_code: str) -> List[Dict]:
        """Get PWD children and rates for a specific parent using db.query()"""
        try:
            db = self._get_db()
            
            # Get children
            sql_children = "SELECT * FROM pwd_children WHERE parent_code = ? ORDER BY pwd_code"
            children = db.query(sql_children, (parent_code,))
            
            if not children:
                return []
            
            # Get rates for all children
            child_codes = [c['pwd_code'] for c in children if c.get('pwd_code')]
            rates = []
            if child_codes:
                placeholders = ','.join(['?'] * len(child_codes))
                sql_rates = f"SELECT * FROM pwd_rates WHERE pwd_code IN ({placeholders})"
                rates = db.query(sql_rates, tuple(child_codes))
            
            # Combine data
            result = []
            for child in children:
                child_rates = [r for r in rates if r.get('pwd_code') == child.get('pwd_code')]
                result.append({
                    'pwd_code': child.get('pwd_code'),
                    'description': child.get('description'),
                    'unit': child.get('unit'),
                    'rates': child_rates
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting PWD children by parent: {e}")
            return []
    
    # =========================================================
    # PWD RATES
    # =========================================================
    
    def get_pwd_rates(self, pwd_code: str = None, zone: str = None) -> pd.DataFrame:
        """Get PWD rates as DataFrame"""
        results = self.get_pwd_rates_dict(pwd_code, zone)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_pwd_rates_dict(self, pwd_code: str = None, zone: str = None) -> List[Dict]:
        """Get PWD rates as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            conditions = []
            params = []
            
            if pwd_code:
                conditions.append("pwd_code = ?")
                params.append(pwd_code)
            if zone:
                conditions.append("zone_name = ?")
                params.append(zone)
            
            sql = "SELECT * FROM pwd_rates"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY pwd_code, zone_name"
            
            result = db.query(sql, tuple(params) if params else None)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting PWD rates: {e}")
            return []
    
    def get_pwd_rates_by_code(self, pwd_code: str) -> List[Dict]:
        """Get PWD rates for a specific code"""
        return self.get_pwd_rates_dict(pwd_code=pwd_code)
    
    # =========================================================
    # LGED CHAPTERS
    # =========================================================
    
    def get_lged_chapters(self) -> pd.DataFrame:
        """Get LGED chapters as DataFrame"""
        results = self.get_lged_chapters_dict()
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_chapters_dict(self) -> List[Dict]:
        """Get LGED chapters as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            sql = "SELECT * FROM lged_chapters ORDER BY chapter_number"
            result = db.query(sql)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting LGED chapters: {e}")
            return []
    
    # =========================================================
    # LGED SECTIONS
    # =========================================================
    
    def get_lged_sections(self, chapter_number: str = None) -> pd.DataFrame:
        """Get LGED sections as DataFrame"""
        results = self.get_lged_sections_dict(chapter_number)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_sections_dict(self, chapter_number: str = None) -> List[Dict]:
        """Get LGED sections as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            if chapter_number:
                sql = "SELECT * FROM lged_sections WHERE chapter_number = ? ORDER BY section_number"
                result = db.query(sql, (chapter_number,))
            else:
                sql = "SELECT * FROM lged_sections ORDER BY section_number"
                result = db.query(sql)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting LGED sections: {e}")
            return []
    
    # =========================================================
    # LGED PARENTS
    # =========================================================
    
    def get_lged_parents(self, chapter_number: str = None, section_number: str = None) -> pd.DataFrame:
        """Get LGED parents as DataFrame"""
        results = self.get_lged_parents_dict(chapter_number, section_number)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_parents_dict(self, chapter_number: str = None, section_number: str = None) -> List[Dict]:
        """Get LGED parents as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            conditions = []
            params = []
            
            if chapter_number:
                conditions.append("chapter_number = ?")
                params.append(chapter_number)
            if section_number:
                conditions.append("section_number = ?")
                params.append(section_number)
            
            sql = "SELECT * FROM lged_parents"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY code"
            
            result = db.query(sql, tuple(params) if params else None)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting LGED parents: {e}")
            return []
    
    # =========================================================
    # LGED CHILDREN
    # =========================================================
    
    def get_lged_children(self, parent_code: str = None, chapter_number: str = None, limit: int = 100) -> pd.DataFrame:
        """Get LGED children as DataFrame"""
        results = self.get_lged_children_dict(parent_code, chapter_number, limit)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_children_dict(self, parent_code: str = None, chapter_number: str = None, limit: int = 100) -> List[Dict]:
        """Get LGED children as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            conditions = []
            params = []
            
            if parent_code:
                conditions.append("parent_code = ?")
                params.append(parent_code)
            if chapter_number:
                conditions.append("chapter_number = ?")
                params.append(chapter_number)
            
            sql = "SELECT * FROM lged_children"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY code LIMIT ?"
            params.append(limit)
            
            result = db.query(sql, tuple(params))
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting LGED children: {e}")
            return []
    
    # =========================================================
    # LGED ZONE MAPPING
    # =========================================================
    
    def get_lged_zone_mapping(self) -> pd.DataFrame:
        """Get LGED zone mapping as DataFrame"""
        results = self.get_lged_zone_mapping_dict()
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_lged_zone_mapping_dict(self) -> List[Dict]:
        """Get LGED zone mapping as list of dictionaries using db.query()"""
        try:
            db = self._get_db()
            sql = "SELECT * FROM lged_zone_mapping ORDER BY zone_code"
            result = db.query(sql)
            return result if result else []
        except Exception as e:
            print(f"❌ Error getting LGED zone mapping: {e}")
            return []
    
    # =========================================================
    # RATE VERSIONS - FIXED
    # =========================================================
    
    def get_rate_versions(self, source: str = None) -> pd.DataFrame:
        """Get rate versions as DataFrame"""
        results = self.get_rate_versions_dict(source)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def get_rate_versions_dict(self, source: str = None) -> List[Dict]:
        """
        Get rate versions as list of dictionaries using db.query()
        THIS IS THE FIXED VERSION - uses db.query() directly
        """
        try:
            db = self._get_db()
            
            # ✅ Use db.query() directly - NOT self._query()
            if source:
                sql = "SELECT * FROM rate_versions WHERE source = ? ORDER BY edition_year DESC, version_number DESC"
                result = db.query(sql, (source,))
            else:
                sql = "SELECT * FROM rate_versions ORDER BY edition_year DESC, version_number DESC"
                result = db.query(sql)
            
            print(f"🔍 get_rate_versions_dict: source='{source}', found {len(result) if result else 0} versions")
            
            # Debug: Print versions found
            if result:
                for v in result:
                    print(f"   Version: id={v.get('id')}, source={v.get('source')}, edition={v.get('edition_year')}, is_active={v.get('is_active')}")
            else:
                print(f"⚠️ No versions found for source='{source}'")
                
                # Try without filter to see what's in the table
                sql_all = "SELECT * FROM rate_versions ORDER BY created_at DESC"
                all_versions = db.query(sql_all)
                if all_versions:
                    print(f"📊 All versions in table: {len(all_versions)}")
                    for v in all_versions:
                        print(f"   - id={v.get('id')}, source='{v.get('source')}', edition={v.get('edition_year')}")
                else:
                    print("📊 No versions at all in rate_versions table!")
            
            return result if result else []
            
        except Exception as e:
            print(f"❌ Error getting rate versions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # =========================================================
    # CREATE VERSION
    # =========================================================
    
    def create_rate_version_system(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new rate version using db.execute()"""
        try:
            db = self._get_db()
            
            # Get current max version number
            sql_max = "SELECT MAX(version_number) as max_version FROM tenant_rate_versions WHERE rate_book_id = ?"
            result = db.query_one(sql_max, (data.get('rate_book_id'),))
            max_val = result.get('max_version', 0) if result else 0
            next_version = max_val + 1
            
            # If this is set as current, unset others
            if data.get('is_current', False):
                sql_update = "UPDATE tenant_rate_versions SET is_current = 0 WHERE rate_book_id = ?"
                db.execute(sql_update, (data.get('rate_book_id'),))
            
            # Insert new version
            sql_insert = """
                INSERT INTO tenant_rate_versions (
                    rate_book_id, version_name, version_number, 
                    effective_from, is_current, notes, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                data.get('rate_book_id'),
                data.get('version_name', f'Version {next_version}'),
                next_version,
                data.get('effective_from', datetime.now().date().isoformat()),
                1 if data.get('is_current', False) else 0,
                data.get('notes'),
                data.get('created_by'),
                datetime.now().isoformat()
            )
            
            db.execute(sql_insert, params)
            
            # Get the inserted ID
            sql_id = "SELECT last_insert_rowid() as id"
            id_result = db.query_one(sql_id)
            return id_result.get('id') if id_result else None
            
        except Exception as e:
            logger.error(f"Error creating rate version: {e}")
            raise
    
    # =========================================================
    # GET RATE BY ITEM CODE
    # =========================================================
    
    def get_rate_by_item_code(self, schedule_type: str, item_code: str) -> Optional[Dict]:
        """Get rate by item code from specified schedule using db.query_one()"""
        try:
            db = self._get_db()
            table = 'pwd_chapters' if schedule_type == 'pwd' else 'lged_schedule'
            sql = f"SELECT * FROM {table} WHERE item_code = ?"
            return db.query_one(sql, (item_code,))
        except Exception as e:
            logger.error(f"Error getting rate by item code: {e}")
            return None
    
    # =========================================================
    # UPDATE PWD CHAPTER
    # =========================================================
    
    def update_pwd_chapter(self, version_id: int, chapter_num: str, hierarchy: Dict,
                          edition_year: int, notes: str, updated_by: str) -> Dict:
        """Update a specific chapter in an existing version using db.execute()"""
        try:
            db = self._get_db()
            print("=" * 60)
            print("🔍 update_pwd_chapter STARTED")
            print("=" * 60)
            print(f"🔍 version_id: {version_id}")
            print(f"🔍 chapter_num: {chapter_num}")
            print(f"🔍 edition_year: {edition_year}")
            print(f"🔍 hierarchy keys: {hierarchy.keys()}")
            print(f"🔍 parents in hierarchy: {len(hierarchy.get('parents', []))}")
            print(f"🔍 children in hierarchy: {len(hierarchy.get('children', []))}")
            
            if hierarchy.get('parents'):
                print("🔍 First 5 parents from hierarchy:")
                for p in hierarchy['parents'][:5]:
                    print(f"   {p}")
            # Delete existing data for this chapter
            # 1. Get child codes
            sql_children = "SELECT pwd_code FROM pwd_children WHERE version_id = ? AND chapter_number = ?"
            child_codes_result = db.query(sql_children, (version_id, chapter_num))
            
            if child_codes_result:
                child_codes = [c['pwd_code'] for c in child_codes_result if c.get('pwd_code')]
                if child_codes:
                    placeholders = ','.join(['?'] * len(child_codes))
                    sql_delete_rates = f"DELETE FROM pwd_rates WHERE pwd_code IN ({placeholders})"
                    db.execute(sql_delete_rates, tuple(child_codes))
            
            # 2. Delete children
            sql_delete_children = "DELETE FROM pwd_children WHERE version_id = ? AND chapter_number = ?"
            db.execute(sql_delete_children, (version_id, chapter_num))
            
            # 3. Delete parents
            sql_delete_parents = "DELETE FROM pwd_parents WHERE version_id = ? AND chapter_number = ?"
            db.execute(sql_delete_parents, (version_id, chapter_num))
            
            # Save parents
            parents_saved = 0
            for parent in hierarchy.get('parents', []):
                pwd_code = parent.get('code') or parent.get('pwd_code')
                if not pwd_code:
                    continue
                
                description = parent.get('description', '')
                ch_num = parent.get('chapter', chapter_num) or parent.get('chapter_number', chapter_num)
                
                # ✅ CORRECTED: Only insert columns that exist in the table
                sql_insert_parent = """
                    INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(pwd_code) DO UPDATE SET
                        description = excluded.description,
                        chapter_number = excluded.chapter_number,
                        version_id = excluded.version_id
                """
                db.execute(sql_insert_parent, (
                    pwd_code,
                    description,
                    ch_num,
                    version_id
                ))
                parents_saved += 1
                print(f"✅ Inserted parent: {pwd_code}")


            
            # Save children and rates
            children_saved = 0
            rates_saved = 0
            
            for child in hierarchy.get('children', []):
                code = child.get('pwd_code') or child.get('code')
                if not code:
                    continue
                
                parent_code = child.get('parent_code') or code
                
                # Insert child
                sql_insert_child = """
                    INSERT INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id, chapter_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pwd_code) DO UPDATE SET
                        parent_code = excluded.parent_code,
                        description = excluded.description,
                        unit = excluded.unit,
                        edition_year = excluded.edition_year,
                        version_id = excluded.version_id,
                        chapter_number = excluded.chapter_number
                """
                db.execute(sql_insert_child, (
                    code,
                    parent_code,
                    child.get('description', ''),
                    child.get('unit', ''),
                    edition_year,
                    version_id,
                    chapter_num
                ))
                children_saved += 1
                
                # Insert rates
                for zone, rate in child.get('rates', {}).items():
                    sql_insert_rate = """
                        INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(pwd_code, zone_name) DO UPDATE SET
                            unit_rate = excluded.unit_rate,
                            edition_year = excluded.edition_year,
                            version_id = excluded.version_id
                    """
                    db.execute(sql_insert_rate, (
                        code,
                        zone,
                        float(rate),
                        edition_year,
                        version_id
                    ))
                    rates_saved += 1
            
            # Log the change
            sql_log = """
                INSERT INTO version_change_log (version_id, source, action, changed_by, details)
                VALUES (?, ?, ?, ?, ?)
            """
            db.execute(sql_log, (
                version_id,
                'PWD',
                'update_chapter',
                updated_by,
                f"Updated Chapter {chapter_num}: {notes}"
            ))
            
            # Update version statistics
            self.update_version_stats(version_id)
            
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
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    # =========================================================
    # UPDATE VERSION STATISTICS
    # =========================================================
    
    def _get_count_from_result(result):
        """Extract count from query result, works with 'total' or 'count' key"""
        if not result:
            return 0
        if 'total' in result:
            return result['total']
        if 'count' in result:
            return result['count']
        # If no known key, return first value
        return list(result.values())[0] if result else 0

    
    def update_version_stats(self, version_id: int) -> Dict[str, Any]:
        """
        Update version statistics for PWD - uses Supabase API directly when available
        
        Args:
            version_id: The version ID to update stats for
            
        Returns:
            Dict with status and counts
        """
        try:
            db = self._get_db()
            print(f"🔍 update_version_stats called for version {version_id}")
            
            # ✅ Check if version exists
            version = db.query_one(
                "SELECT id, source FROM rate_versions WHERE id = ?",
                (version_id,)
            )
            
            if not version:
                print(f"❌ Version {version_id} not found")
                return {'success': False, 'error': 'Version not found'}
            
            source = version.get('source', 'PWD')
            
            # ✅ Get counts based on source
            if source == 'PWD':
                parent_result = db.query_one(
                    "SELECT COUNT(*) as total FROM pwd_parents WHERE version_id = ?",
                    (version_id,)
                )
                child_result = db.query_one(
                    "SELECT COUNT(*) as total FROM pwd_children WHERE version_id = ?",
                    (version_id,)
                )
                rate_result = db.query_one(
                    "SELECT COUNT(*) as total FROM pwd_rates WHERE version_id = ?",
                    (version_id,)
                )
            else:
                parent_result = db.query_one(
                    "SELECT COUNT(*) as total FROM lged_parents WHERE version_id = ?",
                    (version_id,)
                )
                child_result = db.query_one(
                    "SELECT COUNT(*) as total FROM lged_children WHERE version_id = ?",
                    (version_id,)
                )
                rate_result = db.query_one(
                    "SELECT COUNT(*) as total FROM lged_zone_rates WHERE version_id = ?",
                    (version_id,)
                )
            
            parent_count = parent_result.get('total', 0) if parent_result else 0
            child_count = child_result.get('total', 0) if child_result else 0
            rate_count = rate_result.get('total', 0) if rate_result else 0
            
            print(f"📊 Counts: parents={parent_count}, children={child_count}, rates={rate_count}")
            
            # ✅ Prepare update data
            update_data = {
                'total_parents': parent_count,
                'total_children': child_count,
                'total_rates': rate_count,
                'updated_at': datetime.now().isoformat()
            }
            
            # ✅ Use the SAME pattern as update_user!
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                try:
                    print(f"🔍 Using Supabase API for update: {update_data}")
                    response = db.supabase.table('rate_versions').update(update_data).eq('id', version_id).execute()
                    print(f"✅ Supabase update response: {response.data if response.data else 'No data returned'}")
                    
                    # ✅ Verify the update
                    verify = db.query_one(
                        "SELECT total_parents, total_children, total_rates FROM rate_versions WHERE id = ?",
                        (version_id,)
                    )
                    print(f"🔍 Verified after Supabase update: {verify}")
                    
                    return {
                        'success': True,
                        'version_id': version_id,
                        'counts': {
                            'parents': parent_count,
                            'children': child_count,
                            'rates': rate_count
                        }
                    }
                except Exception as e:
                    print(f"⚠️ Supabase update error: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fall through to SQLite fallback
            
            # ✅ SQLite fallback (if not Supabase or Supabase failed)
            print(f"🔍 Using SQLite fallback for update")
            db.execute(
                """
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?, updated_at = ?
                WHERE id = ?
                """,
                (parent_count, child_count, rate_count, datetime.now().isoformat(), version_id)
            )
            
            print(f"✅ Stats updated for version {version_id}")
            
            # ✅ Verify
            verify = db.query_one(
                "SELECT total_parents, total_children, total_rates FROM rate_versions WHERE id = ?",
                (version_id,)
            )
            print(f"🔍 Verified: {verify}")
            
            return {
                'success': True,
                'version_id': version_id,
                'counts': {
                    'parents': parent_count,
                    'children': child_count,
                    'rates': rate_count
                }
            }
            
        except Exception as e:
            print(f"❌ Error updating version stats: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


    def _update_version_record(self, version_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update a version record with the given updates
        
        Args:
            version_id: The version ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = self._get_db()
            
            # ✅ Build SET clause dynamically
            set_clauses = []
            params = []
            
            allowed_fields = [
                'name', 'description', 'status', 'is_active',
                'total_parents', 'total_children', 'total_rates',
                'updated_at', 'imported_by'
            ]
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
                    print(f"🔍 DEBUG - adding {key} = {value}")
            
            if not set_clauses:
                print("⚠️ No fields to update")
                return False
            
            # Add WHERE clause
            params.append(version_id)
            
            sql = f"""
                UPDATE rate_versions 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """
            
            print(f"🔍 SQL: {sql}")
            print(f"🔍 params: {params}")
            
            # ✅ Execute with proper error handling
            db.execute(sql, tuple(params))
            return True
            
        except Exception as e:
            print(f"❌ Error updating version record: {e}")
            import traceback
            traceback.print_exc()
            return False



    
    # =========================================================
    # UTILITY METHODS
    # =========================================================
    
    def test_method(self):
        """Test method to verify binding"""
        return "SystemRateCRUD is working!"