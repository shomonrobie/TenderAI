"""
Basic Bid Optimizer Module
Simple, fast bid recommendations based on official estimate
No competitor data required - just quick percentage-based suggestions
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple

from modules.rbac import (
    can_optimize_bid,
    can_export_data,
    render_role_badge,
    get_user_role
)
from modules.tender_selector import render_tender_selector


class BasicBidOptimizer:
    """Simple bid optimizer based on official estimate only"""
    
    def __init__(self, official_estimate: float, procurement_type: str = 'works'):
        self.official_estimate = float(official_estimate)
        self.procurement_type = procurement_type
        
        # Base recommendation percentages by procurement type
        self.base_percentages = {
            'works': 0.92,      # 92% of OCE for construction works
            'goods': 0.94,      # 94% of OCE for goods/supplies
            'services': 0.95    # 95% of OCE for services
        }
        
        # Risk adjustment ranges
        self.risk_adjustments = {
            'aggressive': -0.03,   # Bid 3% lower than base
            'moderate': 0.00,      # Base recommendation
            'conservative': 0.02   # Bid 2% higher than base
        }
    
    def calculate_bid(self, risk_tolerance: str = 'moderate') -> Dict:
        """
        Calculate basic bid recommendation.
        
        Args:
            risk_tolerance: 'aggressive', 'moderate', or 'conservative'
        
        Returns:
            Dictionary with bid recommendation and metrics
        """
        # Get base percentage for procurement type
        base_pct = self.base_percentages.get(self.procurement_type, 0.92)
        
        # Apply risk adjustment
        risk_adj = self.risk_adjustments.get(risk_tolerance, 0.00)
        final_pct = base_pct + risk_adj
        
        # Calculate recommended bid
        recommended_bid = self.official_estimate * final_pct
        recommended_bid = round(recommended_bid, 3)
        
        # Calculate win probability (estimate-based)
        if final_pct < 0.89:
            win_probability = 0.85  # 85% chance if bidding very low
        elif final_pct < 0.92:
            win_probability = 0.70  # 70% chance
        elif final_pct < 0.95:
            win_probability = 0.55  # 55% chance
        else:
            win_probability = 0.40  # 40% chance
        
        # Calculate estimated profit (assuming 12% margin on cost)
        estimated_cost = self.official_estimate * 0.85
        expected_profit = recommended_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        # Determine risk level
        if final_pct < 0.89:
            risk_level, risk_color = "HIGH", "🔴"
        elif final_pct < 0.93:
            risk_level, risk_color = "MEDIUM", "🟡"
        else:
            risk_level, risk_color = "LOW", "🟢"
        
        # Calculate savings compared to OCE
        savings = self.official_estimate - recommended_bid
        
        return {
            'recommended_bid': recommended_bid,
            'bid_ratio': round(final_pct, 4),
            'win_probability': round(win_probability, 4),
            'expected_profit': round(expected_profit, 3),
            'expected_value': round(expected_value, 3),
            'estimated_cost': round(estimated_cost, 3),
            'savings_vs_oce': round(savings, 3),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'risk_tolerance': risk_tolerance,
            'procurement_type': self.procurement_type,
            'base_percentage': round(base_pct * 100, 1),
            'final_percentage': round(final_pct * 100, 1)
        }
    
    def get_quick_scenarios(self) -> pd.DataFrame:
        """Generate quick scenarios for all risk tolerances"""
        scenarios = []
        
        for risk in ['aggressive', 'moderate', 'conservative']:
            result = self.calculate_bid(risk)
            scenarios.append({
                'Risk Tolerance': risk.capitalize(),
                'Bid Amount': f"BDT {result['recommended_bid']:,.3f}",
                'Bid Ratio': f"{result['final_percentage']:.1f}%",
                'Win Probability': f"{result['win_probability']*100:.0f}%",
                'Expected Profit': f"BDT {result['expected_profit']:,.3f}",
                'Risk Level': f"{result['risk_color']} {result['risk_level']}"
            })
        
        return pd.DataFrame(scenarios)

def check_basic_optimizer_access(company_id, subscription_manager=None):
    """Check if user can access Basic Bid Optimizer (Free users can access)"""
    user_role = get_user_role()
    
    # System admin always has access
    if user_role == 'system_admin':
        return True, 'system_admin', "System Admin - Full access"
    
    # Basic Bid Optimizer is FREE for all registered users
    if not subscription_manager or not company_id:
        return True, 'free', "Free tier access"
    
    try:
        sub = subscription_manager.get_company_subscription(company_id)
        plan = sub.get('plan', 'free')
        # All plans including free can use Basic Bid Optimizer
        return True, plan, f"Access granted - {plan.upper()} plan"
    except:
        return True, 'free', "Access granted"


def render_basic_bid_optimizer(db=None, subscription_manager=None):
    """Render Basic Bid Optimizer UI"""
    
    st.markdown("## 📈 Basic Bid Optimizer")
    st.markdown("*Quick bid recommendation based on official estimate only*")
    
    render_role_badge()
    
    # Access check - ALWAYS returns True for this tool
    company_id = st.session_state.get('company_id')
    has_access, plan, access_msg = check_basic_optimizer_access(company_id, subscription_manager)
    
    # Show plan info but don't block access
    if plan != 'system_admin':
        st.info(f"ℹ️ {access_msg}")

    # Access check
    user_role = get_user_role()
    if not can_optimize_bid() and user_role != 'system_admin':
        st.error("🔒 You don't have permission to use the Bid Optimizer")
        return
    
    # Tender selection or manual input
    st.markdown("### 📋 Tender Selection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        input_method = st.radio(
            "Select Input Method",
            options=["Manual Entry", "Select from Existing Tender"],
            horizontal=True
        )
    
    official_estimate = None
    tender_title = None
    tender_id = None
    procurement_type = 'works'
    
    if input_method == "Select from Existing Tender":
        if db:
            try:
                company_id = st.session_state.get('company_id')
                tenders_df = db.get_company_tenders(company_id)
                
                if not tenders_df.empty:
                    selected = st.selectbox(
                        "Select Tender",
                        tenders_df.to_dict('records'),
                        format_func=lambda x: f"{x.get('tender_id', 'N/A')} - {x.get('tender_title', 'Untitled')[:50]}"
                    )
                    official_estimate = selected.get('official_estimate', 0)
                    tender_title = selected.get('tender_title', '')
                    tender_id = selected.get('id')
                    procurement_type = selected.get('procurement_type', 'works')
                    st.success(f"✅ Selected: {tender_title[:60]}")
                else:
                    st.info("No tenders found. Please add tenders in Tender Management.")
                    input_method = "Manual Entry"
            except Exception as e:
                st.warning(f"Could not load tenders: {e}")
                input_method = "Manual Entry"
    
    if input_method == "Manual Entry" or official_estimate is None or official_estimate == 0:
        col1, col2 = st.columns(2)
        with col1:
            official_estimate = st.number_input(
                "Official Estimate (BDT) *",
                min_value=10000.0,
                value=7500000.0,
                step=100000.0,
                format="%.3f"
            )
        with col2:
            procurement_type = st.selectbox(
                "Procurement Type",
                options=['works', 'goods', 'services'],
                index=0,
                help="Works: Construction | Goods: Supplies/Materials | Services: Consulting"
            )
        
        tender_title = "Manual Entry"
    
    # Risk selection
    st.markdown("---")
    st.markdown("### ⚙️ Strategy Selection")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_tolerance = st.select_slider(
            "Risk Tolerance",
            options=['aggressive', 'moderate', 'conservative'],
            value='moderate',
            format_func=lambda x: {
                'aggressive': '🎯 Aggressive (Win Focus)',
                'moderate': '⚖️ Moderate (Balanced)',
                'conservative': '🛡️ Conservative (Profit Focus)'
            }.get(x, x.capitalize())
        )
    
    # Generate button
    if st.button("🚀 Calculate Recommendation", type="primary", use_container_width=True):
        with st.spinner("Calculating bid recommendation..."):
            optimizer = BasicBidOptimizer(official_estimate, procurement_type)
            result = optimizer.calculate_bid(risk_tolerance)
            scenarios_df = optimizer.get_quick_scenarios()
            
            st.session_state.basic_result = result
            st.session_state.basic_scenarios = scenarios_df
            st.session_state.basic_tender_info = {
                'tender_title': tender_title,
                'tender_id': tender_id,
                'procurement_type': procurement_type,
                'official_estimate': official_estimate,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    # Display results
    if st.session_state.get('basic_result'):
        result = st.session_state.basic_result
        tender_info = st.session_state.basic_tender_info
        
        st.markdown("---")
        st.markdown("## 🤖 Bid Recommendation")
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Recommended Bid",
                f"BDT {result['recommended_bid']:,.3f}",
                f"{result['final_percentage']:.1f}% of OCE"
            )
        
        with col2:
            st.metric(
                "Win Probability",
                f"{result['win_probability']*100:.0f}%"
            )
        
        with col3:
            st.metric(
                "Expected Profit",
                f"BDT {result['expected_profit']:,.3f}"
            )
        
        with col4:
            st.metric(
                "Savings vs OCE",
                f"BDT {result['savings_vs_oce']:,.3f}"
            )
        
        # Strategy explanation
        st.markdown("### 📊 Strategy Analysis")
        
        strategy_explanations = {
            'aggressive': """
            **🎯 Aggressive Strategy (Win Focus)**
            - Bids lower to maximize win probability
            - Lower profit margin per win
            - Best when you need to win at any cost
            - Recommended for: Competitive markets, must-win tenders
            """,
            'moderate': """
            **⚖️ Moderate Strategy (Balanced)**
            - Balanced approach between winning and profit
            - Good for most tender situations
            - Standard market position
            - Recommended for: Typical tenders with reasonable competition
            """,
            'conservative': """
            **🛡️ Conservative Strategy (Profit Focus)**
            - Higher bids with better profit margins
            - Lower win probability but higher per-win profit
            - Best when you have unique advantages
            - Recommended for: Specialized work, less competition
            """
        }
        
        st.info(strategy_explanations.get(risk_tolerance, strategy_explanations['moderate']))
        
        # Quick scenarios comparison
        st.markdown("### 📋 Strategy Comparison")
        st.dataframe(st.session_state.basic_scenarios, use_container_width=True, hide_index=True)
        
        # Detailed breakdown
        with st.expander("📐 Detailed Calculation Breakdown", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Input Parameters**")
                st.write(f"- Official Estimate: BDT {tender_info['official_estimate']:,.3f}")
                st.write(f"- Procurement Type: {tender_info['procurement_type'].upper()}")
                st.write(f"- Base Percentage: {result['base_percentage']:.1f}%")
                st.write(f"- Risk Adjustment: {result['final_percentage'] - result['base_percentage']:+.1f}%")
            
            with col2:
                st.markdown("**Output Metrics**")
                st.write(f"- Recommended Bid: BDT {result['recommended_bid']:,.3f}")
                st.write(f"- Estimated Cost: BDT {result['estimated_cost']:,.3f}")
                st.write(f"- Expected Profit: BDT {result['expected_profit']:,.3f}")
                st.write(f"- Expected Value: BDT {result['expected_value']:,.3f}")
        
        # Export options
        if can_export_data():
            st.markdown("---")
            st.markdown("### 📥 Export Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export as CSV
                export_data = {
                    'Metric': ['Tender Title', 'Official Estimate', 'Recommended Bid', 'Bid Ratio', 
                              'Win Probability', 'Expected Profit', 'Risk Level', 'Strategy'],
                    'Value': [
                        tender_info['tender_title'],
                        f"BDT {tender_info['official_estimate']:,.3f}",
                        f"BDT {result['recommended_bid']:,.3f}",
                        f"{result['final_percentage']:.1f}%",
                        f"{result['win_probability']*100:.0f}%",
                        f"BDT {result['expected_profit']:,.3f}",
                        f"{result['risk_color']} {result['risk_level']}",
                        risk_tolerance.capitalize()
                    ]
                }
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Results (CSV)",
                    data=csv,
                    file_name=f"bid_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Export as JSON
                import json
                json_data = {
                    'tender_info': tender_info,
                    'recommendation': result,
                    'scenarios': st.session_state.basic_scenarios.to_dict('records')
                }
                json_str = json.dumps(json_data, indent=2, default=str)
                st.download_button(
                    "📋 Download Results (JSON)",
                    data=json_str,
                    file_name=f"bid_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )


# Convenience function for main.py
def render(db=None, subscription_manager=None):
    render_basic_bid_optimizer(db, subscription_manager)