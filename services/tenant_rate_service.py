# services/tenant_rate_service.py

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.unified_db_manager import get_db_manager

logger = logging.getLogger(__name__)


class TenantRateService:
    """Service layer for tenant rate management - uses DatabaseCRUD directly"""
    
    def __init__(self, db=None):
        self.db = db or get_db_manager()
    
    # ========== RATE BOOKS ==========
    
    def create_rate_book(
        self,
        tenant_id: int,
        tenant_type: str,
        name: str,
        source_type: str,
        description: Optional[str] = None,
        source_version_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new rate book"""
        try:
            book_id = self.db.create_rate_book({
                'tenant_id': tenant_id,
                'tenant_type': tenant_type,
                'name': name,
                'source_type': source_type,
                'source_version_id': source_version_id,
                'description': description,
                'created_by': created_by,
                'is_active': True
            })
            
            if not book_id:
                return {'success': False, 'error': 'Failed to create rate book'}
            
            # Create initial version
            version_id = self.db.create_rate_version({
                'rate_book_id': book_id,
                'version_name': 'Initial Version',
                'effective_from': datetime.now().date().isoformat(),
                'is_current': True,
                'created_by': created_by
            })
            
            return {
                'success': True,
                'book_id': book_id,
                'version_id': version_id,
                'message': 'Rate book created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating rate book: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_rate_books(
        self,
        tenant_id: int,
        tenant_type: str = 'company',
        include_archived: bool = False
    ) -> Dict[str, Any]:
        """Get all rate books for a tenant"""
        try:
            books = self.db.get_rate_books_by_tenant(
                tenant_id, tenant_type, include_archived
            )
            
            return {
                'success': True,
                'books': books,
                'count': len(books)
            }
            
        except Exception as e:
            logger.error(f"Error getting rate books: {e}")
            return {
                'success': False, 
                'error': str(e),
                'books': [],
                'count': 0
            }
    
    def clone_master_rates(
        self,
        book_id: int,
        source_type: str,
        version_id: int,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Clone master rates to a tenant rate book"""
        try:
            result = self.db.clone_master_to_company(
                book_id=book_id,
                source_type=source_type,
                version_id=version_id,
                user_id=user_id,
                filters=filters
            )
            
            # Log the clone
            if result.get('success'):
                self.db.log_audit(
                    rate_book_id=book_id,
                    action='CLONE',
                    field_name='master_rates',
                    old_value='none',
                    new_value=f'{source_type} v{version_id}',
                    user_id=user_id
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error cloning master rates: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========== VERSIONS ==========
    
    def create_version(
        self,
        book_id: int,
        version_name: Optional[str] = None,
        effective_from: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new version of a rate book"""
        try:
            version_id = self.db.create_rate_version({
                'rate_book_id': book_id,
                'version_name': version_name,
                'effective_from': effective_from,
                'is_current': True,
                'notes': notes,
                'created_by': created_by
            })
            
            return {
                'success': True,
                'version_id': version_id,
                'message': 'Version created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating version: {e}")
            return {'success': False, 'error': str(e)}
    
    def set_current_version(self, version_id: int) -> Dict[str, Any]:
        """Set a version as the current version"""
        try:
            result = self.db.set_current_version(version_id)
            
            if result:
                return {
                    'success': True,
                    'message': 'Current version updated successfully'
                }
            else:
                return {'success': False, 'error': 'Version not found'}
            
        except Exception as e:
            logger.error(f"Error setting current version: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========== ITEMS AND PRICING ==========
    
    def get_items(
        self,
        book_id: int,
        version_id: Optional[int] = None,
        search: Optional[str] = None,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """Get items for a rate book with optional search"""
        try:
            items = self.db.get_rate_items_with_pricing(book_id, version_id)
            
            if search:
                search_lower = search.lower()
                items = [
                    item for item in items 
                    if search_lower in item.get('item_code', '').lower() 
                    or search_lower in item.get('item_description', '').lower()
                ]
            
            return {
                'success': True,
                'items': items,
                'count': len(items)
            }
            
        except Exception as e:
            logger.error(f"Error getting items: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_pricing(
        self,
        version_id: int,
        item_id: int,
        pricing_level: str,
        price: float,
        user_id: int
    ) -> Dict[str, Any]:
        """Update pricing for an item"""
        try:
            valid_levels = ['AGGRESSIVE', 'COMPETITIVE', 'STANDARD']
            if pricing_level.upper() not in valid_levels:
                return {
                    'success': False,
                    'error': f'Invalid pricing level. Must be one of: {", ".join(valid_levels)}'
                }
            
            result = self.db.update_pricing(
                version_id, item_id, pricing_level.upper(), price, user_id
            )
            
            if result:
                return {
                    'success': True,
                    'message': 'Pricing updated successfully'
                }
            else:
                return {'success': False, 'error': 'Failed to update pricing'}
            
        except Exception as e:
            logger.error(f"Error updating pricing: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_bulk_pricing(
        self,
        version_id: int,
        updates: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """Update pricing for multiple items"""
        try:
            successful = 0
            failed = 0
            errors = []
            
            for update in updates:
                result = self.update_pricing(
                    version_id,
                    update.get('item_id'),
                    update.get('pricing_level', 'COMPETITIVE'),
                    update.get('price', 0),
                    user_id
                )
                
                if result.get('success'):
                    successful += 1
                else:
                    failed += 1
                    errors.append({
                        'item_id': update.get('item_id'),
                        'error': result.get('error', 'Unknown error')
                    })
            
            return {
                'success': True,
                'successful': successful,
                'failed': failed,
                'errors': errors,
                'message': f'Updated {successful} items, {failed} failed'
            }
            
        except Exception as e:
            logger.error(f"Error in bulk pricing update: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========== AUDIT ==========
    
    def get_audit_log(
        self,
        book_id: Optional[int] = None,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Get audit log with pagination"""
        try:
            offset = (page - 1) * page_size
            entries = self.db.get_audit_log(book_id, user_id, page_size, offset)
            
            return {
                'success': True,
                'entries': entries,
                'page': page,
                'page_size': page_size,
                'count': len(entries)
            }
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return {'success': False, 'error': str(e)}