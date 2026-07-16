# modules/rate_viewer.py - Refactored to use crud_rates.py

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from database.unified_db_manager import get_db_manager

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
    
    def __init__(self):
        self.db = get_db_manager()
    
    def _is_user_logged_in(self) -> bool:
        """Check if user is logged in"""
        if 'user_id' in st.session_state and st.session_state.user_id:
            return True
        if 'user_role' in st.session_state and st.session_state.user_role:
            return True
        if 'user' in st.session_state and st.session_state.user:
            return True
        return False
    
    def _get_current_user(self) -> Dict[str, Any]:
        """Get current user data"""
        user = {}
        user['id'] = st.session_state.get('user_id')
        user['username'] = st.session_state.get('username', 'unknown')
        user['role'] = st.session_state.get('user_role', 'viewer')
        user['company_id'] = st.session_state.get('company_id')
        
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
        
        if not self._is_user_logged_in():
            st.warning("⚠️ Please log in to access rate viewer.")
            if st.button("Go to Login"):
                st.session_state.page = "login"
                st.rerun()
            return
        
        user = self._get_current_user()
        render_role_badge()
        
        st.markdown("""
        <div class="main-header">
            <h1>📊 Rate Schedule Viewer</h1>
            <p>View, search, filter, and export rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        can_view_system = can_view_system_rates()
        can_view_tenant = can_view_tenant_rates()
        
        tabs_to_show = []
        if can_view_system:
            tabs_to_show.append("🏗️ PWD Master")
            tabs_to_show.append("🛣️ LGED Master")
        if can_view_tenant:
            tabs_to_show.append("📚 My Rate Books")
        
        if not tabs_to_show:
            st.warning("🔒 You don't have permission to view any rates.")
            return
        
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
    # PWD MASTER RATES - Using RateCRUD
    # =========================================================================
    
    def _render_pwd_master(self):
        """Render PWD master rates with RBAC controls"""
        st.markdown("### 🏗️ PWD Master Rates")
        
        can_edit = can_edit_system_rates()
        can_export = can_export_system_rates()
        
        if can_edit:
            st.success("👑 You have edit access to PWD master rates")
        else:
            st.info("🔒 View-only access. Contact System Administrator for edit permissions.")
        
        data = self._load_pwd_data()
        
        if data.empty:
            st.info("No PWD rates found. Please import data first.")
            if can_edit:
                st.button("📥 Import PWD Rates", key="import_pwd")
            return
        
        self._render_pwd_rates(data, can_edit, can_export)

    def _render_pwd_rates(self, data: pd.DataFrame, can_edit: bool, can_export: bool):
        """Render PWD rates with full features - Works with chapter filter"""
        
        # Debug info
        if st.checkbox("Show Debug Info", key="pwd_debug"):
            st.write("Data columns:", data.columns.tolist())
            st.write("Sample data:", data.head())
        
        st.markdown("#### 🔍 Filters")
        
        # ========== 5 Columns for Filters ==========
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            # ✅ CHAPTER FILTER - Will detect 'chapter_number' column
            if 'chapter_number' in data.columns:
                # Convert all chapters to string for consistent display
                chapters = sorted(data['chapter_number'].dropna().astype(str).unique())
                chapter_options = ["All"] + chapters
                selected_chapter = st.selectbox(
                    "📚 Chapter", 
                    chapter_options, 
                    key="pwd_chapter_filter"
                )
            else:
                selected_chapter = "All"
                st.info("No chapter column")
        
        with col2:
            if 'zone_name' in data.columns:
                zones = sorted(data['zone_name'].dropna().unique().tolist())
                selected_zone = st.selectbox("📍 Zone", ["All"] + zones, key="pwd_zone_filter")
            else:
                selected_zone = "All"
        
        with col3:
            search_term = st.text_input(
                "🔍 Search", 
                placeholder="Code or description...", 
                key="pwd_search"
            )
        
        with col4:
            items_per_page = st.selectbox(
                "📄 Items per page", 
                [10, 25, 50, 100, 200], 
                key="pwd_items_per_page"
            )
        
        with col5:
            # Show count for selected chapter
            if selected_chapter != "All" and 'chapter_number' in data.columns:
                count = len(data[data['chapter_number'].astype(str) == selected_chapter])
                st.metric("📊 Items", count)
            else:
                st.metric("📊 Total Items", len(data))
        
        # ========== APPLY FILTERS ==========
        filtered_data = data.copy()
        
        # 1. Chapter filter
        if selected_chapter != "All" and 'chapter_number' in data.columns:
            filtered_data = filtered_data[
                filtered_data['chapter_number'].astype(str) == selected_chapter
            ]
        
        # 2. Zone filter
        if selected_zone != "All" and 'zone_name' in data.columns:
            filtered_data = filtered_data[filtered_data['zone_name'] == selected_zone]
        
        # 3. Search filter
        if search_term:
            search_lower = search_term.lower()
            filtered_data = filtered_data[
                filtered_data['pwd_code'].astype(str).str.contains(search_term, case=False, na=False) |
                filtered_data['description'].astype(str).str.contains(search_term, case=False, na=False)
            ]
        
        # Clean data
        if 'unit_rate' in filtered_data.columns:
            filtered_data['unit_rate'] = pd.to_numeric(filtered_data['unit_rate'], errors='coerce')
            filtered_data = filtered_data.dropna(subset=['unit_rate'])
        
        if filtered_data.empty:
            st.warning(f"No data found for Chapter {selected_chapter if selected_chapter != 'All' else 'All'}")
            return
        
        # ========== PIVOT DATA ==========
        try:
            # Determine columns for pivot
            desc_col = 'description' if 'description' in filtered_data.columns else 'specification_text'
            unit_col = 'unit' if 'unit' in filtered_data.columns else 'measurement_unit'
            
            # Pivot columns
            index_cols = ['pwd_code', desc_col, unit_col]
            if 'chapter_number' in filtered_data.columns:
                index_cols.append('chapter_number')
            
            pivot_data = filtered_data.pivot_table(
                index=index_cols,
                columns='zone_name',
                values='unit_rate',
                aggfunc='first'
            ).reset_index()
            
        except Exception as e:
            st.error(f"Pivot error: {e}")
            st.dataframe(filtered_data, use_container_width=True, hide_index=True)
            return
        
        # Clean up column names
        pivot_data.columns.name = None
        pivot_data = pivot_data.rename(columns={
            'pwd_code': 'Item Code',
            desc_col: 'Description',
            unit_col: 'Unit'
        })
        
        if 'chapter_number' in pivot_data.columns:
            pivot_data = pivot_data.rename(columns={'chapter_number': 'Chapter'})
        
        pivot_data = pivot_data.fillna('')
        
        # Format rate columns
        zone_columns = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
        for col in zone_columns:
            if col in pivot_data.columns:
                pivot_data[col] = pivot_data[col].apply(
                    lambda x: f"৳{x:,.2f}" if x and x != '' else ''
                )
        
        # ========== DISPLAY ==========
        if 'Chapter' in pivot_data.columns:
            st.caption(f"📚 Showing Chapter {selected_chapter if selected_chapter != 'All' else 'All Chapters'} - {len(pivot_data)} items")
        
        # ========== PAGINATION ==========
        total_items = len(pivot_data)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        if 'pwd_page_num' not in st.session_state:
            st.session_state.pwd_page_num = 1
        
        # Reset page when filter changes
        current_filter = (selected_chapter, selected_zone, search_term)
        if st.session_state.get('pwd_last_filter') != current_filter:
            st.session_state.pwd_page_num = 1
            st.session_state.pwd_last_filter = current_filter
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.pwd_page_num <= 1, key="pwd_prev"):
                st.session_state.pwd_page_num -= 1
                st.rerun()
        
        with col2:
            st.markdown(
                f"""
                <div style='text-align: center; padding-top: 8px;'>
                    <span style='color: #555;'>
                        Page <strong>{st.session_state.pwd_page_num}</strong> of <strong>{total_pages}</strong>
                        <span style='color: #ccc; margin: 0 10px;'>|</span>
                        Total: <strong>{total_items:,}</strong> items
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            next_col1, next_col2 = st.columns([2, 1])
            with next_col2:
                if st.button("Next ▶", disabled=st.session_state.pwd_page_num >= total_pages, key="pwd_next"):
                    st.session_state.pwd_page_num += 1
                    st.rerun()
        
        start_idx = (st.session_state.pwd_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = pivot_data.iloc[start_idx:end_idx]
        
        # ========== DISPLAY DATA ==========
        if can_edit:
            edited_data = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                key=f"pwd_editor_{st.session_state.pwd_page_num}"
            )
            
            col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
            with col_save2:
                if st.button("💾 Save PWD Changes", key="save_pwd", use_container_width=True):
                    self._save_pwd_changes(edited_data, data)
                    st.success("✅ PWD rates updated successfully!")
                    st.rerun()
        else:
            st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # ========== EXPORT ==========
        if can_export:
            self._render_export_options(pivot_data, "pwd_rates_export")
        
        # ========== SUMMARY STATISTICS ==========
        with st.expander("📊 Summary Statistics", expanded=False):
            self._render_summary_stats(filtered_data, zone_columns)


    def _render_summary_stats(self, data: pd.DataFrame, zone_columns: List[str]):
        """Render summary statistics for PWD rates"""
        
        st.markdown("#### 📊 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_items = data['pwd_code'].nunique() if 'pwd_code' in data.columns else len(data)
            st.metric("Total Items", total_items)
        
        with col2:
            if 'zone_name' in data.columns:
                zones = data['zone_name'].nunique()
                st.metric("Zones", zones)
            else:
                st.metric("Zones", "N/A")
        
        with col3:
            if 'chapter_number' in data.columns:
                chapters = data['chapter_number'].nunique()
                st.metric("Chapters", chapters)
            else:
                st.metric("Chapters", "N/A")
        
        with col4:
            if 'unit_rate' in data.columns:
                avg_rate = data['unit_rate'].mean()
                st.metric("Avg Rate", f"৳{avg_rate:,.2f}")
            else:
                st.metric("Avg Rate", "N/A")
        
        # Chapter breakdown
        if 'chapter_number' in data.columns:
            st.markdown("##### 📚 Chapter Breakdown")
            chapter_counts = data['chapter_number'].value_counts().sort_index()
            st.bar_chart(chapter_counts)
            
            chapter_data = []
            for chapter, count in chapter_counts.items():
                chapter_data.append({
                    'Chapter': chapter,
                    'Items': count,
                    'Percentage': f"{(count / len(data) * 100):.1f}%"
                })
            st.dataframe(pd.DataFrame(chapter_data), use_container_width=True, hide_index=True)
        
        # Zone distribution
        if 'zone_name' in data.columns and 'unit_rate' in data.columns:
            st.markdown("##### 📍 Zone Rate Distribution")
            zone_stats = data.groupby('zone_name')['unit_rate'].agg(['mean', 'min', 'max', 'count']).reset_index()
            zone_stats.columns = ['Zone', 'Average', 'Min', 'Max', 'Count']
            zone_stats['Average'] = zone_stats['Average'].apply(lambda x: f"৳{x:,.2f}")
            zone_stats['Min'] = zone_stats['Min'].apply(lambda x: f"৳{x:,.2f}")
            zone_stats['Max'] = zone_stats['Max'].apply(lambda x: f"৳{x:,.2f}")
            st.dataframe(zone_stats, use_container_width=True, hide_index=True)

    # =========================================================================
    # LGED MASTER RATES - Using RateCRUD
    # =========================================================================
    
    def _render_lged_master(self):
        """Render LGED master rates with RBAC controls"""
        st.markdown("### 🛣️ LGED Master Rates")
        
        can_edit = can_edit_system_rates()
        can_export = can_export_system_rates()
        
        if can_edit:
            st.success("👑 You have edit access to LGED master rates")
        else:
            st.info("🔒 View-only access. Contact System Administrator for edit permissions.")
        
        data = self._load_lged_data()
        
        if data.empty:
            st.info("No LGED rates found. Please import data first.")
            if can_edit:
                st.button("📥 Import LGED Rates", key="import_lged")
            return
        
        self._render_lged_rates(data, can_edit, can_export)
    
    def _render_lged_rates(self, data: pd.DataFrame, can_edit: bool, can_export: bool):
        """Render LGED rates with full features"""
        
        if st.checkbox("Show Debug Info", key="lged_debug"):
            st.write("Data types:")
            st.write(data.dtypes)
            st.write("Sample data:")
            st.dataframe(data.head())
        
        data['unit_rate'] = pd.to_numeric(data['unit_rate'], errors='coerce')
        data = data.dropna(subset=['unit_rate'])
        
        if data.empty:
            st.warning("No valid rate data found")
            return
        
        zone_names = data['zone_name'].unique().tolist()
        
        st.markdown("#### 🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
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
        
        filtered_data = data.copy()
        
        if selected_chapter != "All":
            filtered_data = filtered_data[filtered_data['chapter_number'] == selected_chapter]
        
        if selected_zone != "All":
            filtered_data = filtered_data[filtered_data['zone_name'] == selected_zone]
        
        if search_term:
            filtered_data = filtered_data[
                filtered_data['code'].astype(str).str.contains(search_term, case=False, na=False) |
                filtered_data['description'].astype(str).str.contains(search_term, case=False, na=False)
            ]
        
        if filtered_data.empty:
            st.warning("No data found matching the filters")
            return
        
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
        
        pivot_data.columns.name = None
        pivot_data = pivot_data.rename(columns={
            'code': 'Item Code',
            'description': 'Description',
            'unit': 'Unit'
        })
        
        for zone in zone_names:
            if zone in pivot_data.columns:
                pivot_data[zone] = pd.to_numeric(pivot_data[zone], errors='coerce').fillna(0)
                pivot_data[zone] = pivot_data[zone].apply(lambda x: f"৳{x:,.2f}" if x > 0 else '')
        
        total_items = len(pivot_data)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        if 'lged_page_num' not in st.session_state:
            st.session_state.lged_page_num = 1
        
        current_filter = (selected_chapter, selected_zone, search_term)
        if st.session_state.get('lged_last_filter') != current_filter:
            st.session_state.lged_page_num = 1
            st.session_state.lged_last_filter = current_filter
        
        # ===== PAGINATION WITH RIGHT-ALIGNED NEXT BUTTON =====
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.lged_page_num <= 1, key="lged_prev"):
                st.session_state.lged_page_num -= 1
                st.rerun()
        
        with col2:
            st.markdown(
                f"""
                <div style='text-align: center; padding-top: 8px;'>
                    <span style='color: #555;'>
                        Page <strong>{st.session_state.lged_page_num}</strong> of <strong>{total_pages}</strong>
                        <span style='color: #ccc; margin: 0 10px;'>|</span>
                        Total: <strong>{total_items:,}</strong> items
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            next_container = st.container()
            with next_container:
                next_col1, next_col2 = st.columns([2, 1])
                with next_col2:
                    if st.button("Next ▶", disabled=st.session_state.lged_page_num >= total_pages, key="lged_next"):
                        st.session_state.lged_page_num += 1
                        st.rerun()
        
        start_idx = (st.session_state.lged_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = pivot_data.iloc[start_idx:end_idx]
        
        if can_edit:
            edited_data = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                key=f"lged_editor_{st.session_state.lged_page_num}"
            )
            
            col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
            with col_save2:
                if st.button("💾 Save LGED Changes", key="save_lged", use_container_width=True):
                    self._save_lged_changes(edited_data, data)
                    st.success("✅ LGED rates updated successfully!")
                    st.rerun()
        else:
            st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        if can_export:
            self._render_export_options(pivot_data, "lged_rates_export")


    def _render_tenant_rate_books(self):
        """Render tenant rate books with RBAC controls"""
        st.markdown("### 📚 My Rate Books")
        
        can_edit = can_edit_tenant_rates()
        can_export = can_export_tenant_rates()
        
        user_id = st.session_state.get('user_id')
        company_id = st.session_state.get('company_id')
        
        if not user_id:
            st.warning("⚠️ User not logged in. Please log in again.")
            return
        
        tenant_id = company_id or user_id
        tenant_type = 'company' if company_id else 'user'
        
        # ✅ Use RateCRUD directly
        books = self.db.get_rate_books_by_tenant(tenant_id, tenant_type)
        
        if not books:
            st.info("No rate books found. Create a rate book from the Rate Management page.")
            if st.button("➕ Go to Rate Management", key="go_to_rate_management"):
                st.session_state.page = "rate_management"
                st.rerun()
            return
        
        book_options = {}
        for b in books:
            if isinstance(b, dict) and 'id' in b and 'name' in b:
                book_options[b['id']] = b['name']
        
        if not book_options:
            st.info("No valid rate books found.")
            return
        
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="tenant_rate_book_select"
        )
        
        if not selected_book_id:
            return
        
        selected_book = None
        for b in books:
            if isinstance(b, dict) and b.get('id') == selected_book_id:
                selected_book = b
                break
        
        if not selected_book:
            st.error("Selected rate book not found")
            return
        
        st.markdown(f"""
        **Source:** {selected_book.get('source_type', 'Unknown')}  
        **Status:** {'Active' if selected_book.get('is_active') else 'Inactive'}  
        **Items:** {selected_book.get('item_count', 0)}  
        **Versions:** {selected_book.get('version_count', 0)}
        """)
        
        # ✅ Get versions using RateCRUD
        versions = self.db.get_versions_for_book(selected_book_id)
        
        if not versions:
            st.info("No versions found for this rate book")
            return
        
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
        
        # ✅ Get items with pricing
        items = self.db.get_rate_items_with_pricing(selected_book_id, selected_version_id)
        
        if not items:
            st.info("No items found in this rate book")
            return
        
        # ✅ Build display data with CORRECT column mapping
        data = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pricing = item.get('pricing', {})
            
            # ✅ Extract ALL 4 pricing levels
            standard_price = pricing.get('STANDARD', {}).get('price', 0)
            competitive_price = pricing.get('COMPETITIVE', {}).get('price', 0)
            aggressive_price = pricing.get('AGGRESSIVE', {}).get('price', 0)
            premium_price = pricing.get('PREMIUM', {}).get('price', 0)
            
            # ✅ Debug - print to console
            print(f"Item: {item.get('item_code')}")
            print(f"  STANDARD: {standard_price}")
            print(f"  COMPETITIVE: {competitive_price}")
            print(f"  AGGRESSIVE: {aggressive_price}")
            print(f"  PREMIUM: {premium_price}")
            
            data.append({
                'Item Code': item.get('item_code', ''),
                'Description': item.get('item_description', ''),
                'Unit': item.get('unit', ''),
                'Standard': standard_price,       # ✅ Matches data_editor column name
                'Competitive': competitive_price, # ✅ Matches data_editor column name
                'Aggressive': aggressive_price,   # ✅ Matches data_editor column name
                'Premium': premium_price,         # ✅ Matches data_editor column name
            })
        
        df = pd.DataFrame(data)
        
        # ✅ Show pricing level info
        st.info("💡 **Pricing Levels:** Aggressive (-16%), Competitive (-12%), Standard (0%), Premium (+10%)")
        
        items_per_page = st.selectbox("Items per page", [10, 25, 50, 100, 200], key="tenant_items_per_page")
        
        total_items = len(df)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        if 'tenant_page_num' not in st.session_state:
            st.session_state.tenant_page_num = 1
        
        # ===== PAGINATION WITH RIGHT-ALIGNED NEXT BUTTON =====
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.tenant_page_num <= 1, key="tenant_prev"):
                st.session_state.tenant_page_num -= 1
                st.rerun()
        
        with col2:
            st.markdown(
                f"""
                <div style='text-align: center; padding-top: 8px;'>
                    <span style='color: #555;'>
                        Page <strong>{st.session_state.tenant_page_num}</strong> of <strong>{total_pages}</strong>
                        <span style='color: #ccc; margin: 0 10px;'>|</span>
                        Total: <strong>{total_items:,}</strong> items
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            next_container = st.container()
            with next_container:
                next_col1, next_col2 = st.columns([2, 1])
                with next_col2:
                    if st.button("Next ▶", disabled=st.session_state.tenant_page_num >= total_pages, key="tenant_next"):
                        st.session_state.tenant_page_num += 1
                        st.rerun()
        
        start_idx = (st.session_state.tenant_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = df.iloc[start_idx:end_idx]
        
        # ✅ Display with ALL 4 columns
        if can_edit and not selected_book.get('is_archived', False):
            edited_df = st.data_editor(
                page_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Item Code": st.column_config.TextColumn("Item Code", width="small"),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Unit": st.column_config.TextColumn("Unit", width="small"),
                    "Aggressive": st.column_config.NumberColumn("Aggressive (-16%)", format="%.2f", help="16% discount from Standard"),
                    "Competitive": st.column_config.NumberColumn("Competitive (-12%)", format="%.2f", help="12% discount from Standard"),
                    "Standard": st.column_config.NumberColumn("Standard (0%)", format="%.2f", help="Base rate"),
                    "Premium": st.column_config.NumberColumn("Premium (+10%)", format="%.2f", help="10% premium from Standard"),
                },
                key=f"tenant_editor_{selected_book_id}_{selected_version_id}_{st.session_state.tenant_page_num}"
            )
            
            col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
            with col_save2:
                if st.button("💾 Save Changes", key="save_tenant_changes", use_container_width=True):
                    self._save_tenant_pricing_changes(edited_df, items, selected_version_id)
                    st.success("✅ Pricing updated successfully!")
                    st.rerun()
        else:
            # ✅ Display all 4 columns
            st.dataframe(
                page_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Item Code": st.column_config.TextColumn("Item Code", width="small"),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Unit": st.column_config.TextColumn("Unit", width="small"),
                    "Aggressive": st.column_config.NumberColumn("Aggressive (-16%)", format="%.2f"),
                    "Competitive": st.column_config.NumberColumn("Competitive (-12%)", format="%.2f"),
                    "Standard": st.column_config.NumberColumn("Standard (0%)", format="%.2f"),
                    "Premium": st.column_config.NumberColumn("Premium (+10%)", format="%.2f"),
                }
            )
        
        if can_export:
            self._render_export_options(df, f"rate_book_{selected_book.get('name', 'unknown')}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _load_pwd_data(self) -> pd.DataFrame:
        """Load PWD data using RateCRUD"""
        try:
            # ✅ Get children with correct column names
            children = self.db.query("""
                SELECT pwd_code, description, unit, parent_code
                FROM pwd_children
            """)
            
            if not children:
                return pd.DataFrame()
            
            # ✅ Get parents for chapter info
            parents = self.db.query("""
                SELECT pwd_code, chapter_number
                FROM pwd_parents
            """)
            
            # ✅ Get rates
            rates = self.db.query("""
                SELECT pwd_code, zone_name, unit_rate
                FROM pwd_rates
            """)
            
            df_children = pd.DataFrame(children)
            df_parents = pd.DataFrame(parents) if parents else pd.DataFrame(columns=['pwd_code', 'chapter_number'])
            df_rates = pd.DataFrame(rates) if rates else pd.DataFrame(columns=['pwd_code', 'zone_name', 'unit_rate'])
            
            # Merge in Pandas
            df = df_children.merge(df_parents, left_on='parent_code', right_on='pwd_code', how='left', suffixes=('', '_parent'))
            df = df.merge(df_rates, on='pwd_code', how='left')
            
            # ✅ Rename columns to match expected names
            df = df.rename(columns={
                'description': 'specification_text',
                'unit': 'measurement_unit'
            })
            
            df = df.dropna(subset=['pwd_code'])
            df['unit_rate'] = pd.to_numeric(df['unit_rate'], errors='coerce')
            
            # ✅ Return with expected columns
            columns_needed = ['pwd_code', 'specification_text', 'measurement_unit', 'chapter_number', 'zone_name', 'unit_rate']
            for col in columns_needed:
                if col not in df.columns:
                    df[col] = ''
            
            return df[columns_needed]
            
        except Exception as e:
            if "does not exist" in str(e).lower() or "undefined" in str(e).lower():
                st.info("PWD master data table not found. Please import PWD data first.")
            else:
                st.error(f"Error loading PWD data: {e}")
            return pd.DataFrame()

    
    def _load_lged_data(self) -> pd.DataFrame:
        """Load LGED data using RateCRUD"""
        try:
            # ✅ Get children
            children = self.db.query("""
                SELECT id, code, description, unit, parent_code
                FROM lged_children
            """)
            
            if not children:
                return pd.DataFrame()
            
            # ✅ Get rates
            rates = self.db.query("""
                SELECT child_id, zone_name, unit_rate
                FROM lged_zone_rates
            """)
            
            df_children = pd.DataFrame(children)
            df_rates = pd.DataFrame(rates) if rates else pd.DataFrame(columns=['child_id', 'zone_name', 'unit_rate'])
            
            # Merge in Pandas
            df = df_children.merge(df_rates, left_on='id', right_on='child_id', how='left')
            
            # ✅ Extract chapter number from parent_code
            df['chapter_number'] = df['parent_code'].apply(
                lambda x: str(x).split('.')[0] if x and '.' in str(x) else ''
            )
            
            df = df.dropna(subset=['code'])
            df['unit_rate'] = pd.to_numeric(df['unit_rate'], errors='coerce')
            
            # ✅ Return with expected columns
            columns_needed = ['code', 'description', 'unit', 'parent_code', 'zone_name', 'unit_rate', 'chapter_number']
            for col in columns_needed:
                if col not in df.columns:
                    df[col] = ''
            
            return df[columns_needed]
            
        except Exception as e:
            if "does not exist" in str(e).lower() or "undefined" in str(e).lower():
                st.info("LGED master data table not found. Please import LGED data first.")
            else:
                st.error(f"Error loading LGED data: {e}")
            return pd.DataFrame()

    
    def _save_pwd_changes(self, edited_data: pd.DataFrame, original_data: pd.DataFrame):
        """Save PWD rate changes - using RateCRUD"""
        # Implementation would update the database via RateCRUD
        st.info("PWD save functionality implementation")
    
    def _save_lged_changes(self, edited_data: pd.DataFrame, original_data: pd.DataFrame):
        """Save LGED rate changes - using RateCRUD"""
        # Implementation would update the database via RateCRUD
        st.info("LGED save functionality implementation")
    
    def _save_tenant_pricing_changes(
        self, 
        edited_data: pd.DataFrame, 
        original_items: List[Dict], 
        version_id: int
    ):
        """Save tenant pricing changes using RateCRUD"""
        
        user_id = st.session_state.get('user_id')
        
        if not user_id:
            st.error("⚠️ User not logged in. Cannot save changes.")
            return
        
        items_by_code = {item.get('item_code'): item for item in original_items if item.get('item_code')}
        
        saved_count = 0
        error_count = 0
        skipped_count = 0
        
        for _, row in edited_data.iterrows():
            item_code = row.get('Item Code')
            if not item_code or item_code not in items_by_code:
                continue
            
            item = items_by_code[item_code]
            item_id = item.get('id')
            
            if not item_id:
                continue
            
            # ✅ Save ALL 4 pricing levels
            pricing_levels = [
                ('Aggressive', 'AGGRESSIVE'),
                ('Competitive', 'COMPETITIVE'),
                ('Standard', 'STANDARD'),
                ('Premium', 'PREMIUM'),  # ✅ ADDED
            ]
            
            for col_name, db_level in pricing_levels:
                price = row.get(col_name)
                
                if price is None or price == '':
                    skipped_count += 1
                    continue
                
                try:
                    price_val = float(price)
                    if price_val >= 0:
                        success = self.db.update_pricing(
                            version_id=version_id,
                            item_id=item_id,
                            pricing_level=db_level,
                            price=price_val,
                            user_id=user_id
                        )
                        if success:
                            saved_count += 1
                        else:
                            error_count += 1
                except (ValueError, TypeError):
                    error_count += 1
        
        if saved_count > 0:
            st.success(f"✅ Saved {saved_count} pricing updates successfully!")
        if error_count > 0:
            st.warning(f"⚠️ {error_count} updates failed. Check the logs for details.")
        if skipped_count > 0 and error_count == 0:
            st.info(f"ℹ️ {skipped_count} fields were empty and skipped.")
    
    
    def _save_tenant_pricing_changes_bak(
        self, 
        edited_data: pd.DataFrame, 
        original_items: List[Dict], 
        version_id: int
    ):
        """Save tenant pricing changes using RateCRUD"""
        
        user_id = st.session_state.get('user_id')
        
        if not user_id:
            st.error("⚠️ User not logged in. Cannot save changes.")
            return
        
        items_by_code = {item.get('item_code'): item for item in original_items if item.get('item_code')}
        
        for _, row in edited_data.iterrows():
            item_code = row.get('Item Code')
            if not item_code or item_code not in items_by_code:
                continue
            
            item = items_by_code[item_code]
            item_id = item.get('id')
            
            if not item_id:
                continue
            
            for level in ['Aggressive', 'Competitive', 'Standard']:
                price = row.get(level)
                if price is not None and price != '':
                    try:
                        self.db.update_pricing(
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
# CONVENIENCE FUNCTION
# =========================================================================

def render_rate_viewer():
    """Convenience function to render rate viewer"""
    viewer = RateViewer()
    viewer.render()