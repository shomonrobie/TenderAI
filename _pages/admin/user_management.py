"""
User Management Module - State-Driven View Router Pattern
Uses st.dataframe with singleton selection and comprehensive validation
All database operations use UserCRUD methods - NO RAW SQL
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


def render_user_management(db):
    """Main entry point for user management with view routing"""
    
    # Initialize session state for this module
    if "user_view" not in st.session_state:
        st.session_state.user_view = "grid"
    if "user_selected_id" not in st.session_state:
        st.session_state.user_selected_id = None
    if "user_page" not in st.session_state:
        st.session_state.user_page = 1
    if "user_search" not in st.session_state:
        st.session_state.user_search = ""
    if "user_sort_by" not in st.session_state:
        st.session_state.user_sort_by = "full_name"
    if "user_sort_order" not in st.session_state:
        st.session_state.user_sort_order = "asc"
    if "user_per_page" not in st.session_state:
        st.session_state.user_per_page = 10
    
    # Route to appropriate view
    if st.session_state.user_view == "detail":
        render_user_detail_view(db)
    else:
        render_user_grid_view(db)


def render_user_grid_view(db):
    """Render spreadsheet-style grid view using st.dataframe"""
    
    st.markdown("### 👥 USER MANAGEMENT SYSTEM")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1])
    
    with col1:
        if st.button("➕ Add New User", key="user_add_btn", type="primary", use_container_width=True):
            st.session_state.user_selected_id = None
            st.session_state.user_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.user_search = st.text_input(
            "🔍 Search",
            placeholder="Name, email, or username...",
            value=st.session_state.user_search,
            key="user_search_input",
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
        
        col_sort, col_order = st.columns(2)
        with col_sort:
            sort_label = st.selectbox(
                "Sort",
                options=list(sort_by_map.keys()),
                index=list(sort_by_map.values()).index(st.session_state.user_sort_by) if st.session_state.user_sort_by in sort_by_map.values() else 0,
                key="user_sort_select",
                label_visibility="collapsed"
            )
            st.session_state.user_sort_by = sort_by_map[sort_label]
        
        with col_order:
            order_options = ["asc", "desc"]
            order_labels = ["⬆ Asc", "⬇ Desc"]
            order_idx = order_options.index(st.session_state.user_sort_order) if st.session_state.user_sort_order in order_options else 0
            st.session_state.user_sort_order = st.selectbox(
                "Order",
                options=order_options,
                format_func=lambda x: order_labels[order_options.index(x)],
                index=order_idx,
                key="user_order_select",
                label_visibility="collapsed"
            )
    
    with col4:
        st.session_state.user_per_page = st.selectbox(
            "Rows",
            options=[5, 10, 25, 50, 100],
            index=[5, 10, 25, 50, 100].index(st.session_state.user_per_page) if st.session_state.user_per_page in [5, 10, 25, 50, 100] else 1,
            key="user_per_page_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH USERS =====
    try:
        # ✅ Use get_all_users() which already includes company_name
        all_users = db.get_all_users()
        
        # Apply search filter
        if st.session_state.user_search:
            search_lower = st.session_state.user_search.lower()
            users = [
                u for u in all_users
                if search_lower in str(u.get('username', '')).lower()
                or search_lower in str(u.get('email', '')).lower()
                or search_lower in str(u.get('full_name', '')).lower()
            ]
        else:
            users = all_users
            
        total = len(users)
        
        # ✅ Get system users separately if needed
        # Note: get_all_users() already includes system users (company_id IS NULL)
        # so we don't need to separately fetch system_users
        
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return
    
    if not users:
        st.info("No users found. Click 'Add New User' to create one.")
        return
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, user in enumerate(users):
        role_display = user.get('role', 'viewer').replace('_', ' ').title()
        is_active = user.get('is_active', 0)
        status_display = "✅ Active" if is_active == 1 else "❌ Inactive"
        
        df_data.append({
            'id': user.get('id'),
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'email': user.get('email', 'N/A'),
            'role': role_display,
            'status': status_display,
            'is_active': is_active,
            'company': user.get('company_name', ''),  # ✅ Now this will work!
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== SORT =====
    sort_column = st.session_state.user_sort_by
    sort_ascending = st.session_state.user_sort_order == "asc"
    
    if sort_column in df.columns:
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
        inactive = total - active
        st.metric("Inactive", inactive)
    with col4:
        system_users = len([u for u in users if u.get('company_id') is None])
        st.metric("System Users", system_users)
    
    st.markdown("---")
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['id', 'username', 'full_name', 'email', 'role', 'status', 'company']
    
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
            "company": st.column_config.Column("Company", width="medium"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            user_id = row_data.get('id')
            if user_id:
                st.session_state.user_selected_id = user_id
                st.session_state.user_view = "detail"
                st.rerun()
    
    # ===== PAGINATION =====
    per_page = st.session_state.user_per_page
    total_pages = (total + per_page - 1) // per_page
    
    # Ensure page is within bounds
    if st.session_state.user_page > total_pages and total_pages > 0:
        st.session_state.user_page = total_pages
    
    start_idx = (st.session_state.user_page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    
    with col1:
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} users")
    
    with col2:
        if st.button("◀ Prev", key="user_prev", disabled=(st.session_state.user_page <= 1), use_container_width=True):
            st.session_state.user_page -= 1
            st.rerun()
    
    with col3:
        if st.button("Next ▶", key="user_next", disabled=(st.session_state.user_page >= total_pages), use_container_width=True):
            st.session_state.user_page += 1
            st.rerun()
    
    with col4:
        jump_to = st.number_input(
            "Jump to page",
            min_value=1,
            max_value=total_pages if total_pages > 0 else 1,
            value=st.session_state.user_page,
            step=1,
            key="user_jump_to",
            label_visibility="collapsed"
        )
        if jump_to != st.session_state.user_page and 1 <= jump_to <= total_pages:
            st.session_state.user_page = jump_to
            st.rerun()

def render_user_detail_view(db):
    """Render full-page detail view for user CRUD with validation"""
    
    user_id = st.session_state.user_selected_id
    is_new = user_id is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Add New User" if is_new else f"✏️ Edit User Details (ID: {user_id})"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to User Grid", key="user_back_to_grid"):
        st.session_state.user_view = "grid"
        st.session_state.user_selected_id = None
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
            'specialization': '',
            'years_experience': 0,
            'location': '',
            'website': '',
            'bio': '',
            'company_id': None,
            'company_name': ''
        }
    else:
        user = db.get_user_by_id(user_id)
        if not user:
            st.error(f"User with ID {user_id} not found")
            if st.button("Close", key="user_close_not_found"):
                st.session_state.user_view = "grid"
                st.session_state.user_selected_id = None
                st.rerun()
            return
    
    # ===== EDIT FORM WITH VALIDATION =====
    with st.form(key="user_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">👤 Account Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "Full Name *",
                value=user.get('full_name', ''),
                key="user_edit_full_name"
            )
            
            username = st.text_input(
                "Username *",
                value=user.get('username', ''),
                key="user_edit_username",
                help="3-30 characters, letters, numbers, and underscores only"
            )
            
            email = st.text_input(
                "Email Address *",
                value=user.get('email', ''),
                key="user_edit_email",
                help="Valid email format required"
            )
        
        with col2:
            mobile = st.text_input(
                "Mobile Number *",
                value=user.get('mobile_number', ''),
                key="user_edit_mobile",
                help="Bangladeshi mobile: 01XXXXXXXXX (11 digits)"
            )
            
            phone = st.text_input(
                "Phone",
                value=user.get('phone', ''),
                key="user_edit_phone"
            )
            
            # Company assignment
            companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
            company_options = {c['company_name']: c['id'] for c in companies}
            
            current_company_name = user.get('company_name', '')
            company_list = ["No Company"] + list(company_options.keys())
            
            if current_company_name and current_company_name in company_options:
                company_index = company_list.index(current_company_name)
            else:
                company_index = 0
            
            company_name = st.selectbox(
                "Company",
                options=company_list,
                index=company_index,
                key="user_edit_company"
            )
            company_id = company_options.get(company_name, None) if company_name != "No Company" else None
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PERMISSIONS & ACCESS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">⚙️ Permissions & Access</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            role_options = ["system_admin", "company_admin", "manager", "analyst", "estimator", "viewer", "individual"]
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
                key="user_edit_role"
            )
        
        with col2:
            is_active = st.radio(
                "Account Status",
                options=["Active", "Inactive"],
                index=0 if user.get('is_active', 0) == 1 else 1,
                key="user_edit_status"
            )
            is_active_bool = is_active == "Active"
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PROFESSIONAL INFORMATION =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">💼 Professional Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            specialization = st.text_input(
                "Specialization",
                value=user.get('specialization', ''),
                key="user_edit_specialization"
            )
            years_experience = st.number_input(
                "Years of Experience",
                min_value=0,
                max_value=50,
                value=user.get('years_experience', 0) or 0,
                key="user_edit_years_exp"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value=user.get('location', ''),
                key="user_edit_location"
            )
            website = st.text_input(
                "Website",
                value=user.get('website', ''),
                key="user_edit_website"
            )
        
        bio = st.text_area(
            "Bio",
            value=user.get('bio', ''),
            max_chars=500,
            key="user_edit_bio"
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
                    "🗑️ Delete User",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    st.warning("⚠️ Are you sure you want to delete this user?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Delete", key=f"user_confirm_delete_{user_id}"):
                            if db.delete_user(user_id):
                                st.success("User deleted successfully!")
                                st.session_state.user_view = "grid"
                                st.session_state.user_selected_id = None
                                st.rerun()
                            else:
                                st.error("Failed to delete user")
                    with col_cancel:
                        if st.button("❌ Cancel", key="user_cancel_delete"):
                            st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.user_view = "grid"
                st.session_state.user_selected_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION WITH VALIDATION =====
    if submitted:
        # Build updates dictionary
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
        
        if specialization:
            updates['specialization'] = safe_strip(specialization)
        updates['years_experience'] = years_experience if years_experience > 0 else None
        
        if location:
            updates['location'] = safe_strip(location)
        if website:
            updates['website'] = safe_strip(website)
        if bio:
            updates['bio'] = safe_strip(bio)
        updates['company_id'] = company_id
        print(f"🔍 DEBUG - company_name selected: {company_name}")
        print(f"🔍 DEBUG - company_options: {company_options}")
        print(f"🔍 DEBUG - resolved company_id: {company_id}")
        print(f"🔍 DEBUG - company_list: {company_list}")
        print(f"🔍 DEBUG - company_index: {company_index}")
        # ✅ Debug print to verify
        print(f"🔍 DEBUG - company_name: {company_name}")
        print(f"🔍 DEBUG - company_id resolved: {company_id}")

        # ✅ Add to updates
        updates['company_id'] = company_id

        # ✅ Debug print the final updates
        print(f"🔍 DEBUG - final updates: {updates}")
        if company_id is None or company_id == 0:
            if role != 'individual':
                validation_errors.append(
                    "❌ Users without a company assignment can only have the 'individual' role. "
                    "Please either assign a company or change the role to 'individual'."
                )
        # Rule 2: If company_id is set, role cannot be 'individual'
        else:
            if role == 'individual':
                validation_errors.append(
                    "❌ Users assigned to a company cannot have the 'individual' role. "
                    "Please select a different role (e.g., company_admin, manager, analyst, viewer)."
                )
    

        # Show validation errors
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # ============================================================
            # DUPLICATE CHECKING USING CRUD METHODS
            # ============================================================
            duplicate_errors = []
            exclude_id = None if is_new else user_id
        
            # ✅ DEBUG: Print values (INSIDE the submitted block)
            print(f"🔍 DEBUG - is_new: {is_new}")
            print(f"🔍 DEBUG - user_id: {user_id}")
            print(f"🔍 DEBUG - exclude_id: {exclude_id}")
            print(f"🔍 DEBUG - updates['username']: {updates.get('username')}")
            print(f"🔍 DEBUG - updates['email']: {updates.get('email')}")
            print(f"🔍 DEBUG - updates['mobile_number']: {updates.get('mobile_number')}")
            
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
                    # Create new user
                    st.info("Create user functionality would be implemented here")
                else:
                    if db.update_user(user_id, updates):
                        st.success("✅ User updated successfully!")
                        st.balloons()
                        st.session_state.user_view = "grid"
                        st.session_state.user_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to update user")

    
    st.markdown('</div>', unsafe_allow_html=True)