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
        
        # Get subscription info
        sub = self._get_subscription(company_id)
        
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
    
    def _get_subscription(self, company_id):
        """Get company subscription with plan details"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, p.max_boq_generations, p.max_bid_optimizations,
                       p.max_tender_analyses, p.max_users, p.can_export_data,
                       p.can_manage_team, p.plan_name
                FROM subscriptions s
                LEFT JOIN subscription_plans p ON s.plan = p.plan_name
                WHERE s.company_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC LIMIT 1
            """, (company_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'plan': row[3],
                    'plan_name': row[21] if len(row) > 21 else row[3].capitalize(),
                    'status': row[4],
                    'boq_used': row[14] if len(row) > 14 else 0,
                    'max_boq': row[15] if len(row) > 15 else 5,
                    'bid_used': row[16] if len(row) > 16 else 0,
                    'max_bid': row[17] if len(row) > 17 else 5,
                    'analyses_used': row[6] if len(row) > 6 else 0,
                    'max_analyses': row[18] if len(row) > 18 else 5,
                    'max_users': row[19] if len(row) > 19 else 1,
                    'can_export': row[20] if len(row) > 20 else False,
                    'can_manage_team': row[21] if len(row) > 21 else False,
                    'end_date': row[5]
                }
        except Exception as e:
            print(f"Error: {e}")
        
        return {
            'plan': 'free',
            'plan_name': 'Free',
            'status': 'active',
            'boq_used': 0,
            'max_boq': 5,
            'bid_used': 0,
            'max_bid': 5,
            'analyses_used': 0,
            'max_analyses': 5,
            'max_users': 1,
            'can_export': False,
            'can_manage_team': False
        }
    
    def _render_header(self, sub):
        """Render dashboard header with subscription info"""
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Plan", sub['plan_name'].upper())
        
        with col2:
            days_left = 999
            if sub.get('end_date'):
                try:
                    end_date = datetime.strptime(sub['end_date'], '%Y-%m-%d') if isinstance(sub['end_date'], str) else sub['end_date']
                    days_left = (end_date - datetime.now().date()).days
                except:
                    pass
            st.metric("Days Remaining", max(0, days_left))
        
        with col3:
            boq_remaining = sub['max_boq'] - sub['boq_used'] if sub['max_boq'] != -1 else "∞"
            st.metric("BOQ Remaining", boq_remaining)
        
        with col4:
            bid_remaining = sub['max_bid'] - sub['bid_used'] if sub['max_bid'] != -1 else "∞"
            st.metric("Bid Optimizations", bid_remaining)
        
        # Warning if limits are low
        if sub['max_boq'] != -1:
            boq_percent = (sub['boq_used'] / sub['max_boq']) * 100 if sub['max_boq'] > 0 else 0
            if boq_percent > 80:
                st.warning(f"⚠️ You have used {boq_percent:.0f}% of your BOQ limit. Upgrade to continue.")
        
        st.markdown("---")
    
    def _render_usage_metrics(self, company_id, sub):
        """Render usage metrics with progress bars"""
        
        st.markdown("### 📊 Usage This Month")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if sub['max_boq'] == -1:
                st.progress(0)
                st.caption("BOQ: Unlimited")
            else:
                percent = (sub['boq_used'] / sub['max_boq']) * 100 if sub['max_boq'] > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"BOQ: {sub['boq_used']} / {sub['max_boq']} ({percent:.0f}%)")
        
        with col2:
            if sub['max_bid'] == -1:
                st.progress(0)
                st.caption("Bid Optimizations: Unlimited")
            else:
                percent = (sub['bid_used'] / sub['max_bid']) * 100 if sub['max_bid'] > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"Bid Opt: {sub['bid_used']} / {sub['max_bid']} ({percent:.0f}%)")
        
        with col3:
            if sub['max_analyses'] == -1:
                st.progress(0)
                st.caption("Analyses: Unlimited")
            else:
                percent = (sub['analyses_used'] / sub['max_analyses']) * 100 if sub['max_analyses'] > 0 else 0
                st.progress(min(1.0, percent / 100))
                st.caption(f"Analyses: {sub['analyses_used']} / {sub['max_analyses']} ({percent:.0f}%)")
        
        st.markdown("---")
    
    def _render_tender_management(self, company_id):
        """Manage tenders"""
        
        st.markdown("### 📋 Tender Management")
        
        # Get existing tenders
        tenders = self._get_company_tenders(company_id)
        
        if not tenders.empty:
            st.markdown("#### Your Tenders")
            
            # Format for display
            display_df = tenders[['tender_id', 'tender_title', 'procuring_entity', 'official_estimate', 'bid_status', 'created_at']].copy()
            display_df['official_estimate'] = display_df['official_estimate'].apply(lambda x: f"৳{x:,.2f}" if x else 'N/A')
            display_df['created_at'] = display_df['created_at'].astype(str).str[:10]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # View/Edit selected tender
            selected_tender = st.selectbox(
                "Select tender to work on",
                options=tenders['tender_id'].tolist(),
                format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50]}"
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
        if sub['max_boq'] != -1 and sub['boq_used'] >= sub['max_boq']:
            st.error(f"❌ You have reached your BOQ limit ({sub['max_boq']}). Please upgrade your plan.")
            return
        
        # Get tenders
        tenders = self._get_company_tenders(company_id)
        
        if tenders.empty:
            st.info("No tenders found. Please create a tender first.")
            return
        
        # Select tender
        selected_tender = st.selectbox(
            "Select Tender",
            options=tenders['tender_id'].tolist(),
            format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50]}",
            key="boq_tender_select"
        )
        
        if selected_tender:
            tender_data = tenders[tenders['tender_id'] == selected_tender].iloc[0]
            
            # Select rate source
            rate_source = st.radio("Rate Schedule", ["PWD", "LGED"], horizontal=True)
            
            # Select chapter
            if rate_source == "PWD":
                chapters = self.db.get_pwd_chapters()
                if not chapters.empty:
                    chapter = st.selectbox("Chapter", chapters['chapter_number'].tolist())
                else:
                    st.warning("No PWD rates found. Import rates first.")
                    return
            else:
                chapters = self.db.get_lged_chapters()
                if not chapters.empty:
                    chapter = st.selectbox("Chapter", chapters['chapter_number'].tolist())
                    # Select section (optional)
                    sections = self._get_lged_sections(chapter)
                    section = st.selectbox("Section (Optional)", [""] + sections)
                else:
                    st.warning("No LGED rates found. Import rates first.")
                    return
            
            if st.button("Generate BOQ", type="primary"):
                with st.spinner("Generating BOQ..."):
                    boq_data = self._generate_boq(selected_tender, rate_source, chapter, section if rate_source == "LGED" else None)
                    
                    if boq_data is not None:
                        # Increment usage
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
                        
                        # Save to history
                        self._save_boq_history(company_id, selected_tender, tender_data['tender_title'], 
                                               rate_source, len(boq_data), boq_data['total'].sum() if 'total' in boq_data.columns else 0)
    
    def _render_bid_optimization(self, company_id, sub):
        """Run bid optimization"""
        
        st.markdown("### 🎯 Bid Optimization")
        
        # Check limit
        if sub['max_bid'] != -1 and sub['bid_used'] >= sub['max_bid']:
            st.error(f"❌ You have reached your bid optimization limit ({sub['max_bid']}). Please upgrade your plan.")
            return
        
        # Get tenders
        tenders = self._get_company_tenders(company_id)
        
        if tenders.empty:
            st.info("No tenders found. Please create a tender first.")
            return
        
        # Select tender
        selected_tender = st.selectbox(
            "Select Tender",
            options=tenders['tender_id'].tolist(),
            format_func=lambda x: f"{x} - {tenders[tenders['tender_id']==x]['tender_title'].iloc[0][:50]}",
            key="optimize_tender_select"
        )
        
        if selected_tender:
            tender_data = tenders[tenders['tender_id'] == selected_tender].iloc[0]
            official_estimate = tender_data.get('official_estimate', 0)
            
            st.info(f"**Official Estimate:** ৳{official_estimate:,.2f}")
            
            # Competitor data entry
            st.markdown("#### Competitor Bid Data")
            
            competitors = self._get_competitor_bids(selected_tender)
            
            if not competitors.empty:
                st.dataframe(competitors, use_container_width=True)
            
            # Add competitor
            with st.expander("➕ Add Competitor Bid", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    comp_name = st.text_input("Competitor Name")
                with col2:
                    comp_bid = st.number_input("Bid Amount (BDT)", min_value=0.0, step=100000.0)
                
                if st.button("Add Competitor"):
                    if comp_name and comp_bid > 0:
                        self._add_competitor_bid(selected_tender, comp_name, comp_bid)
                        st.rerun()
            
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
                        
                        # Save analysis
                        self._save_analysis(company_id, selected_tender, tender_data['tender_title'], 
                                           result, official_estimate)
    
    def _render_reports(self, company_id, sub):
        """Generate reports"""
        
        st.markdown("### 📈 Reports")
        
        if not sub.get('can_export', False):
            st.warning("🔒 Export feature is not available in your current plan. Upgrade to Professional or Enterprise to export data.")
            return
        
        report_type = st.selectbox("Select Report Type", [
            "BOQ History",
            "Bid Analysis",
            "Competitor Analysis",
            "Usage Report",
            "Tender Performance"
        ])
        
        date_range = st.selectbox("Date Range", ["Last 30 Days", "Last 3 Months", "Last 6 Months", "All Time"])
        
        if st.button("Generate Report", type="primary"):
            report_data = self._generate_report(company_id, report_type, date_range)
            
            if report_data is not None and not report_data.empty:
                csv = report_data.to_csv(index=False)
                st.download_button(
                    "📥 Download Report (CSV)",
                    csv,
                    f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
                
                # Also show preview
                st.markdown("#### Report Preview")
                st.dataframe(report_data.head(20), use_container_width=True)
    
    def _render_settings(self, company_id):
        """Company settings"""
        
        st.markdown("### ⚙️ Company Settings")
        
        # Get company info
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
                    # Update company
                    self._update_company(company_id, {
                        'company_name': new_name,
                        'email': new_email,
                        'phone': new_phone,
                        'division': new_division
                    })
                    st.success("Settings saved!")
                    st.rerun()
    
    # ========== Helper Methods ==========
    
    def _get_company_tenders(self, company_id):
        """Get tenders for company"""
        try:
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT tender_id, tender_title, procuring_entity, division,
                       official_estimate, bid_status, created_at
                FROM company_tenders
                WHERE company_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, conn, params=[company_id])
            conn.close()
            return df
        except:
            return pd.DataFrame()
    
    def _get_lged_sections(self, chapter_num):
        """Get LGED sections for a chapter"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT section_number FROM lged_sections 
                WHERE chapter_number = ?
                ORDER BY display_order
            """, (chapter_num,))
            sections = [row[0] for row in cursor.fetchall()]
            conn.close()
            return sections
        except:
            return []
    
    def _get_competitor_bids(self, tender_id):
        """Get competitor bids for a tender"""
        try:
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT competitor_name, total_bid_amount, submission_date
                FROM competitor_bids
                WHERE tender_id = ?
                ORDER BY total_bid_amount
            """, conn, params=[tender_id])
            conn.close()
            return df
        except:
            return pd.DataFrame()
    
    def _create_tender(self, company_id, tender_id, title, procuring_entity, division, estimate):
        """Create new tender"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO company_tenders (company_id, tender_id, tender_title, procuring_entity, 
                                            division, official_estimate, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, tender_id, title, procuring_entity, division, estimate, 
                  st.session_state.get('user_id', 0), datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error creating tender: {e}")
    
    def _add_competitor_bid(self, tender_id, competitor_name, bid_amount):
        """Add competitor bid"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO competitor_bids (tender_id, competitor_name, total_bid_amount, submission_date)
                VALUES (?, ?, ?, ?)
            """, (tender_id, competitor_name, bid_amount, datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error adding competitor: {e}")
    
    def _generate_boq(self, tender_id, rate_source, chapter, section=None):
        """Generate BOQ from rates"""
        try:
            conn = self.db.get_connection()
            
            if rate_source == "PWD":
                # Get PWD rates for the chapter
                query = """
                    SELECT c.pwd_code as item_code, c.description, c.unit, 
                           r.zone_name, r.unit_rate
                    FROM pwd_children c
                    JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                    WHERE c.chapter_id = (SELECT id FROM rate_chapters WHERE source = 'PWD' AND chapter_number = ?)
                """
                df = pd.read_sql_query(query, conn, params=[chapter])
            else:
                # Get LGED rates for chapter/section
                if section:
                    query = """
                        SELECT code as item_code, description, unit, 
                               zone_a, zone_b, zone_c, zone_d
                        FROM lged_children 
                        WHERE chapter_number = ? AND section_number = ?
                    """
                    df = pd.read_sql_query(query, conn, params=[chapter, section])
                else:
                    query = """
                        SELECT code as item_code, description, unit, 
                               zone_a, zone_b, zone_c, zone_d
                        FROM lged_children 
                        WHERE chapter_number = ?
                    """
                    df = pd.read_sql_query(query, conn, params=[chapter])
            
            conn.close()
            
            if df.empty:
                st.warning(f"No rates found for {rate_source} Chapter {chapter}")
                return None
            
            # For demo, return sample BOQ
            return df.head(20)
            
        except Exception as e:
            st.error(f"Error generating BOQ: {e}")
            return None
    
    def _run_optimization(self, tender_id, official_estimate):
        """Run bid optimization"""
        # Get competitor bids
        competitors = self._get_competitor_bids(tender_id)
        
        if competitors.empty:
            # Simple recommendation based on estimate
            recommended = official_estimate * 0.95
            win_prob = 70
            profit = recommended * 0.12
            recommendation = f"Based on the official estimate of ৳{official_estimate:,.2f}, we recommend bidding around ৳{recommended:,.2f} (5% below estimate) for competitive positioning."
        else:
            # Smart recommendation based on competitor data
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
    
    def _save_analysis(self, company_id, tender_id, tender_title, result, official_estimate):
        """Save analysis to database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tender_analyses (
                    user_id, company_id, tender_id, tender_title, official_estimate,
                    recommended_bid, success_probability, expected_profit,
                    analysis_date, analysis_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.get('user_id', 0), company_id, tender_id, tender_title,
                official_estimate, result['recommended_bid'], result['win_probability'] / 100,
                result['expected_profit'], datetime.now(), 'bid_optimization'
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving analysis: {e}")
    
    def _save_boq_history(self, company_id, tender_id, tender_title, rate_source, item_count, total_cost):
        """Save BOQ generation history"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO boq_generation_history (
                    company_id, tender_id, tender_title, rate_source, 
                    item_count, total_estimated_cost, generated_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, tender_id, tender_title, rate_source, item_count, total_cost, datetime.now(), 'completed'))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving BOQ history: {e}")
    
    def _increment_usage(self, company_id, resource_type):
        """Increment usage counter"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            field_map = {
                'boq': 'max_boq_generations',
                'bid': 'max_bid_optimizations'
            }
            
            if resource_type in field_map:
                # Update subscriptions table
                cursor.execute(f"""
                    UPDATE subscriptions 
                    SET {resource_type}_used = {resource_type}_used + 1,
                        analyses_used = analyses_used + 1
                    WHERE company_id = ?
                """, (company_id,))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error incrementing usage: {e}")
    
    def _generate_report(self, company_id, report_type, date_range):
        """Generate report data"""
        try:
            conn = self.db.get_connection()
            
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
            
            elif report_type == "Competitor Analysis":
                df = pd.read_sql_query("""
                    SELECT competitor_name, COUNT(*) as appearances,
                           AVG(total_bid_amount) as avg_bid
                    FROM competitor_bids cb
                    JOIN company_tenders ct ON cb.tender_id = ct.tender_id
                    WHERE ct.company_id = ?
                    GROUP BY competitor_name
                    ORDER BY appearances DESC
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
            
            conn.close()
            return df
            
        except Exception as e:
            st.error(f"Error generating report: {e}")
            return pd.DataFrame()
    
    def _update_company(self, company_id, updates):
        """Update company information"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            for key, value in updates.items():
                cursor.execute(f"UPDATE companies SET {key} = ? WHERE id = ?", (value, company_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error updating company: {e}")


# Convenience function
def render_subscriber_dashboard(db):
    dashboard = SubscriberDashboard(db)
    dashboard.render()