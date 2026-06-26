# modules/plan_comparison.py
"""
Dynamic Plan Comparison Page with Vibrant UI
"""

import streamlit as st
from typing import Dict, List, Optional

from modules.subscription_plans import get_plans
from datetime import datetime

def render_plan_comparison_page(show_current_plan: bool = True):
    st.set_page_config(layout="wide", page_title="Pricing Plans", initial_sidebar_state="expanded")
    """
    Render a vibrant, dynamic plan comparison page
    
    Args:
        show_current_plan: Whether to show current plan badge (default: True)
                          Set to False for public pages
    """
    
    # =========================================================================
    # CSS STYLES
    # =========================================================================
    st.markdown("""
    <style>
    /* Page Header */
    .stColumn {
        display: flex;
        flex-direction: column;
    }
    .plans-header {
        text-align: center;
        padding: 3rem 0 2rem 0;
        background: linear-gradient(135deg, #0c0e1a 0%, #1a1a3e 30%, #2d1b69 60%, #764ba2 100%);
        border-radius: 28px;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        color: white;
    }
    .plans-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);
        animation: shimmer 15s ease-in-out infinite;
    }
    @keyframes shimmer {
        0%, 100% { transform: rotate(0deg); }
        50% { transform: rotate(180deg); }
    }
    .plans-header h1 {
        font-size: 3rem;
        font-weight: 800;
        position: relative;
        z-index: 1;
        background: linear-gradient(135deg, #fff 0%, #e0d7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .plans-header p {
        font-size: 1.1rem;
        opacity: 0.8;
        position: relative;
        z-index: 1;
    }
    .plans-header .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        padding: 0.3rem 1.5rem;
        border-radius: 30px;
        font-size: 0.8rem;
        border: 1px solid rgba(255,255,255,0.1);
        position: relative;
        z-index: 1;
        margin-bottom: 0.5rem;
    }
    .plans-header .subtitle-bn {
        font-size: 1rem;
        opacity: 0.7;
        margin-top: 0.25rem;
        position: relative;
        z-index: 1;
        font-weight: 400;
    }
    
    /* === IMPROVED PLAN CARDS === */
    .plan-card {
        border-radius: 20px;
        padding: 2rem 1.5rem 2.5rem 1.5rem;
        text-align: center;
        height: 100%;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: visible !important;
        border: 2px solid transparent;
        background: white;
        display: flex;
        flex-direction: column;
    }

    .plan-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }

    /* Equal height support */
    .plan-card > * {
        flex-shrink: 0;
    }
    .plan-features {
        flex-grow: 1;
        margin-bottom: 1.5rem;
        text-align: left;
        padding: 0;
        list-style: none;
    }
    .plan-features li {
        padding: 4px 0;
        font-size: 0.9rem;
    }

    /* Badges - Fixed positioning */
    .popular-badge, .current-plan-badge {
        position: absolute;
        top: -12px;
        right: 16px;
        padding: 6px 16px;
        border-radius: 30px;
        font-size: 0.75rem;
        font-weight: 700;
        z-index: 20;
        box-shadow: 0 4px 15px rgba(0,0,0,0.25);
        white-space: nowrap;
    }

    .popular-badge {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
    }

    .current-plan-badge {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
    }

    /* Card Glow */
    .plan-card .card-glow {
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        border-radius: 50%;
        opacity: 0;
        transition: opacity 0.6s ease;
        pointer-events: none;
    }
    .plan-card:hover .card-glow {
        opacity: 0.1;
    }

    /* Typography & Elements */
    .plan-card .plan-badge {
        font-size: 3rem;
        margin-bottom: 0.25rem;
        display: block;
    }
    .plan-card .plan-name {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0.25rem 0;
        color: #1a1a2e;
    }
    .plan-card .plan-price {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0.5rem 0;
        color: #1a1a2e;
    }
    .plan-card .plan-price small {
        font-size: 0.8rem;
        font-weight: normal;
        opacity: 0.6;
    }
    .plan-card .plan-divider {
        height: 3px;
        width: 40px;
        margin: 0.75rem auto;
        border-radius: 2px;
    }

    /* Plan Colors */
    .plan-free { border-color: #6c757d; }
    .plan-free .plan-name { color: #6c757d; }
    .plan-free .plan-divider { background: #6c757d; }

    .plan-basic { border-color: #3b82f6; }
    .plan-basic .plan-name { color: #3b82f6; }
    .plan-basic .plan-divider { background: #3b82f6; }
    .plan-basic .card-glow { background: radial-gradient(circle, #3b82f6 0%, transparent 70%); }

    .plan-professional { 
        border-color: #8b5cf6; 
        box-shadow: 0 8px 30px rgba(139, 92, 246, 0.15);
    }
    .plan-professional .plan-name { color: #8b5cf6; }
    .plan-professional .plan-divider { background: #8b5cf6; }
    .plan-professional .card-glow { background: radial-gradient(circle, #8b5cf6 0%, transparent 70%); }

    .plan-enterprise { border-color: #10b981; }
    .plan-enterprise .plan-name { color: #10b981; }
    .plan-enterprise .plan-divider { background: #10b981; }
    .plan-enterprise .card-glow { background: radial-gradient(circle, #10b981 0%, transparent 70%); }
    
    /* Comparison Table */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border-radius: 12px;
        overflow: hidden;
    }
    .comparison-table thead tr {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
        color: white;
    }
    .comparison-table th {
        padding: 14px 16px;
        text-align: center;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .comparison-table td {
        padding: 12px 16px;
        text-align: center;
        border-bottom: 1px solid #f0edf5;
    }
    .comparison-table tbody tr:nth-child(even) {
        background-color: #f8f5ff;
    }
    .comparison-table tbody tr:hover {
        background-color: #ede7f6;
    }
    .comparison-table .feature-label {
        text-align: left;
        font-weight: 500;
        color: #1a1a2e;
    }
    .comparison-table .feature-current {
        background: rgba(16, 185, 129, 0.1);
        border-left: 3px solid #10b981;
    }
    .comparison-table .check {
        color: #10b981;
        font-weight: 700;
        font-size: 1.2rem;
    }
    .comparison-table .cross {
        color: #dc3545;
        font-weight: 700;
        font-size: 1.2rem;
    }
    .comparison-table .limit-value {
        font-weight: 600;
        color: #1a1a2e;
    }
    .comparison-table .unlimited {
        color: #8b5cf6;
        font-weight: 700;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .plans-header h1 { font-size: 2rem; }
        .plan-card { padding: 1.5rem 1rem; }
        .plan-card .plan-price { font-size: 1.6rem; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<style> .plan-card { opacity: 1 !important; } </style>", unsafe_allow_html=True)
    # =========================================================================
    # HEADER
    # =========================================================================
    st.markdown("""
    <div class="plans-header">
        <div class="badge">🚀 FIND YOUR PERFECT PLAN</div>
        <h1>Choose Your Growth Path</h1>
        <p>Select the plan that fits your business needs. Upgrade anytime.</p>
        <div class="subtitle-bn">আপনার ব্যবসার জন্য সেরা প্ল্যান বেছে নিন</div>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # BILLING TOGGLE
    # =========================================================================
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        billing_cycle = st.radio(
            "Billing Cycle",
            ["Monthly", "Yearly (Save 20%)"],
            horizontal=True,
            key="billing_cycle_comparison"
        )
    
    # =========================================================================
    # GET PLANS
    # =========================================================================
    plans = get_plans()
    plan_order = ['free', 'basic', 'professional', 'enterprise']
    
    # ✅ Check if user is logged in before getting current plan
    is_logged_in = st.session_state.get('logged_in', False)
    
    if is_logged_in and show_current_plan:
        from modules.subscription import get_current_user_plan_name
        current_plan = get_current_user_plan_name()
    else:
        current_plan = None
    
    # =========================================================================
    # PLAN CARDS - RENDER WITH st.markdown
    # =========================================================================
    _render_plan_cards(current_plan, billing_cycle, plans, plan_order, is_logged_in)
        

def _render_plan_cards(current_plan: Optional[str], billing_cycle: str, 
                       plans: Dict, plan_order: List[str], is_logged_in: bool):
    """Render plan comparison cards - FIXED"""
    
    if is_logged_in and current_plan:
        try:
            current_index = plan_order.index(current_plan)
            display_plans = plan_order[current_index:]
        except ValueError:
            display_plans = plan_order
        
        if len(display_plans) <= 1:
            st.success("🎉 You're on the highest plan! You have access to all features.")
            return
    else:
        display_plans = plan_order

    cols = st.columns(min(len(display_plans), 4))

    for idx, plan_key in enumerate(display_plans):
        if idx >= 4:
            break

        plan = plans.get(plan_key, {})
        
        # Price logic
        if billing_cycle.startswith("Monthly"):
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

        is_current = is_logged_in and plan_key == current_plan
        is_popular = plan_key == 'professional'

        # ====================== CLEAN COMPACT HTML ======================
        parts = [f'<div class="plan-card plan-{plan_key}" style="border-color: {color};">']

        if is_popular and not is_current:
            parts.append('<div class="popular-badge">⭐ MOST POPULAR</div>')
        if is_current:
            parts.append('<div class="current-plan-badge">✅ CURRENT PLAN</div>')

        parts.append(f'''
            <div class="card-glow" style="background: radial-gradient(circle, {color} 0%, transparent 70%);"></div>
            <span class="plan-badge">{badge}</span>
            <div class="plan-name">{plan_name}</div>
            <div class="plan-price">
                ৳{price:,.0f}
                <small>/{period}</small>
            </div>
            <div class="plan-divider" style="background: {color};"></div>
            <ul class="plan-features">
        ''')

        for feature in features[:5]:
            parts.append(f'<li>✅ {feature}</li>')

        if len(features) > 5:
            parts.append(f'<li style="color: #6c757d; font-size: 0.85rem;">+ {len(features)-5} more features</li>')

        users_text = "Unlimited" if users_limit == -1 else users_limit
        parts.append(f'<li style="color: #6c757d; font-size: 0.85rem;">👥 Up to {users_text} users</li>')
        parts.append('</ul></div>')

        # Join everything into ONE clean HTML string
        card_html = "".join(parts)

        # Render
        with cols[idx]:
            st.markdown(card_html, unsafe_allow_html=True)

            # Bottom action area
            if is_current:
                st.markdown("""
                    <div style="text-align:center; margin-top:15px;">
                        <span style="background:#10b981;color:white;padding:10px 24px;
                                     border-radius:30px;font-weight:600;">
                            ✅ Current Plan
                        </span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                btn_label = "Choose Plan" if not is_logged_in else "⬆️ Upgrade Now"
                if st.button(
                    btn_label,
                    key=f"plan_{plan_key}_{idx}",   # unique key
                    use_container_width=True,
                    type="primary" if is_popular else "secondary"
                ):
                    if is_logged_in:
                        st.session_state.selected_plan = plan_key
                        st.session_state.billing_cycle = "monthly" if billing_cycle.startswith("Monthly") else "yearly"
                        st.session_state.show_checkout = True
                        st.rerun()
                    else:
                        st.session_state.page = "register"
                        st.rerun()