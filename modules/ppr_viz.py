# modules/ppr_viz.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.rbac import can_view_reports, render_role_badge, require_permission


@require_permission('can_view_reports')
def render_ppr_compliance_viz(comparison: dict, tender_data: dict):
    """Interactive PPR 2025 Compliance Visualization with RBAC"""
    
    # Get user permissions
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Show role badge for context
    render_role_badge()
    
    st.markdown("### 📈 PPR 2025 Compliance Dashboard")
    
    # Check if user can view this sensitive data
    if not can_view_reports():
        st.error("🔒 You don't have permission to view compliance reports.")
        st.info("Contact your administrator to upgrade your permissions.")
        return
    
    # For viewers, show limited information
    is_viewer = user_role == 'viewer'
    
    # Safely extract data with defaults
    adv = comparison.get('advanced', comparison.get('basic', {}))
    rec_bid = adv.get('optimal_bid', 0)
    slt_threshold = adv.get('slt_threshold', 0)
    nppi = adv.get('nppi_factor', 0)
    est = tender_data.get('official_estimate', 1)
    
    # Handle competitor bids safely
    comp_bids = []
    competitor_bids_data = tender_data.get('competitor_bids', [])
    if competitor_bids_data:
        for cb in competitor_bids_data:
            if isinstance(cb, dict):
                bid = cb.get('bid', 0)
                if bid > 0:
                    comp_bids.append(float(bid))
            elif isinstance(cb, (int, float)):
                if cb > 0:
                    comp_bids.append(float(cb))
    
    is_compliant = rec_bid >= slt_threshold if slt_threshold > 0 else False
    status_color = "#10b981" if is_compliant else "#ef4444"
    status_label = "✅ PPR Compliant" if is_compliant else "⚠️ SLT Risk"
    
    # For viewers, show masked/anonymized data
    if is_viewer:
        rec_bid_display = rec_bid
        slt_display = slt_threshold
        # Mask competitor bids for viewers
        comp_bids_display = [b * 0.5 for b in comp_bids] if comp_bids else []
    else:
        rec_bid_display = rec_bid
        slt_display = slt_threshold
        comp_bids_display = comp_bids
    
    # 1. Compliance Gauge
    try:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=rec_bid_display,
            title={'text': "Recommended Bid vs SLT Threshold", 'font': {'size': 14}},
            delta={'reference': slt_display, 'relative': True, 'position': "top"},
            gauge={
                'axis': {'range': [slt_display * 0.9 if slt_display > 0 else 0, est], 'tickwidth': 1},
                'bar': {'color': status_color},
                'steps': [
                    {'range': [0, slt_display], 'color': '#fee2e2' if slt_display > 0 else '#e5e7eb'}, 
                    {'range': [slt_display, est], 'color': '#dcfce7'}
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': slt_display}
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render compliance gauge: {e}")
    
    # 2. Bid Distribution
    if comp_bids_display:
        try:
            fig_dist = go.Figure()
            # For viewers, add note that values are masked
            if is_viewer:
                st.caption("🔒 Competitor bid values are masked for viewer access")
            
            fig_dist.add_trace(go.Box(y=comp_bids_display, name='Competitor Bids', marker_color='#3b82f6'))
            fig_dist.add_trace(go.Box(y=[rec_bid_display], name='Our Recommended', marker_color=status_color))
            if slt_display > 0:
                fig_dist.add_hline(y=slt_display, line_dash="dash", line_color="red", annotation_text="SLT Threshold")
            fig_dist.update_layout(title="Bid Distribution vs SLT Threshold", yaxis_title="Bid Amount (BDT)", height=300)
            st.plotly_chart(fig_dist, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render bid distribution: {e}")
    
    # 3. Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("SLT Threshold", f"BDT {slt_display:,.3f}" if slt_display > 0 else "N/A")
    
    with col2:
        if is_compliant:
            st.metric("Recommended Bid", f"BDT {rec_bid_display:,.3f}", 
                     delta=f"{(rec_bid_display-slt_display)/slt_display*100:.1f}% above SLT" if slt_display > 0 else None, 
                     delta_color="normal")
        else:
            st.metric("Recommended Bid", f"BDT {rec_bid_display:,.3f}", 
                     delta="Below SLT" if slt_display > 0 else None, 
                     delta_color="inverse")
    
    with col3:
        st.metric("NPPI Factor", f"{nppi:.3f}", help="National Public Procurement Price Index")
    
    with col4:
        st.markdown(f"""
        <div style="background:{status_color}20; padding:10px; border-radius:8px; border:1px solid {status_color}; text-align:center;">
            <strong style="color:{status_color}; font-size:1.1em;">{status_label}</strong><br>
            <small>PPR 2025 Clause 49</small>
        </div>""", unsafe_allow_html=True)
    
    # 4. Calculation Breakdown (only for non-viewers)
    if not is_viewer:
        with st.expander("🔍 View PPR 2025 Calculation Breakdown", expanded=False):
            st.markdown("`X̄ = 0.5(Avg Comp) + 0.2(Estimate) + 0.3(NPPI)` → `SLT = X̄ - Sd`")
            
            # Prepare breakdown data
            avg_competitor = sum(comp_bids) / len(comp_bids) if comp_bids else 0
            nppi_price = est * nppi
            weighted_avg = adv.get('weighted_average', 0)
            weighted_std = adv.get('weighted_std_dev', 0)
            
            breakdown_data = {
                'Component': ['Avg Competitor', 'Official Estimate', 'NPPI Price', 'Weighted Avg (X̄)', 'Std Dev (Sd)', 'SLT Threshold'],
                'Value': [
                    f"BDT {avg_competitor:,.3f}" if comp_bids else "N/A",
                    f"BDT {est:,.3f}",
                    f"BDT {nppi_price:,.3f}",
                    f"BDT {weighted_avg:,.3f}" if weighted_avg > 0 else "N/A",
                    f"{weighted_std:.3f}" if weighted_std > 0 else "N/A",
                    f"BDT {slt_display:,.3f}" if slt_display > 0 else "N/A"
                ]
            }
            
            st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)
            
            # Show formula explanation
            with st.expander("📖 PPR 2025 Formula Explanation", expanded=False):
                st.markdown("""
                **PPR 2025 (Public Procurement Rules 2025) Compliance Metrics:**
                
                - **NPPI (Non-performing Price Index)**: 28-day market average (default: 0.92)
                - **X̄ (Weighted Average)**: `0.5(Avg Competitor) + 0.2(Official Estimate) + 0.3(NPPI Price)`
                - **Sd (Standard Deviation)**: Statistical measure of bid variance
                - **SLT (Standard Learning Threshold)**: `X̄ - Sd` (Minimum acceptable bid)
                
                **Compliance Rule:** Recommended bid must be ≥ SLT threshold
                """)
    else:
        # For viewers, show limited breakdown
        with st.expander("ℹ️ PPR 2025 Compliance Information", expanded=False):
            st.info("""
            **PPR 2025 (Public Procurement Rules 2025) Compliance**
            
            The SLT (Standard Learning Threshold) ensures bids are not abnormally low.
            Your recommended bid is compared against the SLT threshold for compliance.
            
            Contact your administrator for detailed calculations.
            """)
    
    # Add export option for authorized users
    if can_view_reports() and not is_viewer:
        st.markdown("---")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            # Export as CSV
            export_data = {
                'Metric': ['Recommended Bid', 'SLT Threshold', 'NPPI Factor', 'Is Compliant', 
                          'Official Estimate', 'Number of Competitors'],
                'Value': [rec_bid, slt_threshold, nppi, is_compliant, est, len(comp_bids)]
            }
            export_df = pd.DataFrame(export_data)
            csv = export_df.to_csv(index=False)
            st.download_button(
                "📥 Export Data",
                csv,
                f"ppr_compliance_{tender_data.get('tender_id', 'report')}.csv",
                "text/csv",
                use_container_width=True
            )
        with col3:
            if st.button("📊 Full Report", use_container_width=True):
                st.session_state.show_full_ppr_report = True
                st.rerun()