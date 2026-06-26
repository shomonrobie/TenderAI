# modules/subscriber_dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
import json

class SubscriberDashboard:
    """Unified dashboard for company subscribers"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Main dashboard"""
        
        company_id = st.session_state.get('company_id')
        
        if not company_id:
            st.error("No company associated with this account")
            return
        
        # ✅ Get subscription info using CRUD method
        sub = self.db.get_company_subscription(company_id)
        
        # Header with subscription status
        self._render_header(sub)
        
        # Usage metrics
        self._render_usage_metrics(company_id, sub)
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Tenders",
            "📊 BOQ Generation",
            "🎯 Bid Optimization",
            "📈 Reports",
            "⚙️ Settings"
        ])
        
        with tab1:
            self._render_tender_management(company_id)
        
        with tab2:
            self._render_boq_generation(company_id, sub)
        
        with tab3:
            self._render_bid_optimization(company_id, sub)
        
        with tab4:
            self._render_reports(company_id, sub)
        
        with tab5:
            self._render_settings(company_id)
    
    def _render_header(self, sub):
        """Render dashboard header with subscription info"""
        
        plan = sub.get('subscription_tier', 'free')
        plan_name = sub.get('plan_name', plan.capitalize())
        status = sub.get('status', 'active')
        
        # Get plan config for display
        from modules.subscription import PLANS
        plan_config = PLANS.get(plan, PLANS['free'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Plan", plan_name.upper())
        
        with col2:
            days_left = 999
            end_date = sub.get('end_date')
            if end_date:
                try:
                    if isinstance(end_date, str):
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    else:
                        end_date_obj = end_date
                    days_left = (end_date_obj - datetime.now().date()).days
                except:
                    pass
            st.metric("Days Remaining", max(0, days_left))
        
        with col3:
            max_boq = sub.get('max_boq_generations', 5)
            boq_used = sub.get('boq_used', 0)
            if max_boq == -1:
                boq_remaining = "∞"
            else:
                boq_remaining = max(0, max_boq - boq_used)
            st.metric("BOQ Remaining", boq_remaining)
        
        with col4:
            max_bid = sub.get('max_bid_optimizations', 5)
            bid_used = sub.get('bid_optimizations_used', 0)
            if max_bid == -1:
                bid_remaining = "∞"
            else:
                bid_remaining = max(0, max_bid - bid_used)
            st.metric("Bid Optimizations", bid_remaining)
        
        # Warning if limits are low
        if max_boq != -1 and max_boq > 0:
            boq_percent = (boq_used / max_boq) * 100 if max_boq > 0 else 0
            if boq_percent > 80:
                st.warning(f"⚠️ You have used {boq_percent:.0f}% of your BOQ limit. Upgrade to continue.")
        
        st.markdown("---")
    
    def _render_usage_metrics(self, company_id, sub):
        """Render usage metrics with progress bars"""
        
        st.markdown("### 📊 Usage This Month")
        
        max_boq = sub.get('max_boq_generations', 5)
        boq_used = sub.get('boq_used', 0)
        max_bid = sub.get('max_bid_optimizations', 5)
        bid_used = sub.get('bid_optimizations_used', 0)
        max_analyses = sub.get('max_projects', 5)
        analyses_used = sub.get('analyses_used', 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if max_boq == -1:
                st.progress(0)
                st.caption("BOQ: Unlimited")
            else:
                percent = (boq_used / max_boq) * 100 if max_boq > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"BOQ: {boq_used} / {max_boq} ({percent:.0f}%)")
        
        with col2:
            if max_bid == -1:
                st.progress(0)
                st.caption("Bid Optimizations: Unlimited")
            else:
                percent = (bid_used / max_bid) * 100 if max_bid > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"Bid Opt: {bid_used} / {max_bid} ({percent:.0f}%)")
        
        with col3:
            if max_analyses == -1:
                st.progress(0)
                st.caption("Analyses: Unlimited")
            else:
                percent = (analyses_used / max_analyses) * 100 if max_analyses > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"Analyses: {analyses_used} / {max_analyses} ({percent:.0f}%)")
        
        st.markdown("---")
    
    def _get_company_tenders(self, company_id):
        """Get tenders for company using CRUD method"""
        try:
            return self.db.get_company_tenders(company_id)
        except:
            return pd.DataFrame()
    
    def _render_tender_management(self, company_id):
        """Manage tenders"""
        
        st.markdown("### 📋 Tender Management")
        
        # Get existing tenders using CRUD method
        tenders = self._get_company_tenders(company_id)
        
        if not tenders.empty:
            st.markdown("#### Your Tenders")
            
            # Format for display
            display_cols = ['tender_id', 'tender_title', 'procuring_entity', 'official_estimate', 'bid_status', 'created_at']
            available_cols = [col for col in display_cols if col in tenders.columns]
            
            display_df = tenders[available_cols].copy()
            if 'official_estimate' in display_df.columns:
                display_df['official_estimate'] = display_df['official_estimate'].apply(lambda x: f"৳{x:,.2f}" if x else 'N/A')
            if 'created_at' in display_df.columns:
                display_df['created_at'] = display_df['created_at'].astype(str).str[:10]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # View/Edit selected tender
            if 'tender_id' in tenders.columns:
                tender_list = tenders['tender_id'].tolist()
                if tender_list:
                    selected_tender = st.selectbox(
                        "Select tender to work on",
                        options=tender_list,
                        format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50] if 'tender_title' in tenders.columns else x}"
                    )
                    
                    if selected_tender:
                        st.session_state['selected_tender_id'] = selected_tender
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("📊 Generate BOQ", use_container_width=True):
                                st.session_state['boq_tender'] = selected_tender
                                st.rerun()
                        with col2:
                            if st.button("🎯 Run Optimization", use_container_width=True):
                                st.session_state['optimize_tender'] = selected_tender
                                st.rerun()
                        with col3:
                            if st.button("📈 View Analysis", use_container_width=True):
                                st.session_state['analyze_tender'] = selected_tender
                                st.rerun()
        
        # Create new tender
        with st.expander("➕ Create New Tender", expanded=False):
            with st.form("new_tender_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    tender_id = st.text_input("Tender ID *", placeholder="e-GP Reference Number")
                    tender_title = st.text_input("Tender Title *")
                    procuring_entity = st.text_input("Procuring Entity")
                
                with col2:
                    division = st.selectbox("Division", ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Rangpur", "Mymensingh", "Barishal", "Sylhet"])
                    official_estimate = st.number_input("Official Estimate (BDT)", min_value=0.0, step=100000.0)
                
                submitted = st.form_submit_button("Create Tender", type="primary")
                
                if submitted:
                    if tender_id and tender_title:
                        self._create_tender(company_id, tender_id, tender_title, procuring_entity, division, official_estimate)
                        st.success("✅ Tender created successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill Tender ID and Title")
    
    def _render_boq_generation(self, company_id, sub):
        """Generate BOQ for a tender"""
        
        st.markdown("### 📊 BOQ Generation")
        
        # Check limit
        max_boq = sub.get('max_boq_generations', 5)
        boq_used = sub.get('boq_used', 0)
        
        if max_boq != -1 and boq_used >= max_boq:
            st.error(f"❌ You have reached your BOQ limit ({max_boq}). Please upgrade your plan.")
            return
        
        # Get tenders
        tenders = self._get_company_tenders(company_id)
        
        if tenders.empty:
            st.info("No tenders found. Please create a tender first.")
            return
        
        # Select tender
        if 'tender_id' in tenders.columns:
            selected_tender = st.selectbox(
                "Select Tender",
                options=tenders['tender_id'].tolist(),
                format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50] if 'tender_title' in tenders.columns else x}",
                key="boq_tender_select"
            )
        else:
            st.warning("No tenders available")
            return
        
        if selected_tender:
            # Get tender data
            tender_row = tenders[tenders['tender_id'] == selected_tender]
            official_estimate = tender_row['official_estimate'].iloc[0] if 'official_estimate' in tender_row.columns else 0
            
            st.info(f"**Official Estimate:** ৳{official_estimate:,.2f}")
            
            # Select rate source
            rate_source = st.radio("Rate Schedule", ["PWD", "LGED"], horizontal=True)
            
            if st.button("Generate BOQ", type="primary"):
                with st.spinner("Generating BOQ..."):
                    boq_data = self._generate_sample_boq(selected_tender, official_estimate)
                    
                    if boq_data is not None:
                        # Increment usage (using CRUD method)
                        self._increment_usage(company_id, 'boq')
                        
                        st.success("✅ BOQ generated successfully!")
                        
                        # Display BOQ
                        st.dataframe(boq_data, use_container_width=True)
                        
                        # Download option
                        csv = boq_data.to_csv(index=False)
                        st.download_button(
                            "📥 Download BOQ (CSV)",
                            csv,
                            f"boq_{selected_tender}_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
    
    def _render_bid_optimization(self, company_id, sub):
        """Run bid optimization"""
        
        st.markdown("### 🎯 Bid Optimization")
        
        # Check limit
        max_bid = sub.get('max_bid_optimizations', 5)
        bid_used = sub.get('bid_optimizations_used', 0)
        
        if max_bid != -1 and bid_used >= max_bid:
            st.error(f"❌ You have reached your bid optimization limit ({max_bid}). Please upgrade your plan.")
            return
        
        # Get tenders
        tenders = self._get_company_tenders(company_id)
        
        if tenders.empty:
            st.info("No tenders found. Please create a tender first.")
            return
        
        # Select tender
        if 'tender_id' in tenders.columns:
            selected_tender = st.selectbox(
                "Select Tender",
                options=tenders['tender_id'].tolist(),
                format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50] if 'tender_title' in tenders.columns else x}",
                key="optimize_tender_select"
            )
        else:
            st.warning("No tenders available")
            return
        
        if selected_tender:
            tender_row = tenders[tenders['tender_id'] == selected_tender]
            official_estimate = tender_row['official_estimate'].iloc[0] if 'official_estimate' in tender_row.columns else 0
            
            st.info(f"**Official Estimate:** ৳{official_estimate:,.2f}")
            
            # Simple optimization
            if st.button("Run Optimization", type="primary"):
                with st.spinner("Running optimization..."):
                    result = self._run_optimization(selected_tender, official_estimate)
                    
                    if result:
                        # Increment usage
                        self._increment_usage(company_id, 'bid')
                        
                        # Display results
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Recommended Bid", f"৳{result['recommended_bid']:,.2f}")
                        col2.metric("Win Probability", f"{result['win_probability']:.1f}%")
                        col3.metric("Expected Profit", f"৳{result['expected_profit']:,.2f}")
                        
                        st.markdown("#### Recommendation")
                        st.success(result['recommendation'])
        
        # Add competitor
        with st.expander("➕ Add Competitor", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                comp_name = st.text_input("Competitor Name")
            with col2:
                comp_bid = st.number_input("Bid Amount (BDT)", min_value=0.0, step=100000.0)
            
            if st.button("Add Competitor"):
                if comp_name and comp_bid > 0:
                    self._add_competitor_bid(selected_tender, comp_name, comp_bid)
                    st.rerun()
    
    def _render_reports(self, company_id, sub):
        """Generate reports"""
        
        st.markdown("### 📈 Reports")
        
        can_export = sub.get('can_export_data', False)
        
        if not can_export:
            st.warning("🔒 Export feature is not available in your current plan. Upgrade to Professional or Enterprise to export data.")
            return
        
        report_type = st.selectbox("Select Report Type", [
            "BOQ History",
            "Bid Analysis",
            "Tender Performance"
        ])
        
        if st.button("Generate Report", type="primary"):
            report_data = self._generate_report(company_id, report_type)
            
            if report_data is not None and not report_data.empty:
                csv = report_data.to_csv(index=False)
                st.download_button(
                    "📥 Download Report (CSV)",
                    csv,
                    f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
                
                st.markdown("#### Report Preview")
                st.dataframe(report_data.head(20), use_container_width=True)
    
    def _render_settings(self, company_id):
        """Company settings"""
        
        st.markdown("### ⚙️ Company Settings")
        
        # Get company info using CRUD method
        company = self.db.get_company_by_id(company_id)
        
        if company:
            with st.form("company_settings_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Company Name", value=company.get('company_name', ''))
                    new_email = st.text_input("Email", value=company.get('email', ''))
                with col2:
                    new_phone = st.text_input("Phone", value=company.get('phone', ''))
                    new_division = st.text_input("Division", value=company.get('division', ''))
                
                submitted = st.form_submit_button("Save Changes")
                if submitted:
                    # Update company using CRUD method
                    updates = {}
                    if new_name != company.get('company_name'):
                        updates['company_name'] = new_name
                    if new_email != company.get('email'):
                        updates['email'] = new_email
                    if new_phone != company.get('phone'):
                        updates['phone'] = new_phone
                    if new_division != company.get('division'):
                        updates['division'] = new_division
                    
                    if updates:
                        success = self.db.update_company(company_id, updates)
                        if success:
                            st.success("Settings saved!")
                            st.rerun()
                        else:
                            st.error("Failed to save settings")
    
    # ========== Helper Methods ==========
    
    def _create_tender(self, company_id, tender_id, title, procuring_entity, division, estimate):
        """Create new tender using CRUD method"""
        try:
            tender_data = {
                'tender_id': tender_id,
                'tender_title': title,
                'procuring_entity': procuring_entity,
                'division': division,
                'official_estimate': estimate,
                'created_by': st.session_state.get('user_id', 0)
            }
            # Use CRUD method if available
            if hasattr(self.db, 'create_tender'):
                return self.db.create_tender(company_id, tender_data)
            else:
                # Fallback direct insert
                with self.db.get_connection() as conn:
                    cursor = self.db.db_conn.get_cursor(conn)
                    cursor.execute("""
                        INSERT INTO company_tenders (company_id, tender_id, tender_title, procuring_entity, 
                                                    division, official_estimate, created_by, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (company_id, tender_id, title, procuring_entity, division, estimate, 
                          st.session_state.get('user_id', 0)))
                    return True
        except Exception as e:
            st.error(f"Error creating tender: {e}")
            return False
    
    def _add_competitor_bid(self, tender_id, competitor_name, bid_amount):
        """Add competitor bid"""
        try:
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                cursor.execute("""
                    INSERT INTO competitor_bids (tender_id, competitor_name, total_bid_amount, submission_date)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (tender_id, competitor_name, bid_amount))
                st.success("✅ Competitor added!")
        except Exception as e:
            st.error(f"Error adding competitor: {e}")
    
    def _generate_sample_boq(self, tender_id, official_estimate):
        """Generate sample BOQ data"""
        import random
        items = [
            {'Item': 'Excavation', 'Unit': 'm3', 'Qty': 100, 'Rate': 500},
            {'Item': 'Concrete (RCC)', 'Unit': 'm3', 'Qty': 50, 'Rate': 8000},
            {'Item': 'Steel Reinforcement', 'Unit': 'kg', 'Qty': 2000, 'Rate': 90},
            {'Item': 'Brick Work', 'Unit': 'm3', 'Qty': 80, 'Rate': 2500},
            {'Item': 'Plastering', 'Unit': 'm2', 'Qty': 500, 'Rate': 200},
            {'Item': 'Painting', 'Unit': 'm2', 'Qty': 400, 'Rate': 120},
        ]
        
        data = []
        total = 0
        for item in items:
            qty = item['Qty'] * random.uniform(0.8, 1.2)
            rate = item['Rate'] * random.uniform(0.9, 1.1)
            amount = qty * rate
            total += amount
            data.append({
                'Item Code': f'ITEM-{len(data)+1:03d}',
                'Description': item['Item'],
                'Unit': item['Unit'],
                'Quantity': round(qty, 2),
                'Unit Rate': round(rate, 2),
                'Amount': round(amount, 2)
            })
        
        # Scale to match official estimate
        scale = official_estimate / total if total > 0 else 1
        for row in data:
            row['Amount'] = round(row['Amount'] * scale, 2)
            row['Unit Rate'] = round(row['Unit Rate'] * scale, 2)
        
        df = pd.DataFrame(data)
        df['Amount'] = df['Amount'].apply(lambda x: round(x, 2))
        return df
    
    def _run_optimization(self, tender_id, official_estimate):
        """Run simple bid optimization"""
        # Get competitor bids
        competitors = self._get_competitor_bids(tender_id)
        
        if competitors.empty:
            recommended = official_estimate * 0.95
            win_prob = 70
            profit = recommended * 0.12
            recommendation = f"Based on the official estimate of ৳{official_estimate:,.2f}, we recommend bidding around ৳{recommended:,.2f} (5% below estimate) for competitive positioning."
        else:
            min_bid = competitors['total_bid_amount'].min()
            avg_bid = competitors['total_bid_amount'].mean()
            
            recommended = min(min_bid * 0.98, official_estimate * 0.95)
            win_prob = min(95, 100 - (len(competitors) * 5))
            profit = recommended * 0.10
            recommendation = f"Lowest competitor bid is ৳{min_bid:,.2f}. Recommend bidding ৳{recommended:,.2f} for optimal win probability."
        
        return {
            'recommended_bid': recommended,
            'win_probability': win_prob,
            'expected_profit': profit,
            'recommendation': recommendation
        }
    
    def _get_competitor_bids(self, tender_id):
        """Get competitor bids for a tender"""
        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql_query("""
                    SELECT competitor_name, total_bid_amount, submission_date
                    FROM competitor_bids
                    WHERE tender_id = ?
                    ORDER BY total_bid_amount
                """, conn, params=[tender_id])
                return df
        except:
            return pd.DataFrame()
    
    def _increment_usage(self, company_id, resource_type):
        """Increment usage counter using CRUD method"""
        try:
            # Use subscription manager if available
            if hasattr(self.db, 'increment_usage'):
                return self.db.increment_usage(company_id, resource_type)
            else:
                # Fallback direct update
                field_map = {
                    'boq': 'boq_used',
                    'bid': 'bid_optimizations_used'
                }
                if resource_type in field_map:
                    field = field_map[resource_type]
                    with self.db.get_connection() as conn:
                        cursor = self.db.db_conn.get_cursor(conn)
                        cursor.execute(f"""
                            UPDATE subscriptions 
                            SET {field} = {field} + 1, updated_at = CURRENT_TIMESTAMP
                            WHERE company_id = ?
                        """, (company_id,))
                        return True
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            return False
    
    def _generate_report(self, company_id, report_type):
        """Generate report data"""
        try:
            with self.db.get_connection() as conn:
                if report_type == "BOQ History":
                    df = pd.read_sql_query("""
                        SELECT tender_id, tender_title, rate_source, item_count, 
                               total_estimated_cost, generated_at
                        FROM boq_generation_history
                        WHERE company_id = ?
                        ORDER BY generated_at DESC
                    """, conn, params=[company_id])
                
                elif report_type == "Bid Analysis":
                    df = pd.read_sql_query("""
                        SELECT tender_title, official_estimate, recommended_bid,
                               success_probability, expected_profit, analysis_date
                        FROM tender_analyses
                        WHERE company_id = ? AND analysis_type = 'bid_optimization'
                        ORDER BY analysis_date DESC
                    """, conn, params=[company_id])
                
                elif report_type == "Tender Performance":
                    df = pd.read_sql_query("""
                        SELECT tender_id, tender_title, official_estimate,
                               CASE WHEN bid_status = 'Won' THEN 'Won' ELSE 'Lost' END as result,
                               created_at
                        FROM company_tenders
                        WHERE company_id = ?
                        ORDER BY created_at DESC
                    """, conn, params=[company_id])
                else:
                    df = pd.DataFrame()
                
                return df
                
        except Exception as e:
            st.error(f"Error generating report: {e}")
            return pd.DataFrame()


# Convenience function
def render_subscriber_dashboard(db):
    dashboard = SubscriberDashboard(db)
    dashboard.render()