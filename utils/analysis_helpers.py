# utils/analysis_helpers.py

import streamlit as st
import pandas as pd
import json
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from config import DEBUG_MODE, debug_print, COST_ESTIMATE_RATIO, BID_AMOUNT_DECIMALS
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def load_tender_into_form(tender_data):
    """Load tender data into session state model"""
    st.session_state.tender_form_data.update({
        'tender_id': str(tender_data.get('tender_id', '')),
        'tender_title': str(tender_data.get('tender_title', '')),
        'procuring_entity': str(tender_data.get('procuring_entity', '')),
        'division': str(tender_data.get('division', 'Dhaka')),
        'district': str(tender_data.get('district', '')),
        'thana': str(tender_data.get('thana', '')),
        'official_estimate': float(tender_data.get('official_estimate', 0) or 0),
        'tender_security': float(tender_data.get('tender_security', 0) or 0),
        'document_fee': float(tender_data.get('document_fee', 0) or 0),
        'procurement_type': str(tender_data.get('procurement_type', 'works'))
    })

def sync_form_to_model():
    """Sync form widget values to the model before rerun"""
    data = st.session_state.tender_form_data
    data['tender_id'] = st.session_state.get('input_tender_id', data['tender_id'])
    data['tender_title'] = st.session_state.get('input_tender_title', data['tender_title'])
    data['procuring_entity'] = st.session_state.get('input_procuring_entity', data['procuring_entity'])
    data['division'] = st.session_state.get('input_division', data['division'])
    data['district'] = st.session_state.get('input_district', data['district'])
    data['thana'] = st.session_state.get('input_thana', st.session_state.get('input_thana_text', data['thana']))
    data['official_estimate'] = st.session_state.get('input_official_estimate', data['official_estimate'])
    data['tender_security'] = st.session_state.get('input_tender_security', data['tender_security'])
    data['document_fee'] = st.session_state.get('input_document_fee', data['document_fee'])
    data['procurement_type'] = st.session_state.get('input_procurement_type', data['procurement_type'])
    data['risk_tolerance'] = st.session_state.get('analysis_risk_tolerance', data['risk_tolerance'])

def model_to_form():
    """Push model values to form widgets"""
    st.session_state.input_tender_id = st.session_state.tender_form_data['tender_id']
    st.session_state.input_tender_title = st.session_state.tender_form_data['tender_title']
    st.session_state.input_procuring_entity = st.session_state.tender_form_data['procuring_entity']
    st.session_state.input_division = st.session_state.tender_form_data['division']
    st.session_state.input_district = st.session_state.tender_form_data['district']
    st.session_state.input_thana = st.session_state.tender_form_data['thana']
    st.session_state.input_official_estimate = st.session_state.tender_form_data['official_estimate']
    st.session_state.input_tender_security = st.session_state.tender_form_data['tender_security']
    st.session_state.input_document_fee = st.session_state.tender_form_data['document_fee']
    st.session_state.input_procurement_type = st.session_state.tender_form_data['procurement_type']
    st.session_state.analysis_risk_tolerance = st.session_state.tender_form_data['risk_tolerance']
# utils/analysis_helpers.py

def ensure_admin_premium():
    """Force admin to have professional plan for testing"""
    if st.session_state.get('logged_in') and st.session_state.get('user_role') in ['admin', 'system_admin']:
        user_id = st.session_state.user_id
        company_id = st.session_state.get('company_id')
        
        # ✅ Check user subscription first
        sub = db.get_user_subscription(user_id)
        
        if sub.get('subscription_tier') == 'free':
            # ✅ Try to update user subscription
            success = db.update_user_subscription(user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            
            # ✅ If no user subscription, try company subscription
            if not success and company_id:
                success = db.update_company_subscription(company_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            
            if success:
                st.session_state.subscription_plan = 'professional'
                debug_print("🎁 Auto-upgraded admin to professional plan")
                return True
    
    return False

def _save_analysis_callback():
    """Callback function for the Save button - preserves analysis state after save"""
    debug_print("\n" + "="*60)
    debug_print("🔽 SAVE CALLBACK TRIGGERED")
    debug_print("="*60)
    
    conn = None
    try:
        required_keys = [
            'current_analysis_record', 'current_best_result', 'current_best_tier',
            'current_competitor_bids', 'current_risk_tolerance', 'user_id', 'company_id'
        ]
        
        for key in required_keys:
            if key not in st.session_state or st.session_state[key] is None:
                error_msg = f"Missing required session state: {key}"
                debug_print(f"❌ VALIDATION FAILED: {error_msg}")
                st.error(error_msg)
                return
        
        analysis_record = st.session_state.current_analysis_record
        best_result = st.session_state.current_best_result
        best_tier = st.session_state.current_best_tier
        competitor_bids = st.session_state.current_competitor_bids
        risk_tolerance = st.session_state.current_risk_tolerance
        user_id = st.session_state.user_id
        company_id = st.session_state.company_id
        
        official_est = float(analysis_record.get('official_estimate', 0))
        if official_est <= 0:
            st.error("❌ Official estimate must be positive")
            return
            
        optimal_bid = float(best_result['optimal_bid'])
        win_probability = float(best_result['win_probability'])
        confidence_score = float(best_result.get('confidence_score', 0.75))
        risk_level = str(best_result['risk_level'])
        
        estimated_cost = official_est * COST_ESTIMATE_RATIO
        expected_profit = optimal_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        competitor_bids_json = json.dumps(competitor_bids if competitor_bids else [])
        analysis_type_str = f"{best_tier.upper()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        insert_fields = [
            'user_id', 'company_id', 'tender_id', 'tender_title', 'procuring_entity',
            'division', 'official_estimate', 'recommended_bid', 'success_probability',
            'risk_level', 'competitor_count', 'analysis_type', 'analysis_date', 'bid_status'
        ]
        
        insert_values = [
            user_id, company_id,
            str(analysis_record.get('tender_id', '')),
            str(analysis_record.get('tender_title', '')),
            str(analysis_record.get('procuring_entity', '')),
            str(analysis_record.get('division', '')),
            official_est,
            optimal_bid,
            win_probability,
            risk_level,
            int(len(competitor_bids)),
            analysis_type_str,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'draft'
        ]
        
        optional_fields = ['district', 'thana', 'construction_type', 'risk_strategy', 
                          'confidence_score', 'expected_profit', 'expected_value', 'competitor_bids']
        
        for field in optional_fields:
            if field in existing_columns and field in analysis_record:
                insert_fields.append(field)
                if field == 'competitor_bids':
                    insert_values.append(competitor_bids_json)
                elif field == 'confidence_score':
                    insert_values.append(confidence_score)
                elif field == 'expected_profit':
                    insert_values.append(expected_profit)
                elif field == 'expected_value':
                    insert_values.append(expected_value)
                elif field == 'risk_strategy':
                    insert_values.append(str(risk_tolerance))
                else:
                    insert_values.append(str(analysis_record.get(field, '')))
        
        placeholders = ','.join(['?' for _ in range(len(insert_fields))])
        insert_query = f"INSERT INTO tender_analyses ({','.join(insert_fields)}) VALUES ({placeholders})"
        
        cursor.execute(insert_query, insert_values)
        
        analysis_id = cursor.lastrowid
        conn.commit()
        
        st.session_state.last_saved_analysis_id = analysis_id
        st.session_state.last_saved_tender_id = analysis_record.get('tender_id', '')
        
        st.success(f"✅ {best_tier.upper()} analysis saved! (ID: {analysis_id})")
        st.balloons()
        
    except Exception as e:
        debug_print(f"❌ SAVE ERROR: {type(e).__name__}: {str(e)}")
        st.error(f"💥 Error saving analysis: {str(e)}")
    finally:
        if conn:
            conn.close()

def _process_competitor_bids_input(
    bid_source: str, 
    official_estimate: float, 
    tender_id: str,
    competitor_options: Dict[str, int],
    session_key: str = 'analysis_competitor_bids'
) -> List[float]:
    """
    Handle competitor bid input logic (auto-generate or manual entry).
    Returns list of bid amounts (floats, 3 decimal precision).
    """
    competitor_bids = []
    
    if bid_source == "Enter manually":
        # Manual entry mode
        if session_key not in st.session_state:
            st.session_state[session_key] = []
        
        # Render competitor input rows
        num_competitors = st.number_input(
            "Number of competitors", 
            min_value=0, 
            max_value=20, 
            value=max(3, len(st.session_state[session_key])),
            key=f"{session_key}_count"
        )
        
        # Process existing entries
        updated_entries = []
        for idx, entry in enumerate(st.session_state[session_key]):
            updated = render_competitor_bid_row(idx, entry, competitor_options, session_key)
            if not updated['remove'] and updated['name'] and updated['bid'] > 0:
                updated_entries.append({
                    'name': updated['name'],
                    'bid': updated['bid'],
                    'was_winner': updated['was_winner']
                })
        
        st.session_state[session_key] = updated_entries
        
        # Add new competitor section
        with st.expander("➕ Add New Competitor", expanded=False):
            col_a, col_b, col_c, col_d = st.columns([2, 2, 1.5, 0.5])
            with col_a:
                new_name = st.selectbox(
                    "Select from master list", 
                    options=[""] + list(competitor_options.keys()),
                    key=f"{session_key}_new_name"
                )
            with col_b:
                new_bid = st.number_input(
                    "Bid Amount (BDT)",
                    min_value=0.0,
                    value=round(official_estimate * 0.90, 3) if official_estimate > 0 else 0.0,
                    step=100000.0,
                    format="%.3f",
                    key=f"{session_key}_new_bid"
                )
            with col_c:
                new_winner = st.checkbox("Winner?", key=f"{session_key}_new_winner")
            with col_d:
                add_clicked = st.button("Add", key=f"{session_key}_add_btn")
            
            if add_clicked and new_name and new_bid > 0:
                existing_names = [e['name'] for e in st.session_state[session_key]]
                if new_name not in existing_names:
                    st.session_state[session_key].append({
                        'name': new_name,
                        'bid': round(new_bid, 3),
                        'was_winner': new_winner
                    })
                    st.toast(f"✅ Added {new_name}", icon="🎯")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {new_name} already in list")
        
        # Extract bid amounts
        competitor_bids = [round(e['bid'], 3) for e in st.session_state[session_key]]
        
        # Show summary if bids exist
        if competitor_bids:
            with st.expander("📊 Competitor Summary", expanded=True):
                summary_df = pd.DataFrame([
                    {
                        'Competitor': e['name'],
                        'Bid (BDT)': f"{e['bid']:,.3f}",
                        '% of Estimate': f"{e['bid']/official_estimate*100:.2f}%" if official_estimate > 0 else "N/A",
                        'Winner': '🏆' if e.get('was_winner') else ''
                    }
                    for e in st.session_state[session_key]
                ])
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("🗑️ Clear All", key=f"{session_key}_clear", use_container_width=True):
                        st.session_state[session_key] = []
                        st.rerun()
    
    else:
        # Auto-generate mode
        num_competitors = st.slider(
            "Number of competitors to simulate", 
            min_value=3, 
            max_value=15, 
            value=7,
            key=f"{session_key}_auto_count"
        )
        
        # Clear manual entries when switching to auto
        if session_key in st.session_state:
            st.session_state[session_key] = []
        
        # Generate realistic bids with seeded randomness
        seed_val = hash(f"{tender_id}_{official_estimate}_{num_competitors}") % (2**32)
        np.random.seed(seed_val)
        
        base_ratios = np.random.uniform(0.85, 0.98, num_competitors)
        noise = np.random.uniform(-0.03, 0.03, num_competitors)
        final_ratios = np.clip(base_ratios + noise, 0.80, 1.00)
        
        competitor_bids = [round(official_estimate * r, 3) for r in final_ratios]
        
        # Show preview
        with st.expander("🤖 Auto-Generated Bids Preview", expanded=True):
            preview_df = pd.DataFrame({
                'Simulated Bidder': [f"Bidder {i+1}" for i in range(num_competitors)],
                'Bid Amount (BDT)': [f"{b:,.3f}" for b in competitor_bids],
                '% of Estimate': [f"{b/official_estimate*100:.2f}%" for b in competitor_bids]
            })
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            st.caption("💡 Bids are simulated based on historical patterns. Switch to 'Enter manually' for real competitor data.")
    
    return competitor_bids

def calculate_ppr_compliance(official_estimate: float, competitor_bids: List[float], recommended_bid: float) -> Dict:
    """
    Calculate PPR 2025 compliance metrics.
    
    Returns dict with all calculated values for display.
    """
    # PPR 2025 constants
    NPPI_FACTOR = 0.920
    WEIGHTS = {'competitor_avg': 0.5, 'official_est': 0.2, 'nppi': 0.3}
    
    # Calculate NPPI price
    nppi_price = round(official_estimate * NPPI_FACTOR, 3)
    
    # Competitor statistics
    if competitor_bids:
        avg_competitor = float(np.mean(competitor_bids))
        competitor_sample = competitor_bids[:5]  # Use first 5 for std dev
    else:
        # Fallback estimates
        avg_competitor = round(official_estimate * 0.91, 3)
        competitor_sample = [
            round(official_estimate * p, 3) 
            for p in [0.88, 0.90, 0.92, 0.94, 0.95]
        ]
    
    # Weighted average (X̄)
    weighted_avg = round(
        WEIGHTS['competitor_avg'] * avg_competitor +
        WEIGHTS['official_est'] * official_estimate +
        WEIGHTS['nppi'] * nppi_price,
        3
    )
    
    # Weighted standard deviation (Sd)
    if len(competitor_sample) > 0:
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_sample]
        variance = sum(squared_deviations) / len(competitor_sample)
        weighted_std = round(np.sqrt(variance), 3)
    else:
        weighted_std = 0.0
    
    # SLT Threshold
    slt_threshold = round(weighted_avg - weighted_std, 3)
    
    # Evaluation
    is_below_slt = recommended_bid < slt_threshold
    compliance_status = "NON-COMPLIANT ⚠️" if is_below_slt else "COMPLIANT ✅"
    
    return {
        'nppi_factor': NPPI_FACTOR,
        'nppi_price': nppi_price,
        'avg_competitor': avg_competitor,
        'weighted_avg': weighted_avg,
        'weighted_std': weighted_std,
        'slt_threshold': slt_threshold,
        'recommended_bid': recommended_bid,
        'is_below_slt': is_below_slt,
        'compliance_status': compliance_status,
        'competitor_sample': competitor_sample,
        'squared_deviations': squared_deviations if 'squared_deviations' in locals() else []
    }


# =============================================================================
# 🎨 UI HELPER COMPONENTS (Extracted for reusability)
# =============================================================================

def render_tender_info_card(tender_data: Dict) -> None:  # ← Correct: tender_data (parameter name)
    """Render a compact tender information summary card"""
    # Now use tender_data consistently inside:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea;">
        <strong>📋 {tender_data.get('tender_title', 'Untitled')[:60]}{'...' if len(tender_data.get('tender_title',''))>60 else ''}</strong><br>
        <small>
            ID: {tender_data.get('tender_id', 'N/A')} • 
            Entity: {tender_data.get('procuring_entity', 'N/A')[:40]}<br>
            Estimate: BDT {tender_data.get('official_estimate', 0):,.3f} • 
            Deadline: {tender_data.get('submission_deadline', 'N/A')}
        </small>
    </div>
    """, unsafe_allow_html=True)

def safe_title(value, default: str = 'N/A') -> str:
    """
    Safely convert any value to title case.
    Handles None, non-strings, and empty values gracefully.
    
    Args:
        value: Any value (str, None, int, etc.)
        default: Fallback string if value is None/empty
    
    Returns:
        Title-cased string or default
    """
    if value is None:
        return default
    try:
        return str(value).strip().title() if str(value).strip() else default
    except Exception:
        return default


def render_competitor_bid_row(idx: int, competitor_Dict, competitor_options: Dict, key_prefix: str) -> tuple:
    """
    Render a single competitor bid input row.
    Returns updated competitor entry dict.
    """
    col_a, col_b, col_c, col_d = st.columns([2.5, 2, 1.5, 0.5])
    
    with col_a:
        if competitor_options:
            name = st.selectbox(
                "Competitor",
                options=[""] + list(competitor_options.keys()),
                index=list(competitor_options.keys()).index(competitor_entry['name']) if competitor_entry['name'] in competitor_options else 0,
                key=f"{key_prefix}_name_{idx}",
                label_visibility="collapsed"
            )
        else:
            name = st.text_input("Competitor", value=competitor_entry['name'], key=f"{key_prefix}_name_{idx}", label_visibility="collapsed")
    
    with col_b:
        bid = st.number_input(
            "Bid (BDT)",
            min_value=0.0,
            value=float(competitor_entry['bid']),
            step=100000.0,  # 1 lakh steps for easier input
            format="%.3f",  # 3 decimal precision
            key=f"{key_prefix}_bid_{idx}",
            label_visibility="collapsed"
        )
    
    with col_c:
        was_winner = st.checkbox(
            "Winner?",
            value=competitor_entry.get('was_winner', False),
            key=f"{key_prefix}_winner_{idx}"
        )
    
    with col_d:
        remove = st.button("🗑️", key=f"{key_prefix}_remove_{idx}", help="Remove this competitor")
    
    return {
        'name': name,
        'bid': round(bid, 3),  # Ensure 3 decimal precision
        'was_winner': was_winner,
        'remove': remove
    }


def render_comparison(
    basic_result: Dict, 
    advanced_result: Dict, 
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """
    Render side-by-side comparison between basic and advanced analysis.
    
    Note: This is the 2-tier version. For 3-tier, use display_analysis_results_with_report()
    """
    debug_print("🆚 Rendering comparison: Basic vs Advanced")
    
    st.markdown("### 🆚 Analysis Comparison: Basic vs Advanced")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Basic Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {basic_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {basic_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {basic_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {basic_result['risk_color']} {basic_result['risk_level']}")
        st.caption(f"Method: {basic_result.get('method', 'Statistical')}")
    
    with col2:
        st.markdown("#### 🧠 Advanced ML Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {advanced_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {advanced_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {advanced_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {advanced_result['risk_color']} {advanced_result['risk_level']}")
        st.caption(f"Method: {advanced_result.get('method', 'ML Ensemble')}")
    
    # Difference analysis
    diff = advanced_result['optimal_bid'] - basic_result['optimal_bid']
    diff_percent = (diff / official_estimate) * 100 if official_estimate else 0
    
    st.markdown("---")
    st.markdown("#### 💡 Analysis Insight")
    
    if abs(diff) < official_estimate * 0.005:  # 0.5% threshold
        st.info("📊 Both analyses suggest very similar bid amounts (within 0.5%). The market appears stable and predictable.")
    elif diff > 0:
        st.warning(f"""
        📈 Advanced analysis suggests **increasing bid by BDT {diff:,.3f}** ({diff_percent:+.2f}% of estimate) 
        for optimal outcome. This accounts for:
        - Historical competitor patterns
        - Market condition adjustments
        - Risk-optimized positioning
        """)
    else:
        st.success(f"""
        📉 Advanced analysis suggests **decreasing bid by BDT {abs(diff):,.3f}** ({diff_percent:+.2f}% of estimate) 
        to improve win probability while maintaining profitability. This leverages:
        - Identified competitor weaknesses
        - Optimal risk-reward positioning
        - ML-predicted market response
        """)
    
    # Win probability comparison
    win_diff = advanced_result['win_probability'] - basic_result['win_probability']
    if win_diff > 0.10:
        st.success(f"🎯 Advanced ML analysis shows **+{win_diff*100:.0f}% higher win probability** due to identified competitor patterns and market dynamics.")
    elif win_diff < -0.10:
        st.warning(f"⚠️ Advanced analysis shows **-{abs(win_diff)*100:.0f}% win probability** – this may indicate aggressive competitor clustering or market saturation. Review carefully.")
    
    st.markdown("---")
    st.markdown("#### ✅ Recommendation")
    
    # For admin, default to advanced; for others, respect subscription
    if st.session_state.user_role == 'admin' or st.session_state.subscription_plan in ['professional', 'enterprise']:
        recommended = advanced_result
        rec_label = "Advanced ML Analysis"
        rec_icon = "🧠"
    else:
        recommended = basic_result
        rec_label = "Basic Analysis"
        rec_icon = "📊"
    
    st.info(f"""
    {rec_icon} **Recommended Bid:** BDT {recommended['optimal_bid']:,.3f}  
    Based on {rec_label} • Win probability: {recommended['win_probability']*100:.0f}% • Risk: {recommended['risk_color']} {recommended['risk_level']}
    """)
    
    # Save button hint
    if st.session_state.get('current_analysis_record'):
        st.caption("💡 Click '💾 Save Analysis' below to store this recommendation in your history.")
    
    debug_print("✅ Comparison render complete")



# =============================================================================
# 📊 DISPLAY FUNCTION (Fixed syntax errors)
# =============================================================================
def display_analysis_results_with_report(
    comparison: Dict[str, Dict], 
    analysis_record: Dict, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """Display analysis results in tabbed format with save functionality"""
    
    debug_print(f"\n📊 Rendering analysis display | Tiers: {list(comparison.keys()) if comparison else 'None'}")
    
    # =============================================================================
    # 🛡️ SESSION STATE PROTECTION
    # =============================================================================
    if analysis_record and comparison:
        debug_print("💾 Updating session state with fresh analysis data")
        
        # Find best result (single calculation)
        best_result = None
        best_tier = None
        for tier, result in comparison.items():
            score = result.get('confidence_score', 0) * result.get('win_probability', 0)
            current_best_score = (
                best_result.get('confidence_score', 0) * best_result.get('win_probability', 0) 
                if best_result else -1
            )
            if score > current_best_score:
                best_result = result
                best_tier = tier
        
        # Store in session state
        st.session_state.current_analysis_record = analysis_record
        st.session_state.current_best_result = best_result
        st.session_state.current_best_tier = best_tier
        st.session_state.current_competitor_bids = competitor_bids
        st.session_state.current_risk_tolerance = risk_tolerance
        st.session_state.current_comparison = comparison
        
        debug_print(f"✓ Session state updated | Best tier: {best_tier}")
    
    # =============================================================================
    # 📋 BUILD COMPARISON TABLE (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    st.markdown("## 🆚 Three-Tier Analysis Comparison")
    
    comparison_data = []
    active_comparison = comparison if comparison else st.session_state.get('current_comparison', {})
    
    for tier, result in active_comparison.items():
        comparison_data.append({
            'Analysis Type': tier.upper(),
            'Method': result.get('method', 'N/A'),
            'Optimal Bid': f"BDT {result.get('optimal_bid', 0):,.3f}",  # ✅ Changed to 3 decimals
            '% of Estimate': f"{result.get('bid_ratio', 0)*100:.1f}%",
            'Win Probability': f"{result.get('win_probability', 0)*100:.0f}%",
            'Confidence': f"{result.get('confidence_score', 0.70)*100:.0f}%",
            'Risk': f"{result.get('risk_color', '⚪')} {result.get('risk_level', 'Unknown')}"
        })

    
    # ✅ Fixed: Complete condition with colon
    if comparison_data:  # ✅ Was: if comparison_
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        debug_print(f"✓ Displayed comparison table with {len(comparison_df)} rows")
    else:
        st.warning("⚠️ No comparison data available")
        debug_print("⚠️ No data to display in comparison table")
    
    # =============================================================================
    # 💡 AI RECOMMENDATION SECTION
    # =============================================================================
    st.markdown("---")
    st.markdown("### 💡 AI Recommendation")
    
    best_result = st.session_state.get('current_best_result')
    best_tier = st.session_state.get('current_best_tier')
    
    if best_result and best_tier:
        if best_tier == 'enhanced':
            st.success(f"🎯 **Recommended: Enhanced (ML) Analysis** - Highest confidence ({best_result.get('confidence_score', 0.80)*100:.0f}%)")
        elif best_tier == 'advanced':
            st.info(f"📊 **Recommended: Advanced (PPR 2025) Analysis** - Compliant with government procurement rules")
        else:
            st.warning(f"🔬 **Recommended: Basic Analysis** - Use for quick estimates")
        
        optimal_bid = best_result.get('optimal_bid', 0)
        bid_ratio = best_result.get('bid_ratio', 0)
        st.info(f"**Suggested Bid:** BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f} ({bid_ratio*100:.1f}% of estimate)")
        debug_print(f"✓ Displayed recommendation: {best_tier} @ BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f}")
    else:
        st.warning("⚠️ Run analysis first to see recommendations")
    
    # =============================================================================
    # 💾 SAVE BUTTON SECTION (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        has_valid_data = (
            st.session_state.get('current_analysis_record') is not None and
            st.session_state.get('current_best_result') is not None
        )
        
        st.button(
            "💾 Save Analysis to History", 
            key="save_analysis_btn", 
            use_container_width=True, 
            type="primary",
            disabled=not has_valid_data,
            on_click=_save_analysis_callback
        )
        debug_print(f"✓ Save button rendered | Enabled: {has_valid_data}")
        # ✅ Fixed: Complete condition with colon
        if not has_valid_data:  # ✅ Was: if not has_valid_
            st.caption("🔒 Run analysis first to enable saving")
        elif DEBUG_MODE:
            st.caption("🐛 Debug mode active")
    
    # =============================================================================
    # 🔄 Show recently saved status
    # =============================================================================
    if st.session_state.get('last_saved_analysis_id'):
        saved_id = st.session_state.last_saved_analysis_id
        saved_tender = st.session_state.get('last_saved_tender_id', 'Unknown')
        st.success(f"✨ Last saved: Analysis #{saved_id} for Tender {saved_tender}")
    
    debug_print("✅ Display function completed\n")
    
    # Download CSV
    if analysis_record and analysis_record.get('tender_id'):
        export_df = pd.DataFrame(comparison_data)
        csv = export_df.to_csv(index=False)
        st.download_button(
            "📥 Download Comparison Results (CSV)", 
            csv, 
            f"tender_analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "text/csv"
        )


def _export_analysis_csv(analysis: Dict) -> None:
    """Export single analysis to CSV (helper for history page)"""
    try:
        import csv
        import io
        
        # Define fields to export
        fields = [
            'tender_id', 'tender_title', 'procuring_entity', 'official_estimate',
            'recommended_bid', 'success_probability', 'risk_level', 'analysis_type',
            'analysis_date', 'bid_status'
        ]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerow({k: analysis.get(k, '') for k in fields})
        
        # Trigger download
        csv_data = output.getvalue()
        output.close()
        
        tender_id = str(analysis.get('tender_id', 'export')).replace('/', '_')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"analysis_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")
        if DEBUG_MODE:
            st.code(traceback.format_exc(), language="python")