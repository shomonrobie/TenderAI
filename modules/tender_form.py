# modules/tender_form.py
"""
Tender Create/Edit Form - Standalone module with PDF upload support
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from utils.helpers import format_currency_bd
from modules.rbac import can_edit_tender

def render_tender_form():
    """Render the tender create/edit form as a standalone page with PDF upload"""
    
    # Check if we're in edit mode
    is_editing = st.session_state.get('edit_mode', False)
    
    # Load data if editing
    if is_editing and st.session_state.get('extracted_data'):
        data = st.session_state.extracted_data
        st.success(f"✏️ Editing Tender #{st.session_state.get('edit_tender_id')}")
    else:
        data = {}
        st.info("➕ Create New Tender")
    
    # Back button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Tenders", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_tender_id = None
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
            st.session_state.page = "tender_management"
            st.session_state.active_tab = "📊 Dashboard"
            st.rerun()
    
    st.markdown("---")
    
    # =========================================================
    # PDF UPLOAD SECTION (for new tenders only)
    # =========================================================
    if not is_editing:
        st.subheader("📄 Quick Import from PDF (Optional)")
        st.caption("Upload a tender notice PDF to auto-fill the form below")
        
        uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'], key="tender_form_pdf_uploader")
        
        if uploaded_pdf:
            if st.session_state.get('extracted_data') is None or st.session_state.get('last_pdf') != uploaded_pdf.name:
                try:
                    from modules.pdf_parser import parse_tender_pdf
                    with st.spinner("🔍 Parsing PDF..."):
                        parsed = parse_tender_pdf(uploaded_pdf)
                    if parsed:
                        st.session_state.extracted_data = parsed
                        st.session_state.last_pdf = uploaded_pdf.name
                        st.session_state.skip_review = False
                        st.success("✅ PDF parsed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error parsing PDF: {str(e)}")
        
        # Show review if data was parsed
        if st.session_state.get('extracted_data') and not st.session_state.get('skip_review', False):
            from modules.pdf_review import display_review_page
            def confirm_review():
                st.session_state.skip_review = True
                st.rerun()
            display_review_page(st.session_state.extracted_data, confirm_review)
            return
        
        st.markdown("---")
        st.subheader("📝 Or Enter Manually")
    
    # =========================================================
    # MAIN FORM
    # =========================================================
    
    # Get data source (from PDF or manual)
    if st.session_state.get('skip_review', False) and st.session_state.get('extracted_data'):
        data = st.session_state.extracted_data
    elif is_editing and st.session_state.get('extracted_data'):
        data = st.session_state.extracted_data
    else:
        data = {}
    
    # Set default values
    default_values = {
        'tender_id': str(data.get('tender_id', '')) if data else '',
        'tender_title': str(data.get('tender_title', '')) if data else '',
        'procuring_entity': str(data.get('procuring_entity', '')) if data else '',
        'division': str(data.get('division', 'Dhaka')) if data else 'Dhaka',
        'procurement_type': str(data.get('procurement_type', 'works')) if data else 'works',
        'official_estimate': float(data.get('official_estimate', 0.0)) if data else 0.0,
        'submission_deadline': data.get('submission_deadline', datetime.now().date()) if data else datetime.now().date(),
        'tender_security': float(data.get('tender_security', 0.0)) if data else 0.0,
        'document_fee': float(data.get('document_fee', 0.0)) if data else 0.0,
        'project_code': str(data.get('project_code', '')) if data else '',
        'project_name': str(data.get('project_name', '')) if data else '',
        'package_no': str(data.get('package_no', '')) if data else '',
        'budget_type': str(data.get('budget_type', 'Development')) if data else 'Development',
        'notes': str(data.get('notes', '')) if data else ''
    }
    
    # Main form
    with st.form("tender_form", clear_on_submit=False):
        st.markdown("### 📝 Core Tender Details")
        col1, col2 = st.columns(2)
        
        with col1:
            tender_id = st.text_input("Tender ID *", value=default_values['tender_id'], key="form_tender_id")
            tender_title = st.text_area("Tender Title *", value=default_values['tender_title'], height=80, key="form_tender_title")
            procuring_entity = st.text_input("Procuring Entity *", value=default_values['procuring_entity'], key="form_procuring_entity")
            divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            division_index = divisions.index(default_values['division']) if default_values['division'] in divisions else 0
            division = st.selectbox("Division", divisions, index=division_index, key="form_division")
        
        with col2:
            valid_pt = ["works", "goods", "services"]
            pt_index = valid_pt.index(default_values['procurement_type']) if default_values['procurement_type'] in valid_pt else 0
            procurement_type = st.selectbox("Procurement Type", valid_pt, index=pt_index, key="form_procurement_type")
            
            st.markdown("**Official Estimate (OCE) *️⃣**")
            st.caption("This is used for NPPI calculations in bid analysis")
            
            official_estimate = st.number_input(
                "Official Estimate (BDT) *", 
                min_value=0.0,
                step=1000000.0,
                value=default_values['official_estimate'],
                key="form_official_estimate",
                format="%0.3f",
                label_visibility="collapsed"
            )
            
            if official_estimate > 0:
                st.caption(f"💡 Formatted: {format_currency_bd(official_estimate)}")
            
            submission_deadline = st.date_input("Submission Deadline *", value=default_values['submission_deadline'], key="form_deadline")
            
            tender_security = st.number_input(
                "Tender Security (BDT)", 
                min_value=0.0,
                step=10000.0,
                value=default_values['tender_security'],
                key="form_security",
                format="%0.3f"
            )
            
            document_fee = st.number_input(
                "Document Fee (BDT)", 
                min_value=0.0,
                step=500.0,
                value=default_values['document_fee'],
                key="form_doc_fee",
                format="%0.3f"
            )
        
        with st.expander("📝 Additional Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                project_code = st.text_input("Project Code", value=default_values['project_code'], key="form_project_code")
                package_no = st.text_input("Package No.", value=default_values['package_no'], key="form_package_no")
                budget_type = st.text_input("Budget Type", value=default_values['budget_type'], key="form_budget_type")
            with col2:
                project_name = st.text_area("Project Name", value=default_values['project_name'], height=60, key="form_project_name")
                notes = st.text_area("Notes", value=default_values['notes'], height=60, key="form_notes")
        
        if official_estimate > 0:
            st.caption(f"💡 Formatted estimate: {format_currency_bd(official_estimate)}")
        
        # Submit button
        btn_text = "💾 Update Tender" if is_editing else "🚀 Create Tender"
        submitted = st.form_submit_button(btn_text, use_container_width=True, type="primary")
        
        # Clear form button (only for manual mode)
        if not is_editing and not st.session_state.get('skip_review', False):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col2:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.session_state.extracted_data = None
                    st.session_state.skip_review = False
                    st.session_state._last_pdf_name = None
                    st.rerun()
        
        if submitted:
            # Validate
            if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
                st.error("❌ Please fill all required fields marked with *")
                return
            
            tender_data = {
                'tender_id': tender_id,
                'tender_title': tender_title,
                'procuring_entity': procuring_entity,
                'division': division,
                'procurement_type': procurement_type,
                'official_estimate': official_estimate,
                'submission_deadline': submission_deadline,
                'tender_security': tender_security,
                'document_fee': document_fee,
                'project_code': project_code,
                'project_name': project_name,
                'package_no': package_no,
                'budget_type': budget_type,
                'notes': notes,
                'is_active': 1
            }
            
            # Import db here to avoid circular imports
            from database.unified_db_manager import UnifiedDatabaseManager
            db = UnifiedDatabaseManager()
            
            if is_editing:
                # Update existing tender
                if can_edit_tender():
                    success = db.update_tender(st.session_state.edit_tender_id, tender_data, st.session_state.user_id)
                    if success:
                        st.success("✅ Tender updated successfully!")
                        st.success(f"💰 OCE updated to: {format_currency_bd(official_estimate)}")
                        st.balloons()
                        # Clear session state
                        st.session_state.edit_mode = False
                        st.session_state.edit_tender_id = None
                        st.session_state.extracted_data = None
                        st.session_state.skip_review = False
                        st.session_state.page = "tender_management"
                        st.session_state.active_tab = "📊 Dashboard"
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to update tender")
                else:
                    st.error("❌ You don't have permission to edit this tender")
            else:
                # Create new tender
                tender_db_id = db.create_tender(st.session_state.company_id, tender_data, st.session_state.user_id)
                if tender_db_id:
                    st.success(f"✅ Tender '{tender_title}' created successfully!")
                    st.balloons()
                    # Clear PDF-related state
                    st.session_state.extracted_data = None
                    st.session_state.skip_review = False
                    st.session_state._last_pdf_name = None
                    st.session_state.page = "tender_management"
                    st.session_state.active_tab = "📊 Dashboard"
                    st.rerun()
                else:
                    st.error("❌ Failed to create tender. This might be because the Tender ID already exists.")