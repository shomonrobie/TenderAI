# modules/boq_bid_bridge.py - Fixed render_boq_bid_integration

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.boq_generator import BOQGenerator
from modules.advanced_bid_optimizer import get_three_tier_comparison
from modules.report_generator import generate_enhanced_report
from modules.rbac import (
    rbac, can_optimize_bid, can_view_tenders, can_export_data,
    render_role_badge, require_permission
)
from database.unified_db_manager import get_db_manager


class BOQBidIntegrator:
    """Bridge between BOQ Generator and Bid Optimizer"""
    
    def __init__(self, db):
        self.db = db
        self.boq_gen = BOQGenerator()
    
    def get_boq_total_cost(self, tender_id):
        """Get total estimated cost from BOQ for a tender"""
        result = self.db.query("""
            SELECT id, total_estimated_cost, selected_zone, rate_source, edition_year,
                   item_count, generated_at, file_name
            FROM boq_generation_history 
            WHERE tender_id = ? AND status = 'completed'
            ORDER BY generated_at DESC
            LIMIT 1
        """, params=[tender_id])
        
        # ✅ Handle both list and DataFrame
        if result:
            if isinstance(result, list) and len(result) > 0:
                row = result[0]
            elif hasattr(result, 'iloc') and not result.empty:
                row = result.iloc[0].to_dict()
            else:
                return None
            
            return {
                'total_cost': float(row.get('total_estimated_cost', 0)) if row.get('total_estimated_cost') is not None else 0.0,
                'boq_id': row.get('id'),
                'zone': row.get('selected_zone'),
                'source': row.get('rate_source'),
                'edition_year': row.get('edition_year'),
                'item_count': row.get('item_count'),
                'generated_at': row.get('generated_at')
            }
        return None
    
    def get_competitor_bids_for_tender(self, tender_id):
        """Get competitor bids recorded for this tender"""
        result = self.db.query("""
            SELECT competitor_name, total_bid_amount as bid
            FROM competitor_bids 
            WHERE tender_id = ?
            ORDER BY total_bid_amount ASC
        """, params=[tender_id])
        
        # ✅ Handle both list and DataFrame
        if result:
            if isinstance(result, list):
                for r in result:
                    if r.get('bid') is not None:
                        r['bid'] = float(r['bid'])
                return result
            elif hasattr(result, 'to_dict'):
                records = result.to_dict('records')
                for r in records:
                    if r.get('bid') is not None:
                        r['bid'] = float(r['bid'])
                return records
        return []
    
    def prepare_optimization_input(self, tender_id, official_estimate, competitor_bids=None):
        """Prepare input for bid optimizer using BOQ data"""
        boq_data = self.get_boq_total_cost(tender_id)
        estimated_cost = boq_data['total_cost'] if boq_data else official_estimate
        
        if competitor_bids is None:
            competitor_bids = self.get_competitor_bids_for_tender(tender_id)
        
        return {
            'official_estimate': estimated_cost,
            'competitor_bids': competitor_bids,
            'tender_id': tender_id,
            'boq_data': boq_data
        }
    
    def run_optimization(self, tender_id, official_estimate, competitor_bids=None, 
                         procurement_type='works', risk_tolerance='moderate',
                         company_id=None, nppi_factor=None):
        """Run complete optimization with BOQ data"""
        opt_input = self.prepare_optimization_input(tender_id, official_estimate, competitor_bids)
        
        comparison = get_three_tier_comparison(
            official_estimate=opt_input['official_estimate'],
            competitor_bids=opt_input['competitor_bids'],
            procurement_type=procurement_type,
            risk_tolerance=risk_tolerance,
            historical_data=None,
            company_id=company_id,
            nppi_factor=nppi_factor
        )
        
        comparison['boq_metadata'] = opt_input['boq_data']
        return comparison, opt_input


@require_permission('can_optimize_bid')
def render_boq_bid_integration():
    """UI for integrating BOQ with Bid Optimizer with RBAC"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 BOQ to Bid Optimizer</h1>
        <p>Integrate BOQ estimates with AI-powered bid optimization</p>
    </div>
    """, unsafe_allow_html=True)
    
    render_role_badge()
    st.markdown("---")
    
    # Initialize database connection using singleton
    db = get_db_manager()
    
    # Get user info
    user_id = st.session_state.get('user_id')
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    permissions = rbac.get_current_user_permissions()
    
    if not permissions.get('can_optimize_bid', False):
        st.error("🔒 You don't have permission to run bid optimization.")
        st.info("Contact your administrator to upgrade your role.")
        return
    
    # Show permission info
    if user_role == 'viewer':
        st.info("👁️ **Viewer Mode:** You can view results but cannot submit bids.")
    elif user_role == 'analyst':
        st.info("📈 **Analyst Mode:** You can run optimization and submit bids.")
    elif user_role in ['manager', 'company_admin']:
        st.info("📊 **Manager Mode:** Full access to optimization and bid submission.")
    
    # Step 1: Select Tender
    st.markdown("### Step 1: Select Tender")
    
    # ✅ Get tenders as list and convert to DataFrame for display
    tenders_result = db.query("""
        SELECT DISTINCT t.id, t.tender_id, t.tender_title, t.procuring_entity, 
               t.official_estimate, t.procurement_type,
               b.id as boq_id, b.total_estimated_cost, b.generated_at
        FROM company_tenders t
        LEFT JOIN boq_generation_history b ON t.tender_id = b.tender_id
        WHERE t.company_id = ? AND t.is_active = 1
        ORDER BY b.generated_at DESC NULLS LAST, t.submission_deadline ASC
    """, params=[company_id])
    
    # ✅ Convert to DataFrame for display
    if isinstance(tenders_result, list):
        df_tenders = pd.DataFrame(tenders_result) if tenders_result else pd.DataFrame()
    else:
        df_tenders = tenders_result
    
    if df_tenders.empty:
        st.warning("No tenders found. Please create a tender and generate BOQ first.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if permissions.get('can_create_tender', False):
                if st.button("📋 Tender Management", use_container_width=True):
                    st.session_state.page = "tender_management"
                    st.rerun()
        with col2:
            if permissions.get('can_create_boq', False):
                if st.button("📄 Generate BOQ", use_container_width=True):
                    st.session_state.page = "boq_generator"
                    st.rerun()
        with col3:
            if st.button("📚 View Tutorial", use_container_width=True):
                st.session_state.page = "tutorial"
                st.rerun()
        return
    
    # Display tenders safely
    display_data = []
    for _, row in df_tenders.iterrows():
        boq_id = row.get('boq_id')
        total_cost = row.get('total_estimated_cost')
        official_est = row.get('official_estimate')
        
        display_data.append({
            'ID': row.get('tender_id', 'N/A'),
            'Title': str(row.get('tender_title', ''))[:60],
            'Entity': str(row.get('procuring_entity', ''))[:40],
            'BOQ Status': '✅ Yes' if pd.notna(boq_id) and boq_id is not None else '❌ No',
            'BOQ Cost': f"BDT {float(total_cost):,.3f}" if pd.notna(total_cost) and total_cost is not None else 'N/A',
            'Official Est.': f"BDT {float(official_est):,.3f}" if pd.notna(official_est) and official_est is not None else 'N/A'
        })
    
    st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
    
    tender_options = df_tenders['tender_id'].tolist()
    selected_tender_id = st.selectbox(
        "Select Tender for Optimization",
        options=tender_options if tender_options else [],
        format_func=lambda x: f"{x} - {df_tenders[df_tenders['tender_id']==x]['tender_title'].iloc[0][:50]}" if len(df_tenders) > 0 else str(x)
    )
    
    if not selected_tender_id:
        return
    
    tender_row = df_tenders[df_tenders['tender_id'] == selected_tender_id].iloc[0]
    
    st.markdown("---")
    st.markdown("### Step 2: Configure Optimization")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        procurement_type = st.selectbox("Procurement Type", options=['works', 'goods', 'services'], index=0)
    with col2:
        risk_tolerance = st.select_slider("Risk Tolerance", options=['aggressive', 'moderate', 'conservative'], value='moderate')
    with col3:
        nppi_factor = st.number_input("NPPI Factor (optional)", min_value=0.70, max_value=1.10, value=0.920, step=0.005, format="%.3f", help="Leave as 0.920 for default market index")
    
    # Competitor bids
    st.markdown("### Step 3: Competitor Intelligence")
    
    # ✅ Get competitor bids as list
    comp_result = db.query("""
        SELECT competitor_name, total_bid_amount
        FROM competitor_bids 
        WHERE tender_id = ?
        ORDER BY total_bid_amount ASC
    """, params=[selected_tender_id])
    
    if isinstance(comp_result, list):
        df_competitors = pd.DataFrame(comp_result) if comp_result else pd.DataFrame()
    else:
        df_competitors = comp_result
    
    if not df_competitors.empty:
        st.info(f"📊 Found {len(df_competitors)} competitor bids for this tender")
        st.dataframe(df_competitors, use_container_width=True, hide_index=True)
    
    with st.expander("➕ Add Competitor Bid", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            comp_name = st.text_input("Competitor Name", key="comp_name")
        with col2:
            comp_bid = st.number_input("Bid Amount (BDT)", min_value=0.0, step=100000.0, key="comp_bid")
        
        if permissions.get('can_edit_tender', False):
            if st.button("Add Competitor Bid", key="add_comp"):
                if comp_name and comp_bid > 0:
                    db.execute("""
                        INSERT INTO competitor_bids (tender_id, competitor_name, total_bid_amount, submission_date)
                        VALUES (?, ?, ?, ?)
                    """, (selected_tender_id, comp_name, float(comp_bid), datetime.now().isoformat()))
                    st.success(f"Added competitor: {comp_name}")
                    st.rerun()
        else:
            st.info("🔒 You don't have permission to add competitor bids. View-only mode.")
    
    st.markdown("---")
    
    # Create integrator with db
    integrator = BOQBidIntegrator(db)
    can_run_opt = permissions.get('can_optimize_bid', False) or user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']
    
    if can_run_opt:
        if st.button("🚀 Run Bid Optimization", type="primary", use_container_width=True):
            with st.spinner("Running AI-powered optimization..."):
                competitor_bids = integrator.get_competitor_bids_for_tender(selected_tender_id)
                
                official_estimate = float(tender_row.get('official_estimate', 0)) if pd.notna(tender_row.get('official_estimate')) else 0.0
                
                comparison, opt_input = integrator.run_optimization(
                    tender_id=selected_tender_id,
                    official_estimate=official_estimate,
                    competitor_bids=competitor_bids if competitor_bids else None,
                    procurement_type=procurement_type,
                    risk_tolerance=risk_tolerance,
                    company_id=company_id,
                    nppi_factor=nppi_factor if nppi_factor != 0.920 else None
                )
                
                st.session_state.optimization_result = {
                    'comparison': comparison,
                    'tender_id': selected_tender_id,
                    'tender_title': tender_row.get('tender_title', 'Unknown'),
                    'official_estimate': official_estimate,
                    'competitor_count': len(competitor_bids),
                    'boq_cost': opt_input['boq_data']['total_cost'] if opt_input.get('boq_data') else None,
                    'analysis_time': datetime.now().isoformat()
                }
                
                st.success("✅ Optimization complete!")
                st.rerun()
    else:
        st.info("🔒 You don't have permission to run bid optimization. Contact your administrator.")
    
    # Display results
    if st.session_state.get('optimization_result'):
        st.markdown("---")
        st.markdown("### 📊 Optimization Results")
        
        result = st.session_state.optimization_result
        comparison = result.get('comparison', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        best_bid = float(comparison.get('advanced', {}).get('optimal_bid', 0))
        best_win_prob = float(comparison.get('advanced', {}).get('win_probability', 0))
        
        with col1:
            st.metric("Recommended Bid", f"BDT {best_bid:,.3f}")
        with col2:
            st.metric("Win Probability", f"{best_win_prob*100:.1f}%")
        with col3:
            bid_ratio = best_bid / result['official_estimate'] if result.get('official_estimate', 0) > 0 else 0
            st.metric("% of Estimate", f"{bid_ratio*100:.1f}%")
        with col4:
            st.metric("Competitors", result.get('competitor_count', 0))
        
        # Three-tier table
        st.markdown("#### Three-Tier Analysis")
        tier_data = []
        for tier in ['basic', 'advanced', 'enhanced']:
            if tier in comparison:
                t = comparison[tier]
                tier_data.append({
                    'Tier': tier.upper(),
                    'Method': str(t.get('method', 'N/A'))[:30],
                    'Optimal Bid': f"BDT {float(t.get('optimal_bid', 0)):,.3f}",
                    'Win Prob': f"{float(t.get('win_probability', 0))*100:.1f}%",
                    'Bid Ratio': f"{float(t.get('bid_ratio', 0))*100:.1f}%",
                    'Risk': t.get('risk_level', 'N/A')
                })
        
        st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)
        
        # Actions based on permissions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if permissions.get('can_edit_tender', False):
                if st.button("📝 Apply to Tender", use_container_width=True):
                    db.execute("""
                        UPDATE company_tenders 
                        SET our_bid_amount = ?, updated_at = ?
                        WHERE tender_id = ? AND company_id = ?
                    """, (best_bid, datetime.now().isoformat(), selected_tender_id, company_id))
                    st.success(f"✅ Recommended bid BDT {best_bid:,.3f} applied!")
            else:
                st.button("🔒 Apply to Tender", disabled=True, use_container_width=True, help="You don't have permission to edit tenders")
        
        with col2:
            if permissions.get('can_export_data', False):
                if st.button("📄 Generate Report", use_container_width=True):
                    analysis_record = {
                        'tender_id': selected_tender_id,
                        'tender_title': result.get('tender_title', 'Unknown'),
                        'procuring_entity': tender_row.get('procuring_entity', ''),
                        'official_estimate': result.get('official_estimate', 0),
                        'competitor_bids': integrator.get_competitor_bids_for_tender(selected_tender_id),
                        'procurement_type': procurement_type,
                        'risk_tolerance': risk_tolerance,
                        'nppi_factor': nppi_factor,
                        'analysis_date': datetime.now()
                    }
                    
                    user_info = {
                        'full_name': st.session_state.get('full_name', 'User'),
                        'company_name': st.session_state.get('company_name', 'N/A')
                    }
                    
                    generate_enhanced_report(analysis_record, comparison, user_info, format='html')
            else:
                st.button("🔒 Generate Report", disabled=True, use_container_width=True, help="You don't have permission to export reports")
        
        with col3:
            if permissions.get('can_submit_bid', False):
                if st.button("📤 Submit Bid", type="primary", use_container_width=True):
                    db.execute("""
                        UPDATE company_tenders 
                        SET our_bid_amount = ?, bid_status = 'submitted', 
                            bid_submission_date = ?, bid_submitted_by = ?
                        WHERE tender_id = ? AND company_id = ?
                    """, (best_bid, datetime.now().isoformat(), user_id, selected_tender_id, company_id))
                    st.success(f"✅ Bid BDT {best_bid:,.3f} submitted!")
                    st.balloons()
            else:
                st.button("🔒 Submit Bid", disabled=True, use_container_width=True, type="primary", help="You don't have permission to submit bids")