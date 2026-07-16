"""
Company User Management Module
Reusable user management for company admins
Uses the same grid/detail pattern as admin dashboard
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from utils.validators import (
    validate_username,
    validate_email,
    validate_bangladesh_mobile,
    normalize_mobile
)
from utils.helpers import safe_compare, safe_strip


def render_company_user_management(db, company_id: int):
    """
    Render user management for company admins
    Uses the same grid/detail pattern as admin dashboard
    """
    
    # Initialize session state for company user management
    if "comp_user_view" not in st.session_state:
        st.session_state.comp_user_view = "grid"
    if "comp_user_selected_id" not in st.session_state:
        st.session_state.comp_user_selected_id = None
    if "comp_user_search" not in st.session_state:
        st.session_state.comp_user_search = ""
    if "comp_user_sort_by" not in st.session_state:
        st.session_state.comp_user_sort_by = "full_name"
    if "comp_user_sort_order" not in st.session_state:
        st.session_state.comp_user_sort_order = "asc"
    
    # Route to appropriate view
    if st.session_state.comp_user_view == "detail":
        render_company_user_detail_view(db, company_id)
    else:
        render_company_user_grid_view(db, company_id)


def render_company_user_grid_view(db, company_id: int):
    """Render spreadsheet-style grid view for company users"""
    
    st.markdown("### 👥 Company Users")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("➕ Invite User", key="comp_user_add_btn", type="primary", use_container_width=True):
            st.session_state.comp_user_selected_id = None
            st.session_state.comp_user_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.comp_user_search = st.text_input(
            "🔍 Search",
            placeholder="Name, email, or username...",
            value=st.session_state.comp_user_search,
            key="comp_user_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        sort_by_map = {
            "Full Name": "full_name",
            "Username": "username",
            "Email": "email",
            "Role": "role",
            "Status": "is_active"
        }
        
        st.session_state.comp_user_sort_by = st.selectbox(
            "Sort by",
            options=list(sort_by_map.keys()),
            index=list(sort_by_map.values()).index(st.session_state.comp_user_sort_by) if st.session_state.comp_user_sort_by in sort_by_map.values() else 0,
            key="comp_user_sort_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH USERS =====
    try:
        # Get users for this company
        users = db.get_all_users(company_id=company_id)
        
        # Apply search filter
        if st.session_state.comp_user_search:
            search_lower = st.session_state.comp_user_search.lower()
            users = [
                u for u in users
                if search_lower in str(u.get('username', '')).lower()
                or search_lower in str(u.get('email', '')).lower()
                or search_lower in str(u.get('full_name', '')).lower()
            ]
            
        total = len(users)
        
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return
    
    if not users:
        st.info("No users found. Click 'Invite User' to add team members.")
        return
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, user in enumerate(users):
        role_display = user.get('role', 'viewer').replace('_', ' ').title()
        is_active = user.get('is_active', 0)
        status_display = "✅ Active" if is_active == 1 else "❌ Inactive"
        is_approved = user.get('is_approved', 0)
        approved_display = "✅" if is_approved == 1 else "⏳ Pending"
        
        df_data.append({
            'id': user.get('id'),
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'email': user.get('email', 'N/A'),
            'role': role_display,
            'status': status_display,
            'is_active': is_active,
            'is_approved': is_approved,
            'approved': approved_display,
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== SORT =====
    sort_column = st.session_state.comp_user_sort_by
    if sort_column in df.columns:
        sort_ascending = st.session_state.comp_user_sort_order == "asc"
        df = df.sort_values(by=sort_column, ascending=sort_ascending)
        df = df.reset_index(drop=True)
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total)
    with col2:
        active = len([u for u in users if u.get('is_active', 0) == 1])
        st.metric("Active", active)
    with col3:
        approved = len([u for u in users if u.get('is_approved', 0) == 1])
        st.metric("Approved", approved)
    with col4:
        pending = len([u for u in users if u.get('is_approved', 0) == 0])
        st.metric("Pending", pending)
    
    st.markdown("---")
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['id', 'username', 'full_name', 'email', 'role', 'status', 'approved']
    
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
            "username": st.column_config.Column("Username", width="medium"),
            "full_name": st.column_config.Column("Full Name", width="medium"),
            "email": st.column_config.Column("Email", width="large"),
            "role": st.column_config.Column("Role", width="small"),
            "status": st.column_config.Column("Status", width="small"),
            "approved": st.column_config.Column("Approved", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            user_id = row_data.get('id')
            if user_id:
                st.session_state.comp_user_selected_id = user_id
                st.session_state.comp_user_view = "detail"
                st.rerun()
    
    st.caption(f"Showing {len(users)} users")


def render_company_user_detail_view(db, company_id: int):
    """Render full-page detail view for company user management"""
    
    user_id = st.session_state.comp_user_selected_id
    is_new = user_id is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Invite New User" if is_new else f"✏️ Edit User Details (ID: {user_id})"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to User List", key="comp_user_back_to_grid"):
        st.session_state.comp_user_view = "grid"
        st.session_state.comp_user_selected_id = None
        st.rerun()
    
    st.divider()
    
    # ===== GET USER DATA =====
    if is_new:
        user = {
            'id': None,
            'username': '',
            'full_name': '',
            'email': '',
            'mobile_number': '',
            'phone': '',
            'role': 'viewer',
            'is_active': 1,
            'is_approved': 0,
            'specialization': '',
            'years_experience': 0,
            'location': '',
            'website': '',
            'bio': '',
            'company_id': company_id,
            'company_name': ''
        }
    else:
        user = db.get_user_by_id(user_id)
        if not user:
            st.error(f"User with ID {user_id} not found")
            if st.button("Close", key="comp_user_close_not_found"):
                st.session_state.comp_user_view = "grid"
                st.session_state.comp_user_selected_id = None
                st.rerun()
            return
    
    # ===== EDIT FORM =====
    with st.form(key="comp_user_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">👤 Account Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "Full Name *",
                value=user.get('full_name', ''),
                key="comp_user_edit_full_name"
            )
            
            username = st.text_input(
                "Username *",
                value=user.get('username', ''),
                key="comp_user_edit_username",
                help="3-30 characters, letters, numbers, and underscores only"
            )
            
            email = st.text_input(
                "Email Address *",
                value=user.get('email', ''),
                key="comp_user_edit_email",
                help="Valid email format required"
            )
        
        with col2:
            mobile = st.text_input(
                "Mobile Number *",
                value=user.get('mobile_number', ''),
                key="comp_user_edit_mobile",
                help="Bangladeshi mobile: 01XXXXXXXXX (11 digits)"
            )
            
            phone = st.text_input(
                "Phone",
                value=user.get('phone', ''),
                key="comp_user_edit_phone"
            )
            
            # Company is fixed for company users
            st.text_input(
                "Company",
                value=user.get('company_name', 'Your Company'),
                disabled=True,
                key="comp_user_edit_company"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PERMISSIONS & ACCESS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">⚙️ Permissions & Access</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Company roles (excluding system_admin and individual)
            role_options = ["company_admin", "manager", "analyst", "estimator", "viewer"]
            current_role = user.get('role', 'viewer')
            
            if current_role not in role_options:
                role_options.append(current_role)
            
            try:
                role_index = role_options.index(current_role)
            except ValueError:
                role_index = 0
            
            role = st.radio(
                "System Role",
                options=role_options,
                index=role_index,
                key="comp_user_edit_role",
                help="Company users can have various roles based on their responsibilities."
            )
        
        with col2:
            is_active = st.radio(
                "Account Status",
                options=["Active", "Inactive"],
                index=0 if user.get('is_active', 0) == 1 else 1,
                key="comp_user_edit_status"
            )
            is_active_bool = is_active == "Active"
            
            if not is_new:
                is_approved = st.radio(
                    "Approval Status",
                    options=["Approved", "Pending"],
                    index=0 if user.get('is_approved', 0) == 1 else 1,
                    key="comp_user_edit_approved"
                )
                is_approved_bool = is_approved == "Approved"
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PROFESSIONAL INFORMATION =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">💼 Professional Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            specialization = st.text_input(
                "Specialization",
                value=user.get('specialization', ''),
                key="comp_user_edit_specialization"
            )
            years_experience = st.number_input(
                "Years of Experience",
                min_value=0,
                max_value=50,
                value=user.get('years_experience', 0) or 0,
                key="comp_user_edit_years_exp"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value=user.get('location', ''),
                key="comp_user_edit_location"
            )
            website = st.text_input(
                "Website",
                value=user.get('website', ''),
                key="comp_user_edit_website"
            )
        
        bio = st.text_area(
            "Bio",
            value=user.get('bio', ''),
            max_chars=500,
            key="comp_user_edit_bio"
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
                    "🗑️ Remove User",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    st.warning("⚠️ Are you sure you want to remove this user?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Remove", key=f"comp_user_confirm_delete_{user_id}"):
                            if db.delete_user(user_id):
                                st.success("User removed successfully!")
                                st.session_state.comp_user_view = "grid"
                                st.session_state.comp_user_selected_id = None
                                st.rerun()
                            else:
                                st.error("Failed to remove user")
                    with col_cancel:
                        if st.button("❌ Cancel", key="comp_user_cancel_delete"):
                            st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.comp_user_view = "grid"
                st.session_state.comp_user_selected_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION =====
    if submitted:
        updates = {}
        validation_errors = []
        
        # Validate and process each field
        if full_name:
            full_name_clean = safe_strip(full_name)
            if len(full_name_clean) < 2:
                validation_errors.append("Full name must be at least 2 characters")
            else:
                updates['full_name'] = full_name_clean
        else:
            validation_errors.append("Full name is required")
        
        if username:
            username_clean = safe_strip(username)
            is_valid, error_msg = validate_username(username_clean)
            if not is_valid:
                validation_errors.append(f"Username: {error_msg}")
            else:
                updates['username'] = username_clean
        else:
            validation_errors.append("Username is required")
        
        if email:
            email_clean = safe_strip(email)
            is_valid, error_msg = validate_email(email_clean)
            if not is_valid:
                validation_errors.append(f"Email: {error_msg}")
            else:
                updates['email'] = email_clean
        else:
            validation_errors.append("Email is required")
        
        if mobile:
            mobile_clean = safe_strip(mobile)
            normalized_mobile = normalize_mobile(mobile_clean)
            if not validate_bangladesh_mobile(normalized_mobile):
                validation_errors.append("Invalid mobile number. Must be a valid Bangladeshi number (01XXXXXXXXX)")
            else:
                updates['mobile_number'] = normalized_mobile
        else:
            validation_errors.append("Mobile number is required")
        
        if phone:
            updates['phone'] = safe_strip(phone)
        
        updates['role'] = role
        updates['is_active'] = 1 if is_active_bool else 0
        updates['company_id'] = company_id
        
        if not is_new:
            updates['is_approved'] = 1 if is_approved_bool else 0
        
        if specialization:
            updates['specialization'] = safe_strip(specialization)
        updates['years_experience'] = years_experience if years_experience > 0 else None
        
        if location:
            updates['location'] = safe_strip(location)
        if website:
            updates['website'] = safe_strip(website)
        if bio:
            updates['bio'] = safe_strip(bio)
        
        # Show validation errors
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # ============================================================
            # DUPLICATE CHECKING
            # ============================================================
            duplicate_errors = []
            exclude_id = None if is_new else user_id
            
            # Check username duplicate
            if db.check_username_exists(updates['username'], exclude_id):
                duplicate_errors.append(f"Username '{updates['username']}' is already taken")
            
            # Check email duplicate
            if db.check_email_exists(updates['email'], exclude_id):
                duplicate_errors.append(f"Email '{updates['email']}' is already registered")
            
            # Check mobile duplicate
            if db.check_mobile_exists(updates['mobile_number'], exclude_id):
                duplicate_errors.append(f"Mobile number '{updates['mobile_number']}' is already registered")
            
            if duplicate_errors:
                for err in duplicate_errors:
                    st.error(f"❌ {err}")
            else:
                # Save to database
                if is_new:
                    # Create new user in this company
                    user_data = {
                        'username': updates['username'],
                        'email': updates['email'],
                        'full_name': updates['full_name'],
                        'phone': updates.get('phone', ''),
                        'mobile_number': updates['mobile_number'],
                        'role': updates['role'],
                        'password': 'Temporary@123'  # Will need to be reset
                    }
                    success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        st.success(f"✅ User {updates['full_name']} invited successfully!")
                        st.info(f"📧 An invitation email will be sent to {updates['email']}")
                        st.session_state.comp_user_view = "grid"
                        st.session_state.comp_user_selected_id = None
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create user: {result}")
                else:
                    if db.update_user(user_id, updates):
                        st.success("✅ User updated successfully!")
                        st.balloons()
                        st.session_state.comp_user_view = "grid"
                        st.session_state.comp_user_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to update user")
    
    st.markdown('</div>', unsafe_allow_html=True)