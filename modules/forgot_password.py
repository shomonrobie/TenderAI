import streamlit as st
import secrets
from database.unified_db_manager import UnifiedDatabaseManager
from modules.email_verification import send_password_reset_email

db = UnifiedDatabaseManager()

def render_forgot_password():
    st.markdown("### 🔑 Reset Your Password")
    
    with st.form("forgot_password_form"):
        email = st.text_input("Enter your registered email")
        submitted = st.form_submit_button("Send Reset Link", type="primary")
        
        if submitted:
            if not email:
                st.error("Please enter your email")
            else:
                user = db.get_user_by_email(email)
                if user:
                    # Generate secure token
                    reset_token = secrets.token_urlsafe(32)
                    
                    if db.store_password_reset_token(email, reset_token):
                        reset_link = f"https://itender-bd.streamlit.app/reset-password?token={reset_token}"
                        if send_password_reset_email(email, reset_link):
                            st.success("✅ Reset link sent to your email!")
                        else:
                            st.error("Failed to send email")
                    else:
                        st.error("System error. Please try again.")
                else:
                    st.error("No account found with this email.")