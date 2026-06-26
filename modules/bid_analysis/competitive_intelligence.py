# modules/bid_analysis/competitive_intelligence.py - COMPLETE FIXED VERSION

import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
from modules.bid_analysis.bid_core import (
    CostEngine, NPPIEngine, SLTEngine, CompetitorEngine,
    WinProbabilityEngine, OptimumBidEngine, get_config, get_nested_config, get_nppi_range
)
from modules.rbac import render_role_badge
from modules.subscription_manager import check_subscription_access
from modules.tender_selector_helper import render_tender_selector_with_boq
from modules.competitor_selector import (
    render_competitor_selector,
    get_selected_competitor_bids
)
import random


def render_competitive_intelligence(db=None, subscription_manager=None):
    st.markdown("## 🧠 Competitive Intelligence")
    st.markdown("*Full scenario-based bid optimisation with three cost levels*")
    render_role_badge()

    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)
    if not has_access:
        st.warning(msg)
        st.info("Upgrade to use Competitive Intelligence (8 credits).")
        return

    # Tender selection
    tender_data = render_tender_selector_with_boq(db, company_id)
    
    if not tender_data:
        st.info("Please select a tender with BOQ to proceed.")
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
    
    if not items:
        st.warning("No BOQ items found. Competitive Intelligence requires BOQ items.")
        st.info("Please generate a BOQ with items for this tender first.")
        if st.button("📊 Go to BOQ Generator"):
            st.session_state.page = "boq_generator"
            st.rerun()
        return
    
    # Get three-level costs
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
    st.caption(f"BOQ #{boq.get('id')} - {len(items)} items")
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
    
    # Compute three costs from BOQ items
    cost_agg = total_aggressive or total_estimated_cost
    cost_comp = total_competitive or total_estimated_cost
    cost_std = total_standard or total_estimated_cost
    
    # Show cost breakdown
    st.markdown("### 💰 Cost Breakdown from BOQ")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Aggressive Cost", f"BDT {cost_agg:,.3f}")
    with col2:
        st.metric("🟡 Competitive Cost", f"BDT {cost_comp:,.3f}")
    with col3:
        st.metric("🔴 Standard Cost", f"BDT {cost_std:,.3f}")
    
    # Check if costs are valid
    if cost_agg == 0 and cost_comp == 0 and cost_std == 0:
        st.error("⚠️ All costs are zero! Please check BOQ items and rate books.")
        st.info("Make sure you have rate books with pricing levels (Aggressive, Competitive, Standard).")
        return
    
    # Risk Tolerance
    risk_tolerance = st.select_slider(
        "Risk Tolerance (applied to all profiles)",
        options=['aggressive', 'moderate', 'conservative'],
        value='moderate',
        format_func=lambda x: {'aggressive': '🎯 Aggressive', 'moderate': '⚖️ Moderate', 'conservative': '🛡️ Conservative'}.get(x, x)
    )
    
    # ===== COMPETITOR SOURCE =====
    st.markdown("---")
    st.markdown("### 👥 Competitor Source")
    st.info(f"📌 Filtering competitors by procurement type: **{procurement_type.upper()}**")
    
    competitor_source = st.radio(
        "Competitor Source",
        ["Auto-generate", "Select from database"],
        index=0,
        key="ci_comp_source"
    )
    
    profiles = []
    if competitor_source == "Select from database":
        selected_competitors, stats = render_competitor_selector(
            db=db,
            company_id=company_id,
            procurement_type=procurement_type,
            title="👥 Select Competitors",
            show_table=True,
            multi_select=True,
            max_select=20
        )
        
        if selected_competitors:
            profiles = selected_competitors
            st.success(f"✅ Selected {len(profiles)} competitors for simulation")
        else:
            st.warning("No competitors selected. Switching to auto-generate.")
            competitor_source = "Auto-generate"
    
    # Scenario parameters
    st.markdown("---")
    st.markdown("### ⚙️ Scenario Parameters")
    col1, col2 = st.columns(2)
    with col1:
        min_competitors = st.number_input("Min Competitors", min_value=1, max_value=50, value=5)
        max_competitors = st.number_input("Max Competitors", min_value=min_competitors+1, max_value=100, value=19)
        num_scenarios = st.slider("Number of competitor steps", min_value=1, max_value=20, value=9)
        competitor_counts = np.linspace(min_competitors, max_competitors, num_scenarios, dtype=int).tolist()
    with col2:
        nppi_min_default, nppi_max_default = get_nppi_range(procurement_type, company_id)
        nppi_min = st.number_input(
            "NPPI Min", 
            min_value=0.85, 
            max_value=0.98, 
            value=float(nppi_min_default),
            step=0.001, 
            format="%.3f"
        )
        nppi_max = st.number_input(
            "NPPI Max", 
            min_value=nppi_min, 
            max_value=0.98, 
            value=float(nppi_max_default),
            step=0.001, 
            format="%.3f"
        )
        nppi_steps = st.slider("NPPI steps", min_value=1, max_value=10, value=5)
        nppi_values = np.linspace(nppi_min, nppi_max, nppi_steps).tolist()
    
    bidding_pattern = st.selectbox("Bidding Pattern", ['realistic', 'aggressive', 'conservative', 'uniform'], index=0)
    ai_strategy = st.selectbox("AI Strategy", ['weighted_ensemble', 'conservative', 'aggressive', 'statistical', 'ml_style'], index=0)

    # ✅ Initialize variables outside the button block
    recommendations = {}
    unified = {}
    scenario_data = []
    cost_agg_used = cost_agg
    cost_comp_used = cost_comp
    cost_std_used = cost_std
    analysis_data = {}

    if st.button("🚀 Run Competitive Intelligence", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_scenarios = len(competitor_counts) * len(nppi_values)
        status_text.text(f"Generating {total_scenarios} scenarios with risk tolerance: {risk_tolerance}...")
        results_by_profile = {
            'aggressive': [],
            'competitive': [],
            'standard': []
        }
        scenario_data = []

        for i, n_comp in enumerate(competitor_counts):
            for j, nppi_val in enumerate(nppi_values):
                if competitor_source == "Select from database" and profiles:
                    if n_comp <= len(profiles):
                        sampled = random.sample(profiles, n_comp)
                    else:
                        sampled = random.choices(profiles, k=n_comp)
                    comp_bids = get_selected_competitor_bids(sampled, official_estimate)
                else:
                    comp_bids = CompetitorEngine.generate(
                        n_comp, official_estimate,
                        min_price_pct=get_config('default_min_price_pct', 0.88, company_id),
                        max_price_pct=get_config('default_max_price_pct', 1.08, company_id),
                        pattern=bidding_pattern,
                        random_seed=42 + i*100 + j
                    )
                
                slt_engine = SLTEngine(official_estimate, comp_bids, nppi_val, procurement_type)
                wa, wsd, slt = slt_engine.compute()

                for profile, cost in [('aggressive', cost_agg), ('competitive', cost_comp), ('standard', cost_std)]:
                    opt_engine = OptimumBidEngine(
                        official_estimate, cost, comp_bids, slt, nppi_val, risk_tolerance, procurement_type
                    )
                    bid = opt_engine.get_bid()
                    wp_engine = WinProbabilityEngine(bid, official_estimate, comp_bids,
                                                     historical_data=[],
                                                     company_id=company_id,
                                                     nppi_factor=nppi_val)
                    win_prob = wp_engine.get_win_probability(method='multi_factor')
                    profit = bid - cost
                    ev = profit * win_prob
                    bid_ratio = bid / official_estimate
                    risk_thresholds = get_config('risk_thresholds', [0.85, 0.89, 0.93, 0.96], company_id)
                    risk_labels = get_config('risk_labels', ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'MEDIUM-LOW', 'LOW'], company_id)
                    for idx, th in enumerate(risk_thresholds):
                        if bid_ratio < th:
                            risk_level = risk_labels[idx]
                            break
                    else:
                        risk_level = risk_labels[-1]
                    
                    results_by_profile[profile].append({
                        'competitors': n_comp,
                        'nppi': nppi_val,
                        'bid': bid,
                        'win_prob': win_prob,
                        'profit': profit,
                        'ev': ev,
                        'risk_level': risk_level
                    })
                scenario_data.append({
                    'competitors': n_comp,
                    'nppi': nppi_val,
                    'slt': slt,
                    'wa': wa,
                    'wsd': wsd
                })
                progress = (i * len(nppi_values) + j + 1) / total_scenarios
                progress_bar.progress(progress)
                status_text.text(f"Processed scenario {i*len(nppi_values)+j+1}/{total_scenarios}")

        progress_bar.empty()
        status_text.text("Aggregating results...")

        # Aggregate per profile
        recommendations = {}
        for profile, results in results_by_profile.items():
            if results:
                bids = [r['bid'] for r in results]
                wins = [r['win_prob'] for r in results]
                profits = [r['profit'] for r in results]
                evs = [r['ev'] for r in results]
                weights = [r['competitors'] for r in results]
                total_w = sum(weights)
                if total_w > 0:
                    avg_bid = sum(b * w for b, w in zip(bids, weights)) / total_w
                    avg_win = sum(wp * w for wp, w in zip(wins, weights)) / total_w
                    avg_profit = sum(p * w for p, w in zip(profits, weights)) / total_w
                    avg_ev = sum(ev * w for ev, w in zip(evs, weights)) / total_w
                else:
                    avg_bid = np.mean(bids)
                    avg_win = np.mean(wins)
                    avg_profit = np.mean(profits)
                    avg_ev = np.mean(evs)
                avg_bid_ratio = avg_bid / official_estimate
                risk_thresholds = get_config('risk_thresholds', [0.85, 0.89, 0.93, 0.96], company_id)
                risk_labels = get_config('risk_labels', ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'MEDIUM-LOW', 'LOW'], company_id)
                for idx, th in enumerate(risk_thresholds):
                    if avg_bid_ratio < th:
                        agg_risk = risk_labels[idx]
                        break
                else:
                    agg_risk = risk_labels[-1]
                recommendations[profile] = {
                    'bid': avg_bid,
                    'win_prob': avg_win,
                    'profit': avg_profit,
                    'ev': avg_ev,
                    'risk_level': agg_risk
                }

        # Unified recommendation
        best_profile = max(recommendations, key=lambda p: recommendations[p]['ev'])
        unified = recommendations[best_profile]
        unified['profile'] = best_profile

        st.markdown("---")
        st.markdown("## 📊 Competitive Intelligence Results")

        # Store in session
        analysis_data = {
            'tender_id': tender_id,
            'tender_title': tender_title,
            'official_estimate': official_estimate,
            'procurement_type': procurement_type,
            'recommended_bid': unified.get('bid', 0),
            'win_probability': unified.get('win_prob', 0),
            'risk_level': unified.get('risk_level', 'MEDIUM'),
            'expected_profit': unified.get('profit', 0),
            'expected_value': unified.get('ev', 0),
            'recommendations': recommendations,
            'unified': unified,
            'scenario_count': len(competitor_counts) * len(nppi_values),
            'competitor_range': f"{min_competitors}-{max_competitors}",
            'nppi_range': f"{nppi_min}-{nppi_max}",
            'risk_tolerance': risk_tolerance,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state.competitive_intel_results = analysis_data

        # Display
        st.markdown("### Three Cost Profile Recommendations (Risk Tolerance: {})".format(risk_tolerance.upper()))
        
        # Build DataFrame with correct values
        df_data = []
        for profile, data in recommendations.items():
            if profile == 'aggressive':
                cost = cost_agg
            elif profile == 'competitive':
                cost = cost_comp
            else:
                cost = cost_std
            
            bid = data.get('bid', 0)
            win_prob = data.get('win_prob', 0) * 100
            profit = bid - cost
            ev = data.get('ev', 0)
            risk = data.get('risk_level', 'MEDIUM')
            
            df_data.append({
                'Profile': profile.capitalize(),
                'Cost': f"BDT {cost:,.3f}",
                'Bid': f"BDT {bid:,.3f}",
                'Profit': f"BDT {profit:,.3f}",
                'Win Prob': f"{win_prob:.1f}%",
                'EV': f"BDT {ev:,.3f}",
                'Risk': risk
            })
        
        df_profiles = pd.DataFrame(df_data)
        st.dataframe(df_profiles, use_container_width=True, hide_index=True)

        st.markdown("### 🏆 Unified Recommendation")
        
        # Get unified recommendation with correct values
        best_profile = unified.get('profile', 'competitive')
        best_bid = unified.get('bid', 0)
        best_win = unified.get('win_prob', 0) * 100
        best_ev = unified.get('ev', 0)
        best_risk = unified.get('risk_level', 'MEDIUM')
        
        # Get cost for best profile
        if best_profile == 'aggressive':
            best_cost = cost_agg
        elif best_profile == 'competitive':
            best_cost = cost_comp
        else:
            best_cost = cost_std
        
        best_profit = best_bid - best_cost
        
        st.success(f"**Recommended Profile:** {best_profile.upper()}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Optimal Bid", f"BDT {best_bid:,.3f}")
        col2.metric("Cost", f"BDT {best_cost:,.3f}")
        col3.metric("Expected Profit", f"BDT {best_profit:,.3f}")
        col4.metric("Expected Value", f"BDT {best_ev:,.3f}")
        
        st.write(f"**Risk Level:** {best_risk}")
        st.write(f"**Win Probability:** {best_win:.1f}%")

    # ✅ Export Options (outside the button block, using session state)
    if st.session_state.get('competitive_intel_results'):
        result = st.session_state.competitive_intel_results
        recommendations = result.get('recommendations', {})
        unified = result.get('unified', {})
        
        st.markdown("---")
        st.markdown("### 📄 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Generate HTML Report", use_container_width=True):
                try:
                    from modules.html_report_generator import generate_analysis_report
                    
                    # Prepare comprehensive report data
                    report_data = {
                        'tender_id': result.get('tender_id', 'N/A'),
                        'tender_title': result.get('tender_title', 'N/A'),
                        'official_estimate': result.get('official_estimate', 0),
                        'procurement_type': result.get('procurement_type', 'works'),
                        'recommended_bid': unified.get('bid', 0),
                        'win_probability': unified.get('win_prob', 0),
                        'risk_level': unified.get('risk_level', 'MEDIUM'),
                        'expected_profit': unified.get('profit', 0),
                        'expected_value': unified.get('ev', 0),
                        'recommendations': recommendations,
                        'unified': unified,
                        'scenario_count': result.get('scenario_count', 0),
                        'competitor_range': result.get('competitor_range', '5-19'),
                        'nppi_range': result.get('nppi_range', '0.920-0.942'),
                        'risk_tolerance': result.get('risk_tolerance', 'moderate'),
                        'boq_cost': cost_agg,
                        'analysis_date': result.get('analysis_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    }
                    
                    user_info = {
                        'full_name': st.session_state.get('full_name', 'User'),
                        'company_name': st.session_state.get('company_name', 'N/A')
                    }
                    
                    report_buffer = generate_analysis_report(report_data, user_info, tier="competitive")
                    
                    st.download_button(
                        "📥 Download Competitive Intel Report",
                        report_buffer,
                        f"competitive_intel_{result.get('tender_id', 'report')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        "text/html",
                        use_container_width=True,
                        key="download_competitive_html"
                    )
                    st.success("✅ HTML Report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating HTML report: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col2:
            export = {
                'inputs': {
                    'official_estimate': result.get('official_estimate', 0),
                    'procurement_type': result.get('procurement_type', 'works'),
                    'cost_profiles': {'aggressive': cost_agg, 'competitive': cost_comp, 'standard': cost_std},
                    'scenario_params': {
                        'min_competitors': min_competitors,
                        'max_competitors': max_competitors,
                        'nppi_min': nppi_min,
                        'nppi_max': nppi_max,
                        'pattern': bidding_pattern
                    },
                    'risk_tolerance': risk_tolerance
                },
                'recommendations': recommendations,
                'unified': unified,
                'scenarios': scenario_data
            }
            json_str = json.dumps(export, indent=2, default=str)
            st.download_button(
                "📊 Download JSON", 
                json_str, 
                f"competitive_intel_{result.get('tender_id', 'report')}_{datetime.now().strftime('%Y%m%d')}.json", 
                "application/json",
                use_container_width=True,
                key="download_competitive_json"
            )
        
        with col3:
            df_profiles_csv = pd.DataFrame.from_dict(recommendations, orient='index')
            df_profiles_csv['bid'] = df_profiles_csv['bid'].apply(lambda x: f"{x:,.3f}")
            df_profiles_csv['win_prob'] = df_profiles_csv['win_prob'].apply(lambda x: f"{x:.3f}")
            csv = df_profiles_csv.to_csv(index=True)
            st.download_button(
                "📊 Download CSV", 
                csv, 
                f"competitive_intel_profiles_{result.get('tender_id', 'report')}_{datetime.now().strftime('%Y%m%d')}.csv", 
                "text/csv",
                use_container_width=True,
                key="download_competitive_csv"
            )