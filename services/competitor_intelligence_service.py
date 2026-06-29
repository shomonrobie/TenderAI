"""
Competitor Intelligence Service
Orchestrates competitor intelligence features using existing CRUD operations
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
from database.crud_operations import DatabaseCRUD
import logging

logger = logging.getLogger(__name__)


class CompetitorIntelligenceService:
    """Service for competitor intelligence features"""
    
    def __init__(self):
        self.db = DatabaseCRUD()
    
    def get_competitor_profile(self, competitor_id: int) -> Optional[Dict]:
        """
        Get complete competitor intelligence profile
        
        Args:
            competitor_id: The competitor's ID
        
        Returns:
            Dictionary with all profile data or None
        """
        company_id = st.session_state.get('company_id')
        if not company_id:
            return None
        
        # Get competitor with stats
        competitor = self.db.get_competitor_with_stats(competitor_id, company_id)
        if not competitor:
            return None
        
        competitor_name = competitor['competitor_name']
        
        # Get all data
        history = self.db.get_competitor_bid_history_with_details(competitor_name, company_id)
        analytics = self.db.get_competitor_analytics(competitor_name, company_id)
        activity_insights = self.db.get_competitor_activity_insights(competitor_name, company_id)
        behavioral_insights = self.db.get_competitor_behavioral_insights(competitor_name, company_id)
        chart_data = self.db.get_competitor_chart_data(competitor_name, company_id)
        
        # Build overview
        overview = {
            'company_name': competitor['competitor_name'],
            'registration_number': competitor.get('business_type', ''),
            'first_active': analytics.get('first_active'),
            'last_active': analytics.get('last_active'),
            'active_months': analytics.get('active_months', 0),
            'total_participations': analytics.get('total_bids', 0),
            'total_wins': analytics.get('total_wins', 0),
            'win_percentage': analytics.get('win_rate', 0),
            'avg_bid': analytics.get('avg_bid', 0),
            'avg_discount': analytics.get('avg_discount', 0),
            'avg_rank': 0,  # Will be calculated from history
            'avg_nppi': analytics.get('avg_nppi', 0),
            'avg_slt': 0,  # Placeholder
            'details': competitor.get('details', '')
        }
        
        # Calculate average rank from history
        if history:
            df = pd.DataFrame(history)
            overview['avg_rank'] = round(df['rank'].mean(), 2) if 'rank' in df.columns else 0
        
        return {
            'competitor': competitor,
            'overview': overview,
            'history': history,
            'analytics': analytics,
            'activity_insights': activity_insights,
            'behavioral_insights': behavioral_insights,
            'charts': chart_data
        }
    
    def get_competitors_list(self, limit: int = 20, offset: int = 0, 
                            search: str = None, sort_by: str = 'competitor_name') -> Dict:
        """
        Get paginated list of competitors
        
        Args:
            limit: Number of records to return
            offset: Offset for pagination
            search: Search term
            sort_by: Column to sort by
        
        Returns:
            Dictionary with competitors list and total count
        """
        company_id = st.session_state.get('company_id')
        if not company_id:
            return {'competitors': [], 'total': 0}
        
        return self.db.get_paginated_competitors(
            company_id, limit, offset, search, sort_by
        )
    
    def get_competitor_summary_stats(self) -> Dict:
        """
        Get summary statistics for all competitors
        
        Returns:
            Dictionary with total, active, avg_win_rate, avg_bid_ratio
        """
        company_id = st.session_state.get('company_id')
        if not company_id:
            return {'total': 0, 'active': 0, 'avg_win_rate': 0, 'avg_bid_ratio': 0}
        
        result = self.db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                ROUND(AVG(CASE WHEN total_bids > 0 THEN (total_wins * 100.0 / total_bids) ELSE 0 END), 2) as avg_win_rate,
                ROUND(AVG(avg_bid_ratio), 4) as avg_bid_ratio
            FROM competitor_master
            WHERE company_id = ?
        """, (company_id,))
        
        if result:
            return result[0]
        return {'total': 0, 'active': 0, 'avg_win_rate': 0, 'avg_bid_ratio': 0}