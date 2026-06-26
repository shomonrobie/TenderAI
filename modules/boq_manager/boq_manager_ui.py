# modules/boq_manager_ui.py

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from modules.rbac import render_role_badge, can_view_boq, can_edit_boq, can_delete_boq
from modules.tender_selector import render_tender_selector

DB_PATH = "data/tender_system.db"


def render_boq_manager(db=None):
    """BOQ Manager - View all BOQs with tender linkage and three-level costing"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📋 BOQ Manager</h1>
        <p>View, manage, and analyze all BOQs with three-level costing</p>
    </div>
    """, unsafe_allow_html=True)
    
    render_role_badge()
    st.markdown("---")
    
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    if not can_view_boq():
        st.error("🔒 You don't have permission to view BOQs.")
        return
    
    # ========== FILTERS ==========
    st.markdown("### 🔍 Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=["All", "draft", "completed", "locked", "submitted"],
            index=0
        )
    
    with col2:
        # Get tenders for filter
        conn = sqlite3.connect(DB_PATH)
        tenders_df = pd.read_sql_query("""
            SELECT DISTINCT tender_id, tender_title
            FROM boq_generation_history
            WHERE company_id = ?
            ORDER BY created_at DESC
        """, conn, params=[company_id])
        conn.close()
        
        tender_options = ["All"] + tenders_df['tender_id'].tolist()
        tender_filter = st.selectbox("Tender", options=tender_options)
    
    with col3:
        boq_type = st.selectbox(
            "BOQ Type",
            options=["All", "Quick", "Formal"],
            index=0
        )
    
    with col4:
        search_term = st.text_input("🔍 Search", placeholder="Search by tender ID or title...")
    
    # ========== LOAD BOQS ==========
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT 
            bh.id,
            bh.tender_id,
            bh.tender_title,
            bh.procuring_entity,
            bh.rate_source,
            bh.selected_zone,
            bh.item_count,
            bh.total_estimated_cost,
            bh.status,
            bh.is_locked,
            bh.is_quick_boq,
            bh.generated_at,
            bh.created_at,
            bh.updated_at,
            u.username as created_by,
            rb.name as rate_book_name
        FROM boq_generation_history bh
        LEFT JOIN users u ON bh.user_id = u.id
        LEFT JOIN tenant_rate_books rb ON bh.rate_book_id = rb.id
        WHERE bh.company_id = ?
    """
    params = [company_id]
    
    if status_filter != "All":
        query += " AND bh.status = ?"
        params.append(status_filter)
    
    if tender_filter != "All":
        query += " AND bh.tender_id = ?"
        params.append(tender_filter)
    
    if boq_type == "Quick":
        query += " AND bh.is_quick_boq = 1"
    elif boq_type == "Formal":
        query += " AND bh.is_quick_boq = 0"
    
    if search_term:
        query += " AND (bh.tender_id LIKE ? OR bh.tender_title LIKE ?)"
        params.extend([f"%{search_term}%", f"%{search_term}%"])
    
    query += " ORDER BY bh.created_at DESC"
    
    boqs = cursor.fetchall()
    conn.close()
    
    # ========== SUMMARY STATS ==========
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total BOQs", len(boqs))
    
    with col2:
        locked = sum(1 for b in boqs if b['is_locked'])
        st.metric("🔒 Locked", locked)
    
    with col3:
        draft = sum(1 for b in boqs if b['status'] == 'draft')
        st.metric("📝 Draft", draft)
    
    with col4:
        completed = sum(1 for b in boqs if b['status'] == 'completed')
        st.metric("✅ Completed", completed)
    
    with col5:
        quick = sum(1 for b in boqs if b['is_quick_boq'])
        st.metric("⚡ Quick BOQs", quick)
    
    st.divider()
    
    # ========== BOQ LIST ==========
    if not boqs:
        st.info("No BOQs found. Generate your first BOQ using the BOQ Generator.")
        if st.button("📊 Go to BOQ Generator"):
            st.session_state.page = "boq_generator"
            st.rerun()
        return
    
    # ✅ Display BOQs in cards
    for boq in boqs:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2.5, 1.5, 1.5, 1])
            
            with col1:
                # BOQ Header
                boq_type_icon = "⚡ Quick" if boq['is_quick_boq'] else "📋 Formal"
                lock_icon = "🔒" if boq['is_locked'] else "📝"
                
                st.markdown(f"### {lock_icon} BOQ #{boq['id']} - {boq_type_icon}")
                st.markdown(f"**Tender:** {boq['tender_id']} - {boq['tender_title'][:60]}...")
                st.caption(f"**Entity:** {boq['procuring_entity'] or 'N/A'}")
                
                if boq['rate_book_name']:
                    st.caption(f"**Rate Book:** {boq['rate_book_name']}")
            
            with col2:
                st.markdown("**📊 Summary**")
                st.write(f"Items: {boq['item_count'] or 0}")
                st.write(f"Status: {boq['status'].upper()}")
                
                # Total cost
                total_cost = boq['total_estimated_cost'] or 0
                st.write(f"Total: BDT {total_cost:,.3f}")
            
            with col3:
                st.markdown("**📅 Dates**")
                st.write(f"Created: {boq['created_at'][:16] if boq['created_at'] else 'N/A'}")
                st.write(f"Generated: {boq['generated_at'][:16] if boq['generated_at'] else 'N/A'}")
            
            with col4:
                # Action buttons
                if st.button("👁️ View Details", key=f"view_{boq['id']}"):
                    st.session_state.view_boq_id = boq['id']
                    st.rerun()
                
                if boq['is_locked'] and user_role in ['admin', 'system_admin', 'company_admin']:
                    if st.button("🔓 Unlock", key=f"unlock_{boq['id']}"):
                        _unlock_boq(boq['id'])
                        st.rerun()
                
                if st.button("📄 Export", key=f"export_{boq['id']}"):
                    st.session_state.export_boq_id = boq['id']
                    st.rerun()
    
    # ========== BOQ DETAILS VIEW ==========
    if st.session_state.get('view_boq_id'):
        boq_id = st.session_state.view_boq_id
        _render_boq_details(boq_id, company_id)
    
    # ========== EXPORT HANDLER ==========
    if st.session_state.get('export_boq_id'):
        boq_id = st.session_state.export_boq_id
        _export_boq(boq_id)
        st.session_state.export_boq_id = None


def _render_boq_details(boq_id: int, company_id: int):
    """Render detailed view of a BOQ with three-level costing"""
    
    st.divider()
    st.markdown("## 📊 BOQ Details")
    
    # ✅ Fetch BOQ with items
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get BOQ header
    cursor.execute("""
        SELECT 
            bh.*,
            u.username as created_by,
            rb.name as rate_book_name
        FROM boq_generation_history bh
        LEFT JOIN users u ON bh.user_id = u.id
        LEFT JOIN tenant_rate_books rb ON bh.rate_book_id = rb.id
        WHERE bh.id = ? AND bh.company_id = ?
    """, (boq_id, company_id))
    
    boq = cursor.fetchone()
    
    if not boq:
        st.error("BOQ not found")
        st.session_state.view_boq_id = None
        return
    
    # Get BOQ items
    cursor.execute("""
        SELECT 
            id, item_code, description, unit, quantity, unit_rate, total, is_custom, notes
        FROM boq_items
        WHERE boq_id = ?
        ORDER BY is_custom DESC, item_code
    """, (boq_id,))
    
    items = cursor.fetchall()
    conn.close()
    
    # ✅ BOQ Header
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**BOQ ID:** {boq['id']}")
        st.markdown(f"**Tender:** {boq['tender_id']}")
        st.markdown(f"**Title:** {boq['tender_title'][:100]}...")
    
    with col2:
        st.markdown(f"**Status:** {boq['status'].upper()}")
        st.markdown(f"**Locked:** {'✅ Yes' if boq['is_locked'] else '❌ No'}")
        st.markdown(f"**Type:** {'⚡ Quick' if boq['is_quick_boq'] else '📋 Formal'}")
    
    with col3:
        st.markdown(f"**Rate Book:** {boq['rate_book_name'] or 'N/A'}")
        st.markdown(f"**Rate Source:** {boq['rate_source'] or 'N/A'}")
        st.markdown(f"**Zone:** {boq['selected_zone'] or 'N/A'}")
    
    st.divider()
    
    # ✅ Show items with three-level costing
    if items:
        st.markdown("### 📋 BOQ Items")
        
        # ✅ Calculate three-level costs if available
        # For each item, we need to get the three cost levels from the rate book
        # If not available, we use unit_rate as competitive and derive others
        
        item_data = []
        total_aggressive = 0
        total_competitive = 0
        total_standard = 0
        
        for item in items:
            item_code = item['item_code']
            description = item['description']
            unit = item['unit']
            quantity = item['quantity']
            unit_rate = item['unit_rate'] or 0
            
            # Try to get three-level costs from rate books
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pricing_level, price
                FROM tenant_pricing_levels
                WHERE rate_item_id IN (
                    SELECT id FROM tenant_rate_items
                    WHERE item_code = ? AND is_active = 1
                )
                AND rate_version_id IN (
                    SELECT id FROM tenant_rate_versions
                    WHERE rate_book_id IN (
                        SELECT id FROM tenant_rate_books
                        WHERE tenant_id = ? AND is_active = 1 AND is_archived = 0
                    )
                    AND is_current = 1
                )
                ORDER BY pricing_level
            """, (item_code, company_id))
            
            pricing = cursor.fetchall()
            conn.close()
            
            aggressive_rate = 0
            competitive_rate = unit_rate
            standard_rate = 0
            
            for p in pricing:
                if p['pricing_level'] == 'AGGRESSIVE':
                    aggressive_rate = p['price']
                elif p['pricing_level'] == 'COMPETITIVE':
                    competitive_rate = p['price']
                elif p['pricing_level'] == 'STANDARD':
                    standard_rate = p['price']
            
            # If no rates found, derive from unit_rate
            if competitive_rate == 0 and unit_rate > 0:
                competitive_rate = unit_rate
                aggressive_rate = unit_rate * 0.85
                standard_rate = unit_rate * 1.15
            
            # Calculate totals
            total_agg = aggressive_rate * quantity
            total_comp = competitive_rate * quantity
            total_std = standard_rate * quantity
            
            total_aggressive += total_agg
            total_competitive += total_comp
            total_standard += total_std
            
            item_data.append({
                'Item Code': item_code,
                'Description': description[:60],
                'Unit': unit,
                'Quantity': quantity,
                'Aggressive Rate': f"BDT {aggressive_rate:,.2f}" if aggressive_rate > 0 else 'N/A',
                'Competitive Rate': f"BDT {competitive_rate:,.2f}" if competitive_rate > 0 else 'N/A',
                'Standard Rate': f"BDT {standard_rate:,.2f}" if standard_rate > 0 else 'N/A',
                'Total (Comp)': f"BDT {total_comp:,.2f}",
            })
        
        # ✅ Display items table
        df = pd.DataFrame(item_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # ✅ Three-Level Cost Summary
        st.divider()
        st.markdown("### 💰 Three-Level Cost Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(items))
        
        with col2:
            st.metric(
                "🟢 Aggressive Cost", 
                f"BDT {total_aggressive:,.3f}",
                f"{len([i for i in items if i['unit_rate'] > 0])} items with rates"
            )
        
        with col3:
            st.metric(
                "🟡 Competitive Cost", 
                f"BDT {total_competitive:,.3f}",
                f"{len([i for i in items if i['unit_rate'] > 0])} items with rates"
            )
        
        with col4:
            st.metric(
                "🔴 Standard Cost", 
                f"BDT {total_standard:,.3f}",
                f"{len([i for i in items if i['unit_rate'] > 0])} items with rates"
            )
        
        # ✅ Save three-level costs to session
        st.session_state.boq_three_level_costs = {
            'aggressive': total_aggressive,
            'competitive': total_competitive,
            'standard': total_standard
        }
        
        # ✅ Chart showing cost comparison
        st.markdown("### 📊 Cost Level Comparison")
        cost_data = pd.DataFrame({
            'Cost Level': ['Aggressive', 'Competitive', 'Standard'],
            'Total Cost': [total_aggressive, total_competitive, total_standard]
        })
        st.bar_chart(cost_data.set_index('Cost Level'))
        
        # ✅ Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export as CSV", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    csv,
                    f"boq_{boq['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        
        with col2:
            if st.button("📤 Export Three-Level Costs", use_container_width=True):
                cost_data = pd.DataFrame({
                    'Cost Level': ['Aggressive', 'Competitive', 'Standard'],
                    'Total': [total_aggressive, total_competitive, total_standard]
                })
                csv = cost_data.to_csv(index=False)
                st.download_button(
                    "📥 Download Costs",
                    csv,
                    f"boq_costs_{boq['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        
        with col3:
            if st.button("🔒 Close Details", use_container_width=True):
                st.session_state.view_boq_id = None
                st.rerun()
    
    else:
        st.info("No items found in this BOQ")


def _unlock_boq(boq_id: int):
    """Unlock a BOQ (admin only)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE boq_generation_history 
            SET is_locked = 0, locked_at = NULL, locked_by = NULL, status = 'draft'
            WHERE id = ?
        """, (boq_id,))
        conn.commit()
        conn.close()
        st.success(f"✅ BOQ #{boq_id} unlocked successfully!")
    except Exception as e:
        st.error(f"Error unlocking BOQ: {e}")


def _export_boq(boq_id: int):
    """Export BOQ to Excel"""
    try:
        from modules.boq_generator import BOQGenerator
        boq_gen = BOQGenerator()
        boq_data = boq_gen.get_boq_by_id(boq_id)
        
        if boq_data:
            items = boq_data['items']
            matched = [dict(item) for item in items]
            excel_file = boq_gen.generate_boq_excel(
                matched, [], 
                {'tender_id': boq_data['boq'].get('tender_id', 'N/A'),
                 'tender_title': boq_data['boq'].get('tender_title', 'N/A'),
                 'rate_source': boq_data['boq'].get('rate_source', 'N/A'),
                 'selected_zone': boq_data['boq'].get('selected_zone', 'N/A')},
                boq_data['boq'].get('total_estimated_cost', 0)
            )
            
            st.download_button(
                "📥 Download BOQ Excel",
                excel_file,
                f"boq_{boq_data['boq'].get('tender_id', 'N/A')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error exporting BOQ: {e}")


def render_boq_manager_page(db=None):
    """Page wrapper for BOQ Manager"""
    render_boq_manager(db)