# bid_core.py

import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import math
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# HARDCODED DEFAULTS (Lowest priority)
# =============================================================================

HARDCODED_DEFAULTS = {
    # NPPI
    'default_nppi_goods': 0.920,
    'default_nppi_works': 0.890,
    'default_nppi_services': 0.910,
    # Competitor fallback
    'fallback_mean_competitor_ratio': 0.95,
    'fallback_std_competitor_ratio': 0.05,
    # Risk multipliers
    'risk_multipliers': {'aggressive': 0.97, 'moderate': 1.00, 'conservative': 1.03},
    'risk_adjustments': {'aggressive': -0.03, 'moderate': 0.00, 'conservative': 0.02},
    'risk_thresholds': [0.85, 0.89, 0.93, 0.96],
    'risk_labels': ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'MEDIUM-LOW', 'LOW'],
    'risk_colors': ['🔴', '🟠', '🟡', '🟢', '🔵'],
    # Win probability clamp
    'win_probability_clamp_min': 0.05,
    'win_probability_clamp_max': 0.95,
    # Confidence
    'confidence_base': 0.70,
    'confidence_bonus_competitor_count': 0.10,
    'confidence_bonus_historical_our_wins': 0.10,
    'confidence_bonus_factor_consistency': 0.05,
    'confidence_penalty_sparse_data': -0.10,
    # SLT weights
    'slt_weight_mean_competitor': 0.50,
    'slt_weight_official_estimate': 0.20,
    'slt_weight_nppi_price': 0.30,
    'slt_threshold_multiplier': 1.01,
    'bid_upper_clamp_factor': 0.98,
    'base_bid_ratio_no_competitors': 0.89,
    'base_bid_ratio_with_competitors': 0.98,
    # Base percentages
    'base_percentage_goods': 0.94,
    'base_percentage_works': 0.92,
    'base_percentage_services': 0.95,
    # Competitor generation patterns
    'beta_alpha_realistic': 4.0,
    'beta_beta_realistic': 3.0,
    'triangular_low_aggressive': 0.88,
    'triangular_peak_aggressive': 0.90,
    'triangular_high_aggressive': 0.96,
    'normal_mean_conservative': 0.98,
    'normal_std_conservative': 0.025,
    # Cost fallback
    'fallback_estimated_cost_factor': 0.85,
    'default_cost_profile': 'competitive',
    # Bid range defaults
    'default_min_price_pct': 0.88,
    'default_max_price_pct': 1.08,
    'default_competitor_min': 5,
    'default_competitor_max': 19,
    'default_nppi_min': 0.920,
    'default_nppi_max': 0.942,
    'default_scenario_count': 9,
    # Win probability thresholds
    'win_probability_thresholds': [0.89, 0.92, 0.95],
    'win_probability_values': [0.85, 0.70, 0.55, 0.40],
    # Feature flags
    'enable_basic_bid': True,
    'enable_advanced_bid': True,
    'enable_competitive_intel': True,
    'enable_ai_advisor': True,
}


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    """
    Manages configuration with fallback hierarchy:
    1. Company-specific override (if set)
    2. System-wide override (if set)
    3. Hardcoded default
    """
    
    def __init__(self, db=None):
        self.db = db
        self._cache = {}
        self._company_cache = {}
    
    def _get_system_config(self, key: str) -> Optional[Any]:
        """Get system-wide config from database."""
        if not self.db:
            return None
        
        try:
            if key in self._cache:
                return self._cache[key]
            
            value = self.db.get_config(key)
            if value is not None:
                try:
                    parsed = json.loads(value)
                    self._cache[key] = parsed
                    return parsed
                except (json.JSONDecodeError, TypeError):
                    self._cache[key] = value
                    return value
            return None
        except Exception as e:
            logger.warning(f"Error getting system config for {key}: {e}")
            return None
    
    def _get_company_config(self, company_id: int, key: str) -> Optional[Any]:
        """Get company-specific config from database."""
        if not self.db or not company_id:
            return None
        
        try:
            cache_key = f"{company_id}:{key}"
            if cache_key in self._company_cache:
                return self._company_cache[cache_key]
            
            value = self.db.get_company_config(company_id, key)
            if value is not None:
                self._company_cache[cache_key] = value
                return value
            return None
        except Exception as e:
            logger.warning(f"Error getting company config for {company_id}:{key}: {e}")
            return None
    
    def get(self, key: str, company_id: Optional[int] = None, 
            default: Optional[Any] = None) -> Any:
        """Get configuration value with fallback hierarchy."""
        if company_id:
            value = self._get_company_config(company_id, key)
            if value is not None:
                return value
        
        value = self._get_system_config(key)
        if value is not None:
            return value
        
        if default is not None:
            return default
        return HARDCODED_DEFAULTS.get(key, None)
    
    def get_nested(self, key: str, subkey: str, company_id: Optional[int] = None,
                   default: Optional[Any] = None) -> Any:
        """Get a nested value from a dictionary config."""
        value = self.get(key, company_id)
        if isinstance(value, dict):
            return value.get(subkey, default)
        return default
    
    def set_company_config(self, company_id: int, key: str, value: Any,
                           description: str = None, user_id: int = None) -> bool:
        """Set company-specific config."""
        if self.db:
            return self.db.set_company_config(company_id, key, value, 
                                              description=description, 
                                              user_id=user_id)
        return False
    
    def get_nppi_range(self, procurement_type: str, company_id: Optional[int] = None) -> Tuple[float, float]:
        """Get NPPI min and max for a procurement type."""
        min_key = f"nppi_range_{procurement_type}_min"
        max_key = f"nppi_range_{procurement_type}_max"
        min_val = self.get(min_key, company_id)
        max_val = self.get(max_key, company_id)
        
        if min_val is not None and max_val is not None:
            return float(min_val), float(max_val)
        
        defaults = {
            'goods': (0.920, 0.942),
            'works': (0.890, 0.920),
            'services': (0.910, 0.940)
        }
        return defaults.get(procurement_type, (0.920, 0.942))


# =============================================================================
# GLOBAL CONFIG MANAGER INSTANCE
# =============================================================================

_config_manager = None

def get_config_manager(db=None):
    global _config_manager
    if _config_manager is None or (_config_manager.db is None and db is not None):
        _config_manager = ConfigManager(db)
    return _config_manager


def get_config(key: str, default: Any = None, company_id: Optional[int] = None) -> Any:
    """Legacy function for backward compatibility."""
    manager = get_config_manager()
    return manager.get(key, company_id, default)


def get_nested_config(key: str, subkey: str, default: Any = None,
                      company_id: Optional[int] = None) -> Any:
    """Get nested config value."""
    manager = get_config_manager()
    return manager.get_nested(key, subkey, company_id, default)


def get_nppi_range(procurement_type: str, company_id: Optional[int] = None) -> Tuple[float, float]:
    """Get NPPI range for a procurement type."""
    manager = get_config_manager()
    return manager.get_nppi_range(procurement_type, company_id)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_bid_values(competitor_bids):
    """Safely extract numeric bid values from list of dicts or numbers."""
    if not competitor_bids:
        return []
    if isinstance(competitor_bids[0], dict):
        return [float(b.get('bid', 0)) for b in competitor_bids if isinstance(b, dict) and 'bid' in b]
    return [float(b) for b in competitor_bids if isinstance(b, (int, float))]


# =============================================================================
# COST ENGINE
# =============================================================================

class CostEngine:
    """Computes total cost from BOQ items using a cost profile."""
    
    def __init__(self, boq_items=None, official_estimate=None, cost_profile='competitive'):
        self.boq_items = boq_items or []
        self.official_estimate = official_estimate
        self.cost_profile = cost_profile
        self._cost = None

    def compute(self):
        if self.boq_items:
            total = 0.0
            for item in self.boq_items:
                qty = float(item.get('quantity', 0))
                rate_key = f"{self.cost_profile}_rate"
                rate = float(item.get(rate_key, 0))
                total += qty * rate
            self._cost = total
        else:
            factor = get_config('fallback_estimated_cost_factor', 0.85)
            if self.official_estimate is None:
                raise ValueError("Either BOQ or official estimate must be provided.")
            self._cost = self.official_estimate * factor
        return self._cost

    def get_cost(self):
        if self._cost is None:
            self.compute()
        return self._cost


# =============================================================================
# NPPI ENGINE
# =============================================================================

class NPPIEngine:
    """Returns NPPI factor. Supports single value or range."""
    
    def __init__(self, company_id=None, procurement_type='works',
                 historical_data=None, nppi_override=None):
        self.company_id = company_id
        self.procurement_type = procurement_type
        self.historical_data = historical_data or []
        self.nppi_override = nppi_override
        self._factor = None

    def compute(self):
        if self.nppi_override is not None:
            self._factor = self.nppi_override
            return self._factor

        if self.company_id:
            try:
                from modules.historical_data import get_weighted_nppi
                nppi, _ = get_weighted_nppi(self.company_id, self.procurement_type)
                if nppi:
                    self._factor = nppi
                    return self._factor
            except:
                pass

        if self.historical_data and len(self.historical_data) >= 3:
            deviations = []
            for record in self.historical_data:
                if 'awarded_price' in record and 'official_estimate' in record:
                    if record['official_estimate'] > 0:
                        dev = (record['awarded_price'] - record['official_estimate']) / record['official_estimate']
                        deviations.append(dev)
            if deviations:
                self._factor = round(1 + np.mean(deviations), 4)
                return self._factor

        default_key = f"default_nppi_{self.procurement_type}"
        self._factor = get_config(default_key, 0.92, self.company_id)
        return self._factor

    def get_factor(self):
        if self._factor is None:
            self.compute()
        return self._factor


# =============================================================================
# SLT ENGINE
# =============================================================================

class SLTEngine:
    """Computes Weighted Average, Weighted Std Dev, and SLT threshold."""
    
    def __init__(self, official_estimate, competitor_bids,
                 nppi_factor, procurement_type='works'):
        self.official_estimate = float(official_estimate)
        self.competitor_bids = extract_bid_values(competitor_bids)
        self.nppi_factor = float(nppi_factor)
        self.procurement_type = procurement_type
        self._wa = None
        self._wsd = None
        self._slt = None

    def compute(self):
        nppi_price = self.official_estimate * self.nppi_factor
        if self.competitor_bids:
            mean_comp = np.mean(self.competitor_bids)
        else:
            mean_comp = self.official_estimate * get_config('fallback_mean_competitor_ratio', 0.95)

        w1 = get_config('slt_weight_mean_competitor', 0.50)
        w2 = get_config('slt_weight_official_estimate', 0.20)
        w3 = get_config('slt_weight_nppi_price', 0.30)
        
        wa = w1 * mean_comp + w2 * self.official_estimate + w3 * nppi_price

        if self.competitor_bids and len(self.competitor_bids) > 1:
            squared_deviations = [(wa - bid) ** 2 for bid in self.competitor_bids]
            wsd = np.sqrt(np.mean(squared_deviations))
        else:
            wsd = self.official_estimate * 0.03

        slt = wa - wsd

        self._wa = wa
        self._wsd = wsd
        self._slt = slt
        return wa, wsd, slt

    def get_wa(self):
        if self._wa is None:
            self.compute()
        return self._wa

    def get_wsd(self):
        if self._wsd is None:
            self.compute()
        return self._wsd

    def get_slt(self):
        if self._slt is None:
            self.compute()
        return self._slt


# =============================================================================
# COMPETITOR ENGINE
# =============================================================================

class CompetitorEngine:
    """Generates synthetic competitor bids and processes user data."""
    
    @staticmethod
    def generate(competitor_count, official_estimate,
                 min_price_pct=0.88, max_price_pct=1.08,
                 pattern='realistic', random_seed=42):
        np.random.seed(random_seed)
        min_bid = official_estimate * min_price_pct
        max_bid = official_estimate * max_price_pct

        if pattern == 'uniform':
            bids = np.random.uniform(min_bid, max_bid, competitor_count)
        elif pattern == 'realistic':
            alpha = get_config('beta_alpha_realistic', 4.0)
            beta = get_config('beta_beta_realistic', 3.0)
            ratios = np.random.beta(alpha, beta, competitor_count)
            scaled_ratios = min_price_pct + ratios * (max_price_pct - min_price_pct)
            bids = official_estimate * scaled_ratios
        elif pattern == 'aggressive':
            low = get_config('triangular_low_aggressive', 0.88)
            peak = get_config('triangular_peak_aggressive', 0.90)
            high = get_config('triangular_high_aggressive', 0.96)
            ratios = np.random.triangular(low, peak, high, competitor_count)
            bids = official_estimate * ratios
        elif pattern == 'conservative':
            mean_ratio = get_config('normal_mean_conservative', 0.98)
            std_ratio = get_config('normal_std_conservative', 0.025)
            ratios = np.random.normal(mean_ratio, std_ratio, competitor_count)
            ratios = np.clip(ratios, min_price_pct, max_price_pct)
            bids = official_estimate * ratios
        else:
            bids = np.random.uniform(min_bid, max_bid, competitor_count)

        return [round(float(b), 3) for b in bids]

    @staticmethod
    def prepare_input(competitor_bids, official_estimate):
        """Clean user-provided competitor bids, fallback to generated if needed."""
        if competitor_bids and len(competitor_bids) > 0:
            bids = extract_bid_values(competitor_bids)
            if bids:
                return bids, np.mean(bids), np.std(bids), len(bids)
        fallback_count = 5
        bids = CompetitorEngine.generate(fallback_count, official_estimate)
        return bids, np.mean(bids), np.std(bids), len(bids)


# =============================================================================
# WIN PROBABILITY ENGINE
# =============================================================================

class WinProbabilityEngine:
    """Multi-factor win probability calculation."""
    
    def __init__(self, bid_price, official_estimate, competitor_bids,
                 historical_data=None, market_factors=None,
                 company_id=None, nppi_factor=None):
        self.bid_price = float(bid_price)
        self.official_estimate = float(official_estimate)
        self.competitor_bids = extract_bid_values(competitor_bids)
        self.historical_data = historical_data or []
        self.market_factors = market_factors or {}
        self.company_id = company_id
        self.nppi_factor = nppi_factor
        self._win_prob = None
        self._confidence = None

    def compute_normal_cdf(self):
        """Simple normal CDF based on competitor distribution."""
        if not self.competitor_bids or len(self.competitor_bids) < 2:
            return 0.50
        mean_comp = np.mean(self.competitor_bids)
        std_comp = np.std(self.competitor_bids)
        if std_comp == 0:
            return 0.50
        z = (mean_comp - self.bid_price) / std_comp
        prob = stats.norm.cdf(z)
        return np.clip(prob, get_config('win_probability_clamp_min', 0.05),
                       get_config('win_probability_clamp_max', 0.95))

    def compute_multi_factor(self):
        """Five-factor model."""
        # Factor 1: Price position (30%)
        if self.competitor_bids:
            all_bids = self.competitor_bids + [self.bid_price]
            sorted_bids = sorted(all_bids)
            position = sorted_bids.index(self.bid_price)
            percentile = position / len(sorted_bids) if len(sorted_bids) > 0 else 0.5
            if percentile <= 0.2:
                score1 = 0.90
            elif percentile <= 0.4:
                score1 = 0.75
            elif percentile <= 0.6:
                score1 = 0.55
            elif percentile <= 0.8:
                score1 = 0.35
            else:
                score1 = 0.20
            if len(self.competitor_bids) > 1:
                spread = (max(self.competitor_bids) - min(self.competitor_bids)) / self.official_estimate
                if spread > 0.15:
                    score1 = min(0.95, score1 * 1.1)
                elif spread < 0.05:
                    score1 = score1 * 0.9
        else:
            score1 = 0.50

        # Factor 2: Competitor intelligence (25%)
        if self.competitor_bids and len(self.competitor_bids) >= 3:
            mean_bid = np.mean(self.competitor_bids)
            aggressive = len([b for b in self.competitor_bids if b < mean_bid * 0.95])
            conservative = len([b for b in self.competitor_bids if b > mean_bid * 1.05])
            if aggressive > conservative:
                target_percentile = 0.15
            elif conservative > aggressive:
                target_percentile = 0.35
            else:
                target_percentile = 0.25
            all_bids = self.competitor_bids + [self.bid_price]
            sorted_bids = sorted(all_bids)
            current_percentile = sorted_bids.index(self.bid_price) / len(sorted_bids) if len(sorted_bids) > 0 else 0.5
            diff = abs(current_percentile - target_percentile)
            score2 = max(0.1, 1.0 - diff)
            if self.bid_price < min(self.competitor_bids):
                score2 = min(0.95, score2 * 1.15)
        else:
            score2 = 0.50

        # Factor 3: Historical pattern (20%)
        if self.historical_data and len(self.historical_data) >= 5:
            our_wins = []
            comp_wins = []
            for record in self.historical_data:
                if record.get('winning_company_type') == 'Our Company':
                    if 'winning_bid' in record and 'official_estimate' in record:
                        ratio = record['winning_bid'] / record['official_estimate']
                        our_wins.append(ratio)
                elif record.get('winning_company_type') == 'Competitor':
                    if 'winning_bid' in record and 'official_estimate' in record:
                        ratio = record['winning_bid'] / record['official_estimate']
                        comp_wins.append(ratio)
            all_wins = our_wins if len(our_wins) >= 3 else (comp_wins if len(comp_wins) >= 3 else [])
            if all_wins:
                mean_ratio = np.mean(all_wins)
                std_ratio = np.std(all_wins) if len(all_wins) > 1 else 0.03
                current_ratio = self.bid_price / self.official_estimate
                if std_ratio > 0:
                    z_score = abs(current_ratio - mean_ratio) / std_ratio
                    score3 = max(0.1, 1.0 - (z_score / 3))
                else:
                    score3 = 0.60 if abs(current_ratio - mean_ratio) < 0.03 else 0.40
            else:
                score3 = 0.50
        else:
            score3 = 0.50

        # Factor 4: Market conditions (15%)
        seasonality = self.market_factors.get('seasonality', 1.0)
        competition_level = self.market_factors.get('competition_level', 'medium')
        economic_factor = self.market_factors.get('economic_factor', 1.0)
        base4 = 0.60
        base4 *= (0.95 if seasonality < 0.97 else (1.05 if seasonality > 1.02 else 1.0))
        comp_map = {'low': 1.08, 'medium': 1.00, 'high': 0.92, 'very_high': 0.85}
        base4 *= comp_map.get(competition_level, 1.0)
        base4 *= (0.95 if economic_factor > 1.05 else 1.0)
        score4 = np.clip(base4, 0.10, 0.95)

        # Factor 5: NPPI alignment (10%)
        if self.nppi_factor:
            expected = self.official_estimate * self.nppi_factor
            if expected > 0:
                diff = abs(self.bid_price - expected) / expected
                if diff < 0.02:
                    score5 = 0.90
                elif diff < 0.05:
                    score5 = 0.75
                elif diff < 0.10:
                    score5 = 0.55
                else:
                    score5 = 0.30
                if self.bid_price < expected:
                    score5 = min(0.95, score5 * 1.1)
            else:
                score5 = 0.50
        else:
            score5 = 0.50

        weights = [0.30, 0.25, 0.20, 0.15, 0.10]
        scores = [score1, score2, score3, score4, score5]
        prob = sum(s * w for s, w in zip(scores, weights))
        prob = np.clip(prob, get_config('win_probability_clamp_min', 0.05),
                       get_config('win_probability_clamp_max', 0.95))
        return prob

    def compute_confidence(self):
        """Confidence score based on data richness."""
        conf = get_config('confidence_base', 0.70)
        num_comp = len(self.competitor_bids)
        if num_comp >= 10:
            conf += get_config('confidence_bonus_competitor_count', 0.10)
        elif num_comp >= 5:
            conf += 0.05
        elif num_comp < 3:
            conf += get_config('confidence_penalty_sparse_data', -0.10)

        if self.historical_data:
            our_wins = sum(1 for r in self.historical_data if r.get('winning_company_type') == 'Our Company')
            if our_wins >= 5:
                conf += get_config('confidence_bonus_historical_our_wins', 0.10)
            elif len(self.historical_data) >= 20:
                conf += 0.05
            elif len(self.historical_data) < 5:
                conf += get_config('confidence_penalty_sparse_data', -0.10)

        conf += get_config('confidence_bonus_factor_consistency', 0.05)
        return np.clip(conf, 0.50, 0.95)

    def get_win_probability(self, method='multi_factor'):
        if method == 'normal_cdf':
            prob = self.compute_normal_cdf()
        else:
            prob = self.compute_multi_factor()
        self._win_prob = prob
        return prob

    def get_confidence(self):
        if self._confidence is None:
            self._confidence = self.compute_confidence()
        return self._confidence


# =============================================================================
# OPTIMUM BID ENGINE
# =============================================================================

class OptimumBidEngine:
    """Searches for optimal bid that maximises EV - λ*Risk."""
    
    def __init__(self, official_estimate, estimated_cost, competitor_bids,
                 slt_threshold, nppi_factor, risk_tolerance='moderate',
                 procurement_type='works'):
        self.official_estimate = float(official_estimate)
        self.estimated_cost = float(estimated_cost)
        self.competitor_bids = extract_bid_values(competitor_bids)
        self.slt_threshold = float(slt_threshold)
        self.nppi_factor = float(nppi_factor)
        self.risk_tolerance = risk_tolerance
        self.procurement_type = procurement_type
        self._optimal_bid = None

    def compute(self):
        if self.competitor_bids:
            mean_comp = np.mean(self.competitor_bids)
            base = mean_comp * get_config('base_bid_ratio_with_competitors', 0.98)
        else:
            base = self.official_estimate * get_config('base_bid_ratio_no_competitors', 0.89)

        risk_mult = get_nested_config('risk_multipliers', self.risk_tolerance, 1.00)
        bid = base * risk_mult

        min_bid = self.slt_threshold * get_config('slt_threshold_multiplier', 1.01)
        max_bid = self.official_estimate * get_config('bid_upper_clamp_factor', 0.98)
        bid = max(bid, min_bid)
        bid = min(bid, max_bid)

        self._optimal_bid = round(bid, 3)
        return self._optimal_bid

    def get_bid(self):
        if self._optimal_bid is None:
            self.compute()
        return self._optimal_bid