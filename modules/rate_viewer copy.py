# modules/rate_viewer.py

import streamlit as st
import pandas as pd
import numpy as np

class RateViewer:
    """Rate viewer dashboard with sorting, filtering, pagination, and search"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Main rate viewer interface"""
        
        st.markdown("""
        <div class="main-header">
            <h1>📊 Rate Schedule Viewer</h1>
            <p>View, search, filter, and export PWD and LGED rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Source selection
        source = st.radio(
            "Select Rate Schedule",
            options=["PWD", "LGED"],
            horizontal=True,
            key="rate_viewer_source"
        )
        
        st.markdown("---")
        
        # Get data based on source
        if source == "PWD":
            self._render_pwd_rates()
        else:
            self._render_lged_rates()
    
    def _render_pwd_rates(self):
        """Render PWD rates with full features"""
        
        st.markdown("### 🏗️ PWD Rates")
        
        # Load data
        data = self._load_pwd_data()
        
        if data.empty:
            st.info("No PWD rates found. Please import data first.")
            return
        
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
                selected_chapter = st.selectbox("Chapter", ["All"] + list(chapters))
            else:
                selected_chapter = "All"
        
        with col2:
            # Zone filter
            if 'zone_name' in data.columns:
                zones = data['zone_name'].dropna().unique().tolist()
                selected_zone = st.selectbox("Zone", ["All"] + zones)
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
                aggfunc='first'  # Use 'first' to avoid aggregation issues
            ).reset_index()
        except Exception as e:
            st.error(f"Pivot error: {e}")
            # Fallback: display as is
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
        if st.session_state.get('pwd_last_filter') != (selected_chapter, selected_zone, search_term):
            st.session_state.pwd_page_num = 1
            st.session_state.pwd_last_filter = (selected_chapter, selected_zone, search_term)
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.pwd_page_num <= 1):
                st.session_state.pwd_page_num -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.pwd_page_num} of {total_pages} (Total: {total_items} items)")
        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.pwd_page_num >= total_pages):
                st.session_state.pwd_page_num += 1
                st.rerun()
        
        # Slice data for current page
        start_idx = (st.session_state.pwd_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = pivot_data.iloc[start_idx:end_idx]
        
        # Display the dataframe
        st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # Export options
        st.markdown("---")
        st.markdown("#### 📥 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = pivot_data.to_csv(index=False)
            st.download_button(
                "📥 Download as CSV",
                csv,
                f"pwd_rates_export.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Show summary statistics
            with st.expander("📊 Summary Statistics", expanded=False):
                stats_data = []
                for zone in rate_columns:
                    if zone in filtered_data['zone_name'].values:
                        zone_data = filtered_data[filtered_data['zone_name'] == zone]['unit_rate']
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
    
    def _render_lged_rates(self):
        """Render LGED rates with full features"""
        
        st.markdown("### 🛣️ LGED Rates")
        
        # Load data
        data = self._load_lged_data()
        
        if data.empty:
            st.info("No LGED rates found. Please import data first.")
            return
        
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
        
        # Pivot table - use 'first' to avoid aggregation issues
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
        
        # Display the dataframe
        st.dataframe(page_data, use_container_width=True, hide_index=True)
        
        # Export options
        st.markdown("---")
        st.markdown("#### 📥 Export Data")
        
        csv = pivot_data.to_csv(index=False)
        st.download_button(
            "📥 Download as CSV",
            csv,
            f"lged_rates_export.csv",
            "text/csv",
            use_container_width=True
        )

    
    def _load_pwd_data(self):
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
    
    def _load_lged_data(self):
        """Load LGED data from database"""
        try:
            conn = self.db.get_connection()
            
            # First check if tables exist and have data
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


# Convenience function
def render_rate_viewer(db):
    viewer = RateViewer(db)
    viewer.render()