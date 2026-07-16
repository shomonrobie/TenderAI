"""
Role Management Module - State-Driven View Router Pattern
Uses st.dataframe with singleton selection and comprehensive validation
All database operations use RoleCRUD methods - NO RAW SQL
"""

import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================================
# CONSTANTS
# ============================================================

ROLE_DESCRIPTIONS = {
    'admin': '👑 Full platform access',
    'system_admin': '👑 Full platform access',
    'system_support': '🛠️ Can view all companies, support access',
    'system_auditor': '📊 Read-only across platform',
    'company_admin': '🏢 Full company management',
    'company_manager': '📋 Can manage tenders and create users',
    'manager': '📋 Can manage tenders and create users',
    'analyst': '🔬 Can run analyses and view reports',
    'viewer': '👁️ Read-only access',
    'individual': '👤 Full company management for individual users',
    'tender_manager': '📋 Can manage tenders, submit bids, and approve bids',
    'estimator': '📊 Can create estimates and analyze costs'
}

# ============================================================
# PERMISSION DEFINITIONS
# ============================================================

ALL_PERMISSIONS = [
    # User Management
    'manage_users', 'manage_team', 'create_user', 'delete_user',
    'can_create_user', 'can_delete_user', 'can_manage_company_users',
    
    # Content Management
    'manage_tenders', 'view_reports', 'export_data',
    'can_manage_tenders', 'can_edit_company_settings',
    
    # Analysis
    'run_analysis', 'view_rates', 'edit_rates', 'delete_rates',
    'can_view_company_analyses',
    
    # System
    'manage_zones', 'manage_versions', 'manage_chapters',
    'manage_parents', 'manage_children', 'change_plans',
    'delete_any', 'can_manage_company_subscription',
    
    # Tender Management
    'can_view_tenders', 'can_create_tender', 'can_edit_tender',
    'can_submit_bid', 'can_manage_team', 'can_approve_bids',
    
    # Additional
    'can_create_estimates', 'can_manage_alerts', 'can_send_notifications',
    'can_receive_alerts', 'view_analytics', 'export_analytics',
    'create_custom_reports', 'can_manage_system_users', 'can_view_all_analyses',
    'can_manage_roles', 'can_view_system_logs'
]

PERMISSION_CATEGORIES = {
    "👤 User Management": [
        'manage_users', 'manage_team', 'create_user', 'delete_user',
        'can_create_user', 'can_delete_user', 'can_manage_company_users'
    ],
    "📄 Content Management": [
        'manage_tenders', 'view_reports', 'export_data',
        'can_manage_tenders', 'can_edit_company_settings'
    ],
    "🔬 Analysis": [
        'run_analysis', 'view_rates', 'edit_rates', 'delete_rates',
        'can_view_company_analyses'
    ],
    "⚙️ System": [
        'manage_zones', 'manage_versions', 'manage_chapters',
        'manage_parents', 'manage_children', 'change_plans',
        'delete_any', 'can_manage_company_subscription'
    ],
    "📋 Tender Management": [
        'can_view_tenders', 'can_create_tender', 'can_edit_tender',
        'can_submit_bid', 'can_manage_team', 'can_approve_bids'
    ],
    "📊 Advanced": [
        'view_analytics', 'export_analytics', 'create_custom_reports',
        'can_send_notifications', 'can_receive_alerts', 'can_manage_alerts'
    ],
    "🔐 System Admin": [
        'can_manage_system_users', 'can_view_all_analyses',
        'can_manage_roles', 'can_view_system_logs'
    ]
}


def get_role_description(role_name: str) -> str:
    """Get description for a role"""
    return ROLE_DESCRIPTIONS.get(role_name, 'Custom role')


# ============================================================
# MAIN RENDER FUNCTIONS
# ============================================================

def render_role_management(db):
    """Main entry point for role management with view routing"""
    
    # Initialize session state
    if "role_view" not in st.session_state:
        st.session_state.role_view = "grid"
    if "role_selected_name" not in st.session_state:
        st.session_state.role_selected_name = None
    if "role_page" not in st.session_state:
        st.session_state.role_page = 1
    if "role_search" not in st.session_state:
        st.session_state.role_search = ""
    if "role_per_page" not in st.session_state:
        st.session_state.role_per_page = 10
    
    if st.session_state.role_view == "detail":
        render_role_detail_view(db)
    else:
        render_role_grid_view(db)


def render_role_grid_view(db):
    """Render spreadsheet-style grid view using st.dataframe"""
    
    st.markdown("### 🔐 ROLE MANAGEMENT SYSTEM")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("➕ Add New Role", key="role_add_btn", type="primary", use_container_width=True):
            st.session_state.role_selected_name = None
            st.session_state.role_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.role_search = st.text_input(
            "🔍 Search roles...",
            placeholder="Role name or description...",
            value=st.session_state.role_search,
            key="role_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        st.session_state.role_per_page = st.selectbox(
            "Rows",
            options=[5, 10, 25, 50],
            index=[5, 10, 25, 50].index(st.session_state.role_per_page) if st.session_state.role_per_page in [5, 10, 25, 50] else 1,
            key="role_per_page_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH ROLES =====
    try:
        roles = db.get_all_roles()
    except Exception as e:
        st.error(f"Error loading roles: {e}")
        return
    
    if not roles:
        st.info("No roles found. Click 'Add New Role' to create one.")
        return
    
    # ===== FILTER ROLES =====
    if st.session_state.role_search:
        search_lower = st.session_state.role_search.lower()
        roles = [
            r for r in roles
            if search_lower in r.get('role_name', '').lower()
            or search_lower in get_role_description(r.get('role_name', '')).lower()
        ]
    
    if not roles:
        st.info("No roles match the search criteria")
        return
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Roles", len(roles))
    with col2:
        # Count system roles
        system_roles = [r for r in roles if r.get('role_name') in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'viewer']]
        st.metric("System Roles", len(system_roles))
    with col3:
        custom_roles = len(roles) - len(system_roles)
        st.metric("Custom Roles", custom_roles)
    with col4:
        # Count users with roles
        total_users = 0
        for role in roles:
            users = db.get_users_with_role(role.get('role_name'))
            total_users += len(users)
        st.metric("Users with Roles", total_users)
    
    st.markdown("---")
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, role in enumerate(roles):
        role_name = role.get('role_name')
        permissions = role.get('permissions', {})
        perm_count = len([p for p in permissions.values() if p])
        
        users = db.get_users_with_role(role_name)
        user_count = len(users)
        
        is_system = role_name in ['admin', 'system_admin', 'company_admin', 'manager', 'company_manager', 'analyst', 'viewer']
        description = get_role_description(role_name)
        
        df_data.append({
            'id': role.get('id'),
            'role_name': role_name,
            'display_name': role_name.replace('_', ' ').title(),
            'description': description,
            'permissions': perm_count,
            'users': user_count,
            'is_system': is_system,
            'created_at': role.get('created_at', ''),
            '_record': role
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['display_name', 'description', 'permissions', 'users', 'is_system']
    
    event = st.dataframe(
        df[display_columns],
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "display_name": st.column_config.Column("Role", width="medium"),
            "description": st.column_config.Column("Description", width="large"),
            "permissions": st.column_config.Column("Permissions", width="small"),
            "users": st.column_config.Column("Users", width="small"),
            "is_system": st.column_config.Column("System", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            role_name = row_data.get('role_name')
            if role_name:
                st.session_state.role_selected_name = role_name
                st.session_state.role_view = "detail"
                st.rerun()
    
    st.caption(f"Showing {len(roles)} roles")


def render_role_detail_view(db):
    """Render full-page detail view for role CRUD with checkbox permissions"""
    
    role_name = st.session_state.role_selected_name
    is_new = role_name is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Add New Role" if is_new else f"✏️ Edit Role: {role_name.replace('_', ' ').title()}"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to Role Grid", key="role_back_to_grid"):
        st.session_state.role_view = "grid"
        st.session_state.role_selected_name = None
        st.rerun()
    
    st.divider()
    
    # ===== GET ROLE DATA =====
    if is_new:
        role = {
            'id': None,
            'role_name': '',
            'permissions': {},
            'created_at': None,
            'updated_at': None
        }
        is_system = False
    else:
        role = db.get_role_by_name(role_name)
        if not role:
            st.error(f"Role '{role_name}' not found")
            if st.button("Close", key="role_close_not_found"):
                st.session_state.role_view = "grid"
                st.session_state.role_selected_name = None
                st.rerun()
            return
        
        is_system = role_name in ['admin', 'system_admin', 'company_admin', 'manager', 'company_manager', 'analyst', 'viewer']
    
    # ===== EDIT FORM WITH CHECKBOX PERMISSIONS =====
    with st.form(key="role_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📋 Role Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if is_new:
                role_name_input = st.text_input(
                    "Role Name *",
                    placeholder="e.g., tender_manager, content_editor",
                    help="Use lowercase with underscores (e.g., tender_manager)",
                    key="role_edit_name"
                )
                
                # Validate role name format
                if role_name_input and not re.match(r'^[a-z_][a-z0-9_]*$', role_name_input):
                    st.warning("Role name should use lowercase letters, numbers, and underscores only")
            else:
                st.text_input(
                    "Role Name",
                    value=role_name,
                    disabled=True,
                    key="role_edit_name"
                )
                role_name_input = role_name
        
        with col2:
            description = st.text_input(
                "Role Description",
                value=get_role_description(role_name) if not is_new else "",
                placeholder="e.g., Can manage tenders and submit bids",
                key="role_edit_description"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ============================================================
        # PERMISSIONS - CHECKBOXES
        # ============================================================
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">🔑 Permissions</div>', unsafe_allow_html=True)
        st.caption("Enable or disable permissions for this role")
        
        permissions = role.get('permissions', {})
        updated_perms = {}
        
        # Display permissions by category with checkboxes
        for category, perm_keys in PERMISSION_CATEGORIES.items():
            st.markdown(f"**{category}**")
            cols = st.columns(3)
            
            for i, key in enumerate(perm_keys):
                # Get current value
                current_value = permissions.get(key, False)
                
                with cols[i % 3]:
                    new_value = st.checkbox(
                        key.replace('_', ' ').title(),
                        value=current_value,
                        key=f"role_perm_{role_name}_{key}" if not is_new else f"new_role_perm_{key}",
                        help=f"Permission: {key}"
                    )
                    updated_perms[key] = new_value
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ============================================================
        # SYSTEM ROLE WARNING
        # ============================================================
        if not is_new and is_system:
            st.info(f"🔒 '{role_name.replace('_', ' ').title()}' is a system role. You can still modify permissions.")
        
        # ============================================================
        # FORM ACTIONS
        # ============================================================
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Save Changes",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if not is_new and not is_system:
                delete_clicked = st.form_submit_button(
                    "🗑️ Delete Role",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    users = db.get_users_with_role(role_name)
                    if users:
                        st.error(f"❌ Cannot delete '{role_name}' - it has {len(users)} users assigned. Reassign users first.")
                    else:
                        st.warning(f"⚠️ Are you sure you want to delete role '{role_name}'?")
                        col_confirm, col_cancel = st.columns(2)
                        with col_confirm:
                            if st.button("✅ Confirm Delete", key=f"role_confirm_delete_{role_name}"):
                                if db.delete_role(role_name):
                                    st.success(f"✅ Role '{role_name}' deleted!")
                                    st.session_state.role_view = "grid"
                                    st.session_state.role_selected_name = None
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete role")
                        with col_cancel:
                            if st.button("❌ Cancel", key="role_cancel_delete"):
                                st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.role_view = "grid"
                st.session_state.role_selected_name = None
                st.rerun()
    
    # ============================================================
    # PROCESS FORM SUBMISSION
    # ============================================================
    if submitted:
        validation_errors = []
        
        if is_new:
            # Validate role name
            if not role_name_input:
                validation_errors.append("Role name is required")
            elif not re.match(r'^[a-z_][a-z0-9_]*$', role_name_input):
                validation_errors.append("Role name should use lowercase letters, numbers, and underscores only")
            
            # Check if role exists
            existing = db.get_role_by_name(role_name_input)
            if existing:
                validation_errors.append(f"Role '{role_name_input}' already exists")
        
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # Add description to permissions
            if description:
                updated_perms['description'] = description
            
            if is_new:
                # Create new role
                if db.create_role(role_name_input, updated_perms, description):
                    st.success(f"✅ Role '{role_name_input}' created successfully!")
                    st.balloons()
                    st.session_state.role_view = "grid"
                    st.session_state.role_selected_name = None
                    st.rerun()
                else:
                    st.error("❌ Failed to create role")
            else:
                # Update permissions for role (including system roles)
                if db.update_role_permissions(role_name, updated_perms):
                    st.success(f"✅ Permissions for '{role_name}' updated successfully!")
                    st.balloons()
                    st.session_state.role_view = "grid"
                    st.session_state.role_selected_name = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update permissions")
    
    st.markdown('</div>', unsafe_allow_html=True)


# Export functions
__all__ = [
    'render_role_management',
    'render_role_grid_view',
    'render_role_detail_view',
    'ROLE_DESCRIPTIONS',
    'PERMISSION_CATEGORIES',
    'ALL_PERMISSIONS',
    'get_role_description'
]