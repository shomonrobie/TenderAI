#modules/user_management.py
import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager
from utils.helpers import validate_password_strength
import re

db = UnifiedDatabaseManager()

import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager
from utils.helpers import validate_password_strength
import re

db = UnifiedDatabaseManager()

def render_user_management():
    """Enhanced user management with profile fields, avatar, and social links"""
    
    # ✅ Use selected_company_id if set (from admin dashboard)
    company_id = st.session_state.get('selected_company_id')
    
    # If no selected_company_id, fallback to session company_id
    if not company_id:
        company_id = st.session_state.get('company_id')
    
    # Get company name
    company_name = "Unknown Company"
    if company_id:
        company = db.get_company_by_id(company_id)
        if company:
            company_name = company.get('company_name', 'Unknown Company')
        else:
            st.error(f"Company with ID {company_id} not found!")
            return
    
    st.markdown(f"""
    <div class="main-header">
        <h1>👥 User Management - {company_name}</h1>
        <p>Manage team members, roles, permissions, and profiles for <strong>{company_name}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if not company_id:
        st.error("Company ID not found. Please log in again.")
        return
    
    # ========== SESSION STATE FOR PAGINATION & FILTERS ==========
    if 'user_page' not in st.session_state:
        st.session_state.user_page = 1
    if 'user_search' not in st.session_state:
        st.session_state.user_search = ""
    if 'user_role_filter' not in st.session_state:
        st.session_state.user_role_filter = ""
    if 'user_status_filter' not in st.session_state:
        st.session_state.user_status_filter = None
    if 'show_profile_fields' not in st.session_state:
        st.session_state.show_profile_fields = False
    
    # ========== FILTERS & SEARCH ==========
    st.markdown("### 🔍 Filter Users")
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        search_term = st.text_input("Search by name, username, or email", 
                                    value=st.session_state.user_search,
                                    key="user_search_input")
    with col2:
        role_filter = st.selectbox("Role", ["All", "company_admin", "manager", "analyst", "viewer"],
                                   index=0, key="role_filter_select")
    with col3:
        status_filter = st.selectbox("Status", ["All", "Active", "Inactive"],
                                     index=0, key="status_filter_select")
    with col4:
        # Toggle profile fields display
        show_profile = st.checkbox("Show Profile Fields", 
                                   value=st.session_state.show_profile_fields,
                                   key="show_profile_toggle")
        st.session_state.show_profile_fields = show_profile
    with col5:
        if st.button("🔄 Reset Filters", use_container_width=True):
            st.session_state.user_search = ""
            st.session_state.user_role_filter = ""
            st.session_state.user_status_filter = None
            st.session_state.user_page = 1
            st.session_state.show_profile_fields = False
            st.rerun()
    
    # Update session state based on current inputs
    st.session_state.user_search = search_term
    st.session_state.user_role_filter = "" if role_filter == "All" else role_filter
    st.session_state.user_status_filter = None if status_filter == "All" else (1 if status_filter == "Active" else 0)
    
    # ========== PAGINATION SETUP ==========
    users_per_page = 10
    offset = (st.session_state.user_page - 1) * users_per_page
    
    users, total = db.get_all_users_filtered(
        company_id=company_id,
        search=st.session_state.user_search,
        role=st.session_state.user_role_filter,
        status=st.session_state.user_status_filter,
        limit=users_per_page,
        offset=offset
    )
    
    # ========== STATS CARDS ==========
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Users", total)
    with col2:
        active_count = len([u for u in users if u.get('is_active') == 1])
        st.metric("Active Users", active_count)
    with col3:
        admin_count = len([u for u in users if u.get('role') in ['admin', 'company_admin']])
        st.metric("Admins", admin_count)
    with col4:
        analyst_count = len([u for u in users if u.get('role') == 'analyst'])
        st.metric("Analysts", analyst_count)
    with col5:
        # Count users with profile pictures
        avatar_count = len([u for u in users if u.get('avatar_url')])
        st.metric("With Avatar", avatar_count)
    
    # ========== ADD USER FORM (Collapsible) ==========
    with st.expander(f"➕ Add New User to {company_name}", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
                mobile_number = st.text_input("Mobile Number *", help="Bangladeshi mobile: 01XXXXXXXXX")
                role = st.selectbox("Role *", ["company_admin", "manager", "analyst", "viewer"])
            with col2:
                phone = st.text_input("Phone")
                location = st.text_input("Location", help="City, State, or Country")
                specialization = st.text_input("Specialization", help="e.g., Civil Engineer, Data Analyst")
                years_experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=0)
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Temporary Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            score = 0
            if not generate_password and password:
                score, msg, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<small style='color:{color}'>{msg}</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button(f"Add User to {company_name}", type="primary")
            if submitted:
                if not all([full_name, email, username, mobile_number]):
                    st.error("Please fill all required fields (*)")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                elif not generate_password and score < 60:
                    st.error("Password is too weak")
                else:
                    final_password = db.generate_random_password() if generate_password else password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip() if phone else None,
                        'mobile_number': mobile_number.strip(),
                        'role': role,
                        'location': location.strip() if location else None,
                        'specialization': specialization.strip() if specialization else None,
                        'years_experience': years_experience if years_experience > 0 else None
                    }
                    success, result = db.create_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        if generate_password:
                            st.success(f"User {full_name} added successfully! Password: `{final_password}`")
                        else:
                            st.success(f"User {full_name} added successfully!")
                        st.session_state.user_page = 1
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")
    
    # ========== TEAM MEMBERS LIST ==========
    st.markdown(f"### 📋 Team Members of {company_name}")

    if not users:
        st.info(f"No users found in {company_name} matching the criteria.")
        return

    for user in users:
        user_id = user.get('id')
        username = user.get('username', 'N/A')
        email = user.get('email', 'N/A')
        full_name = user.get('full_name', 'N/A')
        phone = user.get('phone', '') or ""
        mobile_number = user.get('mobile_number', 'N/A')
        mobile_verified = user.get('mobile_verified', False)
        role = user.get('role', 'viewer')
        is_active = user.get('is_active', 1)
        created_at = user.get('created_at', 'N/A')
        last_login = user.get('last_login', None)
        
        # Get profile fields (if available from user dict or fetch separately)
        avatar_url = user.get('avatar_url')
        bio = user.get('bio', '')
        location = user.get('location', '')
        website = user.get('website', '')
        specialization = user.get('specialization', '')
        years_experience = user.get('years_experience', 0)
        
        # Get social links for this user
        social_links = []
        try:
            social_links = db.get_user_social_links(user_id)
        except Exception:
            pass  # Table might not exist yet
        
        with st.expander(f"👤 {full_name} (@{username}) - {role.replace('_', ' ').title()}", expanded=False):
            
            # ========== USER HEADER WITH AVATAR ==========
            col_avatar, col_info = st.columns([1, 4])
            
            with col_avatar:
                if avatar_url:
                    try:
                        st.image(avatar_url, width=80)
                    except:
                        st.image(f"https://ui-avatars.com/api/?name={full_name}&size=80&background=6366f1&color=ffffff", width=80)
                else:
                    st.image(f"https://ui-avatars.com/api/?name={full_name}&size=80&background=6366f1&color=ffffff", width=80)
            
            with col_info:
                st.markdown(f"**Status:** {'🟢 Active' if is_active else '🔴 Inactive'}")
                st.markdown(f"**Mobile:** {mobile_number} {'✅ Verified' if mobile_verified else '❌ Not Verified'}")
                if specialization:
                    st.markdown(f"**Specialization:** {specialization}")
                if years_experience and years_experience > 0:
                    st.markdown(f"**Experience:** {years_experience} years")
            
            # ========== SOCIAL LINKS PREVIEW ==========
            if social_links:
                st.markdown("**Social Links:**")
                platform_icons = {
                    "facebook": "📘", "twitter": "🐦", "instagram": "📸", 
                    "linkedin": "💼", "github": "🐙", "youtube": "📺",
                    "tiktok": "🎵", "pinterest": "📌", "reddit": "🤖",
                    "whatsapp": "📱", "telegram": "✈️", "discord": "🎮",
                    "slack": "💬", "medium": "✍️", "dev.to": "💻"
                }
                link_cols = st.columns(min(len(social_links), 4))
                for idx, link in enumerate(social_links[:4]):
                    with link_cols[idx % 4]:
                        platform = link.get('platform', '')
                        url = link.get('url', '#')
                        icon = platform_icons.get(platform, "🔗")
                        st.markdown(f"{icon} [{platform.title()}]({url})")
                if len(social_links) > 4:
                    st.caption(f"and {len(social_links) - 4} more...")
                st.divider()
            
            # ========== EDIT FORM ==========
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("#### 📝 Edit User Information")
                
                # Basic Information
                new_full_name = st.text_input("Full Name", value=full_name, key=f"name_{user_id}")
                new_email = st.text_input("Email", value=email, key=f"email_{user_id}")
                new_phone = st.text_input("Phone", value=phone, key=f"phone_{user_id}")
                
                # Read-only mobile
                st.text_input("Mobile Number (Read-Only)", value=mobile_number, disabled=True, key=f"mobile_{user_id}")
                
                # Mobile verification status
                if mobile_verified:
                    st.success("📱 Mobile Verified ✅")
                else:
                    st.warning("📱 Mobile Not Verified ⚠️")
                    if st.button("📱 Verify Mobile", key=f"verify_mobile_{user_id}"):
                        db.update_user(user_id, mobile_verified=1)
                        st.success("Mobile verified successfully!")
                        st.rerun()
                
                # Role and Status
                col_role, col_status = st.columns(2)
                with col_role:
                    new_role = st.selectbox(
                        "Role",
                        options=["company_admin", "manager", "analyst", "viewer"],
                        index=["company_admin", "manager", "analyst", "viewer"].index(role) if role in ["company_admin", "manager", "analyst", "viewer"] else 2,
                        key=f"role_{user_id}"
                    )
                with col_status:
                    new_status = st.checkbox("Active", value=bool(is_active), key=f"status_{user_id}")
                
                st.divider()
                
                # Profile Fields (Enhanced)
                st.markdown("#### 👤 Profile Information")
                
                # Only show profile fields if toggled or always show
                if st.session_state.show_profile_fields:
                    new_location = st.text_input("Location", value=location or "", key=f"location_{user_id}")
                    new_website = st.text_input("Website", value=website or "", key=f"website_{user_id}")
                    new_specialization = st.text_input("Specialization", value=specialization or "", key=f"specialization_{user_id}")
                    new_years_experience = st.number_input("Years of Experience", 
                                                         min_value=0, max_value=50, 
                                                         value=years_experience or 0,
                                                         key=f"experience_{user_id}")
                    new_bio = st.text_area("Bio", value=bio or "", 
                                         key=f"bio_{user_id}",
                                         help="Brief description about the user (max 500 characters)",
                                         max_chars=500)
                else:
                    # Show compact profile info
                    if location or website or specialization:
                        st.markdown("**Profile Info:**")
                        if location:
                            st.markdown(f"📍 **Location:** {location}")
                        if website:
                            st.markdown(f"🌐 **Website:** {website}")
                        if specialization:
                            st.markdown(f"🎯 **Specialization:** {specialization}")
                        if years_experience:
                            st.markdown(f"📅 **Experience:** {years_experience} years")
                    else:
                        st.info("No profile information added yet. Toggle 'Show Profile Fields' to add.")
                
                # Save button
                if st.button("💾 Save All Changes", key=f"save_{user_id}", type="primary"):
                    updates = {}
                    
                    # Basic info updates
                    if new_full_name != full_name:
                        updates['full_name'] = new_full_name
                    if new_email != email:
                        if re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                            updates['email'] = new_email
                        else:
                            st.error("Invalid email format")
                    if new_phone != phone:
                        updates['phone'] = new_phone
                    if new_role != role:
                        updates['role'] = new_role
                    if new_status != bool(is_active):
                        updates['is_active'] = 1 if new_status else 0
                    
                    # Profile field updates
                    if st.session_state.show_profile_fields:
                        if new_location != location:
                            updates['location'] = new_location
                        if new_website != website:
                            updates['website'] = new_website
                        if new_specialization != specialization:
                            updates['specialization'] = new_specialization
                        if new_years_experience != years_experience:
                            updates['years_experience'] = new_years_experience
                        if new_bio != bio:
                            updates['bio'] = new_bio
                    
                    if updates:
                        success = db.update_user(user_id, **updates)
                        if success:
                            # Log activity
                            db.log_user_activity(user_id, 'profile_update', 'Updated user information by admin')
                            st.success("User updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update user")
                    else:
                        st.info("No changes made")
            
            # ========== ACTIONS PANEL ==========
            with col2:
                st.markdown("#### ⚡ Quick Actions")
                
                # View full profile
                if st.button("👤 View Full Profile", key=f"view_profile_{user_id}", use_container_width=True):
                    st.session_state.view_user_id = user_id
                    st.session_state.page = "view_user_profile"
                    st.rerun()
                
                st.divider()
                
                # Reset password
                if st.button("🔑 Reset Password", key=f"reset_pw_{user_id}", use_container_width=True):
                    success, new_pw = db.reset_user_password(user_id)
                    if success:
                        st.success(f"✅ New password: `{new_pw}`")
                        st.info("📋 Please copy this password and share it securely with the user.")
                    else:
                        st.error(f"Failed to reset password: {new_pw}")
                
                st.divider()
                
                # Delete user (except self)
                if user_id != st.session_state.user_id:
                    if st.button("🗑️ Delete User", key=f"delete_{user_id}", type="secondary", use_container_width=True):
                        success = db.delete_user(user_id)
                        if success:
                            st.success(f"User {full_name} deleted successfully")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                else:
                    st.warning("🔒 You cannot delete your own account")
                
                st.divider()
                
                # User metadata
                st.markdown("**📊 User Info**")
                st.caption(f"**Created:** {str(created_at)[:16] if created_at else 'N/A'}")
                st.caption(f"**Last Login:** {str(last_login)[:16] if last_login else 'Never'}")
                st.caption(f"**Mobile Verified:** {'✅ Yes' if mobile_verified else '❌ No'}")
                if avatar_url:
                    st.caption("**Has Profile Picture:** ✅")
    
    # ========== PAGINATION CONTROLS ==========
    total_pages = (total + users_per_page - 1) // users_per_page
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=(st.session_state.user_page <= 1)):
                st.session_state.user_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.user_page} of {total_pages}")
            # Page input for direct navigation
            page_input = st.number_input("Go to page", min_value=1, max_value=total_pages, 
                                        value=st.session_state.user_page, step=1, 
                                        key="page_input", label_visibility="collapsed")
            if page_input != st.session_state.user_page:
                st.session_state.user_page = page_input
                st.rerun()
        with col3:
            if st.button("Next ▶", disabled=(st.session_state.user_page >= total_pages)):
                st.session_state.user_page += 1
                st.rerun()
    
    # ========== EXPORT OPTIONS ==========
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("📊 Export Users (CSV)", use_container_width=True):
            # Export current filtered users to CSV
            if users:
                df = pd.DataFrame(users)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"users_{company_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No users to export")
    
    with col2:
        if st.button("📋 Copy Email List", use_container_width=True):
            if users:
                emails = [u.get('email') for u in users if u.get('email')]
                st.code('\n'.join(emails), language="text")
            else:
                st.warning("No users to copy")
    
    with col3:
        if st.button("📱 Copy Mobile List", use_container_width=True):
            if users:
                mobiles = [u.get('mobile_number') for u in users if u.get('mobile_number')]
                st.code('\n'.join(mobiles), language="text")
            else:
                st.warning("No users to copy")
    
    # ========== BACK BUTTON ==========
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Company Management", use_container_width=True):
            # ✅ Clear selected company
            if 'selected_company_id' in st.session_state:
                del st.session_state.selected_company_id
            st.session_state.page = "admin_dashboard"
            st.rerun()

def render_user_management_bak():
    """Full user management with CRUD, search, pagination, inline editing"""
    
    # ✅ Use selected_company_id if set (from admin dashboard)
    company_id = st.session_state.get('selected_company_id')
    
    # If no selected_company_id, fallback to session company_id
    if not company_id:
        company_id = st.session_state.get('company_id')
    
    # Get company name
    company_name = "Unknown Company"
    if company_id:
        company = db.get_company_by_id(company_id)
        if company:
            company_name = company.get('company_name', 'Unknown Company')
        else:
            st.error(f"Company with ID {company_id} not found!")
            return
    
    st.markdown(f"""
    <div class="main-header">
        <h1>👥 User Management - {company_name}</h1>
        <p>Manage team members, roles, and permissions for <strong>{company_name}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    if not company_id:
        st.error("Company ID not found. Please log in again.")
        return
    
    # ========== SESSION STATE FOR PAGINATION & FILTERS ==========
    if 'user_page' not in st.session_state:
        st.session_state.user_page = 1
    if 'user_search' not in st.session_state:
        st.session_state.user_search = ""
    if 'user_role_filter' not in st.session_state:
        st.session_state.user_role_filter = ""
    if 'user_status_filter' not in st.session_state:
        st.session_state.user_status_filter = None
    
    # ========== FILTERS & SEARCH ==========
    st.markdown("### 🔍 Filter Users")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search_term = st.text_input("Search by name, username, or email", 
                                    value=st.session_state.user_search,
                                    key="user_search_input")
    with col2:
        role_filter = st.selectbox("Role", ["All", "company_admin", "manager", "analyst", "viewer"],
                                   index=0, key="role_filter_select")
    with col3:
        status_filter = st.selectbox("Status", ["All", "Active", "Inactive"],
                                     index=0, key="status_filter_select")
    with col4:
        if st.button("🔄 Reset Filters", use_container_width=True):
            st.session_state.user_search = ""
            st.session_state.user_role_filter = ""
            st.session_state.user_status_filter = None
            st.session_state.user_page = 1
            # ✅ Keep the selected company
            st.rerun()
    
    # Update session state based on current inputs
    st.session_state.user_search = search_term
    st.session_state.user_role_filter = "" if role_filter == "All" else role_filter
    st.session_state.user_status_filter = None if status_filter == "All" else (1 if status_filter == "Active" else 0)
    
    # ========== PAGINATION SETUP ==========
    users_per_page = 10
    offset = (st.session_state.user_page - 1) * users_per_page
    
    users, total = db.get_all_users_filtered(
        company_id=company_id,
        search=st.session_state.user_search,
        role=st.session_state.user_role_filter,
        status=st.session_state.user_status_filter,
        limit=users_per_page,
        offset=offset
    )
    
    # Stats cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total)
    with col2:
        active_count = len([u for u in users if u.get('is_active') == 1])
        st.metric("Active Users", active_count)
    with col3:
        admin_count = len([u for u in users if u.get('role') in ['admin', 'company_admin']])
        st.metric("Admins", admin_count)
    with col4:
        analyst_count = len([u for u in users if u.get('role') == 'analyst'])
        st.metric("Analysts", analyst_count)
    
    # ========== ADD USER FORM (Collapsible) ==========
    with st.expander(f"➕ Add New User to {company_name}", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
                mobile_number = st.text_input("Mobile Number *", help="Bangladeshi mobile: 01XXXXXXXXX")
                role = st.selectbox("Role *", ["company_admin", "manager", "analyst", "viewer"])
            with col2:
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Temporary Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            score = 0
            if not generate_password and password:
                score, msg, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<small style='color:{color}'>{msg}</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button(f"Add User to {company_name}", type="primary")
            if submitted:
                if not all([full_name, email, username, mobile_number]):
                    st.error("Please fill all required fields (*)")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                elif not generate_password and score < 60:
                    st.error("Password is too weak")
                else:
                    final_password = db.generate_random_password() if generate_password else password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip(),
                        'mobile_number': mobile_number.strip(),
                        'role': role
                    }
                    success, result = db.create_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        if generate_password:
                            st.success(f"User {full_name} added successfully! Password: `{final_password}`")
                        else:
                            st.success(f"User {full_name} added successfully!")
                        st.session_state.user_page = 1
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")
    
    # ========== TEAM MEMBERS LIST ==========
    st.markdown(f"### 📋 Team Members of {company_name}")

    if not users:
        st.info(f"No users found in {company_name} matching the criteria.")
        return

    for user in users:
        user_id = user.get('id')
        username = user.get('username', 'N/A')
        email = user.get('email', 'N/A')
        full_name = user.get('full_name', 'N/A')
        phone = user.get('phone', '') or ""
        mobile_number = user.get('mobile_number', 'N/A')
        mobile_verified = user.get('mobile_verified', False)
        role = user.get('role', 'viewer')
        is_active = user.get('is_active', 1)
        created_at = user.get('created_at', 'N/A')
        last_login = user.get('last_login', None)
        
        with st.expander(f"👤 {full_name} (@{username}) - {role.replace('_', ' ').title()}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.text_input("Username (Read-Only)", value=username, disabled=True, key=f"username_{user_id}")
                
                new_full_name = st.text_input("Full Name", value=full_name, key=f"name_{user_id}")
                new_email = st.text_input("Email", value=email, key=f"email_{user_id}")
                new_phone = st.text_input("Phone", value=phone, key=f"phone_{user_id}")
                st.text_input("Mobile Number (Read-Only)", value=mobile_number, disabled=True, key=f"mobile_{user_id}")
                
                if mobile_verified:
                    st.success("📱 Mobile Verified ✅")
                else:
                    st.warning("📱 Mobile Not Verified ⚠️")
                
                new_role = st.selectbox(
                    "Role",
                    options=["company_admin", "manager", "analyst", "viewer"],
                    index=["company_admin", "manager", "analyst", "viewer"].index(role) if role in ["company_admin", "manager", "analyst", "viewer"] else 2,
                    key=f"role_{user_id}"
                )
                new_status = st.checkbox("Active", value=bool(is_active), key=f"status_{user_id}")
                
                if st.button("💾 Save Changes", key=f"save_{user_id}"):
                    updates = {}
                    if new_full_name != full_name:
                        updates['full_name'] = new_full_name
                    if new_email != email:
                        if re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                            updates['email'] = new_email
                        else:
                            st.error("Invalid email format")
                    if new_phone != phone:
                        updates['phone'] = new_phone
                    if new_role != role:
                        updates['role'] = new_role
                    if new_status != bool(is_active):
                        updates['is_active'] = 1 if new_status else 0
                    
                    if updates:
                        success = db.update_user(user_id, **updates)
                        if success:
                            st.success("User updated successfully")
                            st.rerun()
                        else:
                            st.error("Failed to update user")
                    else:
                        st.info("No changes made")
            
            with col2:
                st.markdown("#### Actions")
                
                if st.button("🔑 Reset Password", key=f"reset_pw_{user_id}"):
                    success, new_pw = db.reset_user_password(user_id)
                    if success:
                        st.success(f"New password: `{new_pw}`")
                
                if user_id != st.session_state.user_id:
                    if st.button("🗑️ Delete User", key=f"delete_{user_id}", type="secondary"):
                        success = db.delete_user(user_id)
                        if success:
                            st.success(f"User {full_name} deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                else:
                    st.caption("(You cannot delete your own account)")
                
                st.markdown("---")
                st.markdown(f"**Created:** {str(created_at)[:16] if created_at else 'N/A'}")
                st.markdown(f"**Last Login:** {str(last_login)[:16] if last_login else 'Never'}")
                st.markdown(f"**Mobile Verified:** {'✅ Yes' if mobile_verified else '❌ No'}")
    
    # ========== PAGINATION CONTROLS ==========
    total_pages = (total + users_per_page - 1) // users_per_page
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=(st.session_state.user_page <= 1)):
                st.session_state.user_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.user_page} of {total_pages}")
        with col3:
            if st.button("Next ▶", disabled=(st.session_state.user_page >= total_pages)):
                st.session_state.user_page += 1
                st.rerun()
    
    # ========== BACK BUTTON ==========
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Company Management", use_container_width=True):
            # ✅ Clear selected company
            if 'selected_company_id' in st.session_state:
                del st.session_state.selected_company_id
            st.session_state.page = "admin_dashboard"
            st.rerun()


def render_role_management():
    """UI for managing role-based permissions (admin/company_admin only)"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Role & Permission Management</h1>
        <p>Define what each role can do in the system</p>
    </div>
    """, unsafe_allow_html=True)

    # Check permission
    user_role = st.session_state.get('user_role')
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("❌ You don't have permission to manage roles.")
        return

    # Get all roles and their current permissions
    roles = db.get_all_roles()
    if not roles:
        st.warning("No role data found. Please contact support.")
        return

    st.info("💡 Changes here affect what users with each role can see and do. Permissions are saved immediately.")
    
    # Tabs for different permission categories
    tab1, tab2 = st.tabs(["📊 General Permissions", "🏗️ Rate Management Permissions"])
    
    with tab1:
        render_general_permissions(roles)
    
    with tab2:
        render_rate_permissions(roles)


def render_general_permissions(roles):
    """Render general system permissions"""
    
    for role_info in roles:
        role_name = role_info['role']
        perms = role_info['permissions']
        
        # Skip editing 'admin' if you want to lock it
        if role_name == 'admin' and st.session_state.get('user_role') != 'system_admin':
            st.warning(f"Role '{role_name}' permissions are locked for your account level.")
            continue
        
        with st.expander(f"📌 Role: **{role_name.replace('_', ' ').title()}**", expanded=False):
            # Prepare permission keys
            perm_keys = [
                'manage_users', 'manage_tenders', 'run_analysis',
                'view_reports', 'export_data', 'change_plans',
                'manage_team', 'delete_any'
            ]
            
            # Use columns to display checkboxes in a grid
            col_count = 4
            cols = st.columns(col_count)
            updated_perms = {}
            
            for i, key in enumerate(perm_keys):
                col = cols[i % col_count]
                current = perms.get(key, False)
                label = key.replace('_', ' ').title()
                with col:
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_{key}")
                    updated_perms[key] = new_val
            
            # Save button for this role
            if st.button(f"💾 Save General Permissions for {role_name}", key=f"save_general_{role_name}"):
                # Merge with existing rate permissions
                current_perms = db.get_role_permissions(role_name)
                current_perms.update(updated_perms)
                success = db.update_role_permissions(role_name, current_perms)
                if success:
                    st.success(f"Permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions.")


def render_rate_permissions(roles):
    """Render rate management permissions"""
    
    st.markdown("#### 🏗️ Rate Management Permissions")
    st.caption("Control access to Zones, Chapters, Parents, Children, and Versions")
    
    for role_info in roles:
        role_name = role_info['role']
        perms = role_info['permissions']
        
        if role_name == 'admin' and st.session_state.get('user_role') != 'system_admin':
            continue
        
        with st.expander(f"📌 Role: **{role_name.replace('_', ' ').title()}**", expanded=False):
            # Rate management permission keys
            rate_perm_keys = [
                'view_rates', 'edit_rates', 'delete_rates',
                'manage_zones', 'manage_chapters', 'manage_parents',
                'manage_children', 'manage_versions'
            ]
            
            # Display in two columns
            col1, col2 = st.columns(2)
            updated_perms = {}
            
            # Column 1
            with col1:
                for key in rate_perm_keys[:4]:
                    current = perms.get(key, False)
                    label = key.replace('_', ' ').title()
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_rate_{key}")
                    updated_perms[key] = new_val
            
            # Column 2
            with col2:
                for key in rate_perm_keys[4:]:
                    current = perms.get(key, False)
                    label = key.replace('_', ' ').title()
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_rate_{key}")
                    updated_perms[key] = new_val
            
            # Save button
            if st.button(f"💾 Save Rate Permissions for {role_name}", key=f"save_rate_{role_name}"):
                current_perms = db.get_role_permissions(role_name)
                current_perms.update(updated_perms)
                success = db.update_role_permissions(role_name, current_perms)
                if success:
                    st.success(f"Rate permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions.")


def render_permission_matrix(roles):
    """Display permission matrix for quick reference"""
    with st.expander("📊 Permission Matrix (Read‑only)", expanded=False):
        matrix_data = []
        for role_info in roles:
            row = {'Role': role_info['role'].replace('_', ' ').title()}
            perms = role_info['permissions']
            
            # General permissions
            for key in ['manage_users', 'manage_tenders', 'run_analysis', 'view_reports', 'export_data']:
                row[key.replace('_', ' ').title()] = '✅' if perms.get(key, False) else '❌'
            
            # Rate permissions
            for key in ['view_rates', 'edit_rates', 'manage_parents', 'manage_children']:
                row[key.replace('_', ' ').title()] = '✅' if perms.get(key, False) else '❌'
            
            matrix_data.append(row)
        
        st.dataframe(matrix_data, use_container_width=True, hide_index=True)
