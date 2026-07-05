# modules/boq_generator_ui.py - Refactored to use crud_boq and crud_rates

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import get_db_manager
from modules.boq_generator import BOQGenerator
from modules.rbac import (
    rbac, can_view_boq, can_create_boq, can_edit_boq, 
    can_delete_boq, can_export_data, render_role_badge
)


def render_boq_generator():
    """BOQ Generator UI - Refactored to use crud_boq and crud_rates"""
    
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
    
    # ✅ Use cached db manager
    db = get_db_manager()
    
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id', 0)
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    boq_gen = BOQGenerator(db)
    permissions = rbac.get_current_user_permissions()
    can_create = permissions.get('can_create_boq', False)
    
    # ========== STEP 1: Select Rate Book ==========
    st.markdown("### 📋 Step 1: Select Rate Book")
    
    # ✅ Use crud_rates method
    rate_books = db.get_company_rate_books(company_id)
    
    if not rate_books:
        st.warning("⚠️ No rate books found. Please create or clone rate books first.")
        if st.button("📋 Go to Rate Management"):
            st.session_state.page = "company_rate_management"
            st.rerun()
        return
    
    book_options = {}
    for book in rate_books:
        label = f"{book.get('name', 'Unnamed')} ({book.get('source_type', 'Unknown')})"
        if book.get('custom_source'):
            label += f" - {book.get('custom_source')}"
        if book.get('is_demo'):
            label += " 📌"
        book_options[book.get('id')] = label
    
    col1, col2 = st.columns(2)
    with col1:
        selected_book_id = st.selectbox(
            "Select Rate Book",
            options=list(book_options.keys()),
            format_func=lambda x: book_options.get(x, "Unknown"),
            key="boq_rate_book"
        )
    
    # ✅ Get version using crud_rates method
    version = db.get_rate_book_version(selected_book_id)
    if not version:
        st.error("No active version found for this rate book.")
        return
    
    with col2:
        st.info(f"📖 Version: {version.get('name', 'Unknown')}")
    
    pricing_level = st.selectbox(
        "Pricing Level",
        options=["AGGRESSIVE", "COMPETITIVE", "STANDARD", "PWD_OFFICIAL"],
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
        
        # ========== ✅ ADD COLUMN DETECTION HERE ==========
        # Detect columns for debugging
        def find_column(df, possible_names):
            """Find a column in DataFrame by trying multiple possible names"""
            df_cols_lower = [col.lower().strip() for col in df.columns]
            for name in possible_names:
                name_lower = name.lower().strip()
                if name_lower in df_cols_lower:
                    idx = df_cols_lower.index(name_lower)
                    return df.columns[idx]
            return None
        
        code_col = find_column(df_boq, ['Item Code (if any)', 'Item Code', 'Code', 'item_code', 'Item No', 'Sl No'])
        desc_col = find_column(df_boq, ['Description of Item', 'Description', 'description', 'Item Description', 'Particulars'])
        qty_col = find_column(df_boq, ['Quantity', 'Qty', 'qty', 'quantity'])
        unit_col = find_column(df_boq, ['Measurement Unit', 'Unit', 'unit', 'UOM'])
        
        # ✅ Add the debug expander here
        with st.expander("🔍 Column Detection", expanded=False):
            st.write("**Detected columns in your file:**")
            st.write(f"- Code column: **{code_col or 'Not found'}**")
            st.write(f"- Description column: **{desc_col or 'Not found'}**")
            st.write(f"- Quantity column: **{qty_col or 'Not found'}**")
            st.write(f"- Unit column: **{unit_col or 'Not found'}**")
            st.write("**Sample data (first 3 rows):**")
            st.dataframe(df_boq.head(3))
            
            if not desc_col:
                st.warning("⚠️ **Description column not found!** Please ensure your file has a 'Description' column.")
            if not qty_col:
                st.warning("⚠️ **Quantity column not found!** Please ensure your file has a 'Quantity' column.")
        
        # ========== STEP 4: Match Rates ==========
        st.markdown("### 🔍 Step 3: Match Rates")
        
        # Store selected values in session state
        if 'boq_selected_book_id' not in st.session_state:
            st.session_state.boq_selected_book_id = selected_book_id
        if 'boq_version_id' not in st.session_state:
            st.session_state.boq_version_id = version.get('id')
        if 'boq_pricing_level' not in st.session_state:
            st.session_state.boq_pricing_level = pricing_level
        
        # Load rates using BOQGenerator (which uses crud_rates)
        rates_result = boq_gen.get_rates_from_book(
            st.session_state.boq_selected_book_id, 
            st.session_state.boq_version_id, 
            st.session_state.boq_pricing_level
        )
        
        # Convert to DataFrame
        if isinstance(rates_result, list):
            rates_df = pd.DataFrame(rates_result) if rates_result else pd.DataFrame()
        else:
            rates_df = rates_result
        
        if rates_df.empty:
            st.error(f"No rates found for {book_options.get(selected_book_id, 'selected')} book with {pricing_level} pricing.")
            return
        
        st.info(f"📊 Loaded {len(rates_df)} rates from {book_options.get(selected_book_id, '')} with {pricing_level} pricing")
        
        if st.button("🚀 Match Items with Rates", type="primary", use_container_width=True):
            with st.spinner("Matching items..."):
                st.session_state.boq_selected_book_id = selected_book_id
                st.session_state.boq_version_id = version.get('id')
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
            # ✅ Get tenders using crud_tender method
            tenders = db.get_company_tenders(company_id)
            
            if not tenders:
                st.warning("⚠️ No tenders found. Please create a tender first or use Quick Estimate mode.")
                is_quick_boq = True
            else:
                tender_options = ["-- Select Tender --"]
                tender_map = {}
                for tender in tenders:
                    label = f"{tender.get('tender_id')} - {tender.get('tender_title', '')[:50]} (BDT {tender.get('official_estimate', 0):,.3f})"
                    tender_options.append(label)
                    tender_map[label] = tender.get('id')
                
                selected_tender_label = st.selectbox(
                    "Select Tender",
                    options=tender_options,
                    key="boq_tender_select"
                )
                
                if selected_tender_label and selected_tender_label != "-- Select Tender --":
                    tender_id = tender_map.get(selected_tender_label)
                    if tender_id:
                        tender_row = next((t for t in tenders if t.get('id') == tender_id), None)
                        if tender_row:
                            selected_tender_id = tender_row.get('tender_id')
                            tender_title = tender_row.get('tender_title', '')
                            procuring_entity = tender_row.get('procuring_entity', '')
                            official_estimate = tender_row.get('official_estimate', 0)
                            is_quick_boq = False
                            st.success(f"✅ Linked to: {tender_title}")
                        else:
                            is_quick_boq = True
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
                    
                    # ✅ Use BOQGenerator's create_boq (which uses crud_boq)
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
                    
                    if boq_id:
                        # ✅ Add BOQ items using crud_boq
                        boq_gen.add_boq_items(boq_id, result['matched'])
                        
                        st.success(f"✅ BOQ #{boq_id} saved successfully! ({'Quick' if is_quick_boq else 'Formal'})")
                        st.session_state.saved_boq_id = boq_id
                    else:
                        st.error("Failed to save BOQ")
        
        with col3:
            if st.session_state.get('saved_boq_id'):
                boq_id = st.session_state.saved_boq_id
                if st.button("🔒 Lock BOQ as Final", use_container_width=True):
                    # ✅ Use BOQGenerator's lock_boq (which uses crud_boq)
                    boq_gen.lock_boq(boq_id, user_id)
                    st.success("🔒 BOQ locked successfully!")
                    st.balloons()
                    
                    # ✅ Get BOQ data using crud_boq
                    boq_data = boq_gen.get_boq_by_id(boq_id)
                    if boq_data:
                        items = boq_data.get('items', [])
                        matched = [dict(item) for item in items]
                        boq_info = boq_data.get('boq', {})
                        
                        excel_file = boq_gen.generate_boq_excel(
                            matched, [], 
                            {
                                'tender_id': boq_info.get('tender_id', 'N/A'),
                                'tender_title': boq_info.get('tender_title', 'N/A'),
                                'rate_source': boq_info.get('rate_source', 'N/A'),
                                'selected_zone': boq_info.get('selected_zone', 'N/A')
                            },
                            boq_info.get('total_estimated_cost', 0)
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
        
        # ✅ Get BOQ history using crud_boq
        boq_history = db.get_company_boqs(company_id, limit=20)
        
        if boq_history:
            display_data = []
            for boq in boq_history:
                display_data.append({
                    'id': boq.get('id'),
                    'tender_id': boq.get('tender_id', 'N/A'),
                    'tender_title': boq.get('tender_title', '')[:50],
                    'item_count': boq.get('item_count', 0),
                    'total_estimated_cost': f"BDT {boq.get('total_estimated_cost', 0):,.2f}" if boq.get('total_estimated_cost') else "N/A",
                    'status': boq.get('status', 'draft'),
                    'is_locked': "🔒" if boq.get('is_locked') else "📝",
                    'type': "⚡ Quick" if boq.get('is_quick_boq') else "📋 Formal",
                    'generated_at': boq.get('generated_at', '')
                })
            
            st.dataframe(
                pd.DataFrame(display_data),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "tender_id": st.column_config.TextColumn("Tender ID", width="small"),
                    "tender_title": st.column_config.TextColumn("Title", width="large"),
                    "item_count": st.column_config.NumberColumn("Items", width="small"),
                    "total_estimated_cost": st.column_config.TextColumn("Total Cost", width="medium"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                    "is_locked": st.column_config.TextColumn("Lock", width="small"),
                    "type": st.column_config.TextColumn("Type", width="small"),
                    "generated_at": st.column_config.DatetimeColumn("Generated", width="medium")
                }
            )
            
            # Unlock option for admins
            if user_role in ['admin', 'system_admin', 'company_admin']:
                locked_boqs = [b for b in boq_history if b.get('is_locked')]
                if locked_boqs:
                    with st.expander("🔓 Admin: Unlock BOQ"):
                        boq_to_unlock = st.selectbox(
                            "Select Locked BOQ to Unlock",
                            options=[b.get('id') for b in locked_boqs],
                            format_func=lambda x: f"BOQ #{x} - {next((b.get('tender_id') for b in locked_boqs if b.get('id') == x), 'N/A')}"
                        )
                        if st.button("🔓 Unlock BOQ"):
                            # Add unlock method to BOQGenerator or crud_boq
                            boq_gen.unlock_boq(boq_to_unlock, user_id)
                            st.success(f"✅ BOQ #{boq_to_unlock} unlocked!")
                            st.rerun()
        else:
            st.info("No BOQ history found.")


# Add unlock method to BOQGenerator if not exists
def _add_unlock_method():
    """Helper to add unlock method if not exists"""
    if not hasattr(BOQGenerator, 'unlock_boq'):
        def unlock_boq(self, boq_id: int, user_id: int):
            """Unlock a BOQ"""
            return self.db.unlock_boq(boq_id, user_id)
        BOQGenerator.unlock_boq = unlock_boq