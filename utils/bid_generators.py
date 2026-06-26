def debug_print(*args, **kwargs):
    print(*args, **kwargs)


def run_three_tier_analysis(analysis_record, competitor_bids, risk_tolerance):
    """
    Run the three-tier analysis (Basic, Advanced, Enhanced).
    Replace with your actual analysis logic.
    """
    debug_print(f"🔬 Running analysis | Estimate: {analysis_record['official_estimate']}, Competitors: {len(competitor_bids)}")
    
    official_est = analysis_record['official_estimate']
    
    # Risk multipliers
    risk_mult = {'Low': 0.95, 'Medium': 1.0, 'High': 1.05}.get(risk_tolerance, 1.0)
    
    comparison = {}
    
    # Basic Analysis
    comparison['basic'] = {
        'method': 'Statistical Average',
        'optimal_bid': official_est * 0.92 * risk_mult,
        'bid_ratio': 0.92,
        'win_probability': 0.65,
        'confidence_score': 0.70,
        'risk_level': 'Medium',
        'risk_color': '🟡'
    }
    
    # Advanced Analysis (PPR 2025)
    if ADVANCED_OPTIMIZER_AVAILABLE:
        try:
            adv_result = calculate_optimal_bid_ppr2025(official_est, competitor_bids, risk_tolerance)
            comparison['advanced'] = {
                'method': 'PPR 2025 Compliant',
                'optimal_bid': adv_result['optimal_bid'],
                'bid_ratio': adv_result['bid_ratio'],
                'win_probability': adv_result['win_probability'],
                'confidence_score': 0.82,
                'risk_level': 'Low',
                'risk_color': '🟢'
            }
        except Exception as e:
            debug_print(f"⚠️ Advanced analysis failed: {e}")
            comparison['advanced'] = comparison['basic'].copy()
            comparison['advanced']['method'] = 'PPR 2025 (Fallback)'
    else:
        comparison['advanced'] = {
            'method': 'PPR 2025 (Simulated)',
            'optimal_bid': official_est * 0.94 * risk_mult,
            'bid_ratio': 0.94,
            'win_probability': 0.72,
            'confidence_score': 0.82,
            'risk_level': 'Low',
            'risk_color': '🟢'
        }
    
    # Enhanced Analysis (ML)
    comparison['enhanced'] = {
        'method': 'ML Ensemble Model',
        'optimal_bid': official_est * 0.96 * risk_mult,
        'bid_ratio': 0.96,
        'win_probability': 0.78,
        'confidence_score': 0.88,
        'risk_level': 'Low',
        'risk_color': '🟢'
    }
    
    debug_print(f"✓ Analysis complete | Best tier will be calculated in display function")
    return comparison

# =============================================================================
# 🔢 BID PARSING & CALCULATION UTILITIES
# =============================================================================

import re
from typing import List, Optional, Dict, Union


def parse_competitor_bids(input_text: str, official_estimate: Optional[float] = None) -> List[float]:
    """Parse competitor bids with robust validation"""
    if not input_text or not input_text.strip():
        return []
    
    bids = []
    parts = re.split(r'[,;\n|\t]', input_text)  # ✅ re module now imported
    
    for part in parts:
        cleaned = re.sub(r'[^\d\.]', '', part.strip())
        if not cleaned or cleaned == '.':
            continue
        try:
            bid = round(float(cleaned), BID_AMOUNT_DECIMALS)
            if bid <= 0:
                continue
            if official_estimate and official_estimate > 0:
                min_valid = official_estimate * 0.3
                max_valid = official_estimate * 3.0
                if not (min_valid <= bid <= max_valid):
                    debug_print(f"⚠️ Filtered outlier bid: {bid:,.3f}")
                    continue
            bids.append(bid)
        except (ValueError, TypeError) as e:
            debug_print(f"⚠️ Could not parse bid '{part.strip()}': {e}")
            continue
    
    return sorted(bids)



# =============================================================================
# 📐 BID CALCULATION CONSTANTS (Module-level for easy tuning)
# =============================================================================

BID_RATIOS: Dict[str, float] = {
    'aggressive': 0.86,
    'moderate': 0.89, 
    'conservative': 0.93
}

BID_BOUNDS: Dict[str, float] = {
    'min_ratio': 0.80,
    'max_ratio': 0.98,
    'valid_range_factor': 2.0  # Bids must be within [0.5x, 2x] of estimate
}

RISK_THRESHOLDS: Dict[str, float] = {
    'high_max': 0.87,
    'medium_max': 0.92
}

WIN_PROB_VALUES: Dict[str, float] = {
    'high': 0.85,    # When bid <= min competitor
    'medium': 0.60,  # When bid between min and avg
    'low': 0.35      # When bid >= avg competitor
}


def calculate_basic_bid(
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str = 'moderate'
) -> Dict[str, Union[float, str, bool]]:
    """
    Calculate basic bid recommendation using statistical heuristics.
    
    Args:
        official_estimate: Government/procuring entity's official estimate
        competitor_bids: List of known competitor bid amounts
        risk_tolerance: User's risk preference ('aggressive', 'moderate', 'conservative')
        
    Returns:
        Dict with bid recommendation (3 decimals), win probability, risk assessment
    """
    debug_print(f"🔢 Calculating basic bid | Estimate: {official_estimate:,.3f}, Risk: {risk_tolerance}")
    if official_estimate <= 0:
        debug_print("❌ Invalid official_estimate <= 0")
        return {
            'optimal_bid': 0.0,
            'bid_ratio': 0.0,
            'win_probability': 0.0,
            'risk_level': 'UNKNOWN',
            'risk_color': '⚪',
            'avg_competitor': 0.0,
            'min_competitor': 0.0,
            'is_premium': False,
            'method': 'Error: Invalid estimate'
        }
    # Filter valid competitor bids
    min_valid = official_estimate / BID_BOUNDS['valid_range_factor']
    max_valid = official_estimate * BID_BOUNDS['valid_range_factor']
    valid_bids = [b for b in competitor_bids if min_valid <= b <= max_valid]
    
    # Compute competitor statistics
    if valid_bids:
        avg_competitor = float(np.mean(valid_bids))
        min_competitor = float(np.min(valid_bids))
        debug_print(f"✓ Valid competitors: {len(valid_bids)}, Avg: {avg_competitor:,.3f}, Min: {min_competitor:,.3f}")
    else:
        # Fallback estimates when no valid competitor data
        avg_competitor = round(official_estimate * 0.92, 3)
        min_competitor = round(official_estimate * 0.85, 3)
        debug_print("⚠️ No valid competitor bids; using fallback estimates")
    
    # Calculate recommended bid with 3 decimal precision
    ratio = BID_RATIOS.get(risk_tolerance.lower(), BID_RATIOS['moderate'])
    recommended_bid = round(official_estimate * ratio, 3)
    
    # Adjust if bid is uncompetitive vs market
    if recommended_bid > avg_competitor:
        recommended_bid = round(avg_competitor * 0.99, 3)
        debug_print(f"📉 Adjusted bid to be competitive: {recommended_bid:,.3f}")
    
    # Enforce hard bounds (with 3 decimal precision)
    min_bound = round(official_estimate * BID_BOUNDS['min_ratio'], 3)
    max_bound = round(official_estimate * BID_BOUNDS['max_ratio'], 3)
    recommended_bid = round(max(min_bound, min(max_bound, recommended_bid)), 3)
    
    # Calculate win probability based on positioning
    if recommended_bid <= min_competitor:
        win_prob = WIN_PROB_VALUES['high']
    elif recommended_bid >= avg_competitor:
        win_prob = WIN_PROB_VALUES['low']
    else:
        win_prob = WIN_PROB_VALUES['medium']
    
    # Determine risk level based on bid ratio
    if ratio < RISK_THRESHOLDS['high_max']:
        risk_level, risk_color = "HIGH", "🔴"
    elif ratio < RISK_THRESHOLDS['medium_max']:
        risk_level, risk_color = "MEDIUM", "🟡"
    else:
        risk_level, risk_color = "LOW", "🟢"
    
    result = {
        'optimal_bid': recommended_bid,
        # ✅ Safe division with guard
        'bid_ratio': round(recommended_bid / official_estimate, BID_RATIO_DECIMALS) if official_estimate > 0 else 0.0,
        'win_probability': win_prob,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'avg_competitor': avg_competitor,
        'min_competitor': min_competitor,
        'is_premium': False,
        'method': 'Basic Statistical Heuristic'
    }
    
    debug_print(f"✓ Basic bid result: BDT {result['optimal_bid']:,.3f} | Win: {win_prob*100:.1f}% | Risk: {risk_level}")
    return result


def _generate_competitor_bids_basic(official_estimate: float, num_competitors: int = 3) -> list:
    """
    Generate realistic competitor bids based on official estimate.
    Bids are distributed around the estimate with natural variation.
    """
    import random
    competitor_bids = []
    
    # Generate bids: typically 85%-115% of estimate, with clustering
    for i in range(num_competitors):
        # Add some randomness: most bids cluster near estimate, some are aggressive/conservative
        if i == 0:
            # Aggressive bidder: 85-95% of estimate
            ratio = random.uniform(0.85, 0.95)
            name = "Aggressive Competitor Co."
        elif i == 1:
            # Conservative bidder: 100-115% of estimate
            ratio = random.uniform(1.00, 1.15)
            name = "Premium Solutions Ltd."
        else:
            # Moderate bidder: 92-108% of estimate
            ratio = random.uniform(0.92, 1.08)
            name = f"Regional Contractor {i}"
        
        bid_amount = official_estimate * ratio
        competitor_bids.append({
            'name': name,
            'bid': round(bid_amount, 2)
        })
    
    return competitor_bids
def _generate_competitor_bids(official_estimate: float, num_competitors: int = 3, risk_preference: str = 'moderate') -> list:
    """
    Generate realistic competitor bids based on official estimate and risk preference.
    """
    import random
    competitor_bids = []
    
    # Risk-based bid ratio ranges
    risk_ranges = {
        'aggressive': (0.82, 0.94),    # Lower bids, higher risk
        'moderate': (0.88, 1.02),      # Balanced around estimate
        'conservative': (0.94, 1.08)   # Higher bids, safer win
    }
    min_ratio, max_ratio = risk_ranges.get(risk_preference, (0.88, 1.02))
    
    for i in range(num_competitors):
        # Add variation: cluster bids with some outliers
        if i < num_competitors - 1:
            # Most bids cluster in middle of range
            ratio = random.uniform(min_ratio + 0.03, max_ratio - 0.03)
        else:
            # Last bid is an outlier (aggressive or conservative)
            ratio = random.choice([random.uniform(min_ratio, min_ratio + 0.03), 
                                  random.uniform(max_ratio - 0.03, max_ratio)])
        
        bid_amount = official_estimate * ratio
        competitor_bids.append({
            'name': f"Competitor {i+1}",
            'bid': round(bid_amount, 3)
        })
    
    return competitor_bids    

__all__ = ['_generate_competitor_bids', '_generate_competitor_bids_basic', 'debug_print']


