# modules/competitor_helper.py

import sqlite3
import random
from typing import List, Dict, Any, Optional

DB_PATH = "data/tender_system.db"

def get_competitor_profiles(company_id: int, procurement_type: str = None) -> List[Dict[str, Any]]:
    """
    Fetch competitor profiles for a company, optionally filtered by procurement type.
    
    Args:
        company_id: The company ID
        procurement_type: 'works', 'goods', or 'services' - if provided, filters competitors
                          that have bidding history for this type.
    
    Returns:
        List of competitor profiles with avg_bid_ratio, total_bids, etc.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First, get all active competitors
    cursor.execute("""
        SELECT id, competitor_name, business_type, avg_bid_ratio, total_bids, total_wins,
               preferred_strategy, first_seen, last_seen, is_active
        FROM competitor_master
        WHERE company_id = ? AND is_active = 1
        ORDER BY competitor_name
    """, (company_id,))
    
    all_competitors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not procurement_type:
        return all_competitors
    
    # Filter by procurement type if provided
    # Check if competitor has bidding history for this procurement type
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    filtered = []
    for comp in all_competitors:
        # Check if this competitor appears in historical_tenders with matching procurement_type
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM historical_tenders 
            WHERE company_id = ? 
              AND procurement_type = ?
              AND (competitors_data LIKE ? OR winning_competitor = ?)
            LIMIT 1
        """, (company_id, procurement_type, f'%{comp["competitor_name"]}%', comp["competitor_name"]))
        
        result = cursor.fetchone()
        if result and result['count'] > 0:
            filtered.append(comp)
        else:
            # Also check competitor_bids table
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM competitor_bids cb
                JOIN company_tenders ct ON cb.tender_id = ct.tender_id
                WHERE ct.company_id = ? 
                  AND ct.procurement_type = ?
                  AND cb.competitor_name = ?
                LIMIT 1
            """, (company_id, procurement_type, comp["competitor_name"]))
            
            result = cursor.fetchone()
            if result and result['count'] > 0:
                filtered.append(comp)
    
    conn.close()
    
    # If no competitors found for this procurement type, return all (with warning)
    if not filtered:
        # Fallback: return all competitors but mark them as "unverified"
        for comp in all_competitors:
            comp['unverified_for_type'] = True
        return all_competitors
    
    return filtered


def get_competitors_by_procurement_type(company_id: int, procurement_type: str) -> List[Dict[str, Any]]:
    """
    Get competitors specifically filtered by procurement type.
    This is a more efficient version that does the filtering in SQL.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get competitors that have bidding history for this procurement type
    # Using the competitor_bids table joined with company_tenders
    cursor.execute("""
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
            cm.is_active
        FROM competitor_master cm
        JOIN competitor_bids cb ON cm.competitor_name = cb.competitor_name
        JOIN company_tenders ct ON cb.tender_id = ct.tender_id
        WHERE cm.company_id = ? 
          AND ct.company_id = ?
          AND ct.procurement_type = ?
          AND cm.is_active = 1
        GROUP BY cm.id
        ORDER BY cm.competitor_name
    """, (company_id, company_id, procurement_type))
    
    competitors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not competitors:
        # Fallback: get all active competitors
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, competitor_name, business_type, avg_bid_ratio, total_bids, total_wins,
                   preferred_strategy, first_seen, last_seen, is_active
            FROM competitor_master
            WHERE company_id = ? AND is_active = 1
            ORDER BY competitor_name
        """, (company_id,))
        competitors = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return competitors


def get_competitor_bids_from_profiles(profiles: List[Dict[str, Any]], 
                                      official_estimate: float, 
                                      random_factor: float = 0.02) -> List[float]:
    """
    Generate bid amounts from competitor profiles based on their avg_bid_ratio.
    Adds slight randomness to simulate realistic variation.
    
    Args:
        profiles: List of competitor profile dicts (from get_competitor_profiles)
        official_estimate: The official estimate for the current tender
        random_factor: Random variation factor (±%)
    
    Returns:
        List of generated bid amounts
    """
    if not profiles:
        return []
    
    bids = []
    for comp in profiles:
        # Use avg_bid_ratio if available, otherwise default to 0.92
        ratio = comp.get('avg_bid_ratio', 0.92)
        if ratio == 0 or ratio is None:
            ratio = 0.92
        
        # Add randomness ±random_factor * ratio
        noise = 1 + random.uniform(-random_factor, random_factor)
        bid = official_estimate * ratio * noise
        bids.append(round(bid, 3))
    return bids


def sample_competitors_from_profiles(profiles: List[Dict[str, Any]], 
                                     count: int) -> List[Dict[str, Any]]:
    """
    Randomly sample `count` competitors from the profiles list.
    If count > len(profiles), sample with replacement.
    """
    if not profiles:
        return []
    if count <= len(profiles):
        return random.sample(profiles, count)
    else:
        # Sample with replacement to reach desired count
        return random.choices(profiles, k=count)


def get_competitor_stats(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get aggregated competitor statistics from profiles.
    """
    if not profiles:
        return {'count': 0, 'avg_ratio': 0, 'avg_bids': 0, 'avg_wins': 0}
    
    total_bids = sum(p.get('total_bids', 0) for p in profiles)
    total_wins = sum(p.get('total_wins', 0) for p in profiles)
    avg_ratio = sum(p.get('avg_bid_ratio', 0.92) for p in profiles) / len(profiles)
    
    return {
        'count': len(profiles),
        'avg_ratio': round(avg_ratio, 4),
        'total_bids': total_bids,
        'total_wins': total_wins,
        'win_rate': round(total_wins / total_bids if total_bids > 0 else 0, 4)
    }


def get_competitor_names(profiles: List[Dict[str, Any]]) -> List[str]:
    """Get list of competitor names from profiles."""
    return [p.get('competitor_name', 'Unknown') for p in profiles]