"""
CRUD Operations for Tender Management Module
All database operations for tenders, bids, teams, milestones, and revisions
""# database/crud_tender.py - Simplified version

"""


from typing import Optional, Dict, List, Any, Union
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class TenderCRUD:
    """Tender-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """
        Get the database manager - works both as standalone and when bound to DatabaseCRUD
        """
        
        import traceback
        print(f"🔍 TenderCRUD._get_db() called")
        print(f"   - hasattr(self, 'query'): {hasattr(self, 'query')}")
        print(f"   - hasattr(self, '_db_manager'): {hasattr(self, '_db_manager')}")
        print(f"   - self._db_manager: {self._db_manager}")
        # If this instance has the methods directly (bound to DatabaseCRUD)
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        # Otherwise use the stored db_manager
        elif self._db_manager:
            return self._db_manager
        else:
            raise AttributeError("No database connection available")
    
    def get_company_tenders(self, company_id: int, status_filter: Optional[str] = None, 
                           limit: int = 100) -> List[Dict]:
        """Get all tenders for a company with submitter names"""
        db = self._get_db()
        
        # ✅ Use TRUE for boolean columns
        sql = """
            SELECT ct.*, u.full_name as submitted_by_name
            FROM company_tenders ct
            LEFT JOIN users u ON ct.bid_submitted_by = u.id
            WHERE ct.company_id = ? AND ct.is_active = TRUE
        """
        params = [company_id]
        
        if status_filter:
            sql += " AND ct.bid_status = ?"
            params.append(status_filter)
        
        sql += " ORDER BY ct.created_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.query(sql, tuple(params))
        
        # Normalize boolean values (already boolean from Supabase)
        for result in results:
            result['is_active'] = result.get('is_active', False)
            result['is_locked'] = result.get('is_locked', False)
            result['is_copy'] = result.get('is_copy', False)
            
        return results
    
    def get_tender_by_id(self, tender_id: str, company_id: Optional[int] = None) -> Optional[Dict]:
        """Get a single tender by ID"""
        db = self._get_db()
        
        # ✅ Use TRUE for boolean columns
        sql = """
            SELECT ct.*, u.full_name as submitted_by_name
            FROM company_tenders ct
            LEFT JOIN users u ON ct.bid_submitted_by = u.id
            WHERE ct.tender_id = ? AND ct.is_active = TRUE
        """
        params = [tender_id]
        
        if company_id:
            sql += " AND ct.company_id = ?"
            params.append(company_id)
        
        result = db.query_one(sql, tuple(params))
        if result:
            result['is_active'] = result.get('is_active', False)
            result['is_locked'] = result.get('is_locked', False)
            result['is_copy'] = result.get('is_copy', False)
        return result
    
    def get_tender_by_db_id(self, tender_db_id: int, company_id: int) -> Optional[Dict]:
        """Get a tender by its database ID (primary key)"""
        import traceback
        print(f"🔍 TenderCRUD.get_tender_by_db_id() called")
        print(f"   - tender_db_id: {tender_db_id}")
        print(f"   - company_id: {company_id}")
        print(f"   - self._db_manager: {self._db_manager}")
        print(f"   - Call stack: {traceback.format_stack()[-3:-1]}")
        
        db = self._get_db()
        print(f"   - db returned: {type(db)}")
        
        # ✅ Use the database manager's query_one method
        sql = """
            SELECT tender_id FROM company_tenders 
            WHERE id = ? AND company_id = ? AND is_active = TRUE
        """
        result = db.query_one(sql, (tender_db_id, company_id))
        print(f"   - result: {result}")
        
        if not result:
            return None
        
        tender_id_str = result.get('tender_id')
        return self.get_tender_by_id(tender_id_str, company_id)


    
    def get_tender_analysis_by_id(self, analysis_id: int) -> Optional[Dict]:
        """Get a tender analysis by ID"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT 
                id, user_id, company_id, tender_id, tender_title,
                procuring_entity, division, district, construction_type,
                official_estimate, recommended_bid, actual_bid,
                success_probability, risk_level, competitor_count,
                bid_status, analysis_date, competitor_bids,
                risk_strategy, confidence_score, expected_profit,
                expected_value, slt_threshold, nppi_factor,
                weighted_average, analysis_type, final_submitted_bid,
                is_final_submitted, actual_winning_bid, actual_winner,
                our_rank_actual, total_bidders_actual, bid_accuracy_score,
                lessons_learned, post_evaluation_date, is_demo,
                data_source_type, is_archived
            FROM tender_analyses 
            WHERE id = ?
        """, (analysis_id,))

    def get_company_tender_analyses(self, company_id: int, tender_id: str = None, limit: int = 20) -> List[Dict]:
        """Get tender analyses for a company"""
        db = self._get_db()
        
        params = [company_id]
        sql = """
            SELECT id, tender_id, tender_title, recommended_bid, 
                confidence_score, analysis_date, bid_status
            FROM tender_analyses 
            WHERE company_id = ?
        """
        
        if tender_id:
            sql += " AND tender_id = ?"
            params.append(tender_id)
        
        sql += " ORDER BY analysis_date DESC LIMIT ?"
        params.append(limit)
        
        return db.query(sql, tuple(params))

    def get_company_monthly_analytics(self, company_id: int, months: int = 6) -> List[Dict]:
        """Get monthly analytics trend for a company"""
        db = self._get_db()
        
        # ✅ Use column alias with AS keyword for clarity
        sql = """
            SELECT 
                strftime('%Y-%m', analysis_date) AS month,
                COUNT(*) AS count,
                ROUND(AVG(confidence_score), 1) AS avg_conf,
                SUM(CASE WHEN bid_status = 'won' THEN 1 ELSE 0 END) AS wins
            FROM tender_analyses
            WHERE company_id = ?
            GROUP BY strftime('%Y-%m', analysis_date)
            ORDER BY month DESC
            LIMIT ?
        """
        
        results = db.query(sql, (company_id, months))
        
        # ✅ Ensure results are properly formatted with string keys
        formatted_results = []
        for row in results:
            formatted_results.append({
                'month': row.get('month', ''),
                'count': row.get('count', 0),
                'avg_conf': row.get('avg_conf', 0),
                'wins': row.get('wins', 0)
            })
        
        return formatted_results
    def create_tender(self, tender_data: Dict) -> int:
        """Create a new tender"""
        db = self._get_db()
        
        required_fields = ['company_id', 'tender_id', 'tender_title', 'procuring_entity']
        for field in required_fields:
            if field not in tender_data:
                raise ValueError(f"Missing required field: {field}")
        
        sql = """
            INSERT INTO company_tenders (
                company_id, tender_id, tender_title, procuring_entity,
                official_estimate, procurement_type, submission_deadline,
                description, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            tender_data.get('company_id'),
            tender_data.get('tender_id'),
            tender_data.get('tender_title'),
            tender_data.get('procuring_entity'),
            tender_data.get('official_estimate', 0),
            tender_data.get('procurement_type', 'works'),
            tender_data.get('submission_deadline'),
            tender_data.get('description', ''),
            True,  # ✅ is_active - boolean
            datetime.now().isoformat()
        )
        
        db.execute(sql, params)
        
        # Get the inserted tender
        result = db.query_one(
            "SELECT id FROM company_tenders WHERE tender_id = ? AND company_id = ?",
            (tender_data.get('tender_id'), tender_data.get('company_id'))
        )
        
        return result['id'] if result else None
    
    def update_tender(self, tender_id: str, company_id: int, update_data: Dict) -> bool:
        """Update a tender"""
        db = self._get_db()
        
        try:
            updates = []
            params = []
            
            allowed_fields = [
                'tender_title', 'procuring_entity', 'official_estimate',
                'procurement_type', 'submission_deadline', 'description',
                'bid_status', 'our_bid_amount', 'bid_submission_date',
                'bid_submitted_by', 'is_locked'
            ]
            
            for key, value in update_data.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            # ✅ Handle boolean fields separately with True/False
            if 'is_active' in update_data:
                updates.append("is_active = ?")
                params.append(True if update_data['is_active'] else False)
            
            if 'is_locked' in update_data:
                updates.append("is_locked = ?")
                params.append(True if update_data['is_locked'] else False)
            
            if 'is_copy' in update_data:
                updates.append("is_copy = ?")
                params.append(True if update_data['is_copy'] else False)
            
            if 'is_archived' in update_data:
                updates.append("is_archived = ?")
                params.append(True if update_data['is_archived'] else False)
            
            if not updates:
                return True
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            params.extend([tender_id, company_id])
            
            sql = f"""
                UPDATE company_tenders 
                SET {', '.join(updates)}
                WHERE tender_id = ? AND company_id = ?
            """
            
            db.execute(sql, tuple(params))
            return True
            
        except Exception as e:
            logger.error(f"Error updating tender: {e}")
            return False
    
    def delete_tender(self, tender_id: str, company_id: int) -> bool:
        """Soft delete a tender (set is_active = FALSE)"""
        db = self._get_db()
        
        try:
            db.execute("""
                UPDATE company_tenders 
                SET is_active = ?, updated_at = ?
                WHERE tender_id = ? AND company_id = ?
            """, (False, datetime.now().isoformat(), tender_id, company_id))  # ✅ Use False
            return True
        except Exception as e:
            logger.error(f"Error deleting tender: {e}")
            return False
    
    def archive_tender(self, tender_id: str, company_id: int, reason: Optional[str] = None) -> bool:
        """Archive a tender"""
        db = self._get_db()
        
        try:
            params = [True, datetime.now().isoformat()]  # ✅ is_archived = True
            if reason:
                params.append(reason)
            params.extend([tender_id, company_id])
            
            sql = """
                UPDATE company_tenders 
                SET is_archived = ?, archived_at = ?, archive_reason = ?
                WHERE tender_id = ? AND company_id = ?
            """ if reason else """
                UPDATE company_tenders 
                SET is_archived = ?, archived_at = ?
                WHERE tender_id = ? AND company_id = ?
            """
            
            db.execute(sql, tuple(params))
            return True
        except Exception as e:
            logger.error(f"Error archiving tender: {e}")
            return False
    
    def get_tender_with_boq(self, tender_id: str, company_id: int) -> Optional[Dict]:
        """Get tender with its latest BOQ data"""
        db = self._get_db()
        
        # ✅ Use TRUE for boolean columns
        sql = """
            SELECT 
                ct.*, 
                b.id as boq_id, 
                b.total_estimated_cost as boq_total_cost,
                b.selected_zone as boq_zone,
                b.rate_source as boq_source,
                b.item_count as boq_item_count,
                b.status as boq_status,
                b.generated_at as boq_generated_at,
                u.full_name as submitted_by_name
            FROM company_tenders ct
            LEFT JOIN boq_generation_history b ON ct.tender_id = b.tender_id AND b.status = 'completed'
            LEFT JOIN users u ON ct.bid_submitted_by = u.id
            WHERE ct.tender_id = ? AND ct.company_id = ? AND ct.is_active = TRUE
            ORDER BY b.generated_at DESC
            LIMIT 1
        """
        result = db.query_one(sql, (tender_id, company_id))
        if result:
            result['is_active'] = result.get('is_active', False)
            result['is_locked'] = result.get('is_locked', False)
        return result
    
    def create_tender_copy(self, original_tender_id: int, created_by: int) -> Optional[int]:
        """Create a backup copy of a tender with all fields"""
        db = self._get_db()
        
        # Get original
        original = db.query_one("SELECT * FROM company_tenders WHERE id = ?", (original_tender_id,))
        if not original:
            return None
        
        # Prepare copy data - exclude id
        copy_data = {k: v for k, v in original.items() if k != 'id'}
        
        # Modify fields for copy
        copy_data['tender_id'] = f"{copy_data.get('tender_id', '')}_COPY"
        copy_data['tender_title'] = f"{copy_data.get('tender_title', '')} (Backup Copy)"
        
        # ✅ Use True/False for boolean fields
        copy_data['is_locked'] = False
        copy_data['is_copy'] = True
        copy_data['is_active'] = True  # Ensure copy is active
        copy_data['is_archived'] = False  # Ensure copy is not archived
        
        copy_data['original_tender_id'] = original_tender_id
        copy_data['created_by'] = created_by
        copy_data['created_at'] = datetime.now().isoformat()
        copy_data['updated_at'] = None
        
        # Reset bid/submission/evaluation fields
        reset_fields = [
            'bid_submitted_by', 'bid_status', 'our_bid_amount', 
            'bid_submission_date', 'evaluation_status', 'winning_bid_amount',
            'winning_competitor', 'our_rank', 'total_bidders', 'award_date'
        ]
        for field in reset_fields:
            copy_data[field] = None
        
        # Build and execute INSERT
        columns = list(copy_data.keys())
        placeholders = ', '.join(['?'] * len(columns))
        sql = f"INSERT INTO company_tenders ({', '.join(columns)}) VALUES ({placeholders})"
        
        db.execute(sql, tuple(copy_data.values()))
        
        # Get the new ID
        result = db.query_one(
            "SELECT id FROM company_tenders WHERE tender_id = ? AND created_by = ? ORDER BY created_at DESC LIMIT 1",
            (copy_data['tender_id'], created_by)
        )
        
        return result['id'] if result else None

    
    # =========================================================================
    # BID OPERATIONS
    # =========================================================================
    
    def update_tender_bid(self, tender_id: int, bid_amount: float, updated_by: int) -> bool:
        """Update bid amount with revision tracking"""
        # Check current bid
        db = self._get_db()
        current = db.query_one("SELECT our_bid_amount FROM company_tenders WHERE id = ?", (tender_id,))
        
        if current and current.get('our_bid_amount') is not None:
            current_amount = float(current['our_bid_amount'])
            if current_amount != bid_amount:
                # Add revision
                self.add_bid_revision(tender_id, bid_amount, updated_by, 'Bid amount updated via UI')
        
        # Update bid
        sql = """
            UPDATE company_tenders 
            SET our_bid_amount = ?, updated_at = ?
            WHERE id = ?
        """
        result = self.execute(sql, (bid_amount, datetime.now(), tender_id))
        return result > 0 if isinstance(result, int) else False
    
    def submit_bid(self, tender_id: int, final_bid_amount: float, submitted_by: int) -> bool:
        """Submit a bid"""
        sql = """
            UPDATE company_tenders 
            SET our_bid_amount = ?, bid_submitted_by = ?, 
                bid_submission_date = ?, bid_status = 'submitted',
                updated_at = ?
            WHERE id = ?
        """
        result = self.execute(sql, (final_bid_amount, submitted_by, datetime.now(), 
                                      datetime.now(), tender_id))
        return result > 0 if isinstance(result, int) else False
    
    def update_tender_result(self, tender_id: int, winning_bid_amount: float, 
                            winning_competitor: str, our_rank: int, 
                            total_bidders: int, award_date: str, bid_status: str) -> bool:
        """Update tender results"""
        sql = """
            UPDATE company_tenders 
            SET winning_bid_amount = ?, winning_competitor = ?, our_rank = ?,
                total_bidders = ?, award_date = ?, bid_status = ?,
                evaluation_status = 'completed', updated_at = ?
            WHERE id = ?
        """
        result = self.execute(sql, (winning_bid_amount, winning_competitor, our_rank,
                                      total_bidders, award_date, bid_status, 
                                      datetime.now(), tender_id))
        return result > 0 if isinstance(result, int) else False
    
    def clear_tender_winner(self, tender_id: str) -> bool:
        """Clear winner from tender"""
        sql = """
            UPDATE company_tenders 
            SET winning_competitor = NULL, 
                winning_bid_amount = NULL,
                evaluation_status = 'completed',
                updated_at = CURRENT_TIMESTAMP
            WHERE tender_id = ?
        """
        result = self.execute(sql, (tender_id,))
        return result > 0 if isinstance(result, int) else False
    
    def update_tender_lock_status(self, tender_id: int, locked: bool, 
                                 locked_by: Optional[int] = None) -> bool:
        """Update lock status of a tender"""
        sql = """
            UPDATE company_tenders 
            SET is_locked = ?, locked_at = ?, locked_by = ?, updated_at = ?
            WHERE id = ?
        """
        locked_at = datetime.now() if locked else None
        result = self.execute(sql, (1 if locked else 0, locked_at, locked_by, 
                                      datetime.now(), tender_id))
        return result > 0 if isinstance(result, int) else False
    
    # =========================================================================
    # COMPETITOR BID OPERATIONS
    # =========================================================================
    
    def update_competitor_bid(self, tender_id: str, competitor_name: str, 
                             bid_amount: float, was_winner: bool = False) -> bool:
        """Update or insert competitor bid"""
        # Get company_id from tender
        db = self._get_db()
        company_id = self._get_company_id_from_tender(tender_id)
        if not company_id:
            return False
        
        # Get official estimate
        est_result = db.query_one(
            "SELECT official_estimate FROM company_tenders WHERE tender_id = ?", 
            (tender_id,)
        )
        official_estimate = float(est_result['official_estimate']) if est_result and est_result.get('official_estimate') else 1.0
        
        bid_ratio = bid_amount / official_estimate if official_estimate > 0 else 0.95
        
        # Check if exists
        check_sql = """
            SELECT id FROM competitor_bid_history 
            WHERE tender_id = ? AND competitor_name = ?
        """
        existing = db.query_one(check_sql, (tender_id, competitor_name))
        
        if existing:
            sql = """
                UPDATE competitor_bid_history 
                SET bid_amount = ?,
                    was_winner = ?,
                    bid_ratio = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tender_id = ? AND competitor_name = ?
            """
            result = self.execute(sql, (bid_amount, 1 if was_winner else 0, 
                                          bid_ratio, tender_id, competitor_name))
        else:
            sql = """
                INSERT INTO competitor_bid_history 
                (company_id, competitor_name, tender_id, bid_amount, official_estimate, 
                 bid_ratio, was_winner, bid_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            result = self.execute(sql, (
                company_id, competitor_name, tender_id, bid_amount, official_estimate,
                bid_ratio, 1 if was_winner else 0, datetime.now().date()
            ))
        
        if result and (isinstance(result, int) and result > 0):
            # Update competitor stats
            self.update_competitor_stats_from_bid(
                company_id=company_id,
                competitor_name=competitor_name,
                bid_ratio=bid_ratio,
                was_winner=was_winner
            )
            return True
        return False
    
    def get_competitor_bids(self, tender_id: str, company_id: int) -> List[Dict]:
        """Get all competitor bids for a tender"""
        db = self._get_db()  # ✅ Get the database manager
        
        sql = """
            SELECT competitor_name, bid_amount, was_winner, bid_date
            FROM competitor_bid_history
            WHERE tender_id = ? AND company_id = ?
            ORDER BY bid_amount ASC
        """
        # ✅ Use db.query() instead of self.query()
        return db.query(sql, (tender_id, company_id))

    
    # =========================================================================
    # BID REVISION OPERATIONS
    # =========================================================================
    
    def add_bid_revision(self, tender_id: int, bid_amount: float, 
                        revised_by: int, reason: str) -> bool:
        """Add bid revision history"""
        # Get next revision number
        rev_sql = "SELECT COALESCE(MAX(revision_number), 0) + 1 FROM bid_revisions WHERE tender_id = ?"
        db = self._get_db()
        result = db.query_one(rev_sql, (tender_id,))
        next_rev = result['coalesce'] if result and 'coalesce' in result else 1
        
        sql = """
            INSERT INTO bid_revisions (tender_id, revision_number, bid_amount, 
                                      revised_by, reason, revised_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        result = self.execute(sql, (tender_id, next_rev, bid_amount, 
                                      revised_by, reason, datetime.now()))
        return result > 0 if isinstance(result, int) else False
    
    def get_bid_revisions(self, tender_id: int) -> List[Dict]:
        """Get bid revision history"""
        
        db = self._get_db()
        sql = """
            SELECT revision_number, bid_amount, revised_by, reason, revised_at
            FROM bid_revisions 
            WHERE tender_id = ?
            ORDER BY revision_number DESC
        """
        return db.query(sql, (tender_id,))
    
    # =========================================================================
    # TEAM MANAGEMENT OPERATIONS
    # =========================================================================
    def get_tender_team(self, tender_id: int) -> List[Dict]:
        """Get team members assigned to a tender"""
        db = self._get_db()
        
        # ✅ Use TRUE/FALSE for boolean columns (Supabase compatible)
        sql = """
            SELECT u.id, u.full_name, u.role, ta.role as assigned_role, ta.assigned_at
            FROM tender_team_assignments ta
            JOIN users u ON ta.user_id = u.id
            WHERE ta.tender_id = ? AND ta.is_active = TRUE
            ORDER BY ta.assigned_at DESC
        """
        results = db.query(sql, (tender_id,))
        
        # ✅ Return list of dictionaries (not tuples)
        return results if results else []
    
    def assign_team_member(self, tender_id: int, user_id: int, role: str) -> bool:
        """Assign a team member to a tender"""
        # Check for existing active assignment
        check_sql = """
            SELECT id FROM tender_team_assignments 
            WHERE tender_id = ? AND user_id = ? AND is_active = 1
        """
        db = self._get_db()
        existing = db.query_one(check_sql, (tender_id, user_id))
        
        if existing:
            return True  # Already assigned
        
        sql = """
            INSERT INTO tender_team_assignments (tender_id, user_id, role, assigned_at, is_active)
            VALUES (?, ?, ?, ?, 1)
        """
        result = self.execute(sql, (tender_id, user_id, role, datetime.now()))
        return result > 0 if isinstance(result, int) else False
    
    def remove_team_member(self, tender_id: int, user_id: int) -> bool:
        """Remove a team member assignment (soft delete)"""
        sql = """
            UPDATE tender_team_assignments 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE tender_id = ? AND user_id = ?
        """
        result = self.execute(sql, (tender_id, user_id))
        return result > 0 if isinstance(result, int) else False
    
    # =========================================================================
    # MILESTONE OPERATIONS
    # =========================================================================
    
    def add_milestone(self, tender_id: int, milestone_name: str, due_date: str, 
                     assigned_to: Optional[int], notes: str) -> Optional[int]:
        """Add a milestone/task for a tender"""
        sql = """
            INSERT INTO tender_milestones (
                tender_id, milestone_name, due_date, assigned_to, notes, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?)
        """
        result = self.execute(sql, (tender_id, milestone_name, due_date, 
                                      assigned_to, notes, datetime.now()))
        return result if isinstance(result, int) else None
    
    def get_tender_milestones(self, tender_id: int) -> List[Dict]:
        """Get milestones for a tender - returns List[Dict]"""
        db = self._get_db()
        
        sql = """
            SELECT m.*, u.full_name as assigned_to_name
            FROM tender_milestones m
            LEFT JOIN users u ON m.assigned_to = u.id
            WHERE m.tender_id = ? AND m.is_active = 1
            ORDER BY m.due_date ASC, m.completed DESC
        """
        results = db.query(sql, (tender_id,))
        
        # ✅ Return list (not DataFrame)
        return results if results else []

    
    def complete_milestone(self, milestone_id: int) -> bool:
        """Mark a milestone as completed"""
        sql = """
            UPDATE tender_milestones 
            SET completed = 1, completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        result = self.execute(sql, (milestone_id,))
        return result > 0 if isinstance(result, int) else False
    
    def delete_milestone(self, milestone_id: int) -> bool:
        """Soft delete a milestone"""
        sql = """
            UPDATE tender_milestones 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        result = self.execute(sql, (milestone_id,))
        return result > 0 if isinstance(result, int) else False
    
    # # =========================================================================
    # # USER OPERATIONS
    # # =========================================================================
    
    # def get_all_users(self, company_id: int) -> List[Dict]:
    #     """Get all active users for a company"""
    #     sql = """
    #         SELECT id, username, full_name, email, role, is_active
    #         FROM users
    #         WHERE company_id = ? AND is_active = 1
    #         ORDER BY full_name ASC
    #     """
    #     return db.query(sql, (company_id,))
    
    # def get_user_by_id(self, user_id: int) -> Optional[Dict]:
    #     """Get user by ID"""
    #     sql = "SELECT id, username, full_name, email, role FROM users WHERE id = ? AND is_active = 1"
    #     return db.query_one(sql, (user_id,))
    
    # =========================================================================
    # COMPETITOR STATS OPERATIONS
    # =========================================================================
    
    def update_competitor_stats_from_bid(self, company_id: int, competitor_name: str, 
                                        bid_ratio: float, was_winner: bool) -> bool:
        """Update competitor statistics"""
        # Check if competitor exists
        db = self._get_db()
        check_sql = """
            SELECT id FROM competitor_master 
            WHERE company_id = ? AND competitor_name = ?
        """
        existing = db.query_one(check_sql, (company_id, competitor_name))
        
        if existing:
            # Get current total_bids for calculation
            
            current = db.query_one(
                "SELECT total_bids FROM competitor_master WHERE company_id = ? AND competitor_name = ?",
                (company_id, competitor_name)
            )
            if current:
                current_bids = current.get('total_bids', 0)
                wins = 1 if was_winner else 0
                
                sql = """
                    UPDATE competitor_master 
                    SET total_bids = total_bids + 1,
                        total_wins = total_wins + ?,
                        avg_bid_ratio = (avg_bid_ratio * ? + ?) / (? + 1),
                        last_seen = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE company_id = ? AND competitor_name = ?
                """
                result = self.execute(sql, (wins, current_bids, bid_ratio, current_bids, company_id, competitor_name))
            else:
                wins = 1 if was_winner else 0
                sql = """
                    UPDATE competitor_master 
                    SET total_bids = total_bids + 1,
                        total_wins = total_wins + ?,
                        avg_bid_ratio = (avg_bid_ratio * total_bids + ?) / (total_bids + 1),
                        last_seen = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE company_id = ? AND competitor_name = ?
                """
                result = self.execute(sql, (wins, bid_ratio, company_id, competitor_name))
        else:
            # Insert new competitor
            wins = 1 if was_winner else 0
            sql = """
                INSERT INTO competitor_master 
                (company_id, competitor_name, total_bids, total_wins, avg_bid_ratio, 
                 first_seen, last_seen, is_active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 
                       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            result = self.execute(sql, (company_id, competitor_name, wins, 
                                          bid_ratio, datetime.now().date()))
        
        return result > 0 if isinstance(result, int) else False
    
    def get_competitor_master_list(self, company_id: int, active_only: bool = True) -> List[Dict]:
        """Get competitor master list"""
        
        db = self._get_db()
        sql = "SELECT * FROM competitor_master WHERE company_id = ?"
        params = [company_id]
        
        if active_only:
            sql += " AND is_active = 1"
        
        sql += " ORDER BY competitor_name ASC"
        return db.query(sql, tuple(params))
    
    # =========================================================================
    # STATISTICS OPERATIONS
    # =========================================================================
    
    def get_tender_summary_stats(self, company_id: int) -> Dict[str, Any]:
        """Get summary statistics for tenders"""
        
        db = self._get_db()
        sql = """
            SELECT 
                COUNT(*) as total_tenders,
                SUM(CASE WHEN bid_status = 'won' THEN 1 ELSE 0 END) as won_count,
                SUM(CASE WHEN bid_status = 'submitted' THEN 1 ELSE 0 END) as submitted_count,
                SUM(CASE WHEN bid_status = 'draft' THEN 1 ELSE 0 END) as draft_count,
                SUM(CASE WHEN bid_status = 'lost' THEN 1 ELSE 0 END) as lost_count,
                AVG(CASE WHEN bid_status = 'won' THEN official_estimate ELSE NULL END) as avg_win_value
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
        """
        result = db.query_one(sql, (company_id,))
        return result or {}
    
    def get_tender_count_by_status(self, company_id: int) -> Dict[str, int]:
        """Get count of tenders by status"""
        
        db = self._get_db()
        sql = """
            SELECT bid_status, COUNT(*) as count
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
            GROUP BY bid_status
        """
        results = db.query(sql, (company_id,))
        return {r['bid_status']: r['count'] for r in results}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_company_id_from_tender(self, tender_id: str) -> Optional[int]:
        """Helper to get company_id from tender_id"""
        
        db = self._get_db()
        sql = "SELECT company_id FROM company_tenders WHERE tender_id = ?"
        result = db.query_one(sql, (tender_id,))
        return result['company_id'] if result else None
    
    def get_tender_analyses(self, company_id: int, user_id: int, user_role: str = 'viewer', limit: int = 200) -> List[Dict]:
        """
        Get tender analyses for a company with role-based filtering
        
        Args:
            company_id: Company ID
            user_id: User ID
            user_role: User role (viewer, analyst, manager, etc.)
            limit: Maximum number of records to return
        
        Returns:
            List of analysis records
        """
        db = self._get_db()
        
        try:
            # Build query based on user role
            if user_role in ['admin', 'system_admin', 'company_admin']:
                # Admins can see all analyses for the company
                sql = """
                    SELECT 
                        id, tender_id, tender_title, procuring_entity,
                        official_estimate, recommended_bid, success_probability,
                        confidence_score, risk_level, bid_status,
                        construction_type, division, district, thana,
                        nppi_factor, weighted_average, slt_threshold,
                        risk_strategy, competitor_bids, analysis_date,
                        analysis_type, created_at, updated_at
                    FROM tender_analyses
                    WHERE company_id = ?
                    ORDER BY analysis_date DESC
                    LIMIT ?
                """
                params = [company_id, limit]
            elif user_role in ['manager', 'analyst']:
                # Managers and analysts can see all analyses (same as admin for this module)
                sql = """
                    SELECT 
                        id, tender_id, tender_title, procuring_entity,
                        official_estimate, recommended_bid, success_probability,
                        confidence_score, risk_level, bid_status,
                        construction_type, division, district, thana,
                        nppi_factor, weighted_average, slt_threshold,
                        risk_strategy, competitor_bids, analysis_date,
                        analysis_type, created_at, updated_at
                    FROM tender_analyses
                    WHERE company_id = ?
                    ORDER BY analysis_date DESC
                    LIMIT ?
                """
                params = [company_id, limit]
            else:
                # Viewers can only see their own analyses
                sql = """
                    SELECT 
                        id, tender_id, tender_title, procuring_entity,
                        official_estimate, recommended_bid, success_probability,
                        confidence_score, risk_level, bid_status,
                        construction_type, division, district, thana,
                        nppi_factor, weighted_average, slt_threshold,
                        risk_strategy, competitor_bids, analysis_date,
                        analysis_type, created_at, updated_at
                    FROM tender_analyses
                    WHERE company_id = ? AND user_id = ?
                    ORDER BY analysis_date DESC
                    LIMIT ?
                """
                params = [company_id, user_id, limit]
            
            results = db.query(sql, tuple(params))
            
            # Parse competitor_bids JSON if needed
            for row in results:
                if row.get('competitor_bids') and isinstance(row['competitor_bids'], str):
                    try:
                        row['competitor_bids'] = json.loads(row['competitor_bids'])
                    except:
                        row['competitor_bids'] = []
            
            return results
            
        except Exception as e:
            print(f"Error getting tender analyses: {e}")
            import traceback
            traceback.print_exc()
            return []
