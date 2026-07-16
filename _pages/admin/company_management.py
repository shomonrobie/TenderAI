"""
Company Management Module - State-Driven View Router Pattern
Uses st.dataframe with singleton selection and comprehensive validation
All database operations use CompanyCRUD methods - NO RAW SQL
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from utils.validators import (
    validate_email,
    validate_bangladesh_mobile,
    normalize_mobile
)
from utils.helpers import safe_compare, safe_strip


def render_company_management(db):
    """Main entry point for company management with view routing"""
    
    if "company_view" not in st.session_state:
        st.session_state.company_view = "grid"
    if "company_selected_id" not in st.session_state:
        st.session_state.company_selected_id = None
    if "company_page" not in st.session_state:
        st.session_state.company_page = 1
    if "company_search" not in st.session_state:
        st.session_state.company_search = ""
    if "company_status_filter" not in st.session_state:
        st.session_state.company_status_filter = "All"
    if "company_sort_by" not in st.session_state:
        st.session_state.company_sort_by = "company_name"
    if "company_per_page" not in st.session_state:
        st.session_state.company_per_page = 10
    
    if st.session_state.company_view == "detail":
        render_company_detail_view(db)
    else:
        render_company_grid_view(db)


def render_company_grid_view(db):
    """Render spreadsheet-style grid view using st.dataframe"""
    
    st.markdown("### 🏢 COMPANY MANAGEMENT SYSTEM")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1])
    
    with col1:
        if st.button("➕ Add New Company", key="company_add_btn", type="primary", use_container_width=True):
            st.session_state.company_selected_id = None
            st.session_state.company_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.company_search = st.text_input(
            "🔍 Search",
            placeholder="Name, email, or registration...",
            value=st.session_state.company_search,
            key="company_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        status_options = ["All", "Active", "Inactive"]
        st.session_state.company_status_filter = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(st.session_state.company_status_filter),
            key="company_status_filter_select",
            label_visibility="collapsed"
        )
    
    with col4:
        st.session_state.company_per_page = st.selectbox(
            "Rows",
            options=[5, 10, 25, 50],
            index=[5, 10, 25, 50].index(st.session_state.company_per_page) if st.session_state.company_per_page in [5, 10, 25, 50] else 1,
            key="company_per_page_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH COMPANIES =====
    try:
        status = None if st.session_state.company_status_filter == "All" else (1 if st.session_state.company_status_filter == "Active" else 0)
        
        per_page = st.session_state.company_per_page
        offset = (st.session_state.company_page - 1) * per_page
        
        companies, total = db.get_all_companies_filtered(
            search=st.session_state.company_search if st.session_state.company_search else None,
            status=status,
            limit=per_page,
            offset=offset
        )
                
    except Exception as e:
        st.error(f"Error loading companies: {e}")
        return
    
    if not companies:
        st.info("No companies found. Click 'Add New Company' to create one.")
        return
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, company in enumerate(companies):
        # Get user count
        try:
            stats = db.get_company_stats_by_id(company.get('id'))
            user_count = stats.get('total_users', 0)
        except:
            user_count = 0
        
        # Get subscription
        try:
            subscription = db.get_company_subscription(company.get('id'))
            plan_name = subscription.get('plan', 'Free').title() if subscription else 'Free'
        except:
            plan_name = 'Free'
        
        # Format status
        is_active = company.get('is_active', 0)
        status_display = "🟢 Active" if is_active == 1 else "🔴 Inactive"
        
        df_data.append({
            'id': company.get('id'),
            'company_name': company.get('company_name', 'Unknown'),
            'email': company.get('email', ''),
            'phone': company.get('phone', ''),
            'mobile_number': company.get('mobile_number', ''),
            'plan': plan_name,
            'users': user_count,
            'status': status_display,
            'is_active': is_active,
            'created_at': company.get('created_at', ''),
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== SORT =====
    sort_column = st.session_state.company_sort_by
    if sort_column in df.columns:
        df = df.sort_values(by=sort_column, ascending=True)
        df = df.reset_index(drop=True)
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Companies", total)
    with col2:
        active = len([c for c in companies if c.get('is_active', 0) == 1])
        st.metric("Active", active)
    with col3:
        inactive = total - active
        st.metric("Inactive", inactive)
    with col4:
        total_users = 0
        for c in companies:
            try:
                stats = db.get_company_stats_by_id(c.get('id'))
                total_users += stats.get('total_users', 0)
            except:
                pass
        st.metric("Total Users", total_users)
    
    st.markdown("---")
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['id', 'company_name', 'email', 'phone', 'plan', 'users', 'status']
    
    # Style the dataframe
    styled_df = df[display_columns].style
    
    def color_status(val):
        if 'Active' in str(val):
            return 'color: #065f46; background-color: #d1fae5;'
        elif 'Inactive' in str(val):
            return 'color: #991b1b; background-color: #fee2e2;'
        return ''
    
    styled_df = styled_df.map(color_status, subset=['status'])
    
    event = st.dataframe(
        styled_df,
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.Column("ID", width="small"),
            "company_name": st.column_config.Column("Company Name", width="large"),
            "email": st.column_config.Column("Email", width="medium"),
            "phone": st.column_config.Column("Phone", width="small"),
            "plan": st.column_config.Column("Plan", width="small"),
            "users": st.column_config.Column("Users", width="small"),
            "status": st.column_config.Column("Status", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            company_id = row_data.get('id')
            if company_id:
                st.session_state.company_selected_id = company_id
                st.session_state.company_view = "detail"
                st.rerun()
    
    # ===== PAGINATION =====
    total_pages = (total + per_page - 1) // per_page
    start_idx = (st.session_state.company_page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    
    with col1:
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} companies")
    
    with col2:
        if st.button("◀ Prev", key="company_prev", disabled=(st.session_state.company_page <= 1), use_container_width=True):
            st.session_state.company_page -= 1
            st.rerun()
    
    with col3:
        if st.button("Next ▶", key="company_next", disabled=(st.session_state.company_page >= total_pages), use_container_width=True):
            st.session_state.company_page += 1
            st.rerun()
    
    with col4:
        jump_to = st.number_input(
            "Jump to page",
            min_value=1,
            max_value=total_pages if total_pages > 0 else 1,
            value=st.session_state.company_page,
            step=1,
            key="company_jump_to",
            label_visibility="collapsed"
        )
        if jump_to != st.session_state.company_page and 1 <= jump_to <= total_pages:
            st.session_state.company_page = jump_to
            st.rerun()


def render_company_detail_view(db):
    """Render full-page detail view for company CRUD with validation"""
    
    company_id = st.session_state.company_selected_id
    is_new = company_id is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Add New Company" if is_new else f"✏️ Edit Company Details (ID: {company_id})"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to Company Grid", key="company_back_to_grid"):
        st.session_state.company_view = "grid"
        st.session_state.company_selected_id = None
        st.rerun()
    
    st.divider()
    
    # ===== GET COMPANY DATA =====
    if is_new:
        company = {
            'id': None,
            'company_name': '',
            'email': '',
            'phone': '',
            'mobile_number': '',
            'website': '',
            'division': '',
            'district': '',
            'address': '',
            'registration_number': '',
            'vat_number': '',
            'is_active': 1
        }
    else:
        company = db.get_company_by_id(company_id)
        if not company:
            st.error(f"Company with ID {company_id} not found")
            if st.button("Close", key="company_close_not_found"):
                st.session_state.company_view = "grid"
                st.session_state.company_selected_id = None
                st.rerun()
            return
    
    # ===== EDIT FORM WITH VALIDATION =====
    with st.form(key="company_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📋 Company Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input(
                "Company Name *",
                value=company.get('company_name', ''),
                key="company_edit_name",
                help="Company legal name (minimum 2 characters)"
            )
            
            email = st.text_input(
                "Email",
                value=company.get('email', ''),
                key="company_edit_email",
                help="Valid email format required"
            )
            
            phone = st.text_input(
                "Phone",
                value=company.get('phone', ''),
                key="company_edit_phone",
                help="Company phone number"
            )
            
            mobile_number = st.text_input(
                "Mobile Number *",
                value=company.get('mobile_number', ''),
                key="company_edit_mobile",
                help="Bangladeshi mobile: 01XXXXXXXXX (11 digits)"
            )
        
        with col2:
            website = st.text_input(
                "Website",
                value=company.get('website', ''),
                key="company_edit_website",
                help="Company website URL"
            )
            
            division = st.text_input(
                "Division",
                value=company.get('division', ''),
                key="company_edit_division"
            )
            
            district = st.text_input(
                "District",
                value=company.get('district', ''),
                key="company_edit_district"
            )
            
            registration_number = st.text_input(
                "Registration Number",
                value=company.get('registration_number', ''),
                key="company_edit_reg",
                help="Company registration number"
            )
            
            vat_number = st.text_input(
                "VAT Number",
                value=company.get('vat_number', ''),
                key="company_edit_vat",
                help="VAT registration number"
            )
        
        address = st.text_area(
            "Address",
            value=company.get('address', ''),
            height=80,
            key="company_edit_address",
            help="Company physical address"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== STATUS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">🔐 Status</div>', unsafe_allow_html=True)
        
        is_active = st.checkbox(
            "Active",
            value=company.get('is_active', 0) == 1,
            key="company_edit_active"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== FORM ACTIONS =====
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Save Changes",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if not is_new:
                delete_clicked = st.form_submit_button(
                    "🗑️ Delete Company",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    # Check if company has users
                    users, _ = db.get_all_users_filtered(company_id=company_id, limit=1)
                    if users:
                        st.error("❌ Cannot delete company with existing users. Reassign users first.")
                    else:
                        st.warning("⚠️ Are you sure you want to delete this company?")
                        col_confirm, col_cancel = st.columns(2)
                        with col_confirm:
                            if st.button("✅ Confirm Delete", key=f"company_confirm_delete_{company_id}"):
                                # Delete company - you'll need to implement this
                                st.info("Delete functionality would be implemented here")
                        with col_cancel:
                            if st.button("❌ Cancel", key="company_cancel_delete"):
                                st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.company_view = "grid"
                st.session_state.company_selected_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION WITH VALIDATION =====
    if submitted:
        updates = {}
        validation_errors = []
        
        # ===== VALIDATE COMPANY NAME =====
        if company_name:
            company_name_clean = safe_strip(company_name)
            if len(company_name_clean) < 2:
                validation_errors.append("Company name must be at least 2 characters")
            else:
                updates['company_name'] = company_name_clean
        else:
            validation_errors.append("Company name is required")
        
        # ===== VALIDATE MOBILE NUMBER =====
        if mobile_number:
            mobile_clean = safe_strip(mobile_number)
            normalized_mobile = normalize_mobile(mobile_clean)
            if not validate_bangladesh_mobile(normalized_mobile):
                validation_errors.append("Invalid mobile number. Must be a valid Bangladeshi number (01XXXXXXXXX)")
            else:
                updates['mobile_number'] = normalized_mobile
        else:
            validation_errors.append("Mobile number is required")
        
        # ===== VALIDATE EMAIL =====
        if email and email.strip():
            email_clean = safe_strip(email)
            is_valid, error_msg = validate_email(email_clean)
            if not is_valid:
                validation_errors.append(f"Email: {error_msg}")
            else:
                updates['email'] = email_clean
        else:
            # Email is optional, set to None if empty
            updates['email'] = None
        
        # ===== PROCESS OPTIONAL FIELDS =====
        if phone and phone.strip():
            updates['phone'] = safe_strip(phone)
        else:
            updates['phone'] = None
        
        if website and website.strip():
            updates['website'] = safe_strip(website)
        else:
            updates['website'] = None
        
        if division and division.strip():
            updates['division'] = safe_strip(division)
        else:
            updates['division'] = None
        
        if district and district.strip():
            updates['district'] = safe_strip(district)
        else:
            updates['district'] = None
        
        if address and address.strip():
            updates['address'] = safe_strip(address)
        else:
            updates['address'] = None
        
        if registration_number and registration_number.strip():
            updates['registration_number'] = safe_strip(registration_number)
        else:
            updates['registration_number'] = None
        
        if vat_number and vat_number.strip():
            updates['vat_number'] = safe_strip(vat_number)
        else:
            updates['vat_number'] = None
        
        updates['is_active'] = 1 if is_active else 0
        
            # ===== SHOW VALIDATION ERRORS =====
    if validation_errors:
        for err in validation_errors:
            st.error(f"❌ {err}")
    else:
        # ============================================================
        # DUPLICATE CHECKING USING COMPANY CRUD METHODS
        # ============================================================
        duplicate_errors = []
        
        # Determine exclude_id for update vs new
        exclude_id = None if is_new else company_id
        
        # Check company name duplicate
        if db.check_company_name_exists(updates['company_name'], exclude_id):
            duplicate_errors.append(f"Company name '{updates['company_name']}' already exists")
        
        # Check mobile duplicate
        if db.check_company_mobile_exists(updates['mobile_number'], exclude_id):
            duplicate_errors.append(f"Mobile number '{updates['mobile_number']}' already exists")
        
        # Check email duplicate (if email is provided)
        if updates.get('email') and db.check_company_email_exists(updates['email'], exclude_id):
            duplicate_errors.append(f"Email '{updates['email']}' already exists")
        
        if duplicate_errors:
            for err in duplicate_errors:
                st.error(f"❌ {err}")
        else:
            # ============================================================
            # SAVE TO DATABASE
            # ============================================================
            if is_new:
                # Create new company
                success, result = db.create_company(updates)
                if success:
                    st.success(f"✅ Company '{updates['company_name']}' created successfully!")
                    st.balloons()
                    st.session_state.company_view = "grid"
                    st.session_state.company_selected_id = None
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create company: {result}")
            else:
                # Update existing company
                if db.update_company(company_id, updates):
                    st.success("✅ Company updated successfully!")
                    st.balloons()
                    st.session_state.company_view = "grid"
                    st.session_state.company_selected_id = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update company")
    
    st.markdown('</div>', unsafe_allow_html=True)