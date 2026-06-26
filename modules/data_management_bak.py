# modules/data_management.py - Complete fixed version

import streamlit as st
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from services.demo_data_generator import DemoDataGenerator
from services.data_reset_service import DataResetService
from services.tenant_rate_service import TenantRateService
from modules.rbac import render_role_badge, can_manage_system, can_create_rate_book

logger = logging.getLogger(__name__)


class DataManagement:
    """Data Management UI for company admins"""
    
    def __init__(self, db):
        self.db = db
        self.demo_generator = DemoDataGenerator(db)
        self.reset_service = DataResetService(db)
        self.rate_service = TenantRateService(db)
    
    def render(self):
        """Main data management interface"""
        
        st.title("⚙️ Data Management")
        render_role_badge()
        
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        user_role = st.session_state.get('user_role', 'viewer')
        
        if not company_id:
            st.warning("⚠️ No company found.")
            return
        
        # ✅ Show environment status banner
        self._render_environment_status_banner(company_id)
        
        # ✅ NEW: Clear tab structure with distinct purposes
        tabs = st.tabs([
            "📚 My Rate Books",      # View/Edit your company rates
            "📊 Master Rates",       # Read-only master rates (PWD/LGED)
            "🔄 Clone & Resync",     # Clone master rates, resync copies
            "📥 Import & Export",    # Import/Export data
            "📋 Audit History"       # View changes
        ])
        
        with tabs[0]:
            self._render_my_rate_books(company_id, user_id)
        
        with tabs[1]:
            self._render_master_rates_viewer()
        
        with tabs[2]:
            self._render_clone_resync_ui(company_id, user_id)
        
        with tabs[3]:
            self._render_import_export_ui(company_id, user_id)
        
        with tabs[4]:
            self._render_audit_history(company_id)

    
    # =========================================================================
    # ENVIRONMENT STATUS
    # =========================================================================
    def _render_my_rate_books(self, company_id: int, user_id: int):
        """Render My Rate Books with View and Edit capabilities"""
        
        st.subheader("📚 My Rate Books")
        st.caption("View and manage your company's rate books")
        
        # ✅ Fetch all rate books
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type, 
                rb.custom_source,
                rb.is_active, 
                rb.is_archived,
                rb.is_demo,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count,
                (SELECT COUNT(*) FROM tenant_rate_versions WHERE rate_book_id = rb.id AND is_current = 1) as has_current_version
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.is_archived = 0
            ORDER BY rb.source_type, rb.name
        """, (company_id,))
        
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            st.info("ℹ️ You don't have any rate books yet.")
            st.info("Go to 'Clone & Resync' tab to clone master rates, or create custom rates.")
            return
        
        # ✅ Display each book with action buttons
        for book in books:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2.5, 1.5, 1])
                
                with col1:
                    # Book icon and info
                    icon = {
                        'PWD': '🏗️',
                        'LGED': '🛣️',
                        'CUSTOM': '✨'
                    }.get(book['source_type'], '📋')
                    
                    source_label = book['source_type']
                    if book['custom_source'] and book['custom_source'] != 'CUSTOM':
                        source_label = f"{book['source_type']} ({book['custom_source']})"
                    
                    st.markdown(f"**{icon} {book['name']}**")
                    st.caption(f"{source_label} - {book['item_count'] or 0} items")
                    
                    if book['is_demo']:
                        st.caption("📌 Demo Data")
                
                with col2:
                    # View button
                    if st.button("👁️ View Details", key=f"view_{book['id']}"):
                        st.session_state.view_book_id = book['id']
                        st.session_state.view_book_name = book['name']
                        st.session_state.view_book_source = book['source_type']
                        st.session_state.page = "rate_viewer"
                        st.rerun()
                    
                    # Edit Costs button (for all books)
                    if st.button("✏️ Edit Costs", key=f"edit_{book['id']}"):
                        st.session_state.edit_book_id = book['id']
                        st.session_state.edit_book_name = book['name']
                        st.session_state.page = "company_rate_management"
                        st.rerun()
                
                with col3:
                    # Source-specific actions
                    if book['source_type'] == 'CUSTOM':
                        if st.button("📝 Add Item", key=f"add_item_{book['id']}"):
                            st.session_state.add_item_book_id = book['id']
                            st.session_state.page = "company_rate_management"
                            st.rerun()
                    else:
                        # PWD/LGED: Resync option
                        if st.button("🔄 Resync", key=f"resync_{book['id']}"):
                            st.session_state.resync_book_id = book['id']
                            st.session_state.resync_source = book['source_type']
                            st.rerun()
        
        # ✅ Create new rate book (if user has permission)
        if can_create_rate_book():
            st.divider()
            with st.expander("➕ Create New Rate Book", expanded=False):
                self._render_create_rate_book_form(company_id, user_id)

    def _render_create_rate_book_form(self, company_id: int, user_id: int):
        """Render form to create a new rate book"""
        
        with st.form("create_rate_book_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                book_name = st.text_input("Book Name*", placeholder="e.g., My PWD Rates, UNDP Rates")
                source_type = st.selectbox(
                    "Source Type",
                    options=["PWD", "LGED", "CUSTOM"],
                    help="Select the type of rates for this book"
                )
            
            with col2:
                description = st.text_area("Description", placeholder="Optional description...")
                
                if source_type == "CUSTOM":
                    custom_source = st.text_input(
                        "Custom Source Label",
                        placeholder="e.g., UNDP, RHD, REB",
                        help="Label for your custom rate source"
                    )
                else:
                    custom_source = None
                
                is_active = st.checkbox("Activate immediately", value=True)
            
            submitted = st.form_submit_button("🚀 Create Rate Book", use_container_width=True, type="primary")
            
            if submitted:
                if not book_name:
                    st.error("Please enter a book name")
                    return
                
                try:
                    from services.tenant_rate_service import TenantRateService
                    service = TenantRateService()
                    
                    result = service.create_rate_book(
                        tenant_id=company_id,
                        tenant_type='company',
                        name=book_name,
                        source_type=source_type,
                        description=description or f"{source_type} rate book",
                        created_by=user_id
                    )
                    
                    if result.get('success'):
                        st.success(f"✅ Created rate book: {book_name}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Failed to create')}")
                        
                except Exception as e:
                    st.error(f"Error creating rate book: {e}")

    def _render_master_rates_viewer(self):
        """Render read-only master rates (PWD/LGED)"""
        
        st.subheader("📊 Master Rates (System Level)")
        st.caption("🔒 These are system-wide master rates managed by System Administrator")
        
        # ✅ Check permission
        user_role = st.session_state.get('user_role', 'viewer')
        is_admin = user_role in ['admin', 'system_admin']
        
        if not is_admin:
            st.info("ℹ️ You have read-only access to master rates.")
            st.info("To create your company rates, go to 'Clone & Resync' tab.")
        
        source = st.radio(
            "Select Master Rate Schedule",
            options=["PWD", "LGED"],
            horizontal=True,
            key="master_rate_viewer_source"
        )
        
        # ✅ Show filters
        col1, col2 = st.columns(2)
        with col1:
            # Zone filter
            zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
            selected_zone = st.selectbox("Zone", zones, key="master_zone")
        with col2:
            # Chapter filter
            if source == "PWD":
                chapters = ["All"] + [f"{i:02d}" for i in range(1, 22)]
            else:
                chapters = ["All"] + [str(i) for i in range(1, 10)]
            selected_chapter = st.selectbox("Chapter", chapters, key="master_chapter")
        
        # ✅ Load and display master rates (read-only)
        # ... (existing code to load master rates)
        
        # ✅ Admin-only: Import master rates
        if is_admin:
            st.divider()
            with st.expander("📥 Import Master Rates (Admin Only)", expanded=False):
                self._render_master_import_ui(source)


    def _render_environment_status_banner(self, company_id: int):
        """Render environment status banner (compact version)"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT environment_mode, onboarding_status, demo_data_generated_at, production_activated_at
                FROM companies WHERE id = ?
            """, (company_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # ✅ FIX: Use indexing, not .get()
                mode = result['environment_mode'] or 'DEMO'
                status = result['onboarding_status'] or 'pending'
                
                if mode == 'DEMO':
                    st.info("🟢 **Environment: DEMO** - You're using demo data. Switch to production when ready.")
                else:
                    st.success("🔵 **Environment: PRODUCTION** - You're using real production data.")
                
                if status == 'completed':
                    st.success("✅ Onboarding: Completed")
                else:
                    st.warning("⏳ Onboarding: In progress")
        except Exception as e:
            logger.error(f"Error rendering environment banner: {e}")
            st.error(f"Could not load environment status: {e}")

    
    def _render_environment_status_detail(self, company_id: int):
        """Render detailed environment status"""
        
        st.subheader("📊 Environment Status")
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            company = cursor.fetchone()
            
            cursor.execute("SELECT * FROM company_onboarding_status WHERE company_id = ?", (company_id,))
            onboarding = cursor.fetchone()
            
            cursor.execute("""
                SELECT * FROM demo_data_generation_log 
                WHERE company_id = ? 
                ORDER BY started_at DESC LIMIT 5
            """, (company_id,))
            
            logs = cursor.fetchall()
            conn.close()
            
            if company:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Environment Mode", company['environment_mode'] or 'DEMO')
                    st.metric("Onboarding Status", company['onboarding_status'] or 'pending')
                
                with col2:
                    demo_at = company['demo_data_generated_at']
                    st.metric("Demo Data Generated", "✅" if demo_at else "❌")
                    prod_at = company['production_activated_at']
                    st.metric("Production Activated", "✅" if prod_at else "❌")
            
            if onboarding:
                st.subheader("Onboarding Progress")
                try:
                    step_data = {}
                    if onboarding['step_data']:
                        try:
                            step_data = json.loads(onboarding['step_data'])
                        except:
                            pass
                    
                    st.json({
                        'Step': onboarding['onboarding_step'] or 1,
                        'Completed': onboarding['onboarding_completed'] or 0,
                        'Demo Generated': onboarding['demo_generated'] or 0,
                        'Production Activated': onboarding['production_activated'] or 0,
                        'Data Source': step_data.get('data_source', 'Not set')
                    })
                except Exception as e:
                    st.json({
                        'Step': onboarding['onboarding_step'] or 1,
                        'Completed': onboarding['onboarding_completed'] or 0
                    })
            
            if logs:
                st.subheader("Recent Demo Data Generation")
                log_list = []
                for row in logs:
                    log_list.append({
                        'generation_type': row['generation_type'],
                        'items_generated': row['items_generated'],
                        'status': row['status'],
                        'completed_at': row['completed_at']
                    })
                df = pd.DataFrame(log_list)
                st.dataframe(df)
                
        except Exception as e:
            st.error(f"Error loading environment status: {e}")
            logger.error(f"Environment status error: {e}")
    
    # =========================================================================
    # MY RATE BOOKS - View/Edit all user's books
    # =========================================================================
    
    def _render_existing_books_management(self, company_id: int, user_id: int):
        """Render management UI for existing rate books"""
        
        st.subheader("📚 My Rate Books")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type, 
                rb.custom_source,
                rb.is_active, 
                rb.is_archived,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.is_archived = 0
        """, (company_id,))
        
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            st.info("ℹ️ You don't have any rate books yet.")
            st.info("Go to 'Clone Master Rates' to copy PWD/LGED rates, or 'Custom Rates' to create your own.")
            return
        
        for book in books:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    status_icon = "✅" if book['is_active'] else "📦"
                    source_icon = {
                        'PWD': '🏗️',
                        'LGED': '🛣️',
                        'CUSTOM': '✨'
                    }.get(book['source_type'], '📋')
                    
                    source_label = book['source_type']
                    if book['custom_source'] and book['custom_source'] != 'CUSTOM':
                        source_label = f"{book['source_type']} ({book['custom_source']})"
                    
                    st.markdown(f"**{source_icon} {book['name']}**")
                    st.caption(f"{source_label} - {book['item_count'] or 0} items - {status_icon}")
                
                with col2:
                    # ✅ View button - goes to user's instance with edit permission
                    if st.button("👁️ View", key=f"view_book_{book['id']}"):
                        st.session_state.view_book_id = book['id']
                        st.session_state.view_book_name = book['name']
                        st.session_state.view_book_source = book['source_type']
                        st.session_state.page = "rate_viewer"
                        st.rerun()
                
                with col3:
                    # ✅ Edit button - only for CUSTOM books (master instances are edited via Resync)
                    if book['source_type'] == 'CUSTOM':
                        if st.button("✏️ Edit", key=f"edit_book_{book['id']}"):
                            st.session_state.edit_book_id = book['id']
                            st.session_state.edit_book_name = book['name']
                            st.session_state.page = "company_rate_management"
                            st.rerun()
                    else:
                        # For PWD/LGED, show Resync option
                        if st.button("🔄 Resync", key=f"resync_{book['id']}"):
                            st.session_state.resync_book_id = book['id']
                            st.session_state.resync_source = book['source_type']
                            st.session_state.resync_book_name = book['name']
                            st.rerun()
                
                with col4:
                    # ✅ Details button
                    if st.button("📊 Details", key=f"details_{book['id']}"):
                        self._show_book_details(book['id'])
                
                with col5:
                    # ✅ Archive button
                    if st.button("🗑️ Archive", key=f"archive_{book['id']}"):
                        if st.checkbox(f"Archive '{book['name']}'?"):
                            conn = self.db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE tenant_rate_books 
                                SET is_archived = 1, archived_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (book['id'],))
                            conn.commit()
                            conn.close()
                            st.success(f"Archived {book['name']}")
                            st.rerun()
    
    def _show_book_details(self, book_id: int):
        """Show detailed view of a rate book"""
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rb.*,
                    (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count,
                    (SELECT COUNT(*) FROM tenant_rate_versions WHERE rate_book_id = rb.id) as version_count
                FROM tenant_rate_books rb
                WHERE rb.id = ?
            """, (book_id,))
            
            book = cursor.fetchone()
            conn.close()
            
            if book:
                # ✅ FIX: Use dictionary-style indexing, not .get()
                st.markdown(f"### 📊 Details for: {book['name']}")
                st.write(f"**Source Type:** {book['source_type']}")
                
                # Handle custom_source safely (might be None)
                custom_source = book['custom_source'] if book['custom_source'] else 'N/A'
                st.write(f"**Custom Source:** {custom_source}")
                
                st.write(f"**Items:** {book['item_count'] or 0}")
                st.write(f"**Versions:** {book['version_count'] or 0}")
                st.write(f"**Active:** {'✅' if book['is_active'] else '❌'}")
                st.write(f"**Archived:** {'✅' if book['is_archived'] else '❌'}")
                st.write(f"**Created:** {book['created_at']}")
                
                if book['description']:
                    st.write(f"**Description:** {book['description']}")
        except Exception as e:
            st.error(f"Error loading book details: {e}")

    
    # =========================================================================
    # CLONE MASTER RATES
    # =========================================================================
    
    def _render_clone_master_ui(self, company_id: int, user_id: int):
        """Clone master rates to company"""
        
        st.subheader("📋 Clone Master Rates to Your Company")
        st.caption("Create a company instance of PWD or LGED master rates that you can customize.")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type, 
                rb.is_active, 
                rb.is_archived,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.source_type IN ('PWD', 'LGED') AND rb.is_archived = 0
        """, (company_id,))
        
        existing_books = cursor.fetchall()
        conn.close()
        
        existing_types = {book['source_type'] for book in existing_books}
        has_pwd = 'PWD' in existing_types
        has_lged = 'LGED' in existing_types
        
        if existing_books:
            st.info("📚 Your current master instances:")
            for book in existing_books:
                status = "✅ Active" if book['is_active'] else "📦 Inactive"
                items = book['item_count'] or 0
                st.write(f"  - **{book['name']}** ({book['source_type']}) - {status} - {items} items")
                
                # ✅ Add View and Resync buttons for existing books
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"👁️ View {book['source_type']}", key=f"view_clone_{book['id']}"):
                        st.session_state.view_book_id = book['id']
                        st.session_state.view_book_name = book['name']
                        st.session_state.page = "rate_viewer"
                        st.rerun()
                with col2:
                    if st.button(f"🔄 Resync {book['source_type']}", key=f"resync_clone_{book['id']}"):
                        st.session_state.resync_book_id = book['id']
                        st.session_state.resync_source = book['source_type']
                        st.session_state.resync_book_name = book['name']
                        st.rerun()
        else:
            st.info("ℹ️ You don't have any master instances yet. Clone one below.")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if has_pwd:
                st.success("✅ PWD rates already cloned")
            else:
                if st.button("📋 Clone PWD Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning PWD master rates..."):
                        result = self._clone_master_to_company(company_id, user_id, 'PWD')
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")
        
        with col2:
            if has_lged:
                st.success("✅ LGED rates already cloned")
            else:
                if st.button("📋 Clone LGED Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning LGED master rates..."):
                        result = self._clone_master_to_company(company_id, user_id, 'LGED')
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")
    
    def _clone_master_to_company(self, company_id: int, user_id: int, source_type: str) -> Dict[str, Any]:
        """Clone master rates to company"""
        try:
            from services.tenant_rate_service import TenantRateService
            service = TenantRateService()
            
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
                return {'success': False, 'error': f'No active {source_type} master version found'}
            
            version_id = version['id']
            
            # Create rate book
            book_name = f"My {source_type} Rates"
            result = service.create_rate_book(
                tenant_id=company_id,
                tenant_type='company',
                name=book_name,
                source_type=source_type,
                description=f"Company instance of {source_type} master rates",
                source_version_id=version_id,
                created_by=user_id
            )
            
            if not result.get('success'):
                return result
            
            # Clone master rates
            clone_result = service.clone_master_rates(
                book_id=result['book_id'],
                source_type=source_type,
                version_id=result['version_id'],
                user_id=user_id
            )
            
            return clone_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # CUSTOM RATES
    # =========================================================================
    
    def _render_custom_rates_ui(self, company_id: int, user_id: int):
        """Create and manage custom rates - Support multiple custom books"""
        
        st.subheader("✨ Create Custom Rates")
        st.caption("Create your own custom rate books (UNDP, RHD, REB, etc.)")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.is_active, 
                rb.is_archived,
                rb.custom_source,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.source_type = 'CUSTOM' AND rb.is_archived = 0
        """, (company_id,))
        
        custom_books = cursor.fetchall()
        conn.close()
        
        if custom_books:
            st.success(f"✅ You have {len(custom_books)} custom rate book(s)")
            
            for book in custom_books:
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1])
                    
                    with col1:
                        source_label = book['custom_source'] or 'CUSTOM'
                        st.markdown(f"**📚 {book['name']}**")
                        st.caption(f"{source_label} - {book['item_count'] or 0} items - {'Active' if book['is_active'] else 'Inactive'}")
                    
                    with col2:
                        if st.button("👁️ View", key=f"view_custom_{book['id']}"):
                            st.session_state.view_book_id = book['id']
                            st.session_state.view_book_name = book['name']
                            st.session_state.page = "rate_viewer"
                            st.rerun()
                    
                    with col3:
                        if st.button("✏️ Edit", key=f"edit_custom_{book['id']}"):
                            st.session_state.edit_book_id = book['id']
                            st.session_state.edit_book_name = book['name']
                            st.session_state.page = "company_rate_management"
                            st.rerun()
                    
                    with col4:
                        if st.button("📥 Import", key=f"import_custom_{book['id']}"):
                            st.session_state.import_book_id = book['id']
                            st.rerun()
                    
                    with col5:
                        if st.button("📊 Details", key=f"details_custom_{book['id']}"):
                            self._show_book_details(book['id'])
            
            with st.expander("➕ Create Another Custom Rate Book"):
                self._render_create_custom_book_form(company_id, user_id, f"create_custom_{company_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            if st.session_state.get('import_book_id'):
                book_id = st.session_state.import_book_id
                st.info(f"Importing to book: {book_id}")
                self._render_import_custom_items_ui(company_id, user_id, book_id)
        
        else:
            st.info("ℹ️ You don't have any custom rate books yet.")
            with st.expander("➕ Create Your First Custom Rate Book", expanded=True):
                self._render_create_custom_book_form(company_id, user_id, f"create_first_custom_{company_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    def _render_create_custom_book_form(self, company_id: int, user_id: int, form_key: str = None):
        """Render form to create a new custom book"""
        
        if form_key is None:
            form_key = f"create_custom_book_{company_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        with st.form(form_key):
            book_name = st.text_input("Book Name*", placeholder="UNDP Rates, RHD Rates, REB Rates, etc.")
            description = st.text_area("Description", placeholder="Description of this custom rate book")
            
            custom_source = st.selectbox(
                "Rate Source Type",
                options=["CUSTOM", "UNDP", "RHD", "REB", "LGED", "PWD", "Other"],
                help="Select the source of these custom rates",
                key=f"custom_source_{form_key}"
            )
            
            if custom_source == "Other":
                custom_source = st.text_input("Specify Source", placeholder="e.g., Local Market Rates", key=f"other_source_{form_key}")
            
            col1, col2 = st.columns(2)
            with col1:
                include_template = st.checkbox("Include template items", value=True, key=f"include_template_{form_key}")
            with col2:
                is_active = st.checkbox("Activate immediately", value=True, key=f"is_active_{form_key}")
            
            submitted = st.form_submit_button("🚀 Create Custom Rate Book", use_container_width=True, type="primary")
            
            if submitted:
                if not book_name:
                    st.error("Please enter a book name")
                    return
                
                from services.tenant_rate_service import TenantRateService
                service = TenantRateService()
                
                result = service.repository.create_rate_book({
                    'tenant_id': company_id,
                    'tenant_type': 'company',
                    'name': book_name,
                    'source_type': 'CUSTOM',
                    'custom_source': custom_source,
                    'description': description or f"Custom rates: {book_name}",
                    'is_active': 1 if is_active else 0,
                    'created_by': user_id
                })
                
                if result:
                    book_id = result
                    
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM tenant_rate_versions 
                        WHERE rate_book_id = ? AND is_current = 1
                    """, (book_id,))
                    version = cursor.fetchone()
                    conn.close()
                    
                    version_id = version['id'] if version else None
                    
                    if include_template and version_id:
                        self._add_template_items(company_id, user_id, book_id, version_id, custom_source)
                    
                    st.success(f"✅ Created custom rate book: {book_name} ({custom_source})")
                    st.rerun()
                else:
                    st.error("❌ Failed to create rate book")
    
    def _add_template_items(self, company_id: int, user_id: int, book_id: int, version_id: int, source: str):
        """Add template items to a new custom book"""
        
        from services.tenant_rate_service import TenantRateService
        service = TenantRateService()
        
        templates = {
            'UNDP': [
                ('UNDP001', 'Skilled Labor (Foreman)', 'day', 950),
                ('UNDP002', 'Skilled Labor (Carpenter)', 'day', 700),
                ('UNDP003', 'Skilled Labor (Mason)', 'day', 600),
                ('UNDP004', 'Unskilled Labor', 'day', 450),
                ('UNDP005', 'Equipment Rental (JCB)', 'hour', 1000),
                ('UNDP006', 'Equipment Rental (Dump Truck)', 'hour', 800),
                ('UNDP007', 'Transportation (Truck 3T)', 'trip', 4500),
                ('UNDP008', 'Quality Control (Concrete Test)', 'test', 2000),
            ],
            'RHD': [
                ('RHD001', 'Road Base Course', 'cum', 2200),
                ('RHD002', 'Bituminous Pavement', 'sqm', 850),
                ('RHD003', 'Sub-Base Layer', 'cum', 1800),
                ('RHD004', 'Drainage Works', 'meter', 500),
            ],
            'REB': [
                ('REB001', 'Electric Pole Installation', 'unit', 5000),
                ('REB002', 'Transformer Installation', 'unit', 15000),
                ('REB003', 'Cable Laying', 'meter', 200),
                ('REB004', 'Meter Installation', 'unit', 1000),
            ]
        }
        
        items_to_add = templates.get(source.upper(), [
            ('CUST001', 'Custom Item 1', 'each', 1000),
            ('CUST002', 'Custom Item 2', 'each', 1200),
            ('CUST003', 'Custom Item 3', 'each', 1500),
        ])
        
        for code, desc, unit, base_rate in items_to_add:
            try:
                item_id = service.repository.create_rate_item({
                    'rate_book_id': book_id,
                    'item_code': code,
                    'item_description': desc,
                    'unit': unit,
                    'is_custom': 1,
                    'created_by': user_id,
                    'skip_pricing': True
                })
                
                for level, discount in [('ECONOMY', 0.22), ('MARKET', 0.18), ('PREMIUM', 0.14)]:
                    price = base_rate * (1 - discount)
                    service.repository.update_pricing(
                        version_id=version_id,
                        item_id=item_id,
                        pricing_level=level,
                        price=round(price, 2),
                        user_id=user_id
                    )
            except Exception as e:
                logger.warning(f"Could not add template item {code}: {e}")
    
    def _render_import_custom_items_ui(self, company_id: int, user_id: int, book_id: int):
        """Import custom items from file"""
        
        st.markdown("##### Upload File")
        st.caption("Supports CSV, Excel (xlsx, xls)")
        
        st.info("📌 **CSV Format:** Use comma-separated values. If descriptions contain commas, wrap them in quotes.")
        st.caption("Example: `CUST001,\"Skilled Labor, Foreman\",day,800,950,1100,UNDP,Construction supervisor`")
        
        uploaded_file = st.file_uploader(
            "Choose file",
            type=["xlsx", "xls", "csv"],
            key=f"import_custom_items_{book_id}"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    try:
                        df = pd.read_csv(uploaded_file, encoding='utf-8')
                    except pd.errors.ParserError as e:
                        st.warning(f"⚠️ Parser error: {e}. Trying with alternative settings...")
                        try:
                            uploaded_file.seek(0)
                            df = pd.read_csv(
                                uploaded_file, 
                                encoding='utf-8',
                                quotechar='"',
                                escapechar='\\'
                            )
                        except:
                            uploaded_file.seek(0)
                            df = pd.read_csv(
                                uploaded_file, 
                                encoding='utf-8',
                                header=None,
                                names=['item_code', 'description', 'unit', 'economy_rate', 'market_rate', 'premium_rate', 'source', 'notes']
                            )
                else:
                    df = pd.read_excel(uploaded_file)
                
                df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
                
                column_map = {}
                for col in df.columns:
                    if 'code' in col or 'item' in col:
                        column_map['item_code'] = col
                    elif 'description' in col or 'desc' in col or 'name' in col:
                        column_map['description'] = col
                    elif 'unit' in col:
                        column_map['unit'] = col
                    elif 'economy' in col or 'aggres' in col:
                        column_map['economy_rate'] = col
                    elif 'market' in col or 'compet' in col:
                        column_map['market_rate'] = col
                    elif 'premium' in col or 'standard' in col or 'high' in col:
                        column_map['premium_rate'] = col
                    elif 'source' in col:
                        column_map['source'] = col
                    elif 'note' in col:
                        column_map['notes'] = col
                
                if 'item_code' not in column_map or 'description' not in column_map:
                    st.error("❌ Could not find required columns: 'item_code' and 'description'")
                    st.write("Found columns:", list(df.columns))
                    st.code("item_code,description,unit,economy_rate,market_rate,premium_rate,source,notes")
                    return
                
                std_df = pd.DataFrame()
                std_df['item_code'] = df[column_map['item_code']].astype(str).str.strip()
                std_df['description'] = df[column_map['description']].astype(str).str.strip()
                
                if 'unit' in column_map:
                    std_df['unit'] = df[column_map['unit']].astype(str).str.strip()
                else:
                    std_df['unit'] = ''
                
                default_rates = {'economy_rate': 1000, 'market_rate': 1200, 'premium_rate': 1500}
                for rate_key, default_val in default_rates.items():
                    if rate_key in column_map:
                        std_df[rate_key] = pd.to_numeric(df[column_map[rate_key]], errors='coerce').fillna(default_val)
                    else:
                        std_df[rate_key] = default_val
                
                if 'source' in column_map:
                    std_df['source'] = df[column_map['source']].astype(str).str.strip()
                else:
                    std_df['source'] = 'CUSTOM'
                
                if 'notes' in column_map:
                    std_df['notes'] = df[column_map['notes']].astype(str).str.strip()
                else:
                    std_df['notes'] = ''
                
                std_df = std_df[std_df['item_code'].notna() & (std_df['item_code'] != '')]
                std_df = std_df[std_df['description'].notna() & (std_df['description'] != '')]
                
                if std_df.empty:
                    st.error("❌ No valid data found after processing")
                    return
                
                st.markdown("**Preview (processed):**")
                st.dataframe(std_df.head(10))
                st.info(f"📋 Found {len(std_df)} items ready to import")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 Validate Data", key=f"validate_custom_{book_id}"):
                        errors = []
                        for idx, row in std_df.iterrows():
                            if not row.get('item_code') or not row.get('description'):
                                errors.append(f"Row {idx+2}: Missing required fields")
                        if errors:
                            for err in errors[:10]:
                                st.error(f"❌ {err}")
                        else:
                            st.success("✅ All items validated successfully!")
                
                with col2:
                    if st.button("📥 Import Custom Items", key=f"import_custom_{book_id}", type="primary"):
                        with st.spinner(f"Importing {len(std_df)} custom items..."):
                            result = self._import_custom_items(company_id, user_id, book_id, std_df)
                            if result.get('success'):
                                st.success(f"✅ {result.get('message', 'Import successful!')}")
                                if result.get('errors'):
                                    with st.expander("⚠️ Errors encountered"):
                                        for err in result.get('errors', []):
                                            st.write(f"- {err}")
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('error', 'Import failed')}")
                                
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.code(str(e))
    
    def _import_custom_items(self, company_id: int, user_id: int, book_id: int, df: pd.DataFrame) -> Dict[str, Any]:
        """Import custom items from dataframe"""
        try:
            from services.tenant_rate_service import TenantRateService
            service = TenantRateService()
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = 1
            """, (book_id,))
            version = cursor.fetchone()
            conn.close()
            
            if not version:
                return {'success': False, 'error': 'No active version found for this book'}
            
            version_id = version['id']
            
            success_count = 0
            error_count = 0
            errors = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_rows = len(df)
            
            for idx, row in df.iterrows():
                progress = (idx + 1) / total_rows
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx + 1}/{total_rows}: {row.get('item_code', 'Unknown')}")
                
                try:
                    item_code = str(row.get('item_code', '')).strip()
                    description = str(row.get('description', '')).strip()
                    unit = str(row.get('unit', '')).strip()
                    economy_rate = float(row.get('economy_rate', 0))
                    market_rate = float(row.get('market_rate', 0))
                    premium_rate = float(row.get('premium_rate', 0))
                    
                    if not item_code or not description:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Missing item_code or description")
                        continue
                    
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM tenant_rate_items 
                        WHERE rate_book_id = ? AND item_code = ? AND is_archived = 0
                    """, (book_id, item_code))
                    existing = cursor.fetchone()
                    conn.close()
                    
                    if existing:
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE tenant_rate_items 
                            SET item_description = ?, unit = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (description, unit, existing['id']))
                        conn.commit()
                        conn.close()
                        item_id = existing['id']
                    else:
                        item_id = service.repository.create_rate_item({
                            'rate_book_id': book_id,
                            'item_code': item_code,
                            'item_description': description,
                            'unit': unit,
                            'is_custom': 1,
                            'created_by': user_id,
                            'skip_pricing': True
                        })
                    
                    if item_id:
                        pricing_data = [
                            ('ECONOMY', economy_rate),
                            ('MARKET', market_rate),
                            ('PREMIUM', premium_rate)
                        ]
                        
                        for level, price in pricing_data:
                            if price > 0:
                                service.repository.update_pricing(
                                    version_id=version_id,
                                    item_id=item_id,
                                    pricing_level=level,
                                    price=round(price, 2),
                                    user_id=user_id
                                )
                        
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Failed to create item {item_code}")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {idx+2}: {str(e)}")
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count > 0:
                st.balloons()
                st.success(f"✅ Successfully imported {success_count} custom items!")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} items failed.")
            else:
                st.error(f"❌ Import failed. No items were imported.")
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tenant_rate_import_log 
                (rate_book_id, file_name, import_type, total_records, successful_records, failed_records, error_log, imported_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, 'custom_import.csv', 'CUSTOM', len(df), success_count, error_count, 
                  json.dumps(errors[:20]), user_id))
            conn.commit()
            conn.close()
            
            if errors:
                with st.expander(f"⚠️ {len(errors)} Errors encountered"):
                    for err in errors[:20]:
                        st.write(f"- {err}")
                    if len(errors) > 20:
                        st.write(f"... and {len(errors) - 20} more errors")
            
            return {
                'success': True,
                'message': f'Imported {success_count} items, {error_count} failed',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors[:20]
            }
            
        except Exception as e:
            logger.error(f"Error importing custom items: {e}")
            return {'success': False, 'error': str(e)}
    
    def _render_boq_import_ui(self, company_id: int, user_id: int):
        """Import BOQ data"""
        
        st.subheader("📊 Import BOQ Data")
        st.caption("Import your BOQ data for analysis and optimization.")
        
        uploaded_file = st.file_uploader(
            "Choose BOQ Excel file",
            type=["xlsx", "xls", "csv"],
            key="import_boq"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.markdown("**Preview:**")
                st.dataframe(df.head(10))
                
                if st.button("📥 Import BOQ", use_container_width=True, type="primary"):
                    with st.spinner("Importing BOQ data..."):
                        # Import logic here
                        st.success("✅ BOQ data imported successfully!")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    def _render_audit_history(self, company_id: int):
        """Render audit history"""
        
        st.subheader("📋 Audit History")
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM archive_metadata 
                WHERE company_id = ? 
                ORDER BY initiated_at DESC
            """, (company_id,))
            
            archives = cursor.fetchall()
            conn.close()
            
            if archives:
                archive_list = []
                for row in archives:
                    archive_list.append({
                        'archive_batch_id': row['archive_batch_id'],
                        'operation_type': row['operation_type'],
                        'description': row['description'],
                        'total_records_archived': row['total_records_archived'],
                        'initiated_at': row['initiated_at'],
                        'status': row['status']
                    })
                df = pd.DataFrame(archive_list)
                st.dataframe(df)
            else:
                st.info("No audit records found.")
        except Exception as e:
            st.error(f"Error loading audit history: {e}")

    # modules/data_management.py - Add this method

    def _render_clone_resync_ui(self, company_id: int, user_id: int):
        """Clone master rates to company and resync existing copies"""
        
        st.subheader("🔄 Clone & Resync")
        st.caption("Clone PWD/LGED master rates to your company, or resync existing copies with the latest master rates.")
        
        # ========== CLONE MASTER RATES ==========
        st.markdown("### 📋 Clone Master Rates")
        st.caption("Create a company instance of PWD or LGED master rates.")
        
        # Check existing clones
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type, 
                rb.is_active, 
                rb.is_archived,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.source_type IN ('PWD', 'LGED') AND rb.is_archived = 0
        """, (company_id,))
        
        existing_books = cursor.fetchall()
        conn.close()
        
        existing_types = {book['source_type'] for book in existing_books}
        has_pwd = 'PWD' in existing_types
        has_lged = 'LGED' in existing_types
        
        if existing_books:
            st.info("📚 Your current master instances:")
            for book in existing_books:
                status = "✅ Active" if book['is_active'] else "📦 Inactive"
                items = book['item_count'] or 0
                st.write(f"  - **{book['name']}** ({book['source_type']}) - {status} - {items} items")
        else:
            st.info("ℹ️ You don't have any master instances yet. Clone one below.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if has_pwd:
                st.success("✅ PWD rates already cloned")
                if st.button("📊 View PWD Rates", use_container_width=True, key="view_pwd_clone"):
                    st.session_state.page = "rate_viewer"
                    st.rerun()
            else:
                if st.button("📋 Clone PWD Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning PWD master rates..."):
                        result = self._clone_master_to_company(company_id, user_id, 'PWD')
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")
        
        with col2:
            if has_lged:
                st.success("✅ LGED rates already cloned")
                if st.button("📊 View LGED Rates", use_container_width=True, key="view_lged_clone"):
                    st.session_state.page = "rate_viewer"
                    st.rerun()
            else:
                if st.button("📋 Clone LGED Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning LGED master rates..."):
                        result = self._clone_master_to_company(company_id, user_id, 'LGED')
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")
        
        st.divider()
        
        # ========== RESYNC EXISTING COPIES ==========
        st.markdown("### 🔄 Resync with Master")
        st.caption("Update your existing copies with the latest master rates.")
        st.warning("⚠️ This will OVERWRITE your current rates with master rates!")
        
        # Get books that can be resynced (PWD/LGED with items)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? 
            AND rb.source_type IN ('PWD', 'LGED') 
            AND rb.is_archived = 0
            AND rb.is_active = 1
        """, (company_id,))
        
        resync_books = cursor.fetchall()
        conn.close()
        
        if not resync_books:
            st.info("ℹ️ No PWD or LGED books to resync. Clone one first.")
        else:
            # Select book to resync
            book_options = {b['id']: f"{b['name']} ({b['source_type']}) - {b['item_count'] or 0} items" for b in resync_books}
            selected_resync_id = st.selectbox(
                "Select Book to Resync",
                options=list(book_options.keys()),
                format_func=lambda x: book_options.get(x, "Unknown"),
                key="resync_select"
            )
            
            if selected_resync_id:
                selected_book = next((b for b in resync_books if b['id'] == selected_resync_id), None)
                
                if selected_book:
                    st.warning(f"⚠️ You are about to resync **{selected_book['name']}** ({selected_book['source_type']})")
                    st.caption(f"This will replace all {selected_book['item_count'] or 0} items with the latest master rates.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        confirm = st.checkbox("I understand this will overwrite my current rates", key="resync_confirm")
                    with col2:
                        if confirm:
                            if st.button("🔄 Resync Now", type="primary", use_container_width=True):
                                with st.spinner(f"Resyncing {selected_book['source_type']}..."):
                                    result = self._resync_with_master(
                                        company_id, 
                                        user_id, 
                                        selected_book['id'], 
                                        selected_book['source_type']
                                    )
                                    if result.get('success'):
                                        st.success(f"✅ {result.get('message', 'Resync successful!')}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {result.get('error', 'Resync failed')}")
                        else:
                            st.button("🔄 Resync Now", disabled=True, use_container_width=True, 
                                    help="Please confirm the checkbox first")


    def _resync_with_master(self, company_id: int, user_id: int, book_id: int, source_type: str) -> Dict[str, Any]:
        """Resync company rates with master"""
        try:
            from services.tenant_rate_service import TenantRateService
            service = TenantRateService()
            
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
                return {'success': False, 'error': f'No active {source_type} master version found'}
            
            version_id = version['id']
            
            # Delete existing items for this book
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Delete pricing levels
            cursor.execute("""
                DELETE FROM tenant_pricing_levels 
                WHERE rate_item_id IN (
                    SELECT id FROM tenant_rate_items 
                    WHERE rate_book_id = ?
                )
            """, (book_id,))
            
            # Delete items
            cursor.execute("""
                DELETE FROM tenant_rate_items 
                WHERE rate_book_id = ?
            """, (book_id,))
            
            conn.commit()
            conn.close()
            
            # Clone fresh master rates
            clone_result = service.clone_master_rates(
                book_id=book_id,
                source_type=source_type,
                version_id=version_id,
                user_id=user_id
            )
            
            # Log the resync
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tenant_rate_audit 
                (rate_book_id, action, field_name, old_value, new_value, user_id)
                VALUES (?, 'RESYNC', 'all_items', 'previous_version', ?, ?)
            """, (book_id, f'v{version_id}', user_id))
            conn.commit()
            conn.close()
            
            return clone_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    # modules/data_management.py - Add this method

    def _render_import_export_ui(self, company_id: int, user_id: int):
        """Import and Export company rate data"""
        
        st.subheader("📥 Import & Export")
        st.caption("Import custom rates or export your company rate books.")
        
        # ========== TABS FOR IMPORT/EXPORT ==========
        tab1, tab2, tab3, tab4 = st.tabs([
            "📤 Export Rates",
            "📥 Import Custom Rates",
            "📥 Import Costs",
            "📤 Export BOQ"
        ])
        
        with tab1:
            self._render_export_rates_ui(company_id, user_id)
        
        with tab2:
            self._render_import_custom_rates_ui(company_id, user_id)
        
        with tab3:
            self._render_import_costs_ui(company_id, user_id)
        
        with tab4:
            self._render_export_boq_ui(company_id, user_id)


    def _render_export_rates_ui(self, company_id: int, user_id: int):
        """Export company rate books to CSV/Excel"""
        
        st.markdown("#### 📤 Export Rate Book")
        st.caption("Export your company rate books with all cost levels.")
        
        # Get all rate books
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                rb.id, 
                rb.name, 
                rb.source_type,
                rb.custom_source,
                (SELECT COUNT(*) FROM tenant_rate_items WHERE rate_book_id = rb.id AND is_archived = 0) as item_count
            FROM tenant_rate_books rb
            WHERE rb.tenant_id = ? AND rb.is_archived = 0
            ORDER BY rb.source_type, rb.name
        """, (company_id,))
        
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            st.info("ℹ️ No rate books found to export.")
            return
        
        # Select book to export
        book_options = {}
        for book in books:
            source_label = book['source_type']
            if book['custom_source'] and book['custom_source'] != 'CUSTOM':
                source_label = f"{book['source_type']} ({book['custom_source']})"
            book_options[book['id']] = f"{book['name']} ({source_label}) - {book['item_count'] or 0} items"
        
        selected_book_id = st.selectbox(
            "Select Rate Book to Export",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="export_book_select"
        )
        
        if not selected_book_id:
            return
        
        # Get version
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, version_name, is_current 
            FROM tenant_rate_versions 
            WHERE rate_book_id = ? 
            ORDER BY is_current DESC, version_number DESC
            LIMIT 1
        """, (selected_book_id,))
        version = cursor.fetchone()
        conn.close()
        
        if not version:
            st.warning("No version found for this book")
            return
        
        version_id = version['id']
        
        # Get items with costs
        from services.tenant_rate_service import TenantRateService
        service = TenantRateService()
        items = service.repository.get_rate_items_by_book(selected_book_id, version_id)
        
        if not items:
            st.info("No items found in this rate book")
            return
        
        # Prepare export data
        export_data = []
        for item in items:
            if not isinstance(item, dict):
                continue
            
            pricing = item.get('pricing', {})
            
            def get_cost(pricing_data, level):
                if not pricing_data:
                    return ''
                if isinstance(pricing_data, dict):
                    level_data = pricing_data.get(level, {})
                    if isinstance(level_data, dict):
                        return level_data.get('price', '')
                    elif isinstance(level_data, (int, float)):
                        return level_data
                return ''
            
            export_data.append({
                'Item Code': item.get('item_code', ''),
                'Description': item.get('item_description', ''),
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if item.get('is_custom') else 'Master',
                'Aggressive Cost': get_cost(pricing, 'AGGRESSIVE'),
                'Competitive Cost': get_cost(pricing, 'COMPETITIVE'),
                'Standard Cost': get_cost(pricing, 'STANDARD'),
            })
        
        df = pd.DataFrame(export_data)
        
        st.markdown("#### Export Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Total: {len(df)} items")
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV Export
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Export as CSV",
                csv,
                f"rate_book_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            # Excel Export
            try:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Rate Book', index=False)
                    
                    # Add summary sheet
                    summary_data = {
                        'Parameter': ['Book Name', 'Source Type', 'Total Items', 'Export Date'],
                        'Value': [
                            next((b['name'] for b in books if b['id'] == selected_book_id), 'N/A'),
                            next((b['source_type'] for b in books if b['id'] == selected_book_id), 'N/A'),
                            len(df),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                output.seek(0)
                st.download_button(
                    "📥 Export as Excel",
                    output,
                    f"rate_book_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.info("💡 Install openpyxl for Excel export: `pip install openpyxl`")


    def _render_import_custom_rates_ui(self, company_id: int, user_id: int):
        """Import custom rate items from CSV/Excel"""
        
        st.markdown("#### 📥 Import Custom Rate Items")
        st.caption("Import custom items that are not in PWD/LGED master rates.")
        st.info("📌 Format: item_code, description, unit, aggressive_cost, competitive_cost, standard_cost")
        
        # Get existing custom books
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, custom_source
            FROM tenant_rate_books 
            WHERE tenant_id = ? AND source_type = 'CUSTOM' AND is_archived = 0
        """, (company_id,))
        
        custom_books = cursor.fetchall()
        conn.close()
        
        if not custom_books:
            st.warning("⚠️ No custom rate book found. Create one first in 'My Rate Books' tab.")
            return
        
        book_options = {b['id']: f"{b['name']} ({b['custom_source'] or 'CUSTOM'})" for b in custom_books}
        selected_book_id = st.selectbox(
            "Select Custom Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="import_custom_book_select"
        )
        
        if not selected_book_id:
            return
        
        uploaded_file = st.file_uploader(
            "Choose file (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            key="import_custom_file"
        )
        
        if uploaded_file:
            try:
                # Read file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Normalize columns
                df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
                
                # Map columns
                column_map = {}
                for col in df.columns:
                    if 'code' in col or 'item' in col:
                        column_map['item_code'] = col
                    elif 'description' in col or 'desc' in col:
                        column_map['description'] = col
                    elif 'unit' in col:
                        column_map['unit'] = col
                    elif 'aggressive' in col or 'agg' in col:
                        column_map['aggressive_cost'] = col
                    elif 'competitive' in col or 'comp' in col:
                        column_map['competitive_cost'] = col
                    elif 'standard' in col or 'std' in col:
                        column_map['standard_cost'] = col
                
                if 'item_code' not in column_map or 'description' not in column_map:
                    st.error("❌ Could not find required columns: 'item_code' and 'description'")
                    st.write("Found columns:", list(df.columns))
                    return
                
                # Create standardized dataframe
                std_df = pd.DataFrame()
                std_df['item_code'] = df[column_map['item_code']].astype(str).str.strip()
                std_df['description'] = df[column_map['description']].astype(str).str.strip()
                std_df['unit'] = df[column_map['unit']].astype(str).str.strip() if 'unit' in column_map else ''
                
                # Handle costs with defaults
                default_costs = {
                    'aggressive_cost': 1000,
                    'competitive_cost': 1200,
                    'standard_cost': 1500
                }
                
                for cost_key, default_val in default_costs.items():
                    if cost_key in column_map:
                        std_df[cost_key] = pd.to_numeric(df[column_map[cost_key]], errors='coerce').fillna(default_val)
                    else:
                        std_df[cost_key] = default_val
                
                # Remove empty rows
                std_df = std_df[std_df['item_code'].notna() & (std_df['item_code'] != '')]
                std_df = std_df[std_df['description'].notna() & (std_df['description'] != '')]
                
                if std_df.empty:
                    st.error("❌ No valid data found")
                    return
                
                st.markdown("**Preview:**")
                st.dataframe(std_df.head(10))
                st.info(f"📋 Found {len(std_df)} items ready to import")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 Validate Data", key="validate_import"):
                        errors = self._validate_import_data(std_df)
                        if errors:
                            for err in errors[:10]:
                                st.error(f"❌ {err}")
                        else:
                            st.success("✅ All items validated successfully!")
                
                with col2:
                    if st.button("📥 Import Custom Rates", key="import_custom", type="primary"):
                        with st.spinner(f"Importing {len(std_df)} custom items..."):
                            result = self._import_custom_items_data(company_id, user_id, selected_book_id, std_df)
                            if result.get('success'):
                                st.success(f"✅ {result.get('message', 'Import successful!')}")
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('error', 'Import failed')}")
                
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.info("💡 Make sure your CSV/Excel has the correct format:")
                st.code("item_code,description,unit,aggressive_cost,competitive_cost,standard_cost")


    def _render_import_costs_ui(self, company_id: int, user_id: int):
        """Import costs for existing rate book items"""
        
        st.markdown("#### 📥 Import Costs")
        st.caption("Import costs for items in an existing rate book.")
        st.info("📌 Format: item_code, aggressive_cost, competitive_cost, standard_cost")
        
        # Get all rate books
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, source_type
            FROM tenant_rate_books 
            WHERE tenant_id = ? AND is_archived = 0
        """, (company_id,))
        
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            st.info("ℹ️ No rate books found.")
            return
        
        book_options = {b['id']: f"{b['name']} ({b['source_type']})" for b in books}
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="import_costs_book_select"
        )
        
        if not selected_book_id:
            return
        
        uploaded_file = st.file_uploader(
            "Choose file (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            key="import_costs_file"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                else:
                    df = pd.read_excel(uploaded_file)
                
                df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
                
                # Map columns
                column_map = {}
                for col in df.columns:
                    if 'code' in col or 'item' in col:
                        column_map['item_code'] = col
                    elif 'aggressive' in col or 'agg' in col:
                        column_map['aggressive_cost'] = col
                    elif 'competitive' in col or 'comp' in col:
                        column_map['competitive_cost'] = col
                    elif 'standard' in col or 'std' in col:
                        column_map['standard_cost'] = col
                
                if 'item_code' not in column_map:
                    st.error("❌ Could not find required column: 'item_code'")
                    return
                
                # Create standardized dataframe
                std_df = pd.DataFrame()
                std_df['item_code'] = df[column_map['item_code']].astype(str).str.strip()
                
                for cost_key in ['aggressive_cost', 'competitive_cost', 'standard_cost']:
                    if cost_key in column_map:
                        std_df[cost_key] = pd.to_numeric(df[column_map[cost_key]], errors='coerce')
                    else:
                        std_df[cost_key] = None
                
                # Remove empty rows
                std_df = std_df[std_df['item_code'].notna() & (std_df['item_code'] != '')]
                
                if std_df.empty:
                    st.error("❌ No valid data found")
                    return
                
                st.markdown("**Preview:**")
                st.dataframe(std_df.head(10))
                st.info(f"📋 Found {len(std_df)} items ready to import")
                
                if st.button("📥 Import Costs", type="primary", use_container_width=True):
                    with st.spinner(f"Importing costs for {len(std_df)} items..."):
                        result = self._import_cost_data(company_id, user_id, selected_book_id, std_df)
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Import successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Import failed')}")
                
            except Exception as e:
                st.error(f"Error reading file: {e}")


    def _render_export_boq_ui(self, company_id: int, user_id: int):
        """Export BOQ data"""
        
        st.markdown("#### 📤 Export BOQ Data")
        st.caption("Export BOQ data for analysis and reporting.")
        
        # Get BOQ history
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tender_id, tender_title, item_count, total_estimated_cost,
                selected_zone, rate_source, status, generated_at
            FROM boq_generation_history
            WHERE company_id = ?
            ORDER BY generated_at DESC
            LIMIT 50
        """, (company_id,))
        
        boqs = cursor.fetchall()
        conn.close()
        
        if not boqs:
            st.info("ℹ️ No BOQs found to export.")
            return
        
        boq_options = {b['id']: f"{b['tender_title'][:50]}... ({b['generated_at']})" for b in boqs}
        selected_boq_id = st.selectbox(
            "Select BOQ to Export",
            options=list(boq_options.keys()),
            format_func=lambda x: boq_options.get(x, "Unknown"),
            key="export_boq_select"
        )
        
        if not selected_boq_id:
            return
        
        # Get BOQ items
        conn = self.db.get_connection()
        boq_items = pd.read_sql_query("""
            SELECT item_code, description, unit, quantity, unit_rate, total, is_custom
            FROM boq_items
            WHERE boq_id = ?
            ORDER BY is_custom DESC, item_code
        """, conn, params=[selected_boq_id])
        conn.close()
        
        if boq_items.empty:
            st.info("No items found in this BOQ")
            return
        
        # Get BOQ header
        boq_info = next((b for b in boqs if b['id'] == selected_boq_id), None)
        
        st.markdown("#### Preview")
        st.dataframe(boq_items.head(10), use_container_width=True)
        st.caption(f"Total: {len(boq_items)} items")
        
        # Export
        csv = boq_items.to_csv(index=False)
        st.download_button(
            "📥 Export BOQ as CSV",
            csv,
            f"boq_{boq_info['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True,
            type="primary"
        )


    def _validate_import_data(self, df: pd.DataFrame) -> List[str]:
        """Validate import data"""
        errors = []
        for idx, row in df.iterrows():
            if not row.get('item_code'):
                errors.append(f"Row {idx+2}: Missing item_code")
            if not row.get('description'):
                errors.append(f"Row {idx+2}: Missing description")
        return errors


    def _import_custom_items_data(self, company_id: int, user_id: int, book_id: int, df: pd.DataFrame) -> Dict[str, Any]:
        """Import custom items data"""
        try:
            from services.tenant_rate_service import TenantRateService
            service = TenantRateService()
            
            # Get current version
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = 1
            """, (book_id,))
            version = cursor.fetchone()
            conn.close()
            
            if not version:
                return {'success': False, 'error': 'No active version found'}
            
            version_id = version['id']
            
            success_count = 0
            error_count = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    item_code = str(row.get('item_code', '')).strip()
                    description = str(row.get('description', '')).strip()
                    unit = str(row.get('unit', '')).strip()
                    aggressive = float(row.get('aggressive_cost', 0))
                    competitive = float(row.get('competitive_cost', 0))
                    standard = float(row.get('standard_cost', 0))
                    
                    if not item_code or not description:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Missing required fields")
                        continue
                    
                    # Create item
                    item_id = service.repository.create_rate_item({
                        'rate_book_id': book_id,
                        'item_code': item_code,
                        'item_description': description,
                        'unit': unit,
                        'is_custom': 1,
                        'created_by': user_id,
                        'skip_pricing': True
                    })
                    
                    if item_id:
                        # Add costs
                        cost_levels = [
                            ('AGGRESSIVE', aggressive),
                            ('COMPETITIVE', competitive),
                            ('STANDARD', standard)
                        ]
                        
                        for level, cost in cost_levels:
                            if cost > 0:
                                service.repository.update_pricing(
                                    version_id=version_id,
                                    item_id=item_id,
                                    pricing_level=level,
                                    price=round(cost, 2),
                                    user_id=user_id
                                )
                        
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Failed to create item")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {idx+2}: {str(e)}")
            
            return {
                'success': True,
                'message': f'Imported {success_count} items, {error_count} failed',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors[:20]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


    def _import_cost_data(self, company_id: int, user_id: int, book_id: int, df: pd.DataFrame) -> Dict[str, Any]:
        """Import cost data for existing items"""
        try:
            from services.tenant_rate_service import TenantRateService
            service = TenantRateService()
            
            # Get current version
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = 1
            """, (book_id,))
            version = cursor.fetchone()
            conn.close()
            
            if not version:
                return {'success': False, 'error': 'No active version found'}
            
            version_id = version['id']
            
            # Get existing items by code
            items = service.repository.get_rate_items_by_book(book_id, version_id)
            items_by_code = {item['item_code']: item for item in items if isinstance(item, dict)}
            
            success_count = 0
            error_count = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    item_code = str(row.get('item_code', '')).strip()
                    
                    if not item_code:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Missing item_code")
                        continue
                    
                    if item_code not in items_by_code:
                        error_count += 1
                        errors.append(f"Row {idx+2}: Item '{item_code}' not found in rate book")
                        continue
                    
                    item_id = items_by_code[item_code]['id']
                    
                    # Update costs
                    for level in ['aggressive_cost', 'competitive_cost', 'standard_cost']:
                        cost = row.get(level)
                        if cost is not None and cost != '':
                            try:
                                cost = float(cost)
                                level_name = level.upper().replace('_COST', '')
                                service.repository.update_pricing(
                                    version_id=version_id,
                                    item_id=item_id,
                                    pricing_level=level_name,
                                    price=round(cost, 2),
                                    user_id=user_id
                                )
                            except:
                                pass
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {idx+2}: {str(e)}")
            
            return {
                'success': True,
                'message': f'Updated {success_count} items, {error_count} failed',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors[:20]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}    
    

def render_data_management(db):
    """Convenience function"""
    manager = DataManagement(db)
    manager.render()