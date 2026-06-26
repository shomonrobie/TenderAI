
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
    """Contact us page with form"""
    debug_print("📞 Rendering contact page")
    
    render_page_header("📞 Contact Us", "We're here to help")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("contact_form", clear_on_submit=True):
            name = st.text_input("Your Name *", key="contact_name")
            email = st.text_input("Your Email *", key="contact_email")
            subject = st.selectbox("Subject", 
                ["General Inquiry", "Technical Support", "Sales Question", "Partnership", "Other"],
                key="contact_subject"
            )
            message = st.text_area("Message *", height=150, key="contact_message")
            
            submitted = st.form_submit_button("Send Message", use_container_width=True, type="primary")
            
            if submitted:
                if not all([name, email, message]):
                    st.error("❌ Please fill all required fields")
                else:
                    try:
                        db.save_contact_message(name, email, subject, message)
                        st.success("✅ Thank you! We'll get back to you within 24 hours.")
                        # Clear form by rerunning
                        st.rerun()
                    except Exception as e:
                        debug_print(f"❌ Contact form error: {e}")
                        st.error("❌ Failed to send message. Please try again or email support@tenderai.com")
    
    with col2:
        st.markdown("### 📬 Other Ways to Reach Us")
        st.markdown("""
        **Email**  
        📧 support@tenderai.com  
        📧 sales@tenderai.com  
        
        **Phone**  
        📱 +880 1XXX-XXXXXX (Sat-Thu, 9AM-6PM)  
        
        **Office**  
        📍 Dhaka, Bangladesh  
        """)
        
        st.markdown("### ⏱️ Response Times")
        st.markdown("""
        - **Technical Support**: < 4 hours (business days)  
        - **Sales Inquiries**: < 24 hours  
        - **General Questions**: < 48 hours  
        """)
    
    from modules.footer import render_footer
    render_footer()
    debug_print("✅ Contact page render complete")