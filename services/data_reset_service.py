# services/data_reset_service.py

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DataResetService:
    """Service for managing data reset operations"""
    
    def __init__(self, db):
        self.db = db
    
    def reset_demo_data(self, company_id: int, user_id: int) -> Dict[str, Any]:
        """Reset demo data for a company (archives demo data)"""
        
        results = {
            'archived_books': 0,
            'archived_boqs': 0,
            'archived_analyses': 0,
            'archive_batch_id': None
        }
        
        try:
            # Generate batch ID
            batch_id = f"DEMO_RESET_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            results['archive_batch_id'] = batch_id
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 1. Archive demo rate books
            cursor.execute("""
                SELECT id, name FROM tenant_rate_books 
                WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
            """, (company_id,))
            
            books = cursor.fetchall()
            for book in books:
                book_id = book['id']
                
                # Archive the book
                cursor.execute("""
                    UPDATE tenant_rate_books 
                    SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                        archive_reason = 'Demo data reset'
                    WHERE id = ?
                """, (user_id, book_id))
                
                # Archive associated items
                cursor.execute("""
                    UPDATE tenant_rate_items 
                    SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                        archive_reason = 'Demo data reset'
                    WHERE rate_book_id = ?
                """, (user_id, book_id))
                
                # Archive associated pricing
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?
                    WHERE rate_version_id IN (
                        SELECT id FROM tenant_rate_versions WHERE rate_book_id = ?
                    )
                """, (user_id, book_id))
                
                results['archived_books'] += 1
            
            # 2. Archive demo BOQs
            cursor.execute("""
                UPDATE boq_generation_history 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                    archive_reason = 'Demo data reset'
                WHERE company_id = ? AND is_demo = 1 AND is_archived = 0
            """, (user_id, company_id))
            results['archived_boqs'] = cursor.rowcount
            
            # 3. Archive demo analyses
            cursor.execute("""
                UPDATE tender_analyses 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                    archive_reason = 'Demo data reset'
                WHERE company_id = ? AND is_demo = 1 AND is_archived = 0
            """, (user_id, company_id))
            results['archived_analyses'] = cursor.rowcount
            
            # 4. Log archive metadata
            cursor.execute("""
                INSERT INTO archive_metadata 
                (archive_batch_id, company_id, operation_type, description, 
                 total_records_archived, status, initiated_by, completed_at)
                VALUES (?, ?, 'DEMO_RESET', 'Reset demo data', ?, 'completed', ?, CURRENT_TIMESTAMP)
            """, (batch_id, company_id, 
                  results['archived_books'] + results['archived_boqs'] + results['archived_analyses'],
                  user_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'results': results,
                'message': f"Archived {results['archived_books']} rate books, {results['archived_boqs']} BOQs, {results['archived_analyses']} analyses"
            }
            
        except Exception as e:
            logger.error(f"Error resetting demo data: {e}")
            return {'success': False, 'error': str(e)}
    
    def activate_production_data(self, company_id: int, user_id: int) -> Dict[str, Any]:
        """Switch company to production mode"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            batch_id = f"PROD_SWITCH_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 1. Archive all demo data
            demo_result = self.reset_demo_data(company_id, user_id)
            
            # 2. Update company to production
            cursor.execute("""
                UPDATE companies 
                SET environment_mode = 'PRODUCTION',
                    production_activated_at = CURRENT_TIMESTAMP,
                    onboarding_status = 'completed'
                WHERE id = ?
            """, (company_id,))
            
            # 3. Update onboarding status
            cursor.execute("""
                UPDATE company_onboarding_status 
                SET production_activated = 1, 
                    production_activated_at = CURRENT_TIMESTAMP,
                    onboarding_completed = 1,
                    onboarding_completed_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
            """, (company_id,))
            
            # 4. Log archive metadata
            cursor.execute("""
                INSERT INTO archive_metadata 
                (archive_batch_id, company_id, operation_type, description, 
                 total_records_archived, status, initiated_by, completed_at)
                VALUES (?, ?, 'PRODUCTION_SWITCH', 'Switched to production mode', 
                        ?, 'completed', ?, CURRENT_TIMESTAMP)
            """, (batch_id, company_id, 
                  demo_result.get('results', {}).get('archived_books', 0) + 
                  demo_result.get('results', {}).get('archived_boqs', 0) + 
                  demo_result.get('results', {}).get('archived_analyses', 0),
                  user_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': 'Company switched to PRODUCTION mode',
                'batch_id': batch_id
            }
            
        except Exception as e:
            logger.error(f"Error activating production: {e}")
            return {'success': False, 'error': str(e)}
    
    def full_company_reset(self, company_id: int, user_id: int) -> Dict[str, Any]:
        """Full reset of all company data (System Admin only)"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            batch_id = f"FULL_RESET_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Archive all company data
            
            # 1. Rate books
            cursor.execute("""
                UPDATE tenant_rate_books 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                    archive_reason = 'Full company reset'
                WHERE tenant_id = ? AND is_archived = 0
            """, (user_id, company_id))
            archived_books = cursor.rowcount
            
            # 2. BOQs
            cursor.execute("""
                UPDATE boq_generation_history 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                    archive_reason = 'Full company reset'
                WHERE company_id = ? AND is_archived = 0
            """, (user_id, company_id))
            archived_boqs = cursor.rowcount
            
            # 3. Analyses
            cursor.execute("""
                UPDATE tender_analyses 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?,
                    archive_reason = 'Full company reset'
                WHERE company_id = ? AND is_archived = 0
            """, (user_id, company_id))
            archived_analyses = cursor.rowcount
            
            # 4. Scenarios
            cursor.execute("""
                UPDATE saved_scenarios 
                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP, archived_by = ?
                WHERE company_id = ? AND is_archived = 0
            """, (user_id, company_id))
            archived_scenarios = cursor.rowcount
            
            # 5. Reset company to demo mode
            cursor.execute("""
                UPDATE companies 
                SET environment_mode = 'DEMO',
                    demo_data_generated_at = NULL,
                    production_activated_at = NULL,
                    onboarding_status = 'pending'
                WHERE id = ?
            """, (company_id,))
            
            # 6. Reset onboarding status
            cursor.execute("""
                UPDATE company_onboarding_status 
                SET demo_generated = 0,
                    demo_generated_at = NULL,
                    production_activated = 0,
                    production_activated_at = NULL,
                    onboarding_completed = 0,
                    onboarding_completed_at = NULL
                WHERE company_id = ?
            """, (company_id,))
            
            # 7. Log archive metadata
            total_archived = archived_books + archived_boqs + archived_analyses + archived_scenarios
            cursor.execute("""
                INSERT INTO archive_metadata 
                (archive_batch_id, company_id, operation_type, description, 
                 total_records_archived, status, initiated_by, completed_at)
                VALUES (?, ?, 'FULL_RESET', 'Full company data reset', 
                        ?, 'completed', ?, CURRENT_TIMESTAMP)
            """, (batch_id, company_id, total_archived, user_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': f'Full reset completed. Archived {total_archived} records.',
                'batch_id': batch_id,
                'archived_records': {
                    'books': archived_books,
                    'boqs': archived_boqs,
                    'analyses': archived_analyses,
                    'scenarios': archived_scenarios,
                    'total': total_archived
                }
            }
            
        except Exception as e:
            logger.error(f"Error performing full reset: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_archive_history(self, company_id: int, limit: int = 50) -> List[Dict]:
        """Get archive history for a company"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    am.archive_batch_id,
                    am.operation_type,
                    am.description,
                    am.total_records_archived,
                    am.status,
                    u.full_name as initiated_by_name,
                    am.initiated_at,
                    am.completed_at
                FROM archive_metadata am
                LEFT JOIN users u ON am.initiated_by = u.id
                WHERE am.company_id = ?
                ORDER BY am.initiated_at DESC
                LIMIT ?
            """, (company_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting archive history: {e}")
            return []