# modules/subscription_ui.py

import streamlit as st
from datetime import datetime
from typing import Dict, Optional

from database.unified_db_manager import db
from modules.subscription_plans import get_plans, get_plan, is_premium_plan, refresh_plans_cache


def render_subscription_card(
    subscription: Dict,
    company_id: int,
    show_update: bool = True,
    show_cancel: bool = True,
    title: str = "💳 Subscription Management"
):
    """Render a complete subscription management card"""
    
    # Debug: Verify company exists
    company = db.get_company_by_id(company_id)
    if company:
        print(f"🏢 render_subscription_card for: {company.get('company_name')} (ID: {company_id})")
        print(f"📊 Subscription plan: {subscription.get('subscription_tier', 'unknown')}")
    else:
        print(f"⚠️ Company with ID {company_id} not found!")
    
    st.markdown(f"#### {title}")
    
    # Display current subscription
    _render_subscription_metrics(subscription)
    
    st.markdown("---")
    
    # Update subscription section
    if show_update:
        _render_update_subscription_section(subscription, company_id)
    
    # Cancel subscription section
    if show_cancel and subscription.get('plan') != 'free':
        st.markdown("---")
        _render_cancel_subscription_section(company_id)
    
    # Subscription details
    st.markdown("---")
    _render_subscription_details(subscription)


def _render_subscription_metrics(subscription: Dict):
    """Render subscription metrics cards"""
    
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    status = subscription.get('status', 'active')
    
    plan_config = get_plan(plan)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Plan", plan.upper())
    
    with col2:
        st.metric("Status", status.upper())
    
    with col3:
        limit = subscription.get('max_projects') or subscription.get('analyses_limit', 5)
        used = subscription.get('analyses_used', 0)
        
        if limit == -1:
            st.metric("Analyses", "Unlimited")
        else:
            remaining = max(0, limit - used)
            st.metric("Analyses Remaining", f"{remaining}/{limit}")

def _render_update_subscription_section(subscription: Dict, company_id: int):
    """Render update subscription section with safety checks"""
    
    st.markdown("#### Update Subscription")
    
    # Safety check: Verify this company exists
    company = db.get_company_by_id(company_id)
    if not company:
        st.error(f"❌ Company with ID {company_id} not found!")
        print(f"❌ ERROR: Company {company_id} not found in _render_update_subscription_section")
        return
    
    current_plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    plans = get_plans()
    plan_options = list(plans.keys())
    
    # Debug: Show which company is being edited
    print("=" * 60)
    print("🔧 SUBSCRIPTION UPDATE UI")
    print("=" * 60)
    print(f"   Company Name: {company.get('company_name', 'Unknown')}")
    print(f"   Company ID: {company_id}")
    print(f"   Current Plan: {current_plan}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_plan = st.selectbox(
            "Select Plan",
            options=plan_options,
            index=plan_options.index(current_plan) if current_plan in plan_options else 0,
            key=f"plan_select_{company_id}"
        )
        print(f"   Selected Plan: {new_plan}")
    
    with col2:
        duration = st.selectbox(
            "Duration",
            options=["monthly", "yearly"],
            key=f"duration_select_{company_id}"
        )
        print(f"   Duration: {duration}")
    
    # Plan benefits
    plan_config = get_plan(new_plan)
    features = plan_config.get('features', ['Basic features'])
    st.info("\n".join([f"• {f}" for f in features[:5]]))
    
    # ✅ Single button for update - no confirmation button needed
    if st.button(f"💾 Update Subscription", key=f"update_sub_{company_id}", type="primary", use_container_width=True):
        print("\n" + "=" * 80)
        print("🔄 UPDATE SUBSCRIPTION BUTTON CLICKED")
        print("=" * 80)
        print(f"   🏢 Company: {company.get('company_name', 'Unknown')} (ID: {company_id})")
        print(f"   📋 Current Plan: {current_plan}")
        print(f"   📋 New Plan: {new_plan}")
        print(f"   📅 Duration: {duration}")
        print("=" * 80)
        
        # ✅ Execute update directly - no confirmation needed
        _execute_subscription_update(
            company_id, 
            new_plan, 
            duration, 
            company.get('company_name', 'Unknown'),
            current_plan
        )

def _render_update_subscription_section_bak(subscription: Dict, company_id: int):
    """Render update subscription section with comprehensive debug logs"""
    
    st.markdown("#### Update Subscription")
    
    # Safety check: Verify this company exists
    company = db.get_company_by_id(company_id)
    if not company:
        st.error(f"❌ Company with ID {company_id} not found!")
        print(f"❌ ERROR: Company {company_id} not found in _render_update_subscription_section")
        return
    
    current_plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    plans = get_plans()
    plan_options = list(plans.keys())
    
    # =========================================================================
    # DEBUG: Comprehensive subscription info
    # =========================================================================
    print("=" * 80)
    print("🔧 SUBSCRIPTION UPDATE UI - DETAILED DEBUG")
    print("=" * 80)
    print(f"   📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   🏢 Company Name: {company.get('company_name', 'Unknown')}")
    print(f"   🆔 Company ID: {company_id}")
    print(f"   📋 Current Plan: {current_plan}")
    print(f"   📋 Current Plan Config: {get_plan(current_plan)}")
    print(f"   📋 Available Plans: {plan_options}")
    print(f"   📊 Subscription Data: {subscription}")
    print("=" * 80)
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_plan = st.selectbox(
            "Select Plan",
            options=plan_options,
            index=plan_options.index(current_plan) if current_plan in plan_options else 0,
            key=f"plan_select_{company_id}"
        )
        print(f"   🔄 Selected Plan: {new_plan}")
    
    with col2:
        duration = st.selectbox(
            "Duration",
            options=["monthly", "yearly"],
            key=f"duration_select_{company_id}"
        )
        print(f"   📅 Duration: {duration}")
    
    # Plan benefits
    plan_config = get_plan(new_plan)
    features = plan_config.get('features', ['Basic features'])
    st.info("\n".join([f"• {f}" for f in features[:5]]))
    
    if st.button(f"💾 Update Subscription", key=f"update_sub_{company_id}", type="primary", use_container_width=True):
        print("\n" + "=" * 80)
        print("🔄 UPDATE SUBSCRIPTION BUTTON CLICKED")
        print("=" * 80)
        print(f"   🏢 Company: {company.get('company_name', 'Unknown')} (ID: {company_id})")
        print(f"   📋 Current Plan: {current_plan}")
        print(f"   📋 New Plan: {new_plan}")
        print(f"   📅 Duration: {duration}")
        print("=" * 80)
        
        # Show confirmation with company name
        st.warning(f"⚠️ You are about to update subscription for **{company.get('company_name', 'Unknown')}**")
        st.info(f"**From:** {current_plan.upper()} → **To:** {new_plan.upper()}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Update", key=f"confirm_update_{company_id}", type="primary"):
                # Proceed with update
                _execute_subscription_update(
                    company_id, 
                    new_plan, 
                    duration, 
                    company.get('company_name', 'Unknown'),
                    current_plan
                )
        with col2:
            if st.button("❌ Cancel", key=f"cancel_update_{company_id}"):
                st.rerun()

def _execute_subscription_update(company_id: int, new_plan: str, duration: str, company_name: str, old_plan: str):
    """Execute the subscription update with comprehensive verification and debug"""
    
    print("\n" + "=" * 80)
    print("🔄 EXECUTING SUBSCRIPTION UPDATE")
    print("=" * 80)
    print(f"   🏢 Company: {company_name} (ID: {company_id})")
    print(f"   📋 From Plan: {old_plan}")
    print(f"   📋 To Plan: {new_plan}")
    print(f"   📅 Duration: {duration}")
    print(f"   🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    transaction_id = f'ADMIN_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    print(f"   📝 Transaction ID: {transaction_id}")
    
    try:
        # Step 1: Verify company still exists
        print("\n📌 STEP 1: Verifying company exists...")
        company_check = db.get_company_by_id(company_id)
        if not company_check:
            st.error(f"❌ Company {company_id} not found!")
            print(f"   ❌ ERROR: Company {company_id} not found during update!")
            return
        print(f"   ✅ Company verified: {company_check.get('company_name')}")

        # Step 2: Get current subscription before update
        print("\n📌 STEP 2: Getting current subscription...")
        before_sub = db.get_company_subscription(company_id)
        before_plan = before_sub.get('subscription_tier') or before_sub.get('plan', 'free')
        print(f"   📊 Before Update - Plan: {before_plan}")
        
        # Step 3: Update the subscription
        print("\n📌 STEP 3: Executing database update...")
        print(f"   🔄 Updating: {company_name} from {old_plan} to {new_plan}")
        
        success = db.update_company_subscription(
            company_id, 
            new_plan, 
            duration, 
            'admin_manual',
            transaction_id
        )
        
        print(f"   📊 Update Result: {success}")
        
        # Step 4: Verify the update
        print("\n📌 STEP 4: Verifying update...")
        after_sub = db.get_company_subscription(company_id)
        after_plan = after_sub.get('subscription_tier') or after_sub.get('plan', 'free')
        print(f"   📊 After Update - Plan: {after_plan}")
        
        # Step 5: Compare before and after
        print("\n📌 STEP 5: Comparing results...")
        if before_plan != after_plan:
            print(f"   ✅ SUCCESS: Plan changed from {before_plan} to {after_plan}")
        else:
            print(f"   ⚠️ WARNING: Plan did NOT change! Expected {new_plan}, got {after_plan}")
        
        # Step 6: Clear cache
        print("\n📌 STEP 6: Refreshing plans cache...")
        refresh_plans_cache()
        print("   ✅ Plans cache refreshed")
        
        # Step 7: Show result
        print("\n📌 STEP 7: Update result")
        if success:
            print("   ✅ UPDATE SUCCESSFUL!")
            print(f"   🎯 Company: {company_name}")
            print(f"   📋 Old Plan: {old_plan}")
            print(f"   📋 New Plan: {after_plan}")
            
            st.success(f"✅ Subscription for **{company_name}** updated from **{old_plan.upper()}** to **{after_plan.upper()}**!")
            st.balloons()
            st.rerun()
        else:
            print("   ❌ UPDATE FAILED - Returned False")
            st.error("❌ Failed to update subscription. Please check logs for details.")
            st.info("💡 Tip: You may need to refresh the page and try again.")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION during update:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        st.error(f"Error updating subscription: {str(e)}")
        st.info("💡 Please try again or contact support.")

def _execute_subscription_update_bak(company_id: int, new_plan: str, duration: str, company_name: str, old_plan: str):
    """Execute the subscription update with comprehensive verification and debug"""
    
    print("\n" + "=" * 80)
    print("🔄 EXECUTING SUBSCRIPTION UPDATE")
    print("=" * 80)
    print(f"   🏢 Company: {company_name} (ID: {company_id})")
    print(f"   📋 From Plan: {old_plan}")
    print(f"   📋 To Plan: {new_plan}")
    print(f"   📅 Duration: {duration}")
    print(f"   🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    transaction_id = f'ADMIN_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    print(f"   📝 Transaction ID: {transaction_id}")
    
    try:
        # Step 1: Verify company still exists
        print("\n📌 STEP 1: Verifying company exists...")
        company_check = db.get_company_by_id(company_id)
        if not company_check:
            st.error(f"❌ Company {company_id} not found!")
            print(f"   ❌ ERROR: Company {company_id} not found during update!")
            return
        print(f"   ✅ Company verified: {company_check.get('company_name')}")

        # Step 2: Get current subscription before update
        print("\n📌 STEP 2: Getting current subscription...")
        before_sub = db.get_company_subscription(company_id)
        before_plan = before_sub.get('subscription_tier') or before_sub.get('plan', 'free')
        print(f"   📊 Before Update - Plan: {before_plan}")
        print(f"   📊 Before Update - Data: {before_sub}")
        
        # Step 3: Update the subscription
        print("\n📌 STEP 3: Executing database update...")
        print(f"   🔄 Updating: {company_name} from {old_plan} to {new_plan}")
        
        success = db.update_company_subscription(
            company_id, 
            new_plan, 
            duration, 
            'admin_manual',
            transaction_id
        )
        
        print(f"   📊 Update Result: {success}")
        
        # Step 4: Verify the update
        print("\n📌 STEP 4: Verifying update...")
        after_sub = db.get_company_subscription(company_id)
        after_plan = after_sub.get('subscription_tier') or after_sub.get('plan', 'free')
        print(f"   📊 After Update - Plan: {after_plan}")
        print(f"   📊 After Update - Data: {after_sub}")
        
        # Step 5: Compare before and after
        print("\n📌 STEP 5: Comparing results...")
        if before_plan != after_plan:
            print(f"   ✅ SUCCESS: Plan changed from {before_plan} to {after_plan}")
        else:
            print(f"   ⚠️ WARNING: Plan did NOT change! Expected {new_plan}, got {after_plan}")
        
        # Step 6: Clear cache
        print("\n📌 STEP 6: Refreshing plans cache...")
        refresh_plans_cache()
        print("   ✅ Plans cache refreshed")
        
        # Step 7: Show result
        print("\n📌 STEP 7: Update result")
        if success:
            print("   ✅ UPDATE SUCCESSFUL!")
            print(f"   🎯 Company: {company_name}")
            print(f"   📋 Old Plan: {old_plan}")
            print(f"   📋 New Plan: {after_plan}")
            print(f"   📝 Transaction: {transaction_id}")
            
            st.success(f"✅ Subscription for **{company_name}** updated from **{old_plan.upper()}** to **{after_plan.upper()}**!")
            st.balloons()
            st.rerun()
        else:
            print("   ❌ UPDATE FAILED - Returned False")
            st.error("❌ Failed to update subscription. Please check logs for details.")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION during update:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        st.error(f"Error updating subscription: {str(e)}")


def _render_cancel_subscription_section(company_id: int):
    """Render cancel subscription section with debug logs"""
    
    company = db.get_company_by_id(company_id)
    company_name = company.get('company_name', 'Unknown') if company else 'Unknown'
    
    print("=" * 60)
    print("🔧 CANCEL SUBSCRIPTION UI")
    print("=" * 60)
    print(f"   Company: {company_name} (ID: {company_id})")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col2:
        if st.button(f"❌ Cancel Subscription", key=f"cancel_sub_{company_id}", use_container_width=True):
            print("\n" + "=" * 60)
            print("🔄 CANCEL SUBSCRIPTION BUTTON CLICKED")
            print("=" * 60)
            print(f"   Company: {company_name} (ID: {company_id})")
            
            # Show confirmation
            st.warning(f"⚠️ You are about to cancel subscription for **{company_name}**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Cancel", key=f"confirm_cancel_{company_id}", type="primary"):
                    _execute_subscription_cancel(company_id, company_name)
            with col2:
                if st.button("❌ No, Keep Plan", key=f"keep_plan_{company_id}"):
                    st.rerun()


def _execute_subscription_cancel(company_id: int, company_name: str):
    """Execute subscription cancellation with verification"""
    
    print("\n" + "=" * 60)
    print("🔄 EXECUTING SUBSCRIPTION CANCELLATION")
    print("=" * 60)
    print(f"   Company: {company_name} (ID: {company_id})")
    
    transaction_id = f'CANCEL_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    print(f"   Transaction ID: {transaction_id}")
    
    try:
        # Get current plan before cancellation
        before_sub = db.get_company_subscription(company_id)
        before_plan = before_sub.get('subscription_tier') or before_sub.get('plan', 'free')
        print(f"   📊 Current Plan: {before_plan}")
        
        # Cancel subscription
        success = db.update_company_subscription(
            company_id, 
            'free', 
            'monthly', 
            'admin_cancelled',
            transaction_id
        )
        
        print(f"   Cancel Result: {success}")
        
        if success:
            # Verify the update
            after_sub = db.get_company_subscription(company_id)
            after_plan = after_sub.get('subscription_tier') or after_sub.get('plan', 'free')
            print(f"   📊 After Cancel - Plan: {after_plan}")
            
            refresh_plans_cache()
            print("   ✅ Plans cache refreshed")
            
            st.success(f"✅ Subscription for **{company_name}** cancelled. Plan set to FREE.")
            st.rerun()
        else:
            print("   ❌ Cancel failed - returned False")
            st.error("Failed to cancel subscription")
            
    except Exception as e:
        print(f"   ❌ Exception during cancel: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Error cancelling subscription: {str(e)}")


def _render_subscription_details(subscription: Dict):
    """Render subscription details"""
    
    st.markdown("#### Subscription Details")
    
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    start_date = subscription.get('start_date')
    end_date = subscription.get('end_date')
    payment_method = subscription.get('payment_method')
    transaction_id = subscription.get('transaction_id')
    
    st.caption(f"**Plan:** {plan.upper()}")
    st.caption(f"**Start Date:** {start_date if start_date else 'N/A'}")
    st.caption(f"**End Date:** {end_date if end_date else 'N/A'}")
    if payment_method:
        st.caption(f"**Payment Method:** {payment_method}")
    if transaction_id:
        st.caption(f"**Transaction ID:** {transaction_id}")