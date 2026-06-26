import streamlit as st
import pandas as pd
import random
from datetime import datetime
from modules.advanced_bid_optimizer import get_three_tier_comparison
from modules.report_generator import generate_unified_report, generate_html_content_only
from utils.analysis_helpers import (
    load_tender_into_form, sync_form_to_model, model_to_form, 
    ensure_admin_premium, _save_analysis_callback
)
from utils.bid_generators import _generate_competitor_bids
from utils.helpers import render_page_header
from config import DEBUG_MODE, debug_print
from database.unified_db_manager import UnifiedDatabaseManager
from modules.rbac import (
    rbac, can_run_analysis, can_export_data, can_view_tenders,
    render_role_badge, require_permission, is_analyst
)

from utils.db_helpers import get_company_tenders_cached

db = UnifiedDatabaseManager()
@require_permission('can_run_analysis')
def render_tender_analysis() -> None:
    """Three-Tier Tender Analysis Page with RBAC"""
    debug_print("🎯 Rendering tender analysis page")
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Get user permissions
    permissions = rbac.get_current_user_permissions()
    user_role = st.session_state.get('user_role', 'viewer')
    can_export = permissions.get('can_export_data', False)
    can_view_tenders_permission = permissions.get('can_view_tenders', False)
    
    # Check subscription limit
    sub = db.get_effective_subscription(
        st.session_state.user_id, 
        st.session_state.company_id if st.session_state.get('account_type') == 'company' else None
    )
    st.session_state.subscription_plan = sub.get('plan', 'free')
    st.session_state.analyses_used = sub.get('analyses_used', 0)
    st.session_state.analyses_limit = sub.get('analyses_limit', 5)
    st.session_state.sub_owner_type = sub.get('owner_type', 'free')
    
    # Show role-based info
    if user_role == 'viewer':
        st.info("👁️ **Viewer Mode:** You can view analysis results but cannot run new analyses.")
    elif user_role == 'analyst':
        st.info("📈 **Analyst Mode:** You can run analyses and save results.")
    elif user_role in ['manager', 'company_admin']:
        st.info("📊 **Manager Mode:** Full access to analysis features.")
    
    if st.session_state.analyses_limit > 0 and st.session_state.analyses_used >= st.session_state.analyses_limit:
        st.warning(f"🔒 {st.session_state.sub_owner_type.title()} analysis limit reached.")
        if st.button("💳 Upgrade Plan", type="primary"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    is_premium = st.session_state.subscription_plan in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    # Check if user can run analysis (Analyst and above)
    can_run = is_analyst() or user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    # Initialize session state (same as before)
    if 'tender_form_data' not in st.session_state:
        st.session_state.tender_form_data = {
            'tender_id': '',
            'tender_title': '',
            'procuring_entity': '',
            'division': 'Dhaka',
            'district': '',
            'thana': '',
            'official_estimate': 0.0,
            'tender_security': 0.0,
            'document_fee': 0.0,
            'procurement_type': 'works',
            'risk_tolerance': 'moderate'
        }
    
    # Initialize competitor data model
    if 'competitor_data' not in st.session_state:
        st.session_state.competitor_data = {
            'rows': [],
            'selected_list': [],
            'generated_bids': {},
            'analysis_bids': []
        }
    
    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {
            'current_record': None,
            'current_comparison': None,
            'current_best_result': None,
            'current_best_tier': None,
            'current_competitor_bids': [],
            'current_risk_tolerance': 'moderate',
            'analysis_ready_to_save': False,
            'last_saved_analysis_id': None,
            'last_saved_tender_id': None,
            '_pdf_buffer': None,
            '_pdf_filename': None,
            '_html_buffer': None,  # Add this
            '_html_filename': None  # Add this
        }
    if 'selected_tender_for_analysis' not in st.session_state:
        st.session_state.selected_tender_for_analysis = None
    if 'tender_lock_status' not in st.session_state:
        st.session_state.tender_lock_status = 'unlocked'
    if 'tender_loaded' not in st.session_state:
        st.session_state.tender_loaded = False
    if 'auto_competitor_count' not in st.session_state:
        st.session_state.auto_competitor_count = 3
    if 'auto_risk_pref' not in st.session_state:
        st.session_state.auto_risk_pref = 'moderate'
    if 'analysis_bid_source' not in st.session_state:
        st.session_state.analysis_bid_source = "🤖 Auto-generate realistic bids"
    if '_html_buffer' not in st.session_state.analysis_state:
        st.session_state.analysis_state['_html_buffer'] = None
    if '_html_filename' not in st.session_state.analysis_state:
        st.session_state.analysis_state['_html_filename'] = None

    # Clear stale flags
    if 'tender_form_submitted' in st.session_state:
        del st.session_state.tender_form_submitted

    # Header
    #render_page_header(
    #    f"🎯 Three-Tier Bid Optimization", 
    #    "Compare Basic, Advanced (PPR 2025), and Enhanced (ML) analysis"
    #)

    
    # Ensure admin has premium access
    ensure_admin_premium()
    
    # Subscription check
    sub = db.get_effective_subscription(
        st.session_state.user_id, 
        st.session_state.company_id if st.session_state.get('account_type') == 'company' else None
    )
    st.session_state.subscription_plan = sub.get('plan', 'free')
    st.session_state.analyses_used = sub.get('analyses_used', 0)
    st.session_state.analyses_limit = sub.get('analyses_limit', 5)
    st.session_state.sub_owner_type = sub.get('owner_type', 'free')
    
    if st.session_state.analyses_limit > 0 and st.session_state.analyses_used >= st.session_state.analyses_limit:
        st.warning(f"🔒 {st.session_state.sub_owner_type.title()} analysis limit reached.")
        if st.button("💳 Upgrade Plan", type="primary"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    is_premium = st.session_state.subscription_plan in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    # =============================================================================
    # 🔹 TENDER SELECTOR SECTION
    # =============================================================================
    if can_view_tenders_permission:
        st.markdown("### 🔍 Select Tender for Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_id = st.text_input("Tender ID", key="analysis_search_id", placeholder="e.g., 1265809")
        with col2:
            search_title = st.text_input("Title/Entity", key="analysis_search_title", placeholder="Search...")
        with col3:
            filter_type = st.selectbox("Type", ["All", "works", "goods", "services"], key="analysis_filter_type")
        
        all_tenders = get_company_tenders_cached(st.session_state.company_id)
        filtered = all_tenders.copy()
        
        if search_id:
            filtered = filtered[filtered['tender_id'].str.contains(search_id, case=False, na=False)]
        if search_title:
            filtered = filtered[
                filtered['tender_title'].str.contains(search_title, case=False, na=False) | 
                filtered['procuring_entity'].str.contains(search_title, case=False, na=False)
            ]
        if filter_type != "All":
            filtered = filtered[filtered['procurement_type'] == filter_type]
        
        if not filtered.empty:
            display_df = filtered[['id', 'tender_id', 'tender_title', 'procuring_entity', 
                                  'procurement_type', 'official_estimate', 'submission_deadline', 
                                  'is_locked', 'is_copy']].copy()
            
            display_df['estimate_fmt'] = display_df['official_estimate'].apply(lambda x: f"BDT {x:,.0f}" if pd.notna(x) else "N/A")
            display_df['deadline_fmt'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce').dt.strftime('%d %b %Y')
            display_df['status'] = display_df.apply(lambda r: "🔒 LOCKED" if r['is_locked'] else ("📋 COPY" if r['is_copy'] else "🔓 Open"), axis=1)
            
            st.dataframe(
                display_df[['tender_id', 'tender_title', 'procuring_entity', 'procurement_type', 'estimate_fmt', 'deadline_fmt', 'status']],
                use_container_width=True,
                height=250
            )
            
            tender_options = {f"{row['tender_id']} • {str(row['tender_title'])[:50]}...": row.to_dict() for _, row in filtered.iterrows()}
            selected_label = st.selectbox("Select tender to analyze:", options=["-- Create New Analysis --"] + list(tender_options.keys()), key="analysis_selector")
            
            if selected_label != "-- Create New Analysis --" and selected_label in tender_options:
                selected_data = tender_options[selected_label]
                
                if st.button("📥 Load Tender for Analysis", type="primary", key="load_analysis_tender"):
                    load_tender_into_form(selected_data)
                    model_to_form()
                    st.session_state.selected_tender_for_analysis = selected_data
                    is_locked = bool(selected_data.get('is_locked', False))
                    st.session_state.tender_lock_status = 'locked' if is_locked else 'unlocked'
                    st.toast(f"✅ Loaded: {selected_data['tender_title'][:40]}", icon="📋")
                    st.rerun()
        else:
            st.info("📭 No tenders found. Create a tender first or adjust your search.")
    
    # Show loaded tender summary
    if st.session_state.get('selected_tender_for_analysis'):
        t = st.session_state.selected_tender_for_analysis
        status_badge = "🔒" if t.get('is_locked') else ("📋" if t.get('is_copy') else "🔓")
        st.markdown(f"""
        <div style="background:#f8fafc;padding:0.75rem 1rem;border-radius:8px;border-left:4px solid #3b82f6;margin:0.5rem 0">
            <strong>{status_badge} {str(t.get('tender_title',''))[:70]}{'...' if len(str(t.get('tender_title',''))) > 70 else ''}</strong><br>
            <small>ID: {t.get('tender_id')} • Est: BDT {t.get('official_estimate',0):,.0f} • Deadline: {str(t.get('submission_deadline',''))[:10]}</small>
        </div>
        """, unsafe_allow_html=True)
    # =============================================================================
    # 🔹 NPPI FACTOR CONFIGURATION - MOVED OUTSIDE FORM FOR DYNAMIC UPDATES
    # =============================================================================
    st.markdown("---")
    st.markdown("### 📊 NPPI Factor Configuration")
    st.markdown("""
    <div style="background: #f0f9ff; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;">
        <small>💡 <strong>NPPI (Non-performing Price Index)</strong> is a key factor in PPR 2025 calculations.
        It represents the 28-day market average and affects SLT threshold calculations.</small>
    </div>
    """, unsafe_allow_html=True)
    
    # This is OUTSIDE the form, so it updates immediately when changed
    nppi_mode = st.radio(
        "Select NPPI Factor Method:",
        options=["Default (0.92)", "Manual Entry", "Dynamic (Calculate from historical data)"],
        index=0,
        key="nppi_mode_radio_outside",
        help="Choose how the NPPI factor should be calculated for this analysis",
        horizontal=True
    )
    
    nppi_factor_value = 0.920  # Default
    nppi_warning = None
    
    # Conditional display based on selection (updates immediately because it's outside form)
    if nppi_mode == "Default (0.92)":
        st.info("📌 Using default NPPI factor: **0.920** (28-day market average)")
        nppi_factor_value = 0.920
        
    elif nppi_mode == "Manual Entry":
        st.success("✏️ **Manual Entry Mode Active** - Enter custom NPPI factor below")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            nppi_factor_value = st.number_input(
                "Enter Custom NPPI Factor",
                min_value=0.70,
                max_value=1.15,
                value=st.session_state.get('manual_nppi_value_outside', 0.920),
                step=0.005,
                format="%.3f",
                key="manual_nppi_value_outside",
                help="Enter a custom NPPI factor between 0.70 and 1.15"
            )
        
        with col2:
            official_estimate = st.session_state.get('input_official_estimate', 0)
            nppi_price = official_estimate * nppi_factor_value
            st.metric(
                "NPPI Price", 
                f"BDT {nppi_price:,.0f}",
                delta=f"{(nppi_factor_value - 0.92) * 100:+.1f}% vs default"
            )
        
        # Warning for extreme values
        if nppi_factor_value < 0.85:
            st.warning("⚠️ NPPI factor is significantly below market average (0.92)")
        elif nppi_factor_value > 0.99:
            st.warning("⚠️ NPPI factor is significantly above market average (0.92)")
        else:
            st.success(f"✅ NPPI factor {nppi_factor_value:.3f} is within normal range")
    
    elif nppi_mode == "Dynamic (Calculate from historical data)":
        st.info("📊 **Dynamic Mode Active** - Calculating from historical data")
        
        try:
            from modules.advanced_bid_optimizer import AdvancedBidOptimizer
            optimizer = AdvancedBidOptimizer()
            
            historical_df = db.get_historical_tenders(st.session_state.company_id, limit=50)
            
            if historical_df is not None and not historical_df.empty:
                with st.spinner("Calculating dynamic NPPI..."):
                    historical_data = historical_df.to_dict('records')
                    dynamic_nppi = optimizer.calculate_nppi(
                        st.session_state.get('input_procurement_type', 'goods'),
                        historical_data=historical_data
                    )
                    nppi_factor_value = dynamic_nppi
                
                st.success(f"✅ Dynamic NPPI: **{dynamic_nppi:.4f}** from {len(historical_df)} tenders")
            else:
                nppi_warning = "⚠️ No historical data. Using default 0.92"
                nppi_factor_value = 0.920
                st.warning(nppi_warning)
                
        except Exception as e:
            nppi_warning = f"⚠️ Error: {str(e)}. Using default 0.92"
            nppi_factor_value = 0.920
            st.warning(nppi_warning)
    
    # Store NPPI values in session state for use in form
    st.session_state.nppi_factor_value = nppi_factor_value
    st.session_state.nppi_mode_selected = nppi_mode
    
    # Show current NPPI factor
    official_estimate = st.session_state.get('input_official_estimate', 0)
    nppi_price = official_estimate * nppi_factor_value
    
    st.markdown(f"""
    <div style="background: #e8f5e9; padding: 0.75rem; border-radius: 8px; text-align: center;">
        <strong>Current NPPI Factor:</strong> {nppi_factor_value:.4f}<br>
        <small>NPPI Price: BDT {nppi_price:,.0f}</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # =============================================================================
    # 🔹 BID SOURCE SELECTION
    # =============================================================================
    st.markdown("### 📝 Analysis Inputs")
    
    is_new = st.session_state.selected_tender_for_analysis is None
    is_locked = st.session_state.get('tender_lock_status') == 'locked' and not is_new
    form_disabled = is_locked and st.session_state.user_role != 'admin'
    
    if form_disabled:
        st.warning("🔒 Tender is locked. Only admin can edit.")
    
    # Disable analysis if user doesn't have permission
    if not can_run:
        st.error("🔒 You don't have permission to run analysis. Contact your administrator.")
        st.info("Upgrade to Analyst role or higher to run bid optimization.")
        return
    
    bid_source = st.radio(
        "Provide competitor bids:",
        ["🤖 Auto-generate realistic bids", "✍️ Enter manually from known competitors"],
        horizontal=True,
        key="analysis_bid_source",
        disabled=form_disabled
    )
    
    is_manual_mode = "manually" in bid_source.lower() or "manual" in bid_source.lower()

    
    # =============================================================================
    # 🔹 COMPETITOR SELECTION UI (Manual Mode Only)
    # =============================================================================
    if is_manual_mode:
        st.markdown("---")
        st.markdown("#### 👥 Select Competitors for Analysis")
        
        competitors = db.get_competitor_master_list(st.session_state.company_id)
        competitor_options = {c[1]: c[0] for c in competitors} if competitors else {}
        
        if competitor_options:
            selected_competitors = st.multiselect(
                "Choose competitors from master list",
                options=list(competitor_options.keys()),
                default=st.session_state.competitor_data.get('selected_list', []),
                key="selected_competitors_multiselect"
            )
            
            st.session_state.competitor_data['selected_list'] = selected_competitors
            
            if selected_competitors:
                col_gen1, col_gen2, col_gen3 = st.columns([2, 1, 1])
                
                with col_gen1:
                    bid_strategy = st.selectbox(
                        "Bid generation strategy",
                        options=["Realistic (based on history)", "Aggressive (lower bids)", "Conservative (higher bids)", "Random (wide range)"],
                        key="bid_gen_strategy"
                    )
                
                with col_gen2:
                    if st.button("🎲 Generate Random Bids", key="generate_random_bids_btn", use_container_width=True, type="primary"):
                        sync_form_to_model()
                        estimate_val = st.session_state.tender_form_data['official_estimate']
                        
                        if estimate_val > 0:
                            random_bids = {}
                            for comp_name in selected_competitors:
                                comp_id = competitor_options[comp_name]
                                comp_data = db.get_competitor_by_id(comp_id)
                                
                                if bid_strategy == "Realistic (based on history)":
                                    if comp_data and comp_data['avg_bid_ratio']:
                                        base_ratio = comp_data['avg_bid_ratio']
                                        bid_ratio = base_ratio * random.uniform(0.95, 1.05)
                                    else:
                                        bid_ratio = random.uniform(0.88, 0.96)
                                elif bid_strategy == "Aggressive (lower bids)":
                                    bid_ratio = random.uniform(0.82, 0.89)
                                elif bid_strategy == "Conservative (higher bids)":
                                    bid_ratio = random.uniform(0.94, 1.02)
                                else:
                                    bid_ratio = random.uniform(0.80, 1.10)
                                
                                bid_ratio = max(0.75, min(1.15, bid_ratio))
                                bid_amount = estimate_val * bid_ratio
                                random_bids[comp_name] = round(bid_amount, 2)
                            
                            st.session_state.competitor_data['generated_bids'] = random_bids
                            st.session_state.competitor_data['rows'] = []
                            for comp_name, bid_amount in random_bids.items():
                                st.session_state.competitor_data['rows'].append({
                                    'id': len(st.session_state.competitor_data['rows']),
                                    'name': comp_name,
                                    'bid': float(bid_amount)
                                })
                            st.session_state.competitor_data['analysis_bids'] = [
                                {'name': row['name'], 'bid': row['bid']}
                                for row in st.session_state.competitor_data['rows']
                            ]
                            st.success(f"✅ Generated bids for {len(random_bids)} competitors!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Please enter Official Estimate first")
                
                with col_gen3:
                    if st.button("🗑️ Clear All", key="clear_all_generated", use_container_width=True):
                        sync_form_to_model()
                        st.session_state.competitor_data = {
                            'rows': [],
                            'selected_list': [],
                            'generated_bids': {},
                            'analysis_bids': []
                        }
                        st.rerun()
                
                # Display generated bids
                if st.session_state.competitor_data.get('rows'):
                    st.markdown("---")
                    st.markdown("##### Review & Edit Bids")
                    
                    rows_to_remove = []
                    for idx, row in enumerate(st.session_state.competitor_data['rows']):
                        col_a, col_b, col_c, col_d = st.columns([2.5, 2.5, 1.5, 0.5])
                        
                        with col_a:
                            st.text_input("Competitor", value=row['name'], key=f"comp_name_{idx}", disabled=True)
                        
                        with col_b:
                            updated_bid = st.number_input(
                                "Bid (BDT)",
                                value=float(row['bid']),
                                step=100000.0,
                                format="%.3f",
                                key=f"comp_bid_edit_{idx}"
                            )
                            st.session_state.competitor_data['rows'][idx]['bid'] = float(updated_bid)
                        
                        with col_c:
                            estimate = st.session_state.tender_form_data['official_estimate']
                            if estimate > 0:
                                pct = (updated_bid / estimate) * 100
                                st.caption(f"{pct:.1f}% of estimate")
                        
                        with col_d:
                            if st.button("🗑️", key=f"remove_gen_comp_{idx}"):
                                rows_to_remove.append(idx)
                                st.rerun()
                    
                    for idx in reversed(rows_to_remove):
                        st.session_state.competitor_data['rows'].pop(idx)
                    
                    # Update analysis bids
                    st.session_state.competitor_data['analysis_bids'] = [
                        {'name': row['name'], 'bid': float(row['bid'])}
                        for row in st.session_state.competitor_data['rows']
                        if row['name'] and row['bid'] > 0
                    ]
                    
                    # Show recommendation
                    if st.session_state.competitor_data['analysis_bids'] and st.session_state.tender_form_data['official_estimate'] > 0:
                        st.markdown("---")
                        st.markdown("### 🎯 Bid Recommendation")
                        
                        estimate = st.session_state.tender_form_data['official_estimate']
                        bid_values = [b['bid'] for b in st.session_state.competitor_data['analysis_bids']]
                        min_bid = min(bid_values)
                        avg_bid = sum(bid_values) / len(bid_values)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📊 Avg Competitor", f"BDT {avg_bid:,.0f}")
                        with col2:
                            st.metric("📈 Min Competitor", f"BDT {min_bid:,.0f}")
                        with col3:
                            st.metric("🎯 Competitors", len(bid_values))
                        
                        risk_tolerance = st.session_state.tender_form_data['risk_tolerance']
                        if risk_tolerance == 'aggressive':
                            recommended = min_bid * 0.98
                        elif risk_tolerance == 'conservative':
                            recommended = avg_bid * 0.98
                        else:
                            recommended = (min_bid + avg_bid) / 2
                        
                        recommended = max(recommended, estimate * 0.85)
                        recommended = min(recommended, estimate * 1.05)
                        
                        st.info(f"**💰 Recommended Bid:** BDT {recommended:,.2f} ({recommended/estimate*100:.1f}% of estimate)")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ Use This Bid", key="use_recommended_bid_final", use_container_width=True):
                                sync_form_to_model()
                                st.session_state.tender_form_data['official_estimate'] = recommended
                                model_to_form()
                                st.success(f"✅ Recommended bid set to BDT {recommended:,.2f}")
                                st.rerun()
                        
                        with col_btn2:
                            if st.button("🔄 Regenerate Bids", key="regenerate_bids_final", use_container_width=True):
                                sync_form_to_model()
                                st.session_state.competitor_data['rows'] = []
                                st.session_state.competitor_data['generated_bids'] = {}
                                st.session_state.competitor_data['analysis_bids'] = []
                                st.rerun()
                    
                    if st.session_state.competitor_data['analysis_bids']:
                        st.success(f"✅ **{len(st.session_state.competitor_data['analysis_bids'])} competitor(s) ready for analysis**")
                
                elif selected_competitors:
                    st.info("🎲 Click 'Generate Random Bids' to create bid amounts for selected competitors")
            else:
                st.info("📭 Select competitors from the list above to begin")
            
            st.caption("💡 **Tip:** Need to add new competitors? Go to **Competitor Master Database** page.")
        else:
            st.warning("📭 No competitors found in master list.")
            if st.button("📋 Go to Competitor Master Database", key="goto_competitor_master", use_container_width=True):
                st.session_state.page = "competitor_master"
                st.rerun()
    
    # =============================================================================
    # 🔹 MAIN ANALYSIS FORM
    # =============================================================================
    with st.form("analysis_form", clear_on_submit=False):
        with st.expander("📋 Basic Tender Details", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Tender ID *", key="input_tender_id", disabled=form_disabled)
                st.text_area("Tender Title *", height=40, key="input_tender_title", disabled=form_disabled)
                st.text_input("Procuring Entity *", key="input_procuring_entity", disabled=form_disabled)
            with c2:
                from modules.bangladesh_locations import DIVISIONS, get_districts, get_upazilas
                div = st.selectbox("Division", DIVISIONS, key="input_division", disabled=form_disabled)
                dists = get_districts(div)
                dist = st.selectbox("District", dists, key="input_district", disabled=form_disabled)
                upzs = get_upazilas(dist)
                if upzs:
                    st.selectbox("Thana/Upazila", upzs, key="input_thana", disabled=form_disabled)
                else:
                    st.text_input("Thana/Upazila", key="input_thana_text", disabled=form_disabled)
        
        with st.expander("💰 Financial Details", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Official Estimate (BDT) *", min_value=0.0, step=100000.0, format="%.3f", key="input_official_estimate", disabled=form_disabled)
                st.number_input("Tender Security (BDT)", min_value=0.0, step=10000.0, format="%.3f", key="input_tender_security", disabled=form_disabled)
            with c2:
                st.selectbox("Procurement Type", ["works", "goods", "services"], key="input_procurement_type", disabled=form_disabled)
                st.number_input("Document Fee (BDT)", min_value=0.0, step=500.0, format="%.3f", key="input_document_fee", disabled=form_disabled)
        
        with st.expander("🎯 Risk Strategy", expanded=True):
            risk_tolerance = st.select_slider(
                "Risk tolerance",
                options=['aggressive', 'moderate', 'conservative'],
                value='moderate',
                key="analysis_risk_tolerance",
                disabled=form_disabled
            )
            st.session_state.tender_form_data['risk_tolerance'] = risk_tolerance
       
        with st.expander("⚙️ Auto-Bid Calculation Settings", expanded=True):
            auto_disabled = is_manual_mode or form_disabled
            if is_manual_mode:
                st.info("🔒 Auto-bid settings are disabled in Manual mode.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.auto_competitor_count = st.slider(
                    "Number of Competitors", min_value=2, max_value=50, 
                    value=st.session_state.get('auto_competitor_count', 3),
                    disabled=auto_disabled
                )
            with col2:
                st.session_state.auto_risk_pref = st.selectbox(
                    "Risk Preference", options=['aggressive', 'moderate', 'conservative'],
                    index=['aggressive', 'moderate', 'conservative'].index(st.session_state.get('auto_risk_pref', 'moderate')),
                    disabled=auto_disabled
                )
        
        form_complete = all([
            st.session_state.get('input_tender_id', ''),
            st.session_state.get('input_tender_title', ''),
            st.session_state.get('input_procuring_entity', ''),
            (st.session_state.get('input_official_estimate', 0) or 0) > 0
        ])
        
        has_competitor_bids = False
        if is_manual_mode:
            has_competitor_bids = len(st.session_state.competitor_data.get('analysis_bids', [])) > 0
        else:
            has_competitor_bids = (st.session_state.get('input_official_estimate', 0) or 0) > 0
        
        
        submit_disabled = not form_complete or not has_competitor_bids or form_disabled or not can_run
        form_submitted = st.form_submit_button("🚀 Run Three-Tier Analysis", type="primary", use_container_width=True, disabled=submit_disabled)
        
        if not form_complete and not form_disabled:
            st.caption("⚠️ Fill required fields: Tender ID, Title, Entity, Estimate")
        elif not has_competitor_bids and not form_disabled:
            if is_manual_mode:
                st.caption("⚠️ Add at least one competitor using the selection above")
            else:
                st.caption("⚠️ Enter Official Estimate first")
        elif not can_run:
            st.caption("🔒 You need higher permissions to run analysis")
    
    # =============================================================================
    # 🔹 RUN ANALYSIS
    # =============================================================================
    if form_submitted and not form_disabled and can_run:
        try:
            sync_form_to_model()
            
            # ✅ Get competitor bids based on mode
            if is_manual_mode:
                competitor_bids = st.session_state.competitor_data.get('analysis_bids', [])
            else:
                estimate_val = st.session_state.tender_form_data['official_estimate']
                competitor_count = st.session_state.get('auto_competitor_count', 3)
                risk_pref = st.session_state.get('auto_risk_pref', 'moderate')
                competitor_bids = _generate_competitor_bids(estimate_val, num_competitors=competitor_count, risk_preference=risk_pref)
            
            # ✅ Get NPPI configuration from session state (moved outside auto/manual block)
            nppi_factor = st.session_state.get('nppi_factor_value', 0.920)
            nppi_mode = st.session_state.get('nppi_mode_selected', 'Default')
            nppi_warning = st.session_state.get('nppi_warning', None)

            
            debug_print(f"📊 Using NPPI factor: {nppi_factor} (Mode: {nppi_mode})")
            
            inputs = {
                'tender_id': st.session_state.tender_form_data['tender_id'],
                'tender_title': st.session_state.tender_form_data['tender_title'],
                'procuring_entity': st.session_state.tender_form_data['procuring_entity'],
                'official_estimate': st.session_state.tender_form_data['official_estimate'],
                'procurement_type': st.session_state.tender_form_data['procurement_type'],
                'division': st.session_state.tender_form_data['division'],
                'district': st.session_state.tender_form_data['district'],
                'thana': st.session_state.tender_form_data['thana'],
                'risk_tolerance': st.session_state.tender_form_data['risk_tolerance'],
                'competitor_bids': competitor_bids,
                'nppi_factor': nppi_factor,  # ✅ Add NPPI factor to inputs
                'nppi_mode': nppi_mode,      # ✅ Add NPPI mode to inputs
                'nppi_warning': nppi_warning  # ✅ Add NPPI warning to inputs
            }
            
            if inputs['official_estimate'] <= 0 or not inputs['competitor_bids']:
                st.error("❌ Please provide valid estimate and competitor bids")
            else:
                with st.spinner("🔍 Running Three-Tier Analysis..."):
                    from modules.advanced_bid_optimizer import get_three_tier_comparison
                    comparison = get_three_tier_comparison(
                        official_estimate=inputs['official_estimate'],
                        competitor_bids=inputs['competitor_bids'],
                        procurement_type=inputs['procurement_type'],
                        risk_tolerance=inputs['risk_tolerance'],
                        company_id=st.session_state.company_id,
                        nppi_factor=nppi_factor  # ✅ Pass NPPI factor to analysis
                    )
                    
                    best_tier = max(comparison.keys(), key=lambda t: comparison[t].get('confidence_score', 0) * comparison[t]['win_probability'])
                    
                    st.session_state.analysis_state['current_record'] = {
                        'tender_id': inputs['tender_id'],
                        'tender_title': inputs['tender_title'],
                        'procuring_entity': inputs['procuring_entity'],
                        'division': inputs['division'],
                        'district': inputs['district'],
                        'thana': inputs['thana'],
                        'construction_type': inputs['procurement_type'],
                        'official_estimate': round(inputs['official_estimate'], 3),
                        'competitor_bids': inputs['competitor_bids'],
                        'risk_tolerance': inputs['risk_tolerance'],
                        'procurement_type': inputs['procurement_type'],
                        'competitor_count': len(inputs['competitor_bids']),
                        'nppi_factor': nppi_factor,      # ✅ Store NPPI factor
                        'nppi_mode': nppi_mode,          # ✅ Store NPPI mode
                        'nppi_warning': nppi_warning     # ✅ Store NPPI warning
                    }
                    st.session_state.analysis_state['current_comparison'] = comparison
                    st.session_state.analysis_state['current_best_result'] = comparison[best_tier]
                    st.session_state.analysis_state['current_best_tier'] = best_tier
                    st.session_state.analysis_state['current_competitor_bids'] = inputs['competitor_bids']
                    st.session_state.analysis_state['analysis_ready_to_save'] = True
                    
                    db.increment_analysis_usage(st.session_state.user_id)
                    st.session_state.analyses_used += 1
                    st.success("✅ Analysis complete!")
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            st.error(f"❌ Analysis error: {str(e)}")

    
    # =============================================================================
    # 🔹 DISPLAY RESULTS (Using unified report generator)
    # =============================================================================
    if st.session_state.analysis_state.get('current_record') is not None:
        comparison = st.session_state.analysis_state['current_comparison']
        analysis_record = st.session_state.analysis_state['current_record']
        best_result = st.session_state.analysis_state['current_best_result']
        best_tier = st.session_state.analysis_state['current_best_tier']
        comp_bids = analysis_record.get('competitor_bids', [])
        
        # Prepare user info for report
        user_info = {
            'full_name': st.session_state.get('full_name', 'N/A'),
            'company_name': st.session_state.get('company_name', 'N/A')
        }
        
        # Prepare analysis record for report generator (matches expected structure)
        analysis_record_for_report = {
            'tender_id': analysis_record.get('tender_id'),
            'tender_title': analysis_record.get('tender_title'),
            'procuring_entity': analysis_record.get('procuring_entity'),
            'official_estimate': analysis_record.get('official_estimate'),
            'division': analysis_record.get('division'),
            'district': analysis_record.get('district'),
            'thana': analysis_record.get('thana'),
            'procurement_type': analysis_record.get('procurement_type'),
            'submission_deadline': analysis_record.get('submission_deadline', 'N/A'),
            'risk_tolerance': analysis_record.get('risk_tolerance', 'moderate'),
            'competitor_bids': comp_bids,
            'competitor_count': len(comp_bids),
            'recommended_bid': best_result.get('optimal_bid', 0),
            'success_probability': best_result.get('win_probability', 0),
            'risk_level': best_result.get('risk_level', 'MEDIUM')
        }
        
        
        # Generate and display HTML report (matches PDF content exactly)
        generate_unified_report(
            analysis_record=analysis_record_for_report,
            comparison=comparison,
            user_info=user_info,
            format='html'  # Display HTML in Streamlit
        )
        
        st.markdown("---")
        st.markdown("### 📄 Export Options")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col1:
            if can_export:
                if st.button("📑 Generate PDF Report", use_container_width=True, key="gen_pdf_btn"):
                    try:
                        pdf_buffer = generate_unified_report(
                            analysis_record=analysis_record_for_report,
                            comparison=comparison,
                            user_info=user_info,
                            format='pdf'  # Return PDF buffer
                        )
                        
                        if pdf_buffer and pdf_buffer.getbuffer().nbytes > 0:
                            safe_tid = str(analysis_record.get('tender_id', 'report')).replace('/', '_').replace(' ', '_')
                            filename = f"Babui_TenderAI_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                            st.session_state.analysis_state['_pdf_buffer'] = pdf_buffer
                            st.session_state.analysis_state['_pdf_filename'] = filename
                            st.success(f"✅ PDF generated!")
                            st.rerun()
                        else:
                            st.error("❌ PDF generation failed - empty buffer")
                    except Exception as e:
                        st.error(f"❌ PDF Error: {str(e)}")
                    pass
            else:
                st.button("🔒 PDF Report", disabled=True, use_container_width=True, 
                         help="Upgrade to export reports")
        with col2:
            if can_export:
                if st.button("📄 Save as HTML", use_container_width=True, key="save_html_btn"):
                    try:
                        # Import the new function
                        
                        
                        # Generate HTML content as string
                        html_content = generate_html_content_only(
                            analysis_record=analysis_record_for_report,
                            comparison=comparison,
                            user_info=user_info
                        )
                        
                        if html_content and len(html_content) > 0:
                            safe_tid = str(analysis_record.get('tender_id', 'report')).replace('/', '_').replace(' ', '_')
                            filename = f"Babui_TenderAI_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                            st.session_state.analysis_state['_html_buffer'] = html_content.encode('utf-8')
                            st.session_state.analysis_state['_html_filename'] = filename
                            st.success(f"✅ HTML report generated!")
                            st.rerun()
                        else:
                            st.error("❌ HTML generation failed - empty content")
                    except Exception as e:
                        st.error(f"❌ HTML Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                    pass
            else:
                st.button("🔒 HTML Report", disabled=True, use_container_width=True,
                         help="Upgrade to export reports")
                
        with col3:
            if can_export:
                # ... CSV export code ...
                # CSV Export
                export_rows = []
                for tier, result in comparison.items():
                    export_rows.append({
                        'Tier': tier.upper(),
                        'Method': result.get('method', ''),
                        'Optimal_Bid_BDT': result['optimal_bid'],
                        'Win_Probability_%': round(result['win_probability'] * 100, 1),
                        'Confidence_%': round(result.get('confidence_score', 0.7) * 100, 1),
                        'PPR_Compliant': 'Yes' if result.get('optimal_bid', 0) >= result.get('slt_threshold', 0) else 'No'
                    })
                csv = pd.DataFrame(export_rows).to_csv(index=False)
                st.download_button(
                    "📥 Export CSV", 
                    data=csv, 
                    file_name=f"analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )
                pass
            else:
                st.button("🔒 CSV Export", disabled=True, use_container_width=True,
                         help="Upgrade to export data")
        with col4:
            has_valid_data = st.session_state.analysis_state.get('current_record') is not None
            if can_run:
                st.button(
                    "💾 Save to History", 
                    key="save_analysis_main_btn", 
                    use_container_width=True, 
                    type="primary", 
                    disabled=not has_valid_data, 
                    on_click=_save_analysis_callback
                )
            else:
                st.button("🔒 Save to History", disabled=True, use_container_width=True,
                         help="You don't have permission to save analyses")            

        with col5:            
            if st.button("🔄 New Analysis", use_container_width=True, type="secondary"):
                sync_form_to_model()
                for key in ['current_record', 'current_comparison', 'current_best_result', '_pdf_buffer', '_pdf_filename', '_html_buffer', '_html_filename']:
                    if key in st.session_state.analysis_state:
                        st.session_state.analysis_state[key] = None
                st.rerun()
                pass

        # Download section for generated files
        if can_export:
            st.markdown("---")
            st.markdown("### 📁 Download Ready Files")

            # Create columns for downloads
            col_d1, col_d2, col_d3 = st.columns(3)

            with col_d1:
                if st.session_state.analysis_state.get('_pdf_buffer') and st.session_state.analysis_state.get('_pdf_filename'):
                    st.download_button(
                        "💾 Download PDF Report",
                        data=st.session_state.analysis_state['_pdf_buffer'],
                        file_name=st.session_state.analysis_state['_pdf_filename'],
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf_report"
                    )

            with col_d2:
                if st.session_state.analysis_state.get('_html_buffer') and st.session_state.analysis_state.get('_html_filename'):
                    st.download_button(
                        "📄 Download HTML Report",
                        data=st.session_state.analysis_state['_html_buffer'],
                        file_name=st.session_state.analysis_state['_html_filename'],
                        mime="text/html",
                        use_container_width=True,
                        key="download_html_report"
                    )

            with col_d3:
                # Clear files button
                if st.button("🗑️ Clear All Reports", use_container_width=True, key="clear_reports"):
                    st.session_state.analysis_state['_pdf_buffer'] = None
                    st.session_state.analysis_state['_pdf_filename'] = None
                    st.session_state.analysis_state['_html_buffer'] = None
                    st.session_state.analysis_state['_html_filename'] = None
                    st.rerun()
            
        # Show recently saved status
        if st.session_state.analysis_state.get('last_saved_analysis_id'):
            saved_id = st.session_state.analysis_state['last_saved_analysis_id']
            saved_tender = st.session_state.analysis_state.get('last_saved_tender_id', 'Unknown')
            st.success(f"✨ Last saved: Analysis #{saved_id} for Tender {saved_tender}")
    
    debug_print("✅ Tender analysis page complete")