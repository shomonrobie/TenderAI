# modules/boq_generator_ui.py

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager
from modules.rbac import (
    rbac, can_view_boq, can_create_boq, can_edit_boq, 
    can_delete_boq, can_export_data, render_role_badge
)
from modules.tender_selector import render_tender_selector
from modules.boq_generator import BOQGenerator

db = UnifiedDatabaseManager()
class BOQGeneratorUI:
    """BOQ Generator for Subscribers - Read-only rates, custom items allowed"""
    
    def __init__(self, db):
        self.db = db
    
    def get_master_rates(self, source='PWD', zone='Zone-A', chapter=None):
        """Get master rates (read-only for subscribers)"""
        try:
            if self.db is None:
                st.error("Database connection not available")
                return pd.DataFrame()
                
            conn = self.db.get_connection()
            
            # Get active version
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, edition_year FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC LIMIT 1
            """, (source,))
            version = cursor.fetchone()
            
            if not version:
                conn.close()
                return pd.DataFrame()
            
            version_id, edition_year = version
            
            if source == 'PWD':
                # PWD now uses Zone-A, Zone-B, etc. directly
                query = """
                    SELECT c.pwd_code as item_code, c.description, c.unit, 
                           r.unit_rate as rate,
                           'master' as item_type
                    FROM pwd_children c
                    JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                    WHERE c.version_id = ? AND r.version_id = ? 
                    AND r.zone_name = ?
                """
                params = [version_id, version_id, zone]
                
                if chapter:
                    query += " AND c.pwd_code LIKE ?"
                    params.append(f"{chapter}%")
                
                query += " ORDER BY c.pwd_code"
                
            else:  # LGED
                zone_col = {
                    'Zone-A': 'zone_a',
                    'Zone-B': 'zone_b',
                    'Zone-C': 'zone_c',
                    'Zone-D': 'zone_d'
                }.get(zone, 'zone_a')
                
                query = f"""
                    SELECT code as item_code, description, unit, 
                           {zone_col} as rate,
                           'master' as item_type
                    FROM lged_children 
                    WHERE version_id = ?
                """
                params = [version_id]
                
                if chapter:
                    query += " AND code LIKE ?"
                    params.append(f"{chapter}%")
                
                query += " ORDER BY code"
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
            
        except Exception as e:
            st.error(f"Error loading rates: {e}")
            return pd.DataFrame()
    
    def get_user_custom_items(self, boq_id):
        """Get user's custom items for this BOQ"""
        try:
            if self.db is None:
                return pd.DataFrame()
                
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT id, item_code, description, unit, quantity, unit_rate, total, notes
                FROM boq_items
                WHERE boq_id = ? AND is_custom = 1
                ORDER BY id
            """, conn, params=[boq_id])
            conn.close()
            return df
        except:
            return pd.DataFrame()
    
    def add_custom_item(self, boq_id, item_code, description, unit, quantity, unit_rate, notes=None):
        """Add user-defined custom item to BOQ (not saved to master rates)"""
        try:
            if self.db is None:
                return False, "Database connection not available"
                
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            total = quantity * unit_rate
            
            cursor.execute("""
                INSERT INTO boq_items (
                    boq_id, item_code, description, unit, quantity, unit_rate, total, is_custom, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (boq_id, item_code, description, unit, quantity, unit_rate, total, notes))
            
            # Update BOQ totals
            cursor.execute("""
                UPDATE boq_generation_history 
                SET item_count = (SELECT COUNT(*) FROM boq_items WHERE boq_id = ?),
                    total_estimated_cost = (SELECT SUM(total) FROM boq_items WHERE boq_id = ?)
                WHERE id = ?
            """, (boq_id, boq_id, boq_id))
            
            conn.commit()
            conn.close()
            return True, "Custom item added"
        except Exception as e:
            return False, str(e)
    
    def update_boq_item_quantity(self, item_id, quantity):
        """Update quantity of existing BOQ item"""
        try:
            if self.db is None:
                return False, "Database connection not available"
                
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE boq_items 
                SET quantity = ?, total = quantity * unit_rate
                WHERE id = ?
            """, (quantity, item_id))
            
            # Get boq_id to update totals
            cursor.execute("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
            boq_id = cursor.fetchone()[0]
            
            cursor.execute("""
                UPDATE boq_generation_history 
                SET total_estimated_cost = (SELECT SUM(total) FROM boq_items WHERE boq_id = ?)
                WHERE id = ?
            """, (boq_id, boq_id))
            
            conn.commit()
            conn.close()
            return True, "Quantity updated"
        except Exception as e:
            return False, str(e)
    
    def remove_boq_item(self, item_id):
        """Remove item from BOQ"""
        try:
            if self.db is None:
                return False, "Database connection not available"
                
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT boq_id FROM boq_items WHERE id = ?", (item_id,))
            boq_id = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM boq_items WHERE id = ?", (item_id,))
            
            cursor.execute("""
                UPDATE boq_generation_history 
                SET item_count = (SELECT COUNT(*) FROM boq_items WHERE boq_id = ?),
                    total_estimated_cost = (SELECT SUM(total) FROM boq_items WHERE boq_id = ?)
                WHERE id = ?
            """, (boq_id, boq_id, boq_id))
            
            conn.commit()
            conn.close()
            return True, "Item removed"
        except Exception as e:
            return False, str(e)
    
    def get_company_boqs(self, company_id, limit=50):
        """Get all BOQs for a company (for viewing history)"""
        try:
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT id, tender_id, tender_title, item_count, total_estimated_cost,
                       selected_zone, rate_source, status, generated_at
                FROM boq_generation_history
                WHERE company_id = ?
                ORDER BY generated_at DESC
                LIMIT ?
            """, conn, params=[company_id, limit])
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading BOQ history: {e}")
            return pd.DataFrame()


def render_boq_generator():
    """BOQ Generator UI with RBAC"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 BOQ Generator</h1>
        <p>Generate Bill of Quantities from PWD/LGED rate schedules</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Check if user can view BOQ
    if not can_view_boq():
        st.error("🔒 You don't have permission to view BOQ.")
        return
    
    # Initialize database connection
    try:
        db = UnifiedDatabaseManager()
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return
    
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    boq_ui = BOQGeneratorUI(db)
    permissions = rbac.get_current_user_permissions()
    
    # Show permission summary
    if not permissions.get('can_create_boq'):
        st.info("🔒 You have view-only access to BOQ. Contact your admin for create permissions.")
    
    # Create tabs for different BOQ functions
    tabs_list = ["📝 Generate BOQ"]
    
    if permissions.get('can_view_boq'):
        tabs_list.append("📋 BOQ History")
    
    tabs = st.tabs(tabs_list)
    tab_idx = 0
    
    # Generate BOQ Tab
    with tabs[tab_idx]:
        _render_boq_generation_form(boq_ui, db, company_id, permissions)
    tab_idx += 1
    
    # BOQ History Tab (if user has view permission)
    if permissions.get('can_view_boq') and len(tabs_list) > 1:
        with tabs[tab_idx]:
            _render_boq_history(boq_ui, company_id, permissions)
        tab_idx += 1

def _render_boq_generation_form(boq_ui, db, company_id, permissions):
    """Render BOQ generation form with tenant rate support"""
    
    can_create = permissions.get('can_create_boq', False)
    can_edit = permissions.get('can_edit_boq', False)
    
    # ========== Step 1: Select Rate Source ==========
    st.markdown("### Step 1: Select Rate Source")
    
    # ✅ FIX: Get rate books with proper connection handling
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, source_type, is_demo 
        FROM tenant_rate_books 
        WHERE tenant_id = ? AND is_active = 1 AND is_archived = 0
        ORDER BY is_demo DESC, source_type
    """, (company_id,))
    rate_books = cursor.fetchall()
    conn.close()
    
    has_rate_books = len(rate_books) > 0
    
    if has_rate_books:
        st.success(f"✅ Found {len(rate_books)} rate books for your company")
        
        # Let user choose rate source
        source_options = ["PWD", "LGED", "CUSTOM"]
        rate_source = st.radio("Rate Source", source_options, horizontal=True)
        
        # Show available rate books for this source
        available_books = [b for b in rate_books if b['source_type'] == rate_source or rate_source == 'CUSTOM']
        
        if available_books:
            book_options = {b['id']: f"{b['name']} {'(Demo)' if b['is_demo'] else ''}" for b in available_books}
            selected_book_id = st.selectbox(
                "Select Rate Book",
                options=list(book_options.keys()),
                format_func=lambda x: book_options.get(x, "Unknown")
            )
            
            # ✅ FIX: Get version for this book with separate connection
            conn = db.get_connection()
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
            
            if version:
                st.info(f"📖 Using version: {version['version_name']}")
        else:
            st.warning(f"No {rate_source} rate book found. Please clone or create one first.")
            if st.button("📋 Go to Rate Management"):
                st.session_state.page = "company_rate_management"
                st.rerun()
            return
    else:
        st.warning("⚠️ No rate books found. Please create or clone rate books first.")
        if st.button("📋 Go to Rate Management"):
            st.session_state.page = "company_rate_management"
            st.rerun()
        return
    
    # ========== Step 2: Select Tender ==========
    st.markdown("### Step 2: Select Tender")
    
    try:
        conn = db.get_connection()
        tenders = pd.read_sql_query("""
            SELECT id, tender_id, tender_title, official_estimate, procuring_entity
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
            ORDER BY created_at DESC
        """, conn, params=[company_id])
        conn.close()
    except Exception as e:
        st.error(f"Error loading tenders: {e}")
        return
    
    if tenders.empty:
        st.info("No tenders found. Please create a tender first.")
        if st.button("➕ Create New Tender"):
            st.session_state.page = "tender_management"
            st.rerun()
        return
    
    selected_tender = st.selectbox(
        "Select Tender",
        options=tenders['id'].tolist(),
        format_func=lambda x: f"{tenders[tenders['id']==x]['tender_id'].iloc[0]} - {tenders[tenders['id']==x]['tender_title'].iloc[0][:50]}"
    )
    
    if selected_tender:
        tender_info = tenders[tenders['id'] == selected_tender].iloc[0]
        st.info(f"**Official Estimate:** BDT {tender_info['official_estimate']:,.2f}")
    
    # ========== Step 3: Zone Selection ==========
    st.markdown("### Step 3: Select Zone")
    
    zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
    zone_labels = {
        "Zone-A": "Dhaka & Mymensingh Division",
        "Zone-B": "Chattogram & Sylhet Division",
        "Zone-C": "Rajshahi & Rangpur Division",
        "Zone-D": "Khulna & Barishal Division"
    }
    
    selected_zone = st.selectbox(
        "Select Zone",
        options=zones,
        format_func=lambda x: f"{x} - {zone_labels.get(x, x)}"
    )
    
    # ========== Step 4: Select Items ==========
    st.markdown("### Step 4: Select Items")
    
    # ✅ FIX: Load rates from tenant book with proper connection
    boq_gen = BOQGenerator()
    rates_df = boq_gen.get_tenant_rates(company_id, rate_source)
    
    if rates_df.empty:
        st.warning(f"No rates found in {rate_source} rate book")
        if rate_source != 'CUSTOM' and st.button(f"🔄 Clone {rate_source} Master Rates"):
            st.session_state.page = "company_rate_management"
            st.rerun()
        return
    
    st.success(f"📋 Loaded {len(rates_df)} rate items")
    
    # Search filter
    search_term = st.text_input("🔍 Search items", placeholder="Item code or description...")
    if search_term:
        rates_df = rates_df[
            rates_df['item_code'].str.contains(search_term, case=False, na=False) |
            rates_df['description'].str.contains(search_term, case=False, na=False)
        ]
        st.caption(f"Showing {len(rates_df)} matching items")
    
    # ✅ FIX: Create BOQ with proper connection handling
    if can_create and 'current_boq_id' not in st.session_state:
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get version info
            cursor.execute("""
                SELECT version_id FROM tenant_rate_books WHERE id = ?
            """, (selected_book_id,))
            version_info = cursor.fetchone()
            
            cursor.execute("""
                INSERT INTO boq_generation_history (
                    user_id, company_id, tender_id, tender_title, procuring_entity,
                    selected_zone, rate_source, rate_book_id, status, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
            """, (
                st.session_state.get('user_id', 0), company_id, tender_info['tender_id'], 
                tender_info['tender_title'], tender_info.get('procuring_entity', ''),
                selected_zone, rate_source, selected_book_id, datetime.now()
            ))
            
            st.session_state.current_boq_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error creating BOQ: {e}")
            return
    elif not can_create:
        st.info("🔒 You don't have permission to create BOQ. View existing BOQs in the History tab.")
        return
    
    # ========== Display Items and Add to BOQ ==========
    st.markdown("#### Add Items to BOQ")
    
    items_per_page = 15
    total_pages = (len(rates_df) + items_per_page - 1) // items_per_page if len(rates_df) > 0 else 1
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1) - 1
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rates_df))
    
    for idx in range(start_idx, end_idx):
        row = rates_df.iloc[idx]
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 1, 1, 1.5, 1])
            
            with col1:
                st.markdown(f"**{row['item_code']}**")
            with col2:
                st.markdown(row['description'][:70])
            with col3:
                st.markdown(row['unit'])
            with col4:
                st.markdown(f"BDT {row['rate']:,.2f}")
            with col5:
                quantity = st.number_input(
                    "Qty",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"master_qty_{row['item_code']}_{idx}",
                    label_visibility="collapsed"
                )
            with col6:
                if quantity > 0 and can_edit:
                    if st.button("➕ Add", key=f"add_master_{row['item_code']}_{idx}"):
                        success, msg = boq_ui.add_custom_item(
                            boq_id=st.session_state.current_boq_id,
                            item_code=row['item_code'],
                            description=row['description'],
                            unit=row['unit'],
                            quantity=quantity,
                            unit_rate=row['rate']
                        )
                        if success:
                            st.success(f"Added {row['item_code']}")
                            st.rerun()
                        else:
                            st.error(msg)
    
    # ========== Add Custom Items ==========
    if can_edit:
        st.markdown("---")
        st.markdown("### Add Custom Items (Not in Rate Book)")
        
        with st.expander("➕ Add Custom Item", expanded=False):
            with st.form("custom_item_form"):
                col1, col2 = st.columns(2)
                with col1:
                    custom_code = st.text_input("Item Code", placeholder="e.g., CUSTOM-001")
                    custom_desc = st.text_input("Description", placeholder="Item description")
                    custom_unit = st.text_input("Unit", placeholder="e.g., sqm, cum, each")
                with col2:
                    custom_quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
                    custom_rate = st.number_input("Unit Rate (BDT)", min_value=0.0, value=1000.0, step=100.0)
                    custom_notes = st.text_area("Notes (optional)", placeholder="Any additional notes...")
                
                submitted = st.form_submit_button("Add Custom Item")
                
                if submitted and custom_code and custom_desc:
                    success, msg = boq_ui.add_custom_item(
                        boq_id=st.session_state.current_boq_id,
                        item_code=custom_code,
                        description=custom_desc,
                        unit=custom_unit,
                        quantity=custom_quantity,
                        unit_rate=custom_rate,
                        notes=custom_notes
                    )
                    if success:
                        st.success("Custom item added!")
                        st.rerun()
                    else:
                        st.error(msg)
    
    # ========== Review BOQ ==========
    st.markdown("---")
    st.markdown("### Review BOQ")
    
    try:
        conn = db.get_connection()
        boq_items = pd.read_sql_query("""
            SELECT id, item_code, description, unit, quantity, unit_rate, total, is_custom, notes
            FROM boq_items
            WHERE boq_id = ?
            ORDER BY is_custom DESC, item_code
        """, conn, params=[st.session_state.current_boq_id])
        conn.close()
    except Exception as e:
        st.error(f"Error loading BOQ items: {e}")
        return
    
    if boq_items.empty:
        st.info("No items added yet. Add items from rate book or custom items above.")
    else:
        # Display items with edit/remove options
        st.markdown("#### Current BOQ Items")
        
        for _, item in boq_items.iterrows():
            with st.container():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 3, 1, 1, 1, 1, 0.8])
                
                with col1:
                    st.markdown(f"**{item['item_code']}**")
                    if item['is_custom']:
                        st.caption("🆕 Custom")
                with col2:
                    st.markdown(item['description'][:60])
                with col3:
                    st.markdown(item['unit'])
                with col4:
                    if can_edit:
                        new_qty = st.number_input(
                            "Qty",
                            min_value=0.0,
                            value=float(item['quantity']),
                            step=1.0,
                            key=f"edit_qty_{item['id']}",
                            label_visibility="collapsed"
                        )
                        if new_qty != item['quantity']:
                            boq_ui.update_boq_item_quantity(item['id'], new_qty)
                            st.rerun()
                    else:
                        st.markdown(f"{item['quantity']:,.2f}")
                with col5:
                    st.markdown(f"BDT {item['unit_rate']:,.2f}")
                with col6:
                    st.markdown(f"BDT {item['total']:,.2f}")
                with col7:
                    if can_edit and st.button("🗑️", key=f"remove_{item['id']}"):
                        boq_ui.remove_boq_item(item['id'])
                        st.rerun()
                
                st.markdown("---")
        
        # BOQ Summary
        total_cost = boq_items['total'].sum()
        master_items = len(boq_items[boq_items['is_custom'] == 0])
        custom_items = len(boq_items[boq_items['is_custom'] == 1])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(boq_items))
        with col2:
            st.metric("Rate Book Items", master_items)
        with col3:
            st.metric("Custom Items", custom_items)
        with col4:
            st.metric("Total Cost", f"BDT {total_cost:,.2f}")
        
        # Action buttons
        if can_edit:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Generate Final BOQ", type="primary", use_container_width=True):
                    try:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE boq_generation_history 
                            SET item_count = ?, total_estimated_cost = ?, status = 'completed'
                            WHERE id = ?
                        """, (len(boq_items), total_cost, st.session_state.current_boq_id))
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ BOQ generated successfully!")
                        st.balloons()
                        
                        # Show download option
                        boq_data = boq_items[['item_code', 'description', 'unit', 'quantity', 'unit_rate', 'total']]
                        csv = boq_data.to_csv(index=False)
                        st.download_button(
                            "📥 Download BOQ (CSV)",
                            csv,
                            f"boq_{tender_info['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
                    except Exception as e:
                        st.error(f"Error generating BOQ: {e}")
            
            with col2:
                if st.button("🗑️ Clear All Items", use_container_width=True):
                    try:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM boq_items WHERE boq_id = ?", (st.session_state.current_boq_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing items: {e}")

def _render_boq_history(boq_ui, company_id, permissions):
    """Render BOQ history for the company"""
    
    st.markdown("### 📋 BOQ History")
    st.caption("View all BOQs generated by your company")
    
    boqs = boq_ui.get_company_boqs(company_id)
    
    if boqs.empty:
        st.info("No BOQs found. Generate your first BOQ!")
        return
    
    # Display BOQs
    for _, boq in boqs.iterrows():
        with st.expander(f"📄 BOQ #{boq['id']} - {boq['tender_title'][:60]}..."):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Items", boq['item_count'])
            with col2:
                # Convert to float, default to 0.0 if None or invalid
                try:
                    total_cost = float(boq['total_estimated_cost']) if boq['total_estimated_cost'] is not None else 0.0
                    st.metric("Total Cost", f"BDT {total_cost:,.3f}")
                except (ValueError, TypeError):
                    st.metric("Total Cost", "BDT 0.000")
            with col3:
                st.metric("Zone", boq['selected_zone'])
            with col4:
                st.metric("Status", boq['status'].upper())
            
            st.caption(f"Generated: {boq['generated_at']} | Source: {boq['rate_source']}")
            
            # View details button (all can view)
            if st.button("📄 View Details", key=f"view_boq_{boq['id']}"):
                st.session_state.view_boq_id = boq['id']
                st.rerun()

    
    # Export option (if user has export permission)
    if permissions.get('can_export_data'):
        csv = boqs.to_csv(index=False)
        st.download_button(
            "📥 Export BOQ History (CSV)",
            csv,
            f"boq_history_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )