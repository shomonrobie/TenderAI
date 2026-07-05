# modules/competitor_helper.py - Refactored to use CompetitorCRUD

import random
from typing import List, Dict, Any, Optional
from database.unified_db_manager import get_db_manager


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
    db = get_db_manager()
    
    # ✅ Use CRUD method
    if procurement_type:
        competitors = db.get_competitors_by_procurement_type(company_id, procurement_type)
    else:
        competitors = db.get_competitor_master_list(company_id, active_only=True)
    
    # If no competitors found and procurement_type was specified, return all with warning
    if not competitors and procurement_type:
        competitors = db.get_competitor_master_list(company_id, active_only=True)
        for comp in competitors:
            comp['unverified_for_type'] = True
    
    return competitors


def get_competitors_by_procurement_type(company_id: int, procurement_type: str) -> List[Dict[str, Any]]:
    """Get competitors specifically filtered by procurement type."""
    db = get_db_manager()
    return db.get_competitors_by_procurement_type(company_id, procurement_type)


def get_competitor_bids_from_profiles(
    profiles: List[Dict[str, Any]], 
    official_estimate: float, 
    random_factor: float = 0.02
) -> List[float]:
    """
    Generate bid amounts from competitor profiles based on their avg_bid_ratio.
    Adds slight randomness to simulate realistic variation.
    
    Args:
        profiles: List of competitor profile dicts
        official_estimate: The official estimate for the current tender
        random_factor: Random variation factor (±%)
    
    Returns:
        List of generated bid amounts
    """
    if not profiles:
        return []
    
    bids = []
    for comp in profiles:
        ratio = comp.get('avg_bid_ratio', 0.92)
        if ratio == 0 or ratio is None:
            ratio = 0.92
        
        noise = 1 + random.uniform(-random_factor, random_factor)
        bid = official_estimate * ratio * noise
        bids.append(round(bid, 3))
    return bids


def sample_competitors_from_profiles(profiles: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    """
    Randomly sample `count` competitors from the profiles list.
    If count > len(profiles), sample with replacement.
    """
    if not profiles:
        return []
    if count <= len(profiles):
        return random.sample(profiles, count)
    else:
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