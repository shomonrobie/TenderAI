import streamlit as st
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def show():
    st.markdown("""
    <div class="main-header">
        <h1>📞 Contact Us</h1>
        <p>We'd love to hear from you</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Get in Touch
        
        **Office Address:**
        House 123, Road 45
        Gulshan 2, Dhaka 1212
        Bangladesh
        
        **Phone:**
        📞 +880 1234 567890
        
        **Email:**
        📧 sales@tenderai.com
        📧 support@tenderai.com
        
        **Business Hours:**
        Sunday - Thursday: 9:00 AM - 6:00 PM
        """)
    
    with col2:
        st.markdown("### Send us a Message")
        
        with st.form("contact_form"):
            name = st.text_input("Full Name*")
            email = st.text_input("Email Address*")
            subject = st.selectbox("Subject", ["General Inquiry", "Sales", "Support", "Partnership"])
            message = st.text_area("Message*", height=150)
            
            if st.form_submit_button("Send Message", use_container_width=True):
                if name and email and message:
                    db.save_contact_message(name, email, subject, message)
                    st.success("Thank you! We'll get back to you within 24 hours.")
                else:
                    st.error("Please fill all required fields")