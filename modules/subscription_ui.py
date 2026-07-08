# modules/subscription_ui.py - Refactored (Fixed)

import streamlit as st
from datetime import datetime
from typing import Dict, Optional

from database.unified_db_manager import get_db_manager
from modules.subscription_plans import get_plans, get_plan, is_premium_plan, refresh_plans_cache

db = get_db_manager()


def render_subscription_card(
    subscription: Dict,
    company_id: int,
    show_update: bool = True,
    show_cancel: bool = True,
    title: str = "💳 Subscription Management"
):
    """Render a complete subscription management card"""
    
    # ✅ Get company details
    company = db.get_company_by_id(company_id)
    company_name = company.get('company_name', 'Unknown') if company else 'Unknown'
    
    # ✅ Extract plan correctly
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    
    # ✅ DEBUG: Log the subscription data
    print("=" * 60)
    print(f"🔍 render_subscription_card - {company_name}")
    print("=" * 60)
    print(f"   Company ID: {company_id}")
    print(f"   Company Name: {company_name}")
    print(f"   Extracted Plan: {plan}")
    print(f"   Full Subscription: {subscription}")
    print("=" * 60)
    
    st.markdown(f"#### {title}")
    
    # ✅ Display current subscription with correct plan
    _render_subscription_metrics(subscription, company)
    
    st.markdown("---")
    
    # Update subscription section
    if show_update:
        _render_update_subscription_section(subscription, company_id)
    
    # Cancel subscription section
    if show_cancel and plan not in ['free', 'FREE']:
        st.markdown("---")
        _render_cancel_subscription_section(company_id)
    
    # Subscription details
    st.markdown("---")
    _render_subscription_details(subscription, company_id)  # ✅ Pass company_id for unique keys


def _render_subscription_metrics(subscription: Dict, company: Dict = None):
    """Render subscription metrics cards"""
    
    # ✅ Get plan correctly
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    status = subscription.get('status', 'active')
    
    plan_config = get_plan(plan)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # ✅ Show company name if available
        if company:
            st.metric("Company", company.get('company_name', 'Unknown'))
        st.metric("Current Plan", plan.upper())
    
    with col2:
        st.metric("Status", status.upper())
    
    with col3:
        # ✅ Get limits correctly
        limit = subscription.get('max_projects') or subscription.get('analyses_limit', 5)
        used = subscription.get('analyses_used', 0)
        
        if limit == -1 or limit == 999999:
            st.metric("Analyses", "♾️ Unlimited")
        else:
            remaining = max(0, limit - used)
            st.metric("Analyses Remaining", f"{remaining}/{limit}")


def _render_update_subscription_section(subscription: Dict, company_id: int):
    """Render update subscription section"""
    
    company = db.get_company_by_id(company_id)
    if not company:
        st.error(f"❌ Company with ID {company_id} not found!")
        return
    
    # ✅ Get current plan correctly
    current_plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    company_name = company.get('company_name', 'Unknown')
    
    plans = get_plans()
    plan_options = list(plans.keys())
    
    print("=" * 60)
    print(f"🔧 SUBSCRIPTION UPDATE UI - {company_name}")
    print("=" * 60)
    print(f"   Company: {company_name} (ID: {company_id})")
    print(f"   Current Plan: {current_plan}")
    print(f"   Available Plans: {plan_options}")
    print("=" * 60)
    
    st.markdown("#### Update Subscription")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # ✅ Show current plan as default
        current_index = plan_options.index(current_plan) if current_plan in plan_options else 0
        new_plan = st.selectbox(
            "Select Plan",
            options=plan_options,
            index=current_index,
            key=f"plan_select_{company_id}"
        )
    
    with col2:
        duration = st.selectbox(
            "Duration",
            options=["monthly", "yearly"],
            key=f"duration_select_{company_id}"
        )
    
    # ✅ Show plan benefits
    plan_config = get_plan(new_plan)
    features = plan_config.get('features', ['Basic features'])
    st.info("\n".join([f"• {f}" for f in features[:5]]))
    
    # ✅ Update button
    if st.button(f"💾 Update Subscription", key=f"update_sub_{company_id}", type="primary", use_container_width=True):
        print("\n" + "=" * 80)
        print(f"🔄 UPDATE SUBSCRIPTION BUTTON CLICKED - {company_name}")
        print("=" * 80)
        print(f"   Company: {company_name} (ID: {company_id})")
        print(f"   Current Plan: {current_plan}")
        print(f"   New Plan: {new_plan}")
        print(f"   Duration: {duration}")
        print("=" * 80)
        
        _execute_subscription_update(
            company_id, 
            new_plan, 
            duration, 
            company_name,
            current_plan
        )


def _execute_subscription_update(company_id: int, new_plan: str, duration: str, company_name: str, old_plan: str):
    """Execute subscription update"""
    
    transaction_id = f'ADMIN_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    
    try:
        # ✅ Verify company exists
        company_check = db.get_company_by_id(company_id)
        if not company_check:
            st.error(f"❌ Company {company_id} not found!")
            return
        
        # ✅ Update subscription
        success = db.update_company_subscription(
            company_id, 
            new_plan, 
            duration, 
            'admin_manual',
            transaction_id
        )
        
        if success:
            # ✅ Verify the update
            after_sub = db.get_company_subscription(company_id)
            after_plan = after_sub.get('subscription_tier') or after_sub.get('plan', 'free')
            
            print(f"   ✅ UPDATE SUCCESSFUL!")
            print(f"   📋 Old Plan: {old_plan}")
            print(f"   📋 New Plan: {after_plan}")
            
            refresh_plans_cache()
            
            st.success(f"✅ Subscription for **{company_name}** updated from **{old_plan.upper()}** to **{after_plan.upper()}**!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Failed to update subscription. Please check logs.")
            
    except Exception as e:
        print(f"❌ Exception during update: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Error updating subscription: {str(e)}")


def _render_cancel_subscription_section(company_id: int):
    """Render cancel subscription section"""
    
    company = db.get_company_by_id(company_id)
    company_name = company.get('company_name', 'Unknown') if company else 'Unknown'
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col2:
        if st.button(f"❌ Cancel Subscription", key=f"cancel_sub_{company_id}", use_container_width=True):
            st.warning(f"⚠️ You are about to cancel subscription for **{company_name}**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Cancel", key=f"confirm_cancel_{company_id}", type="primary"):
                    _execute_subscription_cancel(company_id, company_name)
            with col2:
                if st.button("❌ No, Keep Plan", key=f"keep_plan_{company_id}"):
                    st.rerun()


def _execute_subscription_cancel(company_id: int, company_name: str):
    """Execute subscription cancellation"""
    
    transaction_id = f'CANCEL_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    
    try:
        # ✅ Get current plan before cancellation
        before_sub = db.get_company_subscription(company_id)
        before_plan = before_sub.get('subscription_tier') or before_sub.get('plan', 'free')
        print(f"   📊 Current Plan: {before_plan}")
        
        # ✅ Cancel subscription
        success = db.update_company_subscription(
            company_id, 
            'free', 
            'monthly', 
            'admin_cancelled',
            transaction_id
        )
        
        if success:
            refresh_plans_cache()
            st.success(f"✅ Subscription for **{company_name}** cancelled. Plan set to FREE.")
            st.rerun()
        else:
            st.error("Failed to cancel subscription")
            
    except Exception as e:
        print(f"❌ Exception during cancel: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Error cancelling subscription: {str(e)}")


def _render_subscription_details(subscription: Dict, company_id: int):
    """Render subscription details with unique keys"""
    
    # ✅ Get plan correctly
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    start_date = subscription.get('start_date')
    end_date = subscription.get('end_date')
    payment_method = subscription.get('payment_method')
    transaction_id = subscription.get('transaction_id')
    
    st.markdown("#### Subscription Details")
    st.caption(f"**Plan:** {plan.upper()}")
    st.caption(f"**Start Date:** {start_date if start_date else 'N/A'}")
    st.caption(f"**End Date:** {end_date if end_date else 'N/A'}")
    
    if payment_method:
        st.caption(f"**Payment Method:** {payment_method}")
    if transaction_id:
        st.caption(f"**Transaction ID:** {transaction_id}")
    
    # ✅ Add Debug section (with unique key per company)
    if st.checkbox("🔧 Show Debug Info", key=f"debug_subscription_{company_id}"):
        st.json({
            "plan": plan,
            "subscription_tier": subscription.get('subscription_tier'),
            "plan_field": subscription.get('plan'),
            "analyses_limit": subscription.get('analyses_limit'),
            "max_boq_generations": subscription.get('max_boq_generations'),
            "max_bid_optimizations": subscription.get('max_bid_optimizations'),
            "can_export_data": subscription.get('can_export_data'),
            "can_manage_team": subscription.get('can_manage_team'),
            "start_date": start_date,
            "end_date": end_date,
            "full_data": subscription
        })