"""
TenderAI Bid Scenario Generator Module
PPR 2025 Compliant - User-configurable competitor scenarios
WITH DATABASE INTEGRATION - Company/User Isolation
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import random
import json
import warnings
import streamlit as st
warnings.filterwarnings('ignore')
import xlsxwriter

from modules.advanced_bid_optimizer import (
    calculate_optimal_bid_ppr2025,
    calculate_advanced_ppr_analysis,
    _extract_bid_values
)

from modules.rbac import (
    can_access_scenario_generator,
    can_generate_scenarios,
    can_export_scenarios,
    get_user_role,
    render_role_badge
)
from modules.tender_selector import render_tender_selector
from modules.subscription_manager import SubscriptionManager, check_subscription_access


class BidScenarioGenerator:
    """Generate multiple scenarios with user-configurable parameters."""
    
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
        """Generate human-readable reasoning for the recommendation."""
        optimal_bids = [s['optimized_bid'] for s in scenarios]
        num_comps_list = [s['num_competitors'] for s in scenarios]
        
        reasoning = f"""
Based on analysis of {len(scenarios)} scenarios with {min(num_comps_list)} to {max(num_comps_list)} competitors:

• The recommended bid of BDT {recommended_bid:,.3f} represents {((recommended_bid/self.official_estimate)*100):.1f}% of the official estimate
• Scenario optimal bids ranged from BDT {min(optimal_bids):,.3f} to BDT {max(optimal_bids):,.3f}
• The recommendation balances win probability and profit margin
• More competitors generally require more aggressive pricing
• All calculations comply with PPR 2025 SLT evaluation criteria
"""
        return reasoning.strip()


def get_tenders_for_company(db, company_id, search_term=""):
    """Get tenders for a company with search."""
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
    except Exception as e:
        print(f"Error getting tenders: {e}")
        return pd.DataFrame()


def render_saved_scenarios_view(db, company_id, user_id):
    """Render the saved scenarios view with company/user isolation."""
    st.markdown("## 📚 Saved Scenarios")
    
    # Tab for different views
    tab1, tab2, tab3 = st.tabs(["My Scenarios", "Favorite Scenarios", "Shared with Me"])
    
    with tab1:
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Search scenarios", placeholder="Search by name...", key="search_scenarios")
        with col2:
            refresh = st.button("🔄 Refresh", use_container_width=True, key="refresh_scenarios")
        
        # Pagination
        if 'scenario_page' not in st.session_state:
            st.session_state.scenario_page = 0
        items_per_page = 10
        
        # Get scenarios for this user/company
        scenarios, total = db.get_user_scenarios(
            company_id=company_id,
            user_id=user_id,  # Filter by user - each user sees their own scenarios
            limit=items_per_page,
            offset=st.session_state.scenario_page * items_per_page,
            search=search_term
        )
        
        if not scenarios:
            st.info("No saved scenarios found. Generate and save a scenario to see it here.")
        else:
            st.caption(f"Showing {len(scenarios)} of {total} scenarios")
            
            for scenario in scenarios:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{scenario['scenario_name']}**")
                        st.caption(f"Created: {scenario['created_at'][:16] if scenario['created_at'] else 'N/A'}")
                    
                    with col2:
                        st.markdown(f"OCE: BDT {scenario['official_estimate']:,.3f}")
                        st.markdown(f"Recommended: BDT {scenario['recommended_bid']:,.3f}")
                    
                    with col3:
                        win_prob = scenario.get('expected_win_probability', 0) or 0.5
                        st.metric("Win Prob.", f"{win_prob*100:.0f}%")
                        st.caption(f"Confidence: {scenario['confidence_score']*100:.0f}%")
                    
                    with col4:
                        # View button
                        if st.button("👁️ View", key=f"view_{scenario['id']}", use_container_width=True):
                            st.session_state.view_scenario_id = scenario['id']
                            st.rerun()
                        
                        # Favorite button
                        fav_text = "⭐" if scenario.get('is_favorite') else "☆"
                        if st.button(fav_text, key=f"fav_{scenario['id']}", help="Favorite"):
                            db.toggle_favorite_scenario(scenario['id'], company_id, not scenario.get('is_favorite'))
                            st.rerun()
                    
                    st.markdown("---")
            
            # Pagination controls
            if total > items_per_page:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if st.button("◀ Previous", disabled=st.session_state.scenario_page == 0):
                        st.session_state.scenario_page -= 1
                        st.rerun()
                with col2:
                    st.markdown(f"<div style='text-align: center'>Page {st.session_state.scenario_page + 1} of {(total + items_per_page - 1) // items_per_page}</div>", unsafe_allow_html=True)
                with col3:
                    if st.button("Next ▶", disabled=(st.session_state.scenario_page + 1) * items_per_page >= total):
                        st.session_state.scenario_page += 1
                        st.rerun()
    
    with tab2:
        # Favorite scenarios only
        fav_scenarios, fav_total = db.get_user_scenarios(
            company_id=company_id,
            user_id=user_id,
            is_favorite=True,
            limit=50
        )
        
        if not fav_scenarios:
            st.info("No favorite scenarios. Star a scenario to add it to favorites.")
        else:
            for scenario in fav_scenarios:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{scenario['scenario_name']}**")
                with col2:
                    st.markdown(f"Recommended: BDT {scenario['recommended_bid']:,.3f}")
                with col3:
                    if st.button("👁️ View", key=f"fav_view_{scenario['id']}"):
                        st.session_state.view_scenario_id = scenario['id']
                        st.rerun()
                st.markdown("---")
    
    with tab3:
        st.info("Shared scenarios will appear here (coming soon)")


def render_scenario_detail_view(db, scenario_id, company_id):
    """Render detailed view of a saved scenario."""
    scenario = db.get_scenario_by_id(scenario_id, company_id)
    
    if not scenario:
        st.error("Scenario not found or access denied")
        if st.button("← Back to Scenarios"):
            st.session_state.pop('view_scenario_id', None)
            st.rerun()
        return
    
    # Back button
    if st.button("← Back to Saved Scenarios"):
        st.session_state.pop('view_scenario_id', None)
        st.rerun()
    
    st.markdown(f"## 📊 {scenario['scenario_name']}")
    st.caption(f"Created: {scenario['created_at']} | Views: {scenario.get('view_count', 0)}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Official Estimate", f"BDT {scenario['official_estimate']:,.3f}")
    with col2:
        st.metric("Recommended Bid", f"BDT {scenario['recommended_bid']:,.3f}")
    with col3:
        st.metric("Bid Ratio", f"{scenario['bid_ratio']*100:.1f}%")
    with col4:
        st.metric("Confidence", f"{scenario['confidence_score']*100:.1f}%")
    
    # Scenarios table
    scenarios_data = scenario.get('scenarios_data', [])
    if scenarios_data:
        df = pd.DataFrame(scenarios_data)
        st.markdown("### 📈 Scenario Results")
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Share options
    with st.expander("🔗 Share this Scenario"):
        email = st.text_input("Share with email", placeholder="colleague@company.com")
        permission = st.selectbox("Permission", ['view', 'edit'], index=0)
        if st.button("Generate Share Link"):
            token = db.share_scenario(scenario_id, st.session_state.user_id, email, permission)
            if token:
                share_url = f"{st.get_option('server.baseUrlPath')}/shared_scenario?token={token}"
                st.code(share_url, language="text")
                st.caption("Copy this link to share with others")
    
    # Delete button
    if st.button("🗑️ Delete Scenario", type="secondary"):
        if db.delete_scenario(scenario_id, company_id):
            st.success("Scenario deleted successfully")
            st.session_state.pop('view_scenario_id', None)
            st.rerun()
def render_bid_scenario_generator_ui(db=None, subscription_manager=None):
    """
    Render the Bid Scenario Generator UI with RBAC + Subscription checks.
    """
    # Check if we're viewing a saved scenario
    if st.session_state.get('view_scenario_id'):
        render_scenario_detail_view(db, st.session_state.view_scenario_id, st.session_state.company_id)
        return
    
    # Check if we're viewing saved scenarios list
    if st.session_state.get('page') == 'saved_scenarios':
        render_saved_scenarios_view(db, st.session_state.company_id, st.session_state.user_id)
        return
    
    st.markdown("## 🎲 Bid Scenario Generator")
    st.markdown("*Generate multiple competitor scenarios with AI-powered bid recommendations*")
    
    # Add link to saved scenarios
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        if st.button("📚 View Saved Scenarios", use_container_width=True):
            st.session_state.page = 'saved_scenarios'
            st.rerun()
    
    st.markdown("---")
    
    # Render role badge
    render_role_badge()
    
    # ========== RBAC ACCESS CHECK ==========
    user_role = get_user_role()
    
    if not can_access_scenario_generator():
        st.error("🔒 **Access Denied**")
        return
    
    # ========== SUBSCRIPTION CHECK ==========
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    is_system_admin = user_role == 'system_admin'
    
    
    has_subscription, current_plan, sub_message = check_subscription_access(
        company_id=company_id, 
        user_id=user_id,
        subscription_manager=subscription_manager
    )
    
    if not has_subscription and not is_system_admin:
        st.warning("🔒 **Premium Feature - Subscription Required**")
        st.error(f"❌ {sub_message}")
        return
    
    # ========== ACCESS GRANTED ==========
    if is_system_admin:
        st.success(f"✅ **Full Access Granted** - 👑 System Admin")
    else:
        st.success(f"✅ **Access Granted** - {current_plan.upper()} Plan | Role: {user_role.upper()}")
    
    can_generate = can_generate_scenarios()
    can_export = can_export_scenarios()
        
    
    # ========== TENDER SELECTION ==========
    search_term = st.text_input("🔍 Search Tender", placeholder="Enter tender ID or title...")

    selected_tender_id, tender_title, official_estimate, procurement_type, \
    procuring_entity, division, district = render_tender_selector(
        db=db,
        company_id=st.session_state.get('company_id'),
        search_term=search_term,
        include_manual_entry=True,
        title="📋 Select Tender",
        show_table=True,
        show_summary=True
    )

    if not selected_tender_id and not tender_title:
        st.warning("Please select or enter a tender")
        return

        
        official_estimate = selected_tender_row['official_estimate']
        procurement_type = selected_tender_row['procurement_type']
        selected_tender_id = selected_tender_row['id']
        tender_title = selected_tender_row['tender_title']
    
    # ========== PRICE RANGE CONFIGURATION - FIXED ==========
    st.markdown("---")
    st.markdown("### 📊 Bid Price Range Configuration")
    
    # Initialize session state
    if 'min_price_pct' not in st.session_state:
        st.session_state.min_price_pct = 0.88
    if 'max_price_pct' not in st.session_state:
        st.session_state.max_price_pct = 1.08
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Use number input instead of slider for reliability
        min_percent = st.number_input(
            "Minimum Bid Price (% of OCE)",
            min_value=70,
            max_value=95,
            value=int(st.session_state.min_price_pct * 100),
            step=1,
            key="min_price_percent",
            help="Lowest possible bid as percentage of OCE (default: 88% = 12% below)"
        )
        min_price_pct = min_percent / 100.0
        st.session_state.min_price_pct = min_price_pct
        st.caption(f"💰 Minimum bid: BDT {official_estimate * min_price_pct:,.3f}")
    
    with col2:
        max_percent = st.number_input(
            "Maximum Bid Price (% of OCE)",
            min_value=102,
            max_value=120,
            value=int(st.session_state.max_price_pct * 100),
            step=1,
            key="max_price_percent",
            help="Highest possible bid as percentage of OCE (default: 108% = 8% above)"
        )
        max_price_pct = max_percent / 100.0
        st.session_state.max_price_pct = max_price_pct
        st.caption(f"💰 Maximum bid: BDT {official_estimate * max_price_pct:,.3f}")
    
    if min_price_pct >= max_price_pct:
        st.error("❌ Minimum price must be less than maximum price!")
        return
    
    # ========== SCENARIO CONFIGURATION ==========
    st.markdown("### 🎲 Scenario Configuration")
    
    scenario_config = st.radio(
        "Scenario Setup", 
        ["📊 Default (9 scenarios)", "✏️ Custom"], 
        horizontal=True,
        key="scenario_config"
    )
    
    if scenario_config == "📊 Default (9 scenarios)":
        competitor_counts = [5, 6, 7, 8, 10, 12, 14, 16, 19]
        st.info(f"📊 Will generate **{len(competitor_counts)} scenarios** with competitor counts: {', '.join(map(str, competitor_counts))}")
    else:
        col1, col2 = st.columns(2)
        with col1:
            min_comp = st.number_input("Minimum Competitors", min_value=1, max_value=50, value=5, key="min_comp")
        with col2:
            max_comp = st.number_input("Maximum Competitors", min_value=min_comp + 1, max_value=100, value=19, key="max_comp")
        
        num_scenarios = st.slider("Number of Scenarios", min_value=1, max_value=20, value=9, key="num_scenarios")
        competitor_counts = sorted(set(np.linspace(min_comp, max_comp, num_scenarios, dtype=int)))
        
        manual_override = st.checkbox("Manual Entry (comma-separated)", key="manual_override")
        if manual_override:
            manual_input = st.text_input("Competitor Counts", value="5, 8, 11, 14, 17, 19", key="manual_counts")
            try:
                competitor_counts = [int(x.strip()) for x in manual_input.split(',')]
                st.success(f"✅ Using custom counts: {competitor_counts}")
            except:
                st.error("Invalid input. Using auto-generated counts.")
        
        st.success(f"📊 Will generate **{len(competitor_counts)} scenarios** with counts: {competitor_counts}")
    
    # ========== OTHER PARAMETERS ==========
    col1, col2 = st.columns(2)
    
    with col1:
        pattern = st.selectbox(
            "Competitor Bidding Pattern",
            options=['realistic', 'aggressive', 'conservative', 'uniform'],
            index=0,
            key="bidding_pattern",
            help="""
            - **realistic**: Most bids cluster around typical market prices (recommended)
            - **aggressive**: Many bids near the lower end (highly competitive market)
            - **conservative**: Bids clustered near OCE (less competitive)
            - **uniform**: Even distribution across the entire range
            """
        )
    
    with col2:
        ai_strategy = st.selectbox(
            "AI Recommendation Strategy",
            options=['weighted_ensemble', 'conservative', 'aggressive', 'statistical', 'ml_style'],
            index=0,
            key="ai_strategy",
            format_func=lambda x: {
                'weighted_ensemble': '🎯 Weighted Ensemble (Balanced)',
                'conservative': '🛡️ Conservative (Highest Profit)',
                'aggressive': '⚡ Aggressive (Highest Win Chance)',
                'statistical': '📊 Statistical (Mean - 0.5*Std)',
                'ml_style': '🤖 ML-Style (Regression)'
            }.get(x, x)
        )
    
    # Advanced options
    with st.expander("🔧 Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            random_seed = st.number_input("Random Seed", min_value=1, max_value=9999, value=42, step=1, key="random_seed")
        with col2:
            risk_tolerance = st.select_slider(
                "Risk Tolerance", 
                options=['conservative', 'moderate', 'aggressive'], 
                value='moderate',
                key="risk_tolerance"
            )
    
    # Scenario name for saving
    st.markdown("### 💾 Save Options")
    col1, col2 = st.columns([2, 1])
    with col1:
        scenario_name = st.text_input(
            "Scenario Name (for saving)", 
            value=f"Scenario {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            key="scenario_name",
            help="Give your scenario a meaningful name to find it later"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        auto_save = st.checkbox("Auto-save to database", value=False, key="auto_save")
    
    # ========== GENERATE BUTTON ==========
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_btn = st.button(
            "🚀 Generate Scenarios", 
            type="primary", 
            use_container_width=True, 
            disabled=not can_generate,
            key="generate_btn"
        )
    
    # ========== GENERATE AND DISPLAY ==========
    if generate_btn:
        with st.spinner("🔄 Generating scenarios and calculating optimal bids..."):
            generator = BidScenarioGenerator(
                official_estimate=official_estimate,
                procurement_type=procurement_type,
                min_price_pct=min_price_pct,
                max_price_pct=max_price_pct,
                random_seed=random_seed
            )
            
            scenarios = generator.generate_scenarios(competitor_counts, pattern)
            recommendation = generator.get_ai_recommended_bid(scenarios, ai_strategy)
            
            # Prepare summary
            scenario_summary = []
            competitor_stats_list = []
            
            for s in scenarios:
                scenario_summary.append({
                    'Scenario #': s['scenario_id'],
                    'Competitors': s['num_competitors'],
                    'Optimal Bid (BDT)': s['optimized_bid'],
                    'Bid Ratio (%)': round(s['bid_ratio'] * 100, 2),
                    'Win Probability (%)': round(s['win_probability'] * 100, 2),
                    'Risk Level': s['risk_level'],
                    'Expected Profit (BDT)': round(s['expected_profit'], 2),
                    'SLT Threshold (BDT)': round(s['slt_threshold'], 2),
                    'NPPI Factor': s['nppi_factor']
                })
                
                competitor_stats_list.append({
                    'Scenario #': s['scenario_id'],
                    'Competitors': s['num_competitors'],
                    'Min Competitor Bid': s['competitor_stats']['min'],
                    'Max Competitor Bid': s['competitor_stats']['max'],
                    'Mean Competitor Bid': s['competitor_stats']['mean'],
                    'Median Competitor Bid': s['competitor_stats']['median'],
                    'Std Dev Competitor': s['competitor_stats']['std']
                })
            
            report = {
                'generation_params': {
                    'official_estimate': official_estimate,
                    'procurement_type': procurement_type,
                    'min_price_pct': min_price_pct,
                    'max_price_pct': max_price_pct,
                    'pattern': pattern,
                    'competitor_counts': competitor_counts,
                    'tender_id': selected_tender_id,
                    'tender_title': tender_title,
                    'ai_strategy': ai_strategy,
                    'random_seed': random_seed,
                    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'scenarios': scenario_summary,
                'scenarios_full': scenarios,
                'competitor_stats': competitor_stats_list,
                'ai_recommendation': recommendation
            }
            
            st.session_state['current_report'] = report
            
            # ========== SAVE TO DATABASE ==========
            if auto_save and db and company_id and user_id:
                scenario_data = {
                    'tender_id': selected_tender_id,
                    'scenario_name': scenario_name,
                    'description': f"Generated with {pattern} pattern, {ai_strategy} strategy. Price range: {min_price_pct*100:.0f}%-{max_price_pct*100:.0f}% of OCE",
                    'official_estimate': official_estimate,
                    'procurement_type': procurement_type,
                    'min_price_pct': min_price_pct,
                    'max_price_pct': max_price_pct,
                    'competitor_counts': competitor_counts,
                    'bidding_pattern': pattern,
                    'ai_strategy': ai_strategy,
                    'random_seed': random_seed,
                    'recommended_bid': recommendation['recommended_bid'],
                    'bid_ratio': recommendation['bid_ratio'],
                    'confidence_score': recommendation['confidence_score'],
                    'expected_win_probability': recommendation['expected_win_probability'],
                    'scenarios': scenario_summary,
                    'competitor_stats': competitor_stats_list
                }
                scenario_id = db.save_scenario(company_id, user_id, scenario_data)
                if scenario_id:
                    st.toast(f"✅ Scenario saved to database! ID: {scenario_id}", icon="💾")
    
    # ========== DISPLAY RESULTS ==========
    if st.session_state.get('current_report'):
        report = st.session_state['current_report']
        rec = report['ai_recommendation']
        
        st.markdown("---")
        st.markdown("## 🤖 AI Recommended Bid Price")
        
        # Highlighted recommendation
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Recommended Bid",
                f"BDT {rec['recommended_bid']:,.3f}",
                f"{rec['bid_ratio']*100:.1f}% of OCE"
            )
        with col2:
            st.metric("Confidence Score", f"{rec['confidence_score']*100:.1f}%")
        with col3:
            st.metric("Expected Win Prob.", f"{rec['expected_win_probability']*100:.1f}%")
        with col4:
            st.metric("Strategy", rec['strategy_used'].replace('_', ' ').title())
        
        with st.expander("📊 View Recommendation Reasoning"):
            st.markdown(rec['reasoning'])
            st.caption(f"Generated for: {report['generation_params'].get('tender_title', 'N/A')}")
        
        # Scenarios Table
        st.markdown("## 📈 Scenario Analysis Results")
        st.caption(f"Price Range: {report['generation_params']['min_price_pct']*100:.0f}% - {report['generation_params']['max_price_pct']*100:.0f}% of OCE")
        
        df_scenarios = pd.DataFrame(report['scenarios'])
        st.dataframe(df_scenarios, use_container_width=True, hide_index=True)
        
        # Competitor Statistics Table
        with st.expander("📊 View Competitor Statistics"):
            df_competitor_stats = pd.DataFrame(report['competitor_stats'])
            st.dataframe(df_competitor_stats, use_container_width=True, hide_index=True)
        
        # Detailed competitor bids
        with st.expander("🔍 View Detailed Competitor Bids for Each Scenario"):
            for scenario in report['scenarios_full']:
                st.markdown(f"**Scenario {scenario['scenario_id']}** - {scenario['num_competitors']} Competitors")
                
                bids_df = pd.DataFrame({
                    'Competitor': [f"Comp {i+1}" for i in range(len(scenario['competitor_bids']))],
                    'Bid Price (BDT)': scenario['competitor_bids']
                })
                bids_df['Bid Price (BDT)'] = bids_df['Bid Price (BDT)'].apply(lambda x: f"{x:,.3f}")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.dataframe(bids_df, hide_index=True, use_container_width=True)
                with col2:
                    stats_data = scenario['competitor_stats']
                    st.markdown(f"""
                    **Statistics:**
                    - Min: BDT {stats_data['min']:,.3f}
                    - Max: BDT {stats_data['max']:,.3f}
                    - Mean: BDT {stats_data['mean']:,.3f}
                    - Median: BDT {stats_data['median']:,.3f}
                    - Std Dev: BDT {stats_data['std']:,.3f}
                    """)
                st.markdown("---")
        
        # ========== EXPORT OPTIONS ==========
        if can_export:
            st.markdown("## 📥 Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # CSV Export
                csv_data = pd.DataFrame(report['scenarios']).to_csv(index=False)
                st.download_button(
                    "📄 Export as CSV",
                    data=csv_data,
                    file_name=f"scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="csv_export"
                )
            
            with col2:
                # Excel Export
                try:
                    import io
                    import xlsxwriter
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Scenarios sheet
                        pd.DataFrame(report['scenarios']).to_excel(writer, sheet_name='Scenarios', index=False)
                        
                        # Competitor stats sheet
                        pd.DataFrame(report['competitor_stats']).to_excel(writer, sheet_name='Competitor Stats', index=False)
                        
                        # AI Recommendation sheet
                        rec_df = pd.DataFrame([{
                            'Metric': 'Recommended Bid (BDT)',
                            'Value': rec['recommended_bid'],
                            'Note': f"{rec['bid_ratio']*100:.1f}% of OCE"
                        }, {
                            'Metric': 'Confidence Score',
                            'Value': f"{rec['confidence_score']*100:.1f}%",
                            'Note': ''
                        }, {
                            'Metric': 'Expected Win Probability',
                            'Value': f"{rec['expected_win_probability']*100:.1f}%",
                            'Note': ''
                        }, {
                            'Metric': 'Strategy Used',
                            'Value': rec['strategy_used'],
                            'Note': ''
                        }])
                        rec_df.to_excel(writer, sheet_name='AI Recommendation', index=False)
                        
                        # Parameters sheet
                        params_df = pd.DataFrame([{
                            'Parameter': k,
                            'Value': str(v)
                        } for k, v in report['generation_params'].items()])
                        params_df.to_excel(writer, sheet_name='Parameters', index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "📊 Export as Excel",
                        data=output,
                        file_name=f"scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="excel_export"
                    )
                except ImportError:
                    st.warning("⚠️ xlsxwriter not installed. Install with: pip install xlsxwriter")
            
            with col3:
                # JSON Export
                import json
                json_data = json.dumps(report, indent=2, default=str)
                st.download_button(
                    "📋 Export as JSON",
                    data=json_data,
                    file_name=f"scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="json_export"
                )
        
        # ========== SAVE BUTTON (if not auto-saved) ==========
        if not auto_save and db and company_id and user_id:
            st.markdown("---")
            st.markdown("### 💾 Save to Database")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                save_name = st.text_input("Scenario Name", value=scenario_name, key="save_name_input")
            with col2:
                if st.button("💾 Save Scenario", type="primary", use_container_width=True, key="manual_save_btn"):
                    scenario_data = {
                        'tender_id': selected_tender_id,
                        'scenario_name': save_name,
                        'description': f"Generated with {pattern} pattern, {ai_strategy} strategy",
                        'official_estimate': official_estimate,
                        'procurement_type': procurement_type,
                        'min_price_pct': min_price_pct,
                        'max_price_pct': max_price_pct,
                        'competitor_counts': competitor_counts,
                        'bidding_pattern': pattern,
                        'ai_strategy': ai_strategy,
                        'random_seed': random_seed,
                        'recommended_bid': rec['recommended_bid'],
                        'bid_ratio': rec['bid_ratio'],
                        'confidence_score': rec['confidence_score'],
                        'expected_win_probability': rec['expected_win_probability'],
                        'scenarios': report['scenarios'],
                        'competitor_stats': report['competitor_stats']
                    }
                    scenario_id = db.save_scenario(company_id, user_id, scenario_data)
                    if scenario_id:
                        st.success(f"✅ Scenario saved successfully! ID: {scenario_id}")
                    else:
                        st.error("❌ Failed to save scenario")
        
        # Timestamp
        st.caption(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    print("✅ Bid Scenario Generator with Database Integration ready!")