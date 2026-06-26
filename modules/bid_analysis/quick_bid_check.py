# modules/bid_analysis/quick_bid_check.py - COMPLETE FIXED VERSION

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.bid_analysis.bid_core import get_config, get_nested_config
from modules.rbac import render_role_badge
from modules.tender_selector import render_tender_selector
from modules.tender_selector_helper import render_tender_selector_with_boq


def render_quick_bid_check(db=None, subscription_manager=None):
    st.markdown("## ⚡ Quick Bid Check")
    st.markdown("*Instant heuristic bid recommendation from Official Cost Estimate*")
    render_role_badge()

    # Access check (free tier)
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')

    # Tender selection or manual entry
    use_tender = st.checkbox("Select a tender", value=False)
    
    if use_tender:
        tender_data = render_tender_selector_with_boq(db, company_id)
        if not tender_data:
            st.info("Please select a tender.")
            return
        official_estimate = tender_data['official_estimate']
        procurement_type = tender_data['procurement_type']
        tender_title = tender_data.get('tender_title', 'Manual Entry')
        tender_id = tender_data.get('tender_id', 'N/A')
        boq_items = tender_data.get('boq_items', [])
    else:
        col1, col2 = st.columns(2)
        with col1:
            official_estimate = st.number_input(
                "Official Estimate (BDT)", 
                min_value=0.0, 
                value=7500000.0, 
                step=100000.0, 
                format="%.3f"
            )
        with col2:
            procurement_type = st.selectbox("Procurement Type", ['works', 'goods', 'services'], index=1)
        tender_title = "Manual Entry"
        tender_id = None
        boq_items = []
    
    # ===== NPPI FACTOR (Optional) =====
    st.markdown("### 📊 NPPI Factor (Optional)")
    st.caption("Override the default NPPI factor. Leave blank to use system default.")
    
    col1, col2 = st.columns(2)
    with col1:
        use_nppi = st.checkbox("Use custom NPPI factor", value=False)
    
    nppi_factor = None
    if use_nppi:
        with col2:
            nppi_factor = st.number_input(
                "NPPI Factor", 
                min_value=0.85, 
                max_value=0.98, 
                value=0.920, 
                step=0.001, 
                format="%.3f",
                help="NPPI factor affects the SLT threshold calculation. Default varies by procurement type."
            )
    
    # Risk tolerance
    risk_tolerance = st.select_slider(
        "Risk Tolerance",
        options=['aggressive', 'moderate', 'conservative'],
        value='moderate',
        format_func=lambda x: {'aggressive': '🎯 Aggressive', 'moderate': '⚖️ Moderate', 'conservative': '🛡️ Conservative'}.get(x, x)
    )

    # ✅ Initialize variables outside the button block
    bid = 0
    win_prob = 0
    profit = 0
    ev = 0
    risk_level = 'MEDIUM'
    risk_color = '🟡'
    bid_ratio = 0
    nppi_price = 0
    slt_threshold = 0
    final_pct = 0

    if st.button("🚀 Get Quick Bid", type="primary", use_container_width=True):
        # Get NPPI factor (use default if not provided)
        if nppi_factor is None:
            default_key = f"default_nppi_{procurement_type}"
            nppi_factor = get_config(default_key, 0.92, company_id)
        
        # Calculate base percentage
        base_pct_key = f'base_percentage_{procurement_type}'
        base_pct = get_config(base_pct_key)
        if base_pct is None:
            base_pct = 0.92 if procurement_type == 'works' else 0.94 if procurement_type == 'goods' else 0.95

        # Risk adjustment
        risk_adj_dict = get_config('risk_adjustments')
        if risk_adj_dict is None:
            risk_adj_dict = {'aggressive': -0.03, 'moderate': 0.00, 'conservative': 0.02}
        
        risk_adj = risk_adj_dict.get(risk_tolerance, 0.00)
        final_pct = base_pct + risk_adj
        bid = official_estimate * final_pct
        bid_ratio = bid / official_estimate
        
        # Calculate NPPI Price for reference
        nppi_price = official_estimate * nppi_factor
        
        # Heuristic win probability (adjusted by NPPI)
        if nppi_price > 0:
            nppi_diff = abs(bid - nppi_price) / nppi_price
            nppi_win_adj = max(0, 1 - nppi_diff * 2)
        else:
            nppi_win_adj = 0.5
        
        thresholds = get_config('win_probability_thresholds', [0.89, 0.92, 0.95])
        probs = get_config('win_probability_values', [0.85, 0.70, 0.55, 0.40])
        if bid_ratio < thresholds[0]:
            win_prob = probs[0]
        elif bid_ratio < thresholds[1]:
            win_prob = probs[1]
        elif bid_ratio < thresholds[2]:
            win_prob = probs[2]
        else:
            win_prob = probs[3]
        
        # Blend with NPPI adjustment
        win_prob = win_prob * 0.7 + nppi_win_adj * 0.3
        win_prob = max(0.10, min(0.95, win_prob))
        
        # Calculate cost and profit
        cost = official_estimate * get_config('fallback_estimated_cost_factor', 0.85)
        profit = bid - cost
        ev = profit * win_prob
        
        # Calculate SLT threshold (simplified)
        slt_threshold = official_estimate * 0.80
        if nppi_factor:
            slt_threshold = min(slt_threshold, nppi_price * 0.95)
        
        # Risk level
        risk_thresholds = get_config('risk_thresholds', [0.85, 0.89, 0.93, 0.96])
        risk_labels = get_config('risk_labels', ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'MEDIUM-LOW', 'LOW'])
        risk_colors = get_config('risk_colors', ['🔴', '🟠', '🟡', '🟢', '🔵'])
        risk_idx = 0
        for i, thresh in enumerate(risk_thresholds):
            if bid_ratio < thresh:
                risk_idx = i
                break
        else:
            risk_idx = len(risk_labels) - 1
        risk_level = risk_labels[risk_idx]
        risk_color = risk_colors[risk_idx]

        # Display results
        st.markdown("---")
        st.markdown("## 📊 Quick Bid Results")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Recommended Bid", f"BDT {bid:,.3f}", f"{final_pct*100:.1f}% of OCE")
        col2.metric("Win Probability", f"{win_prob*100:.0f}%")
        col3.metric("Expected Profit", f"BDT {profit:,.3f}")
        col4.metric("Risk Level", f"{risk_color} {risk_level}")

        # NPPI Information
        st.markdown("#### 📊 NPPI Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("NPPI Factor", f"{nppi_factor:.4f}")
        with col2:
            st.metric("NPPI Price", f"BDT {nppi_price:,.3f}")
        with col3:
            slt_status = "✅ Above" if bid >= slt_threshold else "⚠️ Below"
            st.metric("SLT Threshold (Simplified)", f"BDT {slt_threshold:,.3f}", slt_status)

        st.info(f"**Strategy:** {risk_tolerance.capitalize()} approach. Bid {final_pct*100:.1f}% below OCE. "
                f"NPPI factor {nppi_factor:.4f} applied. Quick heuristic – upgrade to Advanced for full PPR compliance.")

        # Save to session
        st.session_state.quick_bid_result = {
            'tender_id': tender_id,
            'tender_title': tender_title,
            'official_estimate': official_estimate,
            'procurement_type': procurement_type,
            'recommended_bid': bid,
            'win_probability': win_prob,
            'expected_profit': profit,
            'expected_value': ev,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'strategy': risk_tolerance,
            'nppi_factor': nppi_factor,
            'nppi_price': nppi_price,
            'slt_threshold': slt_threshold,
            'bid_ratio': bid_ratio,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # ✅ Export Options (outside the button block, using session state)
    if st.session_state.get('quick_bid_result'):
        result = st.session_state.quick_bid_result
        
        st.markdown("---")
        st.markdown("### 📄 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generate HTML Report", use_container_width=True):
                user_info = {
                    'full_name': st.session_state.get('full_name', 'User'),
                    'company_name': st.session_state.get('company_name', 'N/A')
                }
                from modules.html_report_generator import generate_analysis_report
                report_buffer = generate_analysis_report(result, user_info, tier="quick")
                st.download_button(
                    "📥 Download HTML Report",
                    report_buffer,
                    f"quick_bid_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    "text/html",
                    use_container_width=True
                )
        
        with col2:
            data = {
                'Metric': ['Recommended Bid', 'Win Probability', 'Expected Profit', 'Risk Level', 
                          'Bid Ratio', 'NPPI Factor', 'SLT Threshold'],
                'Value': [
                    result.get('recommended_bid', 0),
                    f"{result.get('win_probability', 0):.3f}",
                    result.get('expected_profit', 0),
                    result.get('risk_level', 'MEDIUM'),
                    f"{result.get('bid_ratio', 0):.3f}",
                    f"{result.get('nppi_factor', 0):.4f}",
                    f"{result.get('slt_threshold', 0):,.3f}"
                ]
            }
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False)
            st.download_button(
                "📊 Export CSV", 
                csv, 
                f"quick_bid_check_{datetime.now().strftime('%Y%m%d')}.csv", 
                "text/csv",
                use_container_width=True
            )