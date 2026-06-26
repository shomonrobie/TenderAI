"""
Advanced Win Probability Engine for PPR 2025 Compliant Bidding
Updated to use winner-based NPPI and improved historical data
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from collections import Counter
import warnings
warnings.filterwarnings('ignore')
from modules.historical_data import get_weighted_nppi


class AdvancedWinProbabilityEngine:
    """
    Multi-factor win probability calculator
    Updated with winner-based NPPI and competitor behavior analysis
    """
    
    def __init__(self):
        self.historical_patterns = {}
        self.competitor_models = {}
    
    def calculate_win_probability(self, bid_price, official_estimate, competitor_bids, 
                                  historical_data=None, market_factors=None, 
                                  competitor_profiles=None, company_id=None):
        """
        Calculate comprehensive win probability using multiple factors
        Updated to use winner-based historical data
        """
        
        factors = {}
        weights = {
            'price_position': 0.30,
            'competitor_intelligence': 0.25,
            'historical_pattern': 0.20,
            'market_conditions': 0.15,
            'nppi_alignment': 0.10
        }
        
        # Factor 1: Price Position Analysis
        factors['price_position'] = self._price_position_score(
            bid_price, official_estimate, competitor_bids
        )
        
        # Factor 2: Competitor Intelligence
        factors['competitor_intelligence'] = self._competitor_intelligence_score(
            bid_price, competitor_bids, competitor_profiles
        )
        
        # Factor 3: Historical Pattern Matching (updated)
        factors['historical_pattern'] = self._historical_pattern_score(
            bid_price, official_estimate, historical_data, company_id
        )
        
        # Factor 4: Market Conditions
        factors['market_conditions'] = self._market_conditions_score(
            bid_price, official_estimate, market_factors
        )
        
        # Factor 5: NPPI Alignment (new factor)
        factors['nppi_alignment'] = self._nppi_alignment_score(
            bid_price, official_estimate, historical_data, company_id
        )
        
        # Calculate weighted probability
        win_probability = sum(factors[f] * weights[f] for f in weights)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(factors, len(competitor_bids), historical_data)
        
        return {
            'win_probability': min(0.95, max(0.05, win_probability)),
            'confidence_score': confidence_score,
            'contributing_factors': factors,
            'weights_used': weights
        }
    
    def _price_position_score(self, bid_price, official_estimate, competitor_bids):
        """
        Score based on bid position relative to competitors and winning patterns
        """
        if not competitor_bids or len(competitor_bids) < 2:
            # Insufficient data - use estimate-based scoring
            ratio = bid_price / official_estimate
            if ratio < 0.88:
                return 0.85  # Very competitive
            elif ratio < 0.92:
                return 0.70
            elif ratio < 0.95:
                return 0.50
            else:
                return 0.30
        
        # Calculate percentile position among competitors
        all_bids = competitor_bids + [bid_price]
        sorted_bids = sorted(all_bids)
        position = sorted_bids.index(bid_price)
        percentile = position / len(sorted_bids) if len(sorted_bids) > 0 else 0.5
        
        # Lower bid = higher percentile = better chance
        if percentile <= 0.2:  # Among lowest 20%
            score = 0.90
        elif percentile <= 0.4:
            score = 0.75
        elif percentile <= 0.6:
            score = 0.55
        elif percentile <= 0.8:
            score = 0.35
        else:
            score = 0.20
        
        # Adjust based on spread
        spread = (max(competitor_bids) - min(competitor_bids)) / official_estimate
        if spread > 0.15:  # Wide spread - more opportunity
            score = min(0.95, score * 1.1)
        elif spread < 0.05:  # Tight spread - very competitive
            score = score * 0.9
        
        return score
    
    def _competitor_intelligence_score(self, bid_price, competitor_bids, competitor_profiles):
        """
        Score based on competitor behavior patterns and historical performance
        """
        if not competitor_bids or len(competitor_bids) < 3:
            return 0.50
        
        # Identify competitor clusters
        mean_bid = np.mean(competitor_bids)
        std_bid = np.std(competitor_bids)
        
        # Count aggressive vs conservative bidders
        aggressive_count = len([b for b in competitor_bids if b < mean_bid * 0.95])
        conservative_count = len([b for b in competitor_bids if b > mean_bid * 1.05])
        
        # Determine if market favors lower bids
        if aggressive_count > conservative_count:
            target_percentile = 0.15
        elif conservative_count > aggressive_count:
            target_percentile = 0.35
        else:
            target_percentile = 0.25
        
        # Calculate current percentile
        all_bids = competitor_bids + [bid_price]
        sorted_bids = sorted(all_bids)
        current_percentile = sorted_bids.index(bid_price) / len(sorted_bids) if len(sorted_bids) > 0 else 0.5
        
        # Score based on how close to target percentile
        percentile_diff = abs(current_percentile - target_percentile)
        score = max(0.1, 1.0 - percentile_diff)
        
        # Bonus for beating aggressive bidders
        if bid_price < min(competitor_bids):
            score = min(0.95, score * 1.15)
        
        return score
    
    def _historical_pattern_score(self, bid_price, official_estimate, historical_data, company_id=None):
        """
        Score based on historical winning patterns - updated to use winner-based data
        """
        if not historical_data or len(historical_data) < 5:
            return 0.50
        
        # Separate data by winner type
        our_wins = []
        competitor_wins = []
        
        for record in historical_data:
            if record.get('winning_company_type') == 'Our Company':
                if 'winning_bid' in record and 'official_estimate' in record:
                    ratio = record['winning_bid'] / record['official_estimate']
                    our_wins.append(ratio)
            elif record.get('winning_company_type') == 'Competitor':
                if 'winning_bid' in record and 'official_estimate' in record:
                    ratio = record['winning_bid'] / record['official_estimate']
                    competitor_wins.append(ratio)
        
        # Use our wins if available (most relevant)
        if our_wins and len(our_wins) >= 3:
            winning_ratios = our_wins
            source = "our_wins"
        elif competitor_wins and len(competitor_wins) >= 3:
            winning_ratios = competitor_wins
            source = "competitor_wins"
        else:
            # Fallback to all data
            winning_ratios = []
            for record in historical_data:
                if 'winning_bid' in record and 'official_estimate' in record:
                    ratio = record['winning_bid'] / record['official_estimate']
                    winning_ratios.append(ratio)
            source = "all_data"
        
        if not winning_ratios:
            return 0.50
        
        # Calculate typical winning ratio range
        mean_ratio = np.mean(winning_ratios)
        std_ratio = np.std(winning_ratios)
        
        current_ratio = bid_price / official_estimate
        
        # Calculate how close to typical winning ratio
        if std_ratio > 0:
            z_score = abs(current_ratio - mean_ratio) / std_ratio
            score = max(0.1, 1.0 - (z_score / 3))
        else:
            score = 0.60 if abs(current_ratio - mean_ratio) < 0.03 else 0.40
        
        # Adjust based on data source confidence
        if source == "our_wins":
            score = min(0.95, score * 1.1)  # Our wins are most reliable
        elif source == "competitor_wins":
            score = score * 0.95  # Competitor wins slightly less reliable
        
        # Trend analysis
        recent_ratios = winning_ratios[-3:] if len(winning_ratios) >= 3 else winning_ratios
        trend = np.mean(recent_ratios) - np.mean(winning_ratios)
        
        if trend < 0:  # Winning bids trending downward (more aggressive)
            score = min(0.90, score * 1.05)
        
        return score
    
    def _market_conditions_score(self, bid_price, official_estimate, market_factors):
        """
        Score based on current market conditions
        """
        if not market_factors:
            return 0.50
        
        score = 0.60  # Base score
        
        # Seasonality adjustment
        seasonality = market_factors.get('seasonality', 1.0)
        if seasonality < 0.97:  # Monsoon/hard season
            score *= 0.95  # Lower chance
        elif seasonality > 1.02:  # Peak season
            score *= 1.05
        
        # Competition level
        competition_level = market_factors.get('competition_level', 'medium')
        competition_scores = {'low': 1.08, 'medium': 1.00, 'high': 0.92, 'very_high': 0.85}
        score *= competition_scores.get(competition_level, 1.00)
        
        # Economic factors
        economic_factor = market_factors.get('economic_factor', 1.0)
        if economic_factor > 1.05:  # High inflation/materials cost
            score *= 0.95
        
        return min(0.95, max(0.10, score))
    
    def _nppi_alignment_score(self, bid_price, official_estimate, historical_data, company_id=None):
        """
        Score based on alignment with market NPPI (PPR 2025 compliant)
        """
        try:
            if company_id:
                nppi_factor, nppi_source = get_weighted_nppi(company_id, 'goods')
            else:
                nppi_factor = 0.92
        except:
            nppi_factor = 0.92
        
        # Calculate expected market price based on NPPI
        expected_market_price = official_estimate * nppi_factor
        
        # Calculate how close our bid is to market expectation
        ratio_diff = abs(bid_price - expected_market_price) / expected_market_price
        
        if ratio_diff < 0.02:  # Within 2% of market expectation
            score = 0.90
        elif ratio_diff < 0.05:  # Within 5%
            score = 0.75
        elif ratio_diff < 0.10:  # Within 10%
            score = 0.55
        else:
            score = 0.30
        
        # Adjust based on whether we're below market (more competitive)
        if bid_price < expected_market_price:
            score = min(0.95, score * 1.1)
        
        return score

    
    def _calculate_confidence(self, factors, num_competitors, historical_data):
        """
        Calculate confidence score for the prediction
        Updated to consider winner data quality
        """
        confidence = 0.70  # Base confidence
        
        # More competitors = more data = higher confidence
        if num_competitors >= 10:
            confidence += 0.10
        elif num_competitors >= 5:
            confidence += 0.05
        elif num_competitors < 3:
            confidence -= 0.10
        
        # Historical data improves confidence - check for winner data
        if historical_data:
            our_wins_count = sum(1 for r in historical_data if r.get('winning_company_type') == 'Our Company')
            comp_wins_count = sum(1 for r in historical_data if r.get('winning_company_type') == 'Competitor')
            
            if our_wins_count >= 5:
                confidence += 0.10
            elif comp_wins_count >= 10:
                confidence += 0.05
            elif len(historical_data) >= 20:
                confidence += 0.05
            elif len(historical_data) < 5:
                confidence -= 0.10
        else:
            confidence -= 0.10
        
        # Factor consistency
        factor_values = list(factors.values())
        if np.std(factor_values) < 0.15:  # Factors agree
            confidence += 0.05
        elif np.std(factor_values) > 0.30:  # Factors disagree
            confidence -= 0.05
        
        return min(0.95, max(0.50, confidence))


class CompetitorBehaviorAnalyzer:
    """
    Analyzes competitor bidding patterns to predict their behavior
    Updated to track winner information
    """
    
    def __init__(self):
        self.competitor_history = {}
    
    def analyze_competitors(self, competitor_bids, historical_competitor_data=None):
        """
        Analyze competitor behavior patterns
        """
        if not competitor_bids:
            return None
        
        analysis = {
            'count': len(competitor_bids),
            'mean': np.mean(competitor_bids),
            'std': np.std(competitor_bids),
            'min': np.min(competitor_bids),
            'max': np.max(competitor_bids),
            'clusters': [],
            'aggressiveness_score': 0.5
        }
        
        # Identify clusters
        if len(competitor_bids) >= 3:
            mean = analysis['mean']
            analysis['aggressive_count'] = len([b for b in competitor_bids if b < mean * 0.95])
            analysis['moderate_count'] = len([b for b in competitor_bids if mean * 0.95 <= b <= mean * 1.05])
            analysis['conservative_count'] = len([b for b in competitor_bids if b > mean * 1.05])
            
            # Calculate aggressiveness score (0-1)
            total = len(competitor_bids)
            analysis['aggressiveness_score'] = (analysis['aggressive_count'] * 1.0 + 
                                                 analysis['moderate_count'] * 0.5) / total
        
        # Predict expected lowest bid
        analysis['predicted_lowest'] = analysis['min'] * 0.98 if analysis['aggressiveness_score'] > 0.6 else analysis['min'] * 0.99
        
        return analysis


class MarketTrendAnalyzer:
    """
    Analyzes market trends for better bid positioning
    Updated to track winner-based trends
    """
    
    def __init__(self):
        self.market_history = []
    
    def analyze_market(self, historical_tenders):
        """
        Analyze market trends from historical tender data
        Now includes winner-based analysis
        """
        if not historical_tenders or len(historical_tenders) < 5:
            return None
        
        analysis = {
            'trend': 'stable',
            'winning_ratio_trend': 0,
            'competition_trend': 0,
            'seasonal_patterns': {},
            'winner_trends': {
                'our_wins_trend': 0,
                'competitor_wins_trend': 0
            }
        }
        
        # Analyze winning ratios over time
        df = pd.DataFrame(historical_tenders)
        
        if 'winning_bid' in df.columns and 'official_estimate' in df.columns:
            df['ratio'] = df['winning_bid'] / df['official_estimate']
            
            if len(df) >= 5:
                # Calculate trend
                recent_avg = df['ratio'].tail(3).mean()
                overall_avg = df['ratio'].mean()
                analysis['winning_ratio_trend'] = (recent_avg - overall_avg) / overall_avg
                
                if analysis['winning_ratio_trend'] < -0.05:
                    analysis['trend'] = 'falling'  # Market getting cheaper
                elif analysis['winning_ratio_trend'] > 0.05:
                    analysis['trend'] = 'rising'   # Market getting more expensive
                else:
                    analysis['trend'] = 'stable'
        
        # Winner trend analysis
        if 'winning_company_type' in df.columns:
            df_sorted = df.sort_values('award_date') if 'award_date' in df.columns else df
            
            # Our wins trend
            our_wins_rolling = df_sorted['winning_company_type'].eq('Our Company').rolling(5).mean()
            if len(our_wins_rolling) >= 5:
                recent_our_wins = our_wins_rolling.tail(3).mean()
                overall_our_wins = our_wins_rolling.mean()
                analysis['winner_trends']['our_wins_trend'] = (recent_our_wins - overall_our_wins) / overall_our_wins if overall_our_wins > 0 else 0
            
            # Competitor wins trend
            comp_wins_rolling = df_sorted['winning_company_type'].eq('Competitor').rolling(5).mean()
            if len(comp_wins_rolling) >= 5:
                recent_comp_wins = comp_wins_rolling.tail(3).mean()
                overall_comp_wins = comp_wins_rolling.mean()
                analysis['winner_trends']['competitor_wins_trend'] = (recent_comp_wins - overall_comp_wins) / overall_comp_wins if overall_comp_wins > 0 else 0
        
        return analysis


# ==================== ENHANCED BID OPTIMIZER ====================

def enhance_win_probability(bid_price, official_estimate, competitor_bids, 
                            historical_data=None, market_factors=None, company_id=None):
    """
    Enhanced win probability calculation using multiple factors
    Updated to include NPPI alignment and winner-based historical data
    """
    engine = AdvancedWinProbabilityEngine()
    
    result = engine.calculate_win_probability(
        bid_price=bid_price,
        official_estimate=official_estimate,
        competitor_bids=competitor_bids,
        historical_data=historical_data,
        market_factors=market_factors,
        company_id=company_id
    )
    
    return result


def calculate_optimal_bid_with_ml(official_estimate, competitor_bids, historical_data=None,
                                   risk_tolerance='moderate', market_factors=None, company_id=None):
    """
    Complete enhanced bid optimization with ML-based win probability
    Updated with improved NPPI and winner-based analysis
    """
    
    # Basic competitor analysis
    if not competitor_bids or len(competitor_bids) < 2:
        # Insufficient data - use estimate-based approach with NPPI
        try:
            from modules.historical_data import get_weighted_nppi
            nppi_factor, _ = get_weighted_nppi(company_id, 'goods') if company_id else (0.92, "Default")
            base_ratio = nppi_factor * 0.98
        except:
            base_ratio = 0.89
            
        ratios = {'aggressive': base_ratio * 0.97, 'moderate': base_ratio, 'conservative': base_ratio * 1.03}
        base_ratio = ratios.get(risk_tolerance, base_ratio)
        candidate_bid = official_estimate * base_ratio
    else:
        # Use competitor average as base
        mean_bid = np.mean(competitor_bids)
        ratios = {'aggressive': 0.98, 'moderate': 0.99, 'conservative': 1.00}
        base_ratio = ratios.get(risk_tolerance, 0.99)
        candidate_bid = mean_bid * base_ratio
    
    # Try multiple bid points to find optimal
    best_bid = candidate_bid
    best_win_prob = 0
    best_expected_value = 0
    
    # Test bids in a range
    test_ratios = [0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95]
    
    for ratio in test_ratios:
        test_bid = official_estimate * ratio
        
        # Skip unrealistic bids
        if competitor_bids and test_bid > max(competitor_bids) * 1.05:
            continue
        if test_bid < official_estimate * 0.80:
            continue
        
        # Calculate win probability with enhanced engine
        wp_result = enhance_win_probability(
            test_bid, official_estimate, competitor_bids, historical_data, market_factors, company_id
        )
        
        win_prob = wp_result['win_probability']
        
        # Calculate expected value (profit * win probability)
        estimated_cost = official_estimate * 0.85
        profit = test_bid - estimated_cost
        expected_value = profit * win_prob
        
        if expected_value > best_expected_value:
            best_expected_value = expected_value
            best_bid = test_bid
            best_win_prob = win_prob
    
    return {
        'optimal_bid': best_bid,
        'bid_ratio': best_bid / official_estimate,
        'win_probability': best_win_prob,
        'expected_value': best_expected_value,
        'estimated_profit': best_bid - (official_estimate * 0.85)
    }


# ==================== TESTING ====================

if __name__ == "__main__":
    # Sample data
    official_estimate = 7_500_000
    competitor_bids = [6_800_000, 7_100_000, 6_900_000, 7_200_000, 6_750_000]
    
    # Sample historical data with winner info
    historical_data = [
        {'winning_bid': 4_600_000, 'official_estimate': 5_000_000, 'winning_company_type': 'Our Company'},
        {'winning_bid': 9_200_000, 'official_estimate': 10_000_000, 'winning_company_type': 'Competitor'},
        {'winning_bid': 2_850_000, 'official_estimate': 3_000_000, 'winning_company_type': 'Our Company'},
        {'winning_bid': 7_800_000, 'official_estimate': 8_500_000, 'winning_company_type': 'Competitor'},
        {'winning_bid': 5_500_000, 'official_estimate': 6_000_000, 'winning_company_type': 'Our Company'},
    ]
    
    # Market factors
    market_factors = {
        'seasonality': 0.98,
        'competition_level': 'high',
        'economic_factor': 1.02
    }
    
    result = calculate_optimal_bid_with_ml(
        official_estimate, competitor_bids, historical_data, 'moderate', market_factors, company_id=1
    )
    
    print("Enhanced ML Bid Optimization Results:")
    print(f"Optimal Bid: BDT {result['optimal_bid']:,.0f}")
    print(f"Win Probability: {result['win_probability']*100:.1f}%")
    print(f"Expected Profit: BDT {result['estimated_profit']:,.0f}")
    print(f"Expected Value: BDT {result['expected_value']:,.0f}")