# crud_competitors.py
# Data access layer for all competitor tables.
# Uses unified_db_manager for database operations.

from unified_db_manager import DatabaseManager
from connections import get_db_connection

# Assume get_db_connection() returns a connection object compatible with DatabaseManager
# or that DatabaseManager is a singleton.

class CompetitorCRUD:
    """CRUD operations for competitor intelligence tables."""
    
    def __init__(self):
        self.db = DatabaseManager(get_db_connection())
    
    # ------------------- competitor_master -------------------
    def get_tracked_competitors(self, company_id: int):
        """Get all competitors tracked by a company (list view)."""
        query = """
            SELECT id, competitor_name, business_type, 
                   first_seen, last_seen, total_bids, total_wins,
                   avg_bid_ratio, preferred_strategy, is_active
            FROM competitor_master
            WHERE company_id = %s
            ORDER BY total_bids DESC, competitor_name
        """
        return self.db.fetch_all(query, (company_id,))
    
    def get_competitor_summary(self, company_id: int, competitor_name: str):
        """Get high-level stats for a single competitor."""
        query = """
            SELECT id, competitor_name, business_type,
                   first_seen, last_seen, total_bids, total_wins,
                   avg_bid_ratio, preferred_strategy, is_active,
                   notes, contact_person, phone, email, address
            FROM competitor_master
            WHERE company_id = %s AND competitor_name = %s
        """
        return self.db.fetch_one(query, (company_id, competitor_name))
    
    def add_competitor(self, company_id: int, data: dict):
        """Insert a new competitor into master."""
        # data dict with keys: competitor_name, business_type, contact_person,
        # phone, email, address, notes, preferred_strategy, is_active
        query = """
            INSERT INTO competitor_master 
            (company_id, competitor_name, business_type, contact_person,
             phone, email, address, notes, preferred_strategy, is_active,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """
        params = (
            company_id,
            data['competitor_name'],
            data.get('business_type'),
            data.get('contact_person'),
            data.get('phone'),
            data.get('email'),
            data.get('address'),
            data.get('notes'),
            data.get('preferred_strategy'),
            data.get('is_active', True)
        )
        return self.db.fetch_one(query, params)['id']
    
    def update_competitor(self, company_id: int, competitor_name: str, data: dict):
        """Update existing competitor in master."""
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        values = list(data.values())
        values.extend([company_id, competitor_name])
        query = f"""
            UPDATE competitor_master
            SET {set_clause}, updated_at = NOW()
            WHERE company_id = %s AND competitor_name = %s
        """
        return self.db.execute(query, values) > 0
    
    # ------------------- competitor_profiles -------------------
    def get_competitor_profile(self, company_id: int, competitor_name: str):
        """Fetch detailed behavioural profile."""
        query = """
            SELECT competitor_name, competitor_type, first_seen, last_seen,
                   total_appearances, wins_count, avg_bid_ratio, bid_std_dev,
                   strategy, notes
            FROM competitor_profiles
            WHERE company_id = %s AND competitor_name = %s
        """
        return self.db.fetch_one(query, (company_id, competitor_name))
    
    def update_profile(self, company_id: int, competitor_name: str, data: dict):
        """Update profile fields."""
        # similar to update_competitor, but on competitor_profiles
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        values = list(data.values())
        values.extend([company_id, competitor_name])
        query = f"""
            UPDATE competitor_profiles
            SET {set_clause}, updated_at = NOW()
            WHERE company_id = %s AND competitor_name = %s
        """
        return self.db.execute(query, values) > 0
    
    # ------------------- competitor_bids -------------------
    def get_bids_for_tender(self, tender_id: str):
        """Get all competitor bids for a specific tender."""
        query = """
            SELECT id, competitor_name, total_bid_amount, 
                   submission_date, is_winner
            FROM competitor_bids
            WHERE tender_id = %s
            ORDER BY total_bid_amount
        """
        return self.db.fetch_all(query, (tender_id,))
    
    def get_all_competitor_bids(self, company_id: int = None):
        """Get all competitor bids (optionally filtered by company)."""
        # This table does not have company_id, so we join with company_tenders
        query = """
            SELECT cb.tender_id, cb.competitor_name, cb.total_bid_amount,
                   cb.submission_date, cb.is_winner,
                   ct.company_id, ct.official_estimate
            FROM competitor_bids cb
            JOIN company_tenders ct ON cb.tender_id = ct.tender_id
            WHERE (%s IS NULL OR ct.company_id = %s)
            ORDER BY cb.submission_date DESC
        """
        return self.db.fetch_all(query, (company_id, company_id))
    
    def insert_bid(self, data: dict):
        """Insert a new competitor bid."""
        query = """
            INSERT INTO competitor_bids 
            (tender_id, competitor_name, total_bid_amount, submission_date, is_winner)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            data['tender_id'],
            data['competitor_name'],
            data['total_bid_amount'],
            data.get('submission_date'),
            data.get('is_winner', 0)
        )
        return self.db.fetch_one(query, params)['id']
    
    # ------------------- competitor_bid_history -------------------
    def get_bid_history(self, company_id: int, competitor_name: str, 
                        filters: dict = None):
        """
        Get historical bids for a specific competitor against this company.
        filters: dict with keys: sector, region, year, min_ratio, max_ratio, etc.
        """
        query = """
            SELECT company_id, competitor_name, tender_id, bid_amount,
                   official_estimate, bid_ratio, was_winner, bid_date,
                   ct.tender_title, ct.division, ct.district,
                   ct.procuring_entity, ct.tender_title
            FROM competitor_bid_history
            JOIN company_tenders ct ON competitor_bid_history.tender_id = ct.tender_id
            WHERE company_id = %s AND competitor_name = %s
        """
        params = [company_id, competitor_name]
        
        # Apply filters if provided
        if filters:
            if 'sector' in filters:
                # You'll need a way to filter by sector; assuming tender_title contains sector
                query += " AND ct.tender_title ILIKE %s"
                params.append(f"%{filters['sector']}%")
            if 'region' in filters:
                query += " AND ct.division = %s"
                params.append(filters['region'])
            if 'year' in filters:
                query += " AND EXTRACT(YEAR FROM bid_date) = %s"
                params.append(filters['year'])
            if 'min_ratio' in filters:
                query += " AND bid_ratio >= %s"
                params.append(filters['min_ratio'])
            if 'max_ratio' in filters:
                query += " AND bid_ratio <= %s"
                params.append(filters['max_ratio'])
        
        query += " ORDER BY bid_date DESC"
        return self.db.fetch_all(query, tuple(params))
    
    def refresh_bid_history_for_company(self, company_id: int):
        """
        Materialize competitor_bid_history from competitor_bids and company_tenders.
        This should be called after new bids are inserted to keep history up-to-date.
        """
        # First, delete existing history for this company to avoid duplicates
        del_query = "DELETE FROM competitor_bid_history WHERE company_id = %s"
        self.db.execute(del_query, (company_id,))
        
        # Then insert fresh data
        ins_query = """
            INSERT INTO competitor_bid_history 
            (company_id, competitor_name, tender_id, bid_amount,
             official_estimate, bid_ratio, was_winner, bid_date, created_at)
            SELECT 
                ct.company_id,
                cb.competitor_name,
                cb.tender_id,
                cb.total_bid_amount,
                ct.official_estimate,
                (cb.total_bid_amount / ct.official_estimate) AS bid_ratio,
                (cb.is_winner = 1) AS was_winner,
                cb.submission_date::date AS bid_date,
                NOW()
            FROM competitor_bids cb
            JOIN company_tenders ct ON cb.tender_id = ct.tender_id
            WHERE ct.company_id = %s
        """
        return self.db.execute(ins_query, (company_id,))