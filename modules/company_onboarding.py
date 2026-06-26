# pages/company_onboarding.py - COMPLETE FIXED VERSION

import streamlit as st
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from services.demo_data_generator import DemoDataGenerator
from services.data_reset_service import DataResetService
from services.tenant_rate_service import TenantRateService
from modules.rbac import render_role_badge

logger = logging.getLogger(__name__)


class CompanyOnboarding:
    """Company onboarding wizard UI"""
    
    def __init__(self, db):
        self.db = db
        self.demo_generator = DemoDataGenerator(db)
        self.reset_service = DataResetService(db)
        self.rate_service = TenantRateService()
    
    def render(self):
        """Main onboarding interface"""
        
        st.title("🏢 Company Onboarding Wizard")
        render_role_badge()
        
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        
        if not company_id:
            st.warning("⚠️ No company found. Please contact support.")
            return
        
        # Check onboarding status
        status = self._get_onboarding_status(company_id)
        
        if status.get('onboarding_completed'):
            st.success("✅ Onboarding completed! You're ready to go.")
            if st.button("Go to Dashboard"):
                st.session_state.page = "dashboard"
                st.rerun()
            return
        
        # Determine current step
        current_step = status.get('onboarding_step', 1)
        
        # Show progress
        self._render_progress(current_step)
        
        # Render appropriate step
        if current_step == 1:
            self._render_step_1_data_source(company_id, user_id)
        elif current_step == 2:
            self._render_step_2_cost_profiles(company_id, user_id)
        elif current_step == 3:
            self._render_step_3_generate_demo(company_id, user_id)
        elif current_step == 4:
            self._render_step_4_activate(company_id, user_id)
    
    def _get_onboarding_status(self, company_id: int) -> Dict:
        """Get onboarding status from database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM company_onboarding_status WHERE company_id = ?
            """, (company_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Convert to dict and ensure all fields exist
                status = dict(result)
                
                # Parse step_data if present
                if status.get('step_data'):
                    try:
                        step_data = json.loads(status['step_data'])
                        # Merge step_data into status for easier access
                        for key, value in step_data.items():
                            if key not in status or status[key] is None:
                                status[key] = value
                    except:
                        pass
                
                return status
            else:
                # Create initial status if not exists
                self._create_onboarding_status(company_id)
                return {'onboarding_step': 1, 'onboarding_completed': 0, 'demo_generated': 0}
                
        except Exception as e:
            logger.error(f"Error getting onboarding status: {e}")
            return {'onboarding_step': 1, 'onboarding_completed': 0, 'demo_generated': 0}

    
    def _create_onboarding_status(self, company_id: int):
        """Create initial onboarding status"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO company_onboarding_status 
                (company_id, onboarding_step, last_step_updated_at)
                VALUES (?, 1, CURRENT_TIMESTAMP)
            """, (company_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creating onboarding status: {e}")
    
    def _render_progress(self, current_step: int):
        """Render progress bar"""
        
        steps = [
            "Choose Data Source",
            "Configure Cost Profiles",
            "Generate Demo Data",
            "Activate Workspace"
        ]
        
        cols = st.columns(len(steps))
        
        for i, (col, step) in enumerate(zip(cols, steps)):
            step_num = i + 1
            with col:
                if step_num < current_step:
                    st.markdown(f"✅ **Step {step_num}**\n\n{step}")
                elif step_num == current_step:
                    st.markdown(f"🔄 **Step {step_num}**\n\n{step}")
                else:
                    st.markdown(f"⬜ **Step {step_num}**\n\n{step}")
        
        st.progress((current_step - 1) / len(steps))
        st.divider()
    
    def _render_step_1_data_source(self, company_id: int, user_id: int):
        """Step 1: Choose data source"""
        
        st.subheader("Step 1: Choose Your Data Source")
        st.markdown("How would you like to start with your rate books?")
        
        with st.form("step1_form"):
            data_source = st.radio(
                "Select an option:",
                options=[
                    ("Start with Demo Data", "DEMO"),
                    ("Clone Master Rates", "CLONE"),
                    ("Import Real Data", "IMPORT")
                ],
                format_func=lambda x: x[0],
                index=0
            )
            
            data_source_value = data_source[1]
            
            # Show description based on selection
            if data_source_value == "DEMO":
                st.info("📊 We'll generate realistic demo data with 500+ items so you can explore all features immediately.")
            elif data_source_value == "CLONE":
                st.info("📋 We'll copy the latest PWD and LGED master rates to your company.")
            else:
                st.info("📥 You'll be guided through importing your existing rate data.")
            
            submitted = st.form_submit_button("Continue →", use_container_width=True)
            
            if submitted:
                try:
                    # First, check if step_data column exists
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    
                    # Try to update with step_data if column exists
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO company_onboarding_status 
                            (company_id, onboarding_step, step_data, last_step_updated_at)
                            VALUES (?, 2, ?, CURRENT_TIMESTAMP)
                        """, (company_id, json.dumps({'data_source': data_source_value})))
                    except Exception as e:
                        # If step_data column doesn't exist, update without it
                        logger.warning(f"step_data column not found, using fallback: {e}")
                        cursor.execute("""
                            INSERT OR REPLACE INTO company_onboarding_status 
                            (company_id, onboarding_step, last_step_updated_at)
                            VALUES (?, 2, CURRENT_TIMESTAMP)
                        """, (company_id,))
                        
                        # Store data source in a separate table or use the step_data column after migration
                    
                    conn.commit()
                    conn.close()
                    
                    # Also update companies table
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE companies 
                        SET onboarding_status = 'in_progress'
                        WHERE id = ?
                    """, (company_id,))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Selected: {data_source_value}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error saving selection: {e}")
                    logger.error(f"Onboarding step 1 error: {e}")

    
    def _render_step_2_cost_profiles(self, company_id: int, user_id: int):
        """Step 2: Configure cost profiles"""
        
        st.subheader("Step 2: Configure Cost Profiles")
        st.markdown("Set your default discount percentages for each pricing level.")
        
        # Get current config or use defaults
        config = self._get_cost_profile_config(company_id)
        
        with st.form("step2_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                economy_discount = st.number_input(
                    "Economy Discount %",
                    min_value=0.0,
                    max_value=50.0,
                    value=float(config.get('economy_discount', 22.0)),
                    step=1.0,
                    help="Aggressive pricing discount from base rate"
                )
            
            with col2:
                market_discount = st.number_input(
                    "Market Discount %",
                    min_value=0.0,
                    max_value=50.0,
                    value=float(config.get('market_discount', 18.0)),
                    step=1.0,
                    help="Competitive pricing discount from base rate"
                )
            
            with col3:
                premium_discount = st.number_input(
                    "Premium Discount %",
                    min_value=0.0,
                    max_value=50.0,
                    value=float(config.get('premium_discount', 14.0)),
                    step=1.0,
                    help="Standard pricing discount from base rate"
                )
            
            st.info("💡 These percentages will be applied to base rates to calculate each pricing level.")
            
            # Use a unique key for the submit button
            submitted = st.form_submit_button("Continue →", use_container_width=True, type="primary")
            
            if submitted:
                try:
                    # Save cost profile
                    self._save_cost_profile(company_id, user_id, {
                        'economy_discount': economy_discount,
                        'market_discount': market_discount,
                        'premium_discount': premium_discount
                    })
                    
                    # Update onboarding step to 3
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    
                    # Get existing step_data
                    cursor.execute("""
                        SELECT step_data FROM company_onboarding_status WHERE company_id = ?
                    """, (company_id,))
                    
                    result = cursor.fetchone()
                    step_data = {}
                    if result and result['step_data']:
                        try:
                            step_data = json.loads(result['step_data'])
                        except:
                            step_data = {}
                    
                    # Update step_data with cost profile info
                    step_data['cost_profile_saved'] = True
                    step_data['economy_discount'] = economy_discount
                    step_data['market_discount'] = market_discount
                    step_data['premium_discount'] = premium_discount
                    
                    # Update to step 3
                    cursor.execute("""
                        UPDATE company_onboarding_status 
                        SET onboarding_step = 3, 
                            step_data = ?,
                            last_step_updated_at = CURRENT_TIMESTAMP
                        WHERE company_id = ?
                    """, (json.dumps(step_data), company_id))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ Cost profile saved! Moving to next step...")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error saving cost profile: {e}")
                    logger.error(f"Step 2 error: {e}")

    
    def _render_step_3_generate_demo(self, company_id: int, user_id: int):
        """Step 3: Generate demo data"""
        
        st.subheader("Step 3: Generate Demo Data")
        st.markdown("We'll now generate realistic demo data for your company.")
        
        # Get onboarding data
        onboarding_data = self._get_onboarding_data(company_id)
        data_source = onboarding_data.get('data_source', 'DEMO')
        
        if data_source == 'DEMO':
            # ✅ Check what demo data exists
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check demo books
            cursor.execute("""
                SELECT source_type, COUNT(*) as count 
                FROM tenant_rate_books 
                WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
                GROUP BY source_type
            """, (company_id,))
            
            books = cursor.fetchall()
            book_summary = {}
            for row in books:
                book_summary[row['source_type']] = row['count']
            
            # Check items count
            cursor.execute("""
                SELECT COUNT(*) as count FROM tenant_rate_items ri
                JOIN tenant_rate_books rb ON ri.rate_book_id = rb.id
                WHERE rb.tenant_id = ? AND ri.is_demo = 1 AND ri.is_archived = 0
            """, (company_id,))
            
            result = cursor.fetchone()
            existing_items = result['count'] if result else 0
            conn.close()
            
            # ✅ Show status of each book type
            st.markdown("#### Current Demo Data Status:")
            col1, col2, col3 = st.columns(3)
            with col1:
                pwd_exists = 'PWD' in book_summary and book_summary['PWD'] > 0
                st.metric("PWD Rates", "✅" if pwd_exists else "❌")
            with col2:
                lged_exists = 'LGED' in book_summary and book_summary['LGED'] > 0
                st.metric("LGED Rates", "✅" if lged_exists else "❌")
            with col3:
                custom_exists = 'CUSTOM' in book_summary and book_summary['CUSTOM'] > 0
                st.metric("Custom Rates", "✅" if custom_exists else "❌")
            
            st.caption(f"Total Items: {existing_items}")
            st.divider()
            
            # ✅ If all books exist with items, show skip option
            if pwd_exists and lged_exists and custom_exists and existing_items > 0:
                st.success(f"✅ All demo data exists with {existing_items} items!")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Skip to Next Step →", use_container_width=True):
                        self._update_onboarding_step(company_id, 4, {'demo_generated': True})
                        st.rerun()
                with col2:
                    if st.button("🔄 Force Regenerate", use_container_width=True, type="secondary"):
                        with st.spinner("Cleaning up and regenerating demo data..."):
                            self._force_regenerate_demo(company_id, user_id)
                        st.rerun()
                return
            
            # If some books exist but are empty, show regenerate
            if (pwd_exists or lged_exists or custom_exists) and existing_items == 0:
                st.warning("⚠️ Found empty demo books. Please regenerate.")
                if st.button("🔄 Regenerate Demo Data", use_container_width=True, type="primary"):
                    with st.spinner("Regenerating demo data..."):
                        self._force_regenerate_demo(company_id, user_id)
                    st.rerun()
                return
            
            # Show generation options
            st.info("📊 Generating missing demo data...")
            
            # Show what will be generated
            with st.expander("📋 What will be generated", expanded=True):
                items_to_generate = []
                if not pwd_exists:
                    items_to_generate.append("- **PWD Demo Rates**: 30+ items across 5 chapters")
                if not lged_exists:
                    items_to_generate.append("- **LGED Demo Rates**: 30+ items across 5 chapters")
                if not custom_exists:
                    items_to_generate.append("- **Custom Demo Rates**: 30+ custom items")
                items_to_generate.append("- **3 Pricing Levels**: Economy, Market, Premium")
                for item in items_to_generate:
                    st.markdown(item)
            
            if st.button("🚀 Generate Missing Demo Data", use_container_width=True, type="primary"):
                with st.spinner("Generating demo data... This may take a moment."):
                    # Only generate missing books
                    result = self._generate_missing_demo_data(company_id, user_id, pwd_exists, lged_exists, custom_exists)
                    
                    if result.get('success'):
                        st.success(f"✅ Generated {result['total_items']} demo items!")
                        
                        # Update onboarding step to 4
                        self._update_onboarding_step(company_id, 4, {
                            'demo_generated': True,
                            'demo_items': result['total_items']
                        })
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to generate demo data: {result.get('error', 'Unknown error')}")
            
            with col2:
                # Show current status
                status = self._get_onboarding_status(company_id)
                if status.get('demo_generated'):
                    st.success("✅ Demo data already generated!")
                    if st.button("Skip to Next Step →", use_container_width=True):
                        self._update_onboarding_step(company_id, 4, {'demo_generated': True})
                        st.rerun()
        
        elif data_source == 'CLONE':
            st.info("📋 Cloning master PWD and LGED rates...")
            
            # Check if cloning already done
            status = self._get_onboarding_status(company_id)
            if status.get('cloning_completed'):
                st.success("✅ Master rates cloned successfully!")
                if st.button("Skip to Next Step →", use_container_width=True):
                    self._update_onboarding_step(company_id, 4, {'cloning_completed': True})
                    st.rerun()
                return
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Clone PWD Rates", use_container_width=True):
                    self._clone_master_rates(company_id, user_id, 'PWD')
            
            with col2:
                if st.button("📋 Clone LGED Rates", use_container_width=True):
                    self._clone_master_rates(company_id, user_id, 'LGED')
            
            if st.button("Skip to Next Step →", use_container_width=True):
                self._update_onboarding_step(company_id, 4, {'cloning_completed': True})
                st.rerun()
        
        else:  # IMPORT
            st.info("📥 You've chosen to import real data.")
            st.markdown("""
            You can import your real data using the Data Management page.
            
            **Next steps:**
            1. Go to Data Management
            2. Click "Import Real Data"  
            3. Upload your Excel/CSV files
            4. Validate and import
            5. Switch to Production mode
            """)
            
            if st.button("Go to Rate Management", use_container_width=True, type="primary"):
                st.session_state.page = "company_rate_management"
                st.rerun()
            
            if st.button("Skip to Dashboard", use_container_width=True):
                self._update_onboarding_step(company_id, 4, {'import_selected': True})
                st.rerun()

    
    def _render_step_4_activate(self, company_id: int, user_id: int):
        """Step 4: Activate workspace"""
        
        st.subheader("Step 4: Activate Workspace")
        st.markdown("You're almost ready! Review your setup and activate your workspace.")
        
        # Get current status and data
        status = self._get_onboarding_status(company_id)
        onboarding_data = self._get_onboarding_data(company_id)
        
        # ✅ FIX: Get data source from multiple sources with better fallback
        data_source = None
        
        # Try step_data first
        if onboarding_data and isinstance(onboarding_data, dict):
            data_source = onboarding_data.get('data_source')
        
        # If not found, try status
        if not data_source and status and isinstance(status, dict):
            # Check if status has data_source directly
            data_source = status.get('data_source')
            # Or check if step_data is in status and parse it
            if not data_source and status.get('step_data'):
                try:
                    step_data = json.loads(status['step_data'])
                    data_source = step_data.get('data_source')
                except:
                    pass
        
        # If still not found, check if demo data exists (infer from data)
        if not data_source:
            # Check if demo data exists
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM tenant_rate_books 
                WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
            """, (company_id,))
            result = cursor.fetchone()
            demo_count = result['count'] if result else 0
            conn.close()
            
            if demo_count > 0:
                # We have demo data, so data source must be DEMO
                data_source = 'DEMO'
                # Save it for future
                self._update_onboarding_step(company_id, 4, {
                    'data_source': 'DEMO',
                    'demo_generated': True,
                    'demo_items': demo_count
                })
            else:
                data_source = 'DEMO'  # Default fallback
        
        # Get demo generated status
        demo_generated = (
            onboarding_data.get('demo_generated') or 
            status.get('demo_generated') or 
            False
        )
        
        # If demo data exists but flag is false, update it
        if not demo_generated:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM tenant_rate_items 
                WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
            """, (company_id,))
            result = cursor.fetchone()
            item_count = result['count'] if result else 0
            conn.close()
            
            if item_count > 0:
                demo_generated = True
                # Update the flag
                self._update_onboarding_step(company_id, 4, {
                    'data_source': data_source,
                    'demo_generated': True,
                    'demo_items': item_count
                })
        
        st.markdown("#### 📋 Setup Summary")
        
        # Check each step
        steps_completed = []
        
        # Step 1: Data Source
        if data_source:
            steps_completed.append(f"✅ Data Source: {data_source}")
        else:
            steps_completed.append("⚠️ Data Source: Not configured")
            if st.button("Go Back to Step 1", use_container_width=True):
                self._update_onboarding_step(company_id, 1, {})
                st.rerun()
            return
        
        # Step 2: Cost Profile
        cost_profile = self._get_cost_profile_config(company_id)
        if cost_profile and cost_profile.get('economy_discount'):
            steps_completed.append(f"✅ Cost Profile: Economy {cost_profile.get('economy_discount', 22)}%, Market {cost_profile.get('market_discount', 18)}%, Premium {cost_profile.get('premium_discount', 14)}%")
        else:
            steps_completed.append("⚠️ Cost Profile: Not configured")
            if st.button("Go Back to Step 2", use_container_width=True):
                self._update_onboarding_step(company_id, 2, {'data_source': data_source})
                st.rerun()
            return
        
        # Step 3: Demo Data
        if data_source == 'DEMO':
            if demo_generated:
                items_count = onboarding_data.get('demo_items', status.get('demo_items', 0))
                if items_count == 0:
                    # Count items from database
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM tenant_rate_items 
                        WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
                    """, (company_id,))
                    result = cursor.fetchone()
                    items_count = result['count'] if result else 0
                    conn.close()
                steps_completed.append(f"✅ Demo Data: Generated {items_count} items")
            else:
                steps_completed.append("⚠️ Demo Data: Not yet generated")
                if st.button("Go Back to Step 3", use_container_width=True):
                    self._update_onboarding_step(company_id, 3, {'data_source': data_source})
                    st.rerun()
                return
        elif data_source == 'CLONE':
            if onboarding_data.get('cloning_completed') or status.get('cloning_completed'):
                steps_completed.append("✅ Master Rates: Cloned successfully")
            else:
                steps_completed.append("⚠️ Master Rates: Not yet cloned")
                if st.button("Go Back to Step 3", use_container_width=True):
                    self._update_onboarding_step(company_id, 3, {'data_source': data_source})
                    st.rerun()
                return
        else:
            steps_completed.append("📥 Import: Ready for data import")
        
        # Display summary
        for step in steps_completed:
            if step.startswith("✅"):
                st.success(step)
            elif step.startswith("⚠️"):
                st.warning(step)
            else:
                st.info(step)
        
        st.divider()
        
        # Check if all required steps are complete
        all_complete = all(s.startswith("✅") or s.startswith("📥") for s in steps_completed)
        
        if not all_complete:
            st.warning("⚠️ Please complete all steps before activating your workspace.")
            return
        
        # Activation button
        st.markdown("#### 🚀 Ready to Activate")
        st.markdown("Your workspace is ready! Click below to activate and start using TenderAI.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Activate Workspace", use_container_width=True, type="primary"):
                try:
                    # Complete onboarding
                    self._complete_onboarding(company_id, user_id)
                    
                    # Log activation
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO archive_metadata 
                        (archive_batch_id, company_id, operation_type, description, 
                        total_records_archived, status, initiated_by, completed_at)
                        VALUES (?, ?, 'ACTIVATION', 'Company workspace activated', 
                                0, 'completed', ?, CURRENT_TIMESTAMP)
                    """, (f"ACTIVATE_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                        company_id, user_id))
                    conn.commit()
                    conn.close()
                    
                    # Show success
                    st.success("🎉 **Onboarding completed!**")
                    st.balloons()
                    st.markdown("""
                    ### 🎊 Welcome to TenderAI!
                    
                    You can now:
                    - 📊 View your rate books
                    - 📋 Create BOQs
                    - 🎯 Run bid optimization
                    - 🔮 Analyze competitors
                    - 📈 Track performance
                    
                    **Get started by going to your Dashboard!**
                    """)
                    
                    if st.button("🚀 Go to Dashboard", use_container_width=True, type="primary"):
                        st.session_state.page = "dashboard"
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error activating workspace: {e}")
                    logger.error(f"Activation error: {e}")



    
    def _update_onboarding_step(self, company_id: int, step: int, data: Dict = None):
        """Update onboarding step"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if data:
                cursor.execute("""
                    UPDATE company_onboarding_status 
                    SET onboarding_step = ?, step_data = ?, last_step_updated_at = CURRENT_TIMESTAMP
                    WHERE company_id = ?
                """, (step, json.dumps(data), company_id))
            else:
                cursor.execute("""
                    UPDATE company_onboarding_status 
                    SET onboarding_step = ?, last_step_updated_at = CURRENT_TIMESTAMP
                    WHERE company_id = ?
                """, (step, company_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating onboarding step: {e}")
    
    def _get_onboarding_data(self, company_id: int) -> Dict:
        """Get onboarding data"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if step_data column exists
            cursor.execute("PRAGMA table_info(company_onboarding_status)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'step_data' in columns:
                cursor.execute("""
                    SELECT step_data FROM company_onboarding_status WHERE company_id = ?
                """, (company_id,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result['step_data']:
                    return json.loads(result['step_data'])
            else:
                conn.close()
                logger.warning("step_data column not found in company_onboarding_status")
            
            return {}
                
        except Exception as e:
            logger.error(f"Error getting onboarding data: {e}")
            return {}

    
    def _get_cost_profile_config(self, company_id: int) -> Dict:
        """Get cost profile configuration"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_cost_profiles'")
            if not cursor.fetchone():
                return {
                    'economy_discount': 22.0,
                    'market_discount': 18.0,
                    'premium_discount': 14.0
                }
            
            cursor.execute("""
                SELECT * FROM company_cost_profiles WHERE company_id = ? AND is_active = 1
            """, (company_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            
            return {
                'economy_discount': 22.0,
                'market_discount': 18.0,
                'premium_discount': 14.0
            }
            
        except Exception as e:
            logger.error(f"Error getting cost profile: {e}")
            return {
                'economy_discount': 22.0,
                'market_discount': 18.0,
                'premium_discount': 14.0
            }
    
    def _save_cost_profile(self, company_id: int, user_id: int, config: Dict):
        """Save cost profile configuration"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_cost_profiles'")
            if not cursor.fetchone():
                # Table doesn't exist, create it
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_cost_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL UNIQUE,
                        profile_name TEXT DEFAULT 'Default',
                        economy_discount REAL DEFAULT 22.0,
                        market_discount REAL DEFAULT 18.0,
                        premium_discount REAL DEFAULT 14.0,
                        markup_percentage REAL DEFAULT 15.0,
                        overhead_percentage REAL DEFAULT 10.0,
                        profit_margin_percentage REAL DEFAULT 15.0,
                        is_active BOOLEAN DEFAULT 1,
                        is_default BOOLEAN DEFAULT 0,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                    )
                """)
                logger.info("Created company_cost_profiles table")
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO company_cost_profiles 
                (company_id, economy_discount, market_discount, premium_discount, 
                is_active, is_default, created_by, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, ?, CURRENT_TIMESTAMP)
            """, (company_id, config['economy_discount'], config['market_discount'], 
                config['premium_discount'], user_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Cost profile saved for company {company_id}")
            
        except Exception as e:
            logger.error(f"Error saving cost profile: {e}")
            raise
    
    def _clone_master_rates(self, company_id: int, user_id: int, source_type: str):
        """Clone master rates to company"""
        try:
            # Get active master version
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC LIMIT 1
            """, (source_type,))
            
            version = cursor.fetchone()
            conn.close()
            
            if not version:
                st.error(f"No active {source_type} master version found.")
                return
            
            version_id = version['id']
            
            # Create rate book
            book_name = f"Demo {source_type} Rates"
            result = self.rate_service.create_rate_book(
                tenant_id=company_id,
                tenant_type='company',
                name=book_name,
                source_type=source_type,
                description=f"Cloned {source_type} master rates",
                source_version_id=version_id,
                created_by=user_id
            )
            
            if result.get('success'):
                # Clone master rates
                clone_result = self.rate_service.clone_master_rates(
                    book_id=result['book_id'],
                    source_type=source_type,
                    version_id=result['version_id'],
                    user_id=user_id
                )
                
                if clone_result.get('success'):
                    st.success(f"✅ Cloned {clone_result['items_created']} {source_type} items!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to clone: {clone_result.get('error')}")
            else:
                st.error(f"❌ Failed to create rate book: {result.get('error')}")
                
        except Exception as e:
            st.error(f"Error cloning master rates: {e}")
            logger.error(f"Clone error: {e}")
    
    def _complete_onboarding(self, company_id: int, user_id: int):
        """Mark onboarding as complete"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Update company_onboarding_status
            cursor.execute("""
                UPDATE company_onboarding_status 
                SET onboarding_completed = 1, 
                    onboarding_completed_at = CURRENT_TIMESTAMP,
                    last_step_updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
            """, (company_id,))
            
            # Update companies table
            cursor.execute("""
                UPDATE companies 
                SET onboarding_status = 'completed'
                WHERE id = ?
            """, (company_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Onboarding completed for company {company_id}")
            
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            raise

    def _generate_missing_demo_data(self, company_id: int, user_id: int, pwd_exists: bool, lged_exists: bool, custom_exists: bool) -> Dict[str, Any]:
        """Generate only missing demo data"""
        
        results = {
            'pwd': None,
            'lged': None,
            'custom': None,
            'total_items': 0
        }
        
        # Generate PWD demo if missing
        if not pwd_exists:
            pwd_result = self.demo_generator.generate_pwd_demo_book(company_id, user_id)
            results['pwd'] = pwd_result
            results['total_items'] += pwd_result.get('items_created', 0)
        
        # Generate LGED demo if missing
        if not lged_exists:
            lged_result = self.demo_generator.generate_lged_demo_book(company_id, user_id)
            results['lged'] = lged_result
            results['total_items'] += lged_result.get('items_created', 0)
        
        # Generate custom demo if missing
        if not custom_exists:
            custom_result = self.demo_generator.generate_custom_demo_book(company_id, user_id)
            results['custom'] = custom_result
            results['total_items'] += custom_result.get('items_created', 0)
        
        return {
            'success': True,
            'results': results,
            'total_items': results['total_items']
        }
        

def render_company_onboarding(db):
    """Convenience function"""
    onboarding = CompanyOnboarding(db)
    onboarding.render()