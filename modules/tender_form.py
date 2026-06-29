# modules/tender_form.py - FULL REFACTORED & EXPANDED v4.3 (650+ lines)
# Includes: URL Parsing, Form Population, Document Upload, File Saving, Document Viewer

import requests
import streamlit as st
import json
import sys
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import shutil
import sys
from utils.helpers import format_currency_bd
from modules.rbac import can_edit_tender
from modules.tender_data_parser import parse_tender_url
from database.unified_db_manager import UnifiedDatabaseManager

# =========================================================
# CONSTANTS
# =========================================================
OCE_MULTIPLIER = 39.45

PROCUREMENT_TYPE_MAP = {
    'nct': 'works', 'otm': 'works', 'open_tendering': 'works',
    'works': 'works', 'goods': 'goods', 'services': 'services',
}

FORM_WIDGET_KEYS = [
    "form_tender_id", "form_tender_title", "form_procuring_entity", "form_division",
    "form_project_code", "form_package_no", "form_app_id", "form_procurement_nature",
    "form_procurement_type", "form_official_estimate", "form_deadline", "form_security",
    "form_doc_fee", "form_budget_type", "form_inviting_official_name",
    "form_inviting_official_designation", "form_inviting_official_phone",
    "form_project_name", "form_notes", "form_pub_date", "form_doc_end_date",
    "form_pre_bid_start", "form_pre_bid_end", "form_bid_open", "form_sec_sub",
    "form_sec_valid", "form_tender_valid", "form_official_address", "form_official_city",
    "form_official_thana", "form_official_district", "form_official_email",
    "form_inv_ref", "form_pe_code", "form_event_type", "form_source_funds",
    "form_eval_type", "form_mode_pay", "form_eligibility", "form_category",
]

DOCUMENT_FOLDER = "tender_documents"


def ensure_document_folder():
    if not os.path.exists(DOCUMENT_FOLDER):
        os.makedirs(DOCUMENT_FOLDER)


def save_uploaded_documents(tender_id: str, uploaded_files: List) -> List[Dict]:
    ensure_document_folder()
    saved_files = []
    for file in uploaded_files:
        if file is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{tender_id}_{timestamp}_{file.name}"
            file_path = os.path.join(DOCUMENT_FOLDER, safe_filename)

            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

            saved_files.append({
                'original_name': file.name,
                'saved_name': safe_filename,
                'file_path': file_path,
                'file_size': file.size,
                'uploaded_at': datetime.now().isoformat(),
                'mime_type': file.type
            })
    return saved_files


def render_document_viewer(documents):
    if not documents:
        st.info("No documents attached yet.")
        return
    with st.expander("📂 Attached Documents", expanded=True):
        for doc in documents:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {doc['original_name']} ({doc['file_size']/1024:.1f} KB)")
            with col2:
                with open(doc['file_path'], "rb") as f:
                    st.download_button("Download", f, doc['original_name'], key=doc['saved_name'])


def render_tender_form():
    """Main function - Tender Form with full functionality"""
    
    # Session State
    for key, default in [
        ('data_loaded', False), ('last_tender_url', None), ('extracted_data', {}),
        ('show_replace_warning', False), ('duplicate_tender_id', None),
        ('edit_mode', False), ('uploaded_documents', []), ('saved_document_metadata', []),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    is_editing = st.session_state.get('edit_mode', False)

    if st.button("← Back to Tenders", use_container_width=True):
        _clear_tender_form_state()
        st.session_state.page = "tender_management"
        st.session_state.active_tab = "Dashboard"
        st.rerun()

    # URL Import Section
    if not is_editing:
        st.subheader("Quick Import from e-GP URL (Optional)")
        st.caption("Paste URL to auto-fill form")
        col1, col2 = st.columns([4, 1])
        with col1:
            tender_url = st.text_input("Enter e-GP Tender URL", key="tender_url_input", placeholder="https://...")
        with col2:
            if st.button("🔄 Re-parse", use_container_width=True):
                st.session_state.last_tender_url = None
                st.session_state.extracted_data = {}
                st.session_state.data_loaded = False
                st.rerun()

        if st.session_state.get('extracted_data'):
            with st.expander("🐛 DEBUG: Raw Extracted Data", expanded=True):
                st.json(st.session_state.extracted_data)
            st.download_button("📥 Export JSON", json.dumps(st.session_state.extracted_data, indent=2, default=str),
                             "extracted_tender_data.json", "application/json")

        if tender_url and st.session_state.get('last_tender_url') != tender_url:
            try:
                with st.spinner("Fetching and parsing..."):
                    parsed = parse_tender_url(tender_url)
                if parsed:
                    st.session_state.extracted_data = parsed
                    st.session_state.last_tender_url = tender_url
                    st.session_state.data_loaded = True
                    # ==================== CONSOLE DEBUG PRINT ====================
                    print("\n" + "="*80, file=sys.stderr)
                    print("🔍 FULL EXTRACTED DATA (RAW) - FOR MAPPING", file=sys.stderr)
                    print("="*80, file=sys.stderr)
                    print(json.dumps(parsed, indent=2, default=str), file=sys.stderr)
                    print("="*80, file=sys.stderr)
                    print(f"Total keys found: {len(parsed)}", file=sys.stderr)
                    print("Available Keys:", list(parsed.keys()), file=sys.stderr)
                    print("="*80, file=sys.stderr)
                    for key, value in parsed.items():
                        # Truncate long values for cleaner output
                        str_value = str(value)
                        if len(str_value) > 200:
                            str_value = str_value[:200] + "..."
                        print(f"  {key}: {str_value}", file=sys.stderr)
                    print("-"*80, file=sys.stderr)
                    
                    _initialize_form_session_state(parsed)
                    st.success("✅ Data parsed successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

    data = st.session_state.get('extracted_data') or {}
    default_values = _get_form_defaults(data, is_editing)

    # Document Upload Section
    # st.subheader("📎 Tender Documents Attachment")
    # uploaded_files = st.file_uploader("Upload files", type=["pdf", "docx", "xlsx", "zip", "jpg", "png"],
    #                                 accept_multiple_files=True, key="doc_uploader")

    # if uploaded_files:
    #     st.session_state.uploaded_documents = uploaded_files
    #     st.success(f"{len(uploaded_files)} file(s) selected")

    # render_document_viewer(st.session_state.get('saved_document_metadata', []))

    # Main Form
    with st.form("tender_form", clear_on_submit=False):
        st.markdown("### Core Tender Details")
        if st.session_state.data_loaded and not is_editing:
            st.caption("Fields auto-filled from e-GP URL.")

        col1, col2 = st.columns(2)
        with col1:
            tender_id = st.text_input("Tender ID *", value=default_values.get('tender_id', ''), key="form_tender_id")
            tender_title = st.text_area("Tender Title *", value=default_values.get('tender_title', ''), height=80, key="form_tender_title")
            procuring_entity = st.text_input("Procuring Entity *", value=default_values.get('procuring_entity', ''), key="form_procuring_entity")
            division = st.selectbox("Division", ["Dhaka","Chittagong","Rajshahi","Khulna","Barisal","Sylhet","Rangpur","Mymensingh"], key="form_division")

        with col2:
            procurement_type = st.selectbox("Procurement Type", ["works", "goods", "services"], key="form_procurement_type")
            official_estimate = st.number_input("Official Estimate (BDT) *", min_value=0.0, value=float(default_values.get('official_estimate', 0)), key="form_official_estimate")
            submission_deadline = st.date_input("Submission Deadline *", value=default_values.get('submission_deadline'), key="form_deadline")
            tender_security = st.number_input("Tender Security", value=float(default_values.get('tender_security', 0)), key="form_security")

        # Expander 1: Dates
        with st.expander("📅 Important Dates & Deadlines", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.date_input("Tender Publication Date", key="form_pub_date")
                st.date_input("Document Selling End Date", key="form_doc_end_date")
                st.date_input("Pre-bid Meeting Start", key="form_pre_bid_start")
                st.date_input("Pre-bid Meeting End", key="form_pre_bid_end")
            with col2:
                st.date_input("Bid Opening Date", key="form_bid_open")
                st.date_input("Security Submission Deadline", key="form_sec_sub")
                st.date_input("Security Valid Upto", key="form_sec_valid")
                st.date_input("Tender Valid Upto", key="form_tender_valid")

        # Expander 2: Contact
        with st.expander("🏢 Procuring Entity Contact Details", expanded=False):
            st.text_area("Official Address", key="form_official_address")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("City", key="form_official_city")
                st.text_input("Thana", key="form_official_thana")
            with col2:
                st.text_input("District", key="form_official_district")
                st.text_input("Email", key="form_official_email")

        # Expander 3: e-GP Details
        with st.expander("📑 e-GP Details & Eligibility", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Invitation Ref No.", key="form_inv_ref")
                st.text_input("PE Code", key="form_pe_code")
                st.text_input("Event Type", key="form_event_type")
                st.text_input("Source of Funds", key="form_source_funds")
            with col2:
                st.text_input("Evaluation Type", key="form_eval_type")
                st.text_input("Mode of Payment", key="form_mode_pay")
            st.text_area("Eligibility Criteria", key="form_eligibility")
            st.text_area("Category", key="form_category")

        # Additional Info
        with st.expander("Additional Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("Project Name", key="form_project_name")
            with col2:
                st.text_area("Notes", key="form_notes")

        submitted = st.form_submit_button("Create Tender" if not is_editing else "Update Tender", type="primary", use_container_width=True)

        if submitted:
            _handle_form_submission(
                tender_id, tender_title, procuring_entity, official_estimate,
                is_editing, default_values, st.session_state.get('uploaded_documents', [])
            )

def get_date_default(data, key):
    """Your original helper function"""
    val = data.get(key) if data else None
    if val and hasattr(val, 'date'):
        return val.date()
    elif val and isinstance(val, str):
        try:
            return datetime.strptime(val, '%Y-%m-%d').date()
        except:
            return None
    return None


def _get_form_defaults(data: Dict, is_editing: bool) -> Dict:
    if not isinstance(data, dict):
        data = {}

    clean_data = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}

    parsed_official_estimate = float(clean_data.get('official_estimate', 0) or 0)
    parsed_tender_security = float(clean_data.get('tender_security', 0) or 0)
    parsed_document_fee = float(clean_data.get('document_fee', 0) or 0)

    # Always calculate OCE
    if parsed_official_estimate <= 0 and parsed_tender_security > 0:
        calculated_oce = parsed_tender_security * OCE_MULTIPLIER
        print(f"ℹ️ Calculated Official Estimate: {calculated_oce}", file=sys.stderr)
    else:
        calculated_oce = parsed_official_estimate

    def to_date(val, key_name=""):
        if not val:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val).date()
            except ValueError:
                print(f"⚠️ Could not parse {key_name}: {val}", file=sys.stderr)
                return None
        return None

    return {
        'tender_id': clean_data.get('tender_id', ''),
        'tender_title': clean_data.get('tender_title', ''),
        'procuring_entity': clean_data.get('procuring_entity', ''),
        'division': clean_data.get('division', 'Dhaka'),
        'district': clean_data.get('district', ''),
        'thana': clean_data.get('thana', ''),
        'country': clean_data.get('country', 'Bangladesh'),
        'procurement_type': PROCUREMENT_TYPE_MAP.get(
            str(clean_data.get('procurement_type', '')).lower(),
            clean_data.get('procurement_type', 'works')
        ),
        'official_estimate': calculated_oce,
        'tender_security': parsed_tender_security,
        'document_fee': parsed_document_fee,
        'invitation_ref_no': clean_data.get('invitation_ref_no', ''),
        'procuring_entity_code': clean_data.get('procuring_entity_code', ''),
        'event_type': clean_data.get('event_type', ''),
        'source_of_funds': clean_data.get('source_of_funds', ''),
        'evaluation_type': clean_data.get('evaluation_type', ''),
        'mode_of_payment': clean_data.get('mode_of_payment', ''),
        'eligibility_criteria': clean_data.get('eligibility_criteria', ''),
        'category': clean_data.get('category', ''),
        'procurement_nature': clean_data.get('procurement_nature', ''),
        'budget_type': clean_data.get('budget_type', ''),
        'inviting_official_name': clean_data.get('inviting_official_name', ''),
        'inviting_official_designation': clean_data.get('inviting_official_designation', ''),
        'inviting_official_phone': clean_data.get('inviting_official_phone', ''),
        'inviting_official_address': clean_data.get('inviting_official_address', ''),
        'inviting_official_city': clean_data.get('inviting_official_city', ''),
        'inviting_official_email': clean_data.get('inviting_official_email', ''),
        'project_code': clean_data.get('project_code', ''),
        'project_name': clean_data.get('project_name', ''),
        'package_no': clean_data.get('package_no', ''),
        'app_id': clean_data.get('app_id', ''),
        'notes': clean_data.get('notes', ''),
        'lots': clean_data.get('lots', []),
        # Dates
        'submission_deadline': to_date(clean_data.get('submission_deadline'), 'submission_deadline'),
        'tender_publication_date': to_date(clean_data.get('tender_publication_date'), 'tender_publication_date'),
        'document_selling_end_date': to_date(clean_data.get('document_selling_end_date'), 'document_selling_end_date'),
        'pre_bid_meeting_start': to_date(clean_data.get('pre_bid_meeting_start'), 'pre_bid_meeting_start'),
        'pre_bid_meeting_end': to_date(clean_data.get('pre_bid_meeting_end'), 'pre_bid_meeting_end'),
        'bid_opening_date': to_date(clean_data.get('bid_opening_date'), 'bid_opening_date'),
        'security_submission_deadline': to_date(clean_data.get('security_submission_deadline'), 'security_submission_deadline'),
        'security_valid_upto': to_date(clean_data.get('security_valid_upto'), 'security_valid_upto'),
        'tender_valid_upto': to_date(clean_data.get('tender_valid_upto'), 'tender_valid_upto'),
    }

def _handle_form_submission(tender_id: str, tender_title: str, procuring_entity: str, 
                          official_estimate: float, is_editing: bool, 
                          default_values: dict, uploaded_documents: List):
    """Complete submission with validation, hybrid dates, and summary banner."""

    errors = []

    # Required numeric/text checks
    if official_estimate <= 0:
        errors.append("Official Estimate (OCE) is required.")
    if float(st.session_state.get("form_security", 0)) <= 0:
        errors.append("Tender Security is required.")
    if not tender_id.strip():
        errors.append("Tender ID is required.")
    if not tender_title.strip():
        errors.append("Tender Title is required.")
    if not procuring_entity.strip():
        errors.append("Procuring Entity is required.")

    # Hybrid date parsing: prefer date picker, fallback to text input
    bid_opening_date_val = st.session_state.get("form_bid_open")
    if not bid_opening_date_val:
        bid_opening_date_val = _parse_date_input(
            st.session_state.get("form_bid_open_text", ""), "Bid Opening Date"
        )

    security_valid_val = st.session_state.get("form_sec_valid")
    if not security_valid_val:
        security_valid_val = _parse_date_input(
            st.session_state.get("form_sec_valid_text", ""), "Security Valid Upto"
        )

    tender_valid_val = st.session_state.get("form_tender_valid")
    if not tender_valid_val:
        tender_valid_val = _parse_date_input(
            st.session_state.get("form_tender_valid_text", ""), "Tender Valid Upto"
        )

    if not bid_opening_date_val:
        errors.append("Bid Opening Date is required.")
    if not security_valid_val:
        errors.append("Security Valid Upto is required.")
    if not tender_valid_val:
        errors.append("Tender Valid Upto is required.")

    # 🚨 Summary validation banner
    if errors:
        st.markdown(
            "<div style='border:2px solid red; padding:10px; background-color:#ffe6e6;'>"
            "⚠️ Please fix the following errors before submission:<br>"
            + "<br>".join(errors) +
            "</div>", unsafe_allow_html=True
        )
        return

    # Save documents
    document_metadata = save_uploaded_documents(tender_id, uploaded_documents) if uploaded_documents else []

    # Full tender data from session state + defaults
    tender_data = {
        'tender_id': tender_id,
        'tender_title': tender_title,
        'procuring_entity': procuring_entity,
        'division': st.session_state.get('form_division', default_values.get('division', '')),
        'district': st.session_state.get('form_district', default_values.get('district', '')),
        'thana': st.session_state.get('form_thana', default_values.get('thana', '')),
        'country': st.session_state.get('form_country', default_values.get('country', 'Bangladesh')),
        'procurement_type': st.session_state.get('form_procurement_type', default_values.get('procurement_type', '')),
        'official_estimate': float(official_estimate),
        'submission_deadline': _format_date('form_deadline'),
        'tender_security': float(st.session_state.get('form_security', default_values.get('tender_security', 0))),
        'document_fee': float(st.session_state.get('form_doc_fee', default_values.get('document_fee', 0))),
        'evaluation_type': st.session_state.get('form_eval_type', default_values.get('evaluation_type', '')),
        'mode_of_payment': st.session_state.get('form_mode_pay', default_values.get('mode_of_payment', '')),
        'eligibility_criteria': st.session_state.get('form_eligibility', default_values.get('eligibility_criteria', '')),
        'invitation_ref_no': st.session_state.get('form_inv_ref', default_values.get('invitation_ref_no', '')),
        'package_no': st.session_state.get('form_package_no', default_values.get('package_no', '')),
        'project_code': st.session_state.get('form_project_code', default_values.get('project_code', '')),
        'project_name': st.session_state.get('form_project_name', default_values.get('project_name', '')),
        'inviting_official_name': st.session_state.get('form_inviting_official_name', ''),
        'inviting_official_designation': st.session_state.get('form_inviting_official_designation', ''),
        'inviting_official_phone': st.session_state.get('form_inviting_official_phone', ''),
        'inviting_official_email': st.session_state.get('form_official_email', default_values.get('inviting_official_email', '')),
        'inviting_official_address': st.session_state.get('form_official_address', default_values.get('inviting_official_address', '')),
        'inviting_official_city': st.session_state.get('form_official_city', default_values.get('inviting_official_city', '')),
        'inviting_official_thana': st.session_state.get('form_official_thana', default_values.get('thana', '')),
        'inviting_official_district': st.session_state.get('form_official_district', default_values.get('district', '')),
        'notes': st.session_state.get('form_notes', default_values.get('notes', '')),
        'app_id': st.session_state.get('form_app_id', default_values.get('app_id', '')),
        'procuring_entity_code': st.session_state.get('form_pe_code', default_values.get('procuring_entity_code', '')),
        'procurement_nature': st.session_state.get('form_procurement_nature', default_values.get('procurement_nature', '')),
        'event_type': st.session_state.get('form_event_type', default_values.get('event_type', '')),
        'budget_type': st.session_state.get('form_budget_type', default_values.get('budget_type', '')),
        'source_of_funds': st.session_state.get('form_source_funds', default_values.get('source_of_funds', '')),
        'category': st.session_state.get('form_category', default_values.get('category', '')),
        'tender_publication_date': _format_date('form_pub_date'),
        'document_selling_end_date': _format_date('form_doc_end_date'),
        'pre_bid_meeting_start': _format_date('form_pre_bid_start'),
        'pre_bid_meeting_end': _format_date('form_pre_bid_end'),
        'bid_opening_date': bid_opening_date_val,
        'security_submission_deadline': _format_date('form_sec_sub'),
        'security_valid_upto': security_valid_val,
        'tender_valid_upto': tender_valid_val,
    }


    db = UnifiedDatabaseManager()
    try:
        if is_editing:
            success = db.update_tender(st.session_state.edit_tender_id, tender_data, st.session_state.user_id)
            if success:
                st.success("✅ Tender updated successfully!")
                st.balloons()
        else:
            db.create_tender(st.session_state.company_id, tender_data, st.session_state.user_id)
            st.success("✅ Tender created successfully!")
            st.balloons()

        _clear_tender_form_state()
        st.session_state.page = "tender_management"
        st.session_state.active_tab = "Dashboard"
        st.rerun()
    except Exception as e:
        st.error(f"Database error: {str(e)}")



def _format_date(key: str):
    d = st.session_state.get(key)
    return d.strftime('%Y-%m-%d') if d else None
def _initialize_form_session_state(parsed_data):
    defaults = _get_form_defaults(parsed_data, False)

    field_mappings = {
        'tender_id': 'form_tender_id',
        'tender_title': 'form_tender_title',
        'procuring_entity': 'form_procuring_entity',
        'division': 'form_division',
        'procurement_type': 'form_procurement_type',
        'official_estimate': 'form_official_estimate',
        'submission_deadline': 'form_deadline',
        'tender_security': 'form_security',
        'document_fee': 'form_doc_fee',
        'project_code': 'form_project_code',
        'project_name': 'form_project_name',
        'package_no': 'form_package_no',
        'budget_type': 'form_budget_type',
        'notes': 'form_notes',
        'app_id': 'form_app_id',
        'procurement_nature': 'form_procurement_nature',
        'inviting_official_name': 'form_inviting_official_name',
        'inviting_official_designation': 'form_inviting_official_designation',
        'inviting_official_phone': 'form_inviting_official_phone',
        'inviting_official_address': 'form_official_address',
        'inviting_official_city': 'form_official_city',
        'inviting_official_email': 'form_official_email',
        'district': 'form_official_district',
        'thana': 'form_official_thana',
        'evaluation_type': 'form_eval_type',
        'mode_of_payment': 'form_mode_pay',
        'eligibility_criteria': 'form_eligibility',
        'invitation_ref_no': 'form_inv_ref',
        'procuring_entity_code': 'form_pe_code',
        'event_type': 'form_event_type',
        'source_of_funds': 'form_source_funds',
        'category': 'form_category',
        'tender_publication_date': 'form_pub_date',
        'document_selling_end_date': 'form_doc_end_date',
        'pre_bid_meeting_start': 'form_pre_bid_start',
        'pre_bid_meeting_end': 'form_pre_bid_end',
        'security_submission_deadline': 'form_sec_sub',
    }

    hybrid_fields = {
        'bid_opening_date': ('form_bid_open', 'form_bid_open_text'),
        'security_valid_upto': ('form_sec_valid', 'form_sec_valid_text'),
        'tender_valid_upto': ('form_tender_valid', 'form_tender_valid_text'),
    }

    for data_key, form_key in field_mappings.items():
        if data_key in defaults and defaults[data_key] is not None:
            st.session_state[form_key] = defaults[data_key]

    for data_key, (date_key, text_key) in hybrid_fields.items():
        val = defaults.get(data_key)
        if val is not None:
            st.session_state[date_key] = val
            st.session_state[text_key] = val.strftime("%Y-%m-%d")
        else:
            st.session_state[date_key] = None
            st.session_state[text_key] = ""

# def _initialize_form_session_state_bak(parsed_data):
#     defaults = _get_form_defaults(parsed_data, False)
#     for k, v in defaults.items():
#         key = f"form_{k}" if not k.startswith("form_") else k
#         if key in FORM_WIDGET_KEYS:
#             st.session_state[key] = v


def _clear_tender_form_state():
    for key in ['edit_mode', 'edit_tender_id', 'extracted_data', 'data_loaded', 'last_tender_url',
                'uploaded_documents', 'saved_document_metadata'] + FORM_WIDGET_KEYS:
        if key in st.session_state:
            del st.session_state[key]

def _parse_date_input(val: str, field_name: str):
    """Validate and convert text input into a date object with inline feedback."""
    if not val or not val.strip():
        st.error(f"{field_name} is required.")
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except ValueError:
        st.error(f"{field_name} must be in YYYY-MM-DD format.")
        return None
