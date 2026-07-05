# database/crud_competitor.py

"""
CRUD Operations for Competitor Management Module
All database operations for competitors, profiles, and bid history
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, date
import logging
import json

logger = logging.getLogger(__name__)


class CompetitorCRUD:
    """Competitor-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get the database manager - works both as standalone and when bound"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()
    
    # =========================================================================
    # COMPETITOR MASTER OPERATIONS
    # =========================================================================
    
    def get_competitor_master_list(self, company_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all competitors for a company from master list"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, competitor_name, business_type, contact_person,
                phone, email, address, notes,
                first_seen, last_seen, total_bids, total_wins,
                avg_bid_ratio, preferred_strategy, is_active,
                created_at, updated_at
            FROM competitor_master
            WHERE company_id = ?
        """
        params = [company_id]
        
        if active_only:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY competitor_name"
        
        results = db.query(query, tuple(params))
        
        # Normalize boolean values
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
        
        return results
    
    def get_competitor_by_id(self, competitor_id: int) -> Optional[Dict[str, Any]]:
        """Get a single competitor by ID"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                id, company_id, competitor_name, business_type, contact_person,
                phone, email, address, notes,
                first_seen, last_seen, total_bids, total_wins,
                avg_bid_ratio, preferred_strategy, is_active,
                created_at, updated_at
            FROM competitor_master
            WHERE id = ?
        """, (competitor_id,))
        
        if result:
            result['is_active'] = bool(result.get('is_active', False))
        
        return result
    
    def get_competitor_by_name(self, company_id: int, competitor_name: str) -> Optional[Dict[str, Any]]:
        """Get competitor by name for a company"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT 
                id, competitor_name, business_type, contact_person,
                phone, email, address, notes,
                first_seen, last_seen, total_bids, total_wins,
                avg_bid_ratio, preferred_strategy, is_active,
                created_at, updated_at
            FROM competitor_master
            WHERE company_id = ? AND competitor_name = ?
        """, (company_id, competitor_name))
    
    def add_competitor_to_master(self, company_id: int, competitor_data: Dict[str, Any]) -> Optional[int]:
        """Add a new competitor to master list"""
        db = self._get_db()
        
        try:
            # Check if competitor already exists
            existing = self.get_competitor_by_name(company_id, competitor_data.get('competitor_name', ''))
            if existing:
                return None
            
            # Insert competitor
            db.execute("""
                INSERT INTO competitor_master (
                    company_id, competitor_name, business_type, contact_person,
                    phone, email, address, notes,
                    preferred_strategy, is_active,
                    first_seen, last_seen, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                competitor_data.get('competitor_name'),
                competitor_data.get('business_type', 'Construction Company'),
                competitor_data.get('contact_person'),
                competitor_data.get('phone'),
                competitor_data.get('email'),
                competitor_data.get('address'),
                competitor_data.get('notes'),
                competitor_data.get('preferred_strategy', 'Unknown'),
                True,
                datetime.now().date().isoformat(),
                datetime.now().date().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # Get the inserted ID
            result = db.query_one("""
                SELECT id FROM competitor_master 
                WHERE company_id = ? AND competitor_name = ?
                ORDER BY created_at DESC LIMIT 1
            """, (company_id, competitor_data.get('competitor_name')))
            
            return result.get('id') if result else None
            
        except Exception as e:
            logger.error(f"Error adding competitor to master: {e}")
            return None
    
    def update_competitor_master(self, competitor_id: int, updates: Dict[str, Any]) -> bool:
        """Update competitor in master list"""
        db = self._get_db()
        
        try:
            allowed_fields = [
                'competitor_name', 'business_type', 'contact_person',
                'phone', 'email', 'address', 'notes',
                'preferred_strategy', 'is_active'
            ]
            
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
            params.append(competitor_id)
            
            db.execute(f"""
                UPDATE competitor_master 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, tuple(params))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating competitor master: {e}")
            return False
    
    def delete_competitor_master(self, competitor_id: int) -> bool:
        """Soft delete a competitor (set is_active = FALSE)"""
        db = self._get_db()
        
        try:
            db.execute("""
                UPDATE competitor_master 
                SET is_active = FALSE, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), competitor_id))
            return True
        except Exception as e:
            logger.error(f"Error deleting competitor master: {e}")
            return False
    
    # =========================================================================
    # COMPETITOR PROFILES OPERATIONS
    # =========================================================================
    
    def get_competitor_profiles(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all competitor profiles for a company"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                id, company_id, competitor_name, competitor_type,
                first_seen, last_seen, total_appearances, wins_count,
                avg_bid_ratio, bid_std_dev, strategy, notes,
                created_at, updated_at
            FROM competitor_profiles
            WHERE company_id = ?
            ORDER BY total_appearances DESC, competitor_name
        """, (company_id,))
    
    def get_competitor_profile_by_name(self, company_id: int, competitor_name: str) -> Optional[Dict[str, Any]]:
        """Get competitor profile by name"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT 
                id, company_id, competitor_name, competitor_type,
                first_seen, last_seen, total_appearances, wins_count,
                avg_bid_ratio, bid_std_dev, strategy, notes,
                created_at, updated_at
            FROM competitor_profiles
            WHERE company_id = ? AND competitor_name = ?
        """, (company_id, competitor_name))
    
    def update_competitor_profile(self, company_id: int, competitor_name: str, data: Dict[str, Any]) -> bool:
        """Update competitor profile"""
        db = self._get_db()
        
        try:
            allowed_fields = [
                'competitor_type', 'strategy', 'notes',
                'total_appearances', 'wins_count', 'avg_bid_ratio', 'bid_std_dev',
                'first_seen', 'last_seen'
            ]
            
            set_clauses = []
            params = []
            
            for key, value in data.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(company_id)
            params.append(competitor_name)
            
            db.execute(f"""
                UPDATE competitor_profiles 
                SET {', '.join(set_clauses)}
                WHERE company_id = ? AND competitor_name = ?
            """, tuple(params))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating competitor profile: {e}")
            return False
    
    def upsert_competitor_profile(self, company_id: int, competitor_name: str, data: Dict[str, Any]) -> bool:
        """Insert or update competitor profile"""
        db = self._get_db()
        
        try:
            # Check if profile exists
            existing = self.get_competitor_profile_by_name(company_id, competitor_name)
            
            if existing:
                # Update existing
                return self.update_competitor_profile(company_id, competitor_name, data)
            else:
                # Insert new
                db.execute("""
                    INSERT INTO competitor_profiles (
                        company_id, competitor_name, competitor_type,
                        first_seen, last_seen, total_appearances, wins_count,
                        avg_bid_ratio, bid_std_dev, strategy, notes,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    competitor_name,
                    data.get('competitor_type', 'Construction Company'),
                    data.get('first_seen', datetime.now().date().isoformat()),
                    data.get('last_seen', datetime.now().date().isoformat()),
                    data.get('total_appearances', 0),
                    data.get('wins_count', 0),
                    data.get('avg_bid_ratio', 0.0),
                    data.get('bid_std_dev', 0.0),
                    data.get('strategy', 'Unknown'),
                    data.get('notes'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                return True
                
        except Exception as e:
            logger.error(f"Error upserting competitor profile: {e}")
            return False
    
    # =========================================================================
    # COMPETITOR BID HISTORY OPERATIONS
    # =========================================================================
    
    def get_competitor_bid_history(
        self, 
        company_id: int, 
        competitor_name: Optional[str] = None, 
        tender_id: Optional[str] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get competitor bid history"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, company_id, competitor_name, tender_id,
                bid_amount, official_estimate, bid_ratio,
                was_winner, bid_date, created_at
            FROM competitor_bid_history
            WHERE company_id = ?
        """
        params = [company_id]
        
        if competitor_name:
            query += " AND competitor_name = ?"
            params.append(competitor_name)
        
        if tender_id:
            query += " AND tender_id = ?"
            params.append(tender_id)
        
        query += " ORDER BY bid_date DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.query(query, tuple(params))
        
        # Normalize boolean
        for row in results:
            row['was_winner'] = bool(row.get('was_winner', False))
        
        return results
    
    def add_competitor_bid_history(self, company_id: int, data: Dict[str, Any]) -> bool:
        """Add competitor bid history record"""
        db = self._get_db()
        
        try:
            # Calculate bid ratio if not provided
            bid_ratio = data.get('bid_ratio')
            if not bid_ratio and data.get('official_estimate', 0) > 0:
                bid_ratio = data.get('bid_amount', 0) / data.get('official_estimate', 1)
            elif not bid_ratio:
                bid_ratio = 0.0
            
            db.execute("""
                INSERT INTO competitor_bid_history (
                    company_id, competitor_name, tender_id,
                    bid_amount, official_estimate, bid_ratio,
                    was_winner, bid_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                data.get('competitor_name'),
                data.get('tender_id'),
                data.get('bid_amount', 0),
                data.get('official_estimate', 0),
                bid_ratio,
                1 if data.get('was_winner', False) else 0,
                data.get('bid_date', datetime.now().date().isoformat()),
                datetime.now().isoformat()
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding competitor bid history: {e}")
            return False
    
    def get_competitor_bids_for_tender(self, tender_id: str) -> List[Dict[str, Any]]:
        """Get competitor bids for a specific tender"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                id, competitor_name, total_bid_amount as bid_amount,
                submission_date, is_winner
            FROM competitor_bids
            WHERE tender_id = ?
            ORDER BY total_bid_amount ASC
        """, (tender_id,))
    
    def add_competitor_bid(self, data: Dict[str, Any]) -> bool:
        """Add competitor bid for a tender"""
        db = self._get_db()
        
        try:
            db.execute("""
                INSERT INTO competitor_bids (
                    tender_id, competitor_name, total_bid_amount,
                    submission_date, is_winner
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                data.get('tender_id'),
                data.get('competitor_name'),
                data.get('total_bid_amount', 0),
                data.get('submission_date', datetime.now().isoformat()),
                1 if data.get('is_winner', False) else 0
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding competitor bid: {e}")
            return False
    
    def update_competitor_bid(self, bid_id: int, updates: Dict[str, Any]) -> bool:
        """Update competitor bid"""
        db = self._get_db()
        
        try:
            allowed_fields = ['total_bid_amount', 'is_winner', 'submission_date']
            
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return True
            
            params.append(bid_id)
            
            db.execute(f"""
                UPDATE competitor_bids 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, tuple(params))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating competitor bid: {e}")
            return False
    
    def delete_competitor_bid(self, bid_id: int) -> bool:
        """Delete competitor bid"""
        db = self._get_db()
        
        try:
            db.execute("DELETE FROM competitor_bids WHERE id = ?", (bid_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting competitor bid: {e}")
            return False
    
    # =========================================================================
    # COMPETITOR ANALYTICS OPERATIONS
    # =========================================================================
    
    def get_competitor_intelligence_summary(self, company_id: int) -> Dict[str, Any]:
        """Get intelligence summary for a company"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                COUNT(*) as total_competitors,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_competitors,
                SUM(total_bids) as total_bids,
                SUM(total_wins) as total_wins,
                AVG(avg_bid_ratio) as avg_market_ratio,
                SUM(CASE WHEN preferred_strategy = 'Aggressive' THEN 1 ELSE 0 END) as aggressive_count,
                SUM(CASE WHEN preferred_strategy = 'Moderate' THEN 1 ELSE 0 END) as moderate_count,
                SUM(CASE WHEN preferred_strategy = 'Conservative' THEN 1 ELSE 0 END) as conservative_count,
                SUM(CASE WHEN preferred_strategy = 'Variable' THEN 1 ELSE 0 END) as variable_count
            FROM competitor_master
            WHERE company_id = ?
        """, (company_id,))
        
        if not result:
            return {
                'total_competitors': 0,
                'active_competitors': 0,
                'total_bids': 0,
                'total_wins': 0,
                'avg_market_ratio': 0.0,
                'overall_win_rate': 0.0,
                'aggressive_count': 0,
                'moderate_count': 0,
                'conservative_count': 0,
                'variable_count': 0
            }
        
        total_bids = result.get('total_bids', 0) or 0
        total_wins = result.get('total_wins', 0) or 0
        result['overall_win_rate'] = (total_wins / total_bids * 100) if total_bids > 0 else 0
        
        return result
    
    def get_competitor_strategy_insights(self, company_id: int) -> Dict[str, Any]:
        """Get competitor strategy insights"""
        db = self._get_db()
        
        results = db.query("""
            SELECT 
                competitor_name, strategy, avg_bid_ratio, 
                total_appearances, wins_count,
                CASE 
                    WHEN total_appearances > 0 THEN CAST(wins_count AS FLOAT) / total_appearances 
                    ELSE 0 
                END as win_rate
            FROM competitor_profiles
            WHERE company_id = ? AND total_appearances >= 2
            ORDER BY total_appearances DESC
        """, (company_id,))
        
        if not results:
            return {
                'total_tracked': 0,
                'aggressive': [],
                'moderate': [],
                'conservative': [],
                'high_win_rate': [],
                'most_frequent': [],
                'market_aggression_index': 0.0
            }
        
        aggressive = [r for r in results if r.get('strategy') == 'Aggressive']
        moderate = [r for r in results if r.get('strategy') == 'Moderate']
        conservative = [r for r in results if r.get('strategy') == 'Conservative']
        high_win_rate = [r for r in results if r.get('win_rate', 0) > 0.5]
        most_frequent = sorted(results, key=lambda x: x.get('total_appearances', 0), reverse=True)[:5]
        
        # Calculate market aggression index
        total_appearances = sum(r.get('total_appearances', 0) for r in results)
        aggressive_appearances = sum(r.get('total_appearances', 0) for r in aggressive)
        market_aggression_index = aggressive_appearances / total_appearances if total_appearances > 0 else 0.5
        
        return {
            'total_tracked': len(results),
            'aggressive': aggressive,
            'moderate': moderate,
            'conservative': conservative,
            'high_win_rate': high_win_rate,
            'most_frequent': most_frequent,
            'market_aggression_index': market_aggression_index
        }
    
    def get_competitor_stats(self, company_id: int, competitor_name: Optional[str] = None) -> Dict[str, Any]:
        """Get competitor statistics"""
        db = self._get_db()
        
        if competitor_name:
            # Get stats for specific competitor
            result = db.query_one("""
                SELECT 
                    competitor_name,
                    total_bids, total_wins,
                    avg_bid_ratio, preferred_strategy,
                    first_seen, last_seen, is_active
                FROM competitor_master
                WHERE company_id = ? AND competitor_name = ?
            """, (company_id, competitor_name))
            
            if result:
                result['win_rate'] = (result.get('total_wins', 0) / result.get('total_bids', 1) * 100) if result.get('total_bids', 0) > 0 else 0
                result['is_active'] = bool(result.get('is_active', False))
            
            return result or {}
        else:
            # Get aggregated stats
            result = db.query_one("""
                SELECT 
                    COUNT(*) as total_competitors,
                    SUM(total_bids) as total_bids,
                    SUM(total_wins) as total_wins,
                    AVG(avg_bid_ratio) as avg_market_ratio
                FROM competitor_master
                WHERE company_id = ? AND is_active = TRUE
            """, (company_id,))
            
            if result:
                total_bids = result.get('total_bids', 0) or 0
                total_wins = result.get('total_wins', 0) or 0
                result['overall_win_rate'] = (total_wins / total_bids * 100) if total_bids > 0 else 0
                result['avg_market_ratio'] = result.get('avg_market_ratio', 0) or 0
            
            return result or {}
    
    # =========================================================================
    # COMPETITOR TRACKING OPERATIONS
    # =========================================================================
    
    def update_competitor_stats_from_bid(
        self, 
        company_id: int, 
        competitor_name: str, 
        bid_ratio: float, 
        was_winner: bool
    ) -> bool:
        """Update competitor master stats from a bid"""
        db = self._get_db()
        
        try:
            # Get current competitor
            competitor = self.get_competitor_by_name(company_id, competitor_name)
            
            if not competitor:
                return False
            
            competitor_id = competitor.get('id')
            total_bids = competitor.get('total_bids', 0) + 1
            total_wins = competitor.get('total_wins', 0) + (1 if was_winner else 0)
            
            # Update avg_bid_ratio
            old_avg = competitor.get('avg_bid_ratio', 0.92)
            old_total = competitor.get('total_bids', 0)
            new_avg = ((old_avg * old_total) + bid_ratio) / total_bids if total_bids > 0 else bid_ratio
            
            # Determine preferred strategy
            strategy = 'Aggressive' if new_avg < 0.88 else 'Moderate' if new_avg < 0.92 else 'Conservative'
            
            db.execute("""
                UPDATE competitor_master 
                SET 
                    total_bids = ?,
                    total_wins = ?,
                    avg_bid_ratio = ?,
                    preferred_strategy = ?,
                    last_seen = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                total_bids,
                total_wins,
                new_avg,
                strategy,
                datetime.now().date().isoformat(),
                datetime.now().isoformat(),
                competitor_id
            ))
            
            # Also update competitor profile
            profile = self.get_competitor_profile_by_name(company_id, competitor_name)
            if profile:
                profile_id = profile.get('id')
                profile_appearances = profile.get('total_appearances', 0) + 1
                profile_wins = profile.get('wins_count', 0) + (1 if was_winner else 0)
                
                # Update profile
                db.execute("""
                    UPDATE competitor_profiles 
                    SET 
                        total_appearances = ?,
                        wins_count = ?,
                        avg_bid_ratio = ?,
                        strategy = ?,
                        last_seen = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    profile_appearances,
                    profile_wins,
                    new_avg,
                    strategy,
                    datetime.now().date().isoformat(),
                    datetime.now().isoformat(),
                    profile_id
                ))
            else:
                # Create new profile
                db.execute("""
                    INSERT INTO competitor_profiles (
                        company_id, competitor_name, 
                        first_seen, last_seen, 
                        total_appearances, wins_count,
                        avg_bid_ratio, strategy,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    competitor_name,
                    datetime.now().date().isoformat(),
                    datetime.now().date().isoformat(),
                    1,
                    1 if was_winner else 0,
                    bid_ratio,
                    strategy,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating competitor stats: {e}")
            return False
    
    def get_competitor_predictions(
        self, 
        company_id: int, 
        competitor_name: str, 
        official_estimate: float
    ) -> Dict[str, Any]:
        """Get competitor bid predictions"""
        db = self._get_db()
        
        # Get competitor profile
        profile = self.get_competitor_profile_by_name(company_id, competitor_name)
        
        if not profile:
            # Default prediction for unknown competitor
            return {
                'predicted_bid': official_estimate * 0.91,
                'strategy': 'Unknown',
                'confidence': 0.40,
                'appearances': 0,
                'win_rate': 0,
                'min_expected': official_estimate * 0.85,
                'max_expected': official_estimate * 0.96
            }
        
        avg_ratio = profile.get('avg_bid_ratio', 0.92)
        std_dev = profile.get('bid_std_dev', 0.05)
        strategy = profile.get('strategy', 'Unknown')
        appearances = profile.get('total_appearances', 0)
        wins = profile.get('wins_count', 0)
        
        # Calculate confidence based on data points
        confidence = min(0.95, 0.50 + (appearances * 0.03))
        
        # Predict with confidence interval
        predicted_ratio = avg_ratio
        min_ratio = max(0.75, avg_ratio - (std_dev * 1.5))
        max_ratio = min(1.00, avg_ratio + (std_dev * 1.5))
        
        return {
            'predicted_bid': official_estimate * predicted_ratio,
            'strategy': strategy,
            'confidence': confidence,
            'appearances': appearances,
            'win_rate': wins / appearances if appearances > 0 else 0,
            'min_expected': official_estimate * min_ratio,
            'max_expected': official_estimate * max_ratio
        }
    
    # =========================================================================
    # COMPETITOR FILTERING OPERATIONS
    # =========================================================================
    
    def get_competitors_by_procurement_type(self, company_id: int, procurement_type: str) -> List[Dict[str, Any]]:
        """Get competitors filtered by procurement type"""
        db = self._get_db()
        
        # Get competitors with bidding history for this procurement type
        results = db.query("""
            SELECT DISTINCT 
                cm.id,
                cm.competitor_name,
                cm.business_type,
                cm.avg_bid_ratio,
                cm.total_bids,
                cm.total_wins,
                cm.preferred_strategy,
                cm.first_seen,
                cm.last_seen,
                cm.is_active,
                (SELECT COUNT(*) FROM competitor_bids cb 
                 WHERE cb.competitor_name = cm.competitor_name 
                 AND cb.tender_id IN (SELECT tender_id FROM company_tenders WHERE company_id = ? AND procurement_type = ?)
                ) as type_bid_count
            FROM competitor_master cm
            LEFT JOIN competitor_bids cb ON cm.competitor_name = cb.competitor_name
            LEFT JOIN company_tenders ct ON cb.tender_id = ct.tender_id
            WHERE cm.company_id = ? 
              AND cm.is_active = TRUE
              AND (ct.procurement_type = ? OR ct.procurement_type IS NULL)
            GROUP BY cm.id
            ORDER BY cm.competitor_name
        """, (company_id, procurement_type, company_id, procurement_type))
        
        # Normalize boolean
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
        
        return results
    
    def get_competitors_for_company(
        self, 
        company_id: int, 
        procurement_type: Optional[str] = None, 
        search_term: str = ""
    ) -> List[Dict[str, Any]]:
        """Get competitors for a company with optional filters"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, competitor_name, business_type,
                avg_bid_ratio, total_bids, total_wins,
                preferred_strategy, first_seen, last_seen, is_active
            FROM competitor_master
            WHERE company_id = ? AND is_active = TRUE
        """
        params = [company_id]
        
        if procurement_type:
            # Filter by procurement type using subquery
            query += """
                AND competitor_name IN (
                    SELECT DISTINCT competitor_name 
                    FROM competitor_bids 
                    WHERE tender_id IN (
                        SELECT tender_id FROM company_tenders 
                        WHERE company_id = ? AND procurement_type = ?
                    )
                )
            """
            params.extend([company_id, procurement_type])
        
        query += " ORDER BY competitor_name"
        
        results = db.query(query, tuple(params))
        
        # Apply search filter
        if search_term:
            search_lower = search_term.lower()
            results = [
                r for r in results 
                if search_lower in r.get('competitor_name', '').lower() 
                or search_lower in r.get('business_type', '').lower()
            ]
        
        # Normalize boolean
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
        
        return results
    
    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================
    
    def get_competitor_names(self, company_id: int, active_only: bool = True) -> List[str]:
        """Get list of competitor names"""
        db = self._get_db()
        
        query = "SELECT competitor_name FROM competitor_master WHERE company_id = ?"
        params = [company_id]
        
        if active_only:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY competitor_name"
        
        results = db.query(query, tuple(params))
        return [r.get('competitor_name', '') for r in results if r.get('competitor_name')]
    
    def get_competitor_activity_summary(self, company_id: int) -> Dict[str, Any]:
        """Get competitor activity summary for dashboard"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active,
                SUM(total_bids) as total_bids,
                SUM(total_wins) as total_wins,
                AVG(avg_bid_ratio) as avg_ratio
            FROM competitor_master
            WHERE company_id = ?
        """, (company_id,))
        
        if not result:
            return {
                'total': 0,
                'active': 0,
                'total_bids': 0,
                'total_wins': 0,
                'avg_ratio': 0.0,
                'win_rate': 0.0
            }
        
        total_bids = result.get('total_bids', 0) or 0
        total_wins = result.get('total_wins', 0) or 0
        
        return {
            'total': result.get('total', 0) or 0,
            'active': result.get('active', 0) or 0,
            'total_bids': total_bids,
            'total_wins': total_wins,
            'avg_ratio': result.get('avg_ratio', 0.0) or 0.0,
            'win_rate': (total_wins / total_bids * 100) if total_bids > 0 else 0.0
        }