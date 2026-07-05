# modules/company_rate_management.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import io
from typing import Optional, Dict, Any, List
from database.unified_db_manager import get_db_manager  # ✅ Import this

from modules.rbac import (
    can_view_tenant_rates,
    can_create_rate_book,
    can_edit_tenant_rates,
    can_delete_tenant_rates,
    can_import_tenant_rates,
    can_export_tenant_rates,
    can_clone_master_rates,
    can_create_rate_version,
    can_archive_rate_book,
    can_manage_rate_books,
    render_role_badge,
    render_protected_button
)


class CompanyRateManagement:
    """
    Company-level rate management module.
    Uses DatabaseCRUD via get_db_manager() for all database operations.
    """
    
    def __init__(self):
        """Initialize with cached database manager"""
        self.db = get_db_manager()  # ✅ Use cached manager
    
        #db = DatabaseCRUD()
        print(f"🔍 has create_rate_book: {hasattr(self.db, 'create_rate_book')}")
        print(f"🔍 has get_rate_books_by_tenant: {hasattr(self.db, 'get_rate_books_by_tenant')}")
        print(f"🔍 has query_one: {hasattr(self.db, 'query_one')}")
        print(f"🔍 has execute: {hasattr(self.db, 'execute')}")

        # Test the binding
        result = self.db.test_method()
        print(f"🔍 test_method result: {result}")

    def _get_tenant_info(self):
        """Get current tenant info from session state"""
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        
        return {
            'user_id': user_id,
            'company_id': company_id,
            'tenant_id': company_id or user_id,  # ✅ Falls back to user_id if no company
            'tenant_type': 'company' if company_id else 'user',  # ✅ Correct type
            'user_role': st.session_state.get('user_role', 'viewer'),
            'username': st.session_state.get('username', 'unknown')
        }

    
    def _check_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        tenant = self._get_tenant_info()
        role = tenant['user_role']
        
        if role in ['system_admin', 'admin']:
            return True
        
        if role in ['company_admin', 'manager']:
            if permission == 'read':
                return can_view_tenant_rates()
            elif permission == 'create':
                return can_create_rate_book()
            elif permission == 'update':
                return can_edit_tenant_rates()
            elif permission == 'delete':
                return can_delete_tenant_rates()
            elif permission == 'import':
                return can_import_tenant_rates()
            elif permission == 'export':
                return can_export_tenant_rates()
            elif permission == 'clone':
                return can_clone_master_rates()
            elif permission == 'version':
                return can_create_rate_version()
            elif permission == 'archive':
                return can_archive_rate_book()
        
        return False
    
    def render(self):
        """Main interface with unified tabs"""
        
        st.markdown("""
        <div class="main-header">
            <h1>📚 Rate Management</h1>
            <p>Manage your rate books, clone master rates, and create custom rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        self._show_environment_status()
        
        tenant = self._get_tenant_info()
        
        # ✅ Show appropriate message for individual users
        if not tenant.get('company_id'):
            st.info("👤 **Individual User Mode** - You can manage your own rate books.")
            st.caption("Rate books created here will be associated with your user account.")
        
        self._show_subscription_info(tenant)

        
        active_tab = st.session_state.get('active_tab', 0)
        
        tabs = st.tabs([
            "📚 My Rate Books",
            "📋 Clone Master Rates",
            "➕ Create Custom Book",
            "✏️ Edit Costs",
            "📊 Versions",
            "📥 Import/Export",
            "📋 Audit History"
        ])
        
        for i, tab in enumerate(tabs):
            with tab:
                self._render_tab_content(i, tenant)
    
    
    def _render_tab_content(self, tab_index: int, tenant: Dict):
        """Render content for each tab"""
        
        if tab_index == 0:
            self._render_my_rate_books(tenant)
        elif tab_index == 1:
            self._render_clone_master_rates(tenant)
        elif tab_index == 2:
            self._render_create_custom_book(tenant)
        elif tab_index == 3:
            self._render_edit_rate_book()
        elif tab_index == 4:
            self._render_rate_versions(tenant)
        elif tab_index == 5:
            self._render_import_export(tenant)
        elif tab_index == 6:
            self._render_audit_history(tenant)
    
    # =========================================================================
    # TAB 1: MY RATE BOOKS
    # =========================================================================
    def _render_my_rate_books(self, tenant: Dict):
        """Render My Rate Books - using db directly"""
        
        st.subheader("📚 My Company Rate Books")
        st.caption("View and manage your company's rate books")
        
        tenant_id = tenant.get('company_id') or tenant.get('user_id')
        tenant_type = tenant.get('tenant_type', 'company')
        
        if not tenant_id:
            st.warning("⚠️ No tenant found.")
            return
        
        # ✅ Use db directly with correct tenant_id and tenant_type
        try:
            books = self.db.get_rate_books_by_tenant(tenant_id, tenant_type)
        except Exception as e:
            st.error(f"Error loading rate books: {e}")
            books = []
        
        if not books:
            st.info("ℹ️ You don't have any rate books yet.")
            st.info("Go to 'Clone Master Rates' tab to clone master rates, or 'Create Custom Book' to create your own.")
            return
        
        # Display each book with action buttons
        for book in books:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2.5, 1.5, 1])
                
                with col1:
                    icon = {
                        'PWD': '🏗️',
                        'LGED': '🛣️',
                        'CUSTOM': '✨'
                    }.get(book.get('source_type'), '📋')
                    
                    source_label = book.get('source_type', 'Unknown')
                    if book.get('custom_source') and book.get('custom_source') != 'CUSTOM':
                        source_label = f"{book.get('source_type')} ({book.get('custom_source')})"
                    
                    try:
                        item_count = self.db.get_item_count(book.get('id'))
                    except Exception as e:
                        item_count = 0
                    
                    try:
                        versions = self.db.get_versions_for_book(book.get('id'))
                        version_count = len(versions) if versions else 0
                    except Exception as e:
                        version_count = 0
                    
                    st.markdown(f"**{icon} {book.get('name', 'Unnamed')}**")
                    st.caption(f"📂 {source_label} • {item_count or 0} items • {version_count} versions")
                    
                    if book.get('is_demo'):
                        st.caption("📌 Demo Data")
                    
                    if not book.get('is_active'):
                        st.caption("📦 Inactive")
                
                with col2:
                    book_id = book.get('id')
                    if book_id:
                        if st.button("👁️ View", key=f"view_{book_id}"):
                            st.session_state.view_book_id = book_id
                            st.session_state.view_book_name = book.get('name')
                            st.session_state.page = "rate_viewer"
                            st.rerun()
                        
                        if st.button("✏️ Edit Costs", key=f"edit_{book_id}"):
                            st.session_state.edit_book_id = book_id
                            st.session_state.edit_book_name = book.get('name')
                            st.session_state.edit_book_source = book.get('source_type')
                            st.session_state.page = "company_rate_management"
                            st.session_state.active_tab = 3
                            st.rerun()
                        
                        if self._check_permission('archive') and not book.get('is_archived'):
                            if st.button("🗑️ Archive", key=f"archive_{book_id}", help="Archive this rate book"):
                                if self.db.archive_rate_book(book_id):
                                    self.db.log_audit(
                                        rate_book_id=book_id,
                                        action='ARCHIVE',
                                        field_name='book',
                                        old_value='active',
                                        new_value='archived',
                                        user_id=tenant.get('user_id')
                                    )
                                    st.success(f"✅ Archived rate book: {book.get('name')}")
                                    st.rerun()
                                else:
                                    st.error("Failed to archive rate book")
                
                with col3:
                    book_id = book.get('id')
                    if book_id:
                        if book.get('source_type') == 'CUSTOM':
                            if st.button("📝 Add Item", key=f"add_item_{book_id}"):
                                st.session_state.edit_book_id = book_id
                                st.session_state.edit_book_name = book.get('name')
                                st.session_state.active_tab = 3
                                st.session_state.show_add_item = True
                                st.rerun()
                            
                            if st.button("📥 Import", key=f"import_custom_{book_id}"):
                                st.session_state.import_book_id = book_id
                                st.session_state.active_tab = 5
                                st.rerun()
                        else:
                            # ✅ Resync button - set session state and rerun
                            if st.button("🔄 Resync", key=f"resync_{book_id}"):
                                st.session_state.resync_book_id = book_id
                                st.session_state.resync_source = book.get('source_type')
                                st.session_state.resync_book_name = book.get('name')
                                st.session_state.show_resync_confirmation = True
                                st.rerun()
                
                st.divider()
                
                # ✅ Show resync confirmation if this book is selected
                if (st.session_state.get('show_resync_confirmation') and 
                    st.session_state.get('resync_book_id') == book_id):
                    self._render_resync_confirmation(book_id, book.get('source_type'), book.get('name'))
        
        # ✅ Create New Rate Book section
        if self._check_permission('create'):
            st.divider()
            with st.expander("➕ Create New Rate Book", expanded=False):
                self._render_create_custom_book(tenant)


    def _render_resync_confirmation(self, book_id: int, source_type: str, book_name: str):
        """Render resync confirmation dialog inline"""
        
        st.divider()
        
        # ✅ Use a wider layout with better styling
        st.markdown("""
        <style>
        .resync-container {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
        }
        .resync-title {
            color: #856404;
            font-weight: bold;
            font-size: 1.1em;
        }
        .resync-warning {
            color: #856404;
            margin: 10px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="resync-container">', unsafe_allow_html=True)
            
            st.markdown(f'<div class="resync-title">⚠️ Resync: {book_name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="resync-warning">This will replace all items with the latest master rates. Your custom changes will be lost.</div>', unsafe_allow_html=True)
            
            # ✅ Get available master versions with better layout
            versions = self.db.query("""
                SELECT id, version_name, edition_year, is_active
                FROM rate_versions 
                WHERE source = ? 
                ORDER BY edition_year DESC
            """, (source_type,))
            
            if versions:
                st.markdown("**Select Master Version to Resync From:**")
                
                # ✅ Use columns for better layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    version_options = {}
                    for v in versions:
                        label = f"{v.get('version_name')} ({v.get('edition_year')})"
                        if v.get('is_active'):
                            label += " ✅ Active"
                        version_options[v.get('id')] = label
                    
                    selected_version_id = st.selectbox(
                        "Version",
                        options=list(version_options.keys()),
                        format_func=lambda x: version_options.get(x, "Unknown"),
                        key=f"resync_version_select_{book_id}",
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # ✅ Actions in the same row
                    col2a, col2b = st.columns(2)
                    with col2a:
                        if st.button("🔄 Confirm", type="primary", key=f"confirm_resync_{book_id}", use_container_width=True):
                            tenant = self._get_tenant_info()
                            tenant_id = tenant.get('company_id') or tenant.get('user_id')
                            user_id = tenant.get('user_id')
                            
                            with st.spinner(f"Resyncing {book_name}..."):
                                result = self._resync_with_master(tenant_id, user_id, book_id, source_type, selected_version_id)
                                
                            if result.get('success'):
                                st.success(f"✅ {result.get('message', 'Resync successful!')}")
                                # ✅ Clear session state
                                st.session_state.resync_book_id = None
                                st.session_state.resync_source = None
                                st.session_state.resync_book_name = None
                                st.session_state.show_resync_confirmation = False
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('error', 'Resync failed')}")
                    with col2b:
                        if st.button("Cancel", key=f"cancel_resync_{book_id}", use_container_width=True):
                            # ✅ Clear session state
                            st.session_state.resync_book_id = None
                            st.session_state.resync_source = None
                            st.session_state.resync_book_name = None
                            st.session_state.show_resync_confirmation = False
                            st.rerun()
            else:
                st.error(f"No {source_type} master versions found")
                if st.button("Close", key=f"close_resync_{book_id}"):
                    st.session_state.resync_book_id = None
                    st.session_state.resync_source = None
                    st.session_state.resync_book_name = None
                    st.session_state.show_resync_confirmation = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)


    def _resync_with_master(self, tenant_id: int, user_id: int, book_id: int, source_type: str, version_id: int) -> Dict[str, Any]:
        """Resync company rates with master - using RateCRUD"""
        try:
            print(f"🔄 Resyncing book {book_id} with {source_type} master version {version_id}")
            
            # ✅ Delete existing items for this book
            print(f"🗑️ Deleting existing items for book {book_id}")
            self.db.delete_items_for_book(book_id)
            
            # ✅ Get the current version for this book
            book_version = self.db.query_one("""
                SELECT id FROM tenant_rate_versions 
                WHERE rate_book_id = ? AND is_current = TRUE
            """, (book_id,))
            
            if not book_version:
                return {'success': False, 'error': 'No current version found for this rate book'}
            
            current_version_id = book_version.get('id')
            print(f"✅ Current version: {current_version_id}")
            
            # ✅ Clone fresh master rates
            print(f"📋 Cloning {source_type} master rates...")
            clone_result = self.db.clone_master_to_company(
                book_id=book_id,
                source_type=source_type,
                version_id=version_id,
                user_id=user_id
            )
            
            print(f"✅ Clone result: {clone_result}")
            
            # ✅ Log the resync
            self.db.log_audit(
                rate_book_id=book_id,
                action='RESYNC',
                field_name='all_items',
                old_value='previous_version',
                new_value=f'v{version_id}',
                user_id=user_id
            )
            
            return clone_result
            
        except Exception as e:
            print(f"❌ Resync error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


    # =========================================================================
    # TAB 2: CLONE MASTER RATES
    # =========================================================================
    def _render_clone_master_rates(self, tenant: Dict):
        """Clone master rates to company - using db directly"""
        
        st.subheader("📋 Clone Master Rates")
        
        # ✅ Show appropriate caption
        if tenant.get('company_id'):
            st.caption("Create a company instance of PWD or LGED master rates that you can customize.")
        else:
            st.caption("Create a personal instance of PWD or LGED master rates that you can customize.")
        
        # ✅ Get tenant info
        tenant_id = tenant.get('company_id') or tenant.get('user_id')
        user_id = tenant.get('user_id')
        tenant_type = tenant.get('tenant_type', 'company')
        
        if not tenant_id:
            st.warning("⚠️ No tenant found.")
            return
        
        # ✅ Use self.db directly with correct tenant_id and tenant_type
        existing_books = self.db.get_rate_books_by_tenant(tenant_id, tenant_type)
        existing_types = {book.get('source_type') for book in existing_books if book.get('source_type') in ['PWD', 'LGED']}
        has_pwd = 'PWD' in existing_types
        has_lged = 'LGED' in existing_types
        
        if existing_types:
            st.info("📚 Your current master instances:")
            for book in existing_books:
                if book.get('source_type') in ['PWD', 'LGED']:
                    status = "✅ Active" if book.get('is_active') else "📦 Inactive"
                    item_count = self.db.get_item_count(book.get('id'))
                    st.write(f"  - **{book.get('name')}** ({book.get('source_type')}) - {status} - {item_count or 0} items")
        else:
            st.info("ℹ️ You don't have any master instances yet. Clone one below.")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if has_pwd:
                st.success("✅ PWD rates already cloned")
                book_id = next((b.get('id') for b in existing_books if b.get('source_type') == 'PWD'), None)
                if book_id and st.button("📊 View PWD Rates", use_container_width=True, key="view_pwd_clone"):
                    st.session_state.view_book_id = book_id
                    st.session_state.page = "rate_viewer"
                    st.rerun()
            else:
                if st.button("📋 Clone PWD Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning PWD master rates..."):
                        # ✅ Use tenant_id instead of company_id
                        result = self._clone_master_to_company(tenant_id, user_id, 'PWD', tenant_type)
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")
        
        with col2:
            if has_lged:
                st.success("✅ LGED rates already cloned")
                book_id = next((b.get('id') for b in existing_books if b.get('source_type') == 'LGED'), None)
                if book_id and st.button("📊 View LGED Rates", use_container_width=True, key="view_lged_clone"):
                    st.session_state.view_book_id = book_id
                    st.session_state.page = "rate_viewer"
                    st.rerun()
            else:
                if st.button("📋 Clone LGED Rates", use_container_width=True, type="primary"):
                    with st.spinner("Cloning LGED master rates..."):
                        # ✅ Use tenant_id instead of company_id
                        result = self._clone_master_to_company(tenant_id, user_id, 'LGED', tenant_type)
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Clone successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Clone failed')}")


    def _clone_master_to_company(self, tenant_id: int, user_id: int, source_type: str, tenant_type: str = 'company') -> Dict[str, Any]:
        """Clone master rates to company or individual user - using RateCRUD"""
        try:
            # Get active master version
            version = self.db.get_active_master_version(source_type)
            
            if not version:
                return {'success': False, 'error': f'No active {source_type} master version found'}
            
            version_id = version.get('id')
            
            # ✅ Determine book name based on tenant type
            if tenant_type == 'company':
                book_name = f"My {source_type} Rates"
            else:
                book_name = f"{source_type} Rates (Individual)"
            
            # Create rate book
            book_id = self.db.create_rate_book({
                'tenant_id': tenant_id,
                'tenant_type': tenant_type,  # 'company' or 'user'
                'name': book_name,
                'source_type': source_type,
                'source_version_id': version_id,
                'description': f"{tenant_type.title()} instance of {source_type} master rates",
                'created_by': user_id,
                'is_active': 1
            })
            
            if not book_id:
                return {'success': False, 'error': 'Failed to create rate book'}
            
            # Create initial version
            version_id = self.db.create_rate_version({
                'rate_book_id': book_id,
                'version_name': 'Initial Version',
                'effective_from': datetime.now().date().isoformat(),
                'is_current': True,
                'created_by': user_id
            })
            
            # Clone master rates
            clone_result = self.db.clone_master_to_company(
                book_id=book_id,
                source_type=source_type,
                version_id=version_id,
                user_id=user_id
            )
            
            # Log the clone
            self.db.log_audit(
                rate_book_id=book_id,
                action='CLONE',
                field_name='master_rates',
                old_value='none',
                new_value=f'{source_type} v{version_id}',
                user_id=user_id
            )
            
            return clone_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

        
    # =========================================================================
    # TAB 3: CREATE CUSTOM BOOK
    # =========================================================================
    # modules/company_rate_management.py - Fix _render_create_custom_book

    def _render_create_custom_book(self, tenant: Dict, tab_index: int = 0):
        """Render form to create a new custom rate book"""
        
        st.markdown("#### 📚 Create Custom Rate Book")
        
        # ✅ Show appropriate caption
        if tenant.get('company_id'):
            st.caption("Create a new custom rate book for your company.")
        else:
            st.caption("Create a new custom rate book for your individual account.")
        
        tenant_id = tenant.get('company_id') or tenant.get('user_id')
        user_id = tenant.get('user_id')
        tenant_type = tenant.get('tenant_type', 'company')
        
        if not tenant_id:
            st.error("No tenant found. Please log in again.")
            return
        
        # ✅ Generate a unique form key
        import time
        import random
        form_key = f"create_custom_book_{tenant_id}_{tab_index}_{int(time.time())}_{random.randint(1000, 9999)}"
    
        with st.form(form_key):
            col1, col2 = st.columns(2)
            
            with col1:
                book_name = st.text_input("Book Name*", placeholder="UNDP Rates, RHD Rates, REB Rates, etc.", key=f"book_name_{form_key}")
                custom_source = st.selectbox(
                    "Rate Source Type",
                    options=["CUSTOM", "UNDP", "RHD", "REB", "LGED", "PWD", "Other"],
                    key=f"custom_source_{form_key}"
                )
                
                if custom_source == "Other":
                    custom_source = st.text_input("Specify Source", placeholder="e.g., Local Market Rates", key=f"other_source_{form_key}")
            
            with col2:
                description = st.text_area("Description", placeholder="Description of this custom rate book", key=f"description_{form_key}")
                is_active = st.checkbox("Activate immediately", value=True, key=f"is_active_{form_key}")
                include_template = st.checkbox("Include template items", value=True, help="Add sample items to get started", key=f"include_template_{form_key}")
            
            submitted = st.form_submit_button("🚀 Create Custom Rate Book", use_container_width=True, type="primary")
            
            if submitted:
                if not book_name:
                    st.error("Please enter a book name")
                    return
                
                try:
                    # ✅ Use RateCRUD
                    # ✅ Use RateCRUD with correct tenant_type
                    book_id = self.db.create_rate_book({
                        'tenant_id': tenant_id,
                        'tenant_type': tenant_type,  # ← 'company' or 'user'
                        'name': book_name,
                        'source_type': 'CUSTOM',
                        'custom_source': custom_source if custom_source != "Other" else custom_source,
                        'description': description or f"Custom rates: {book_name}",
                        'is_active': 1 if is_active else 0,
                        'created_by': user_id
                    })
                    
                    if book_id:
                        # ✅ Log CREATE action
                        self.db.log_audit(
                            rate_book_id=book_id,
                            action='CREATE',
                            field_name='book',
                            old_value='none',
                            new_value=book_name,
                            user_id=user_id
                        )
                        
                        # Get version
                        versions = self.db.get_versions_for_book(book_id)
                        version_id = versions[0].get('id') if versions else None
                        
                        if include_template and version_id:
                            self._add_template_items(book_id, version_id, custom_source)
                        
                        st.success(f"✅ Created custom rate book: {book_name} ({custom_source})")
                        st.rerun()
                    else:
                        st.error("❌ Failed to create rate book")
                except Exception as e:
                    st.error(f"Error creating rate book: {e}")

    def _add_template_items(self, book_id: int, version_id: int, prefix: str):
        """Add template items to a custom rate book - using RateCRUD"""
        
        template_items = [
            {'code': f"{prefix}001", 'description': 'General Construction', 'unit': 'job'},
            {'code': f"{prefix}002", 'description': 'Earth Works', 'unit': 'cum'},
            {'code': f"{prefix}003", 'description': 'Concrete Works', 'unit': 'cum'},
            {'code': f"{prefix}004", 'description': 'Reinforcement', 'unit': 'kg'},
            {'code': f"{prefix}005", 'description': 'Finishing Works', 'unit': 'sqm'},
        ]
        
        user_id = st.session_state.get('user_id')
        
        for item in template_items:
            try:
                item_id = self.db.create_rate_item({
                    'rate_book_id': book_id,
                    'item_code': item['code'],
                    'item_description': item['description'],
                    'unit': item['unit'],
                    'is_custom': 1,
                    'created_by': user_id
                })
                
                # Set default pricing
                for level, price in [('AGGRESSIVE', 1000), ('COMPETITIVE', 1200), ('STANDARD', 1500)]:
                    self.db.update_pricing(
                        version_id=version_id,
                        item_id=item_id,
                        pricing_level=level,
                        price=price,
                        user_id=user_id
                    )
            except Exception as e:
                st.warning(f"Could not add item {item['code']}: {e}")
    
    # =========================================================================
    # TAB 4: EDIT RATE BOOK
    # =========================================================================
    
    def _render_edit_rate_book(self):
        """Edit a rate book's items and costing - using RateCRUD"""
        
        st.markdown("### ✏️ Edit Costs: Company Cost Profiles")
        st.caption("Manage your 3 cost levels for each item: Aggressive, Competitive, Standard")
        
        if not self._check_permission('update'):
            st.warning("🔒 You don't have permission to edit rate books.")
            return
        
        tenant = self._get_tenant_info()
        
        col_env, col_sub = st.columns(2)
        with col_env:
            self._show_environment_status()
        with col_sub:
            self._show_subscription_info(tenant)
        
        tenant_id = tenant.get('company_id') or tenant.get('user_id')
        tenant_type = tenant.get('tenant_type', 'company')
        
        # ✅ Get rate books using RateCRUD with correct tenant_id and tenant_type
        books = self.db.get_rate_books_by_tenant(tenant_id, tenant_type)
        
        if not books:
            st.info("📚 No rate books found. Please create or clone one first.")
            return

        with st.container(border=True):
            col_book, col_version, col_info = st.columns([2, 2, 2])
            
            book_options = {b.get('id'): f"{b.get('name', 'Unknown')} ({b.get('source_type', 'Unknown')})" 
                            for b in books}
            
            with col_book:
                selected_book_id = st.selectbox(
                    "📚 Rate Book",
                    options=list(book_options.keys()),
                    format_func=lambda x: book_options.get(x, "Unknown"),
                    key="edit_book_select"
                )
                
            if not selected_book_id:
                return
                
            selected_book = next((b for b in books if b.get('id') == selected_book_id), None)
            
            # ✅ Get versions using RateCRUD
            versions = self.db.get_versions_for_book(selected_book_id)
            
            if not versions:
                st.warning("No versions found for this rate book")
                return
                
            version_options = {}
            current_version = None
            for v in versions:
                label = f"v{v.get('version_number', '?')} - {v.get('version_name', 'Unknown')}"
                if v.get('is_current'):
                    label += " ✅"
                    current_version = v
                version_options[v.get('id')] = label
                
            with col_version:
                default_version_id = current_version.get('id') if current_version else list(version_options.keys())[0]
                selected_version_id = st.selectbox(
                    "📋 Version",
                    options=list(version_options.keys()),
                    format_func=lambda x: version_options.get(x, "Unknown"),
                    index=list(version_options.keys()).index(default_version_id) if default_version_id in version_options else 0,
                    key="edit_version_select"
                )
                
            with col_info:
                items = self.db.get_rate_items_by_book(selected_book_id, selected_version_id)
                st.metric("Total Items in Book", len(items))

        # ✅ Get items using RateCRUD
        try:
            items = self.db.get_rate_items_with_pricing(selected_book_id, selected_version_id)
        except Exception as e:
            st.error(f"Error loading items: {e}")
            return
            
        if not items:
            st.info("📭 No items found in this rate book.")
            if self._check_permission('create'):
                self._render_add_item_form(selected_book_id, selected_version_id)
            return
            
        # Prepare DataFrame
        data = []
        for item in items:
            pricing = item.get('pricing', {})
            
            def get_cost(p, level):
                if not p or not isinstance(p, dict): return 0.0
                return float(p.get(level, {}).get('price', 0.0))

            data.append({
                'ID': item.get('id', ''),
                'Code': item.get('item_code', ''),
                'Description': item.get('item_description', '')[:80],
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if item.get('is_custom') else 'Master',
                'Aggressive': get_cost(pricing, 'AGGRESSIVE'),
                'Competitive': get_cost(pricing, 'COMPETITIVE'),
                'Standard': get_cost(pricing, 'STANDARD'),
                '🗑️': False
            })
            
        df = pd.DataFrame(data)

        # ========== SEARCH, FILTERS, PAGINATION ==========
        with st.container(border=True):
            col_s, col_f, col_p = st.columns([3, 1, 1])
            with col_s:
                search_term = st.text_input("Search", placeholder="🔍 Search code or description...", key="cost_search", label_visibility="collapsed")
            with col_f:
                type_filter = st.selectbox("Type", ["All", "Master", "Custom"], key="type_filter", label_visibility="collapsed")
            with col_p:
                items_per_page = st.selectbox("Per Page", [10, 25, 50, 100], key="cost_items_per_page", label_visibility="collapsed")

        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[
                filtered_df['Code'].str.contains(search_term, case=False, na=False) |
                filtered_df['Description'].str.contains(search_term, case=False, na=False)
            ]
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['Type'] == type_filter]
            
        total_items = len(filtered_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        if 'cost_page_num' not in st.session_state:
            st.session_state.cost_page_num = 1
            
        # Pagination
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("◀ Prev", disabled=st.session_state.cost_page_num <= 1, key="cost_prev", use_container_width=True):
                st.session_state.cost_page_num -= 1
                st.rerun()
        with col_info:
            st.markdown(f"<div style='text-align:center; padding-top:0.5rem;'>Page **{st.session_state.cost_page_num}** of {total_pages} ({total_items} items)</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next ▶", disabled=st.session_state.cost_page_num >= total_pages, key="cost_next", use_container_width=True):
                st.session_state.cost_page_num += 1
                st.rerun()

        start_idx = (st.session_state.cost_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_df.iloc[start_idx:end_idx].copy()

        # ========== DATA EDITOR ==========
        column_config = {
            "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "Code": st.column_config.TextColumn("Code", disabled=True, width="small"),
            "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
            "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
            "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
            "Aggressive": st.column_config.NumberColumn("🟢 Aggressive", format="%.2f", step=100.0),
            "Competitive": st.column_config.NumberColumn("🟡 Competitive", format="%.2f", step=100.0),
            "Standard": st.column_config.NumberColumn("🔴 Standard", format="%.2f", step=100.0),
            "🗑️": st.column_config.CheckboxColumn("Delete", help="Check to delete this item", default=False, width="small")
        }
        
        editor_key = f"cost_editor_{selected_book_id}_{selected_version_id}_{st.session_state.cost_page_num}"
        
        edited_df = st.data_editor(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            key=editor_key,
            num_rows="fixed"
        )

        # ========== SAVE BUTTONS ==========
        st.markdown("---")
        col_save, col_add, col_del, col_summary = st.columns([2, 1, 1, 2])
        
        with col_save:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="bottom_save"):
                self._save_edited_rates(edited_df, items, selected_version_id)
                st.success("✅ Changes saved successfully!")
                st.rerun()
                
        with col_add:
            if self._check_permission('create'):
                is_showing = st.session_state.get('show_add_item', False)
                btn_label = "❌ Cancel Add" if is_showing else "➕ Add Item"
                if st.button(btn_label, use_container_width=True, key="add_item_btn"):
                    st.session_state.show_add_item = not is_showing
                    st.rerun()
                    
        with col_del:
            checked_count = len(edited_df[edited_df['🗑️'] == True])
            if st.button(f"🗑️ Delete ({checked_count})", use_container_width=True, disabled=checked_count == 0, key="del_btn"):
                self._delete_selected_items(edited_df, items)
                st.rerun()

        with col_summary:
            self._render_cost_summary(page_data)

        # ========== ADD ITEM FORM ==========
        if st.session_state.get('show_add_item', False):
            with st.expander("➕ Add New Item", expanded=True):
                self._render_add_item_form(selected_book_id, selected_version_id)
    
    def _render_add_item_form(self, book_id: int, version_id: int):
        """Render form to add a new item - using RateCRUD"""
        
        form_key = f"add_item_form_{book_id}_{version_id}_{int(datetime.now().timestamp())}"
        
        with st.form(form_key):
            st.markdown("#### ➕ Add New Item")
            
            col1, col2 = st.columns(2)
            
            with col1:
                item_code = st.text_input("Item Code*", placeholder="e.g., CUST-001 or 01.1.1", key=f"item_code_{form_key}")
                description = st.text_input("Description*", placeholder="Item description", key=f"description_{form_key}")
                unit = st.selectbox("Unit", ["", "each", "cum", "sqm", "meter", "kg", "hour", "day", "job", "set"], key=f"unit_{form_key}")
            
            with col2:
                aggressive_cost = st.number_input("Aggressive Cost (BDT)", min_value=0.0, value=1000.0, step=100.0, key=f"aggressive_{form_key}")
                competitive_cost = st.number_input("Competitive Cost (BDT)", min_value=0.0, value=1200.0, step=100.0, key=f"competitive_{form_key}")
                standard_cost = st.number_input("Standard Cost (BDT)", min_value=0.0, value=1500.0, step=100.0, key=f"standard_{form_key}")
            
            is_custom = st.checkbox("This is a custom item (not in master rates)", value=True, key=f"is_custom_{form_key}")
            notes = st.text_area("Notes (optional)", placeholder="Any additional information...", key=f"notes_{form_key}")
            
            submitted = st.form_submit_button("➕ Add Item", use_container_width=True, type="primary")
            
            if submitted:
                if not item_code or not description:
                    st.error("Please fill in all required fields")
                    return
                
                tenant = self._get_tenant_info()
                
                # ✅ Use RateCRUD
                item_id = self.db.create_rate_item({
                    'rate_book_id': book_id,
                    'item_code': item_code,
                    'item_description': description,
                    'unit': unit,
                    'is_custom': 1 if is_custom else 0,
                    'created_by': tenant['user_id']
                })
                
                if item_id:
                    # Add costs for each level
                    for level, cost in [('AGGRESSIVE', aggressive_cost), ('COMPETITIVE', competitive_cost), ('STANDARD', standard_cost)]:
                        if cost > 0:
                            self.db.update_pricing(
                                version_id=version_id,
                                item_id=item_id,
                                pricing_level=level,
                                price=round(cost, 2),
                                user_id=tenant['user_id']
                            )
                    
                    st.success(f"✅ Added item: {item_code}")
                    st.session_state.show_add_item = False
                    st.rerun()
                else:
                    st.error("Failed to add item")
    
    def _save_edited_rates(self, edited_df: pd.DataFrame, original_items: List[Dict], version_id: int):
        """Save edited rates - with audit logging"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        items_by_id = {item.get('id'): item for item in original_items if item.get('id')}
        
        for _, row in edited_df.iterrows():
            item_id = row.get('ID')
            
            if not item_id or item_id not in items_by_id:
                continue
            
            item = items_by_id[item_id]
            
            # Update item details
            updates = {}
            if row.get('Description') != item.get('item_description'):
                updates['item_description'] = row.get('Description')
            if row.get('Unit') != item.get('unit', ''):
                updates['unit'] = row.get('Unit')
            
            if updates:
                self.db.update_rate_item(item_id, updates)
                
                # ✅ Log UPDATE action for item
                self.db.log_audit(
                    rate_book_id=item.get('rate_book_id'),
                    rate_item_id=item_id,
                    action='UPDATE',
                    field_name=', '.join(updates.keys()),
                    old_value=str({k: item.get(k) for k in updates.keys()}),
                    new_value=str(updates),
                    user_id=user_id
                )
            
            # Update costs
            for level in ['AGGRESSIVE', 'COMPETITIVE', 'STANDARD']:
                display_name = 'Aggressive' if level == 'AGGRESSIVE' else 'Competitive' if level == 'COMPETITIVE' else 'Standard'
                price = row.get(display_name)
                if price is not None and price != '':
                    try:
                        old_price = None
                        pricing = item.get('pricing', {})
                        if pricing and level in pricing:
                            old_price = pricing[level].get('price')
                        
                        price = float(price) if isinstance(price, str) else float(price)
                        self.db.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=level,
                            price=round(price, 2),
                            user_id=user_id
                        )
                        
                        # ✅ Log UPDATE action for pricing
                        if old_price is not None and old_price != price:
                            self.db.log_audit(
                                rate_book_id=item.get('rate_book_id'),
                                rate_item_id=item_id,
                                action='UPDATE',
                                field_name=f'pricing_{level}',
                                old_value=str(old_price),
                                new_value=str(round(price, 2)),
                                user_id=user_id
                            )
                    except Exception as e:
                        st.warning(f"Failed to update {item.get('item_code')} - {level}: {e}")

    
    def _delete_selected_items(self, edited_df: pd.DataFrame, original_items: List[Dict]):
        """Delete items that were marked for deletion - using RateCRUD"""
        
        original_ids = {item.get('id') for item in original_items if item.get('id')}
        edited_ids = set(edited_df[edited_df['🗑️'] == True]['ID'].tolist())
        
        deleted_ids = original_ids & edited_ids
        
        if not deleted_ids:
            st.info("No items selected for deletion")
            return
        
        if st.warning(f"Delete {len(deleted_ids)} items?"):
            for item_id in deleted_ids:
                self.db.delete_rate_item(item_id)
            
            st.success(f"✅ Deleted {len(deleted_ids)} items")
    
    def _render_cost_summary(self, df: pd.DataFrame):
        """Render cost summary statistics"""
        
        with st.expander("📊 Cost Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            for col, level, color in [(col1, 'Aggressive', '🟢'), (col2, 'Competitive', '🟡'), (col3, 'Standard', '🔴')]:
                values = pd.to_numeric(df.get(level, pd.Series()), errors='coerce').dropna()
                with col:
                    if not values.empty:
                        st.metric(
                            f"{color} {level}",
                            f"BDT {values.mean():,.2f}",
                            f"Min: {values.min():,.2f} | Max: {values.max():,.2f}"
                        )
                    else:
                        st.metric(f"{color} {level}", "No data")
    
    # =========================================================================
    # TAB 5: VERSIONS
    # =========================================================================
    
    def _render_rate_versions(self, tenant: Dict):
        """Manage rate book versions - using RateCRUD"""
        
        st.subheader("📊 Rate Book Versions")
        
        if not self._check_permission('version'):
            st.warning("🔒 You don't have permission to manage versions.")
            return
        
        # ✅ Get rate books using RateCRUD
        books = self.db.get_rate_books_by_tenant(tenant['company_id'])
        
        if not books:
            st.info("No rate books found")
            return
        
        book_options = {b.get('id'): b.get('name') for b in books}
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="version_book_select"
        )
        
        if not selected_book_id:
            return
        
        selected_book = next((b for b in books if b.get('id') == selected_book_id), None)
        
        # ✅ Get versions using RateCRUD
        versions = self.db.get_versions_for_book(selected_book_id)
        
        if not versions:
            st.info("No versions found for this rate book")
            
            if st.button("📦 Create First Version", use_container_width=True):
                version_id = self.db.create_rate_version({
                    'rate_book_id': selected_book_id,
                    'version_name': "Initial Version",
                    'effective_from': datetime.now().date().isoformat(),
                    'is_current': True,
                    'created_by': tenant['user_id']
                })
                if version_id:
                    st.success("✅ First version created!")
                    st.rerun()
                else:
                    st.error("Failed to create version")
            
            return
        
        # Display versions
        st.markdown(f"#### Versions for {selected_book.get('name')}")
        
        for version in versions:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**v{version.get('version_number', '?')}** - {version.get('version_name', 'Unknown')}")
                
                with col2:
                    status = "✅ CURRENT" if version.get('is_current') else "📦 Archived"
                    st.markdown(f"**Status:** {status}")
                
                with col3:
                    effective = version.get('effective_from', 'N/A')
                    st.markdown(f"**Effective:** {effective}")
                
                with col4:
                    if not version.get('is_current'):
                        if st.button("Set Current", key=f"set_current_{version.get('id')}"):
                            if self.db.set_current_version(version.get('id')):
                                # ✅ Log ACTIVATE action - use version.get('version_number')
                                self.db.log_audit(
                                    rate_book_id=selected_book_id,
                                    action='ACTIVATE',
                                    field_name='version',
                                    old_value='inactive',
                                    new_value=f"v{version.get('version_number')}",
                                    user_id=tenant['user_id']
                                )
                                st.success("✅ Current version updated!")
                                st.rerun()
                            else:
                                st.error("Failed to set current version")
        
        # Create new version
        st.markdown("---")
        st.markdown("#### 📦 Create New Version")
        
        with st.form("create_new_version"):
            version_name = st.text_input("Version Name", placeholder="New Version")
            effective_from = st.date_input("Effective From", value=datetime.now().date())
            notes = st.text_area("Release Notes", placeholder="What's new in this version?")
            
            submitted = st.form_submit_button("Create New Version", use_container_width=True)
            
            if submitted:
                if not version_name:
                    st.error("Please enter a version name")
                    return
                
                version_id = self.db.create_rate_version({
                    'rate_book_id': selected_book_id,
                    'version_name': version_name,
                    'effective_from': effective_from.isoformat(),
                    'is_current': True,
                    'notes': notes,
                    'created_by': tenant['user_id']
                })
                
                if version_id:
                    # ✅ Get the newly created version to get version_number
                    new_version = self.db.query_one(
                        "SELECT version_number FROM tenant_rate_versions WHERE id = ?",
                        (version_id,)
                    )
                    version_number = new_version.get('version_number') if new_version else 1
                    
                    # Log CREATE action
                    self.db.log_audit(
                        rate_book_id=selected_book_id,
                        action='CREATE',
                        field_name='version',
                        old_value='none',
                        new_value=f"{version_name} (v{version_number})",
                        user_id=tenant['user_id']
                    )
                    
                    # Also log ACTIVATE since it's set as current
                    self.db.log_audit(
                        rate_book_id=selected_book_id,
                        action='ACTIVATE',
                        field_name='version',
                        old_value='previous',
                        new_value=f"{version_name} (v{version_number})",
                        user_id=tenant['user_id']
                    )
                    st.success("✅ New version created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create version")
    
    # =========================================================================
    # TAB 6: IMPORT/EXPORT
    # =========================================================================
    
    def _render_import_export(self, tenant: Dict):
        """Render import/export UI"""
        
        st.subheader("📥 Import & Export")
        
        company_id = tenant.get('company_id')
        user_id = tenant.get('user_id')
        
        # ✅ Generate unique keys for each uploader
        import time
        timestamp = int(time.time())
        
        tab1, tab2, tab3 = st.tabs([
            "📤 Export Rates",
            "📥 Import Custom Rates",
            "📥 Import Costs"
        ])
        
        with tab1:
            self._render_export_rates_ui(company_id, user_id)
        
        with tab2:
            self._render_import_custom_rates_ui(company_id, user_id)
        
        with tab3:
            self._render_import_costs_ui(company_id, user_id)
    
    def _render_export_rates_ui(self, company_id: int, user_id: int):
        """Export company rate books - using RateCRUD"""
        
        st.markdown("#### 📤 Export Rate Book")
        st.caption("Export your company rate books with all cost levels.")
        
        # ✅ Get rate books using RateCRUD
        books = self.db.get_rate_books_by_tenant(company_id)
        
        if not books:
            st.info("ℹ️ No rate books found to export.")
            return
        
        book_options = {}
        for book in books:
            item_count = self.db.get_item_count(book.get('id'))
            source_label = book.get('source_type', 'Unknown')
            if book.get('custom_source') and book.get('custom_source') != 'CUSTOM':
                source_label = f"{book.get('source_type')} ({book.get('custom_source')})"
            book_options[book.get('id')] = f"{book.get('name')} ({source_label}) - {item_count or 0} items"
        
        selected_book_id = st.selectbox(
            "Select Rate Book to Export",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="export_book_select"
        )
        
        if not selected_book_id:
            return
        
        # ✅ Get version using RateCRUD
        versions = self.db.get_versions_for_book(selected_book_id)
        if not versions:
            st.warning("No version found for this book")
            return
        
        version_id = versions[0].get('id')
        
        # ✅ Get items with pricing using RateCRUD
        items = self.db.get_rate_items_with_pricing(selected_book_id, version_id)
        
        if not items:
            st.info("No items found in this rate book")
            return
        
        # Prepare export data
        export_data = []
        for item in items:
            pricing = item.get('pricing', {})
            
            def get_cost(pricing_data, level):
                if not pricing_data:
                    return ''
                return pricing_data.get(level, {}).get('price', '')
            
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
            try:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Rate Book', index=False)
                    
                    summary_data = {
                        'Parameter': ['Book Name', 'Source Type', 'Total Items', 'Export Date'],
                        'Value': [
                            next((b.get('name') for b in books if b.get('id') == selected_book_id), 'N/A'),
                            next((b.get('source_type') for b in books if b.get('id') == selected_book_id), 'N/A'),
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
        """Import custom rates - using RateCRUD"""
        
        st.markdown("#### 📥 Import Custom Rate Items")
        
        import time
        upload_key = f"import_custom_{company_id}_{user_id}_{int(time.time())}"

        
        uploaded_file = st.file_uploader(
            "Choose file (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            key=upload_key
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
                    elif 'desc' in col:
                        column_map['item_description'] = col
                    elif 'unit' in col:
                        column_map['unit'] = col
                    elif 'aggressive' in col or 'agg' in col:
                        column_map['aggressive'] = col
                    elif 'competitive' in col or 'comp' in col:
                        column_map['competitive'] = col
                    elif 'standard' in col or 'std' in col:
                        column_map['standard'] = col
                
                if 'item_code' not in column_map:
                    st.error("❌ Could not find required column: 'item_code'")
                    return
                
                # Get all rate books
                books = self.db.get_rate_books_by_tenant(company_id)
                book_options = {b.get('id'): f"{b.get('name')} ({b.get('source_type')})" for b in books}
                
                selected_book_id = st.selectbox(
                    "Select Rate Book to import into",
                    options=list(book_options.keys()),
                    format_func=lambda x: book_options.get(x, "Unknown"),
                    key="import_book_select"
                )
                
                if not selected_book_id:
                    return
                
                # Get version
                versions = self.db.get_versions_for_book(selected_book_id)
                if not versions:
                    st.warning("No version found for this book")
                    return
                
                version_id = versions[0].get('id')
                
                # Create standardized dataframe
                std_df = pd.DataFrame()
                std_df['item_code'] = df[column_map['item_code']].astype(str).str.strip()
                std_df['item_description'] = df[column_map.get('item_description', column_map['item_code'])].astype(str).str.strip()
                std_df['unit'] = df[column_map.get('unit', '')] if 'unit' in column_map else ''
                
                for cost_key in ['aggressive', 'competitive', 'standard']:
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
                
                if st.button("📥 Import Items", type="primary", use_container_width=True):
                    with st.spinner(f"Importing {len(std_df)} items..."):
                        result = self._import_custom_items(company_id, user_id, selected_book_id, version_id, std_df)
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Import successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Import failed')}")
                
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    def _import_custom_items(self, company_id: int, user_id: int, book_id: int, version_id: int, df: pd.DataFrame) -> Dict[str, Any]:
        """Import custom items - using RateCRUD"""
        
        try:
            imported = 0
            errors = []
            
            for _, row in df.iterrows():
                try:
                    # Create item
                    item_id = self.db.create_rate_item({
                        'rate_book_id': book_id,
                        'item_code': row.get('item_code'),
                        'item_description': row.get('item_description', ''),
                        'unit': row.get('unit', ''),
                        'is_custom': 1,
                        'created_by': user_id
                    })
                    
                    if item_id:
                        # Add costs
                        for level, cost_key in [('AGGRESSIVE', 'aggressive'), ('COMPETITIVE', 'competitive'), ('STANDARD', 'standard')]:
                            cost = row.get(cost_key)
                            if cost and cost > 0:
                                self.db.update_pricing(
                                    version_id=version_id,
                                    item_id=item_id,
                                    pricing_level=level,
                                    price=float(cost),
                                    user_id=user_id
                                )
                        imported += 1
                    else:
                        errors.append(row.get('item_code', 'Unknown'))
                except Exception as e:
                    errors.append(f"{row.get('item_code')}: {e}")
            
            if errors:
                return {'success': True, 'message': f"Imported {imported} items, {len(errors)} failed", 'errors': errors}
            else:
                return {'success': True, 'message': f"Imported {imported} items successfully"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _render_import_costs_ui(self, company_id: int, user_id: int):
        """Import costs for existing rate book items - using RateCRUD"""
        
        st.markdown("#### 📥 Import Costs")
        st.caption("Import costs for items in an existing rate book.")
        st.info("📌 Format: item_code, aggressive_cost, competitive_cost, standard_cost")
        
        # ✅ Get rate books using RateCRUD
        books = self.db.get_rate_books_by_tenant(company_id)
        
        if not books:
            st.info("ℹ️ No rate books found.")
            return
        
        book_options = {b.get('id'): f"{b.get('name')} ({b.get('source_type')})" for b in books}
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="import_costs_book_select"
        )
        
        if not selected_book_id:
            return
        
        # ✅ Get version using RateCRUD
        versions = self.db.get_versions_for_book(selected_book_id)
        if not versions:
            st.warning("No version found for this book")
            return
        
        version_id = versions[0].get('id')
        
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
                        column_map['aggressive'] = col
                    elif 'competitive' in col or 'comp' in col:
                        column_map['competitive'] = col
                    elif 'standard' in col or 'std' in col:
                        column_map['standard'] = col
                
                if 'item_code' not in column_map:
                    st.error("❌ Could not find required column: 'item_code'")
                    return
                
                # Create standardized dataframe
                std_df = pd.DataFrame()
                std_df['item_code'] = df[column_map['item_code']].astype(str).str.strip()
                
                for cost_key in ['aggressive', 'competitive', 'standard']:
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
                        result = self._import_cost_data(company_id, user_id, selected_book_id, version_id, std_df)
                        if result.get('success'):
                            st.success(f"✅ {result.get('message', 'Import successful!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Import failed')}")
                
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    def _import_cost_data(self, company_id: int, user_id: int, book_id: int, version_id: int, df: pd.DataFrame) -> Dict[str, Any]:
        """Import cost data - using RateCRUD"""
        
        try:
            imported = 0
            errors = []
            
            # Get existing items by code
            items = self.db.get_rate_items_by_book(book_id, version_id)
            items_by_code = {item.get('item_code'): item for item in items if item.get('item_code')}
            
            for _, row in df.iterrows():
                item_code = row.get('item_code')
                if not item_code or item_code not in items_by_code:
                    errors.append(f"Item not found: {item_code}")
                    continue
                
                try:
                    item_id = items_by_code[item_code].get('id')
                    
                    for level, cost_key in [('AGGRESSIVE', 'aggressive'), ('COMPETITIVE', 'competitive'), ('STANDARD', 'standard')]:
                        cost = row.get(cost_key)
                        if cost and cost > 0:
                            self.db.update_pricing(
                                version_id=version_id,
                                item_id=item_id,
                                pricing_level=level,
                                price=float(cost),
                                user_id=user_id
                            )
                    imported += 1
                except Exception as e:
                    errors.append(f"{item_code}: {e}")
            
            if errors:
                return {'success': True, 'message': f"Imported {imported} items, {len(errors)} failed", 'errors': errors}
            else:
                return {'success': True, 'message': f"Imported {imported} items successfully"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # TAB 7: AUDIT HISTORY
    # =========================================================================
    
    def _render_audit_history(self, tenant: Dict):
        """Render audit history - using RateCRUD"""
        
        st.subheader("📋 Audit History")
        st.caption("Track all changes made to your rate books")
        
        company_id = tenant.get('company_id')
        
        if not company_id:
            st.warning("⚠️ No company found.")
            return
        
        # ✅ Get rate books using RateCRUD
        books = self.db.get_rate_books_by_tenant(company_id)
        
        # ========== FILTERS ==========
        col1, col2, col3 = st.columns(3)
        
        with col1:
            book_options = {0: "All Books"}
            for book in books:
                book_options[book.get('id')] = f"{book.get('name')} ({book.get('source_type')})"
            
            selected_book_id = st.selectbox(
                "Filter by Rate Book",
                options=list(book_options.keys()),
                format_func=lambda x: book_options.get(x, "Unknown"),
                key="audit_book_filter"
            )
        
        with col2:
            action_options = ["All Actions", "CREATE", "UPDATE", "DELETE", "CLONE", "RESYNC", "ARCHIVE", "ACTIVATE"]
            selected_action = st.selectbox(
                "Filter by Action",
                options=action_options,
                key="audit_action_filter"
            )
        
        with col3:
            col3a, col3b = st.columns(2)
            with col3a:
                date_from = st.date_input(
                    "From",
                    value=datetime.now() - timedelta(days=30),
                    key="audit_date_from"
                )
            with col3b:
                date_to = st.date_input(
                    "To",
                    value=datetime.now(),
                    key="audit_date_to"
                )
        
        # ========== FETCH AUDIT DATA ==========
        try:
            audit_records = self.db.get_audit_log(
                book_id=selected_book_id if selected_book_id != 0 else None,
                action=selected_action if selected_action != "All Actions" else None,
                date_from=date_from.strftime('%Y-%m-%d') if date_from else None,
                date_to=date_to.strftime('%Y-%m-%d') if date_to else None
            )
        except Exception as e:
            st.error(f"Error loading audit history: {e}")
            return
        
        if not audit_records:
            st.info("ℹ️ No audit records found.")
            return
        
        # Prepare data for display
        audit_data = []
        for record in audit_records:
            action_icons = {
                'CREATE': '🟢',
                'UPDATE': '🟡',
                'DELETE': '🔴',
                'CLONE': '📋',
                'RESYNC': '🔄',
                'ARCHIVE': '🗑️',
                'ACTIVATE': '✅'
            }
            
            icon = action_icons.get(record.get('action'), '📝')
            
            old_val = record.get('old_value') or ''
            new_val = record.get('new_value') or ''
            
            audit_data.append({
                'Date': record.get('created_at'),
                'Book': record.get('book_name') or 'N/A',
                'Action': f"{icon} {record.get('action')}",
                'Field': record.get('field_name') or 'N/A',
                'Old Value': str(old_val)[:50],
                'New Value': str(new_val)[:50],
                'User': record.get('user_name') or 'Unknown'
            })
        
        df = pd.DataFrame(audit_data)
        
        # ========== PAGINATION ==========
        items_per_page = st.selectbox(
            "Items per page",
            options=[10, 25, 50, 100],
            key="audit_items_per_page"
        )
        
        total_items = len(df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        if 'audit_page_num' not in st.session_state:
            st.session_state.audit_page_num = 1
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.audit_page_num <= 1, key="audit_prev"):
                st.session_state.audit_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.audit_page_num} of {total_pages} (Total: {total_items} records)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.audit_page_num >= total_pages, key="audit_next"):
                st.session_state.audit_page_num += 1
                st.rerun()
        
        start_idx = (st.session_state.audit_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = df.iloc[start_idx:end_idx]
        
        # ========== DISPLAY TABLE ==========
        st.dataframe(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "Book": st.column_config.TextColumn("Rate Book", width="medium"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Field": st.column_config.TextColumn("Field", width="small"),
                "Old Value": st.column_config.TextColumn("Old Value", width="medium"),
                "New Value": st.column_config.TextColumn("New Value", width="medium"),
                "User": st.column_config.TextColumn("User", width="small"),
            }
        )
        
        # ========== EXPORT OPTION ==========
        if st.button("📥 Export Audit Log to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
    
    # ========== HELPER METHODS ==========
    
    def _show_environment_status(self):
        """Show environment status banner"""
        company_id = st.session_state.get('company_id')
        if not company_id:
            return
        
        try:
            # ✅ Use RateCRUD
            result = self.db.get_company_status(company_id)
            
            if result:
                mode = result.get('environment_mode') or 'DEMO'
                status = result.get('onboarding_status') or 'pending'
                
                if mode == 'DEMO':
                    st.info("🟢 **Environment: DEMO** - You're using demo data. Switch to production when ready.")
                else:
                    st.success("🔵 **Environment: PRODUCTION** - You're using real production data.")
                
                if status == 'completed':
                    st.success("✅ Onboarding: Completed")
                else:
                    st.warning("⏳ Onboarding: In progress")
        except Exception as e:
            pass
    
    def _show_subscription_info(self, tenant: Dict):
        """Show subscription and permission info"""
        if tenant.get('company_id'):
            try:
                from modules.subscription_manager import SubscriptionManager
                sub_manager = SubscriptionManager(self.db)
                sub = sub_manager.get_company_subscription(tenant['company_id'])
                
                # ✅ Safe access with .get()
                can_edit = sub.get('can_edit_rates', False) if sub else False
                can_create_versions = sub.get('can_create_versions', False) if sub else False
                plan_name = sub.get('plan_name', 'Free') if sub else 'Free'
                
                st.info(f"📊 Plan: **{plan_name}** | "
                    f"✏️ Edit: {'✅' if can_edit else '❌'} | "
                    f"📦 Versions: {'✅' if can_create_versions else '❌'}")
            except Exception as e:
                st.info("📊 Plan: **Free** | ✏️ Edit: ❌ | 📦 Versions: ❌")


# =========================================================================
# CONVENIENCE FUNCTION
# =========================================================================

def render_company_rate_management():
    """Convenience function to render company rate management"""
    manager = CompanyRateManagement()
    manager.render()