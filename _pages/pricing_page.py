import streamlit as st
from modules.auth import login_user

from config import DEBUG_MODE, debug_print
from utils.helpers import (
    render_page_header,
    render_feature_card,
    render_pricing_card,
    render_demo_credentials,
    navigate_to,
    get_compact_css,
    format_currency_bd,
    format_percentage,
    get_bid_status_badge,
    get_risk_indicator,
    validate_password_strength,
    safe_title
)
def show():
    """Updated Login Page with URL-Based Remember Me & Better Integration"""
    debug_print("🔐 Rendering Pricing page")
        
    # Import and call the subscription module
    from modules.subscription_plan_comparison import render_plan_comparison_page
    render_plan_comparison_page()

    from modules.footer import render_footer
    render_footer()   
    debug_print("✅ Pricing page render complete")