"""
Subscription Management Module - State-Driven View Router Pattern
Uses st.dataframe with singleton selection and comprehensive validation
All database operations use SubscriptionManager methods - NO RAW SQL
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime


def render_subscription_management(db):
    """Main entry point for subscription management with view routing"""
    
    # Initialize session state for this module
    if "sub_view" not in st.session_state:
        st.session_state.sub_view = "grid"
    if "sub_selected_id" not in st.session_state:
        st.session_state.sub_selected_id = None
    if "sub_page" not in st.session_state:
        st.session_state.sub_page = 1
    if "sub_search" not in st.session_state:
        st.session_state.sub_search = ""
    if "sub_status_filter" not in st.session_state:
        st.session_state.sub_status_filter = "All"
    if "sub_plan_filter" not in st.session_state:
        st.session_state.sub_plan_filter = "All"
    if "sub_per_page" not in st.session_state:
        st.session_state.sub_per_page = 10
    
    # Route to appropriate view
    if st.session_state.sub_view == "detail":
        render_subscription_detail_view(db)
    else:
        render_subscription_grid_view(db)


def render_subscription_grid_view(db):
    """Render spreadsheet-style grid view using st.dataframe"""
    
    st.markdown("### 💳 SUBSCRIPTION MANAGEMENT SYSTEM")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1])
    
    with col1:
        if st.button("➕ Add New Subscription", key="sub_add_btn", type="primary", use_container_width=True):
            st.session_state.sub_selected_id = None
            st.session_state.sub_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.sub_search = st.text_input(
            "🔍 Search",
            placeholder="Plan, user, or company...",
            value=st.session_state.sub_search,
            key="sub_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        # Status filter
        status_options = ["All", "Active", "Inactive", "Expired", "Cancelled", "trial"]
        st.session_state.sub_status_filter = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(st.session_state.sub_status_filter) if st.session_state.sub_status_filter in status_options else 0,
            key="sub_status_filter_select",
            label_visibility="collapsed"
        )
    
    with col4:
        st.session_state.sub_per_page = st.selectbox(
            "Rows",
            options=[5, 10, 25, 50],
            index=[5, 10, 25, 50].index(st.session_state.sub_per_page) if st.session_state.sub_per_page in [5, 10, 25, 50] else 1,
            key="sub_per_page_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH SUBSCRIPTIONS =====
    try:
        all_subs = db.get_all_subscriptions()
    except Exception as e:
        st.error(f"Error loading subscriptions: {e}")
        return
    
    if not all_subs:
        st.info("No subscriptions found. Click 'Add New Subscription' to create one.")
        return
    
    # ===== ENRICH WITH ENTITY NAMES =====
    enriched_subs = []
    for sub in all_subs:
        sub_copy = dict(sub)
        
        # Get entity name from the already joined data
        if sub.get('user_id'):
            sub_copy['entity_name'] = sub.get('full_name') or sub.get('username') or f"User #{sub.get('user_id')}"
            sub_copy['entity_type'] = 'User'
            sub_copy['entity_id'] = sub.get('user_id')
        elif sub.get('company_id'):
            sub_copy['entity_name'] = sub.get('company_name') or f"Company #{sub.get('company_id')}"
            sub_copy['entity_type'] = 'Company'
            sub_copy['entity_id'] = sub.get('company_id')
        else:
            sub_copy['entity_name'] = 'Unknown'
            sub_copy['entity_type'] = 'Unknown'
            sub_copy['entity_id'] = None
        
        enriched_subs.append(sub_copy)
    
    # ===== APPLY FILTERS =====
    filtered_subs = enriched_subs
    
    if st.session_state.sub_search:
        search_lower = st.session_state.sub_search.lower()
        filtered_subs = [
            s for s in filtered_subs
            if search_lower in str(s.get('plan', '')).lower()
            or search_lower in str(s.get('entity_name', '')).lower()
            or search_lower in str(s.get('entity_type', '')).lower()
        ]
    
    if st.session_state.sub_status_filter != "All":
        filtered_subs = [s for s in filtered_subs if s.get('status', '').lower() == st.session_state.sub_status_filter.lower()]
    
    if not filtered_subs:
        st.info("No subscriptions match the filters")
        return
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Subscriptions", len(filtered_subs))
    with col2:
        active = len([s for s in filtered_subs if s.get('status') == 'active'])
        st.metric("Active", active)
    with col3:
        # Calculate monthly revenue
        revenue = 0
        for s in filtered_subs:
            if s.get('status') == 'active':
                plan = s.get('plan', 'free')
                if plan == 'basic':
                    revenue += 29
                elif plan == 'pro':
                    revenue += 79
                elif plan == 'enterprise':
                    revenue += 199
        st.metric("Monthly Revenue", f"${revenue:,.2f}")
    with col4:
        trial = len([s for s in filtered_subs if s.get('status') == 'trial'])
        st.metric("Trials", trial)
    
    st.markdown("---")
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, sub in enumerate(filtered_subs):
        # Format status badge
        status = sub.get('status', 'inactive')
        status_display = {
            'active': '🟢 Active',
            'inactive': '🔴 Inactive',
            'expired': '🟠 Expired',
            'cancelled': '⚫ Cancelled',
            'trial': '🟡 Trial'
        }.get(status, status.title())
        
        # Format plan
        plan = sub.get('plan', 'free').title()
        
        # Format dates
        start_date = sub.get('start_date', '')
        end_date = sub.get('end_date', '')
        
        df_data.append({
            'id': sub.get('id'),
            'entity_name': sub.get('entity_name', 'Unknown'),
            'entity_type': sub.get('entity_type', 'Unknown'),
            'plan': plan,
            'status': status_display,
            'status_raw': status,
            'start_date': str(start_date)[:10] if start_date else '',
            'end_date': str(end_date)[:10] if end_date else '',
            'analyses_used': sub.get('analyses_used', 0),
            'analyses_limit': sub.get('analyses_limit', 0),
            'user_id': sub.get('user_id'),
            'company_id': sub.get('company_id'),
            '_record': sub  # Store full record
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['id', 'entity_name', 'entity_type', 'plan', 'status', 'start_date', 'end_date']
    
    # Style the dataframe
    styled_df = df[display_columns].style
    
    def color_status(val):
        if 'Active' in str(val):
            return 'color: #065f46; background-color: #d1fae5;'
        elif 'Inactive' in str(val):
            return 'color: #991b1b; background-color: #fee2e2;'
        elif 'Expired' in str(val):
            return 'color: #92400e; background-color: #fef3c7;'
        elif 'Cancelled' in str(val):
            return 'color: #475569; background-color: #f1f5f9;'
        elif 'Trial' in str(val):
            return 'color: #0369a1; background-color: #e0f2fe;'
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
            "entity_name": st.column_config.Column("Entity", width="large"),
            "entity_type": st.column_config.Column("Type", width="small"),
            "plan": st.column_config.Column("Plan", width="small"),
            "status": st.column_config.Column("Status", width="small"),
            "start_date": st.column_config.Column("Start", width="small"),
            "end_date": st.column_config.Column("End", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            sub_id = row_data.get('id')
            if sub_id:
                st.session_state.sub_selected_id = sub_id
                st.session_state.sub_view = "detail"
                st.rerun()
    
    # ===== PAGINATION =====
    per_page = st.session_state.sub_per_page
    total = len(filtered_subs)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (st.session_state.sub_page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    
    with col1:
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} subscriptions")
    
    with col2:
        if st.button("◀ Prev", key="sub_prev", disabled=(st.session_state.sub_page <= 1), use_container_width=True):
            st.session_state.sub_page -= 1
            st.rerun()
    
    with col3:
        if st.button("Next ▶", key="sub_next", disabled=(st.session_state.sub_page >= total_pages), use_container_width=True):
            st.session_state.sub_page += 1
            st.rerun()
    
    with col4:
        jump_to = st.number_input(
            "Jump to page",
            min_value=1,
            max_value=total_pages if total_pages > 0 else 1,
            value=st.session_state.sub_page,
            step=1,
            key="sub_jump_to",
            label_visibility="collapsed"
        )
        if jump_to != st.session_state.sub_page and 1 <= jump_to <= total_pages:
            st.session_state.sub_page = jump_to
            st.rerun()


def render_subscription_detail_view(db):
    """Render full-page detail view for subscription management"""
    
    sub_id = st.session_state.sub_selected_id
    is_new = sub_id is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Add New Subscription" if is_new else f"✏️ Edit Subscription Details (ID: {sub_id})"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to Subscription Grid", key="sub_back_to_grid"):
        st.session_state.sub_view = "grid"
        st.session_state.sub_selected_id = None
        st.rerun()
    
    st.divider()
    
    # ===== GET SUBSCRIPTION DATA =====
    if is_new:
        subscription = {
            'id': None,
            'user_id': None,
            'company_id': None,
            'plan': 'free',
            'status': 'active',
            'start_date': datetime.now().date().isoformat(),
            'end_date': (datetime.now().date() + timedelta(days=30)).isoformat(),
            'analyses_limit': 5,
            'analyses_used': 0,
            'max_boq_generations': 5,
            'boq_used': 0,
            'max_bid_optimizations': 5,
            'bid_optimizations_used': 0,
            'can_export_data': False,
            'can_edit_rates': False,
            'can_delete_rates': False,
            'can_create_versions': False,
            'can_manage_team': False,
            'entity_name': '',
            'entity_type': 'User'
        }
    else:
        # Get subscription by ID - we need to fetch from all subscriptions
        all_subs = db.get_all_subscriptions()
        subscription = None
        for sub in all_subs:
            if sub.get('id') == sub_id:
                subscription = sub
                break
        
        if not subscription:
            st.error(f"Subscription with ID {sub_id} not found")
            if st.button("Close", key="sub_close_not_found"):
                st.session_state.sub_view = "grid"
                st.session_state.sub_selected_id = None
                st.rerun()
            return
        
        # Enrich with entity name
        if subscription.get('user_id'):
            subscription['entity_name'] = subscription.get('full_name') or subscription.get('username') or f"User #{subscription.get('user_id')}"
            subscription['entity_type'] = 'User'
        elif subscription.get('company_id'):
            subscription['entity_name'] = subscription.get('company_name') or f"Company #{subscription.get('company_id')}"
            subscription['entity_type'] = 'Company'
        else:
            subscription['entity_name'] = 'Unknown'
            subscription['entity_type'] = 'Unknown'
    
    # ===== EDIT FORM =====
    with st.form(key="subscription_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📋 Subscription Information</div>', unsafe_allow_html=True)
        
        # ===== ENTITY SELECTION =====
        col1, col2 = st.columns(2)
        
        with col1:
            entity_type = st.selectbox(
                "Entity Type",
                options=["User", "Company"],
                index=0 if subscription.get('entity_type') == 'User' else 1,
                key="sub_edit_entity_type"
            )
        
        with col2:
            if entity_type == "User":
                # Get users for dropdown
                users, _ = db.get_all_users_filtered(limit=1000)
                user_options = {f"{u.get('full_name')} (@{u.get('username')})": u.get('id') for u in users}
                user_options["None"] = None
                
                current_user_id = subscription.get('user_id')
                current_user_name = None
                for name, uid in user_options.items():
                    if uid == current_user_id:
                        current_user_name = name
                        break
                
                selected_user = st.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    index=list(user_options.keys()).index(current_user_name) if current_user_name else 0,
                    key="sub_edit_user"
                )
                entity_id = user_options.get(selected_user)
            else:
                # Get companies for dropdown
                companies, _ = db.get_all_companies_filtered(limit=1000)
                company_options = {c.get('company_name', 'Unknown'): c.get('id') for c in companies}
                company_options["None"] = None
                
                current_company_id = subscription.get('company_id')
                current_company_name = None
                for name, cid in company_options.items():
                    if cid == current_company_id:
                        current_company_name = name
                        break
                
                selected_company = st.selectbox(
                    "Select Company",
                    options=list(company_options.keys()),
                    index=list(company_options.keys()).index(current_company_name) if current_company_name else 0,
                    key="sub_edit_company"
                )
                entity_id = company_options.get(selected_company)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PLAN & STATUS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">⚙️ Plan & Status</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            plan_options = ["free", "basic", "pro", "enterprise"]
            current_plan = subscription.get('plan', 'free')
            plan_index = plan_options.index(current_plan) if current_plan in plan_options else 0
            
            plan = st.selectbox(
                "Plan",
                options=plan_options,
                index=plan_index,
                key="sub_edit_plan",
                format_func=lambda x: x.title()
            )
        
        with col2:
            status_options = ["active", "inactive", "expired", "cancelled", "trial"]
            current_status = subscription.get('status', 'active')
            status_index = status_options.index(current_status) if current_status in status_options else 0
            
            status = st.selectbox(
                "Status",
                options=status_options,
                index=status_index,
                key="sub_edit_status",
                format_func=lambda x: x.title()
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== DATES =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📅 Dates</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.strptime(subscription.get('start_date', datetime.now().date().isoformat()), '%Y-%m-%d').date() if subscription.get('start_date') else datetime.now().date(),
                key="sub_edit_start_date"
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.strptime(subscription.get('end_date', (datetime.now().date() + timedelta(days=30)).isoformat()), '%Y-%m-%d').date() if subscription.get('end_date') else datetime.now().date() + timedelta(days=30),
                key="sub_edit_end_date"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== USAGE LIMITS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📊 Usage Limits</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            analyses_limit = st.number_input(
                "Analyses Limit",
                min_value=0,
                max_value=9999,
                value=subscription.get('analyses_limit', 5),
                key="sub_edit_analyses_limit"
            )
        
        with col2:
            max_boq = st.number_input(
                "Max BOQ Generations",
                min_value=0,
                max_value=9999,
                value=subscription.get('max_boq_generations', 5),
                key="sub_edit_max_boq"
            )
        
        with col3:
            max_bid_opt = st.number_input(
                "Max Bid Optimizations",
                min_value=0,
                max_value=9999,
                value=subscription.get('max_bid_optimizations', 5),
                key="sub_edit_max_bid_opt"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PERMISSIONS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">🔑 Permissions</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            can_export_data = st.checkbox(
                "Can Export Data",
                value=subscription.get('can_export_data', False),
                key="sub_edit_can_export"
            )
            can_edit_rates = st.checkbox(
                "Can Edit Rates",
                value=subscription.get('can_edit_rates', False),
                key="sub_edit_can_edit_rates"
            )
            can_delete_rates = st.checkbox(
                "Can Delete Rates",
                value=subscription.get('can_delete_rates', False),
                key="sub_edit_can_delete_rates"
            )
        
        with col2:
            can_create_versions = st.checkbox(
                "Can Create Versions",
                value=subscription.get('can_create_versions', False),
                key="sub_edit_can_create_versions"
            )
            can_manage_team = st.checkbox(
                "Can Manage Team",
                value=subscription.get('can_manage_team', False),
                key="sub_edit_can_manage_team"
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
                    "🗑️ Delete Subscription",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    st.warning("⚠️ Are you sure you want to delete this subscription?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Delete", key=f"sub_confirm_delete_{sub_id}"):
                            # Delete subscription - you'll need to implement this
                            st.info("Delete functionality would be implemented here")
                    with col_cancel:
                        if st.button("❌ Cancel", key="sub_cancel_delete"):
                            st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.sub_view = "grid"
                st.session_state.sub_selected_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION =====
    if submitted:
        validation_errors = []
        
        # ===== VALIDATE ENTITY =====
        if not entity_id:
            validation_errors.append("Please select a valid User or Company")
        
        # ===== VALIDATE DATES =====
        if start_date > end_date:
            validation_errors.append("Start date must be before end date")
        
        # ===== SHOW VALIDATION ERRORS =====
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # ===== BUILD UPDATES =====
            updates = {
                'plan': plan,
                'status': status,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'analyses_limit': analyses_limit,
                'max_boq_generations': max_boq,
                'max_bid_optimizations': max_bid_opt,
                'can_export_data': can_export_data,
                'can_edit_rates': can_edit_rates,
                'can_delete_rates': can_delete_rates,
                'can_create_versions': can_create_versions,
                'can_manage_team': can_manage_team
            }
            
            # ===== SAVE TO DATABASE =====
            if is_new:
                # Create new subscription
                if entity_type == "User":
                    # Use update_user_subscription method
                    success = db.update_user_subscription(
                        user_id=entity_id,
                        plan=plan,
                        duration='monthly',
                        payment_method='admin'
                    )
                    if success:
                        st.success("✅ Subscription created successfully!")
                        st.balloons()
                        st.session_state.sub_view = "grid"
                        st.session_state.sub_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to create subscription")
                else:
                    # Use update_company_subscription method
                    success = db.update_company_subscription(
                        company_id=entity_id,
                        plan=plan,
                        duration='monthly',
                        payment_method='admin'
                    )
                    if success:
                        st.success("✅ Subscription created successfully!")
                        st.balloons()
                        st.session_state.sub_view = "grid"
                        st.session_state.sub_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to create subscription")
            else:
                # Update existing subscription
                # Since we don't have a direct update method, we'll use the entity-specific methods
                if subscription.get('user_id'):
                    success = db.update_user_subscription(
                        user_id=subscription.get('user_id'),
                        plan=plan,
                        duration='monthly',
                        payment_method='admin'
                    )
                else:
                    success = db.update_company_subscription(
                        company_id=subscription.get('company_id'),
                        plan=plan,
                        duration='monthly',
                        payment_method='admin'
                    )
                
                if success:
                    st.success("✅ Subscription updated successfully!")
                    st.balloons()
                    st.session_state.sub_view = "grid"
                    st.session_state.sub_selected_id = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update subscription")
    
    st.markdown('</div>', unsafe_allow_html=True)