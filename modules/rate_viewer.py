# modules/rate_viewer.py - UPDATED to match your session state pattern

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

# Import RBAC functions
from modules.rbac import (
    can_view_system_rates,
    can_view_tenant_rates,
    can_edit_system_rates,
    can_edit_tenant_rates,
    can_export_any_rates,
    can_export_system_rates,
    can_export_tenant_rates,
    can_view_audit_logs,
    render_role_badge
)

class RateViewer:
    """Rate viewer dashboard with sorting, filtering, pagination, and search
    Supports both system master rates and tenant rate books with RBAC integration
    """
    
    def __init__(self, db):
        self.db = db
    
    def _is_user_logged_in(self) -> bool:
        """Check if user is logged in using the same pattern as rate_crud_forms"""
        # Check for user_id in session state (matches rate_crud_forms pattern)
        if 'user_id' in st.session_state and st.session_state.user_id:
            return True
        
        # Also check for user_role (matches rate_crud_forms pattern)
        if 'user_role' in st.session_state and st.session_state.user_role:
            return True
        
        # Fallback: check for user object
        if 'user' in st.session_state and st.session_state.user:
            return True
        
        return False
    
    def _get_current_user(self) -> Dict[str, Any]:
        """Get current user data using the same pattern as rate_crud_forms"""
        user = {}
        
        # Get values from session state (matches rate_crud_forms pattern)
        user['id'] = st.session_state.get('user_id')
        user['username'] = st.session_state.get('username', 'unknown')
        user['role'] = st.session_state.get('user_role', 'viewer')
        user['company_id'] = st.session_state.get('company_id')
        
        # Also try to get from user object if it exists
        if 'user' in st.session_state and st.session_state.user:
            user_obj = st.session_state.user
            if isinstance(user_obj, dict):
                user['id'] = user_obj.get('id', user['id'])
                user['username'] = user_obj.get('username', user['username'])
                user['role'] = user_obj.get('role', user['role'])
                user['company_id'] = user_obj.get('company_id', user['company_id'])
                user['full_name'] = user_obj.get('full_name')
                user['email'] = user_obj.get('email')
        
        return user
    
    def render(self):
        """Main rate viewer interface with RBAC-based access control"""
        
        # ✅ Check if user is logged in using the same pattern as rate_crud_forms
        if not self._is_user_logged_in():
            st.warning("⚠️ Please log in to access rate viewer.")
            if st.button("Go to Login"):
                st.session_state.page = "login"
                st.rerun()
            return
        
        # ✅ Get user data
        user = self._get_current_user()
        
        # Show role badge (uses user_role from session state)
        render_role_badge()
        
        st.markdown("""
        <div class="main-header">
            <h1>📊 Rate Schedule Viewer</h1>
            <p>View, search, filter, and export rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check permissions using RBAC (which reads from session state)
        can_view_system = can_view_system_rates()
        can_view_tenant = can_view_tenant_rates()
        
        # Determine which tabs to show
        tabs_to_show = []
        
        if can_view_system:
            tabs_to_show.append("🏗️ PWD Master")
            tabs_to_show.append("🛣️ LGED Master")
        
        if can_view_tenant:
            tabs_to_show.append("📚 My Rate Books")
        
        if not tabs_to_show:
            st.warning("🔒 You don't have permission to view any rates.")
            return
        
        # Create tabs
        tabs = st.tabs(tabs_to_show)
        tab_index = 0
        
        if "🏗️ PWD Master" in tabs_to_show:
            with tabs[tab_index]:
                self._render_pwd_master()
            tab_index += 1
        
        if "🛣️ LGED Master" in tabs_to_show:
            with tabs[tab_index]:
                self._render_lged_master()
            tab_index += 1
        
        if "📚 My Rate Books" in tabs_to_show:
            with tabs[tab_index]:
                self._render_tenant_rate_books()
            tab_index += 1
    
    # =========================================================================
    # PWD MASTER RATES
    # =========================================================================
    
    def _render_pwd_master(self):
        """Render PWD master rates with RBAC controls"""
        
        st.markdown("### 🏗️ PWD Master Rates")
        
        # Check if user can edit
        can_edit = can_edit_system_rates()
        can_export = can_export_system_rates()
        
        if can_edit:
            st.success("👑 You have edit access to PWD master rates")
        else:
            st.info("🔒 View-only access. Contact System Administrator for edit permissions.")
        
        # Load data
        data = self._load_pwd_data()
        
        if data.empty:
            st.info("No PWD rates found. Please import data first.")
            if can_edit:
                st.button("📥 Import PWD Rates", key="import_pwd")
            return
        
        # Render with filters and display
        self._render_pwd_rates(data, can_edit, can_export)
    
    def _render_pwd_rates(self, data: pd.DataFrame, can_edit: bool, can_export: bool):
        """Render PWD rates with full features"""
        
        # Debug info
        if st.checkbox("Show Debug Info", key="pwd_debug"):
            st.write("Data types:")
            st.write(data.dtypes)
            st.write("Sample data:")
            st.dataframe(data.head())
        
        # Filters section
        st.markdown("#### 🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Chapter filter
            if 'chapter_number' in data.columns:
                chapters = sorted(data['chapter_number'].dropna().unique())
                selected_chapter = st.selectbox("Chapter", ["All"] + list(chapters), key="pwd_chapter")
            else:
                selected_chapter = "All"
        
        with col2:
            # Zone filter
            if 'zone_name' in data.columns:
                zones = data['zone_name'].dropna().unique().tolist()
                selected_zone = st.selectbox("Zone", ["All"] + zones, key="pwd_zone")
            else:
                selected_zone = "All"
        
        with col3:
            # Search by code or description
            search_term = st.text_input("Search", placeholder="Code or description...", key="pwd_search")
        
        with col4:
            # Items per page
            items_per_page = st.selectbox("Items per page", [10, 25, 50, 100, 200], key="pwd_items")
        
        # Apply filters
        filtered_data = data.copy()
        
        if selected_chapter != "All":
            filtered_data = filtered_data[filtered_data['chapter_number'] == selected_chapter]
        
        if selected_zone != "All":
            filtered_data = filtered_data[filtered_data['zone_name'] == selected_zone]
        
        if search_term:
            filtered_data = filtered_data[
                filtered_data['pwd_code'].str.contains(search_term, case=False, na=False) |
                filtered_data['specification_text'].str.contains(search_term, case=False, na=False)
            ]
        
        # Ensure unit_rate is numeric
        filtered_data['unit_rate'] = pd.to_numeric(filtered_data['unit_rate'], errors='coerce')
        
        # Remove rows with NaN rates
        filtered_data = filtered_data.dropna(subset=['unit_rate'])
        
        if filtered_data.empty:
            st.warning("No data found matching the filters")
            return
        
        # Pivot table for better display
        try:
            pivot_data = filtered_data.pivot_table(
                index=['pwd_code', 'specification_text', 'measurement_unit'],
                columns='zone_name',
                values='unit_rate',
                aggfunc='first'
            ).reset_index()
        except Exception as e:
            st.error(f"Pivot error: {e}")
            st.dataframe(filtered_data, use_container_width=True, hide_index=True)
            return
        
        # Rename columns
        pivot_data.columns.name = None
        pivot_data = pivot_data.rename(columns={
            'pwd_code': 'Item Code',
            'specification_text': 'Description',
            'measurement_unit': 'Unit'
        })
        
        # Fill NaN with empty string
        pivot_data = pivot_data.fillna('')
        
        # Format rate columns
        rate_columns = ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']
        for col in rate_columns:
            if col in pivot_data.columns:
                pivot_data[col] = pivot_data[col].apply(lambda x: f"৳{x:,.2f}" if x and x != '' else '')
        
        # Pagination
        total_items = len(pivot_data)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Page navigation
        if 'pwd_page_num' not in st.session_state:
            st.session_state.pwd_page_num = 1
        
        # Reset page if filters change
        current_filter = (selected_chapter, selected_zone, search_term)
        if st.session_state.get('pwd_last_filter') != current_filter:
            st.session_state.pwd_page_num = 1
            st.session_state.pwd_last_filter = current_filter
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.pwd_page_num <= 1, key="pwd_prev"):
                st.session_state.pwd_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.pwd_page_num} of {total_pages} (Total: {total_items} items)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.pwd_page_num >= total_pages, key="pwd_next"):
                st.session_state.pwd_page_num += 1
                st.rerun()
        
        # Slice data for current page
        start_idx = (st.session_state.pwd_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = pivot_data.iloc[start_idx:end_idx]
        
        # Display the dataframe with edit controls if user has permission
        if can_edit:
            # Show editable data editor
            edited_data = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                key=f"pwd_editor_{st.session_state.pwd_page_num}"
            )
            
            # Save changes button
            if st.button("💾 Save PWD Changes", key="save_pwd"):
                self._save_pwd_changes(edited_data, data)
                st.success("✅ PWD rates updated successfully!")
                st.rerun()
        else:
            # Read-only display
            st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # Export options
        if can_export:
            self._render_export_options(pivot_data, "pwd_rates_export")
        
        # Summary statistics
        with st.expander("📊 Summary Statistics", expanded=False):
            self._render_summary_stats(filtered_data, rate_columns)
    
    # =========================================================================
    # LGED MASTER RATES
    # =========================================================================
    
    def _render_lged_master(self):
        """Render LGED master rates with RBAC controls"""
        
        st.markdown("### 🛣️ LGED Master Rates")
        
        # Check if user can edit
        can_edit = can_edit_system_rates()
        can_export = can_export_system_rates()
        
        if can_edit:
            st.success("👑 You have edit access to LGED master rates")
        else:
            st.info("🔒 View-only access. Contact System Administrator for edit permissions.")
        
        # Load data
        data = self._load_lged_data()
        
        if data.empty:
            st.info("No LGED rates found. Please import data first.")
            if can_edit:
                st.button("📥 Import LGED Rates", key="import_lged")
            return
        
        # Render with filters and display
        self._render_lged_rates(data, can_edit, can_export)
    
    def _render_lged_rates(self, data: pd.DataFrame, can_edit: bool, can_export: bool):
        """Render LGED rates with full features"""
        
        # Debug info
        if st.checkbox("Show Debug Info", key="lged_debug"):
            st.write("Data types:")
            st.write(data.dtypes)
            st.write("Sample data:")
            st.dataframe(data.head())
        
        # Ensure unit_rate is numeric
        data['unit_rate'] = pd.to_numeric(data['unit_rate'], errors='coerce')
        data = data.dropna(subset=['unit_rate'])
        
        if data.empty:
            st.warning("No valid rate data found")
            return
        
        # Get unique zone names
        zone_names = data['zone_name'].unique().tolist()
        
        # Filters section
        st.markdown("#### 🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Chapter filter
            if 'chapter_number' in data.columns:
                chapters = sorted(data['chapter_number'].dropna().unique())
                selected_chapter = st.selectbox("Chapter", ["All"] + list(chapters), key="lged_chapter")
            else:
                selected_chapter = "All"
        
        with col2:
            selected_zone = st.selectbox("Zone", ["All"] + zone_names, key="lged_zone")
        
        with col3:
            search_term = st.text_input("Search", placeholder="Code or description...", key="lged_search")
        
        with col4:
            items_per_page = st.selectbox("Items per page", [10, 25, 50, 100, 200], key="lged_items")
        
        # Apply filters
        filtered_data = data.copy()
        
        if selected_chapter != "All":
            filtered_data = filtered_data[filtered_data['chapter_number'] == selected_chapter]
        
        if selected_zone != "All":
            filtered_data = filtered_data[filtered_data['zone_name'] == selected_zone]
        
        if search_term:
            filtered_data = filtered_data[
                filtered_data['code'].str.contains(search_term, case=False, na=False) |
                filtered_data['description'].str.contains(search_term, case=False, na=False)
            ]
        
        if filtered_data.empty:
            st.warning("No data found matching the filters")
            return
        
        # Pivot table
        try:
            pivot_data = filtered_data.pivot_table(
                index=['code', 'description', 'unit'],
                columns='zone_name',
                values='unit_rate',
                aggfunc='first'
            ).reset_index()
        except Exception as e:
            st.error(f"Pivot error: {e}")
            st.dataframe(filtered_data, use_container_width=True, hide_index=True)
            return
        
        # Rename columns
        pivot_data.columns.name = None
        pivot_data = pivot_data.rename(columns={
            'code': 'Item Code',
            'description': 'Description',
            'unit': 'Unit'
        })
        
        # Fill NaN with 0 and format
        for zone in zone_names:
            if zone in pivot_data.columns:
                pivot_data[zone] = pd.to_numeric(pivot_data[zone], errors='coerce').fillna(0)
                pivot_data[zone] = pivot_data[zone].apply(lambda x: f"৳{x:,.2f}" if x > 0 else '')
        
        # Pagination
        total_items = len(pivot_data)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Page navigation
        if 'lged_page_num' not in st.session_state:
            st.session_state.lged_page_num = 1
        
        # Reset page if filters change
        current_filter = (selected_chapter, selected_zone, search_term)
        if st.session_state.get('lged_last_filter') != current_filter:
            st.session_state.lged_page_num = 1
            st.session_state.lged_last_filter = current_filter
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.lged_page_num <= 1, key="lged_prev"):
                st.session_state.lged_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.lged_page_num} of {total_pages} (Total: {total_items} items)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.lged_page_num >= total_pages, key="lged_next"):
                st.session_state.lged_page_num += 1
                st.rerun()
        
        # Slice data for current page
        start_idx = (st.session_state.lged_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = pivot_data.iloc[start_idx:end_idx]
        
        # Display the dataframe with edit controls if user has permission
        if can_edit:
            edited_data = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                key=f"lged_editor_{st.session_state.lged_page_num}"
            )
            
            if st.button("💾 Save LGED Changes", key="save_lged"):
                self._save_lged_changes(edited_data, data)
                st.success("✅ LGED rates updated successfully!")
                st.rerun()
        else:
            st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # Export options
        if can_export:
            self._render_export_options(pivot_data, "lged_rates_export")
    
    # =========================================================================
    # TENANT RATE BOOKS
    # =========================================================================
    
    def _render_tenant_rate_books(self):
        """Render tenant rate books with RBAC controls"""
        
        st.markdown("### 📚 My Rate Books")
        
        # Check if user can edit
        can_edit = can_edit_tenant_rates()
        can_export = can_export_tenant_rates()
        
        # ✅ Get tenant info using the same pattern as rate_crud_forms
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        
        if not user_id:
            st.warning("⚠️ User not logged in. Please log in again.")
            return
        
        tenant_id = company_id or user_id
        tenant_type = 'company' if company_id else 'user'
        
        # Load rate books
        from services.tenant_rate_service import TenantRateService
        service = TenantRateService()
        
        result = service.get_rate_books(tenant_id, tenant_type)
        
        # ✅ FIX: Check if result is a dict and has success key
        if not isinstance(result, dict):
            st.error(f"Unexpected response type: {type(result)}")
            return
        
        if not result.get('success'):
            st.error(result.get('error', 'Failed to load rate books'))
            return
        
        books = result.get('books', [])
        
        # ✅ FIX: Ensure books is a list
        if not isinstance(books, list):
            st.error(f"Unexpected books type: {type(books)}")
            return
        
        if not books:
            st.info("No rate books found. Create a rate book from the Rate Management page.")
            
            # Link to rate management
            if st.button("➕ Go to Rate Management", key="go_to_rate_management"):
                st.session_state.page = "rate_management"
                st.rerun()
            return
        
        # ✅ FIX: Ensure book_options is built correctly
        try:
            book_options = {}
            for b in books:
                if isinstance(b, dict) and 'id' in b and 'name' in b:
                    book_options[b['id']] = b['name']
        except Exception as e:
            st.error(f"Error processing rate books: {e}")
            return
        
        if not book_options:
            st.info("No valid rate books found.")
            return
        
        # Select rate book
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="tenant_rate_book_select"
        )
        
        if not selected_book_id:
            return
        
        # Get selected book
        selected_book = None
        for b in books:
            if isinstance(b, dict) and b.get('id') == selected_book_id:
                selected_book = b
                break
        
        if not selected_book:
            st.error("Selected rate book not found")
            return
        
        # Show book info
        st.markdown(f"""
        **Source:** {selected_book.get('source_type', 'Unknown')}  
        **Status:** {'Active' if selected_book.get('is_active') else 'Inactive'}  
        **Items:** {selected_book.get('item_count', 0)}  
        **Versions:** {selected_book.get('version_count', 0)}
        """)
        
        # Get versions
        try:
            versions = service.repository.get_versions_for_book(selected_book_id)
        except Exception as e:
            st.error(f"Error loading versions: {e}")
            return
        
        # ✅ FIX: Ensure versions is a list
        if not isinstance(versions, list):
            st.error(f"Unexpected versions type: {type(versions)}")
            return
        
        if not versions:
            st.info("No versions found for this rate book")
            return
        
        # Select version (default to current)
        version_options = {}
        current_version = None
        
        for v in versions:
            if isinstance(v, dict):
                v_id = v.get('id')
                if v_id:
                    label = f"v{v.get('version_number', '?')} - {v.get('version_name', 'Unknown')}"
                    if v.get('is_current'):
                        label += " ✅"
                        current_version = v
                    version_options[v_id] = label
        
        if not version_options:
            st.info("No valid versions found")
            return
        
        # Auto-select current version
        if current_version:
            default_version_id = current_version.get('id')
        else:
            default_version_id = list(version_options.keys())[0] if version_options else None
        
        if default_version_id is None:
            st.info("No version selected")
            return
        
        selected_version_id = st.selectbox(
            "Select Version",
            options=list(version_options.keys()),
            format_func=lambda x: version_options.get(x, "Unknown"),
            index=list(version_options.keys()).index(default_version_id) if default_version_id in version_options else 0,
            key="tenant_version_select"
        )
        
        if not selected_version_id:
            return
        
        # Get items with pricing
        try:
            items = service.repository.get_rate_items_by_book(selected_book_id, selected_version_id)
        except Exception as e:
            st.error(f"Error loading items: {e}")
            return
        
        # ✅ FIX: Ensure items is a list
        if not isinstance(items, list):
            st.error(f"Unexpected items type: {type(items)}")
            return
        
        if not items:
            st.info("No items found in this rate book")
            return
        
        # Display items with pricing levels
        data = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pricing = item.get('pricing', {})
            data.append({
                'Item Code': item.get('item_code', ''),
                'Description': item.get('item_description', ''),
                'Unit': item.get('unit', ''),
                'Economy': pricing.get('ECONOMY', {}).get('price', '') if isinstance(pricing.get('ECONOMY'), dict) else pricing.get('ECONOMY', ''),
                'Market': pricing.get('MARKET', {}).get('price', '') if isinstance(pricing.get('MARKET'), dict) else pricing.get('MARKET', ''),
                'Premium': pricing.get('PREMIUM', {}).get('price', '') if isinstance(pricing.get('PREMIUM'), dict) else pricing.get('PREMIUM', ''),
            })
        
        if not data:
            st.info("No valid items found")
            return
        
        df = pd.DataFrame(data)
        
        # Pagination
        items_per_page = st.selectbox("Items per page", [10, 25, 50, 100, 200], key="tenant_items_per_page")
        
        total_items = len(df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Page navigation
        if 'tenant_page_num' not in st.session_state:
            st.session_state.tenant_page_num = 1
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.tenant_page_num <= 1, key="tenant_prev"):
                st.session_state.tenant_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.tenant_page_num} of {total_pages} (Total: {total_items} items)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.tenant_page_num >= total_pages, key="tenant_next"):
                st.session_state.tenant_page_num += 1
                st.rerun()
        
        # Slice data
        start_idx = (st.session_state.tenant_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = df.iloc[start_idx:end_idx]
        
        # Display with edit controls
        if can_edit and not selected_book.get('is_archived', False):
            edited_df = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Item Code": st.column_config.TextColumn("Item Code", width="small"),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Unit": st.column_config.TextColumn("Unit", width="small"),
                    "Economy": st.column_config.NumberColumn("Economy (BDT)", format="%.2f"),
                    "Market": st.column_config.NumberColumn("Market (BDT)", format="%.2f"),
                    "Premium": st.column_config.NumberColumn("Premium (BDT)", format="%.2f"),
                },
                key=f"tenant_editor_{selected_book_id}_{selected_version_id}_{st.session_state.tenant_page_num}"
            )
            
            if st.button("💾 Save Changes", key="save_tenant_changes"):
                self._save_tenant_pricing_changes(edited_df, items, selected_version_id)
                st.success("✅ Pricing updated successfully!")
                st.rerun()
        else:
            st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # Export
        if can_export:
            self._render_export_options(df, f"rate_book_{selected_book.get('name', 'unknown')}")

    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _load_pwd_data(self) -> pd.DataFrame:
        """Load PWD data from database"""
        try:
            conn = self.db.get_connection()
            query = """
                SELECT 
                    c.pwd_code,
                    c.description as specification_text,
                    c.unit as measurement_unit,
                    p.chapter_number,
                    r.zone_name,
                    r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_parents p ON c.parent_code = p.pwd_code
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                ORDER BY c.pwd_code, r.zone_name
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Clean up
            df = df.dropna(subset=['pwd_code'])
            df['unit_rate'] = pd.to_numeric(df['unit_rate'], errors='coerce')
            
            return df
        except Exception as e:
            st.error(f"Error loading PWD data: {e}")
            return pd.DataFrame()
    
    def _load_lged_data(self) -> pd.DataFrame:
        """Load LGED data from database"""
        try:
            conn = self.db.get_connection()
            
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lged_children'")
            if not cursor.fetchone():
                return pd.DataFrame()
            
            query = """
                SELECT 
                    c.code,
                    c.description,
                    c.unit,
                    c.parent_code,
                    r.zone_name,
                    r.unit_rate
                FROM lged_children c
                LEFT JOIN lged_zone_rates r ON c.id = r.child_id
                ORDER BY c.code, r.zone_name
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return df
            
            # Extract chapter number from parent_code
            df['chapter_number'] = df['parent_code'].apply(
                lambda x: str(x).split('.')[0] if x and '.' in str(x) else ''
            )
            
            # Clean up
            df = df.dropna(subset=['code'])
            df['unit_rate'] = pd.to_numeric(df['unit_rate'], errors='coerce')
            
            return df
        except Exception as e:
            st.error(f"Error loading LGED data: {e}")
            return pd.DataFrame()
    
    def _save_pwd_changes(self, edited_data: pd.DataFrame, original_data: pd.DataFrame):
        """Save PWD rate changes"""
        # Implementation would update the database
        st.info("PWD save functionality implementation")
    
    def _save_lged_changes(self, edited_data: pd.DataFrame, original_data: pd.DataFrame):
        """Save LGED rate changes"""
        # Implementation would update the database
        st.info("LGED save functionality implementation")
    
    def _save_tenant_pricing_changes(
        self, 
        edited_data: pd.DataFrame, 
        original_items: List[Dict], 
        version_id: int
    ):
        """Save tenant pricing changes"""
        from services.tenant_rate_service import TenantRateService
        service = TenantRateService()
        
        # ✅ Get user ID using the same pattern as rate_crud_forms
        user_id = st.session_state.get('user_id')
        
        if not user_id:
            st.error("⚠️ User not logged in. Cannot save changes.")
            return
        
        # Map items by code
        items_by_code = {item['item_code']: item for item in original_items}
        
        for _, row in edited_data.iterrows():
            item_code = row.get('Item Code')
            if not item_code or item_code not in items_by_code:
                continue
            
            item = items_by_code[item_code]
            item_id = item['id']
            
            # Update each pricing level
            for level in ['Economy', 'Market', 'Premium']:
                price = row.get(level)
                if price is not None and price != '':
                    try:
                        service.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=level.upper(),
                            price=float(price),
                            user_id=user_id
                        )
                    except Exception as e:
                        st.warning(f"Failed to update {item_code} - {level}: {e}")
    
    def _render_export_options(self, data: pd.DataFrame, base_filename: str):
        """Render export options"""
        st.markdown("#### 📥 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = data.to_csv(index=False)
            st.download_button(
                "📥 Download as CSV",
                csv,
                f"{base_filename}.csv",
                "text/csv",
                use_container_width=True
            )
    
    def _render_summary_stats(self, data: pd.DataFrame, zones: List[str]):
        """Render summary statistics"""
        stats_data = []
        for zone in zones:
            if zone in data['zone_name'].values:
                zone_data = data[data['zone_name'] == zone]['unit_rate']
                if not zone_data.empty:
                    stats_data.append({
                        'Zone': zone,
                        'Min Rate': f"৳{zone_data.min():,.2f}",
                        'Max Rate': f"৳{zone_data.max():,.2f}",
                        'Avg Rate': f"৳{zone_data.mean():,.2f}",
                        'Count': len(zone_data)
                    })
        
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)


# =========================================================================
# CONVENIENCE FUNCTION - UPDATED
# =========================================================================

def render_rate_viewer(db):
    """Convenience function to render rate viewer"""
    # Create instance and render
    viewer = RateViewer(db)
    viewer.render()