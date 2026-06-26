# services/tenant_rate_service.py

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.tenant_rate_repository import TenantRateRepository

logger = logging.getLogger(__name__)

class TenantRateService:
    """Service layer for tenant rate management"""
    
    def __init__(self, repository: Optional[TenantRateRepository] = None):
        self.repository = repository or TenantRateRepository()
    
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
            book_id = self.repository.create_rate_book({
                'tenant_id': tenant_id,
                'tenant_type': tenant_type,
                'name': name,
                'source_type': source_type,
                'source_version_id': source_version_id,
                'description': description,
                'created_by': created_by
            })
            
            # Create initial version
            version_id = self.repository.create_rate_version({
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
            books = self.repository.get_rate_books_by_tenant(
                tenant_id, tenant_type, include_archived
            )
            
            # ✅ FIX: Ensure books is a list
            if not isinstance(books, list):
                books = []
            
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
            if source_type == 'PWD':
                result = self.repository.clone_pwd_master(book_id, version_id, filters)
            elif source_type == 'LGED':
                result = self.repository.clone_lged_master(book_id, version_id, filters)
            else:
                return {'success': False, 'error': f'Unknown source type: {source_type}'}
            
            if result.get('success'):
                # Audit the clone operation
                self.repository.get_connection()
                # We'll add audit in repository
                
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
            # Copy all items from current version
            version_id = self.repository.create_rate_version({
                'rate_book_id': book_id,
                'version_name': version_name,
                'effective_from': effective_from,
                'is_current': True,
                'notes': notes,
                'created_by': created_by
            })
            
            # Get items from current version and copy pricing
            current_version = self.repository.get_versions_for_book(book_id)
            if current_version:
                current_version_id = current_version[0]['id'] if current_version else None
                
                if current_version_id:
                    items = self.repository.get_rate_items_by_book(book_id, current_version_id)
                    
                    for item in items:
                        # Copy pricing to new version
                        pricing = self.repository.get_item_pricing(item['id'], current_version_id)
                        
                        for level, prices in pricing.items():
                            if prices:
                                self.repository.update_pricing(
                                    version_id,
                                    item['id'],
                                    level,
                                    prices[0]['price'],
                                    created_by
                                )
            
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
            result = self.repository.set_current_version(version_id)
            
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
            items = self.repository.get_rate_items_by_book(book_id, version_id, active_only)
            
            if search:
                search_lower = search.lower()
                items = [
                    item for item in items 
                    if search_lower in item['item_code'].lower() 
                    or search_lower in item['item_description'].lower()
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
            # Validate pricing level
            valid_levels = ['ECONOMY', 'MARKET', 'PREMIUM']
            if pricing_level.upper() not in valid_levels:
                return {
                    'success': False,
                    'error': f'Invalid pricing level. Must be one of: {", ".join(valid_levels)}'
                }
            
            result = self.repository.update_pricing(
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
                    update['item_id'],
                    update['pricing_level'],
                    update['price'],
                    user_id
                )
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
                    errors.append({
                        'item_id': update['item_id'],
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
            entries = self.repository.get_audit_log(book_id, user_id, page_size, offset)
            
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