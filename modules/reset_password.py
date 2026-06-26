import streamlit as st
import re
from database.unified_db_manager import UnifiedDatabaseManager

# Use string directly instead of PageRoutes to avoid import issues in separate modules
LOGIN_PAGE = "login"

db = UnifiedDatabaseManager()


def validate_password_strength(password: str) -> tuple[float, str, str]:
    """Return strength score (0-100), message, and color"""
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 25
    else:
        feedback.append("≥8 characters")
    
    if re.search(r"[A-Z]", password):
        score += 20
    else:
        feedback.append("Uppercase")
    
    if re.search(r"[a-z]", password):
        score += 20
    else:
        feedback.append("Lowercase")
    
    if re.search(r"\d", password):
        score += 20
    else:
        feedback.append("Number")
    
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 15
    else:
        feedback.append("Special char")
    
    # Determine status
    if score >= 90:
        color = "green"
        status = "✅ Very Strong"
    elif score >= 70:
        color = "lime"
        status = "✅ Strong"
    elif score >= 50:
        color = "orange"
        status = "⚠️ Medium"
    else:
        color = "red"
        status = "❌ Weak"
    
    message = f"**{status}**" + (f" — Add: {', '.join(feedback)}" if feedback else "")
    return score, message, color


def render_reset_password(token: str):
    """Reset password page with strength meter"""
    st.markdown("### 🔑 Set New Password")
    st.caption("This reset link will expire in 60 minutes.")
    
    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password", key="new_pass")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pass")
        
        # === Live Password Strength Meter ===
        if new_password:
            score, message, color = validate_password_strength(new_password)
            st.progress(score / 100)
            st.markdown(f"<p style='color:{color}; font-size:0.95em; margin:4px 0;'>{message}</p>", 
                       unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Update Password", type="primary", use_container_width=True)
        
        if submitted:
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields.")
            elif new_password != confirm_password:
                st.error("❌ Passwords do not match.")
            elif len(new_password) < 8:
                st.error("❌ Password must be at least 8 characters long.")
            else:
                score, _, _ = validate_password_strength(new_password)
                if score < 60:
                    st.error("❌ Your password is too weak. Please strengthen it.")
                else:
                    email = db.verify_reset_token(token)
                    if email:
                        if db.update_password(email, new_password):
                            st.success("✅ Your password has been updated successfully!")
                            st.balloons()
                            
                            # Fixed: Use string instead of PageRoutes
                            st.session_state.page = LOGIN_PAGE
                            st.rerun()
                        else:
                            st.error("Failed to update password. Please try again.")
                    else:
                        st.error("❌ This reset link is invalid or has expired.")