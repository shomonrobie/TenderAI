"""
TenderAI Price-to-Win Simulator Module
PPR 2025 Compliant - AI-powered bid optimization
"""

import numpy as np
import pandas as pd
from datetime import datetime
import random
import json
import base64
import streamlit as st
from typing import Dict, List, Optional, Tuple, Any


from modules.advanced_bid_optimizer import (
    calculate_optimal_bid_ppr2025,
    calculate_advanced_ppr_analysis,
    get_three_tier_comparison,
    _extract_bid_values
)

from modules.rbac import (
    can_access_scenario_generator,
    can_generate_scenarios,
    can_export_scenarios,
    get_user_role,
    render_role_badge,
    can_export_data
)

from modules.competitive_bid_simulator_html_report_generator import HTMLReportGenerator
from modules.subscription_manager import SubscriptionManager, check_subscription_access


class PriceToWinSimulator:
    """Price-to-Win Simulator - Generate optimal bid price with competitor scenarios."""
    
    def __init__(self, official_estimate, procurement_type='goods', 
                 min_price_pct=0.88, max_price_pct=1.08, random_seed=42):
        self.official_estimate = float(official_estimate)
        self.procurement_type = procurement_type
        self.min_price_pct = min_price_pct
        self.max_price_pct = max_price_pct
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        self.market_params = {
            'goods': {'skew': -0.3, 'peak': 0.94},
            'works': {'skew': -0.2, 'peak': 0.92},
            'services': {'skew': -0.1, 'peak': 0.95}
        }
    
    def _generate_competitor_bids(self, num_competitors, pattern='realistic'):
        """Generate random competitor bids within user-defined range."""
        min_bid = self.official_estimate * self.min_price_pct
        max_bid = self.official_estimate * self.max_price_pct
        
        if pattern == 'uniform':
            bids = np.random.uniform(min_bid, max_bid, num_competitors)
        elif pattern == 'realistic':
            params = self.market_params.get(self.procurement_type, {'peak': 0.94})
            peak_ratio = params['peak']
            range_width = self.max_price_pct - self.min_price_pct
            normalized_peak = (peak_ratio - self.min_price_pct) / range_width
            normalized_peak = np.clip(normalized_peak, 0.2, 0.8)
            alpha = 4.0
            beta = 3.0
            ratios = np.random.beta(alpha, beta, num_competitors)
            scaled_ratios = self.min_price_pct + ratios * range_width
            bids = self.official_estimate * scaled_ratios
        elif pattern == 'aggressive':
            ratios = np.random.triangular(self.min_price_pct, 
                                         self.min_price_pct + 0.02,
                                         self.min_price_pct + 0.08, 
                                         num_competitors)
            bids = self.official_estimate * ratios
        elif pattern == 'conservative':
            mean_ratio = min(0.98, self.max_price_pct - 0.02)
            std_ratio = 0.025
            ratios = np.random.normal(mean_ratio, std_ratio, num_competitors)
            ratios = np.clip(ratios, self.min_price_pct, self.max_price_pct)
            bids = self.official_estimate * ratios
        else:
            bids = np.random.uniform(min_bid, max_bid, num_competitors)
        
        return [round(b, 3) for b in bids]
    
    def generate_scenarios(self, competitor_counts, pattern='realistic'):
        """Generate multiple scenarios with user-specified competitor counts."""
        results = []
        
        for i, num_comps in enumerate(competitor_counts, 1):
            competitor_bids = self._generate_competitor_bids(num_comps, pattern)
            
            optimization_result = calculate_optimal_bid_ppr2025(
                official_estimate=self.official_estimate,
                competitor_bids=competitor_bids,
                procurement_type=self.procurement_type,
                risk_tolerance='moderate'
            )
            
            advanced_result = calculate_advanced_ppr_analysis(
                official_estimate=self.official_estimate,
                competitor_bids=competitor_bids,
                procurement_type=self.procurement_type,
                risk_tolerance='moderate'
            )
            
            bid_values = _extract_bid_values(competitor_bids)
            
            scenario = {
                'scenario_id': i,
                'num_competitors': num_comps,
                'competitor_bids': competitor_bids,
                'optimized_bid': optimization_result['optimal_bid'],
                'bid_ratio': optimization_result['bid_ratio'],
                'win_probability': optimization_result['win_probability'],
                'risk_level': optimization_result['risk_level'],
                'risk_color': optimization_result['risk_color'],
                'slt_threshold': optimization_result['slt_threshold'],
                'nppi_factor': optimization_result['nppi_factor'],
                'expected_profit': optimization_result.get('expected_profit', 0),
                'competitor_stats': {
                    'min': min(bid_values) if bid_values else 0,
                    'max': max(bid_values) if bid_values else 0,
                    'mean': np.mean(bid_values) if bid_values else 0,
                    'median': np.median(bid_values) if bid_values else 0,
                    'std': np.std(bid_values) if bid_values else 0
                },
                'advanced_metrics': {
                    'weighted_average': advanced_result.get('weighted_average', 0),
                    'weighted_std_dev': advanced_result.get('weighted_std_dev', 0),
                    'nppi_price': advanced_result.get('nppi_price', 0),
                    'avg_competitor': advanced_result.get('avg_competitor', 0)
                }
            }
            
            results.append(scenario)
        
        return results
    
    def get_ai_recommended_bid(self, scenarios, strategy='weighted_ensemble'):
        """Calculate AI-recommended bid price based on all scenarios."""
        if not scenarios:
            return {'recommended_bid': self.official_estimate * 0.92, 'confidence': 0.5}
        
        optimal_bids = [s['optimized_bid'] for s in scenarios]
        win_probs = [s['win_probability'] for s in scenarios]
        num_comps = [s['num_competitors'] for s in scenarios]
        
        if strategy == 'weighted_ensemble':
            weights = []
            for i, s in enumerate(scenarios):
                w = np.sqrt(s['num_competitors']) * s['win_probability']
                weights.append(w)
            
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
                recommended_bid = sum(b * w for b, w in zip(optimal_bids, normalized_weights))
            else:
                recommended_bid = np.mean(optimal_bids)
        elif strategy == 'conservative':
            recommended_bid = max(optimal_bids)
        elif strategy == 'aggressive':
            recommended_bid = min(optimal_bids)
        elif strategy == 'statistical':
            mean_bid = np.mean(optimal_bids)
            std_bid = np.std(optimal_bids)
            recommended_bid = mean_bid - (0.5 * std_bid)
        elif strategy == 'ml_style':
            if len(num_comps) > 1:
                slope, intercept = np.polyfit(num_comps, optimal_bids, 1)
                avg_comps = np.mean(num_comps)
                recommended_bid = slope * avg_comps + intercept
            else:
                recommended_bid = optimal_bids[0]
        else:
            recommended_bid = np.mean(optimal_bids)
        
        min_allowed = self.official_estimate * self.min_price_pct
        max_allowed = self.official_estimate * self.max_price_pct
        recommended_bid = np.clip(recommended_bid, min_allowed, max_allowed)
        
        bid_std = np.std(optimal_bids)
        relative_std = bid_std / self.official_estimate
        confidence = max(0.5, min(0.95, 1.0 - (relative_std * 2)))
        
        avg_win_prob = np.mean(win_probs)
        bid_ratio = recommended_bid / self.official_estimate
        
        if bid_ratio < 0.89:
            adjusted_win_prob = min(0.95, avg_win_prob * 1.15)
        elif bid_ratio > 0.94:
            adjusted_win_prob = max(0.35, avg_win_prob * 0.85)
        else:
            adjusted_win_prob = avg_win_prob
        
        return {
            'recommended_bid': round(recommended_bid, 3),
            'bid_ratio': round(recommended_bid / self.official_estimate, 4),
            'confidence_score': round(confidence, 4),
            'expected_win_probability': round(adjusted_win_prob, 4),
            'strategy_used': strategy,
            'scenario_count': len(scenarios),
            'bid_range': (round(min(optimal_bids), 3), round(max(optimal_bids), 3)),
            'bid_std_dev': round(bid_std, 3),
            'reasoning': self._generate_recommendation_reasoning(scenarios, recommended_bid)
        }
    
    def _generate_recommendation_reasoning(self, scenarios, recommended_bid):
        """Generate human-readable reasoning."""
        optimal_bids = [s['optimized_bid'] for s in scenarios]
        num_comps_list = [s['num_competitors'] for s in scenarios]
        
        return f"""
Based on analysis of {len(scenarios)} scenarios with {min(num_comps_list)} to {max(num_comps_list)} competitors:

• Recommended bid: BDT {recommended_bid:,.3f} ({((recommended_bid/self.official_estimate)*100):.1f}% of OCE)
• Scenario optimal bids ranged from BDT {min(optimal_bids):,.3f} to BDT {max(optimal_bids):,.3f}
• All calculations comply with PPR 2025 SLT evaluation criteria
"""


def get_tenders_for_company(db, company_id, search_term=""):
    """Get tenders for a company."""
    try:
        conn = db.get_connection()
        query = """
            SELECT id, tender_id, tender_title, official_estimate, procurement_type
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
        """
        params = [company_id]
        if search_term:
            query += " AND (tender_id LIKE ? OR tender_title LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        query += " ORDER BY created_at DESC LIMIT 50"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except:
        return pd.DataFrame()


def render_competitive_bid_simulator_ui(db=None, subscription_manager=None):
    """Main UI function."""
    
    st.markdown("## 🎯 Price-to-Win Simulator")
    st.markdown("*AI-powered bid optimization with competitor scenario analysis*")
    
    render_role_badge()
    
    # Access checks
    user_role = get_user_role()
    if not can_access_scenario_generator():
        st.error("🔒 Access Denied")
        return
    
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    
    has_subscription, current_plan, sub_msg = check_subscription_access(company_id, subscription_manager)
    if not has_subscription and user_role != 'system_admin':
        st.warning("🔒 Premium Feature")
        st.error(sub_msg)
        return
    
    st.success(f"✅ Access Granted - {current_plan.upper()} Plan" if current_plan != 'system_admin' else "✅ System Admin Access")
    
    can_generate = can_generate_scenarios()
    
    # Tender selection
    st.markdown("### 📋 Select Tender")
    
    search_term = st.text_input("🔍 Search Tender", placeholder="Enter tender ID or title...")
    tenders_df = get_tenders_for_company(db, company_id, search_term)
    
    if tenders_df.empty:
        st.info("No tenders found. Please add tenders in Tender Management.")
        official_estimate = st.number_input("OCE - BDT", min_value=10000.0, value=7500000.0, step=100000.0, format="%.3f")
        procurement_type = st.selectbox("Procurement Type", ['goods', 'works', 'services'], index=1)
        selected_tender_id = None
        tender_title = "Manual Entry"
        procuring_entity = "Manual Entry"
        division = "Dhaka"
        district = "Dhaka"
    else:
        st.dataframe(tenders_df[['id', 'tender_id', 'tender_title', 'official_estimate']], use_container_width=True, hide_index=True)
        selected = st.selectbox("Select Tender", tenders_df.to_dict('records'), format_func=lambda x: f"{x['tender_id']} - {x['tender_title'][:50]}")
        official_estimate = selected['official_estimate']
        procurement_type = selected.get('procurement_type', 'works')
        selected_tender_id = selected['id']
        tender_title = selected['tender_title']
        procuring_entity = selected.get('procuring_entity', 'N/A')
        division = selected.get('division', 'Dhaka')
        district = selected.get('district', 'Dhaka')
    
    # Configuration
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        min_price_pct = st.number_input("Min Bid (% of OCE)", 70, 95, 88, 1) / 100.0
    with col2:
        max_price_pct = st.number_input("Max Bid (% of OCE)", 102, 120, 108, 1) / 100.0
    
    if min_price_pct >= max_price_pct:
        st.error("❌ Minimum must be less than maximum")
        return
    
    # Scenario setup
    scenario_type = st.radio("Scenario Setup", ["Default (9 scenarios)", "Custom"], horizontal=True)
    
    if scenario_type == "Default (9 scenarios)":
        competitor_counts = [5, 6, 7, 8, 10, 12, 14, 16, 19]
        st.info(f"Generating {len(competitor_counts)} scenarios with counts: {competitor_counts}")
    else:
        col1, col2 = st.columns(2)
        with col1:
            min_comp = st.number_input("Min Competitors", 1, 50, 5)
        with col2:
            max_comp = st.number_input("Max Competitors", min_comp+1, 100, 19)
        num_scenarios = st.slider("Number of Scenarios", 1, 20, 9)
        competitor_counts = sorted(set(np.linspace(min_comp, max_comp, num_scenarios, dtype=int)))
        st.success(f"Generating {len(competitor_counts)} scenarios")
    
    pattern = st.selectbox("Bidding Pattern", ['realistic', 'aggressive', 'conservative', 'uniform'], index=0)
    ai_strategy = st.selectbox("AI Strategy", ['weighted_ensemble', 'conservative', 'aggressive', 'statistical', 'ml_style'], index=0)
    
    with st.expander("Advanced"):
        random_seed = st.number_input("Random Seed", 1, 9999, 42)
        risk_tolerance = st.select_slider("Risk Tolerance", ['conservative', 'moderate', 'aggressive'], value='moderate')
    
    # Generate button
    if st.button("🚀 Generate Analysis", type="primary", use_container_width=True, disabled=not can_generate):
        with st.spinner("Generating scenarios and optimizing bid..."):
            generator = PriceToWinSimulator(
                official_estimate=official_estimate,
                procurement_type=procurement_type,
                min_price_pct=min_price_pct,
                max_price_pct=max_price_pct,
                random_seed=random_seed
            )
            
            scenarios = generator.generate_scenarios(competitor_counts, pattern)
            recommendation = generator.get_ai_recommended_bid(scenarios, ai_strategy)
            
            # Build scenario summaries for report
            scenario_summary = []
            scenarios_full = []
            
            for s in scenarios:
                scenario_summary.append({
                    'scenario_id': s['scenario_id'],
                    'num_competitors': s['num_competitors'],
                    'optimized_bid': s['optimized_bid'],
                    'bid_ratio': s['bid_ratio'],
                    'win_probability': s['win_probability'],
                    'risk_level': s['risk_level'],
                    'expected_profit': s['expected_profit'],
                    'slt_threshold': s['slt_threshold']
                })
                scenarios_full.append({
                    'scenario_id': s['scenario_id'],
                    'num_competitors': s['num_competitors'],
                    'competitor_bids': s['competitor_bids'],
                    'optimized_bid': s['optimized_bid'],
                    'bid_ratio': s['bid_ratio'],
                    'win_probability': s['win_probability'],
                    'risk_level': s['risk_level'],
                    'risk_color': s['risk_color'],
                    'slt_threshold': s['slt_threshold'],
                    'expected_profit': s['expected_profit'],
                    'competitor_stats': s['competitor_stats']
                })
            
            # Get tier comparison
            tier_comparison = get_three_tier_comparison(
                official_estimate=official_estimate,
                competitor_bids=scenarios[0]['competitor_bids'] if scenarios else [],
                procurement_type=procurement_type,
                risk_tolerance=risk_tolerance,
                nppi_factor=scenarios[0]['nppi_factor'] if scenarios else 0.92
            )
            
            # Build competitor bids list
            competitor_bids_list = []
            if scenarios:
                for i, bid in enumerate(scenarios[0]['competitor_bids'][:20], 1):
                    competitor_bids_list.append({'name': f'Competitor {i}', 'bid': bid})
            
            # Complete analysis data
            analysis_data = {
                'tender_id': selected_tender_id or str(int(datetime.now().timestamp())),
                'tender_title': tender_title,
                'procuring_entity': procuring_entity,
                'division': division,
                'district': district,
                'official_estimate': official_estimate,
                'procurement_type': procurement_type,
                'risk_tolerance': risk_tolerance.capitalize(),
                'slt_threshold': scenarios[0]['slt_threshold'] if scenarios else official_estimate * 0.85,
                'recommended_bid': recommendation['recommended_bid'],
                'win_probability': recommendation['expected_win_probability'],
                'risk_level': recommendation['strategy_used'],
                'competitor_count': max(competitor_counts) if competitor_counts else 0,
                'nppi_factor': scenarios[0]['nppi_factor'] if scenarios else 0.92,
                'avg_competitor': scenarios[0]['competitor_stats']['mean'] if scenarios else official_estimate * 0.92,
                'weighted_average': scenarios[0]['advanced_metrics']['weighted_average'] if scenarios else official_estimate * 0.94,
                'weighted_std_dev': scenarios[0]['advanced_metrics']['weighted_std_dev'] if scenarios else official_estimate * 0.03,
                'estimated_cost': official_estimate * 0.85,
                'bid_ratio': recommendation['bid_ratio'],
                'confidence_score': recommendation['confidence_score'],
                'ai_strategy': ai_strategy,
                'tier_comparison': tier_comparison,
                'competitor_bids': competitor_bids_list,
                'scenarios': scenario_summary,
                'scenarios_full': scenarios_full,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            st.session_state.analysis_data = analysis_data
            st.session_state.scenarios = scenarios
            st.session_state.recommendation = recommendation
            st.session_state.analysis_generated = True
    
    # Display results
    if st.session_state.get('analysis_generated'):
        analysis_data = st.session_state.analysis_data
        recommendation = st.session_state.recommendation
        scenarios = st.session_state.scenarios
        
        # Display recommendation
        st.markdown("---")
        st.markdown("## 🤖 AI Recommendation")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Recommended Bid", f"BDT {recommendation['recommended_bid']:,.3f}", f"{recommendation['bid_ratio']*100:.1f}% of OCE")
        with col2:
            st.metric("Win Probability", f"{recommendation['expected_win_probability']*100:.0f}%")
        with col3:
            st.metric("Confidence Score", f"{recommendation['confidence_score']*100:.0f}%")
        with col4:
            st.metric("Strategy", recommendation['strategy_used'].replace('_', ' ').title())
        
        # Scenarios table
        st.markdown("## 📈 Scenario Results")
        df_scenarios = pd.DataFrame([{
            'Scenario': s['scenario_id'],
            'Competitors': s['num_competitors'],
            'Optimal Bid': f"BDT {s['optimized_bid']:,.3f}",
            'Win Prob': f"{s['win_probability']*100:.0f}%",
            'Risk': s['risk_level']
        } for s in scenarios])
        st.dataframe(df_scenarios, use_container_width=True, hide_index=True)
        
        # Export section
        from modules.competitive_bid_simulator_html_report_generator import render_report_section
        render_report_section(analysis_data)


if __name__ == "__main__":
    print("✅ Price-to-Win Simulator loaded successfully")