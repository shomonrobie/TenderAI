# modules/boq_generator_ui.py - COMPLETE FINAL VERSION

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from modules.boq_generator import BOQGenerator
from modules.rbac import (
    rbac, can_view_boq, can_create_boq, can_edit_boq, 
    can_delete_boq, can_export_data, render_role_badge
)

DB_PATH = "data/tender_system.db"


def render_boq_generator():
    """BOQ Generator UI - Complete version"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 BOQ Generator</h1>
        <p>Upload BOQ file, match rates from your rate books, and generate complete BOQ</p>
    </div>
    """, unsafe_allow_html=True)
    
    render_role_badge()
    st.markdown("---")
    
    # Check permissions
    if not can_view_boq():
        st.error("🔒 You don't have permission to view BOQ.")
        return
    
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id', 0)
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    boq_gen = BOQGenerator()
    permissions = rbac.get_current_user_permissions()
    can_create = permissions.get('can_create_boq', False)
    
    # ========== STEP 1: Select Rate Book ==========
    st.markdown("### 📋 Step 1: Select Rate Book")
    
    rate_books = boq_gen.get_company_rate_books(company_id)
    
    if not rate_books:
        st.warning("⚠️ No rate books found. Please create or clone rate books first.")
        if st.button("📋 Go to Rate Management"):
            st.session_state.page = "company_rate_management"
            st.rerun()
        return
    
    book_options = {}
    for book in rate_books:
        label = f"{book['name']} ({book['source_type']})"
        if book.get('custom_source'):
            label += f" - {book['custom_source']}"
        if book.get('is_demo'):
            label += " 📌"
        book_options[book['id']] = label
    
    col1, col2 = st.columns(2)
    with col1:
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="boq_rate_book"
        )
    
    # Get version
    version = boq_gen.get_rate_book_version(selected_book_id)
    if not version:
        st.error("No active version found for this rate book.")
        return
    
    with col2:
        st.info(f"📖 Version: {version['name']}")
    
    pricing_level = st.selectbox(
        "Pricing Level",
        options=["AGGRESSIVE", "COMPETITIVE", "STANDARD"],
        index=1,
        key="boq_pricing_level_select",
        help="Select which cost level to use for BOQ"
    )
    
    # ========== STEP 2: Upload BOQ File ==========
    st.markdown("### 📄 Step 2: Upload BOQ File")
    st.caption("Upload Excel or CSV file with columns: Item Code (optional), Description, Quantity, Unit")
    
    uploaded_file = st.file_uploader(
        "Choose file (Excel or CSV)",
        type=["xlsx", "xls", "csv"],
        key="boq_upload",
        label_visibility="collapsed"
    )
    
    if not uploaded_file:
        st.info("📤 Upload a BOQ file to get started")
        return
    
    # ========== STEP 3: Read and Process ==========
    try:
        # Read file
        if uploaded_file.name.endswith('.csv'):
            df_boq = pd.read_csv(uploaded_file)
        else:
            df_boq = pd.read_excel(uploaded_file)
        
        # Normalize columns
        df_boq.columns = df_boq.columns.str.strip()
        
        st.success(f"✅ Loaded {len(df_boq)} items from {uploaded_file.name}")
        
        # Show preview
        with st.expander("📊 File Preview", expanded=True):
            st.dataframe(df_boq.head(10), use_container_width=True)
            st.caption(f"Total items: {len(df_boq)}")
        
        # ========== STEP 4: Match Rates ==========
        st.markdown("### 🔍 Step 3: Match Rates")
        
        # Store selected values
        if 'boq_selected_book_id' not in st.session_state:
            st.session_state.boq_selected_book_id = selected_book_id
        if 'boq_version_id' not in st.session_state:
            st.session_state.boq_version_id = version['id']
        if 'boq_pricing_level' not in st.session_state:
            st.session_state.boq_pricing_level = pricing_level
        
        # Load rates from selected book
        rates_df = boq_gen.get_rates_from_book(
            st.session_state.boq_selected_book_id, 
            st.session_state.boq_version_id, 
            st.session_state.boq_pricing_level
        )
        
        if rates_df.empty:
            st.error(f"No rates found in {book_options.get(selected_book_id, 'selected')} book.")
            return
        
        st.info(f"📊 Loaded {len(rates_df)} rates from {book_options.get(selected_book_id, '')}")
        
        if st.button("🚀 Match Items with Rates", type="primary", use_container_width=True):
            with st.spinner("Matching items..."):
                st.session_state.boq_selected_book_id = selected_book_id
                st.session_state.boq_version_id = version['id']
                st.session_state.boq_pricing_level = pricing_level
                
                result = boq_gen.match_boq_items(df_boq, rates_df)
                
                st.session_state.boq_match_result = result
                st.session_state.boq_original_df = df_boq
                
                st.success(f"✅ Matched {result['total_matched']} items, {result['total_unmatched']} unmatched")
                st.rerun()
    
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return
    
    # ========== STEP 5: Show Results ==========
    if st.session_state.get('boq_match_result'):
        result = st.session_state.boq_match_result
        
        st.markdown("### 📊 Matching Results")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Matched", result['total_matched'])
        with col2:
            st.metric("❌ Unmatched", result['total_unmatched'])
        with col3:
            st.metric("💰 Total Cost", f"BDT {result['total_cost']:,.2f}")
        
        # Show matched items
        if result['matched']:
            with st.expander(f"✅ Matched Items ({result['total_matched']})", expanded=True):
                df_matched = pd.DataFrame(result['matched'])
                df_matched['Unit Rate'] = df_matched['Unit Rate'].apply(lambda x: f"{x:,.2f}")
                df_matched['Total'] = df_matched['Total'].apply(lambda x: f"{x:,.2f}")
                st.dataframe(df_matched, use_container_width=True)
        
        # Show unmatched items
        if result['unmatched']:
            with st.expander(f"❌ Unmatched Items ({result['total_unmatched']})", expanded=True):
                df_unmatched = pd.DataFrame(result['unmatched'])
                st.dataframe(df_unmatched, use_container_width=True)
                st.warning("⚠️ These items could not be matched. Please check item codes/descriptions.")
        
        # ========== STEP 6: BOQ Mode Selection ==========
        st.markdown("### 📋 Step 4: Select BOQ Mode")
        st.caption("Choose between Quick Estimate or Formal BOQ linked to a tender.")
        
        boq_mode = st.radio(
            "BOQ Mode",
            options=["Quick Estimate (No Tender)", "Formal BOQ (Link to Tender)"],
            index=0,
            horizontal=True,
            key="boq_mode_select"
        )
        
        is_quick_boq = (boq_mode == "Quick Estimate (No Tender)")
        selected_tender_id = None
        tender_title = "Untitled BOQ"
        procuring_entity = ""
        official_estimate = 0
        
        if boq_mode == "Formal BOQ (Link to Tender)":
            # Get tenders
            conn = sqlite3.connect(DB_PATH)
            tenders = pd.read_sql_query("""
                SELECT id, tender_id, tender_title, procuring_entity, official_estimate
                FROM company_tenders
                WHERE company_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, conn, params=[company_id])
            conn.close()
            
            if tenders.empty:
                st.warning("⚠️ No tenders found. Please create a tender first or use Quick Estimate mode.")
                is_quick_boq = True
                st.rerun()
            else:
                tender_options = ["-- Select Tender --"]
                tender_map = {}
                for _, row in tenders.iterrows():
                    label = f"{row['tender_id']} - {row['tender_title'][:50]} (BDT {row['official_estimate']:,.3f})"
                    tender_options.append(label)
                    tender_map[label] = row['id']
                
                selected_tender_label = st.selectbox(
                    "Select Tender",
                    options=tender_options,
                    key="boq_tender_select"
                )
                
                if selected_tender_label and selected_tender_label != "-- Select Tender --":
                    tender_id = tender_map.get(selected_tender_label)
                    if tender_id:
                        tender_row = tenders[tenders['id'] == tender_id].iloc[0]
                        selected_tender_id = tender_row['tender_id']
                        tender_title = tender_row['tender_title']
                        procuring_entity = tender_row.get('procuring_entity', '')
                        official_estimate = tender_row.get('official_estimate', 0)
                        is_quick_boq = False
                        st.success(f"✅ Linked to: {tender_title}")
                    else:
                        is_quick_boq = True
                else:
                    is_quick_boq = True
        else:
            st.info("📌 Quick Estimate mode: No tender required. BOQ will be saved as a draft.")
        
        # ========== STEP 7: Generate BOQ ==========
        st.markdown("### 📥 Step 5: Generate BOQ")
        st.caption(f"Mode: {'Quick Estimate' if is_quick_boq else 'Formal BOQ'}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 Generate Excel", type="primary", use_container_width=True):
                boq_info = {
                    'tender_id': selected_tender_id or 'N/A',
                    'tender_title': tender_title,
                    'rate_source': book_options.get(st.session_state.boq_selected_book_id, 'Unknown'),
                    'selected_zone': 'N/A'
                }
                
                excel_file = boq_gen.generate_boq_excel(
                    result['matched'], 
                    result['unmatched'],
                    boq_info,
                    result['total_cost']
                )
                
                st.download_button(
                    "📥 Download BOQ Excel",
                    excel_file,
                    f"boq_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col2:
            if can_create:
                if st.button("💾 Save BOQ", use_container_width=True):
                    if not selected_tender_id:
                        selected_tender_id = f"QBOQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        tender_title = f"Quick BOQ {datetime.now().strftime('%Y-%m-%d')}"
                        procuring_entity = "Quick Estimate"
                    
                    boq_id = boq_gen.create_boq(
                        user_id=user_id,
                        company_id=company_id,
                        tender_id=selected_tender_id,
                        tender_title=tender_title,
                        procuring_entity=procuring_entity,
                        rate_book_id=st.session_state.boq_selected_book_id,
                        version_id=st.session_state.boq_version_id,
                        selected_zone='N/A',
                        source_type=book_options.get(st.session_state.boq_selected_book_id, 'Unknown'),
                        is_quick_boq=is_quick_boq
                    )
                    
                    boq_gen.add_boq_items(boq_id, result['matched'])
                    
                    st.success(f"✅ BOQ #{boq_id} saved successfully! ({'Quick' if is_quick_boq else 'Formal'})")
                    st.session_state.saved_boq_id = boq_id
        
        with col3:
            if st.session_state.get('saved_boq_id'):
                boq_id = st.session_state.saved_boq_id
                if st.button("🔒 Lock BOQ as Final", use_container_width=True):
                    boq_gen.lock_boq(boq_id, user_id)
                    st.success("🔒 BOQ locked successfully!")
                    st.balloons()
                    
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
                            "📥 Download Final BOQ",
                            excel_file,
                            f"boq_final_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
        
        # ========== BOQ History ==========
        st.markdown("---")
        st.markdown("### 📋 BOQ History")
        
        conn = sqlite3.connect(DB_PATH)
        boq_history = pd.read_sql_query("""
            SELECT 
                id, tender_id, tender_title, item_count, total_estimated_cost,
                rate_source, status, is_locked, is_quick_boq, generated_at
            FROM boq_generation_history
            WHERE company_id = ?
            ORDER BY generated_at DESC
            LIMIT 20
        """, conn, params=[company_id])
        conn.close()
        
        if not boq_history.empty:
            display_df = boq_history.copy()
            display_df['is_locked'] = display_df['is_locked'].apply(lambda x: "🔒" if x else "📝")
            display_df['type'] = display_df['is_quick_boq'].apply(lambda x: "⚡ Quick" if x else "📋 Formal")
            display_df['total_estimated_cost'] = display_df['total_estimated_cost'].apply(
                lambda x: f"BDT {x:,.2f}" if x else "N/A"
            )
            
            st.dataframe(
                display_df[['id', 'tender_id', 'tender_title', 'item_count', 'total_estimated_cost', 'status', 'is_locked', 'type']],
                use_container_width=True,
                hide_index=True
            )
            
            # Unlock option for admins
            if user_role in ['admin', 'system_admin', 'company_admin']:
                locked_boqs = boq_history[boq_history['is_locked'] == 1]
                if not locked_boqs.empty:
                    with st.expander("🔓 Admin: Unlock BOQ"):
                        boq_to_unlock = st.selectbox(
                            "Select Locked BOQ to Unlock",
                            options=locked_boqs['id'].tolist(),
                            format_func=lambda x: f"BOQ #{x} - {locked_boqs[locked_boqs['id']==x]['tender_id'].iloc[0]}"
                        )
                        if st.button("🔓 Unlock BOQ"):
                            boq_gen.unlock_boq(boq_to_unlock, user_id)
                            st.success(f"✅ BOQ #{boq_to_unlock} unlocked!")
                            st.rerun()
        else:
            st.info("No BOQ history found.")