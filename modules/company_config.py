# pages/company_config.py

import streamlit as st
from modules.bid_analysis.bid_core import get_config_manager, HARDCODED_DEFAULTS
from modules.rbac import render_role_badge

def render_company_config(db):
    st.title("⚙️ Company Configuration")
    render_role_badge()
    
    user_role = st.session_state.get('user_role', 'viewer')
    company_id = st.session_state.get('company_id')
    
    if user_role not in ['company_admin', 'admin', 'system_admin']:
        st.error("🔒 Company Admin access required")
        return
    
    if not company_id:
        st.error("No company found")
        return
    
    manager = get_config_manager(db)
    all_configs = manager.get_all_company_configs(company_id)
    
    st.subheader("📊 Bid Analysis Configuration")
    st.caption("These settings override system defaults for your company only.")
    
    # Group configs by category
    categories = {
        "NPPI Settings": [
            ('default_nppi_goods', 'Default NPPI for Goods', 'number'),
            ('default_nppi_works', 'Default NPPI for Works', 'number'),
            ('default_nppi_services', 'Default NPPI for Services', 'number'),
            ('nppi_range_min', 'NPPI Range Min (Advanced/Competitive)', 'number'),
            ('nppi_range_max', 'NPPI Range Max (Advanced/Competitive)', 'number'),
        ],
        "Competitor Settings": [
            ('fallback_mean_competitor_ratio', 'Mean Competitor Ratio Fallback', 'number'),
            ('fallback_std_competitor_ratio', 'Std Dev Competitor Ratio Fallback', 'number'),
            ('default_competitor_min', 'Default Min Competitors (Simulator)', 'number'),
            ('default_competitor_max', 'Default Max Competitors (Simulator)', 'number'),
        ],
        "Risk Settings": [
            ('risk_multipliers', 'Risk Multipliers (Aggressive/Moderate/Conservative)', 'json'),
            ('risk_thresholds', 'Risk Level Thresholds', 'json'),
            ('risk_labels', 'Risk Level Labels', 'json'),
        ],
        "Cost & Profit Settings": [
            ('fallback_estimated_cost_factor', 'Estimated Cost Factor (when no BOQ)', 'number'),
            ('default_cost_profile', 'Default Cost Profile', 'string'),
        ],
        "SLT Settings": [
            ('slt_weight_mean_competitor', 'SLT Weight: Mean Competitor', 'number'),
            ('slt_weight_official_estimate', 'SLT Weight: Official Estimate', 'number'),
            ('slt_weight_nppi_price', 'SLT Weight: NPPI Price', 'number'),
            ('slt_threshold_multiplier', 'SLT Threshold Multiplier', 'number'),
            ('bid_upper_clamp_factor', 'Max Bid as % of OCE', 'number'),
        ],
        "Win Probability Settings": [
            ('win_probability_clamp_min', 'Win Probability Min Clamp', 'number'),
            ('win_probability_clamp_max', 'Win Probability Max Clamp', 'number'),
            ('confidence_base', 'Base Confidence Score', 'number'),
            ('confidence_bonus_competitor_count', 'Confidence Bonus: Competitor Count', 'number'),
        ],
        "Competitor Generation": [
            ('beta_alpha_realistic', 'Beta Alpha (Realistic Pattern)', 'number'),
            ('beta_beta_realistic', 'Beta Beta (Realistic Pattern)', 'number'),
            ('triangular_low_aggressive', 'Triangular Low (Aggressive Pattern)', 'number'),
            ('triangular_peak_aggressive', 'Triangular Peak (Aggressive Pattern)', 'number'),
            ('triangular_high_aggressive', 'Triangular High (Aggressive Pattern)', 'number'),
            ('normal_mean_conservative', 'Normal Mean (Conservative Pattern)', 'number'),
            ('normal_std_conservative', 'Normal Std Dev (Conservative Pattern)', 'number'),
        ],
    }
    
    for category, configs in categories.items():
        with st.expander(f"📂 {category}", expanded=False):
            for key, label, config_type in configs:
                # Get current value (company override, system, or default)
                current_value = manager.get(key, company_id)
                if current_value is None:
                    current_value = HARDCODED_DEFAULTS.get(key)
                
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**{label}**")
                    st.caption(f"Key: `{key}`")
                
                with col2:
                    if config_type == 'json':
                        if isinstance(current_value, (dict, list)):
                            new_value = st.text_area(
                                "Value (JSON)",
                                value=json.dumps(current_value, indent=2),
                                key=f"company_{key}",
                                height=100
                            )
                        else:
                            new_value = st.text_area(
                                "Value (JSON)",
                                value=str(current_value),
                                key=f"company_{key}",
                                height=100
                            )
                    elif config_type == 'number':
                        new_value = st.number_input(
                            "Value",
                            value=float(current_value) if current_value is not None else 0.0,
                            step=0.001,
                            key=f"company_{key}",
                            format="%.3f"
                        )
                    else:
                        new_value = st.text_input(
                            "Value",
                            value=str(current_value) if current_value is not None else '',
                            key=f"company_{key}"
                        )
                
                with col3:
                    if st.button("💾 Save", key=f"save_company_{key}"):
                        if config_type == 'json':
                            try:
                                parsed = json.loads(new_value)
                                manager.set_company_config(company_id, key, parsed, 
                                                           description=label,
                                                           user_id=st.session_state.get('user_id'))
                                st.success(f"✅ Saved {key}")
                                st.rerun()
                            except json.JSONDecodeError:
                                st.error("Invalid JSON format")
                        else:
                            manager.set_company_config(company_id, key, new_value,
                                                       description=label,
                                                       user_id=st.session_state.get('user_id'))
                            st.success(f"✅ Saved {key}")
                            st.rerun()
                    
                    # Reset to default
                    if st.button("🔄 Reset", key=f"reset_company_{key}"):
                        manager.delete_company_config(company_id, key)
                        st.success(f"✅ Reset {key} to default")
                        st.rerun()
    
    # Show summary of all company configs
    st.divider()
    st.subheader("📋 Current Company Configuration Summary")
    
    if all_configs:
        df = pd.DataFrame([
            {'Key': k, 'Value': str(v)[:100]} 
            for k, v in all_configs.items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No company-specific configurations set. Using system defaults.")