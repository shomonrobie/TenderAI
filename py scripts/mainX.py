import streamlit as st
import sys
import traceback

print("=" * 60)
print("Starting TenderAI Application...")
print("=" * 60)

try:
    print("Step 1: Importing modules...")
    from database.db_manager import DatabaseManager
    from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user

    from modules.subscription import render_subscription_page, render_checkout
    from modules.user_management import render_user_management
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime
    print("Step 1: Modules imported successfully")
    
except Exception as e:
    print(f"ERROR in imports: {str(e)}")
    traceback.print_exc()
    st.error(f"Import error: {str(e)}")
    st.stop()

# Initialize database
print("Step 2: Initializing database...")
try:
    db = DatabaseManager()
    print("Step 2: Database initialized successfully")
except Exception as e:
    print(f"ERROR in database init: {str(e)}")
    traceback.print_exc()
    st.error(f"Database error: {str(e)}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="TenderAI - Tender Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

print("Step 3: Page config set")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-weight: bold;
        width: 100%;
    }
    div[data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

print("Step 4: CSS applied")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'show_checkout' not in st.session_state:
    st.session_state.show_checkout = False

print(f"Step 5: Session state initialized. logged_in={st.session_state.logged_in}, page={st.session_state.page}")

# Import page functions
def ensure_admin_premium():
    """Force admin to have professional plan for testing"""
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            return True
    return False

# Simple placeholder pages for testing
def home_page():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 3rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 3rem;">🏗️ TenderAI</h1>
        <p style="color: white; font-size: 1.5rem;">AI-Powered Tender Management System</p>
    </div>
    """, unsafe_allow_html=True)
    st.success("Home page loaded successfully!")
    if st.button("Login"):
        st.session_state.page = "login"
        st.rerun()

def login_page():
    st.markdown("""
    <div class="main-header">
        <h1 style="text-align: center;">🔐 Login</h1>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                # Simple authentication for testing
                if username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.user_id = 1
                    st.session_state.username = "admin"
                    st.session_state.user_role = "admin"
                    st.session_state.full_name = "System Administrator"
                    st.session_state.company_name = "System Admin"
                    st.success("Login successful!")
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        if st.button("Register"):
            st.session_state.page = "register"
            st.rerun()

def register_page():
    st.markdown("""
    <div class="main-header">
        <h1>📝 Register</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Registration page - to be implemented")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

def dashboard_page():
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome, {st.session_state.get('full_name', 'User')}! 👋</h1>
        <p>Dashboard loaded successfully</p>
    </div>
    """, unsafe_allow_html=True)
    st.success("Dashboard page is working!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Analyses", "0")
    with col2:
        st.metric("Win Rate", "0%")
    with col3:
        st.metric("Active Tenders", "0")
    
    if st.button("Go to Analysis"):
        st.session_state.page = "new_analysis"
        st.rerun()

def tender_analysis_page():
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Bid Optimization</h1>
        <p>Analysis page - Coming Soon</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("This page is under development")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def history_page():
    st.markdown("""
    <div class="main-header">
        <h1>📜 History</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("History page - Coming Soon")

def profile_page():
    st.markdown("""
    <div class="main-header">
        <h1>👤 Profile</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Profile page - Coming Soon")

def pricing_page():
    st.markdown("""
    <div class="main-header">
        <h1>💰 Pricing</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Pricing page - Coming Soon")

def about_page():
    st.markdown("""
    <div class="main-header">
        <h1>ℹ️ About</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("About page - Coming Soon")

def contact_page():
    st.markdown("""
    <div class="main-header">
        <h1>📞 Contact</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Contact page - Coming Soon")

def admin_dashboard_page():
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Admin Dashboard - Coming Soon")

def render_subscription_page():
    st.markdown("""
    <div class="main-header">
        <h1>💳 Subscription</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Subscription page - Coming Soon")

def render_user_management():
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Management</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("User Management - Coming Soon")

def render_checkout():
    st.markdown("""
    <div class="main-header">
        <h1>💳 Checkout</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("Checkout - Coming Soon")

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🏗️ TenderAI")
        st.markdown("---")
        
        if not st.session_state.logged_in:
            menu = {"🏠 Home": "home", "💰 Pricing": "pricing", "ℹ️ About": "about", "📞 Contact": "contact", "🔐 Login": "login"}
            for label, page in menu.items():
                if st.button(label, key=page, use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
        else:
            st.markdown(f"### 👋 {st.session_state.get('full_name', 'User')}")
            st.markdown(f"🏢 {st.session_state.get('company_name', 'Company')}")
            st.markdown(f"⭐ {st.session_state.get('user_role', 'user')}")
            st.markdown("---")
            
            st.markdown("### Main Menu")
            main_menu = {"📊 Dashboard": "dashboard", "🎯 Analysis": "new_analysis", "📜 History": "history", "👤 Profile": "profile"}
            for label, page in main_menu.items():
                if st.button(label, key=page, use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Logout", key="logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.logged_in = False
                st.session_state.page = "home"
                st.rerun()

print("Step 6: All page functions defined")

# Main function
def main():
    print(f"Step 7: Main function called. Current page: {st.session_state.page}")
    
    try:
        render_sidebar()
        print("Step 8: Sidebar rendered")
        
        # Page routing
        if st.session_state.get('show_checkout', False):
            print("Rendering checkout...")
            render_checkout()
        elif not st.session_state.logged_in:
            print(f"Not logged in - rendering public page: {st.session_state.page}")
            if st.session_state.page == 'home':
                home_page()
            elif st.session_state.page == 'login':
                login_page()
            elif st.session_state.page == 'register':
                register_page()
            elif st.session_state.page == 'pricing':
                pricing_page()
            elif st.session_state.page == 'about':
                about_page()
            elif st.session_state.page == 'contact':
                contact_page()
            else:
                home_page()
        else:
            print(f"Logged in - rendering private page: {st.session_state.page}")
            if st.session_state.page == 'dashboard':
                dashboard_page()
            elif st.session_state.page == 'new_analysis':
                tender_analysis_page()
            elif st.session_state.page == 'history':
                history_page()
            elif st.session_state.page == 'profile':
                profile_page()
            elif st.session_state.page == 'subscription':
                render_subscription_page()
            elif st.session_state.page == 'user_management':
                render_user_management()
            elif st.session_state.page == 'admin_dashboard':
                admin_dashboard_page()
            else:
                dashboard_page()
        
        print("Step 9: Page rendering complete")
        
    except Exception as e:
        print(f"ERROR in main: {str(e)}")
        traceback.print_exc()
        st.error(f"An error occurred: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    print("Step 10: Running main()")
    main()
    print("Step 11: Application finished")