# =============================================================================
# ENHANCED report_generator.py - With Detailed Analysis & Visualizations
# =============================================================================

import io
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json
import base64
import logging
import random
from scipy import stats
import traceback
logger = logging.getLogger(__name__)

from version import __version__, __version_date__, get_app_name

# =============================================================================
# SECTION 1: ENHANCED UNIFIED DATA MODEL
# =============================================================================

class EnhancedReportData:
    """Enhanced report data structure with detailed analysis"""
    
    def __init__(self, analysis_record: Dict, comparison: Dict, user_info: Dict = None):
        self.analysis_record = analysis_record or {}
        self.comparison = comparison or {}
        self.user_info = user_info or {}
        self.generated_at = datetime.now()
        
        # Core values (must be first)
        self.tender_id = self._safe_str(analysis_record.get('tender_id'))
        self.tender_title = self._safe_str(analysis_record.get('tender_title'))
        self.procuring_entity = self._safe_str(analysis_record.get('procuring_entity'))
        self.official_estimate = self._safe_float(analysis_record.get('official_estimate'), 1.0)
        
        # Location
        self.division = self._safe_str(analysis_record.get('division'))
        self.district = self._safe_str(analysis_record.get('district'))
        self.thana = self._safe_str(analysis_record.get('thana'))
        
        # Procurement
        self.procurement_type = self._safe_str(analysis_record.get('procurement_type', 'works')).upper()
        self.submission_deadline = self._safe_str(analysis_record.get('submission_deadline', 'N/A'))[:10]
        self.risk_tolerance = self._safe_str(analysis_record.get('risk_tolerance', 'moderate')).title()
        
        # Extract competitor bids
        self.competitor_bids_list = []
        self.competitor_names = []
        self._extract_competitor_bids(analysis_record)
        # ✅ Extract NPPI information from analysis_record (passed from main.py)
        self.nppi_factor = self._safe_float(analysis_record.get('nppi_factor', 0.920))
        self.nppi_mode = self._safe_str(analysis_record.get('nppi_mode', 'Default'))
        self.nppi_warning = analysis_record.get('nppi_warning', None)
        
        # If nppi_factor is not in analysis_record, try to get it from advanced comparison
        if self.nppi_factor == 0.920 and 'advanced' in self.comparison:
            self.nppi_factor = self._safe_float(self.comparison['advanced'].get('nppi_factor', 0.920))

        # Calculate competitor statistics
        if self.competitor_bids_list:
            self.competitor_stats = {
                'count': len(self.competitor_bids_list),
                'min': min(self.competitor_bids_list),
                'max': max(self.competitor_bids_list),
                'mean': np.mean(self.competitor_bids_list),
                'median': np.median(self.competitor_bids_list),
                'std': np.std(self.competitor_bids_list),
                'q1': np.percentile(self.competitor_bids_list, 25),
                'q3': np.percentile(self.competitor_bids_list, 75),
                'cv': np.std(self.competitor_bids_list) / np.mean(self.competitor_bids_list) if np.mean(self.competitor_bids_list) > 0 else 0
            }
        else:
            self.competitor_stats = {}
        
        # Find best tier
        self.best_tier = self._find_best_tier()
        self.best_result = self.comparison.get(self.best_tier, {})
        
        # Tier results
        self.tiers = ['basic', 'advanced', 'enhanced']
        self.tier_display_names = {'basic': 'Basic', 'advanced': 'Advanced (PPR 2025)', 'enhanced': 'Enhanced (ML)'}
        
        # ⚠️ CRITICAL: Define recommended_bid BEFORE calling _calculate_ppr_detailed()
        self.recommended_bid = self._safe_float(self.best_result.get('optimal_bid', 0))
        self.win_probability = self._safe_float(self.best_result.get('win_probability', 0.6))
        self.bid_ratio = self.recommended_bid / self.official_estimate if self.official_estimate > 0 else 0
        
        # Financial projections
        self.estimated_cost = self.official_estimate * 0.85
        self.expected_profit = max(0, self.recommended_bid - self.estimated_cost)
        self.expected_value = self.expected_profit * self.win_probability
        
        # Risk assessment
        self.risk_level = self._safe_str(self.best_result.get('risk_level', 'MEDIUM'))
        
        # ✅ NOW call PPR calculation (after recommended_bid is defined)
        self._calculate_ppr_detailed()
        
        # Set compliance flag after PPR calculation
        self.is_ppr_compliant = self.recommended_bid >= self.slt_threshold if self.slt_threshold > 0 else False
        logger.info(f"EnhancedReportData initialized for tender_id={self.tender_id} | recommended_bid={self.recommended_bid} | win_probability={self.win_probability} | ppr_compliant={self.is_ppr_compliant}")
        print("report_generator.py loaded successfully")
        print("generate_html_content_only function defined:", 'generate_html_content_only' in dir())

    def _extract_competitor_bids(self, analysis_record):
        """Extract competitor bids from various formats"""
        raw_bids = analysis_record.get('competitor_bids', [])
        
        if not raw_bids:
            raw_bids = analysis_record.get('current_competitor_bids', [])
        
        if raw_bids and isinstance(raw_bids, list):
            for item in raw_bids:
                if isinstance(item, dict):
                    bid = self._safe_float(item.get('bid', item.get('amount', 0)))
                    name = self._safe_str(item.get('name', f'Competitor {len(self.competitor_bids_list)+1}'))
                    if bid > 0:
                        self.competitor_bids_list.append(round(bid, 3))
                        self.competitor_names.append(name)
                elif isinstance(item, (int, float)):
                    if item > 0:
                        self.competitor_bids_list.append(round(float(item), 3))
                        self.competitor_names.append(f'Competitor {len(self.competitor_bids_list)+1}')
    
    def _calculate_ppr_detailed(self):
        """Calculate detailed PPR 2025 metrics using the captured NPPI factor"""
        
        # ✅ Use the NPPI factor from analysis (not hardcoded 0.92)
        # If nppi_factor wasn't set, default to 0.92
        nppi_factor = getattr(self, 'nppi_factor', 0.920)
        
        # NPPI Price (using the actual NPPI factor from analysis)
        self.nppi_price = round(self.official_estimate * nppi_factor, 3)
        
        # Competitor statistics
        if self.competitor_bids_list:
            self.avg_competitor = round(np.mean(self.competitor_bids_list), 3)
            self.std_competitor = round(np.std(self.competitor_bids_list), 3)
            self.median_competitor = round(np.median(self.competitor_bids_list), 3)
        else:
            self.avg_competitor = round(self.official_estimate * 0.91, 3)
            self.std_competitor = round(self.official_estimate * 0.05, 3)
            self.median_competitor = self.avg_competitor
        
        # PPR Weights
        weights = {
            'competitor_avg': 0.50,
            'official_est': 0.20,
            'nppi': 0.30
        }
        
        # Weighted Average (X̄) - using actual NPPI factor
        self.weighted_avg = round(
            weights['competitor_avg'] * self.avg_competitor +
            weights['official_est'] * self.official_estimate +
            weights['nppi'] * self.nppi_price,
            3
        )
        
        # Weighted Standard Deviation
        competitor_sample = self.competitor_bids_list[:10] if self.competitor_bids_list else []
        if competitor_sample:
            squared_deviations = [(self.weighted_avg - price) ** 2 for price in competitor_sample]
            variance = sum(squared_deviations) / len(competitor_sample)
            self.weighted_std = round(np.sqrt(variance), 3)
        else:
            self.weighted_std = round(self.official_estimate * 0.03, 3)
        
        # SLT Threshold
        self.slt_threshold = round(self.weighted_avg - self.weighted_std, 3)
        
        # Store the actual NPPI factor used
        self.nppi_factor = nppi_factor
        
        # Market competitiveness score
        if self.official_estimate > 0:
            self.market_position = min(100, max(0, (1 - (self.recommended_bid / self.official_estimate)) * 100))
        else:
            self.market_position = 50
        
        # PPR Compliance Score
        self.is_ppr_compliant = self.recommended_bid >= self.slt_threshold if self.slt_threshold > 0 else False
        
        if self.is_ppr_compliant:
            self.compliance_margin = ((self.recommended_bid - self.slt_threshold) / self.slt_threshold * 100) if self.slt_threshold > 0 else 0
            self.compliance_score = min(100, 70 + (self.compliance_margin * 2))
        else:
            self.compliance_margin = ((self.slt_threshold - self.recommended_bid) / self.slt_threshold * 100) if self.slt_threshold > 0 else 0
            self.compliance_score = max(0, 70 - (self.compliance_margin * 3))


    def _calculate_ppr_detailed_bak(self):
        """Calculate detailed PPR 2025 metrics"""
        # PPR 2025 Constants
        NPPI_FACTOR = 0.920
        
        # NPPI Price
        self.nppi_price = round(self.official_estimate * NPPI_FACTOR, 3)
        
        # Competitor statistics
        if self.competitor_bids_list:
            self.avg_competitor = round(np.mean(self.competitor_bids_list), 3)
            self.std_competitor = round(np.std(self.competitor_bids_list), 3)
            self.median_competitor = round(np.median(self.competitor_bids_list), 3)
        else:
            self.avg_competitor = round(self.official_estimate * 0.91, 3)
            self.std_competitor = round(self.official_estimate * 0.05, 3)
            self.median_competitor = self.avg_competitor
        
        # PPR Weights
        weights = {
            'competitor_avg': 0.50,
            'official_est': 0.20,
            'nppi': 0.30
        }
        
        # Weighted Average (X̄)
        self.weighted_avg = round(
            weights['competitor_avg'] * self.avg_competitor +
            weights['official_est'] * self.official_estimate +
            weights['nppi'] * self.nppi_price,
            3
        )
        
        # Weighted Standard Deviation
        competitor_sample = self.competitor_bids_list[:10] if self.competitor_bids_list else []
        if competitor_sample:
            squared_deviations = [(self.weighted_avg - price) ** 2 for price in competitor_sample]
            variance = sum(squared_deviations) / len(competitor_sample)
            self.weighted_std = round(np.sqrt(variance), 3)
        else:
            self.weighted_std = round(self.official_estimate * 0.03, 3)
        
        # SLT Threshold
        self.slt_threshold = round(self.weighted_avg - self.weighted_std, 3)
        
        # NPPI Factor
        if 'advanced' in self.comparison and self.comparison['advanced']:
            self.nppi_factor = self._safe_float(self.comparison['advanced'].get('nppi_factor', NPPI_FACTOR))
        else:
            self.nppi_factor = NPPI_FACTOR
        
        # Market competitiveness score (uses self.recommended_bid which is now defined)
        if self.official_estimate > 0:
            self.market_position = min(100, max(0, (1 - (self.recommended_bid / self.official_estimate)) * 100))
        else:
            self.market_position = 50
        
        # PPR Compliance Score (uses self.slt_threshold and self.recommended_bid)
        self.is_ppr_compliant = self.recommended_bid >= self.slt_threshold if self.slt_threshold > 0 else False
        
        if self.is_ppr_compliant:
            self.compliance_margin = ((self.recommended_bid - self.slt_threshold) / self.slt_threshold * 100) if self.slt_threshold > 0 else 0
            self.compliance_score = min(100, 70 + (self.compliance_margin * 2))
        else:
            self.compliance_margin = ((self.slt_threshold - self.recommended_bid) / self.slt_threshold * 100) if self.slt_threshold > 0 else 0
            self.compliance_score = max(0, 70 - (self.compliance_margin * 3))

    
    def _safe_str(self, value, default="N/A"):
        if value is None:
            return default
        return str(value).strip() if str(value).strip() else default
    
    def _safe_float(self, value, default=0.0):
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def _find_best_tier(self):
        best = 'basic'
        best_score = -1
        for tier, result in self.comparison.items():
            if result and isinstance(result, dict):
                score = (self._safe_float(result.get('confidence_score', 0.7)) * 
                        self._safe_float(result.get('win_probability', 0)))
                if score > best_score:
                    best_score = score
                    best = tier
        return best
    
    def get_tier_table_data(self):
        headers = ['Analysis Tier', 'Method', 'Optimal Bid (BDT)', '% of Estimate', 'Win Prob', 'Confidence', 'Risk']
        rows = [headers]
        
        for tier in self.tiers:
            if tier in self.comparison:
                r = self.comparison[tier]
                rows.append([
                    self.tier_display_names.get(tier, tier.upper()),
                    self._safe_str(r.get('method', 'N/A'))[:25],
                    f"{self._safe_float(r.get('optimal_bid', 0)):,.3f}",  # 3 decimals
                    f"{self._safe_float(r.get('bid_ratio', 0)) * 100:.2f}%",
                    f"{self._safe_float(r.get('win_probability', 0)) * 100:.0f}%",
                    f"{self._safe_float(r.get('confidence_score', 0.7)) * 100:.0f}%",
                    self._get_risk_display(r.get('risk_level', 'MEDIUM'))
                ])
        
        return rows
    
    def _get_risk_display(self, risk_level):
        risk_level = str(risk_level).upper()
        if risk_level == 'HIGH':
            return "🔴 HIGH"
        elif risk_level == 'MEDIUM':
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"
    
    def generate_detailed_ai_recommendation(self):
        """Generate detailed AI recommendation text"""
        comp_count = len(self.competitor_bids_list)
        pct_of_estimate = self.bid_ratio * 100
        
        # Calculate positioning relative to competitors
        if self.competitor_bids_list:
            min_comp = min(self.competitor_bids_list)
            max_comp = max(self.competitor_bids_list)
            avg_comp = np.mean(self.competitor_bids_list)
            
            if self.recommended_bid <= min_comp:
                positioning = "significantly below the lowest competitor bid"
                positioning_detail = "aggressive pricing strategy"
            elif self.recommended_bid <= avg_comp:
                positioning = "below the average competitor bid"
                positioning_detail = "competitive pricing with good win probability"
            else:
                positioning = "above the average competitor bid"
                positioning_detail = "balanced approach prioritizing profitability"
        else:
            positioning = "based on official estimate and market factors"
            positioning_detail = "standard PPR 2025 compliant approach"
        
        recommendation = (
            f"Based on **{comp_count} competitor bids** and **PPR 2025 compliance metrics**, the optimal bid is "
            f"**BDT {self.recommended_bid:,.3f}** ({pct_of_estimate:.1f}% of estimate). "
            f"This bid maintains a **{self.win_probability*100:.0f}% win probability** while staying "
            f"{'safely above' if self.is_ppr_compliant else 'below'} the SLT threshold of BDT {self.slt_threshold:,.3f}. "
            f"Positioned {positioning}, this represents a {positioning_detail}. "
            f"Risk assessment indicates a **{self.risk_level} risk profile** with "
            f"{'strong' if self.is_ppr_compliant else 'cautionary'} PPR compliance."
        )
        
        return recommendation
    
    def get_ppr_breakdown_data(self):
        """Get PPR 2025 calculation breakdown in multi-line format"""
        nppi_price = self.official_estimate * self.nppi_factor
        
        return [
            ["Step", "Formula / Description", "Calculation", "Result"],
            ["1", "Official Estimate<br/><span style='font-size: 9px; color: #666;'>From tender document</span>", 
            f"BDT {self.official_estimate:,.3f}", "Base Value"],
            
            ["2", "NPPI Factor<br/><span style='font-size: 9px; color: #666;'>28-day market average</span>", 
            f"{self.nppi_factor:.3f}", "Index Factor"],
            
            ["3", "NPPI Price<br/><span style='font-size: 9px; color: #666;'>Estimate × NPPI Factor</span>", 
            f"{self.official_estimate:,.0f} × {self.nppi_factor:.3f}", f"BDT {nppi_price:,.3f}"],
            
            ["4", "Avg Competitor<br/><span style='font-size: 9px; color: #666;'>Σ(Comp Bids) ÷ N</span>", 
            f"({len(self.competitor_bids_list)} bids)", f"BDT {self.avg_competitor:,.3f}"],
            
            ["5", "Weighted Avg (X̄)<br/><span style='font-size: 9px; color: #666;'>0.5(Avg) + 0.2(Est) + 0.3(NPPI)</span>", 
            f"0.5×{self.avg_competitor:,.0f}<br/>+ 0.2×{self.official_estimate:,.0f}<br/>+ 0.3×{nppi_price:,.0f}", 
            f"BDT {self.weighted_avg:,.3f}"],
            
            ["6", "Std Deviation (Sd)<br/><span style='font-size: 9px; color: #666;'>√[Σ(x̄ - xᵢ)²/(n-1)]</span>", 
            f"σ = {self.weighted_std:.3f}", f"BDT {self.weighted_std:,.3f}"],
            
            ["7", "SLT Threshold<br/><span style='font-size: 9px; color: #666;'>X̄ - Sd</span>", 
            f"{self.weighted_avg:,.0f} - {self.weighted_std:,.0f}", f"BDT {self.slt_threshold:,.3f}"],
            
            ["8", "Recommended Bid<br/><span style='font-size: 9px; color: #666;'>AI Optimized</span>", 
            "Based on win probability", f"BDT {self.recommended_bid:,.3f}"],
            
            ["9", "Compliance Check<br/><span style='font-size: 9px; color: #666;'>Bid ≥ SLT?</span>", 
            f"{self.recommended_bid:,.0f} ≥ {self.slt_threshold:,.0f}", 
            f"<strong style='color: {'#10b981' if self.is_ppr_compliant else '#ef4444'}'>{'✅ PASS' if self.is_ppr_compliant else '❌ FAIL'}</strong>"],
        ]



# =============================================================================
# SECTION 2: VISUALIZATION FUNCTIONS
# =============================================================================

def create_competitor_distribution_chart(data: EnhancedReportData) -> plt.Figure:
    """Create competitor bid distribution histogram with KDE"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    if data.competitor_bids_list:
        # Histogram
        ax.hist(data.competitor_bids_list, bins=10, alpha=0.7, color='steelblue', edgecolor='black', label='Competitor Bids')
        
        # Add KDE (kernel density estimate)
        
        kde = stats.gaussian_kde(data.competitor_bids_list)
        x_range = np.linspace(min(data.competitor_bids_list), max(data.competitor_bids_list), 100)
        ax.plot(x_range, kde(x_range) * len(data.competitor_bids_list) * (max(data.competitor_bids_list) - min(data.competitor_bids_list)) / 10, 
                'r-', linewidth=2, label='Density')
        
        # Add recommended bid line
        ax.axvline(data.recommended_bid, color='green', linewidth=2, linestyle='--', label=f'Recommended: BDT {data.recommended_bid:,.0f}')
        
        # Add official estimate line
        ax.axvline(data.official_estimate, color='orange', linewidth=2, linestyle=':', label=f'Estimate: BDT {data.official_estimate:,.0f}')
        
        ax.set_xlabel('Bid Amount (BDT)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Competitor Bid Distribution Analysis', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No competitor data available', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    return fig


def create_win_probability_curve(data: EnhancedReportData) -> plt.Figure:
    """Create win probability vs bid amount curve"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Generate bid range
    min_bid = data.official_estimate * 0.70
    max_bid = data.official_estimate * 1.10
    bid_range = np.linspace(min_bid, max_bid, 100)
    
    # Calculate win probability function (logistic curve)
    # Lower bids = higher win probability, with diminishing returns
    center = data.official_estimate * 0.92
    steepness = 0.00015
    win_probs = 1 / (1 + np.exp(steepness * (bid_range - center)))
    
    # Add noise for realism
    win_probs = win_probs * (1 + np.random.normal(0, 0.02, len(win_probs)))
    win_probs = np.clip(win_probs, 0.05, 0.95)
    
    ax.plot(bid_range, win_probs * 100, 'b-', linewidth=2, label='Win Probability Curve')
    
    # Mark recommended bid
    recommended_win_prob = data.win_probability * 100
    ax.plot(data.recommended_bid, recommended_win_prob, 'ro', markersize=10, label=f'Recommended: {recommended_win_prob:.0f}%')
    
    # Mark competitor bids
    if data.competitor_bids_list:
        for i, bid in enumerate(data.competitor_bids_list[:10]):  # Limit to 10 for clarity
            prob = 1 / (1 + np.exp(steepness * (bid - center))) * 100
            ax.plot(bid, prob, 'gray', marker='x', markersize=5, alpha=0.5)
    
    ax.set_xlabel('Bid Amount (BDT)', fontsize=12)
    ax.set_ylabel('Win Probability (%)', fontsize=12)
    ax.set_title('Win Probability vs Bid Amount', fontsize=14, fontweight='bold')
    ax.set_xlim(min_bid, max_bid)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Format x-axis with BDT
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'BDT {x/1000:.0f}K'))
    
    plt.tight_layout()
    return fig


def create_risk_radar_chart(data: EnhancedReportData) -> plt.Figure:
    """Create risk assessment radar chart"""
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    categories = ['PPR Compliance', 'Win Probability', 'Profit Margin', 'Market Position', 'Competitor Density']
    
    # Calculate scores (0-100)
    compliance_score = data.compliance_score if hasattr(data, 'compliance_score') else 85
    win_score = data.win_probability * 100
    profit_score = min(100, (data.expected_profit / data.official_estimate) * 1000) if data.official_estimate > 0 else 50
    market_score = data.market_position if hasattr(data, 'market_position') else 60
    
    # Competitor density score (more competitors = higher risk)
    if data.competitor_bids_list:
        competitor_density = min(100, (len(data.competitor_bids_list) / 20) * 100)
        density_score = 100 - competitor_density  # Inverse: more competitors = lower score
    else:
        density_score = 50
    
    values = [compliance_score, win_score, profit_score, market_score, density_score]
    
    # Close the polygon
    values += values[:1]
    
    angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
    angles += angles[:1]
    
    ax.plot(angles, values, 'o-', linewidth=2, color='steelblue')
    ax.fill(angles, values, alpha=0.25, color='steelblue')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title('Risk Assessment Dashboard', fontsize=14, fontweight='bold', pad=20)
    ax.grid(True)
    
    plt.tight_layout()
    return fig


def create_performance_dashboard(data: EnhancedReportData) -> plt.Figure:
    """Create performance metrics dashboard with multiple subplots"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Subplot 1: Competitor Distribution (Top Left)
    ax1 = axes[0, 0]
    if data.competitor_bids_list:
        ax1.hist(data.competitor_bids_list, bins=10, alpha=0.7, color='steelblue', edgecolor='black')
        ax1.axvline(data.recommended_bid, color='green', linewidth=2, linestyle='--', label='Recommended')
        ax1.axvline(data.official_estimate, color='orange', linewidth=2, linestyle=':', label='Estimate')
        ax1.set_xlabel('Bid (BDT)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Competitor Bid Distribution', fontweight='bold')
        ax1.legend()
        ax1.ticklabel_format(style='plain', axis='x')
    
    # Subplot 2: Tier Comparison (Top Right)
    ax2 = axes[0, 1]
    tiers = ['Basic', 'Advanced', 'Enhanced']
    win_probs = []
    for tier in ['basic', 'advanced', 'enhanced']:
        if tier in data.comparison:
            win_probs.append(data.comparison[tier].get('win_probability', 0) * 100)
        else:
            win_probs.append(0)
    
    bars = ax2.bar(tiers, win_probs, color=['#ff9999', '#66b3ff', '#99ff99'])
    ax2.set_ylabel('Win Probability (%)')
    ax2.set_title('Win Probability by Analysis Tier', fontweight='bold')
    ax2.set_ylim(0, 100)
    for bar, prob in zip(bars, win_probs):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{prob:.0f}%', ha='center', fontsize=10)
    
    # Subplot 3: Financial Metrics (Bottom Left)
    ax3 = axes[1, 0]
    metrics = ['Cost', 'Profit', 'Expected Value']
    values = [data.estimated_cost, data.expected_profit, data.expected_value]
    colors_metrics = ['#ff9999', '#66b3ff', '#99ff99']
    bars = ax3.bar(metrics, values, color=colors_metrics)
    ax3.set_ylabel('Amount (BDT)')
    ax3.set_title('Financial Analysis', fontweight='bold')
    for bar, val in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + val*0.02, f'BDT {val:,.0f}', ha='center', fontsize=9, rotation=45)
    
    # Subplot 4: Market Position (Bottom Right)
    ax4 = axes[1, 1]
    if data.competitor_bids_list:
        positions = []
        labels = []
        sorted_bids = sorted(data.competitor_bids_list)
        for i, bid in enumerate(sorted_bids[:10]):  # Show top 10
            positions.append(bid)
            labels.append(f'C{i+1}')
        
        # Add recommended bid
        positions.append(data.recommended_bid)
        labels.append('You')
        
        # Find index of recommended bid for color coding
        colors_position = ['gray'] * len(sorted_bids[:10]) + ['green']
        
        y_pos = np.arange(len(positions))
        ax4.barh(y_pos, positions, color=colors_position)
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(labels)
        ax4.set_xlabel('Bid Amount (BDT)')
        ax4.set_title('Market Position - Bid Comparison', fontweight='bold')
        ax4.invert_yaxis()
    
    plt.suptitle('Performance Dashboard', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig


def fig_to_base64(fig):
    """Convert matplotlib figure to base64 for HTML embedding"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return img_base64


# =============================================================================
# SECTION 3: HTML REPORT WITH VISUALIZATIONS
# =============================================================================
def render_enhanced_html_report(data: EnhancedReportData, return_html: bool = False) -> Optional[str]:
    """Render enhanced HTML report with visualizations"""
    
    # Generate visualizations
    dist_fig = create_competitor_distribution_chart(data)
    win_fig = create_win_probability_curve(data)
    radar_fig = create_risk_radar_chart(data)
    dashboard_fig = create_performance_dashboard(data)
    
    # Convert to base64
    dist_img = fig_to_base64(dist_fig)
    win_img = fig_to_base64(win_fig)
    radar_img = fig_to_base64(radar_fig)
    dashboard_img = fig_to_base64(dashboard_fig)
    
    # Generate detailed recommendation
    detailed_recommendation = data.generate_detailed_ai_recommendation()
    
    # PPR breakdown
    ppr_rows = data.get_ppr_breakdown_data()
    ppr_table_html = _generate_html_table(ppr_rows)
    
    # Status styling
    status_color = "#10b981" if data.is_ppr_compliant else "#ef4444"
    status_icon = "✅" if data.is_ppr_compliant else "⚠️"
    status_text = "COMPLIANT" if data.is_ppr_compliant else "SLT RISK"
    risk_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"}.get(data.risk_level.upper(), "#6b7280")
    
    # Build NPPI info HTML if not default
    nppi_info_html = ""
    if hasattr(data, 'nppi_mode') and data.nppi_mode != 'Default':
        nppi_info_html = f"""
        <div style='background: #f0f9ff; padding: 0.5rem; border-radius: 8px; margin: 0.5rem 0;'>
            <small>📊 <strong>NPPI Configuration:</strong> {data.nppi_mode} | Factor: {data.nppi_factor:.4f}</small>
            {f"<small style='color: #e67e22;'> ⚠️ {data.nppi_warning}</small>" if data.nppi_warning else ""}
        </div>
        """
    
    # Competitor table (all with 3 decimals)
    comp_rows = [["#", "Competitor", "Bid Amount (BDT)", "% of Estimate", "Deviation"]]
    if data.competitor_bids_list:
        sorted_comp = sorted(zip(data.competitor_names, data.competitor_bids_list), key=lambda x: x[1])
        for i, (name, bid) in enumerate(sorted_comp, 1):
            pct = (bid / data.official_estimate * 100) if data.official_estimate > 0 else 0
            dev = ((bid - data.official_estimate) / data.official_estimate * 100) if data.official_estimate > 0 else 0
            highlight = "🏆 " if i == 1 else ""
            comp_rows.append([str(i), f"{highlight}{name}", f"{bid:,.3f}", f"{pct:.2f}%", f"{dev:+.2f}%"])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>TenderAI - Enhanced Analysis Report</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
            .report-container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ font-size: 32px; margin-bottom: 8px; }}
            .header p {{ font-size: 14px; opacity: 0.9; }}
            .content {{ padding: 30px; }}
            .section {{ margin-bottom: 35px; }}
            .section-title {{ font-size: 22px; font-weight: bold; color: #1e3a8a; border-left: 5px solid #3b82f6; padding-left: 15px; margin-bottom: 20px; }}
            .info-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; background: #f8fafc; padding: 20px; border-radius: 12px; }}
            .info-item {{ padding: 10px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .info-label {{ font-size: 12px; color: #64748b; margin-bottom: 5px; }}
            .info-value {{ font-size: 18px; font-weight: bold; color: #1e293b; }}
            .recommendation-box {{ background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-left: 5px solid #10b981; padding: 20px; border-radius: 12px; margin: 20px 0; line-height: 1.6; }}
            .warning-box {{ background: #fef3c7; border-left: 5px solid #f59e0b; padding: 15px; border-radius: 8px; }}
            .error-box {{ background: #fef2f2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background: #1e3a8a; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
            tr:hover {{ background: #f1f5f9; }}
            .viz-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
            .viz-card {{ background: #f8fafc; border-radius: 12px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .viz-card img {{ width: 100%; height: auto; border-radius: 8px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .stat-card {{ text-align: center; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; }}
            .stat-value {{ font-size: 28px; font-weight: bold; }}
            .stat-label {{ font-size: 12px; opacity: 0.9; margin-top: 5px; }}
            .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 11px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <h1>🤖 {get_app_name()}</h1>
                <p>AI Enhanced Bid Management System • PPR 2025 Compliant</p>
                <small>Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')} | Analysis ID: {data.tender_id}</small>
            </div>
            
            <div class="content">
                <!-- Quick Stats -->
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-value">{len(data.competitor_bids_list)}</div><div class="stat-label">Competitors</div></div>
                    <div class="stat-card"><div class="stat-value">{data.win_probability*100:.0f}%</div><div class="stat-label">Win Probability</div></div>
                    <div class="stat-card"><div class="stat-value">BDT {data.recommended_bid:,.3f}</div><div class="stat-label">Recommended Bid</div></div>
                    <div class="stat-card"><div class="stat-value">{data.bid_ratio*100:.2f}%</div><div class="stat-label">of Estimate</div></div>
                </div>
                
                <!-- Tender Information -->
                <div class="section">
                    <div class="section-title">📋 Tender Information</div>
                    <div class="info-grid">
                        <div class="info-item"><div class="info-label">Tender ID</div><div class="info-value">{data.tender_id}</div></div>
                        <div class="info-item"><div class="info-label">Procuring Entity</div><div class="info-value">{data.procuring_entity[:40]}</div></div>
                        <div class="info-item"><div class="info-label">Official Estimate</div><div class="info-value">BDT {data.official_estimate:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Procurement Type</div><div class="info-value">{data.procurement_type}</div></div>
                        <div class="info-item"><div class="info-label">Location</div><div class="info-value">{data.division} / {data.district}</div></div>
                        <div class="info-item"><div class="info-label">Risk Tolerance</div><div class="info-value">{data.risk_tolerance}</div></div>
                        <div class="info-item"><div class="info-label">SLT Threshold</div><div class="info-value">BDT {data.slt_threshold:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Compliance</div><div class="info-value"><span class="badge" style="background:{status_color}20; color:{status_color};">{status_icon} {status_text}</span></div></div>
                    </div>
                </div>
                
                <!-- Detailed AI Recommendation -->
                <div class="section">
                    <div class="section-title">🎯 AI Recommendation</div>
                    <div class="recommendation-box">
                        <strong>💡 Strategic Analysis:</strong><br>
                        {detailed_recommendation}<br><br>
                        <strong>📊 Key Insights:</strong>
                        <ul style="margin-top: 10px; margin-left: 20px;">
                            <li><strong>Market Position:</strong> {data.market_position:.1f}% competitive score</li>
                            <li><strong>Compliance Margin:</strong> {'+' if data.is_ppr_compliant else ''}{data.compliance_margin:.1f}% from SLT threshold</li>
                            <li><strong>Expected ROI:</strong> {(data.expected_profit/data.estimated_cost*100):.1f}% on investment</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Visualizations -->
                <div class="section">
                    <div class="section-title">📊 Visual Performance Dashboard</div>
                    <div class="viz-grid">
                        <div class="viz-card"><img src="data:image/png;base64,{dashboard_img}" alt="Performance Dashboard"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{radar_img}" alt="Risk Assessment"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{dist_img}" alt="Competitor Distribution"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{win_img}" alt="Win Probability Curve"></div>
                    </div>
                </div>
                
                <!-- Three-Tier Comparison -->
                <div class="section">
                    <div class="section-title">🔄 Three-Tier Analysis Comparison</div>
                    {_generate_html_table(data.get_tier_table_data())}
                </div>
                
                <!-- Competitor Intelligence -->
                <div class="section">
                    <div class="section-title">👥 Competitor Intelligence ({len(data.competitor_bids_list)} competitors)</div>
                    {_generate_html_table(comp_rows)}
                    <div class="info-grid" style="margin-top: 15px;">
                        <div class="info-item"><div class="info-label">Lowest Bid</div><div class="info-value">BDT {data.competitor_stats.get('min', 0):,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Highest Bid</div><div class="info-value">BDT {data.competitor_stats.get('max', 0):,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Average Bid</div><div class="info-value">BDT {data.competitor_stats.get('mean', 0):,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Std Deviation</div><div class="info-value">BDT {data.competitor_stats.get('std', 0):,.3f}</div></div>
                    </div>
                </div>
                
                <!-- PPR 2025 Calculation Breakdown -->
                <div class="section">
                    <div class="section-title">📐 PPR 2025 Calculation Breakdown</div>
                    {nppi_info_html}
                    {ppr_table_html}
                </div>
                
                <!-- Financial Projections -->
                <div class="section">
                    <div class="section-title">💰 Financial Projections</div>
                    <div class="info-grid">
                        <div class="info-item"><div class="info-label">Estimated Cost</div><div class="info-value">BDT {data.estimated_cost:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Expected Profit</div><div class="info-value">BDT {data.expected_profit:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Win Probability</div><div class="info-value">{data.win_probability*100:.0f}%</div></div>
                        <div class="info-item"><div class="info-label">Expected Value</div><div class="info-value">BDT {data.expected_value:,.3f}</div></div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <div style="margin-bottom: 8px;">
                    
                    <strong>Generated by {get_app_name()}</strong>
                </div>
                <strong>Disclaimer:</strong> This AI-generated analysis complies with Bangladesh PPR 2025 guidelines.<br>
                Final bidding decisions should consider project-specific risks, internal cost structures, and strategic objectives.
                {f"<br>Prepared for: {data.user_info.get('full_name', 'N/A')} | {data.user_info.get('company_name', 'N/A')}" if data.user_info else ""}
            </div>
        </div>
    </body>
    </html>
    """
    
    if return_html:
        return html
    else:
        st.components.v1.html(html, height=800, scrolling=True)
        return None

def _generate_html_table(rows: List[List]) -> str:
    """Generate HTML table with proper text wrapping and column sizing"""
    logger.info(f"Generating HTML table with {len(rows)} rows")
    if not rows:
        return "<p>No data available</p>"
    
    num_cols = len(rows[0]) if rows else 0
    
    # Custom width mapping for specific tables
    col_widths = []
    if rows and len(rows) > 0 and rows[0] and rows[0][0] == "Step":
        # PPR Calculation table - 4 columns with specific widths
        col_widths = ["8%", "32%", "35%", "25%"]
    elif rows and len(rows) > 0 and rows[0] and rows[0][0] == "Analysis Tier":
        # Tier comparison table (7 columns)
        col_widths = ["12%", "20%", "18%", "12%", "12%", "12%", "14%"]
    elif rows and len(rows) > 0 and rows[0] and rows[0][0] == "#":
        # Competitor table (5 columns)
        col_widths = ["8%", "27%", "25%", "20%", "20%"]
    else:
        # Default - equal distribution
        col_widths = [f"{100/num_cols}%" for _ in range(num_cols)]
    
    html = '<table style="width:100%; border-collapse: collapse; table-layout: fixed;">'
    
    for i, row in enumerate(rows):
        html += '<tr>'
        for j, cell in enumerate(row):
            tag = 'th' if i == 0 else 'td'
            width_style = f'width: {col_widths[j]};' if j < len(col_widths) else ''
            
            if i == 0:
                # Header row styling
                style = f'{width_style} background: #1e3a8a; color: white; padding: 10px; text-align: center; font-weight: bold;'
            else:
                # Data row styling with word wrapping
                style = f'{width_style} padding: 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; word-wrap: break-word; word-break: break-word; white-space: normal; line-height: 1.4;'
                
                # Right align numeric columns
                if (j == 2 or j == 3) and any(c.isdigit() for c in str(cell)):
                    style += ' text-align: right;'
                elif j == 0:
                    style += ' text-align: center;'
                else:
                    style += ' text-align: left;'
            
            # Handle multi-line content (convert \n to <br> and preserve HTML)
            cell_content = str(cell)
            if not i == 0:  # For data rows, preserve HTML tags
                # Don't escape HTML for data rows
                html += f'<{tag} style="{style}">{cell_content}</{tag}>'
            else:
                # Escape HTML for header rows
                html += f'<{tag} style="{style}">{cell_content}</{tag}>'
        html += '</tr>'
    html += '</table>'
    return html



# =============================================================================
# SECTION 4: MAIN EXPORT FUNCTION
# =============================================================================

def generate_html_content_only(
    analysis_record: Dict, 
    comparison: Dict, 
    user_info: Dict = None
) -> str:
    """Generate HTML content as string (for saving to file)"""
    data = EnhancedReportData(analysis_record, comparison, user_info)
    return _generate_html_content(data)

def _generate_html_content(data: EnhancedReportData) -> str:
    """Generate HTML content as string (without displaying)"""
    logger.info("Generating HTML content for report")
    
    # Generate visualizations
    dist_fig = create_competitor_distribution_chart(data)
    win_fig = create_win_probability_curve(data)
    radar_fig = create_risk_radar_chart(data)
    dashboard_fig = create_performance_dashboard(data)
    
    # Convert to base64
    dist_img = fig_to_base64(dist_fig)
    win_img = fig_to_base64(win_fig)
    radar_img = fig_to_base64(radar_fig)
    dashboard_img = fig_to_base64(dashboard_fig)
    
    # Generate detailed recommendation
    detailed_recommendation = data.generate_detailed_ai_recommendation()
    
    # PPR breakdown
    ppr_rows = data.get_ppr_breakdown_data()
    ppr_table_html = _generate_html_table(ppr_rows)
    
    # Status styling
    status_color = "#10b981" if data.is_ppr_compliant else "#ef4444"
    status_icon = "✅" if data.is_ppr_compliant else "⚠️"
    status_text = "COMPLIANT" if data.is_ppr_compliant else "SLT RISK"
    
    # Build NPPI info HTML if not default
    nppi_info_html = ""
    if hasattr(data, 'nppi_mode') and data.nppi_mode != 'Default':
        nppi_info_html = f"""
        <div style='background: #f0f9ff; padding: 0.5rem; border-radius: 8px; margin: 0.5rem 0;'>
            <small>📊 <strong>NPPI Configuration:</strong> {data.nppi_mode} | Factor: {data.nppi_factor:.4f}</small>
            {f"<small style='color: #e67e22;'> ⚠️ {data.nppi_warning}</small>" if data.nppi_warning else ""}
        </div>
        """
    
    # Competitor table
    comp_rows = [["#", "Competitor", "Bid Amount (BDT)", "% of Estimate", "Deviation"]]
    if data.competitor_bids_list:
        sorted_comp = sorted(zip(data.competitor_names, data.competitor_bids_list), key=lambda x: x[1])
        for i, (name, bid) in enumerate(sorted_comp, 1):
            pct = (bid / data.official_estimate * 100) if data.official_estimate > 0 else 0
            dev = ((bid - data.official_estimate) / data.official_estimate * 100) if data.official_estimate > 0 else 0
            highlight = "🏆 " if i == 1 else ""
            comp_rows.append([str(i), f"{highlight}{name}", f"{bid:,.3f}", f"{pct:.2f}%", f"{dev:+.2f}%"])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>TenderAI - Enhanced Analysis Report</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
            .report-container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ font-size: 32px; margin-bottom: 8px; }}
            .header p {{ font-size: 14px; opacity: 0.9; }}
            .content {{ padding: 30px; }}
            .section {{ margin-bottom: 35px; }}
            .section-title {{ font-size: 22px; font-weight: bold; color: #1e3a8a; border-left: 5px solid #3b82f6; padding-left: 15px; margin-bottom: 20px; }}
            .info-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; background: #f8fafc; padding: 20px; border-radius: 12px; }}
            .info-item {{ padding: 10px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .info-label {{ font-size: 12px; color: #64748b; margin-bottom: 5px; }}
            .info-value {{ font-size: 18px; font-weight: bold; color: #1e293b; }}
            .recommendation-box {{ background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-left: 5px solid #10b981; padding: 20px; border-radius: 12px; margin: 20px 0; line-height: 1.6; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background: #1e3a8a; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
            tr:hover {{ background: #f1f5f9; }}
            .viz-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
            .viz-card {{ background: #f8fafc; border-radius: 12px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .viz-card img {{ width: 100%; height: auto; border-radius: 8px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .stat-card {{ text-align: center; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; }}
            .stat-value {{ font-size: 28px; font-weight: bold; }}
            .stat-label {{ font-size: 12px; opacity: 0.9; margin-top: 5px; }}
            .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 11px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <h1>🤖 TenderAI</h1>
                <p>AI Enhanced Bid Management System • PPR 2025 Compliant</p>
                <small>Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')} | Analysis ID: {data.tender_id}</small>
            </div>
            
            <div class="content">
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-value">{len(data.competitor_bids_list)}</div><div class="stat-label">Competitors</div></div>
                    <div class="stat-card"><div class="stat-value">{data.win_probability*100:.0f}%</div><div class="stat-label">Win Probability</div></div>
                    <div class="stat-card"><div class="stat-value">BDT {data.recommended_bid:,.3f}</div><div class="stat-label">Recommended Bid</div></div>
                    <div class="stat-card"><div class="stat-value">{data.bid_ratio*100:.2f}%</div><div class="stat-label">of Estimate</div></div>
                </div>
                
                <div class="section">
                    <div class="section-title">📋 Tender Information</div>
                    <div class="info-grid">
                        <div class="info-item"><div class="info-label">Tender ID</div><div class="info-value">{data.tender_id}</div></div>
                        <div class="info-item"><div class="info-label">Procuring Entity</div><div class="info-value">{data.procuring_entity[:40]}</div></div>
                        <div class="info-item"><div class="info-label">Official Estimate</div><div class="info-value">BDT {data.official_estimate:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Procurement Type</div><div class="info-value">{data.procurement_type}</div></div>
                        <div class="info-item"><div class="info-label">Location</div><div class="info-value">{data.division} / {data.district}</div></div>
                        <div class="info-item"><div class="info-label">Risk Tolerance</div><div class="info-value">{data.risk_tolerance}</div></div>
                        <div class="info-item"><div class="info-label">SLT Threshold</div><div class="info-value">BDT {data.slt_threshold:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Compliance</div><div class="info-value"><span class="badge" style="background:{status_color}20; color:{status_color};">{status_icon} {status_text}</span></div></div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">🎯 AI Recommendation</div>
                    <div class="recommendation-box">
                        <strong>💡 Strategic Analysis:</strong><br>
                        {detailed_recommendation}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">📊 Visual Performance Dashboard</div>
                    <div class="viz-grid">
                        <div class="viz-card"><img src="data:image/png;base64,{dashboard_img}" alt="Performance Dashboard"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{radar_img}" alt="Risk Assessment"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{dist_img}" alt="Competitor Distribution"></div>
                        <div class="viz-card"><img src="data:image/png;base64,{win_img}" alt="Win Probability Curve"></div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">🔄 Three-Tier Analysis Comparison</div>
                    {_generate_html_table(data.get_tier_table_data())}
                </div>
                
                <div class="section">
                    <div class="section-title">👥 Competitor Intelligence ({len(data.competitor_bids_list)} competitors)</div>
                    {_generate_html_table(comp_rows)}
                </div>
                
                <div class="section">
                    <div class="section-title">📐 PPR 2025 Calculation Breakdown</div>
                    {nppi_info_html}
                    {ppr_table_html}
                </div>
                
                <div class="section">
                    <div class="section-title">💰 Financial Projections</div>
                    <div class="info-grid">
                        <div class="info-item"><div class="info-label">Estimated Cost</div><div class="info-value">BDT {data.estimated_cost:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Expected Profit</div><div class="info-value">BDT {data.expected_profit:,.3f}</div></div>
                        <div class="info-item"><div class="info-label">Win Probability</div><div class="info-value">{data.win_probability*100:.0f}%</div></div>
                        <div class="info-item"><div class="info-label">Expected Value</div><div class="info-value">BDT {data.expected_value:,.3f}</div></div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <strong>Disclaimer:</strong> This AI-generated analysis complies with Bangladesh PPR 2025 guidelines.<br>
                Final bidding decisions should consider project-specific risks, internal cost structures, and strategic objectives.
                {f"<br>Prepared for: {data.user_info.get('full_name', 'N/A')} | {data.user_info.get('company_name', 'N/A')}" if data.user_info else ""}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def generate_enhanced_report(
    analysis_record: Dict, 
    comparison: Dict, 
    user_info: Dict = None,
    format: str = 'both'
) -> Any:
    """
    Generate enhanced report with full visualizations and detailed analysis.
    
    Args:
        analysis_record: Analysis data from session state
        comparison: Three-tier comparison results
        user_info: User information (name, company)
        format: 'html', 'pdf', 'both', or 'html_buffer'
    
    Returns:
        - If format='html': Displays HTML in Streamlit, returns None
        - If format='html_buffer': Returns HTML as string/bytes
        - If format='pdf': Returns PDF buffer
        - If format='both': Displays HTML and returns PDF buffer
    """
    logger.info(f"Generating enhanced report in format: {format}")

    data = EnhancedReportData(analysis_record, comparison, user_info)
    
    pdf_buffer = None
    
    # Handle HTML display or buffer
    if format == 'html':
        # Display HTML in Streamlit
        html_content = _generate_html_content(data)
        st.components.v1.html(html_content, height=800, scrolling=True)
        return None
    
    elif format == 'html_buffer':
        # Return HTML as bytes for saving
        html_content = _generate_html_content(data)
        return html_content.encode('utf-8')
    
    elif format == 'pdf':
        # Return PDF buffer only
        try:
            pdf_buffer = generate_pdf_report(data)
            return pdf_buffer
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            return None
    
    elif format == 'both':
        # Display HTML and return PDF buffer
        html_content = _generate_html_content(data)
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        try:
            pdf_buffer = generate_pdf_report(data)
            return pdf_buffer
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            return None
    
    return None

import io
import traceback
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER

def generate_pdf_report(data: EnhancedReportData) -> io.BytesIO:
    """Generate Professional PDF Report - Fully Consistent Modern Design"""
    
    buffer = io.BytesIO()
    
    try:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=35, leftMargin=35,
            topMargin=30, bottomMargin=30
        )
        story = []
        styles = getSampleStyleSheet()

        # ====================== UNIFIED PROFESSIONAL TABLE STYLE ======================
        base_table_commands = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1e3a8a')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0,1), (-1,-1), 9),
            ('BOTTOMPADDING', (0,1), (-1,-1), 9),
            ('LEFTPADDING', (0,1), (-1,-1), 10),
            ('RIGHTPADDING', (0,1), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]

        # ====================== CUSTOM STYLES ======================
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=26,
                                     textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER, spaceAfter=6)
        subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12,
                                        textColor=colors.HexColor('#3b82f6'), alignment=TA_CENTER, spaceAfter=18)
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=18,
                                       textColor=colors.HexColor('#1e3a8a'), spaceBefore=18, spaceAfter=12,
                                       fontName='Helvetica-Bold')
        small_font_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7.5,
                                          textColor=colors.grey, leading=9, spaceBefore=2)
        normal_style = styles['Normal']

        def add_figure_to_story(fig, width=480, height=280):
            try:
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format='png', dpi=120, bbox_inches='tight')
                img_buffer.seek(0)
                img = Image(img_buffer, width=width, height=height)
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception:
                story.append(Paragraph("⚠️ Could not render chart.", normal_style))
            finally:
                plt.close(fig)

        # ====================== HEADER ======================
        story.append(Paragraph("🤖 TenderAI", title_style))
        story.append(Paragraph("AI Enhanced Bid Management System • PPR 2025 Compliant", subtitle_style))
        story.append(Paragraph(
            f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')} | Analysis ID: {data.tender_id}",
            ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER, fontSize=9, textColor=colors.grey)
        ))
        story.append(Spacer(1, 18))

        # ====================== QUICK STATISTICS ======================
        story.append(Paragraph("Quick Statistics", section_style))
        stats_data = [
            ["Competitors", f"{len(getattr(data, 'competitor_bids_list', []))}", 
             "Win Probability", f"{getattr(data, 'win_probability', 0)*100:.0f}%"],
            ["Recommended Bid", f"BDT {getattr(data, 'recommended_bid', 0):,.3f}", 
             "% of Estimate", f"{getattr(data, 'bid_ratio', 0)*100:.1f}%"],
        ]
        stats_table = Table(stats_data, colWidths=[1.5*inch]*4)
        stats_table.setStyle(TableStyle(base_table_commands))
        story.append(stats_table)
        story.append(Spacer(1, 18))

        # ====================== TENDER INFORMATION ======================
        story.append(Paragraph("📋 Tender Information", section_style))
        info_data = [
            ["Tender ID", data.tender_id, "Procurement Type", data.procurement_type],
            ["Procuring Entity", getattr(data, 'procuring_entity', '')[:50], 
             "Location", f"{getattr(data, 'division', '')} / {getattr(data, 'district', '')}"],
            ["Official Estimate", f"BDT {getattr(data, 'official_estimate', 0):,.3f}", 
             "Risk Tolerance", getattr(data, 'risk_tolerance', '')],
            ["SLT Threshold", f"BDT {getattr(data, 'slt_threshold', 0):,.3f}", "Compliance", 
             "✅ COMPLIANT" if getattr(data, 'is_ppr_compliant', False) else "⚠️ SLT RISK"],
        ]
        info_table = Table(info_data, colWidths=[1.4*inch, 1.9*inch, 1.4*inch, 1.9*inch])
        info_table.setStyle(TableStyle(base_table_commands))
        story.append(info_table)
        story.append(Spacer(1, 18))

        # ====================== AI RECOMMENDATION ======================
        story.append(Paragraph("🎯 AI Recommendation", section_style))
        detailed_rec = data.generate_detailed_ai_recommendation()
        story.append(Paragraph(detailed_rec, ParagraphStyle('Rec', parent=normal_style, fontSize=10.5, spaceAfter=10)))

        story.append(Paragraph("<b>📊 Key Insights:</b>", ParagraphStyle('Sub', parent=normal_style, fontSize=12, spaceAfter=6)))
        insights = [
            f"• Market Position: {getattr(data, 'market_position', 0):.1f}% competitive score",
            f"• Compliance Margin: {'+' if getattr(data, 'is_ppr_compliant', False) else ''}{getattr(data, 'compliance_margin', 0):.1f}% from SLT threshold",
            f"• Expected ROI: {(getattr(data, 'expected_profit', 0)/getattr(data, 'estimated_cost', 1)*100):.1f}% on investment" 
            if getattr(data, 'estimated_cost', 0) > 0 else "• Expected ROI: N/A"
        ]
        for insight in insights:
            story.append(Paragraph(insight, ParagraphStyle('Insight', parent=normal_style, fontSize=9.5, leftIndent=15, spaceAfter=3)))
        story.append(Spacer(1, 12))

        # ====================== VISUAL PERFORMANCE DASHBOARD ======================
        story.append(Paragraph("📊 Visual Performance Dashboard", section_style))
        try:
            dashboard_fig = create_performance_dashboard(data)
            add_figure_to_story(dashboard_fig, width=480, height=320)
            radar_fig = create_risk_radar_chart(data)
            add_figure_to_story(radar_fig, width=380, height=300)
            dist_fig = create_competitor_distribution_chart(data)
            add_figure_to_story(dist_fig, width=480, height=280)
            win_fig = create_win_probability_curve(data)
            add_figure_to_story(win_fig, width=480, height=280)
        except Exception as e:
            print(f"Chart Warning: {e}")
            story.append(Paragraph("Visualizations could not be generated.", normal_style))
        story.append(Spacer(1, 12))

        # ====================== THREE-TIER ANALYSIS ======================
        story.append(Paragraph("🔄 Three-Tier Analysis Comparison", section_style))
        tier_table_data = data.get_tier_table_data()
        tier_table = Table(tier_table_data, colWidths=[1.35*inch, 1.65*inch, 1.1*inch, 0.9*inch, 0.85*inch, 0.85*inch, 0.9*inch])
        tier_table.setStyle(TableStyle(base_table_commands))
        story.append(tier_table)
        story.append(Spacer(1, 18))

        # ====================== COMPETITOR INTELLIGENCE ======================
        story.append(Paragraph(f"👥 Competitor Intelligence ({len(getattr(data, 'competitor_bids_list', []))} competitors)", section_style))
        
        if getattr(data, 'competitor_bids_list', None):
            sorted_comp = sorted(zip(data.competitor_names, data.competitor_bids_list), key=lambda x: x[1])
            comp_rows = [["#", "Competitor", "Bid Amount (BDT)", "% of Estimate", "Deviation"]]
            for i, (name, bid) in enumerate(sorted_comp, 1):
                pct = (bid / data.official_estimate * 100) if data.official_estimate > 0 else 0
                dev = ((bid - data.official_estimate) / data.official_estimate * 100) if data.official_estimate > 0 else 0
                prefix = "🏆 " if i == 1 else ""
                comp_rows.append([str(i), f"{prefix}{name[:28]}", f"{bid:,.3f}", f"{pct:.2f}%", f"{dev:+.2f}%"])
            
            comp_table = Table(comp_rows, colWidths=[0.5*inch, 1.9*inch, 1.3*inch, 1.0*inch, 1.0*inch])
            comp_table.setStyle(TableStyle(base_table_commands))
            story.append(comp_table)

            story.append(Spacer(1, 8))
            stats_grid_data = [
                ["Lowest Bid", f"BDT {data.competitor_stats.get('min', 0):,.3f}", 
                 "Highest Bid", f"BDT {data.competitor_stats.get('max', 0):,.3f}"],
                ["Average Bid", f"BDT {data.competitor_stats.get('mean', 0):,.3f}", 
                 "Std Deviation", f"BDT {data.competitor_stats.get('std', 0):,.3f}"],
            ]
            stats_grid = Table(stats_grid_data, colWidths=[1.4*inch, 1.7*inch, 1.4*inch, 1.7*inch])
            stats_grid.setStyle(TableStyle(base_table_commands))
            story.append(stats_grid)
        else:
            story.append(Paragraph("No competitor data provided.", normal_style))
        story.append(Spacer(1, 18))

        # ====================== PPR 2025 CALCULATION BREAKDOWN ======================
        story.append(Paragraph("📐 PPR 2025 Calculation Breakdown", section_style))

        # Add NPPI Configuration info if not default (for PDF)
        if hasattr(data, 'nppi_mode') and data.nppi_mode != 'Default':
            nppi_config_text = f"<b>NPPI Configuration:</b> {data.nppi_mode} | Factor: {data.nppi_factor:.4f}"
            if data.nppi_warning:
                nppi_config_text += f" ⚠️ {data.nppi_warning}"
            story.append(Paragraph(nppi_config_text, ParagraphStyle('NPPIInfo', parent=normal_style, fontSize=9, textColor=colors.HexColor('#2563eb'), spaceAfter=8)))
            story.append(Spacer(1, 4))

        nppi_price = data.official_estimate * data.nppi_factor
        weighted_avg_full = getattr(data, 'weighted_avg', 0)
        weighted_std_full = getattr(data, 'weighted_std', 0)
        slt_threshold_full = getattr(data, 'slt_threshold', 0)

        # Create a small font style for the formula descriptions
        small_font_style = ParagraphStyle('Small', parent=normal_style, fontSize=8, leading=10)

        ppr_breakdown = [
            ["Step", "Formula / Description", "Calculation", "Result"],
            ["1", Paragraph("Official Estimate<br/><font color='#666666'>From tender document</font>", small_font_style),
            f"BDT {data.official_estimate:,.3f}", "Base Value"],
            
            ["2", Paragraph("NPPI Factor<br/><font color='#666666'>28-day market average</font>", small_font_style),
            f"{data.nppi_factor:.3f}", "Index Factor"],
            
            ["3", Paragraph("NPPI Price<br/><font color='#666666'>Estimate × NPPI Factor</font>", small_font_style),
            f"{data.official_estimate:,.0f} × {data.nppi_factor:.3f}", f"BDT {nppi_price:,.3f}"],
            
            ["4", Paragraph("Avg Competitor<br/><font color='#666666'>Σ(Comp Bids) ÷ N</font>", small_font_style),
            f"({len(getattr(data, 'competitor_bids_list', []))} bids)", f"BDT {getattr(data, 'avg_competitor', 0):,.3f}"],
            
            ["5", Paragraph("Weighted Avg (X̄)<br/><font color='#666666'>0.5(Avg) + 0.2(Est) + 0.3(NPPI)</font>", small_font_style),
            Paragraph(f"0.5×{getattr(data, 'avg_competitor', 0):,.0f}<br/>"
                    f"+ 0.2×{data.official_estimate:,.0f}<br/>"
                    f"+ 0.3×{nppi_price:,.0f}",
                    ParagraphStyle('Calc', parent=normal_style, fontSize=8, leading=10)),
            f"BDT {weighted_avg_full:,.3f}"],
            
            ["6", Paragraph("Std Deviation (Sd)<br/><font color='#666666'>√[Σ(x̄ - xᵢ)²/(n-1)]</font>", small_font_style),
            f"σ = {weighted_std_full:,.3f}", f"BDT {weighted_std_full:,.3f}"],
            
            ["7", Paragraph("SLT Threshold<br/><font color='#666666'>X̄ - Sd</font>", small_font_style),
            f"{weighted_avg_full:,.0f} - {weighted_std_full:,.0f}", f"BDT {slt_threshold_full:,.3f}"],
            
            ["8", Paragraph("Recommended Bid<br/><font color='#666666'>AI Optimized</font>", small_font_style),
            "Based on win probability", f"BDT {data.recommended_bid:,.3f}"],
            
            ["9", Paragraph("Compliance Check<br/><font color='#666666'>Bid ≥ SLT?</font>", small_font_style),
            f"{data.recommended_bid:,.0f} ≥ {slt_threshold_full:,.0f}",
            Paragraph(f"<b><font color='{'green' if getattr(data, 'is_ppr_compliant', False) else 'red'}'>"
                    f"{'✅ PASS' if getattr(data, 'is_ppr_compliant', False) else '❌ FAIL'}</font></b>", normal_style)],
        ]

        breakdown_table = Table(ppr_breakdown, colWidths=[0.5*inch, 1.95*inch, 2.15*inch, 1.3*inch], repeatRows=1)
        breakdown_table.setStyle(TableStyle(base_table_commands + [
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ALIGN', (0,1), (0,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'),
            ('ALIGN', (2,1), (2,-1), 'LEFT'),
            ('ALIGN', (3,1), (3,-1), 'RIGHT'),
            ('BACKGROUND', (0,-1), (-1,-1), 
            colors.HexColor('#ecfdf5') if getattr(data, 'is_ppr_compliant', False) else colors.HexColor('#fef2f2')),
        ]))
        story.append(breakdown_table)
        story.append(Spacer(1, 18))


        # ====================== FINANCIAL PROJECTIONS ======================
        story.append(Paragraph("💰 Financial Projections", section_style))
        fin_data = [
            ["Metric", "Value", "Interpretation"],
            ["Estimated Cost", f"BDT {getattr(data, 'estimated_cost', 0):,.3f}", "85% of official estimate"],
            ["Expected Profit", f"BDT {getattr(data, 'expected_profit', 0):,.3f}", "If bid wins"],
            ["Win Probability", f"{getattr(data, 'win_probability', 0)*100:.0f}%", "Statistical likelihood"],
            ["Expected Value", f"BDT {getattr(data, 'expected_value', 0):,.3f}", "Profit × Win Probability"]
        ]
        fin_table = Table(fin_data, colWidths=[1.6*inch, 1.6*inch, 2.4*inch])
        fin_table.setStyle(TableStyle(base_table_commands))
        story.append(fin_table)
        story.append(Spacer(1, 25))

        # ====================== DISCLAIMER ======================
        disclaimer = Paragraph(
            "<b>Disclaimer:</b> This AI-generated analysis complies with Bangladesh PPR 2025 guidelines. "
            "Final bidding decisions should consider project-specific risks, internal cost structures, "
            "and strategic objectives.",
            ParagraphStyle('Disc', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=12)
        )
        story.append(disclaimer)

        if getattr(data, 'user_info', None) and data.user_info.get('full_name'):
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"Prepared for: {data.user_info.get('full_name')} | {data.user_info.get('company_name', 'N/A')}",
                ParagraphStyle('Foot', parent=normal_style, fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
            ))

        # ====================== BUILD ======================
        doc.build(story)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print("=== PDF Generation Failed ===")
        print(traceback.format_exc())
        error_buffer = io.BytesIO()
        error_doc = SimpleDocTemplate(error_buffer, pagesize=A4)
        error_doc.build([Paragraph(f"<b>PDF Generation Failed</b><br/>Error: {str(e)}", normal_style)])
        error_buffer.seek(0)
        return error_buffer
 
# Compatibility wrapper
def generate_unified_report(analysis_record, comparison, user_info, format='both'):
    """Compatibility wrapper for generate_enhanced_report"""
    return generate_enhanced_report(analysis_record, comparison, user_info, format)
        

print("=== report_generator.py loaded ===")
print(f"Available functions: {[x for x in dir() if not x.startswith('_')]}")
