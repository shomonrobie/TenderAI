import streamlit as st
from modules.auth import login_user

def show():
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Login</h1>
        <p>Access your TenderAI account</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", use_container_width=True):
                if login_user(username, password):
                    st.success(f"Welcome back, {st.session_state.full_name}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.markdown("---")
        st.markdown("### Demo Accounts")
        
        with st.expander("Click to view demo credentials"):
            st.markdown("""
            **Admin Access:**
            - Username: admin
            - Password: admin123
            
            **Company Admin:**
            - Username: john.doe
            - Password: John@123
            
            **Manager:**
            - Username: jane.smith
            - Password: Jane@123
            
            **Analyst:**
            - Username: rahim.khan
            - Password: Rahim@123
            """)
        
        if st.button("Create New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()