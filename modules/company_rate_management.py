# modules/company_rate_management.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta  # ✅ Make sure timedelta is imported

import json
import io
from typing import Optional, Dict, Any, List

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

from services.tenant_rate_service import TenantRateService


class CompanyRateManagement:
    """
    Company-level rate management module.
    Allows company admins to:
    - Clone master rates (PWD/LGED) to their company
    - Create custom rate books
    - Edit company rates
    - Manage versions
    - Create custom rate items
    """
    
    def __init__(self, db):
        self.db = db
        self.service = TenantRateService()
    
    def _get_tenant_info(self):
        """Get current tenant info from session state"""
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        user_role = st.session_state.get('user_role', 'viewer')
        username = st.session_state.get('username', 'unknown')
        
        return {
            'user_id': user_id,
            'company_id': company_id,
            'tenant_id': company_id or user_id,
            'tenant_type': 'company' if company_id else 'user',
            'user_role': user_role,
            'username': username
        }
    
    def _check_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        tenant = self._get_tenant_info()
        role = tenant['user_role']
        
        # System admins and admins have full access
        if role in ['system_admin', 'admin']:
            return True
        
        # Company admins and managers can manage rates
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
            <h1>🏢 Company Rate Management</h1>
            <p>Manage your company's rate books, clone master rates, and create custom rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        self._show_environment_status()
        
        tenant = self._get_tenant_info()
        
        if not tenant.get('company_id'):
            st.warning("⚠️ No company found. Please contact support.")
            return
        
        self._show_subscription_info(tenant)
        
        # ✅ Get active tab from session state
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
        
        # ✅ Set active tab
        for i, tab in enumerate(tabs):
            if i == active_tab:
                with tab:
                    self._render_tab_content(i, tenant)
            else:
                with tab:
                    self._render_tab_content(i, tenant)

    
    def _render_tab_content(self, tab_index: int, tenant: Dict):
        """Render content for each tab"""
        
        if tab_index == 0:
            self._render_my_rate_books(tenant)
        elif tab_index == 1:
            self._render_clone_master_rates(tenant)
        elif tab_index == 2:
             self._render_create_custom_book(tenant, tab_index=tab_index)
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
    
    # modules/company_rate_management.py - Add this method
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
        """Import custom rates with unique form keys"""
        
        st.markdown("#### 📥 Import Custom Rate Items")
        
        # ✅ Generate unique key
        import time
        upload_key = f"import_custom_{company_id}_{int(time.time())}"
        
        uploaded_file = st.file_uploader(
            "Choose file (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            key=upload_key
        )
    def _render_audit_history(self, tenant: Dict):
        """Render audit history for rate books"""
        
        st.subheader("📋 Audit History")
        st.caption("Track all changes made to your rate books")
        
        company_id = tenant.get('company_id')
        
        if not company_id:
            st.warning("⚠️ No company found.")
            return
        
        # Get all rate books for filter
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, source_type
            FROM tenant_rate_books
            WHERE tenant_id = ? AND is_archived = 0
            ORDER BY name
        """, (company_id,))
        
        books = cursor.fetchall()
        conn.close()
        
        # ============================================
        # ✅ FILTERS
        # ============================================
        col1, col2, col3 = st.columns(3)
        
        with col1:
            book_options = {0: "All Books"}
            for book in books:
                book_options[book['id']] = f"{book['name']} ({book['source_type']})"
            
            selected_book_id = st.selectbox(
                "Filter by Rate Book",
                options=list(book_options.keys()),
                format_func=lambda x: book_options.get(x, "Unknown"),
                key="audit_book_filter"
            )
        
        with col2:
            # Action filter
            action_options = ["All Actions", "CREATE", "UPDATE", "DELETE", "CLONE", "RESYNC", "ARCHIVE", "ACTIVATE"]
            selected_action = st.selectbox(
                "Filter by Action",
                options=action_options,
                key="audit_action_filter"
            )
        
        with col3:
            # Date range
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
        
        # ============================================
        # ✅ FETCH AUDIT DATA
        # ============================================
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    tra.id,
                    tra.rate_book_id,
                    tra.action,
                    tra.field_name,
                    tra.old_value,
                    tra.new_value,
                    tra.user_id,
                    tra.created_at,
                    u.username,
                    u.full_name,
                    u.role as user_role,
                    rb.name as book_name,
                    rb.source_type as book_source
                FROM tenant_rate_audit tra
                LEFT JOIN users u ON tra.user_id = u.id
                LEFT JOIN tenant_rate_books rb ON tra.rate_book_id = rb.id
                WHERE rb.tenant_id = ?
            """
            params = [company_id]
            
            if selected_book_id and selected_book_id != 0:
                query += " AND tra.rate_book_id = ?"
                params.append(selected_book_id)
            
            if selected_action and selected_action != "All Actions":
                query += " AND tra.action = ?"
                params.append(selected_action)
            
            if date_from:
                query += " AND DATE(tra.created_at) >= ?"
                params.append(date_from.strftime('%Y-%m-%d'))
            
            if date_to:
                query += " AND DATE(tra.created_at) <= ?"
                params.append(date_to.strftime('%Y-%m-%d'))
            
            query += " ORDER BY tra.created_at DESC LIMIT 500"
            
            cursor.execute(query, params)
            audit_records = cursor.fetchall()
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading audit history: {e}")
            return
        
        # ============================================
        # ✅ DISPLAY AUDIT RECORDS
        # ============================================
        if not audit_records:
            st.info("ℹ️ No audit records found.")
            return
        
        # Prepare data for display
        audit_data = []
        for record in audit_records:
            # Format action with icon
            action_icons = {
                'CREATE': '🟢',
                'UPDATE': '🟡',
                'DELETE': '🔴',
                'CLONE': '📋',
                'RESYNC': '🔄',
                'ARCHIVE': '🗑️',
                'ACTIVATE': '✅'
            }
            
            icon = action_icons.get(record['action'], '📝')
            
            # Format old/new values
            old_val = record['old_value'] or ''
            new_val = record['new_value'] or ''
            
            if len(str(old_val)) > 50:
                old_val = str(old_val)[:50] + '...'
            if len(str(new_val)) > 50:
                new_val = str(new_val)[:50] + '...'
            
            audit_data.append({
                'Date': record['created_at'],
                'Book': record['book_name'] or 'N/A',
                'Source': record['book_source'] or '',
                'Action': f"{icon} {record['action']}",
                'Field': record['field_name'] or 'N/A',
                'Old Value': old_val,
                'New Value': new_val,
                'User': record['full_name'] or record['username'] or 'Unknown',
                'Role': record['user_role'] or 'viewer'
            })
        
        df = pd.DataFrame(audit_data)
        
        # ============================================
        # ✅ PAGINATION
        # ============================================
        items_per_page = st.selectbox(
            "Items per page",
            options=[10, 25, 50, 100],
            key="audit_items_per_page"
        )
        
        total_items = len(df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Page navigation
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
        
        # Slice data
        start_idx = (st.session_state.audit_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = df.iloc[start_idx:end_idx]
        
        # ============================================
        # ✅ DISPLAY TABLE
        # ============================================
        st.dataframe(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "Book": st.column_config.TextColumn("Rate Book", width="medium"),
                "Source": st.column_config.TextColumn("Source", width="small"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Field": st.column_config.TextColumn("Field", width="small"),
                "Old Value": st.column_config.TextColumn("Old Value", width="medium"),
                "New Value": st.column_config.TextColumn("New Value", width="medium"),
                "User": st.column_config.TextColumn("User", width="small"),
                "Role": st.column_config.TextColumn("Role", width="small"),
            }
        )
        
        # ============================================
        # ✅ EXPORT OPTION
        # ============================================
        if st.button("📥 Export Audit Log to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        # ============================================
        # ✅ SUMMARY STATISTICS
        # ============================================
        with st.expander("📊 Audit Summary", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", len(df))
            
            with col2:
                unique_books = df['Book'].nunique() if not df.empty else 0
                st.metric("Rate Books Affected", unique_books)
            
            with col3:
                unique_users = df['User'].nunique() if not df.empty else 0
                st.metric("Users", unique_users)
            
            with col4:
                # Action breakdown
                if not df.empty:
                    action_counts = df['Action'].value_counts().to_dict()
                    most_common = max(action_counts, key=action_counts.get) if action_counts else 'N/A'
                    st.metric("Most Common Action", most_common)
            
            # Action breakdown chart
            if not df.empty:
                st.markdown("#### Action Breakdown")
                action_data = df['Action'].value_counts().reset_index()
                action_data.columns = ['Action', 'Count']
                st.bar_chart(action_data.set_index('Action'))

    def _render_clone_master_rates(self, tenant: Dict):
        """Clone master rates to company"""
        
        st.subheader("📋 Clone Master Rates")
        st.caption("Create a company instance of PWD or LGED master rates that you can customize.")
        
        company_id = tenant.get('company_id')
        user_id = tenant.get('user_id')
        
        if not company_id:
            st.warning("⚠️ No company found.")
            return
        
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
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if has_pwd:
                st.success("✅ PWD rates already cloned")
                if st.button("📊 View PWD Rates", use_container_width=True, key="view_pwd_clone"):
                    st.session_state.view_book_id = next((b['id'] for b in existing_books if b['source_type'] == 'PWD'), None)
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
                    st.session_state.view_book_id = next((b['id'] for b in existing_books if b['source_type'] == 'LGED'), None)
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
            
            # Log the clone
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tenant_rate_audit 
                (rate_book_id, action, field_name, old_value, new_value, user_id)
                VALUES (?, 'CLONE', 'master_rates', 'none', ?, ?)
            """, (result['book_id'], f'{source_type} v{version_id}', user_id))
            conn.commit()
            conn.close()
            
            return clone_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def _show_environment_status(self):
        """Show environment status banner"""
        company_id = st.session_state.get('company_id')
        if not company_id:
            return
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT environment_mode, onboarding_status
                FROM companies WHERE id = ?
            """, (company_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
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
            pass

    
    def _render_my_rate_books(self, tenant: Dict):
        """Render My Rate Books with View and Edit capabilities"""
        
        st.subheader("📚 My Rate Books")
        st.caption("View and manage your company's rate books")
        
        company_id = tenant.get('company_id')
        
        if not company_id:
            st.warning("⚠️ No company found.")
            return
        
        # Fetch all rate books
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
                    }.get(book['source_type'], '📋')
                    
                    source_label = book['source_type']
                    if book['custom_source'] and book['custom_source'] != 'CUSTOM':
                        source_label = f"{book['source_type']} ({book['custom_source']})"
                    
                    st.markdown(f"**{icon} {book['name']}**")
                    st.caption(f"{source_label} - {book['item_count'] or 0} items")
                    
                    if book['is_demo']:
                        st.caption("📌 Demo Data")
                    
                    if not book['is_active']:
                        st.caption("📦 Inactive")
                
                with col2:
                    # View button
                    if st.button("👁️ View", key=f"view_{book['id']}"):
                        st.session_state.view_book_id = book['id']
                        st.session_state.view_book_name = book['name']
                        st.session_state.page = "rate_viewer"
                        st.rerun()
                    
                    # Edit Costs button (for all books)
                    if st.button("✏️ Edit Costs", key=f"edit_{book['id']}"):
                        st.session_state.edit_book_id = book['id']
                        st.session_state.edit_book_name = book['name']
                        st.session_state.edit_book_source = book['source_type']
                        st.session_state.page = "company_rate_management"
                        st.session_state.active_tab = 3
                        st.rerun()
                
                with col3:
                    if book['source_type'] == 'CUSTOM':
                        if st.button("📝 Add Item", key=f"add_item_{book['id']}"):
                            st.session_state.edit_book_id = book['id']
                            st.session_state.edit_book_name = book['name']
                            st.session_state.active_tab = 3
                            st.session_state.show_add_item = True
                            st.rerun()
                        if st.button("📥 Import", key=f"import_custom_{book['id']}"):
                            st.session_state.import_book_id = book['id']
                            st.session_state.active_tab = 5
                            st.rerun()
                    else:
                        if st.button("🔄 Resync", key=f"resync_{book['id']}"):
                            st.session_state.resync_book_id = book['id']
                            st.session_state.resync_source = book['source_type']
                            st.session_state.resync_book_name = book['name']
                            self._show_resync_confirmation(book['id'], book['source_type'], book['name'])
                            st.rerun()
        
        # ✅ FIX: Pass tenant dict to _render_create_custom_book
        if self._check_permission('create'):
            st.divider()
            with st.expander("➕ Create New Rate Book", expanded=False):
                self._render_create_custom_book(tenant)  # ✅ Pass tenant dict

    def _show_resync_confirmation(self, book_id: int, source_type: str, book_name: str):
        """Show resync confirmation dialog"""
        
        st.warning(f"⚠️ You are about to resync **{book_name}** ({source_type})")
        st.caption("This will replace all items with the latest master rates. Your custom changes will be lost.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Confirm Resync", type="primary"):
                tenant = self._get_tenant_info()
                result = self._resync_with_master(tenant['company_id'], tenant['user_id'], book_id, source_type)
                if result.get('success'):
                    st.success(f"✅ {result.get('message', 'Resync successful!')}")
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('error', 'Resync failed')}")
        with col2:
            if st.button("Cancel"):
                st.session_state.resync_book_id = None
                st.rerun()

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

    def _show_subscription_info(self, tenant: Dict):
        """Show subscription and permission info"""
        if tenant.get('company_id'):
            try:
                from modules.subscription_manager import SubscriptionManager
                sub_manager = SubscriptionManager(self.db)
                sub = sub_manager.get_company_subscription(tenant['company_id'])
                
                can_edit = sub.get('can_edit_rates', False)
                can_create_versions = sub.get('can_create_versions', False)
                
                st.info(f"📊 Plan: **{sub.get('plan_name', 'Free')}** | "
                    f"✏️ Edit: {'✅' if can_edit else '❌'} | "
                    f"📦 Versions: {'✅' if can_create_versions else '❌'}")
            except:
                pass

    def _render_rate_books(self):
        """Display all rate books for the current tenant"""
        
        st.subheader("📚 My Rate Books")
        
        tenant = self._get_tenant_info()
        
        result = self.service.get_rate_books(
            tenant['tenant_id'],
            tenant['tenant_type'],
            include_archived=False
        )
        
        if not result.get('success'):
            st.error(result.get('error', 'Failed to load rate books'))
            return
        
        books = result.get('books', [])
        
        if not books:
            st.info("No rate books found. Clone master rates or create a custom rate book.")
            return
        
        # Display rate books in a grid
        cols = st.columns(2)
        
        for idx, book in enumerate(books):
            col = cols[idx % 2]
            
            with col:
                with st.container(border=True):
                    # Book header
                    status_icon = "📦" if book.get('is_archived') else "📖"
                    source_badge = {
                        'PWD': '🏗️',
                        'LGED': '🛣️',
                        'CUSTOM': '✨'
                    }.get(book.get('source_type'), '📋')
                    
                    st.markdown(f"### {status_icon} {book['name']}")
                    st.markdown(f"**Source:** {source_badge} {book.get('source_type', 'Unknown')}")
                    st.markdown(f"**Items:** {book.get('item_count', 0)}")
                    st.markdown(f"**Versions:** {book.get('version_count', 0)}")
                    st.markdown(f"**Status:** {'✅ Active' if book.get('is_active') else '❌ Inactive'}")
                    
                    if book.get('description'):
                        st.caption(f"📝 {book['description']}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("👁️ View", key=f"view_{book['id']}"):
                            st.session_state.view_book_id = book['id']
                            st.rerun()
                    
                    with col2:
                        if self._check_permission('update') and not book.get('is_archived'):
                            if st.button("✏️ Edit", key=f"edit_{book['id']}"):
                                st.session_state.edit_book_id = book['id']
                                st.rerun()
                    
                    with col3:
                        if self._check_permission('archive') and not book.get('is_archived'):
                            if st.button("🗑️ Archive", key=f"archive_{book['id']}"):
                                result = self.service.repository.archive_rate_book(book['id'])
                                if result:
                                    st.success(f"Archived {book['name']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to archive")
    
    # =========================================================================
    # TAB 2: CLONE MASTER RATES
    # =========================================================================
    
    def _render_clone_master(self, tenant: Dict):
        """Clone PWD or LGED master rates to company"""
        
        st.subheader("📋 Clone Master Rates")
        
        if not self._check_permission('clone'):
            st.warning("🔒 You don't have permission to clone master rates.")
            return
        
        tenant = self._get_tenant_info()
        
        st.info("""
        Cloning master rates creates a copy of PWD or LGED master rates 
        that your company can then customize. The master rates remain unchanged.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Select source type
            source_type = st.radio(
                "Select Master Source",
                options=["PWD", "LGED"],
                horizontal=True,
                key="clone_source"
            )
            
            # Get available master versions
            conn = self.db.get_connection()
            versions_df = pd.read_sql_query("""
                SELECT id, version_name, edition_year, is_active
                FROM rate_versions 
                WHERE source = ?
                ORDER BY edition_year DESC
            """, conn, params=(source_type,))
            conn.close()
            
            if versions_df.empty:
                st.warning(f"No {source_type} master versions found. Please import master rates first.")
                return
            
            version_options = {}
            for _, row in versions_df.iterrows():
                label = f"{row['version_name']} ({row['edition_year']})"
                if row['is_active']:
                    label += " ✅"
                version_options[row['id']] = label
            
            selected_version = st.selectbox(
                "Select Master Version",
                options=list(version_options.keys()),
                format_func=lambda x: version_options.get(x, "Unknown"),
                key="clone_version"
            )
        
        with col2:
            # Rate book name
            book_name = st.text_input(
                "Rate Book Name",
                placeholder=f"My {source_type} Rates",
                key="clone_book_name"
            )
            
            description = st.text_area(
                "Description",
                placeholder=f"Company copy of {source_type} master rates",
                key="clone_description"
            )
            
            # Filters (optional)
            st.markdown("##### Optional Filters")
            
            filter_chapter = st.text_input(
                "Filter by Chapter",
                placeholder="Leave empty for all chapters",
                key="clone_filter_chapter"
            )
            
            filter_year = st.number_input(
                "Filter by Edition Year",
                min_value=2020,
                max_value=2030,
                value=2022,
                step=1,
                key="clone_filter_year",
                help="Select edition year to filter by"
            )
        
        # Clone button
        if st.button("🚀 Clone Master Rates", key="clone_master_btn", use_container_width=True):
            if not book_name:
                st.error("Please enter a rate book name")
                return
            
            # Create the rate book
            result = self.service.create_rate_book(
                tenant_id=tenant['tenant_id'],
                tenant_type=tenant['tenant_type'],
                name=book_name,
                source_type=source_type,
                description=description,
                source_version_id=selected_version,
                created_by=tenant['user_id']
            )
            
            if not result.get('success'):
                st.error(result.get('error', 'Failed to create rate book'))
                return
            
            book_id = result['book_id']
            version_id = result['version_id']
            
            # Clone the master rates
            filters = {}
            if filter_chapter:
                filters['chapter_number'] = filter_chapter
            if filter_year > 0:
                filters['edition_year'] = filter_year
            
            clone_result = self.service.clone_master_rates(
                book_id=book_id,
                source_type=source_type,
                version_id=version_id,
                filters=filters if filters else None,
                user_id=tenant['user_id']
            )
            
            if clone_result.get('success'):
                st.success(f"✅ Successfully created rate book '{book_name}' with {clone_result.get('items_created', 0)} items")
                st.info(f"💡 You can now edit the rates in the 'Edit Rate Book' tab.")
            else:
                st.error(clone_result.get('error', 'Clone failed'))
    
    # =========================================================================
    # TAB 3: CREATE CUSTOM RATE BOOK
    # =========================================================================
    
    def _render_create_custom_book(self, tenant: Dict, tab_index: int = 0):
        """Render form to create a new custom rate book"""
        
        st.markdown("#### 📚 Create Custom Rate Book")
        st.caption("Create a new custom rate book with your own items and costs.")
        
        company_id = tenant.get('company_id')
        user_id = tenant.get('user_id')
        
        # ✅ Generate unique form key with timestamp
        import time
        form_key = f"create_custom_book_{company_id}_{tab_index}"

        
        with st.form(form_key):
            col1, col2 = st.columns(2)
            
            with col1:
                book_name = st.text_input("Book Name*", placeholder="UNDP Rates, RHD Rates, REB Rates, etc.", key=f"book_name_{form_key}")
                custom_source = st.selectbox(
                    "Rate Source Type",
                    options=["CUSTOM", "UNDP", "RHD", "REB", "LGED", "PWD", "Other"],
                    help="Select the source of these custom rates",
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


    
    def _add_template_items(self, book_id: int, version_id: int, prefix: str, default_unit: str):
        """Add template items to a custom rate book"""
        
        template_items = [
            {'code': f"{prefix}001", 'description': 'General Construction', 'unit': default_unit or 'job'},
            {'code': f"{prefix}002", 'description': 'Earth Works', 'unit': default_unit or 'cum'},
            {'code': f"{prefix}003", 'description': 'Concrete Works', 'unit': default_unit or 'cum'},
            {'code': f"{prefix}004", 'description': 'Reinforcement', 'unit': default_unit or 'kg'},
            {'code': f"{prefix}005", 'description': 'Finishing Works', 'unit': default_unit or 'sqm'},
            {'code': f"{prefix}006", 'description': 'Electrical Works', 'unit': default_unit or 'job'},
            {'code': f"{prefix}007", 'description': 'Plumbing Works', 'unit': default_unit or 'job'},
            {'code': f"{prefix}008", 'description': 'HVAC Works', 'unit': default_unit or 'job'},
            {'code': f"{prefix}009", 'description': 'Fire Protection', 'unit': default_unit or 'job'},
            {'code': f"{prefix}010", 'description': 'Landscaping', 'unit': default_unit or 'sqm'},
        ]
        
        user_id = st.session_state.get('user_id')
        
        for item in template_items:
            try:
                item_id = self.service.repository.create_rate_item({
                    'rate_book_id': book_id,
                    'item_code': item['code'],
                    'item_description': item['description'],
                    'unit': item['unit'],
                    'is_custom': 1,
                    'created_by': user_id,
                    'skip_pricing': True  # We'll add pricing separately
                })
                
                # Set default pricing
                for level, price in [('ECONOMY', 1000), ('MARKET', 1200), ('PREMIUM', 1500)]:
                    self.service.repository.update_pricing(
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
    
    def _get_base_rate(self, item: Dict) -> float:
        """
        Get base rate for an item.
        
        For MASTER items: Get from PWD/LGED master tables
        For CUSTOM items: Get from the item's base_rate_reference (stored when created)
        """
        
        is_custom = item.get('is_custom', False)
        
        # ✅ For CUSTOM items: get from base_rate_reference
        if is_custom:
            # Option 1: base_rate_reference stored in tenant_rate_items
            base_rate = item.get('base_rate_reference', 0)
            if base_rate > 0:
                return base_rate
            
            # Option 2: Calculate from pricing levels (reverse the discount)
            pricing = item.get('pricing', {})
            if isinstance(pricing, dict):
                # Use Market/Competitive as base reference
                market = pricing.get('COMPETITIVE', {})
                if isinstance(market, dict):
                    market_price = market.get('price', 0)
                    if market_price > 0:
                        # Reverse the 18% discount: base = market / 0.82
                        return round(market_price / 0.82, 2)
                elif isinstance(market, (int, float)):
                    return round(market / 0.82, 2)
            
            return 0.0
        
        # ✅ For MASTER items: get from PWD/LGED master tables
        master_reference_type = item.get('master_reference_type')
        master_item_code = item.get('item_code')
        
        if not master_reference_type or not master_item_code:
            return 0.0
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if master_reference_type == 'PWD':
                cursor.execute("""
                    SELECT unit_rate FROM pwd_rates 
                    WHERE pwd_code = ? AND zone_name = 'Zone-A'
                    ORDER BY edition_year DESC LIMIT 1
                """, (master_item_code,))
            elif master_reference_type == 'LGED':
                cursor.execute("""
                    SELECT unit_rate FROM lged_zone_rates 
                    WHERE child_id IN (SELECT id FROM lged_children WHERE code = ?)
                    AND zone_name = 'Zone-A'
                """, (master_item_code,))
            else:
                return 0.0
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 0.0
            
        except Exception as e:
            return 0.0

    def _render_add_item_form(self, book_id: int, version_id: int):
        """Render form to add a new item to the rate book"""
        
        # ✅ Generate unique form key
        import time
        form_key = f"add_item_form_{book_id}_{version_id}_{int(time.time())}"
        
        with st.form(form_key):
            st.markdown("#### ➕ Add New Item")
            
            col1, col2 = st.columns(2)
            
            with col1:
                item_code = st.text_input("Item Code*", placeholder="e.g., CUST-001 or 01.1.1", key=f"item_code_{form_key}")
                description = st.text_input("Description*", placeholder="Item description", key=f"description_{form_key}")
                unit = st.selectbox("Unit", ["", "each", "cum", "sqm", "meter", "kg", "hour", "day", "job", "set", "month", "year"], key=f"unit_{form_key}")
            
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
                
                # Create the item
                item_id = self.service.repository.create_rate_item({
                    'rate_book_id': book_id,
                    'item_code': item_code,
                    'item_description': description,
                    'unit': unit,
                    'is_custom': 1 if is_custom else 0,
                    'created_by': tenant['user_id'],
                    'skip_pricing': True
                })
                
                if item_id:
                    # Add costs for each level
                    cost_levels = [
                        ('AGGRESSIVE', aggressive_cost),
                        ('COMPETITIVE', competitive_cost),
                        ('STANDARD', standard_cost)
                    ]
                    
                    for level, cost in cost_levels:
                        if cost > 0:
                            self.service.repository.update_pricing(
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
        """Save edited rates to database"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        # Map original items by ID
        items_by_id = {item['id']: item for item in original_items if isinstance(item, dict) and 'id' in item}
        
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
                self.service.repository.update_rate_item(item_id, updates)
            
            # ✅ Update pricing with proper handling
            for level in ['Economy', 'Market', 'Premium']:
                price = row.get(level)
                if price is not None and price != '':
                    try:
                        # Convert to float if it's a string
                        if isinstance(price, str):
                            price = float(price) if price else 0
                        elif isinstance(price, (int, float)):
                            price = float(price)
                        else:
                            continue
                        
                        self.service.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=level.upper(),
                            price=round(price, 2),
                            user_id=user_id
                        )
                    except Exception as e:
                        st.warning(f"Failed to update {item.get('item_code', 'unknown')} - {level}: {e}")

    
    def _delete_selected_items(self, edited_df: pd.DataFrame, original_items: List[Dict]):
        """Delete items that were removed from the editor"""
        
        original_ids = {item['id'] for item in original_items}
        edited_ids = set(edited_df['ID'].tolist())
        
        deleted_ids = original_ids - edited_ids
        
        if not deleted_ids:
            st.info("No items selected for deletion")
            return
        
        if st.warning(f"Delete {len(deleted_ids)} items?"):
            for item_id in deleted_ids:
                self.service.repository.delete_rate_item(item_id)
            
            st.success(f"✅ Deleted {len(deleted_ids)} items")
    
    # =========================================================================
    # TAB 5: RATE BOOK VERSIONS
    # =========================================================================
    
    def _render_rate_versions(self, tenant: Dict):
        """Manage rate book versions"""
        
        st.subheader("📊 Rate Book Versions")
        
        if not self._check_permission('version'):
            st.warning("🔒 You don't have permission to manage versions.")
            return
        
        tenant = self._get_tenant_info()
        
        # Get all rate books
        result = self.service.get_rate_books(
            tenant['tenant_id'],
            tenant['tenant_type'],
            include_archived=False
        )
        
        if not result.get('success'):
            st.error(result.get('error', 'Failed to load rate books'))
            return
        
        books = result.get('books', [])
        
        if not books:
            st.info("No rate books found")
            return
        
        # Select rate book
        book_options = {b['id']: b['name'] for b in books}
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="version_book_select"
        )
        
        if not selected_book_id:
            return
        
        selected_book = next((b for b in books if b['id'] == selected_book_id), None)
        
        if not selected_book:
            return
        
        # Get versions
        versions = self.service.repository.get_versions_for_book(selected_book_id)
        
        if not versions:
            st.info("No versions found for this rate book")
            
            # Create first version
            if st.button("📦 Create First Version", use_container_width=True):
                result = self.service.create_version(
                    book_id=selected_book_id,
                    version_name="Initial Version",
                    effective_from=datetime.now().date().isoformat(),
                    created_by=tenant['user_id']
                )
                
                if result.get('success'):
                    st.success("✅ First version created!")
                    st.rerun()
                else:
                    st.error(result.get('error', 'Failed to create version'))
            
            return
        
        # Display versions
        st.markdown(f"#### Versions for {selected_book['name']}")
        
        for version in versions:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**v{version['version_number']}** - {version['version_name']}")
                
                with col2:
                    status = "✅ CURRENT" if version['is_current'] else "📦 Archived"
                    st.markdown(f"**Status:** {status}")
                
                with col3:
                    effective = version.get('effective_from', 'N/A')
                    st.markdown(f"**Effective:** {effective}")
                
                with col4:
                    if not version['is_current']:
                        if st.button("Set Current", key=f"set_current_{version['id']}"):
                            self.service.repository.set_current_version(version['id'])
                            st.success("✅ Current version updated!")
                            st.rerun()
        
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
                
                result = self.service.create_version(
                    book_id=selected_book_id,
                    version_name=version_name,
                    effective_from=effective_from.isoformat(),
                    notes=notes,
                    created_by=tenant['user_id']
                )
                
                if result.get('success'):
                    st.success("✅ New version created successfully!")
                    st.rerun()
                else:
                    st.error(result.get('error', 'Failed to create version'))

    # modules/company_rate_management.py - Updated with 3 Cost Levels
    def _render_edit_rate_book(self):
        """Edit a rate book's items and costing with clean layout"""
        
        st.markdown("### ✏️ Edit Costs: Company Cost Profiles")
        st.caption("Manage your 3 cost levels for each item: Aggressive, Competitive, Standard")
        
        if not self._check_permission('update'):
            st.warning("🔒 You don't have permission to edit rate books.")
            return
        
        tenant = self._get_tenant_info()
        
        # ========== 1. TOP INFO (SIDE-BY-SIDE LAYOUT) ==========
        col_env, col_sub = st.columns(2)
        with col_env:
            self._show_environment_status()
        with col_sub:
            self._show_subscription_info(tenant)
            
        # Get all rate books
        result = self.service.get_rate_books(tenant['tenant_id'], tenant['tenant_type'], include_archived=False)
        if not result.get('success'):
            st.error(result.get('error', 'Failed to load rate books'))
            return
        
        books = result.get('books', [])
        if not books:
            st.info("📚 No rate books found. Please create or clone one first.")
            return
            
        # ========== 2. SELECTORS (Clean Container) ==========
        with st.container(border=True):
            col_book, col_version, col_info = st.columns([2, 2, 2])
            
            book_options = {b['id']: f"{b.get('name', 'Unknown')} ({b.get('source_type', 'Unknown')})" 
                            for b in books if isinstance(b, dict)}
            
            with col_book:
                selected_book_id = st.selectbox(
                    "📚 Rate Book",
                    options=list(book_options.keys()),
                    format_func=lambda x: book_options.get(x, "Unknown"),
                    key="edit_book_select"
                )
                
            if not selected_book_id:
                return
                
            selected_book = next((b for b in books if isinstance(b, dict) and b.get('id') == selected_book_id), None)
            
            versions = self.service.repository.get_versions_for_book(selected_book_id)
            if not versions:
                st.warning("No versions found for this rate book")
                return
                
            version_options = {}
            current_version = None
            for v in versions:
                if isinstance(v, dict) and v.get('id'):
                    label = f"v{v.get('version_number', '?')} - {v.get('version_name', 'Unknown')}"
                    if v.get('is_current'):
                        label += " ✅"
                        current_version = v
                    version_options[v['id']] = label
                    
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
                total_items_count = len(self.service.repository.get_rate_items_by_book(selected_book_id, selected_version_id))
                st.metric("Total Items in Book", total_items_count)
                st.caption(f"Editing: **{selected_book.get('name', 'Unknown')}**")

        # ========== 3. COST LEVEL LEGEND (Compact) ==========
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown("🟢 **Aggressive:** Lean ops, minimal overhead")
        with col2: st.markdown("🟡 **Competitive:** Balanced approach")
        with col3: st.markdown("🔴 **Standard:** Full overhead, conservative")
        st.markdown("---")

        # ========== 4. GET & PREPARE DATA ==========
        try:
            items = self.service.repository.get_rate_items_by_book(selected_book_id, selected_version_id)
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
            if not isinstance(item, dict): continue
            pricing = item.get('pricing', {})
            
            def get_cost(p, level):
                if not p or not isinstance(p, dict): return 0.0
                lvl_data = p.get(level, {})
                if isinstance(lvl_data, dict): return float(lvl_data.get('price', 0.0))
                return float(lvl_data) if isinstance(lvl_data, (int, float)) else 0.0

            base_rate = self._get_base_rate(item)
            data.append({
                'ID': item.get('id', ''),
                'Code': item.get('item_code', ''),
                'Description': item.get('item_description', '')[:80],
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if item.get('is_custom') else 'Master',
                'Base Rate': base_rate if base_rate > 0 else 0.0,
                'Aggressive': get_cost(pricing, 'AGGRESSIVE'),
                'Competitive': get_cost(pricing, 'COMPETITIVE'),
                'Standard': get_cost(pricing, 'STANDARD'),
                '🗑️': False
            })
            
        df = pd.DataFrame(data)

        # ========== 5. TOOLBAR: SEARCH, FILTERS ==========
        with st.container(border=True):
            col_s, col_f, col_p = st.columns([3, 1, 1])
            with col_s:
                search_term = st.text_input("Search", placeholder="🔍 Search code or description...", key="cost_search", label_visibility="collapsed")
            with col_f:
                type_filter = st.selectbox("Type", ["All", "Master", "Custom"], key="type_filter", label_visibility="collapsed")
            with col_p:
                items_per_page = st.selectbox("Per Page", [10, 25, 50, 100], key="cost_items_per_page", label_visibility="collapsed")

        # Apply filters
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
        
        # Pagination state
        if 'cost_page_num' not in st.session_state: st.session_state.cost_page_num = 1
        current_filter = (search_term, type_filter)
        if st.session_state.get('cost_last_filter') != current_filter:
            st.session_state.cost_page_num = 1
            st.session_state.cost_last_filter = current_filter
            
        if st.session_state.cost_page_num > total_pages:
            st.session_state.cost_page_num = total_pages

        # ========== 6. BULK OPERATIONS (Moved Up & Fixed) ==========
        # Initialize counters to force data_editor refresh
        if 'bulk_update_counter' not in st.session_state:
            st.session_state.bulk_update_counter = 0
        if 'save_counter' not in st.session_state:
            st.session_state.save_counter = 0

        with st.container(border=True):
            st.markdown("💰 **Bulk Operations** *(Applies to ENTIRE Book Version)*")
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            with col1:
                target_level = st.selectbox("Target Level", ["Aggressive", "Competitive", "Standard"], key="bulk_target")
            with col2:
                percentage = st.number_input("Change %", min_value=-100.0, max_value=100.0, value=10.0, step=0.5, key="bulk_percentage")
            with col3:
                st.write("") # Spacer
                if st.button("📊 Apply to All", use_container_width=True, key="bulk_apply"):
                    self._apply_bulk_update(selected_book_id, selected_version_id, items, target_level, percentage)
                    st.session_state.bulk_update_counter += 1  # ✅ Force data editor refresh
                    st.success(f"✅ Applied {percentage}% to {target_level}")
                    st.rerun()
            with col4:
                st.caption("⚠️ This will update all items in this version, not just the visible page.")

        # ========== 7. PAGINATION & DATA EDITOR ==========
        # Top Pagination
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

        # Slice data
        start_idx = (st.session_state.cost_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_df.iloc[start_idx:end_idx].copy()

        # Column config
        column_config = {
            "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "Code": st.column_config.TextColumn("Code", disabled=True, width="small"),
            "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
            "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
            "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
            "Base Rate": st.column_config.NumberColumn("Base Rate", disabled=True, format="%.2f", width="small"),
            "Aggressive": st.column_config.NumberColumn("🟢 Aggressive", format="%.2f", step=100.0),
            "Competitive": st.column_config.NumberColumn("🟡 Competitive", format="%.2f", step=100.0),
            "Standard": st.column_config.NumberColumn("🔴 Standard", format="%.2f", step=100.0),
            "🗑️": st.column_config.CheckboxColumn("Delete", help="Check to delete this item", default=False, width="small")
        }
        
        # ✅ Dynamic key to force refresh after bulk updates or saves
        editor_key = f"cost_editor_{selected_book_id}_{selected_version_id}_{st.session_state.cost_page_num}_{st.session_state.bulk_update_counter}_{st.session_state.save_counter}"
        
        edited_df = st.data_editor(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            key=editor_key,
            num_rows="fixed"
        )

        # ========== 8. BOTTOM ACTIONS ==========
        st.markdown("---")
        col_save, col_add, col_del, col_summary = st.columns([2, 1, 1, 2])
        
        with col_save:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="bottom_save"):
                deleted_items_df = edited_df[edited_df['🗑️'] == True]
                if not deleted_items_df.empty:
                    self._delete_selected_items(deleted_items_df, items)
                    
                self._save_cost_changes(edited_df, items, selected_version_id)
                st.session_state.save_counter += 1  # ✅ Force data editor refresh
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
                deleted_items_df = edited_df[edited_df['🗑️'] == True]
                self._delete_selected_items(deleted_items_df, items)
                st.session_state.save_counter += 1
                st.rerun()

        with col_summary:
            # ✅ Removed duplicate expander header
            self._render_cost_summary(page_data)

        # ========== 9. ADD ITEM FORM ==========
        if st.session_state.get('show_add_item', False):
            with st.expander("➕ Add New Item", expanded=True):
                self._render_add_item_form(selected_book_id, selected_version_id)
    
    
    def _render_edit_rate_book_bak(self):
        """Edit a rate book's items and costing with clean layout"""
        
        st.subheader("✏️ Edit Costs: Company Cost Profiles")
        st.caption("Manage your 3 cost levels for each item: Aggressive, Competitive, Standard")
        
        if not self._check_permission('update'):
            st.warning("🔒 You don't have permission to edit rate books.")
            return
        
        tenant = self._get_tenant_info()
        
        # Get all rate books
        result = self.service.get_rate_books(
            tenant['tenant_id'],
            tenant['tenant_type'],
            include_archived=False
        )
        
        if not result.get('success'):
            st.error(result.get('error', 'Failed to load rate books'))
            return
        
        books = result.get('books', [])
        
        if not books:
            st.info("No rate books found. Please create or clone one first.")
            return
        
        # ========== SELECT RATE BOOK ==========
        book_options = {}
        for b in books:
            if isinstance(b, dict):
                book_options[b['id']] = f"{b.get('name', 'Unknown')} ({b.get('source_type', 'Unknown')})"
        
        col1, col2 = st.columns(2)
        with col1:
            selected_book_id = st.selectbox(
                "Select Rate Book to Edit",
                options=list(book_options.keys()),
                format_func=lambda x: book_options.get(x, "Unknown"),
                key="edit_book_select"
            )
        
        if not selected_book_id:
            return
        
        selected_book = next((b for b in books if isinstance(b, dict) and b.get('id') == selected_book_id), None)
        if not selected_book:
            return
        
        with col2:
            st.info(f"📖 Editing: **{selected_book.get('name', 'Unknown')}**")
        
        # ========== SELECT VERSION ==========
        versions = self.service.repository.get_versions_for_book(selected_book_id)
        
        if not versions:
            st.warning("No versions found for this rate book")
            return
        
        # Build version options
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
        
        default_version_id = current_version.get('id') if current_version else list(version_options.keys())[0]
        
        selected_version_id = st.selectbox(
            "Select Version",
            options=list(version_options.keys()),
            format_func=lambda x: version_options.get(x, "Unknown"),
            index=list(version_options.keys()).index(default_version_id) if default_version_id in version_options else 0,
            key="edit_version_select"
        )
        
        # ========== COST LEVEL DEFINITIONS ==========
        st.markdown("---")
        st.markdown("#### 📊 Cost Level Definitions")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🟢 **Aggressive Cost**\nLean operations, minimal overhead")
        with col2:
            st.info("🟡 **Competitive Cost**\nBalanced approach, normal overhead")
        with col3:
            st.info("🔴 **Standard Cost**\nFull overhead, conservative approach")
        
        # ========== GET ITEMS ==========
        try:
            items = self.service.repository.get_rate_items_by_book(selected_book_id, selected_version_id)
        except Exception as e:
            st.error(f"Error loading items: {e}")
            return
        
        if not items:
            st.info("No items found in this rate book")
            if self._check_permission('create'):
                with st.expander("➕ Add Item", expanded=True):
                    self._render_add_item_form(selected_book_id, selected_version_id)
            return
        
        # ========== PREPARE DATA ==========
        data = []
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
            
            is_custom = item.get('is_custom', False)
            base_rate = self._get_base_rate(item)
            
            data.append({
                'ID': item.get('id', ''),
                'Code': item.get('item_code', ''),
                'Description': item.get('item_description', '')[:60],
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if is_custom else 'Master',
                'Base Rate': base_rate if base_rate > 0 else ('N/A' if is_custom else 0),
                'Aggressive': get_cost(pricing, 'AGGRESSIVE'),
                'Competitive': get_cost(pricing, 'COMPETITIVE'),
                'Standard': get_cost(pricing, 'STANDARD'),
            })
        
        if not data:
            st.info("No valid items found")
            return
        
        df = pd.DataFrame(data)
        
        # ========== SEARCH & FILTERS ==========
        st.markdown("---")
        st.markdown("#### 🔍 Search & Filters")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input(
                "🔍 Search",
                placeholder="Search by code or description...",
                key="cost_search",
                label_visibility="collapsed"
            )
        with col2:
            type_filter = st.selectbox(
                "Type",
                options=["All", "Master", "Custom"],
                key="type_filter",
                label_visibility="collapsed"
            )
        with col3:
            items_per_page = st.selectbox(
                "Items per page",
                options=[10, 25, 50, 100],
                key="cost_items_per_page",
                label_visibility="collapsed"
            )
        
        # ========== APPLY FILTERS ==========
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[
                filtered_df['Code'].str.contains(search_term, case=False, na=False) |
                filtered_df['Description'].str.contains(search_term, case=False, na=False)
            ]
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['Type'] == type_filter]
        
        total_items = len(filtered_df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # ========== PAGINATION ==========
        if 'cost_page_num' not in st.session_state:
            st.session_state.cost_page_num = 1
        
        # Reset page if filters change
        current_filter = (search_term, type_filter)
        if st.session_state.get('cost_last_filter') != current_filter:
            st.session_state.cost_page_num = 1
            st.session_state.cost_last_filter = current_filter
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Prev", disabled=st.session_state.cost_page_num <= 1, key="cost_prev"):
                st.session_state.cost_page_num -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.cost_page_num} of {total_pages} (Total: {total_items} items)")
        with col3:
            if st.button("Next ▶", disabled=st.session_state.cost_page_num >= total_pages, key="cost_next"):
                st.session_state.cost_page_num += 1
                st.rerun()
        
        # ========== SLICE DATA ==========
        start_idx = (st.session_state.cost_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_df.iloc[start_idx:end_idx]
        
        # ========== BULK OPERATIONS ==========
        st.markdown("---")
        with st.expander("💰 Bulk Operations", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                target_level = st.selectbox(
                    "Target Level",
                    options=["Aggressive", "Competitive", "Standard"],
                    key="bulk_target"
                )
            with col2:
                percentage = st.number_input(
                    "Change %",
                    min_value=-100.0,
                    max_value=100.0,
                    value=10.0,
                    step=0.5,
                    key="bulk_percentage"
                )
            with col3:
                st.write("")
                st.write("")
                if st.button("📊 Apply to All", use_container_width=True):
                    self._apply_bulk_update(selected_book_id, selected_version_id, items, target_level, percentage)
                    st.success(f"✅ Applied {percentage}% to {target_level}")
                    st.rerun()
        
        # ========== DISPLAY EDITOR ==========
        st.markdown("---")
        st.markdown("#### 📋 Items")
        
        # Column config for cleaner display
        column_config = {
            "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "Code": st.column_config.TextColumn("Code", disabled=True, width="small"),
            "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
            "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
            "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
            "Base Rate": st.column_config.TextColumn("Base Rate", disabled=True, width="small"),
            "Aggressive": st.column_config.NumberColumn("🟢 Aggressive", format="%.2f", step=100.0),
            "Competitive": st.column_config.NumberColumn("🟡 Competitive", format="%.2f", step=100.0),
            "Standard": st.column_config.NumberColumn("🔴 Standard", format="%.2f", step=100.0),
        }
        
        edited_df = st.data_editor(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            key=f"cost_editor_{selected_book_id}_{selected_version_id}_{st.session_state.cost_page_num}"
        )
        
        # ========== ACTION BUTTONS ==========
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                self._save_cost_changes(edited_df, items, selected_version_id)
                st.success("✅ Costs saved successfully!")
                st.rerun()
        
        with col2:
            if self._check_permission('create'):
                if st.button("➕ Add Item", use_container_width=True):
                    st.session_state.show_add_item = True
        
        with col3:
            if self._check_permission('delete'):
                if st.button("🗑️ Delete Selected", use_container_width=True):
                    self._delete_selected_items(edited_df, items)
                    st.rerun()
        
        with col4:
            # Show cost summary in a small expander
            with st.expander("📊 Cost Summary", expanded=False):
                self._render_cost_summary(page_data)
        
        # ========== ADD ITEM FORM ==========
        if st.session_state.get('show_add_item', False):
            with st.expander("➕ Add New Item", expanded=True):
                self._render_add_item_form(selected_book_id, selected_version_id)

    def _render_cost_editor(self, book_id: int, version_id: int, items: List[Dict], book: Dict):
        """Render cost editor with pagination, search, and filters"""
        
        st.markdown(f"#### 📊 Cost Editor: {book.get('name', 'Rate Book')}")
        st.caption("Each item has 3 cost levels. The bid optimizer uses these to generate scenarios.")
        
        # ✅ Show cost level definitions
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🟢 **Aggressive Cost**\nLean operations, minimal overhead")
        with col2:
            st.info("🟡 **Competitive Cost**\nBalanced approach, normal overhead")
        with col3:
            st.info("🔴 **Standard Cost**\nFull overhead, conservative approach")
        
        st.divider()
        
        # ✅ Bulk Operations
        self._render_bulk_operations(book_id, version_id, items)
        
        st.divider()
        
        # ✅ Prepare data for editor with 3 cost levels
        data = []
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
            
            base_rate = self._get_base_rate(item)
            
            data.append({
                'ID': item.get('id', ''),
                'Code': item.get('item_code', ''),
                'Description': item.get('item_description', '')[:60],
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if item.get('is_custom') else 'Master',
                'Base Rate': base_rate,
                'Aggressive Cost': get_cost(pricing, 'AGGRESSIVE'),
                'Competitive Cost': get_cost(pricing, 'COMPETITIVE'),
                'Standard Cost': get_cost(pricing, 'STANDARD'),
            })
        
        if not data:
            st.info("No valid items found")
            return
        
        df = pd.DataFrame(data)
        
        # ============================================
        # ✅ SEARCH AND FILTERS
        # ============================================
        st.markdown("#### 🔍 Search & Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input(
                "🔍 Search",
                placeholder="Code or description...",
                key="cost_search",
                help="Search by item code or description"
            )
        
        with col2:
            type_filter = st.selectbox(
                "Item Type",
                options=["All", "Master", "Custom"],
                key="type_filter"
            )
        
        with col3:
            # Items per page
            items_per_page = st.selectbox(
                "Items per page",
                options=[10, 25, 50, 100, 200],
                key="cost_items_per_page"
            )
        
        # ✅ Apply filters
        filtered_df = df.copy()
        
        if search_term:
            filtered_df = filtered_df[
                filtered_df['Code'].str.contains(search_term, case=False, na=False) |
                filtered_df['Description'].str.contains(search_term, case=False, na=False)
            ]
        
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['Type'] == type_filter]
        
        # ============================================
        # ✅ PAGINATION
        # ============================================
        total_items = len(filtered_df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Page navigation
        if 'cost_page_num' not in st.session_state:
            st.session_state.cost_page_num = 1
        
        # Reset page if filters change
        current_filter = (search_term, type_filter)
        if st.session_state.get('cost_last_filter') != current_filter:
            st.session_state.cost_page_num = 1
            st.session_state.cost_last_filter = current_filter
        
        # Display pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.cost_page_num <= 1, key="cost_prev"):
                st.session_state.cost_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.cost_page_num} of {total_pages} (Total: {total_items} items)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.cost_page_num >= total_pages, key="cost_next"):
                st.session_state.cost_page_num += 1
                st.rerun()
        
        # Slice data for current page
        start_idx = (st.session_state.cost_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_df.iloc[start_idx:end_idx]
        
        # ============================================
        # ✅ TABLE HEADER WITH SORTING
        # ============================================
        st.markdown("#### 📋 Items")
        
        # Sort functionality
        sort_col = st.session_state.get('cost_sort_col', 'Code')
        sort_asc = st.session_state.get('cost_sort_asc', True)
        
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔄 Reset Sort", key="reset_sort"):
                st.session_state.cost_sort_col = 'Code'
                st.session_state.cost_sort_asc = True
                st.rerun()
        
        # ============================================
        # ✅ DISPLAY EDITABLE DATAFRAME
        # ============================================
        edited_df = st.data_editor(
            page_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "Code": st.column_config.TextColumn("Code", disabled=True, width="small"),
                "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
                "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                "Base Rate": st.column_config.NumberColumn("Base Rate", disabled=True, format="%.2f"),
                "Aggressive Cost": st.column_config.NumberColumn("🟢 Aggressive", format="%.2f", step=100.0),
                "Competitive Cost": st.column_config.NumberColumn("🟡 Competitive", format="%.2f", step=100.0),
                "Standard Cost": st.column_config.NumberColumn("🔴 Standard", format="%.2f", step=100.0),
            },
            key=f"cost_editor_{book_id}_{version_id}_{st.session_state.cost_page_num}"
        )
        
        # ============================================
        # ✅ SAVE CHANGES
        # ============================================
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                self._save_cost_changes(edited_df, items, version_id)
                st.success("✅ Costs saved successfully!")
                st.rerun()
        
        with col2:
            if self._check_permission('create'):
                if st.button("➕ Add Item", use_container_width=True):
                    st.session_state.show_add_item = True
        
        with col3:
            if self._check_permission('delete'):
                if st.button("🗑️ Delete Selected", use_container_width=True):
                    self._delete_selected_items(edited_df, items)
                    st.rerun()
        
        with col4:
            # ✅ Show cost summary
            self._render_cost_summary(page_data)
        
        # Show add item form if requested
        if st.session_state.get('show_add_item', False):
            with st.expander("➕ Add New Item", expanded=True):
                self._render_add_item_form(book_id, version_id)



    def _save_cost_changes(self, edited_df: pd.DataFrame, original_items: List[Dict], version_id: int):
        """Save cost changes from the editor"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        items_by_id = {item['id']: item for item in original_items if isinstance(item, dict) and 'id' in item}
        
        updated_count = 0
        level_map = {
            'Aggressive Cost': 'AGGRESSIVE',
            'Competitive Cost': 'COMPETITIVE',
            'Standard Cost': 'STANDARD'
        }
        
        for _, row in edited_df.iterrows():
            item_id = row.get('ID')
            
            if not item_id or item_id not in items_by_id:
                continue
            
            for display_level, db_level in level_map.items():
                cost = row.get(display_level)
                if cost is not None and cost != '':
                    try:
                        if isinstance(cost, str):
                            cost = float(cost) if cost else 0
                        elif isinstance(cost, (int, float)):
                            cost = float(cost)
                        else:
                            continue
                        
                        self.service.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=db_level,
                            price=round(cost, 2),
                            user_id=user_id
                        )
                        updated_count += 1
                    except Exception as e:
                        st.warning(f"Failed to update item {item_id} - {display_level}: {e}")
        
        if updated_count > 0:
            st.toast(f"✅ Updated {updated_count} cost entries")


    def _render_bulk_operations(self, book_id: int, version_id: int, items: List[Dict]):
        """Render bulk operations for cost levels"""
        
        st.markdown("#### 💰 Bulk Cost Operations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            target_level = st.selectbox(
                "Target Cost Level",
                options=["Aggressive Cost", "Competitive Cost", "Standard Cost"],
                key="bulk_target_level",
                help="Select which cost level to update"
            )
        
        with col2:
            percentage_change = st.number_input(
                "Percentage Change (%)",
                min_value=-100.0,
                max_value=100.0,
                value=10.0,
                step=0.5,
                key="bulk_percentage",
                help="Positive = increase, Negative = decrease"
            )
        
        with col3:
            include_zero = st.checkbox(
                "Include items with zero cost",
                value=False,
                key="include_zero",
                help="Include items where current cost is 0"
            )
        
        if st.button("📊 Preview Changes", use_container_width=True):
            self._preview_bulk_update(items, target_level, percentage_change)
        
        if st.button("✅ Apply Bulk Change", type="primary", use_container_width=True):
            self._apply_bulk_update(book_id, version_id, items, target_level, percentage_change, include_zero)
            st.success(f"✅ Applied {percentage_change}% change to {target_level}")
            st.rerun()
        
        st.divider()
        
        # ✅ Other bulk operations
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reset to Master Rates", use_container_width=True):
                self._reset_costs_to_master(book_id, version_id)
                st.rerun()
        with col2:
            if st.button("📥 Import Costs from CSV", use_container_width=True):
                st.session_state.show_import_pricing = True
                st.rerun()


    def _preview_bulk_update(self, items: List[Dict], target_level: str, percentage: float):
        """Preview bulk update changes"""
        
        st.markdown("#### 📊 Preview Changes")
        
        level_map = {
            "Aggressive Cost": "AGGRESSIVE",
            "Competitive Cost": "COMPETITIVE",
            "Standard Cost": "STANDARD"
        }
        
        level_key = level_map.get(target_level, "COMPETITIVE")
        
        preview_data = []
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            
            pricing = item.get('pricing', {})
            current_cost = None
            
            if isinstance(pricing, dict):
                level_data = pricing.get(level_key, {})
                if isinstance(level_data, dict):
                    current_cost = level_data.get('price')
                elif isinstance(level_data, (int, float)):
                    current_cost = level_data
            
            if current_cost is not None and current_cost > 0:
                new_cost = current_cost * (1 + percentage / 100)
                preview_data.append({
                    'Code': item.get('item_code', ''),
                    'Description': item.get('item_description', '')[:40],
                    'Current Cost': f"BDT {current_cost:,.2f}",
                    'New Cost': f"BDT {new_cost:,.2f}",
                    'Change': f"{((new_cost - current_cost) / current_cost * 100):.1f}%"
                })
        
        if preview_data:
            st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
            st.caption(f"Showing first 20 of {len(items)} items")
        else:
            st.info("No items found to update")


    def _apply_bulk_update(self, book_id: int, version_id: int, items: List[Dict], 
                            target_level: str, percentage: float, include_zero: bool):
        """Apply bulk percentage update"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        level_map = {
            "Aggressive Cost": "AGGRESSIVE",
            "Competitive Cost": "COMPETITIVE",
            "Standard Cost": "STANDARD"
        }
        
        level_key = level_map.get(target_level, "COMPETITIVE")
        
        updated_count = 0
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            pricing = item.get('pricing', {})
            current_cost = None
            
            if isinstance(pricing, dict):
                level_data = pricing.get(level_key, {})
                if isinstance(level_data, dict):
                    current_cost = level_data.get('price')
                elif isinstance(level_data, (int, float)):
                    current_cost = level_data
            
            if current_cost == 0 and not include_zero:
                continue
            
            if current_cost is not None:
                new_cost = max(0, current_cost * (1 + percentage / 100))
                
                self.service.update_pricing(
                    version_id=version_id,
                    item_id=item['id'],
                    pricing_level=level_key,
                    price=round(new_cost, 2),
                    user_id=user_id
                )
                updated_count += 1
        
        st.toast(f"✅ Updated {updated_count} items in {target_level}")


    def _render_cost_summary(self, df: pd.DataFrame):
        """Render cost summary statistics for the 3 cost levels"""
        
        with st.expander("📊 Cost Summary", expanded=False):
            # ✅ Check if columns exist and have numeric data
            col1, col2, col3 = st.columns(3)
            
            # Get the cost columns safely
            aggressive_col = df['Aggressive Cost'] if 'Aggressive Cost' in df.columns else pd.Series()
            competitive_col = df['Competitive Cost'] if 'Competitive Cost' in df.columns else pd.Series()
            standard_col = df['Standard Cost'] if 'Standard Cost' in df.columns else pd.Series()
            
            # Drop NaN and non-numeric values
            aggressive = pd.to_numeric(aggressive_col, errors='coerce').dropna()
            competitive = pd.to_numeric(competitive_col, errors='coerce').dropna()
            standard = pd.to_numeric(standard_col, errors='coerce').dropna()
            
            with col1:
                if not aggressive.empty:
                    st.metric(
                        "🟢 Aggressive Cost",
                        f"BDT {aggressive.mean():,.2f}",
                        f"Min: {aggressive.min():,.2f} | Max: {aggressive.max():,.2f}"
                    )
                else:
                    st.metric("🟢 Aggressive Cost", "No data")
            
            with col2:
                if not competitive.empty:
                    st.metric(
                        "🟡 Competitive Cost",
                        f"BDT {competitive.mean():,.2f}",
                        f"Min: {competitive.min():,.2f} | Max: {competitive.max():,.2f}"
                    )
                else:
                    st.metric("🟡 Competitive Cost", "No data")
            
            with col3:
                if not standard.empty:
                    st.metric(
                        "🔴 Standard Cost",
                        f"BDT {standard.mean():,.2f}",
                        f"Min: {standard.min():,.2f} | Max: {standard.max():,.2f}"
                    )
                else:
                    st.metric("🔴 Standard Cost", "No data")
            
            # Show cost spread if all have data
            if not aggressive.empty and not competitive.empty and not standard.empty:
                avg_agg = aggressive.mean()
                avg_comp = competitive.mean()
                avg_std = standard.mean()
                
                spread_agg_comp = ((avg_comp - avg_agg) / avg_agg * 100) if avg_agg > 0 else 0
                spread_comp_std = ((avg_std - avg_comp) / avg_comp * 100) if avg_comp > 0 else 0
                
                st.caption(f"**Cost Spread:** Aggressive → Competitive: {spread_agg_comp:.1f}% | Competitive → Standard: {spread_comp_std:.1f}%")



    def _reset_costs_to_master(self, book_id: int, version_id: int):
        """Reset costs to master rates with 3 cost levels"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        book = self.service.repository.get_rate_book(book_id)
        if not book:
            st.error("Book not found")
            return
        
        source_type = book.get('source_type')
        
        if source_type == 'CUSTOM':
            st.warning("Cannot reset custom rates to master. Please edit manually.")
            return
        
        # Get master rates
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if source_type == 'PWD':
            cursor.execute("""
                SELECT c.pwd_code as item_code, r.unit_rate
                FROM pwd_children c
                JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE r.zone_name = 'Zone-A'
                ORDER BY c.pwd_code
            """)
        else:  # LGED
            cursor.execute("""
                SELECT c.code as item_code, r.unit_rate
                FROM lged_children c
                JOIN lged_zone_rates r ON c.id = r.child_id
                WHERE r.zone_name = 'Zone-A'
                ORDER BY c.code
            """)
        
        master_rates = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        items = self.service.repository.get_rate_items_by_book(book_id, version_id)
        
        updated_count = 0
        cost_levels = [
            ('AGGRESSIVE', 0.78),   # 22% below master
            ('COMPETITIVE', 0.82),  # 18% below master
            ('STANDARD', 0.86)      # 14% below master
        ]
        
        for item in items:
            item_code = item.get('item_code')
            if item_code in master_rates:
                base_rate = master_rates[item_code]
                for level, factor in cost_levels:
                    cost = base_rate * factor
                    self.service.update_pricing(
                        version_id=version_id,
                        item_id=item['id'],
                        pricing_level=level,
                        price=round(cost, 2),
                        user_id=user_id
                    )
                updated_count += 1
        
        st.success(f"✅ Reset {updated_count} items to master rates")
    def _render_pricing_editor(self, book_id: int, version_id: int, items: List[Dict], book: Dict):
        """Render full pricing editor with CRUD operations"""
        
        st.markdown(f"#### 📊 Pricing Editor: {book.get('name', 'Rate Book')}")
        st.caption("Edit the three cost levels (Economy, Market, Premium) for each item")
        
        # ✅ Add bulk operations
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("📥 Export Prices", use_container_width=True):
                self._export_pricing(items, version_id)
        with col2:
            if st.button("📤 Import Prices", use_container_width=True):
                st.session_state.show_import_pricing = True
        with col3:
            if st.button("💰 Apply % Change", use_container_width=True):
                st.session_state.show_percent_change = True
        with col4:
            if st.button("🔄 Reset to Master", use_container_width=True):
                if st.checkbox("Reset all prices to master rates?"):
                    self._reset_prices_to_master(book_id, version_id)
                    st.rerun()
        
        # ✅ Show import pricing dialog
        if st.session_state.get('show_import_pricing', False):
            self._render_import_pricing_form(book_id, version_id)
            if st.button("Cancel Import", key="cancel_import"):
                st.session_state.show_import_pricing = False
                st.rerun()
        
        # ✅ Show percent change dialog
        if st.session_state.get('show_percent_change', False):
            self._render_percent_change_form(book_id, version_id, items)
            if st.button("Cancel", key="cancel_percent"):
                st.session_state.show_percent_change = False
                st.rerun()
        
        # Prepare data for editor
        data = []
        for item in items:
            if not isinstance(item, dict):
                continue
            
            pricing = item.get('pricing', {})
            
            # Safely get prices
            def get_price(pricing_data, level):
                if not pricing_data:
                    return ''
                if isinstance(pricing_data, dict):
                    level_data = pricing_data.get(level, {})
                    if isinstance(level_data, dict):
                        return level_data.get('price', '')
                    elif isinstance(level_data, (int, float)):
                        return level_data
                    else:
                        return ''
                elif isinstance(pricing_data, (int, float)):
                    return pricing_data
                else:
                    return ''
            
            data.append({
                'ID': item.get('id', ''),
                'Code': item.get('item_code', ''),
                'Description': item.get('item_description', '')[:50],
                'Unit': item.get('unit', ''),
                'Type': 'Custom' if item.get('is_custom') else 'Master',
                'Economy': get_price(pricing, 'ECONOMY'),
                'Market': get_price(pricing, 'MARKET'),
                'Premium': get_price(pricing, 'PREMIUM'),
            })
        
        if not data:
            st.info("No valid items found")
            return
        
        df = pd.DataFrame(data)
        
        # ✅ Show editable dataframe with proper column config
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "Code": st.column_config.TextColumn("Code", disabled=True, width="small"),
                "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
                "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                "Economy": st.column_config.NumberColumn("Economy (BDT)", format="%.2f", step=100.0, help="Aggressive pricing"),
                "Market": st.column_config.NumberColumn("Market (BDT)", format="%.2f", step=100.0, help="Competitive pricing"),
                "Premium": st.column_config.NumberColumn("Premium (BDT)", format="%.2f", step=100.0, help="Standard pricing"),
            },
            key=f"pricing_editor_{book_id}_{version_id}"
        )
        
        # ✅ Save changes
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                self._save_pricing_changes(edited_df, items, version_id)
                st.success("✅ Pricing saved successfully!")
                st.rerun()
        
        with col2:
            if self._check_permission('create'):
                if st.button("➕ Add Item", use_container_width=True):
                    st.session_state.show_add_item = True
        
        with col3:
            if self._check_permission('delete'):
                if st.button("🗑️ Delete Selected", use_container_width=True):
                    self._delete_selected_items(edited_df, items)
                    st.rerun()
        
        with col4:
            # ✅ Show cost profile summary
            self._render_cost_profile_summary(items)
        
        # Show add item form if requested
        if st.session_state.get('show_add_item', False):
            with st.expander("➕ Add New Item", expanded=True):
                self._render_add_item_form(book_id, version_id)


    def _save_pricing_changes(self, edited_df: pd.DataFrame, original_items: List[Dict], version_id: int):
        """Save pricing changes from the editor"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        # Map original items by ID
        items_by_id = {item['id']: item for item in original_items if isinstance(item, dict) and 'id' in item}
        
        updated_count = 0
        
        for _, row in edited_df.iterrows():
            item_id = row.get('ID')
            
            if not item_id or item_id not in items_by_id:
                continue
            
            # Update pricing for each level
            for level in ['Economy', 'Market', 'Premium']:
                price = row.get(level)
                if price is not None and price != '':
                    try:
                        if isinstance(price, str):
                            price = float(price) if price else 0
                        elif isinstance(price, (int, float)):
                            price = float(price)
                        else:
                            continue
                        
                        self.service.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=level.upper(),
                            price=round(price, 2),
                            user_id=user_id
                        )
                        updated_count += 1
                    except Exception as e:
                        st.warning(f"Failed to update item {item_id} - {level}: {e}")
        
        if updated_count > 0:
            st.toast(f"✅ Updated {updated_count} pricing entries")


    def _render_import_pricing_form(self, book_id: int, version_id: int):
        """Render import pricing from CSV"""
        
        st.markdown("#### 📤 Import Prices from CSV")
        st.caption("Format: item_code,economy,market,premium")
        
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=["csv"],
            key="import_pricing_csv"
        )
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Validate columns
                required = ['item_code', 'economy', 'market', 'premium']
                if not all(col in df.columns for col in required):
                    st.error(f"CSV must have columns: {', '.join(required)}")
                    st.write("Found columns:", list(df.columns))
                    return
                
                st.markdown("**Preview:**")
                st.dataframe(df.head(10))
                
                if st.button("📥 Import Prices", type="primary"):
                    tenant = self._get_tenant_info()
                    user_id = tenant['user_id']
                    
                    success_count = 0
                    for _, row in df.iterrows():
                        item_code = str(row.get('item_code', '')).strip()
                        economy = float(row.get('economy', 0))
                        market = float(row.get('market', 0))
                        premium = float(row.get('premium', 0))
                        
                        if not item_code:
                            continue
                        
                        # Find item by code
                        items = self.service.repository.get_rate_items_by_book(book_id, version_id)
                        item = next((i for i in items if i.get('item_code') == item_code), None)
                        
                        if item:
                            item_id = item['id']
                            for level, price in [('ECONOMY', economy), ('MARKET', market), ('PREMIUM', premium)]:
                                if price > 0:
                                    self.service.update_pricing(
                                        version_id=version_id,
                                        item_id=item_id,
                                        pricing_level=level,
                                        price=round(price, 2),
                                        user_id=user_id
                                    )
                            success_count += 1
                    
                    st.success(f"✅ Imported {success_count} items")
                    st.session_state.show_import_pricing = False
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error reading file: {e}")


    def _render_percent_change_form(self, book_id: int, version_id: int, items: List[Dict]):
        """Render percentage change form"""
        
        st.markdown("#### 💰 Apply Percentage Change")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            level = st.selectbox(
                "Pricing Level",
                options=["Economy", "Market", "Premium"],
                key="percent_level"
            )
        
        with col2:
            percentage = st.number_input(
                "Percentage (%)",
                min_value=-100.0,
                max_value=100.0,
                value=10.0,
                step=0.5,
                key="percent_value"
            )
        
        with col3:
            st.write("")
            st.write("")
            apply_type = st.radio(
                "Apply to",
                options=["All Items", "Selected Items"],
                horizontal=True,
                key="percent_apply_type"
            )
        
        if st.button("Apply Percentage Change", type="primary"):
            tenant = self._get_tenant_info()
            user_id = tenant['user_id']
            
            # Get current prices
            updated_count = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                pricing = item.get('pricing', {})
                current_price = None
                
                if isinstance(pricing, dict):
                    level_data = pricing.get(level.upper(), {})
                    if isinstance(level_data, dict):
                        current_price = level_data.get('price')
                    elif isinstance(level_data, (int, float)):
                        current_price = level_data
                
                if current_price is not None and current_price > 0:
                    new_price = current_price * (1 + percentage / 100)
                    self.service.update_pricing(
                        version_id=version_id,
                        item_id=item['id'],
                        pricing_level=level.upper(),
                        price=round(max(new_price, 0), 2),
                        user_id=user_id
                    )
                    updated_count += 1
            
            st.success(f"✅ Updated {updated_count} items")
            st.session_state.show_percent_change = False
            st.rerun()


    def _export_pricing(self, items: List[Dict], version_id: int):
        """Export pricing to CSV"""
        
        import io
        
        data = []
        for item in items:
            if not isinstance(item, dict):
                continue
            
            pricing = item.get('pricing', {})
            
            def get_price(pricing_data, level):
                if not pricing_data:
                    return ''
                if isinstance(pricing_data, dict):
                    level_data = pricing_data.get(level, {})
                    if isinstance(level_data, dict):
                        return level_data.get('price', '')
                    elif isinstance(level_data, (int, float)):
                        return level_data
                return ''
            
            data.append({
                'item_code': item.get('item_code', ''),
                'description': item.get('item_description', ''),
                'unit': item.get('unit', ''),
                'economy': get_price(pricing, 'ECONOMY'),
                'market': get_price(pricing, 'MARKET'),
                'premium': get_price(pricing, 'PREMIUM'),
            })
        
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        
        st.download_button(
            "📥 Download Pricing CSV",
            csv,
            f"pricing_export_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )


    def _reset_prices_to_master(self, book_id: int, version_id: int):
        """Reset prices to master rates"""
        
        tenant = self._get_tenant_info()
        user_id = tenant['user_id']
        
        # Get the book to know source type
        book = self.service.repository.get_rate_book(book_id)
        if not book:
            st.error("Book not found")
            return
        
        source_type = book.get('source_type')
        
        if source_type == 'CUSTOM':
            st.warning("Cannot reset custom rates to master. Please edit manually.")
            return
        
        # Get master rates
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if source_type == 'PWD':
            cursor.execute("""
                SELECT c.pwd_code as item_code, r.unit_rate
                FROM pwd_children c
                JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE r.zone_name = 'Zone-A'
                ORDER BY c.pwd_code
            """)
        else:  # LGED
            cursor.execute("""
                SELECT c.code as item_code, r.unit_rate
                FROM lged_children c
                JOIN lged_zone_rates r ON c.id = r.child_id
                WHERE r.zone_name = 'Zone-A'
                ORDER BY c.code
            """)
        
        master_rates = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        # Get items
        items = self.service.repository.get_rate_items_by_book(book_id, version_id)
        
        updated_count = 0
        for item in items:
            item_code = item.get('item_code')
            if item_code in master_rates:
                base_rate = master_rates[item_code]
                for level, discount in [('ECONOMY', 0.22), ('MARKET', 0.18), ('PREMIUM', 0.14)]:
                    price = base_rate * (1 - discount)
                    self.service.update_pricing(
                        version_id=version_id,
                        item_id=item['id'],
                        pricing_level=level,
                        price=round(price, 2),
                        user_id=user_id
                    )
                updated_count += 1
        
        st.success(f"✅ Reset {updated_count} items to master rates")


    def _render_cost_profile_summary(self, items: List[Dict]):
        """Render cost profile summary statistics"""
        
        with st.expander("📊 Cost Profile Summary", expanded=False):
            # Calculate averages
            total_items = len(items)
            
            economy_prices = []
            market_prices = []
            premium_prices = []
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                pricing = item.get('pricing', {})
                
                def get_price(pricing_data, level):
                    if not pricing_data:
                        return None
                    if isinstance(pricing_data, dict):
                        level_data = pricing_data.get(level, {})
                        if isinstance(level_data, dict):
                            return level_data.get('price')
                        elif isinstance(level_data, (int, float)):
                            return level_data
                    return None
                
                economy = get_price(pricing, 'ECONOMY')
                market = get_price(pricing, 'MARKET')
                premium = get_price(pricing, 'PREMIUM')
                
                if economy: economy_prices.append(economy)
                if market: market_prices.append(market)
                if premium: premium_prices.append(premium)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Economy (Aggressive)",
                    f"BDT {sum(economy_prices)/len(economy_prices):,.2f}" if economy_prices else "N/A",
                    f"Min: {min(economy_prices):,.2f}" if economy_prices else ""
                )
            
            with col2:
                st.metric(
                    "Market (Competitive)",
                    f"BDT {sum(market_prices)/len(market_prices):,.2f}" if market_prices else "N/A",
                    f"Min: {min(market_prices):,.2f}" if market_prices else ""
                )
            
            with col3:
                st.metric(
                    "Premium (Standard)",
                    f"BDT {sum(premium_prices)/len(premium_prices):,.2f}" if premium_prices else "N/A",
                    f"Min: {min(premium_prices):,.2f}" if premium_prices else ""
                )
            
            # Show price distribution
            if economy_prices and market_prices and premium_prices:
                avg_economy = sum(economy_prices)/len(economy_prices)
                avg_market = sum(market_prices)/len(market_prices)
                avg_premium = sum(premium_prices)/len(premium_prices)
                
                st.caption(f"**Average Spread:** Economy → Market: {((avg_market - avg_economy) / avg_economy * 100):.1f}% | Market → Premium: {((avg_premium - avg_market) / avg_market * 100):.1f}%")

# =========================================================================
# CONVENIENCE FUNCTION
# =========================================================================

def render_company_rate_management(db):
    """Convenience function to render company rate management"""
    manager = CompanyRateManagement(db)
    manager.render()