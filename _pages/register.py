import streamlit as st
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def show():
    """User registration page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📝 Create Account</h1>
        <p>Start your 14-day free trial</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("register_form"):
            st.markdown("### Company Information")
            company_name = st.text_input("Company Name*")
            company_email = st.text_input("Company Email*")
            company_phone = st.text_input("Company Phone")
            division = st.selectbox("Division", ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"])
            
            st.markdown("### Admin Account")
            full_name = st.text_input("Full Name*")
            email = st.text_input("Email Address*")
            username = st.text_input("Username*")
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy*")
            
            if st.form_submit_button("Create Account", use_container_width=True):
                if not all([company_name, company_email, full_name, email, username, password]):
                    st.error("Please fill all required fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif not terms:
                    st.error("Please accept the terms")
                else:
                    # Create company first
                    company_data = {
                        'company_name': company_name,
                        'email': company_email,
                        'phone': company_phone,
                        'division': division
                    }
                    
                    success, result = db.create_company(company_data)
                    
                    if success:
                        company_id = result
                        
                        # Create user
                        user_data = {
                            'username': username,
                            'password': password,
                            'email': email,
                            'full_name': full_name,
                            'phone': '',
                            'role': 'company_admin'
                        }
                        
                        user_success, user_result = db.create_user(company_id, user_data, None)
                        
                        if user_success:
                            st.success("Account created successfully! Please login.")
                            st.session_state.page = "login"
                            st.rerun()
                        else:
                            st.error(f"Error creating user: {user_result}")
                    else:
                        st.error(f"Error creating company: {result}")
    
    with col2:
        st.markdown("### 🎁 What You Get")
        st.markdown("""
        #### Free Trial (14 days):
        - ✅ Professional plan features
        - ✅ Unlimited analyses
        - ✅ AI-powered predictions
        - ✅ Team collaboration
        - ✅ Priority support
        - ✅ No credit card required
        
        #### After Trial:
        - Choose from flexible plans
        - Cancel anytime
        - No hidden fees
        """)
        
        st.info("Already have an account? [Login here](#)")
        if st.button("Login Instead", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()