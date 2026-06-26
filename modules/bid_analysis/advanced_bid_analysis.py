# modules/bid_analysis/advanced_bid_analysis.py - COMPLETE FIXED VERSION

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.bid_analysis.bid_core import (
    CostEngine, NPPIEngine, SLTEngine, CompetitorEngine,
    WinProbabilityEngine, OptimumBidEngine, get_config, get_nested_config
)
from modules.rbac import render_role_badge
from modules.subscription_manager import check_subscription_access
from modules.tender_selector_helper import render_tender_selector_with_boq
from modules.competitor_selector import (
    render_competitor_selector, 
    get_selected_competitor_bids
)


def render_advanced_bid_analysis(db=None, subscription_manager=None):
    st.markdown("## 📈 Advanced Bid Analysis")
    st.markdown("*PPR 2025 compliant bid with competitor intelligence and cost profiling*")
    render_role_badge()

    # Subscription check
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)
    if not has_access:
        st.warning(msg)
        st.info("Upgrade to use Advanced Bid Analysis (3 credits).")
        return

    # Tender selection
    tender_data = render_tender_selector_with_boq(db, company_id)
    
    if not tender_data:
        st.info("Please select a tender to proceed.")
        return
    
    official_estimate = tender_data['official_estimate']
    procurement_type = tender_data['procurement_type']
    tender_title = tender_data['tender_title']
    tender_id = tender_data.get('tender_id', 'N/A')
    
    # Get BOQ data
    boq_data = tender_data.get('boq_data')
    boq_status = tender_data.get('boq_status')
    
    if boq_status == 'not_found':
        st.warning("⚠️ No locked BOQ found for this tender.")
        st.info("Please generate and lock a BOQ first.")
        if st.button("📊 Go to BOQ Generator"):
            st.session_state.page = "boq_generator"
            st.rerun()
        return
    
    if boq_data is None:
        st.warning("No BOQ data available.")
        return
    
    # Extract BOQ data
    boq = boq_data.get('boq', {})
    items = boq_data.get('items', [])
    total_estimated_cost = boq.get('total_estimated_cost', 0)
    three_level_costs = tender_data.get('three_level_costs', {})
    
    total_aggressive = three_level_costs.get('aggressive', 0)
    total_competitive = three_level_costs.get('competitive', 0)
    total_standard = three_level_costs.get('standard', 0)
    
    # If three_level_costs are zero, use total_estimated_cost as fallback
    if total_aggressive == 0 and total_competitive == 0 and total_standard == 0:
        total_aggressive = total_estimated_cost
        total_competitive = total_estimated_cost
        total_standard = total_estimated_cost
    
    st.success(f"✅ Selected: {tender_title} (OCE: BDT {official_estimate:,.3f})")
    
    # Show BOQ Summary
    st.markdown("### 📊 BOQ Summary")
    st.caption(f"BOQ #{boq.get('id')} - {boq.get('item_count', 0)} items")
    st.caption(f"Rate Book: {boq.get('rate_book_name', 'N/A')}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Aggressive Cost", f"BDT {total_aggressive:,.3f}")
    with col2:
        st.metric("🟡 Competitive Cost", f"BDT {total_competitive:,.3f}")
    with col3:
        st.metric("🔴 Standard Cost", f"BDT {total_standard:,.3f}")
    
    # Show BOQ items
    with st.expander("📋 View BOQ Items", expanded=False):
        if items:
            df_items = pd.DataFrame(items)
            display_cols = ['item_code', 'description', 'unit', 'quantity', 'unit_rate', 'total']
            available_cols = [col for col in display_cols if col in df_items.columns]
            if available_cols:
                st.dataframe(df_items[available_cols], use_container_width=True)
            st.caption(f"Total: {len(items)} items | Total Cost: BDT {total_estimated_cost:,.3f}")
        else:
            st.info("No items found in BOQ.")
    
    st.divider()
    
    # OCE override
    oce_override = st.number_input(
        "Override OCE (optional)", 
        min_value=0.0, 
        value=float(official_estimate),
        step=100000.0, 
        format="%.3f"
    )

    if oce_override > 0:
        official_estimate = oce_override
        st.info(f"Using overridden OCE: BDT {official_estimate:,.3f}")
    
    # Input section
    col1, col2 = st.columns(2)
    with col1:
        risk_tolerance = st.select_slider(
            "Risk Tolerance", 
            options=['aggressive', 'moderate', 'conservative'], 
            value='moderate'
        )
    
    with col2:
        cost_profile = st.selectbox(
            "Cost Profile", 
            ['competitive', 'aggressive', 'standard'], 
            index=1
        )
        
        # Show selected cost profile total
        if cost_profile == 'aggressive':
            selected_cost = total_aggressive
        elif cost_profile == 'competitive':
            selected_cost = total_competitive
        else:
            selected_cost = total_standard
        
        st.info(f"📊 Using {cost_profile.upper()} cost: BDT {selected_cost:,.3f}")
    
    # ===== COMPETITOR DATA =====
    st.markdown("---")
    st.info(f"📌 Competitors filtered by procurement type: **{procurement_type.upper()}**")
    
    competitor_source = st.radio(
        "Competitor Source",
        ["Auto-generate", "Enter manually", "Select from database"],
        index=0,
        key="adv_comp_source"
    )
    
    if competitor_source == "Auto-generate":
        competitor_count = st.slider("Number of competitors to generate", min_value=1, max_value=10, value=5)
        competitor_bids = CompetitorEngine.generate(competitor_count, official_estimate)
        st.write(f"Generated {len(competitor_bids)} competitor bids: {competitor_bids}")

    elif competitor_source == "Enter manually":
        comp_input = st.text_area("Enter competitor bids (one per line, numbers only)")
        if comp_input:
            competitor_bids = [float(x.strip()) for x in comp_input.splitlines() if x.strip()]
        else:
            competitor_bids = []

    else:  # Select from database
        selected_competitors, stats = render_competitor_selector(
            db=db,
            company_id=company_id,
            procurement_type=procurement_type,
            title="👥 Select Competitors",
            show_table=True,
            multi_select=True,
            max_select=10
        )
        
        if selected_competitors:
            competitor_bids = get_selected_competitor_bids(selected_competitors, official_estimate)
            st.write(f"Generated {len(competitor_bids)} bids from selected competitors: {competitor_bids}")
        else:
            competitor_bids = []
    
    # NPPI override
    nppi_override = st.number_input(
        "NPPI Factor (optional, 0.85-0.98)", 
        min_value=0.85, 
        max_value=0.98, 
        value=0.920, 
        step=0.001, 
        format="%.3f"
    )

    # ✅ Initialize variables outside the button block
    optimal_bid = 0
    win_prob = 0
    profit = 0
    ev = 0
    risk_level = 'MEDIUM'
    risk_color = '🟡'
    bid_ratio = 0
    confidence = 0
    C_est = 0
    wa = 0
    wsd = 0
    slt = 0
    nppi_factor = 0
    analysis_data = {}

    if st.button("🚀 Run Advanced Analysis", type="primary", use_container_width=True):
        # Use selected cost
        C_est = selected_cost
        
        if C_est == 0:
            C_est = official_estimate * get_config('fallback_estimated_cost_factor', 0.85, company_id)
            st.warning(f"⚠️ BOQ cost is zero. Using fallback cost: BDT {C_est:,.3f}")
        
        # NPPI
        nppi_engine = NPPIEngine(company_id=company_id, procurement_type=procurement_type,
                                 nppi_override=nppi_override)
        nppi_factor = nppi_engine.get_factor()
        
        # SLT
        slt_engine = SLTEngine(official_estimate, competitor_bids, nppi_factor, procurement_type)
        wa, wsd, slt = slt_engine.compute()
        
        # Optimal bid
        opt_engine = OptimumBidEngine(
            official_estimate=official_estimate,
            estimated_cost=C_est,
            competitor_bids=competitor_bids,
            slt_threshold=slt,
            nppi_factor=nppi_factor,
            risk_tolerance=risk_tolerance,
            procurement_type=procurement_type
        )
        optimal_bid = opt_engine.get_bid()
        
        # Win probability
        wp_engine = WinProbabilityEngine(
            bid_price=optimal_bid,
            official_estimate=official_estimate,
            competitor_bids=competitor_bids,
            historical_data=[],
            company_id=company_id,
            nppi_factor=nppi_factor
        )
        win_prob = wp_engine.get_win_probability(method='multi_factor')
        confidence = wp_engine.get_confidence()
        
        # Calculate profit using actual cost
        profit = optimal_bid - C_est
        ev = profit * win_prob
        
        # Risk level
        bid_ratio = optimal_bid / official_estimate
        risk_thresholds = get_config('risk_thresholds', [0.85, 0.89, 0.93, 0.96], company_id)
        risk_labels = get_config('risk_labels', ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'MEDIUM-LOW', 'LOW'], company_id)
        risk_colors = get_config('risk_colors', ['🔴', '🟠', '🟡', '🟢', '🔵'], company_id)
        for i, th in enumerate(risk_thresholds):
            if bid_ratio < th:
                risk_level = risk_labels[i]
                risk_color = risk_colors[i]
                break
        else:
            risk_level = risk_labels[-1]
            risk_color = risk_colors[-1]
        
        # Display results
        st.markdown("---")
        st.markdown("## 📊 Advanced Analysis Results")
        
        # Cost breakdown
        st.markdown("### 💰 Cost Breakdown")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 BOQ Cost", f"BDT {C_est:,.3f}")
        with col2:
            st.metric("💰 Optimal Bid", f"BDT {optimal_bid:,.3f}", f"{bid_ratio*100:.1f}% of OCE")
        with col3:
            profit_color = "normal" if profit > 0 else "inverse"
            st.metric("📈 Expected Profit", f"BDT {profit:,.3f}", delta_color=profit_color)
        with col4:
            st.metric("💹 Expected Value", f"BDT {ev:,.3f}")
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Win Probability", f"{win_prob*100:.0f}%")
        col2.metric("Risk Level", f"{risk_color} {risk_level}")
        col3.metric("Confidence", f"{confidence*100:.0f}%")
        col4.metric("Competitors", len(competitor_bids))
        
        st.markdown("#### SLT & NPPI")
        st.write(f"**SLT Threshold:** BDT {slt:,.3f}")
        st.write(f"**NPPI Factor:** {nppi_factor:.4f}")
        st.write(f"**Weighted Average (WA):** BDT {wa:,.3f}")
        st.write(f"**Weighted Std Dev (WSD):** BDT {wsd:,.3f}")
        
        # Save to session
        analysis_data = {
            'tender_id': tender_id,
            'tender_title': tender_title,
            'official_estimate': official_estimate,
            'procurement_type': procurement_type,
            'recommended_bid': optimal_bid,
            'win_probability': win_prob,
            'risk_level': risk_level,
            'expected_profit': profit,
            'expected_value': ev,
            'nppi_factor': nppi_factor,
            'slt_threshold': slt,
            'competitor_count': len(competitor_bids),
            'cost_profile': cost_profile,
            'boq_cost': C_est,
            'confidence_score': confidence,
            'bid_ratio': bid_ratio,
            'weighted_average': wa,
            'weighted_std_dev': wsd,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state.advanced_result = analysis_data

    # ✅ Export Options (outside the button block, using session state)
    if st.session_state.get('advanced_result'):
        result = st.session_state.advanced_result
        
        st.markdown("---")
        st.markdown("### 📄 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generate HTML Report", use_container_width=True):
                try:
                    from modules.html_report_generator import generate_analysis_report
                    
                    user_info = {
                        'full_name': st.session_state.get('full_name', 'User'),
                        'company_name': st.session_state.get('company_name', 'N/A')
                    }
                    
                    report_buffer = generate_analysis_report(result, user_info, tier="advanced")
                    
                    st.download_button(
                        "📥 Download Advanced Analysis Report",
                        report_buffer,
                        f"advanced_analysis_{result.get('tender_id', 'report')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        "text/html",
                        use_container_width=True,
                        key="download_advanced_html"
                    )
                    st.success("✅ HTML Report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating HTML report: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col2:
            data = {
                'Metric': ['Optimal Bid', 'Bid Ratio', 'Win Probability', 'Expected Profit', 
                          'Risk Level', 'SLT Threshold', 'NPPI Factor', 'Confidence Score', 'BOQ Cost'],
                'Value': [
                    result.get('recommended_bid', 0),
                    f"{result.get('bid_ratio', 0):.3f}",
                    f"{result.get('win_probability', 0):.3f}",
                    result.get('expected_profit', 0),
                    result.get('risk_level', 'MEDIUM'),
                    result.get('slt_threshold', 0),
                    result.get('nppi_factor', 0),
                    result.get('confidence_score', 0),
                    result.get('boq_cost', 0)
                ]
            }
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False)
            st.download_button(
                "📊 Export CSV", 
                csv, 
                f"advanced_analysis_{result.get('tender_id', 'report')}_{datetime.now().strftime('%Y%m%d')}.csv", 
                "text/csv",
                use_container_width=True,
                key="download_advanced_csv"
            )