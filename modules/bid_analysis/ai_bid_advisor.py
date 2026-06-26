# modules/bid_analysis/ai_bid_advisor.py - COMPLETE FIXED VERSION

import streamlit as st
from datetime import datetime
from modules.rbac import render_role_badge
from modules.subscription_manager import check_subscription_access


def render_ai_bid_advisor(db=None, subscription_manager=None):
    st.markdown("## 🤖 AI Bid Advisor")
    st.markdown("*Executive summary and strategic recommendation*")
    render_role_badge()

    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)
    if not has_access:
        st.warning(msg)
        st.info("AI Bid Advisor requires 10 credits.")
        return

    # ✅ Check which analysis results are available
    # ✅ Check which analysis results are available
    has_advanced_result = 'advanced_result' in st.session_state
    has_competitive_result = 'competitive_intel_results' in st.session_state
    
    if not has_advanced_result and not has_competitive_result:
        st.warning("⚠️ Please run Advanced Bid Analysis or Competitive Intelligence first.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📈 Run Advanced Bid Analysis", use_container_width=True):
                st.session_state.page = "advanced_bid"
                st.rerun()
        with col2:
            if st.button("🧠 Run Competitive Intelligence", use_container_width=True):
                st.session_state.page = "competitive_intel"
                st.rerun()
        return
    
    # ✅ Let user choose which analysis to use (if both available)
    if has_advanced_result and has_competitive_result:
        st.info("🎯 Both Advanced Bid Analysis and Competitive Intelligence results are available.")
        
        analysis_choice = st.radio(
            "Select analysis source for AI Advisor:",
            options=[
                ("🧠 Competitive Intelligence (More comprehensive, 8 credits)", "competitive"),
                ("📈 Advanced Bid Analysis (PPR compliant, 3 credits)", "advanced")
            ],
            index=0,
            format_func=lambda x: x[0]
        )
        
        selected_tier = analysis_choice[1]
        
        if selected_tier == "competitive":
            results = st.session_state.competitive_intel_results
            analysis_type = "Competitive Intelligence"
            tier = "competitive"
        else:
            results = st.session_state.advanced_result
            analysis_type = "Advanced Bid Analysis"
            tier = "advanced"
    elif has_competitive_result:
        results = st.session_state.competitive_intel_results
        analysis_type = "Competitive Intelligence"
        tier = "competitive"
    else:
        results = st.session_state.advanced_result
        analysis_type = "Advanced Bid Analysis"
        tier = "advanced"

    
    # ✅ Extract data with proper fallbacks
    unified = results.get('unified', {})
    recommendations = results.get('recommendations', {})
    inputs = results.get('inputs', {})
    
    # Get unified recommendation
    profile = unified.get('profile', 'competitive')
    bid = unified.get('bid', 0)
    win_prob = unified.get('win_prob', 0)
    profit = unified.get('profit', 0)
    risk = unified.get('risk_level', 'MEDIUM')
    
    # If no unified data, try to get from top-level
    if bid == 0:
        bid = results.get('recommended_bid', 0)
        win_prob = results.get('win_probability', 0)
        profit = results.get('expected_profit', 0)
        risk = results.get('risk_level', 'MEDIUM')
    
    # Get inputs
    official_estimate = inputs.get('official_estimate', 0)
    if official_estimate == 0:
        official_estimate = results.get('official_estimate', 0)
    
    procurement_type = inputs.get('procurement_type', 'works')
    risk_tolerance = inputs.get('risk_tolerance', 'moderate')
    
    # Get tender info
    tender_id = results.get('tender_id', 'N/A')
    tender_title = results.get('tender_title', 'N/A')
    
    # Get three cost profiles if available
    cost_profiles = inputs.get('cost_profiles', {})
    cost_agg = cost_profiles.get('aggressive', 0)
    cost_comp = cost_profiles.get('competitive', 0)
    cost_std = cost_profiles.get('standard', 0)
    
    # Calculate bid ratio
    bid_ratio = (bid / official_estimate - 1) * 100 if official_estimate > 0 else 0
    
    # ✅ Generate AI Summary
    summary = f"Bid {abs(bid_ratio):.2f}% {'below' if bid_ratio < 0 else 'above'} OCE using {profile.capitalize()} Cost Profile. "
    summary += f"Estimated win probability {win_prob*100:.0f}%. "
    summary += f"Expected profit BDT {profit:,.3f}. "
    summary += f"Risk {risk.lower()} with {risk_tolerance} risk tolerance."
    
    # ✅ Strategy recommendation
    if win_prob > 0.7:
        strategy = "🎯 **Aggressive win-focused strategy recommended.** High win probability justifies lower margin. Consider this if you need to secure the contract for strategic reasons."
    elif win_prob > 0.4:
        strategy = "⚖️ **Balanced approach recommended.** Moderate win probability with acceptable margin. This is suitable for most competitive tenders."
    else:
        strategy = "🛡️ **Conservative strategy advised.** Consider differentiating on quality, experience, or value-add services rather than price alone."
    
    # ✅ Risk analysis
    risk_analysis = f"""
    - **Risk Level:** {risk.upper()}
    - **Risk Tolerance Used:** {risk_tolerance.capitalize()}
    - Competitor density may force lower bids
    - Ensure cost estimates are accurate; variations can impact profitability
    - Market conditions may change before submission deadline
    """
    
    # ✅ Competitive insights (if available)
    competitive_insights = ""
    if analysis_type == "Competitive Intelligence":
        scenario_count = results.get('scenario_count', 0)
        competitor_range = results.get('competitor_range', 'N/A')
        nppi_range = results.get('nppi_range', 'N/A')
        
        competitive_insights = f"""
        - **Scenarios Analyzed:** {scenario_count}
        - **Competitor Range:** {competitor_range}
        - **NPPI Range:** {nppi_range}
        - **Cost Profiles Used:** Aggressive (BDT {cost_agg:,.3f}), Competitive (BDT {cost_comp:,.3f}), Standard (BDT {cost_std:,.3f})
        """
    
    # ✅ Three profile comparison
    profile_comparison = ""
    if recommendations:
        profile_comparison = f"""
        | Profile | Bid Amount | Win Probability | Expected Profit |
        |---------|------------|-----------------|-----------------|
        | Aggressive | BDT {recommendations.get('aggressive', {}).get('bid', 0):,.3f} | {recommendations.get('aggressive', {}).get('win_prob', 0)*100:.0f}% | BDT {recommendations.get('aggressive', {}).get('profit', 0):,.3f} |
        | Competitive | BDT {recommendations.get('competitive', {}).get('bid', 0):,.3f} | {recommendations.get('competitive', {}).get('win_prob', 0)*100:.0f}% | BDT {recommendations.get('competitive', {}).get('profit', 0):,.3f} |
        | Standard | BDT {recommendations.get('standard', {}).get('bid', 0):,.3f} | {recommendations.get('standard', {}).get('win_prob', 0)*100:.0f}% | BDT {recommendations.get('standard', {}).get('profit', 0):,.3f} |
        """
    
    # ✅ Store AI data for HTML report
    ai_data = {
        'summary': summary,
        'strategy': strategy,
        'metrics': {
            'bid': bid,
            'win_prob': win_prob,
            'profit': profit,
            'strategy': 'Balanced' if win_prob > 0.4 else 'Conservative',
            'confidence': int((0.7 + (win_prob * 0.3)) * 100)
        },
        'risk': risk.upper(),
        'analysis_type': analysis_type,
        'tier': tier,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # ✅ Display results
    st.markdown("---")
    st.markdown(f"### 📋 Executive Summary ({analysis_type})")
    
    # Show source of analysis
    if analysis_type == "Competitive Intelligence":
        st.info("🧠 This recommendation is based on **Competitive Intelligence** analysis with full scenario simulation.")
    else:
        st.info("📈 This recommendation is based on **Advanced Bid Analysis** with PPR 2025 compliance.")
    
    st.markdown(f"**Tender:** {tender_id} - {tender_title}")
    st.markdown(f"**Official Estimate:** BDT {official_estimate:,.3f}")
    st.markdown(f"**Analysis Date:** {ai_data['analysis_date']}")
    
    st.divider()
    
    # Executive Summary
    st.markdown("### 📌 Executive Summary")
    st.info(summary)

    st.markdown("### 💡 Recommended Strategy")
    st.markdown(strategy)

    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recommended Bid", f"BDT {bid:,.3f}")
    col2.metric("Win Probability", f"{win_prob*100:.0f}%")
    col3.metric("Expected Profit", f"BDT {profit:,.3f}")
    col4.metric("Risk Level", f"🟢 {risk.upper()}" if risk == 'LOW' else f"🟡 {risk.upper()}" if risk == 'MEDIUM' else f"🔴 {risk.upper()}")
    
    # Three profile comparison
    if profile_comparison:
        st.markdown("### 📊 Cost Profile Comparison")
        st.markdown(profile_comparison)

    st.markdown("### ⚠️ Key Risks")
    st.markdown(risk_analysis)

    # Competitive insights
    if competitive_insights:
        st.markdown("### 🔍 Competitive Intelligence Insights")
        st.markdown(competitive_insights)

    st.markdown("### 📌 Next Steps")
    st.markdown("""
    1. Review detailed analysis report for scenario breakdown
    2. Adjust bid if risk tolerance changes
    3. Prepare justification documentation for internal approval
    4. Monitor competitor activity before final submission
    5. Set up post-award evaluation tracking
    """)

    # ✅ Export Options
    st.markdown("---")
    st.markdown("### 📄 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Generate AI Report (HTML)", use_container_width=True, type="primary"):
            user_info = {
                'full_name': st.session_state.get('full_name', 'User'),
                'company_name': st.session_state.get('company_name', 'N/A')
            }
            from modules.html_report_generator import generate_analysis_report
            report_buffer = generate_analysis_report(ai_data, user_info, tier="ai")
            st.download_button(
                "📥 Download HTML Report",
                report_buffer,
                f"ai_advisor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                "text/html",
                use_container_width=True
            )
    
    with col2:
        if st.button("📋 Copy Summary", use_container_width=True):
            st.code(summary, language="text")
            st.success("✅ Summary copied to clipboard!")
            
            # Also copy the full recommendation
            full_text = f"""
TenderAI AI Bid Advisor Summary
{'='*50}

Tender: {tender_id} - {tender_title}
Analysis Type: {analysis_type}
Official Estimate: BDT {official_estimate:,.3f}

Recommendation:
{summary}

Strategy:
{strategy}

Key Metrics:
- Recommended Bid: BDT {bid:,.3f}
- Win Probability: {win_prob*100:.0f}%
- Expected Profit: BDT {profit:,.3f}
- Risk Level: {risk.upper()}

Generated: {ai_data['analysis_date']}
            """
            st.code(full_text, language="text")
            st.success("✅ Full summary copied to clipboard!")