# modules/ppr_calculations.py

import numpy as np
from typing import List, Dict, Any, Optional

def calculate_ppr_metrics(
    official_estimate: float, 
    competitor_bids: Optional[List[Dict[str, Any]]] = None, 
    nppi_factor: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate PPR 2025 compliance metrics.
    Reuses the same logic as render_ppr_compliance_viz
    
    Args:
        official_estimate: Government's official estimate for the tender
        competitor_bids: List of competitor bid dictionaries with 'bid' key
        nppi_factor: NPPI factor (default 0.92)
    
    Returns:
        Dictionary with PPR metrics
    """
    
    # Input validation
    if official_estimate <= 0:
        raise ValueError("Official estimate must be greater than 0")
    
    # Extract competitor bid values safely
    comp_bid_values = []
    if competitor_bids and isinstance(competitor_bids, list):
        for cb in competitor_bids:
            if isinstance(cb, dict):
                bid = cb.get('bid', 0)
                if bid and bid > 0:
                    comp_bid_values.append(float(bid))
            elif isinstance(cb, (int, float)):
                if cb > 0:
                    comp_bid_values.append(float(cb))
    
    # Set default NPPI factor
    if nppi_factor is None:
        nppi_factor = 0.92  # Default 28-day average
    
    # Ensure NPPI factor is within reasonable bounds
    nppi_factor = max(0.70, min(1.15, nppi_factor))
    
    nppi_price = official_estimate * nppi_factor
    
    # Calculate weighted average (X̄) - using your formula from the viz
    if comp_bid_values:
        avg_competitor = sum(comp_bid_values) / len(comp_bid_values)
        weighted_average = (0.5 * avg_competitor) + (0.2 * official_estimate) + (0.3 * nppi_price)
        
        # Calculate standard deviation
        if len(comp_bid_values) > 1:
            weighted_std_dev = np.std(comp_bid_values)
        else:
            weighted_std_dev = official_estimate * 0.05  # Default 5% of estimate
    else:
        # No competitor bids - use conservative estimate
        avg_competitor = 0
        weighted_average = official_estimate * 0.85
        weighted_std_dev = official_estimate * 0.10
    
    # SLT Threshold = X̄ - Sd (or 75% of estimate as fallback, whichever is higher)
    slt_threshold = max(weighted_average - weighted_std_dev, official_estimate * 0.75)
    
    # Also calculate the 80% rule for comparison
    slt_eighty_percent = official_estimate * 0.80
    
    # Determine compliance status
    is_compliant = slt_threshold >= slt_eighty_percent
    
    return {
        'nppi_factor': round(nppi_factor, 4),
        'nppi_price': round(nppi_price, 2),
        'avg_competitor': round(avg_competitor, 2) if avg_competitor else 0,
        'weighted_average': round(weighted_average, 2),
        'weighted_std_dev': round(weighted_std_dev, 2),
        'slt_threshold': round(slt_threshold, 2),
        'slt_eighty_percent': round(slt_eighty_percent, 2),
        'is_compliant': is_compliant,
        'competitor_count': len(comp_bid_values),
        'competitor_bids': comp_bid_values
    }


def calculate_bid_accuracy(
    recommended_bid: float, 
    actual_winning_bid: float, 
    official_estimate: float
) -> Dict[str, Any]:
    """
    Calculate bid accuracy score for post-evaluation
    
    Args:
        recommended_bid: The bid amount recommended by the system
        actual_winning_bid: The actual winning bid amount
        official_estimate: Government's official estimate
    
    Returns:
        Dictionary with accuracy metrics
    """
    if actual_winning_bid <= 0:
        return {'accuracy_score': 0, 'difference': 0, 'difference_percent': 0, 'status': 'invalid'}
    
    difference = recommended_bid - actual_winning_bid
    difference_percent = (difference / actual_winning_bid) * 100
    
    # Accuracy score: 1 = perfect, 0 = completely off
    accuracy_score = 1 - (abs(difference) / actual_winning_bid)
    accuracy_score = max(0, min(1, accuracy_score))
    
    # Determine status
    if difference > 0:
        status = "overbid"
    elif difference < 0:
        status = "underbid"
    else:
        status = "perfect"
    
    return {
        'accuracy_score': round(accuracy_score, 4),
        'difference': round(difference, 2),
        'difference_percent': round(difference_percent, 2),
        'status': status,
        'recommended_bid': recommended_bid,
        'actual_winning_bid': actual_winning_bid,
        'official_estimate': official_estimate
    }


def calculate_win_probability(
    our_bid: float,
    competitor_bids: List[float],
    official_estimate: float
) -> Dict[str, Any]:
    """
    Calculate win probability based on bid positioning
    
    Args:
        our_bid: Our bid amount
        competitor_bids: List of competitor bid amounts
        official_estimate: Government's official estimate
    
    Returns:
        Dictionary with win probability metrics
    """
    if not competitor_bids:
        return {
            'win_probability': 0.50,
            'rank': 1,
            'total_competitors': 0,
            'bid_position': 'unknown',
            'message': 'No competitor data available'
        }
    
    # Combine all bids and sort
    all_bids = competitor_bids + [our_bid]
    all_bids.sort()
    
    # Find our rank (1 = lowest bid)
    rank = all_bids.index(our_bid) + 1
    total_bidders = len(all_bids)
    
    # Calculate win probability based on rank
    # Lower rank = higher probability
    base_probability = 1 - ((rank - 1) / total_bidders)
    
    # Adjust based on bid ratio vs official estimate
    bid_ratio = our_bid / official_estimate if official_estimate > 0 else 1
    if bid_ratio > 0.95:
        ratio_penalty = 0.1
    elif bid_ratio > 0.90:
        ratio_penalty = 0.05
    else:
        ratio_penalty = 0
    
    win_probability = max(0.05, min(0.95, base_probability - ratio_penalty))
    
    # Determine bid position
    if rank == 1:
        position = "lowest"
    elif rank <= total_bidders * 0.3:
        position = "competitive"
    elif rank <= total_bidders * 0.6:
        position = "moderate"
    else:
        position = "high"
    
    return {
        'win_probability': round(win_probability, 4),
        'rank': rank,
        'total_competitors': len(competitor_bids),
        'total_bidders': total_bidders,
        'bid_position': position,
        'bid_ratio': round(bid_ratio, 4),
        'message': f"Ranked #{rank} out of {total_bidders} bidders"
    }