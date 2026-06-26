# modules/subscription.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription_ui import render_subscription_card

db = UnifiedDatabaseManager()

# =============================================================================
# PLAN CACHE
# =============================================================================

_plans_cache = None
_plans_cache_time = None


def get_plans_from_db(force_refresh: bool = False) -> Dict[str, Dict]:
    """
    Load plans from subscription_plans table
    
    Args:
        force_refresh: Force refresh from database
    
    Returns:
        Dict of plan configurations
    """
    global _plans_cache, _plans_cache_time
    
    # Return cached plans if not expired (5 minutes)
    if not force_refresh and _plans_cache is not None:
        
        if _plans_cache_time and datetime.now() - _plans_cache_time < timedelta(minutes=5):
            return _plans_cache
    
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT 
                    plan_name,
                    monthly_price,
                    yearly_price,
                    max_boq_generations,
                    max_bid_optimizations,
                    max_tender_analyses,
                    max_users,
                    extension_auto_fills,
                    can_export_data,
                    can_edit_rates,
                    can_delete_rates,
                    can_create_versions,
                    can_manage_team,
                    description,
                    is_active
                FROM subscription_plans
                WHERE is_active = 1
                ORDER BY monthly_price
            """)
            
            rows = cursor.fetchall()
            
            plans = {}
            for row in rows:
                plan_name = row['plan_name']
                plans[plan_name] = {
                    'name': plan_name.title(),
                    'price_monthly': row['monthly_price'] or 0,
                    'price_yearly': row['yearly_price'] or 0,
                    'analyses_limit': row['max_tender_analyses'] or 5,
                    'max_boq_generations': row['max_boq_generations'] or 5,
                    'max_bid_optimizations': row['max_bid_optimizations'] or 5,
                    'extension_auto_fills': row['extension_auto_fills'] or 5,
                    'users_limit': row['max_users'] or 1,
                    'can_export_data': bool(row['can_export_data']),
                    'can_edit_rates': bool(row['can_edit_rates']),
                    'can_delete_rates': bool(row['can_delete_rates']),
                    'can_create_versions': bool(row['can_create_versions']),
                    'can_manage_team': bool(row['can_manage_team']),
                    'description': row['description'] or '',
                    'is_active': bool(row['is_active']),
                    'color': _get_plan_color(plan_name),
                    'badge': _get_plan_badge(plan_name),
                    'features': _get_plan_features(plan_name)
                }
            
            _plans_cache = plans
            _plans_cache_time = datetime.now()
            
            print(f"📊 Loaded {len(plans)} plans from database")
            return plans
            
    except Exception as e:
        print(f"⚠️ subscription.py > Error loading plans from database: {e}")
        # Fallback to default plans
        return get_default_plans()


def get_default_plans() -> Dict[str, Dict]:
    """Fallback default plans if database table doesn't exist"""
    return {
        'free': {
            'name': 'Free',
            'price_monthly': 0,
            'price_yearly': 0,
            'analyses_limit': 5,
            'max_boq_generations': 5,
            'max_bid_optimizations': 5,
            'extension_auto_fills': 5,
            'users_limit': 1,
            'can_export_data': False,
            'can_edit_rates': False,
            'can_delete_rates': False,
            'can_create_versions': False,
            'can_manage_team': False,
            'description': 'Free plan with basic features',
            'is_active': True,
            'color': '#6c757d',
            'badge': '🆓',
            'features': [
                '5 analyses/month',
                'Basic Bid Optimizer',
                'Rate Viewer',
                'Basic reports',
                'Email support',
                '7-day history'
            ]
        },
        'basic': {
            'name': 'Basic',
            'price_monthly': 4999,
            'price_yearly': 49990,
            'analyses_limit': 30,
            'max_boq_generations': 30,
            'max_bid_optimizations': 30,
            'extension_auto_fills': 30,
            'users_limit': 3,
            'can_export_data': True,
            'can_edit_rates': False,
            'can_delete_rates': False,
            'can_create_versions': False,
            'can_manage_team': False,
            'description': 'Basic plan for small businesses',
            'is_active': True,
            'color': '#3b82f6',
            'badge': '📊',
            'features': [
                '30 analyses/month',
                'Basic Bid Optimizer',
                'Advanced Bid Optimizer',
                'AI predictions',
                'Export reports',
                '30-day history',
                'Email support'
            ]
        },
        'professional': {
            'name': 'Professional',
            'price_monthly': 14999,
            'price_yearly': 149990,
            'analyses_limit': -1,
            'max_boq_generations': 100,
            'max_bid_optimizations': 100,
            'extension_auto_fills': 100,
            'users_limit': 10,
            'can_export_data': True,
            'can_edit_rates': True,
            'can_delete_rates': False,
            'can_create_versions': True,
            'can_manage_team': True,
            'description': 'Professional plan for growing businesses',
            'is_active': True,
            'color': '#8b5cf6',
            'badge': '⭐',
            'features': [
                'Unlimited analyses',
                'Competitive Bid Simulator',
                'ML predictions',
                'Competitor tracking',
                'Team collaboration',
                'Priority support',
                'API access'
            ]
        },
        'enterprise': {
            'name': 'Enterprise',
            'price_monthly': 49999,
            'price_yearly': 499990,
            'analyses_limit': -1,
            'max_boq_generations': -1,
            'max_bid_optimizations': -1,
            'extension_auto_fills': -1,
            'users_limit': -1,
            'can_export_data': True,
            'can_edit_rates': True,
            'can_delete_rates': True,
            'can_create_versions': True,
            'can_manage_team': True,
            'description': 'Enterprise plan for large organizations',
            'is_active': True,
            'color': '#10b981',
            'badge': '👑',
            'features': [
                'Everything in Professional',
                'Custom AI model',
                'Dedicated support',
                'SLA guarantee',
                'On-premise option'
            ]
        }
    }


def _get_plan_color(plan_name: str) -> str:
    """Get color for plan"""
    colors = {
        'free': '#6c757d',
        'basic': '#3b82f6',
        'professional': '#8b5cf6',
        'enterprise': '#10b981'
    }
    return colors.get(plan_name, '#6c757d')


def _get_plan_badge(plan_name: str) -> str:
    """Get badge emoji for plan"""
    badges = {
        'free': '🆓',
        'basic': '📊',
        'professional': '⭐',
        'enterprise': '👑'
    }
    return badges.get(plan_name, '📋')


def _get_plan_features(plan_name: str) -> List[str]:
    """Get features for plan"""
    features = {
        'free': [
            '5 analyses/month',
            'Basic Bid Optimizer',
            'Rate Viewer',
            'Basic reports',
            'Email support',
            '7-day history'
        ],
        'basic': [
            '30 analyses/month',
            'Basic Bid Optimizer',
            'Advanced Bid Optimizer',
            'AI predictions',
            'Export reports',
            '30-day history',
            'Email support'
        ],
        'professional': [
            'Unlimited analyses',
            'Competitive Bid Simulator',
            'ML predictions',
            'Competitor tracking',
            'Team collaboration',
            'Priority support',
            'API access'
        ],
        'enterprise': [
            'Everything in Professional',
            'Custom AI model',
            'Dedicated support',
            'SLA guarantee',
            'On-premise option'
        ]
    }
    return features.get(plan_name, ['Basic features'])


def get_plans(force_refresh: bool = False) -> Dict[str, Dict]:
    """Get all plans (with caching)"""
    return get_plans_from_db(force_refresh)


def get_plan(plan_name: str) -> Dict:
    """Get a single plan by name"""
    plans = get_plans()
    return plans.get(plan_name, plans.get('free', {}))


def is_premium_plan(plan_name: str) -> bool:
    """Check if a plan is premium (Professional or Enterprise)"""
    return plan_name in ['professional', 'enterprise']


def get_plan_price(plan_name: str, yearly: bool = False) -> float:
    """Get plan price"""
    plan = get_plan(plan_name)
    return plan.get('price_yearly' if yearly else 'price_monthly', 0)


def get_plan_limit(plan_name: str, limit_type: str) -> int:
    """
    Get a specific limit for a plan
    
    Args:
        plan_name: Plan name
        limit_type: 'analyses', 'boq', 'bid', 'users', 'extension'
    
    Returns:
        Limit value (-1 for unlimited)
    """
    plan = get_plan(plan_name)
    
    limit_map = {
        'analyses': 'analyses_limit',
        'boq': 'max_boq_generations',
        'bid': 'max_bid_optimizations',
        'users': 'users_limit',
        'extension': 'extension_auto_fills'
    }
    
    key = limit_map.get(limit_type, 'analyses_limit')
    return plan.get(key, 5)


# =============================================================================
# UI FUNCTIONS
# =============================================================================

# modules/subscription.py

def render_subscription_page():
    """Render subscription management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>💳 Subscription Management</h1>
        <p>Manage your plan, billing, and premium features</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get plans from database
    plans = get_plans()
    
    # ✅ Get effective plan using the new logic
    effective = get_current_user_effective_plan()
    current_plan = effective.get('plan', 'free')
    source = effective.get('source', 'none')
    subscription = effective.get('subscription', {})
    
    # Debug
    print(f"📊 Subscription Page - User: {st.session_state.user_id}")
    print(f"   Effective Plan: {current_plan} (Source: {source})")
    print(f"   Subscription Data: {subscription}")
    
    # =========================================================================
    # CURRENT SUBSCRIPTION
    # =========================================================================
    st.markdown("### 📋 Current Subscription")
    
    # Show source badge
    source_label = {
        'company': '🏢 Company Plan',
        'individual': '👤 Individual Plan',
        'system_admin': '👑 System Admin',
        'none': ''
    }.get(source, '')
    
    if source_label:
        st.info(f"📌 You are on the **{source_label}**")
    
    render_subscription_card(
        subscription=subscription,
        company_id=st.session_state.get('company_id'),
        show_update=False,
        show_cancel=False,
        title=""
    )
    
    # Current features
    st.markdown("### ✨ Current Plan Features")
    plan_config = get_plan(current_plan)
    for feature in plan_config.get('features', ['Basic features']):
        st.markdown(f"✅ {feature}")
    
    # =========================================================================
    # UPGRADE OPTIONS
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🚀 Upgrade Options")
    
    # ✅ Check if user can upgrade
    # Company users can only upgrade company plan (admin only)
    # Individual users can upgrade their own plan
    user_role = st.session_state.get('user_role', 'viewer')
    company_id = st.session_state.get('company_id')
    
    if company_id and source == 'company':
        # Company user - only company admin can upgrade
        if user_role in ['company_admin', 'admin', 'system_admin']:
            st.info("📌 You are on a company plan. Company admins can upgrade the company subscription.")
            if st.button("🏢 Go to Company Subscription Management", use_container_width=True):
                st.session_state.page = "company_subscription"
                st.rerun()
        else:
            st.info("📌 Your company subscription is managed by your company admin.")
            st.caption("Contact your company admin to request an upgrade.")
    elif not company_id and source == 'individual':
        # Individual user - can upgrade own plan
        _render_upgrade_options(current_plan, plans)
    else:
        # Fallback: show upgrade options if no clear source
        _render_upgrade_options(current_plan, plans)
    
    # =========================================================================
    # ADMIN: VIEW ALL SUBSCRIPTIONS
    # =========================================================================
    if st.session_state.get('user_role') in ['admin', 'system_admin']:
        _render_admin_subscriptions()
    
    # =========================================================================
    # BILLING HISTORY
    # =========================================================================
    _render_billing_history()


def _render_upgrade_options(current_plan: str, plans: Dict):
    """Render upgrade options for individual users or admins"""
    
    plan_order = ['free', 'basic', 'professional', 'enterprise']
    current_index = plan_order.index(current_plan) if current_plan in plan_order else 0
    
    if current_index >= len(plan_order) - 1:
        st.success("🎉 You're on the highest plan! You have access to all features.")
        return
    
    # Billing cycle toggle
    billing_cycle = st.radio(
        "Billing Cycle",
        ["Monthly", "Yearly (Save 20%)"],
        horizontal=True,
        key="billing_cycle"
    )
    
    _render_plan_comparison(current_plan, billing_cycle, plans)

def _render_plan_comparison(current_plan: str, billing_cycle: str, plans: Dict):
    """Render plan comparison cards with gradient styling"""
    
    plan_order = ['free', 'basic', 'professional', 'enterprise']
    current_index = plan_order.index(current_plan) if current_plan in plan_order else 0
    
    upgrade_plans = []
    for i, plan in enumerate(plan_order):
        if i > current_index:
            upgrade_plans.append(plan)
    
    if not upgrade_plans:
        st.success("🎉 You're on the highest plan! You have access to all features.")
        return
    
    cols = st.columns(min(len(upgrade_plans), 3))
    
    for idx, plan_key in enumerate(upgrade_plans):
        if idx >= 3:
            break
        
        plan = plans.get(plan_key, {})
        
        if billing_cycle == "Monthly":
            price = plan.get('price_monthly', 0)
            period = 'month'
        else:
            price = plan.get('price_yearly', 0)
            period = 'year'
        
        plan_name = plan.get('name', plan_key.title())
        badge = plan.get('badge', '📋')
        color = plan.get('color', '#6c757d')
        features = plan.get('features', ['Basic features'])
        users_limit = plan.get('users_limit', 1)
        
        # ✅ Gradient color for different plans
        gradient_colors = {
            'basic': 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
            'professional': 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
            'enterprise': 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
        }
        gradient = gradient_colors.get(plan_key, 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
        
        # ✅ Card border glow
        glow_colors = {
            'basic': 'rgba(59, 130, 246, 0.3)',
            'professional': 'rgba(139, 92, 246, 0.3)',
            'enterprise': 'rgba(16, 185, 129, 0.3)'
        }
        glow = glow_colors.get(plan_key, 'rgba(102, 126, 234, 0.3)')
        
        with cols[idx]:
            st.markdown(f"""
            <div style="background: white; padding: 1.8rem 1.5rem; border-radius: 16px; 
                        border: 2px solid {color};
                        text-align: center; margin: 0.5rem; 
                        position: relative;
                        box-shadow: 0 8px 30px {glow};
                        transition: all 0.3s ease;">
                <div style="font-size: 2.8rem; margin-bottom: 0.25rem;">{badge}</div>
                <h3 style="margin: 0.25rem 0; font-size: 1.5rem; font-weight: 700; color: #1a1a2e;">{plan_name}</h3>
                <div style="font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0; color: #1a1a2e;">
                    ৳{price:,.0f}
                    <small style="font-size: 0.8rem; font-weight: normal; color: #6c757d;">
                        /{period}
                    </small>
                </div>
                <div style="background: {gradient}; height: 3px; width: 50px; margin: 0.75rem auto; border-radius: 2px;"></div>
            """, unsafe_allow_html=True)
            
            # Features with icons
            for feature in features[:4]:
                st.markdown(f"✅ {feature}")
            
            if len(features) > 4:
                st.markdown(f"➕ {len(features) - 4} more features")
            
            users_text = "Unlimited" if users_limit == -1 else users_limit
            st.markdown(f"👥 Up to **{users_text}** users")
            
            # ✅ Button with gradient background
            st.markdown("""
            <style>
            .upgrade-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
            }
            .upgrade-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }
            </style>
            """, unsafe_allow_html=True)
            
            if st.button(
                f"⬆️ Upgrade to {plan_name}", 
                key=f"upgrade_{plan_key}", 
                use_container_width=True,
                type="primary"
            ):
                st.session_state.selected_plan = plan_key
                st.session_state.billing_cycle = billing_cycle.lower()
                st.session_state.show_checkout = True
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
def _render_admin_subscriptions():
    """Render admin view of all subscriptions"""
    
    st.markdown("---")
    st.markdown("### 👑 Admin: All Subscriptions")
    
    all_subs = db.get_all_subscriptions()
    
    if all_subs:
        # Convert to DataFrame
        sub_df = pd.DataFrame(all_subs)
        
        # Select columns to display
        display_cols = ['id', 'plan', 'status', 'company_id', 'user_id', 'start_date', 'end_date']
        available_cols = [col for col in display_cols if col in sub_df.columns]
        
        if available_cols:
            st.dataframe(
                sub_df[available_cols],
                use_container_width=True,
                hide_index=True
            )
        
        # Download option
        csv = sub_df.to_csv(index=False)
        st.download_button(
            "📥 Download Subscriptions CSV",
            csv,
            f"subscriptions_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info("No subscriptions found")


def _render_billing_history():
    """Render billing history"""
    
    st.markdown("---")
    st.markdown("### 📜 Billing History")
    
    # This would typically come from a billing table
    # For now, show sample data
    history_data = [
        {'Date': '2024-03-01', 'Amount': '৳14,999', 'Plan': 'Professional', 'Status': 'Paid'},
        {'Date': '2024-02-01', 'Amount': '৳14,999', 'Plan': 'Professional', 'Status': 'Paid'},
        {'Date': '2024-01-01', 'Amount': '৳14,999', 'Plan': 'Professional', 'Status': 'Paid'},
    ]
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_checkout():
    """Render checkout page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>💳 Checkout</h1>
        <p>Complete your purchase</p>
    </div>
    """, unsafe_allow_html=True)
    
    if 'selected_plan' not in st.session_state:
        st.session_state.selected_plan = 'professional'
    
    plan = get_plan(st.session_state.selected_plan)
    billing = st.session_state.get('billing_cycle', 'monthly')
    
    if billing == 'monthly':
        price = plan.get('price_monthly', 0)
        duration = 'month'
    else:
        price = plan.get('price_yearly', 0)
        duration = 'year'
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_checkout_summary(plan, price, duration, billing)
    
    with col2:
        _render_checkout_features(plan)


def _render_checkout_summary(plan: Dict, price: float, duration: str, billing: str):
    """Render checkout order summary"""
    
    st.markdown(f"### {plan.get('name', 'Plan')} Plan - {duration.upper()}LY")
    
    # Order summary
    st.markdown(f"""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <h4>Order Summary</h4>
        <p><strong>Plan:</strong> {plan.get('name', 'Plan')} ({duration}ly)</p>
        <p><strong>Subtotal:</strong> ৳{price:,.0f}</p>
        <p><strong>VAT (15%):</strong> ৳{price * 0.15:,.0f}</p>
        <hr>
        <p><strong>Total:</strong> ৳{price * 1.15:,.0f}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Payment methods
    st.markdown("### Select Payment Method")
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    
    payment_methods = {
        'bkash': '💚 bKash',
        'nagad': '🧡 Nagad',
        'rocket': '💙 Rocket',
        'card': '💳 Credit Card'
    }
    
    selected_payment = None
    for idx, (key, name) in enumerate(payment_methods.items()):
        with [col_p1, col_p2, col_p3, col_p4][idx]:
            if st.button(name, key=f"pay_{key}", use_container_width=True):
                selected_payment = key
    
    if selected_payment:
        _render_payment_form(selected_payment, payment_methods, plan, price, duration, billing)


def _render_payment_form(selected_payment: str, payment_methods: Dict, plan: Dict, price: float, duration: str, billing: str):
    """Render payment form for selected payment method"""
    
    st.markdown(f"### Payment via {payment_methods[selected_payment]}")
    
    if selected_payment == 'bkash':
        phone = st.text_input("bKash Account Number (01XXXXXXXXX)")
        if st.button("Complete Payment", use_container_width=True):
            if phone:
                transaction_id = f"BKASH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                success = db.update_user_subscription(
                    st.session_state.user_id, 
                    st.session_state.selected_plan, 
                    billing, 
                    selected_payment, 
                    transaction_id
                )
                if success:
                    st.balloons()
                    st.success("✅ Payment successful! Subscription activated.")
                    st.session_state.show_checkout = False
                    st.rerun()
                else:
                    st.error("❌ Payment failed. Please try again.")
            else:
                st.error("Please enter your bKash number")
    
    elif selected_payment == 'card':
        st.markdown("**Card Details**")
        card_number = st.text_input("Card Number", placeholder="4242 4242 4242 4242")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            expiry = st.text_input("Expiry (MM/YY)")
        with col_c2:
            cvv = st.text_input("CVV", type="password")
        
        if st.button("Pay Now", use_container_width=True):
            if card_number and expiry and cvv:
                transaction_id = f"CARD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                success = db.update_user_subscription(
                    st.session_state.user_id, 
                    st.session_state.selected_plan, 
                    billing, 
                    selected_payment, 
                    transaction_id
                )
                if success:
                    st.balloons()
                    st.success("✅ Payment successful! Subscription activated.")
                    st.session_state.show_checkout = False
                    st.rerun()
                else:
                    st.error("❌ Payment failed. Please try again.")
            else:
                st.error("Please fill all card details")


def _render_checkout_features(plan: Dict):
    """Render checkout features sidebar"""
    
    st.markdown("### What's Included")
    features = plan.get('features', ['Basic features'])
    for feature in features:
        st.markdown(f"✅ {feature}")
    
    st.markdown("---")
    st.markdown("### 🔒 Secure Payment")
    st.markdown("""
    - 256-bit SSL encryption
    - PCI compliant
    - Money-back guarantee
    """)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_plan_config(plan_name: str) -> Dict:
    """Get plan configuration by name"""
    return get_plan(plan_name)


def get_current_user_plan() -> Dict:
    """Get current user's plan configuration"""
    current_sub = db.get_user_subscription(st.session_state.user_id)
    current_plan = current_sub.get('subscription_tier', 'free')
    return get_plan(current_plan)


def get_current_user_plan_name() -> str:
    """Get current user's plan name"""
    current_sub = db.get_user_subscription(st.session_state.user_id)
    return current_sub.get('subscription_tier', 'free')


def get_available_plans() -> List[Dict]:
    """Get list of all available plans"""
    plans = get_plans()
    return list(plans.values())


def get_plan_display_name(plan_name: str) -> str:
    """Get display name for plan"""
    plan = get_plan(plan_name)
    return plan.get('name', plan_name.title())


def get_plan_limit_by_type(plan_name: str, limit_type: str) -> int:
    """Get plan limit by type"""
    return get_plan_limit(plan_name, limit_type)


def is_plan_available(plan_name: str) -> bool:
    """Check if a plan is available"""
    plans = get_plans()
    return plan_name in plans


def render_plan_badge(plan_name: str):
    """Render a small plan badge"""
    plan = get_plan(plan_name)
    color = plan.get('color', '#6c757d')
    badge = plan.get('badge', '📋')
    name = plan.get('name', plan_name.title())
    
    st.markdown(f"""
    <span style="background: {color}20; color: {color}; 
                 border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600;">
        {badge} {name}
    </span>
    """, unsafe_allow_html=True)
def render_simple_subscription_status(subscription: Dict):
    """Render a simple subscription status badge"""
    plan = subscription.get('subscription_tier') or subscription.get('plan', 'free')
    status = subscription.get('status', 'active')
    
    plan_config = get_plan(plan)
    color = plan_config.get('color', '#6c757d')
    badge = plan_config.get('badge', '📋')
    name = plan_config.get('name', plan.title())
    
    status_color = '#10b981' if status == 'active' else '#ef4444'
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 8px 16px; 
                background: {color}15; border-radius: 8px; margin: 4px 0; 
                border: 1px solid {color}30;">
        <span style="font-weight: 600; color: {color};">{badge} {name}</span>
        <span style="color: {status_color}; font-size: 0.8rem;">
            • {status.upper()}
        </span>
        <span style="margin-left: auto; font-size: 0.7rem; color: #6c757d;">
            {subscription.get('end_date', 'No expiry')}
        </span>
    </div>
    """, unsafe_allow_html=True)

# modules/subscription.py

def get_effective_plan_for_user(user_id: int) -> Dict:
    """
    Get the effective plan for a user.
    
    Logic:
    1. If user has company_id -> Use company subscription ONLY
    2. If user has NO company_id -> Use individual subscription
    3. If no subscription found -> Free plan
    
    Returns:
        Dict with plan details
    """
    # ✅ Get user data
    user = db.get_user_by_id(user_id)
    if not user:
        return {'plan': 'free', 'source': 'none', 'subscription': {}}
    
    company_id = user.get('company_id')
    
    # ✅ If user belongs to a company, use company subscription ONLY
    if company_id:
        print(f"🏢 User {user_id} belongs to company {company_id} - using company subscription")
        company_sub = db.get_company_subscription(company_id)
        company_plan = company_sub.get('subscription_tier') or company_sub.get('plan', 'free')
        
        return {
            'plan': company_plan,
            'source': 'company',
            'subscription': company_sub,
            'is_premium': is_premium_plan(company_plan),
            'company_id': company_id
        }
    
    # ✅ Individual user - use personal subscription
    print(f"👤 User {user_id} is an individual - using personal subscription")
    user_sub = db.get_user_subscription(user_id)
    user_plan = user_sub.get('subscription_tier') or user_sub.get('plan', 'free')
    
    return {
        'plan': user_plan,
        'source': 'individual',
        'subscription': user_sub,
        'is_premium': is_premium_plan(user_plan),
        'company_id': None
    }


def get_current_user_effective_plan() -> Dict:
    """Get current user's effective plan"""
    user_id = st.session_state.get('user_id')
    if not user_id:
        return {'plan': 'free', 'source': 'none', 'subscription': {}}
    return get_effective_plan_for_user(user_id)


def get_current_user_plan_name() -> str:
    """Get current user's effective plan name"""
    effective = get_current_user_effective_plan()
    return effective.get('plan', 'free')


def is_premium_user() -> bool:
    """Check if current user has premium access"""
    user_role = st.session_state.get('user_role', 'viewer')
    
    # System admins bypass
    if user_role in ['admin', 'system_admin']:
        return True
    
    effective = get_current_user_effective_plan()
    return effective.get('is_premium', False)