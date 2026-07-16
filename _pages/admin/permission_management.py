"""
Permission Management Module
CRUD operations for permissions per role using checkboxes from permissions table
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any


# ============================================================
# PERMISSION TEMPLATES
# ============================================================

PERMISSION_TEMPLATES = {
    "Tender Manager": {
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_submit_bid': True,
        'can_manage_team': True,
        'can_approve_bids': True,
        'description': 'Can manage tenders, submit bids, and approve bids'
    },
    "Estimator": {
        'can_view_tenders': True,
        'can_create_estimates': True,
        'can_edit_rates': True,
        'view_rates': True,
        'run_analysis': True,
        'description': 'Can create estimates and analyze costs'
    },
    "Read Only": {
        'view_reports': True,
        'view_rates': True,
        'can_view_company_analyses': True,
        'description': 'Read-only access'
    },
    "Full Access": {
        'manage_users': True,
        'manage_tenders': True,
        'run_analysis': True,
        'view_reports': True,
        'export_data': True,
        'change_plans': True,
        'manage_team': True,
        'delete_any': True,
        'view_rates': True,
        'edit_rates': True,
        'delete_rates': True,
        'manage_zones': True,
        'manage_chapters': True,
        'manage_parents': True,
        'manage_children': True,
        'manage_versions': True,
        'can_create_user': True,
        'can_delete_user': True,
        'can_manage_tenders': True,
        'can_manage_company_users': True,
        'can_edit_company_settings': True,
        'can_view_company_analyses': True,
        'can_manage_company_subscription': True,
        'description': 'Full access to all features'
    }
}


def render_permission_management(db):
    """Render permission management UI with CRUD operations"""
    
    st.markdown("### 🔑 Permission Management")
    st.caption("Add, edit, and delete permissions per role")
    
    # Initialize session state
    if "perm_selected_role" not in st.session_state:
        st.session_state.perm_selected_role = None
    if "perm_edit_mode" not in st.session_state:
        st.session_state.perm_edit_mode = False
    
    # Get all roles
    roles = db.get_all_roles()
    
    if not roles:
        st.warning("No roles found. Please create roles first in the 'Roles' tab.")
        return
    
    # ============================================================
    # ROLE SELECTOR
    # ============================================================
    role_names = [r.get('role_name') for r in roles]
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_role = st.selectbox(
            "Select Role to Manage Permissions",
            options=role_names,
            index=role_names.index(st.session_state.perm_selected_role) if st.session_state.perm_selected_role in role_names else 0,
            key="perm_role_select"
        )
        st.session_state.perm_selected_role = selected_role
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("📋 Templates", use_container_width=True):
            st.session_state.show_templates = not st.session_state.get('show_templates', False)
            st.rerun()
    
    if not selected_role:
        st.info("Please select a role to manage")
        return
    
    # ============================================================
    # GET ROLE DATA
    # ============================================================
    role = db.get_role_by_name(selected_role)
    if not role:
        st.error(f"Role '{selected_role}' not found")
        return
    
    permissions = role.get('permissions', {})
    description = permissions.get('description', '')
    
    # ============================================================
    # TEMPLATES (Expandable)
    # ============================================================
    if st.session_state.get('show_templates', False):
        with st.expander("📋 Apply Permission Template", expanded=True):
            st.caption("Apply a pre-defined permission template to this role")
            
            template_name = st.selectbox(
                "Select Template",
                options=list(PERMISSION_TEMPLATES.keys()),
                key="perm_template_select"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Apply Template", type="primary", use_container_width=True):
                    template = PERMISSION_TEMPLATES[template_name]
                    
                    # Merge with existing permissions (preserve description if not in template)
                    if 'description' not in template and description:
                        template['description'] = description
                    
                    if db.update_role_permissions(selected_role, template):
                        st.success(f"✅ Applied '{template_name}' template to '{selected_role}'")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Failed to apply template")
            
            with col2:
                if st.button("❌ Close Templates", use_container_width=True):
                    st.session_state.show_templates = False
                    st.rerun()
    
    # ============================================================
    # PERMISSIONS LIST
    # ============================================================
    st.markdown(f"### 📋 Permissions for: `{selected_role}`")
    
    if description:
        st.info(f"📝 Description: {description}")
    
    # ============================================================
    # TOGGLE PERMISSIONS (Checkboxes)
    # ============================================================
    st.markdown("#### ✏️ Toggle Permissions")
    st.caption("Enable or disable permissions for this role")
    
    # Define all possible permission keys
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
    
    # Group permissions by category
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
    
    # Create updated permissions dict
    updated_perms = {}
    
    # Track which permissions exist for this role
    existing_keys = set(permissions.keys())
    
    # Display permissions by category
    for category, perm_keys in PERMISSION_CATEGORIES.items():
        st.markdown(f"**{category}**")
        cols = st.columns(3)
        
        for i, key in enumerate(perm_keys):
            # Check if this permission exists in the role's permissions
            current_value = permissions.get(key, False)
            
            with cols[i % 3]:
                new_value = st.checkbox(
                    key.replace('_', ' ').title(),
                    value=current_value,
                    key=f"perm_{selected_role}_{key}",
                    help=f"Permission: {key}"
                )
                updated_perms[key] = new_value
    
    # Add description field
    st.markdown("---")
    st.markdown("#### 📝 Description")
    new_description = st.text_input(
        "Role Description",
        value=description,
        key=f"perm_desc_{selected_role}",
        placeholder="Brief description of this role's purpose"
    )
    
    # ============================================================
    # SAVE BUTTONS
    # ============================================================
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Permissions", type="primary", use_container_width=True):
            # Add description to permissions
            if new_description:
                updated_perms['description'] = new_description
            elif 'description' in updated_perms:
                del updated_perms['description']
            
            if db.update_role_permissions(selected_role, updated_perms):
                st.success(f"✅ Permissions for '{selected_role}' updated successfully!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to update permissions")
    
    with col2:
        if st.button("🔄 Reset to Current", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("❌ Clear All Permissions", use_container_width=True):
            st.warning(f"⚠️ This will clear ALL permissions for '{selected_role}'")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ Confirm Clear", key="confirm_clear_perms"):
                    empty_perms = {}
                    if new_description:
                        empty_perms['description'] = new_description
                    if db.update_role_permissions(selected_role, empty_perms):
                        st.success(f"✅ All permissions cleared for '{selected_role}'")
                        st.rerun()
                    else:
                        st.error("❌ Failed to clear permissions")
            with col_cancel:
                if st.button("❌ Cancel", key="cancel_clear_perms"):
                    st.rerun()
    
    # ============================================================
    # PERMISSION SUMMARY TABLE
    # ============================================================
    with st.expander("📊 Permission Summary", expanded=False):
        perm_data = []
        for key in ALL_PERMISSIONS:
            value = permissions.get(key, False)
            perm_data.append({
                'Permission': key.replace('_', ' ').title(),
                'Key': key,
                'Status': '✅ Enabled' if value else '❌ Disabled'
            })
        
        if perm_data:
            df = pd.DataFrame(perm_data)
            st.dataframe(df, use_container_width=True, hide_index=True)


# Export for admin dashboard
__all__ = ['render_permission_management']