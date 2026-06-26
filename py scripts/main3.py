"""
TenderAI - Enterprise Tender Management System
Complete Working Version - Fixed
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import traceback
import logging
import sys
import json
# =============================================================================
# 🔧 DEBUG CONFIGURATION - Toggle at the top of your app
# =============================================================================
DEBUG_MODE = True  # Set to False in production

def debug_print(*args, **kwargs):
    """Conditional print for debugging"""
    if DEBUG_MODE:
        print(*args, **kwargs)

def setup_logging():
    """Configure logging with debug level if needed"""
    level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Override existing config
    )

# Call this once at app startup
# setup_logging()
logger = logging.getLogger(__name__)


from datetime import datetime
from database.db_manager import DatabaseManager
from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user

from modules.subscription import render_subscription_page, render_checkout
from modules.user_management import render_user_management

# Initialize database
db = DatabaseManager()

# Try to import advanced optimizer
try:
    from modules.advanced_bid_optimizer import calculate_optimal_bid_ppr2025
    ADVANCED_OPTIMIZER_AVAILABLE = True
except ImportError:
    ADVANCED_OPTIMIZER_AVAILABLE = False

st.set_page_config(
    page_title="TenderAI - Tender Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        font-size: 1.8rem;
        margin: 0;
    }
    .main-header p {
        font-size: 0.9rem;
        margin: 0.5rem 0 0 0;
    }
    .metric-card {
        background: white;
        padding: 0.75rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-card h3 {
        font-size: 0.8rem;
        margin: 0;
        color: #666;
    }
    .metric-card h2 {
        font-size: 1.5rem;
        margin: 0.25rem 0;
    }
    .metric-card small {
        font-size: 0.7rem;
        color: #999;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.4rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.85rem;
        width: 100%;
    }
    div[data-testid="stSidebarNav"] {
        display: none;
    }
    .small-metric {
        text-align: center;
        padding: 0.5rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .small-metric h3 {
        font-size: 0.75rem;
        margin: 0;
        color: #666;
    }
    .small-metric .value {
        font-size: 1.2rem;
        font-weight: bold;
        margin: 0.25rem 0;
    }
    .small-metric .sub {
        font-size: 0.65rem;
        color: #999;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'show_checkout' not in st.session_state:
    st.session_state.show_checkout = False
if 'comparison_result' not in st.session_state:
    st.session_state.comparison_result = None
print(f"Step 5: Session state initialized. logged_in={st.session_state.logged_in}, page={st.session_state.page}")
# Force admin to have professional plan
def ensure_admin_premium():
    """Force admin to have professional plan for testing"""
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            return True
    return False

def parse_competitor_bids(input_text):
    """Properly parse competitor bids from comma-separated string"""
    if not input_text:
        return []
    
    bids = []
    # Split by comma
    parts = input_text.split(',')
    
    for part in parts:
        # Clean the string
        cleaned = part.strip().replace(' ', '').replace('BDT', '').replace('bdt', '')
        # Handle numbers with commas (like 45,000,000)
        cleaned = cleaned.replace(',', '')
        
        try:
            bid = float(cleaned)
            if bid > 0:
                bids.append(bid)
        except ValueError:
            continue
    
    return bids

# ==================== BASIC BID CALCULATION ====================

def calculate_basic_bid(official_estimate, competitor_bids, risk_tolerance='moderate'):
    """Basic bid calculation"""
    
    # Filter out invalid bids (should be close to official estimate range)
    valid_bids = [b for b in competitor_bids if 0.5 * official_estimate <= b <= 2 * official_estimate]
    
    if valid_bids and len(valid_bids) > 0:
        avg_competitor = np.mean(valid_bids)
        min_competitor = np.min(valid_bids)
    else:
        # If no valid competitor bids, estimate based on official estimate
        avg_competitor = official_estimate * 0.92
        min_competitor = official_estimate * 0.85
    
    ratios = {'aggressive': 0.86, 'moderate': 0.89, 'conservative': 0.93}
    ratio = ratios.get(risk_tolerance, 0.89)
    recommended_bid = official_estimate * ratio
    
    # Adjust based on competition
    if recommended_bid > avg_competitor:
        recommended_bid = avg_competitor * 0.99
    
    # Ensure bid is within reasonable range
    recommended_bid = max(recommended_bid, official_estimate * 0.80)
    recommended_bid = min(recommended_bid, official_estimate * 0.98)
    
    # Calculate win probability
    if recommended_bid <= min_competitor:
        win_prob = 0.85
    elif recommended_bid >= avg_competitor:
        win_prob = 0.35
    else:
        win_prob = 0.60
    
    if ratio < 0.87:
        risk_level = "HIGH"
        risk_color = "🔴"
    elif ratio < 0.92:
        risk_level = "MEDIUM"
        risk_color = "🟡"
    else:
        risk_level = "LOW"
        risk_color = "🟢"
    
    return {
        'optimal_bid': recommended_bid,
        'bid_ratio': recommended_bid / official_estimate,
        'win_probability': win_prob,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'avg_competitor': avg_competitor,
        'min_competitor': min_competitor,
        'is_premium': False
    }

# ==================== PAGE FUNCTIONS ====================

def home_page():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 3rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 3rem;">🏗️ TenderAI</h1>
        <p style="color: white; font-size: 1.5rem;">AI-Powered Tender Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    features = [
        ("🤖", "AI Predictions", "85% accurate winning bid predictions"),
        ("📊", "Market Intelligence", "Real-time competitor tracking"),
        ("👥", "Team Collaboration", "Multi-user role-based access"),
    ]
    for idx, (icon, title, desc) in enumerate(features):
        with [col1, col2, col3][idx]:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 10px; text-align: center; margin: 0.5rem;">
                <div style="font-size: 3rem;">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Free Trial", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
        if st.button("💰 View Pricing", use_container_width=True):
            st.session_state.page = "pricing"
            st.rerun()

def login_page():
    """Login page with approval status handling"""
    st.markdown("""
    <div class="main-header">
        <h1 style="text-align: center;">🔐 Login</h1>
        <p style="text-align: center;">Access your TenderAI account</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", use_container_width=True):
                user, status = authenticate_user(username, password)
                
                if status == "pending_approval":
                    st.warning("⚠️ Your account is pending approval by an administrator.")
                    st.info("Please wait for admin approval. You will receive an email notification once approved.")
                elif user and status == "approved":
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.user_email = user[2]
                    st.session_state.full_name = user[3]
                    st.session_state.company_id = user[5]
                    st.session_state.company_name = user[7]
                    st.session_state.user_role = user[4]
                    st.session_state.subscription_plan = user[8] if user[8] else 'free'
                    st.session_state.subscription_status = user[9] if user[9] else 'active'
                    
                    st.success(f"Welcome back, {user[3]}!")
                    st.session_state.page = "dashboard"
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
            
            **Approved Company Admin:**
            - Username: john.doe
            - Password: John@123
            """)
        
        if st.button("Register New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()


def register_page():
    """User registration page"""
    st.markdown("""
    <div class="main-header">
        <h1>📝 Create Account</h1>
        <p>Start your 14-day free trial</p>
        <p>Register for a new account - Approval required</p>
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
                            # Redirect to login page
                            st.session_state.page = "login"
                            st.rerun()
                        else:
                            st.error(f"Error creating user: {user_result}")
                    else:
                        st.error(f"Error creating company: {result}")
    
    with col2:
        st.markdown("### 📝 Registration Process")
        st.markdown("""
        1. **Fill out the registration form**
        2. **Submit for approval**
        3. **Wait for admin approval**
        4. **Login to your account**
        
        ### ⏰ Approval Process
        - Accounts require admin approval
        - You will be notified once approved
        - This ensures security and proper access control
        """)
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


def pricing_page():
    st.markdown("<h1 style='text-align: center;'>💰 Pricing Plans</h1>", unsafe_allow_html=True)
    
    plans = {
        'free': {'name': 'Free', 'price': 0, 'features': ['5 analyses/month', 'Basic reports']},
        'basic': {'name': 'Basic', 'price': 4999, 'features': ['30 analyses/month', 'AI predictions']},
        'professional': {'name': 'Professional', 'price': 14999, 'features': ['Unlimited analyses', 'ML predictions', 'Team collaboration']},
        'enterprise': {'name': 'Enterprise', 'price': 49999, 'features': ['Custom AI', 'Dedicated support']}
    }
    
    col1, col2, col3, col4 = st.columns(4)
    for idx, (key, plan) in enumerate(plans.items()):
        with [col1, col2, col3, col4][idx]:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 10px; text-align: center; margin: 0.5rem;">
                <h3>{plan['name']}</h3>
                <div style="font-size: 2rem; font-weight: bold;">৳{plan['price']:,}<small>/month</small></div>
                <hr>
            """, unsafe_allow_html=True)
            for feature in plan['features']:
                st.markdown(f"✅ {feature}")
            if st.button(f"Select", key=key, use_container_width=True):
                st.session_state.selected_plan = key
                st.session_state.show_checkout = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def about_page():
    st.markdown("""
    <div class="main-header">
        <h1>ℹ️ About Us</h1>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ### Our Mission
    To revolutionize construction industry in Bangladesh with AI technology.
    
    ### Our Vision
    To be the leading AI-powered tender management platform in South Asia.
    """)

def contact_page():
    st.markdown("""
    <div class="main-header">
        <h1>📞 Contact Us</h1>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("contact_form"):
        name = st.text_input("Name*")
        email = st.text_input("Email*")
        message = st.text_area("Message*")
        if st.form_submit_button("Send"):
            db.save_contact_message(name, email, "General", message)
            st.success("Thank you!")

def dashboard_page():
    ensure_admin_premium()
    
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome, {st.session_state.full_name}! 👋</h1>
        <p>{st.session_state.company_name} | {st.session_state.subscription_plan.upper()} Plan</p>
    </div>
    """, unsafe_allow_html=True)
    
    stats = db.get_company_stats(st.session_state.company_id)
    sub = db.get_user_subscription(st.session_state.user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Analyses", stats['total_analyses'])
    with col2:
        st.metric("Win Rate", f"{stats['win_rate']:.0f}%")
    with col3:
        st.metric("Team Members", stats['total_users'])
    with col4:
        limit = sub.get('analyses_limit', 5)
        used = sub.get('analyses_used', 0)
        if limit == -1:
            st.metric("Analyses Left", "Unlimited")
        else:
            st.metric("Analyses Left", max(0, limit - used))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 New Analysis"):
            st.session_state.page = "new_analysis"
            st.rerun()
    with col2:
        if st.button("📜 History"):
            st.session_state.page = "history"
            st.rerun()
    with col3:
        if st.button("👥 User Management"):
            st.session_state.page = "user_management"
            st.rerun()

def history_page():
    st.markdown("""
    <div class="main-header">
        <h1>📜 Tender History</h1>
    </div>
    """, unsafe_allow_html=True)
    
    analyses_df = db.get_user_analyses(st.session_state.user_id, st.session_state.company_id, st.session_state.user_role)
    if len(analyses_df) > 0:
        st.dataframe(analyses_df, use_container_width=True)
    else:
        st.info("No analyses found")

def profile_page():
    st.markdown("""
    <div class="main-header">
        <h1>👤 My Profile</h1>
    </div>
    """, unsafe_allow_html=True)
    
    user = db.get_user_by_id(st.session_state.user_id)
    if user:
        st.info(f"**Name:** {user[5]}")
        st.info(f"**Email:** {user[4]}")
        st.info(f"**Role:** {user[6] if len(user) > 6 else 'N/A'}")
        st.info(f"**Company:** {user[14] if len(user) > 14 else 'N/A'}")

def admin_dashboard_page():
    """Simple admin dashboard"""
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System Administration</p>
    </div>
    """, unsafe_allow_html=True)
    
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", len(all_users))
    with col2:
        active_users = len([u for u in all_users if u[6] == 1]) if all_users else 0
        st.metric("Active Users", active_users)
    with col3:
        st.metric("Total Subscriptions", len(all_subs))
    with col4:
        st.metric("System Status", "Online")
    
    st.markdown("### 📋 All Users")
    if all_users:
        user_data = []
        for u in all_users[:20]:
            user_data.append({
                'Username': u[1], 'Email': u[2], 'Name': u[3], 'Role': u[5], 'Active': '✅' if u[6] else '❌'
            })
        st.dataframe(pd.DataFrame(user_data), use_container_width=True, hide_index=True)

def render_comparison(basic_result, advanced_result, official_estimate, competitor_bids, risk_tolerance):
    """Render comparison between basic and advanced analysis"""
    
    st.markdown("### 🆚 Comparison Results: Basic vs Advanced")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Basic Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {basic_result['optimal_bid']:,.0f}")
        st.markdown(f"- **% of Estimate:** {basic_result['bid_ratio']*100:.1f}%")
        st.markdown(f"- **Win Probability:** {basic_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {basic_result['risk_color']} {basic_result['risk_level']}")
    
    with col2:
        st.markdown("#### 🧠 Advanced ML Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {advanced_result['optimal_bid']:,.0f}")
        st.markdown(f"- **% of Estimate:** {advanced_result['bid_ratio']*100:.1f}%")
        st.markdown(f"- **Win Probability:** {advanced_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {advanced_result['risk_color']} {advanced_result['risk_level']}")
    
    # Difference analysis
    diff = advanced_result['optimal_bid'] - basic_result['optimal_bid']
    diff_percent = (diff / official_estimate) * 100
    
    st.markdown("---")
    st.markdown("#### 💡 Analysis Insight")
    
    if abs(diff) < official_estimate * 0.01:
        st.info("📊 Both analyses suggest similar bid amounts. The market appears stable.")
    elif diff > 0:
        st.warning(f"📈 Advanced analysis suggests increasing bid by BDT {diff:,.0f} ({diff_percent:.1f}% of estimate) for optimal outcome. This accounts for market conditions and competitor patterns.")
    else:
        st.success(f"📉 Advanced analysis suggests decreasing bid by BDT {abs(diff):,.0f} ({abs(diff_percent):.1f}% of estimate) to improve win probability while maintaining profitability.")
    
    # Win probability comparison
    win_diff = advanced_result['win_probability'] - basic_result['win_probability']
    if win_diff > 0.1:
        st.success(f"🎯 Advanced ML analysis shows {win_diff*100:.0f}% higher win probability due to identified competitor patterns.")
    elif win_diff < -0.1:
        st.warning(f"⚠️ Advanced analysis shows lower win probability due to aggressive competitor clustering detected.")
    
    st.markdown("---")
    st.markdown("#### ✅ Recommendation")
    
    if st.session_state.user_role == 'admin':
        st.info(f"**Recommended Bid:** BDT {advanced_result['optimal_bid']:,.0f} (based on advanced ML analysis)")

def _save_analysis_callback():
    """
    Callback function for the Save button.
    Executes when button is clicked, outside the main render cycle.
    """
    debug_print("\n" + "="*60)
    debug_print("🔽 SAVE CALLBACK TRIGGERED")
    debug_print("="*60)
    
    try:
        # === 1. Validate session state ===
        required_keys = [
            'current_analysis_record', 
            'current_best_result', 
            'current_best_tier',
            'current_competitor_bids',
            'current_risk_tolerance',
            'user_id',
            'company_id'
        ]
        
        for key in required_keys:
            if key not in st.session_state or st.session_state[key] is None:
                error_msg = f"Missing required session state: {key}"
                debug_print(f"❌ VALIDATION FAILED: {error_msg}")
                st.error(error_msg)
                return
        
        # === 2. Extract values ===
        analysis_record = st.session_state.current_analysis_record
        best_result = st.session_state.current_best_result
        best_tier = st.session_state.current_best_tier
        competitor_bids = st.session_state.current_competitor_bids
        risk_tolerance = st.session_state.current_risk_tolerance
        user_id = st.session_state.user_id
        company_id = st.session_state.company_id
        
        debug_print(f"✓ Analysis record: {analysis_record.get('tender_id', 'N/A')}")
        debug_print(f"✓ Best tier: {best_tier}")
        debug_print(f"✓ Optimal bid: {best_result.get('optimal_bid', 'N/A')}")
        debug_print(f"✓ Competitor count: {len(competitor_bids)}")
        
        # === 3. Prepare data ===
        official_est = float(analysis_record.get('official_estimate', 0))
        optimal_bid = float(best_result['optimal_bid'])
        win_probability = float(best_result['win_probability'])
        confidence_score = float(best_result.get('confidence_score', 0.75))
        risk_level = str(best_result['risk_level'])
        
        # Calculate derived values
        estimated_cost = official_est * 0.85  # Your business logic
        expected_profit = optimal_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        competitor_bids_json = json.dumps(competitor_bids if competitor_bids else [])
        analysis_type_str = f"{best_tier.upper()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        debug_print(f"✓ Calculated expected_profit: {expected_profit:.2f}")
        debug_print(f"✓ Calculated expected_value: {expected_value:.2f}")
        
        # === 4. Database insertion ===
        debug_print("🗄️  Connecting to database...")
        conn = db.get_connection()  # Your DB connection function
        cursor = conn.cursor()
        
        insert_query = '''
        INSERT INTO tender_analyses (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            division, district, thana, construction_type, official_estimate,
            recommended_bid, success_probability, risk_level, competitor_count,
            analysis_type, competitor_bids, risk_strategy, confidence_score,
            expected_profit, expected_value, analysis_date, bid_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            user_id,
            company_id,
            str(analysis_record.get('tender_id', '')),
            str(analysis_record.get('tender_title', '')),
            str(analysis_record.get('procuring_entity', '')),
            str(analysis_record.get('division', '')),
            str(analysis_record.get('district', '')),
            str(analysis_record.get('thana', '')),
            str(analysis_record.get('construction_type', '')),
            official_est,
            optimal_bid,
            win_probability,
            risk_level,
            int(len(competitor_bids)),
            analysis_type_str,
            competitor_bids_json,
            str(risk_tolerance),
            confidence_score,
            expected_profit,
            expected_value,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'draft'
        )
        
        debug_print(f"🔍 Executing INSERT with {len(params)} parameters...")
        cursor.execute(insert_query, params)
        
        analysis_id = cursor.lastrowid
        conn.commit()
        debug_print(f"✓ Committed transaction. Last insert ID: {analysis_id}")
        
        conn.close()
        debug_print("✓ Database connection closed")
        
        # === 5. Update session state & show success ===
        st.session_state.last_saved_analysis_id = analysis_id
        st.session_state.last_saved_tender_id = analysis_record.get('tender_id', '')
        
        debug_print(f"✅ SAVE SUCCESSFUL! Analysis ID: {analysis_id}")
        debug_print("="*60 + "\n")
        
        st.success(f"✅ {best_tier.upper()} analysis saved! (ID: {analysis_id})")
        st.balloons()
        
        # Optional: Auto-refresh to show updated history
        # st.rerun()  # Uncomment if you want immediate UI refresh
        
    except Exception as e:
        debug_print(f"❌ SAVE ERROR: {type(e).__name__}: {str(e)}")
        logger.error("Save callback failed", exc_info=True)
        
        # Detailed error for debugging
        if DEBUG_MODE:
            import traceback
            debug_print("\n🔎 FULL TRACEBACK:")
            debug_print(traceback.format_exc())
        
        st.error(f"💥 Error saving analysis: {str(e)}")
        if DEBUG_MODE:
            st.code(f"Debug: {type(e).__name__}", language="python")

def display_analysis_results_xxx(comparison, tender_id, official_estimate, competitor_bids, 
                             procurement_type, risk_tolerance, division, district, thana,
                             tender_title, procuring_entity):
    """Display analysis results and save options"""
    
    st.markdown("---")
    st.markdown("## 🆚 Three-Tier Analysis Comparison")
    
    # Create comparison table
    comparison_data = []
    for tier, result in comparison.items():
        comparison_data.append({
            'Analysis Type': tier.upper(),
            'Method': result['method'],
            'Optimal Bid': f"BDT {result['optimal_bid']:,.0f}",
            '% of Estimate': f"{result['bid_ratio']*100:.1f}%",
            'Win Probability': f"{result['win_probability']*100:.0f}%",
            'Confidence': f"{result.get('confidence_score', 0.70)*100:.0f}%",
            'Risk': f"{result['risk_color']} {result['risk_level']}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # Detailed cards
    st.markdown("---")
    st.markdown("### 📊 Detailed Analysis by Tier")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        basic = comparison['basic']
        st.markdown(f"""
        <div style="background: #f0f0f0; padding: 1rem; border-radius: 10px; height: 100%;">
            <h3 style="text-align: center;">🔬 Basic Analysis</h3>
            <hr>
            <p><strong>Optimal Bid:</strong> BDT {basic['optimal_bid']:,.0f}</p>
            <p><strong>Win Probability:</strong> {basic['win_probability']*100:.0f}%</p>
            <p><strong>Risk:</strong> {basic['risk_color']} {basic['risk_level']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        advanced = comparison['advanced']
        st.markdown(f"""
        <div style="background: #e3f2fd; padding: 1rem; border-radius: 10px; height: 100%;">
            <h3 style="text-align: center;">📊 Advanced (PPR 2025)</h3>
            <hr>
            <p><strong>Optimal Bid:</strong> BDT {advanced['optimal_bid']:,.0f}</p>
            <p><strong>Win Probability:</strong> {advanced['win_probability']*100:.0f}%</p>
            <p><strong>Risk:</strong> {advanced['risk_color']} {advanced['risk_level']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        enhanced = comparison['enhanced']
        st.markdown(f"""
        <div style="background: #e8f5e9; padding: 1rem; border-radius: 10px; height: 100%;">
            <h3 style="text-align: center;">🧠 Enhanced (ML)</h3>
            <hr>
            <p><strong>Optimal Bid:</strong> BDT {enhanced['optimal_bid']:,.0f}</p>
            <p><strong>Win Probability:</strong> {enhanced['win_probability']*100:.0f}%</p>
            <p><strong>Risk:</strong> {enhanced['risk_color']} {enhanced['risk_level']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Best recommendation
    best_tier = max(comparison.keys(), key=lambda t: comparison[t].get('confidence_score', 0) * comparison[t]['win_probability'])
    best_result = comparison[best_tier]
    
    st.markdown("---")
    st.markdown("### 💡 AI Recommendation")
    
    if best_tier == 'enhanced':
        st.success(f"🎯 **Recommended: Enhanced (ML) Analysis** - Highest confidence ({comparison['enhanced'].get('confidence_score', 0.80)*100:.0f}%) and most accurate win probability prediction")
    elif best_tier == 'advanced':
        st.info(f"📊 **Recommended: Advanced (PPR 2025) Analysis** - Compliant with government procurement rules")
    else:
        st.warning(f"🔬 **Recommended: Basic Analysis** - Use for quick estimates, but consider upgrading for better accuracy")
    
    st.info(f"**Suggested Bid:** BDT {best_result['optimal_bid']:,.0f} ({best_result['bid_ratio']*100:.1f}% of estimate)")
    
    # ==================== SAVE BUTTON WITH CONSOLE DEBUGGING ====================

   
    if st.button("💾 Save Analysis to History", use_container_width=True, type="primary"):
        try:
            
            logging.info("SAVE BUTTON CLICKED")
            logging.warning("TEST WARNING")    
            st.info("🚀 Save button clicked")

            logger.info("SAVE BUTTON CLICKED")
            st.info("CLICKED")
            logger.info("CLICKED")
            print("CLICKED PRINT", flush=True)    
            official_est = analysis_record['official_estimate']
            competitor_bids_json = json.dumps(competitor_bids)

            logging.info(f"Tender: {analysis_record['tender_id']}")
            logging.info(f"Best bid: {best_result['optimal_bid']}")

            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO tender_analyses (
                user_id, company_id, tender_id, tender_title, procuring_entity,
                division, district, thana, construction_type, official_estimate,
                recommended_bid, success_probability, risk_level, competitor_count,
                analysis_type, competitor_bids, risk_strategy, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                st.session_state.user_id,
                st.session_state.company_id,
                analysis_record['tender_id'],
                analysis_record['tender_title'],
                analysis_record['procuring_entity'],
                analysis_record['division'],
                analysis_record.get('district', ''),
                analysis_record.get('thana', ''),
                analysis_record['construction_type'],
                official_est,
                best_result['optimal_bid'],
                best_result['win_probability'],
                best_result['risk_level'],
                len(competitor_bids),
                f"{best_tier.upper()} Analysis",
                competitor_bids_json,
                risk_tolerance,
                best_result.get('confidence_score', 0.75)
            ))

            analysis_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"SAVED! ID: {analysis_id}")

            st.success(f"✅ Saved! ID: {analysis_id}")

        except Exception as e:
            logger.exception("ERROR saving analysis")
            st.error(str(e))


    
    # Download results
    export_df = pd.DataFrame(comparison_data)
    csv = export_df.to_csv(index=False)
    st.download_button("📥 Download Comparison Results (CSV)", csv, 
                      f"tender_analysis_{tender_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                      "text/csv")
    
    # PPR Metrics Display
    st.markdown("---")
    st.markdown("## 📈 PPR 2025 Compliance Metrics")
    
    # Calculate PPR metrics
    nppi_factor = 0.920
    nppi_price = official_estimate * nppi_factor
    
    # Get competitor bids
    if competitor_bids:
        avg_competitor = np.mean(competitor_bids)
        competitor_prices = competitor_bids[:5]  # Use first 5 competitors for calculation
    else:
        avg_competitor = official_estimate * 0.91
        competitor_prices = [official_estimate * 0.88, official_estimate * 0.90, official_estimate * 0.92, official_estimate * 0.94, official_estimate * 0.95]
    
    # Weighted Average
    term1 = 0.5 * avg_competitor
    term2 = 0.2 * official_estimate
    term3 = 0.3 * nppi_price
    weighted_avg = term1 + term2 + term3
    
    # Weighted Standard Deviation
    squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
    sum_sq_dev = sum(squared_deviations)
    n = len(competitor_prices)
    variance = sum_sq_dev / n if n > 0 else 0
    weighted_std = np.sqrt(variance)
    
    # SLT Threshold
    slt_threshold = weighted_avg - weighted_std
    
    # Best bid from analysis
    best_bid = best_result['optimal_bid']
    is_slt = best_bid < slt_threshold
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("NPPI Factor", f"{nppi_factor:.3f}")
        st.caption("Market index from last 28 days")
    
    with col2:
        st.metric("NPPI Price", f"BDT {nppi_price:,.0f}")
        st.caption(f"= {official_estimate:,.0f} × {nppi_factor:.3f}")
    
    with col3:
        st.metric("Weighted Average (X̄)", f"BDT {weighted_avg:,.0f}")
        st.caption("0.5(Avg) + 0.2(Est) + 0.3(NPPI)")
    
    with col4:
        st.metric("SLT Threshold", f"BDT {slt_threshold:,.0f}")
        st.caption("X̄ - Sd")
    
    # Bid evaluation
    st.markdown("---")
    st.markdown("### ✅ Bid Evaluation")
    
    if is_slt:
        st.error(f"🚨 **SLT RISK:** Your recommended bid of BDT {best_bid:,.0f} is BELOW the SLT threshold of BDT {slt_threshold:,.0f}")
        st.warning("**PPR 2025 Clause 49.3:** Bids below the SLT threshold are considered Significantly Low-priced Tenders and may be rejected.")
    else:
        st.success(f"✅ **PPR Compliant:** Your recommended bid of BDT {best_bid:,.0f} is ABOVE the SLT threshold of BDT {slt_threshold:,.0f}")
        st.info("This bid meets PPR 2025 requirements and is not considered an SLT.")
    
    # Detailed calculation
    with st.expander("📊 View Detailed PPR 2025 Calculation", expanded=False):
        st.markdown("#### Step 1: Competitor Analysis")
        st.write(f"- Number of Competitors: {len(competitor_prices)}")
        st.write(f"- Average Competitor Bid: BDT {avg_competitor:,.0f}")
        st.write(f"- Competitor Bids: {', '.join([f'BDT {b:,.0f}' for b in competitor_prices[:5]])}")
        
        st.markdown("#### Step 2: Weighted Average (X̄)")
        st.write(f"X̄ = 0.5 × {avg_competitor:,.0f} + 0.2 × {official_estimate:,.0f} + 0.3 × {nppi_price:,.0f}")
        st.write(f"X̄ = {term1:,.0f} + {term2:,.0f} + {term3:,.0f} = {weighted_avg:,.0f}")
        
        st.markdown("#### Step 3: Weighted Standard Deviation (Sd)")
        st.write(f"Sd = √[ Σ (X̄ - Xi)² / n ]")
        for i, (price, sq) in enumerate(zip(competitor_prices[:5], squared_deviations[:5]), 1):
            st.write(f"  Competitor {i}: ({weighted_avg:,.0f} - {price:,.0f})² = {sq:,.0f}")
        st.write(f"Sum of squares: {sum_sq_dev:,.0f}")
        st.write(f"Variance: {sum_sq_dev:,.0f} / {n} = {variance:,.0f}")
        st.write(f"Sd = √{variance:,.0f} = {weighted_std:,.0f}")
        
        st.markdown("#### Step 4: SLT Threshold")
        st.write(f"SLT Threshold = X̄ - Sd = {weighted_avg:,.0f} - {weighted_std:,.0f} = {slt_threshold:,.0f}")
        
        st.markdown("#### Step 5: Bid Evaluation")
        st.write(f"Recommended Bid: BDT {best_bid:,.0f}")
        st.write(f"SLT Threshold: BDT {slt_threshold:,.0f}")
        st.write(f"Result: {'BELOW' if is_slt else 'ABOVE'} SLT Threshold")

def tender_analysis_page():
    """Three-Tier Tender Analysis with search and auto-populate"""
    
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Three-Tier Bid Optimization</h1>
        <p>Compare Basic, Advanced (PPR 2025), and Enhanced (ML) analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Ensure admin has premium access
    ensure_admin_premium()
    
    sub = db.get_user_subscription(st.session_state.user_id)
    is_premium = sub.get('plan') in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    # Import location database
    from modules.bangladesh_locations import DIVISIONS, get_districts, get_upazilas
    
    # Initialize session state for selected tender
    if 'selected_tender_for_analysis' not in st.session_state:
        st.session_state.selected_tender_for_analysis = None
    if 'last_analysis_comparison' not in st.session_state:
        st.session_state.last_analysis_comparison = None
    if 'last_analysis_record' not in st.session_state:
        st.session_state.last_analysis_record = None
    if 'last_saved_analysis_id' not in st.session_state:
        st.session_state.last_saved_analysis_id = None
    
    # Tender Selection Section
    st.markdown("### 📋 Tender Selection")
    
    # Get existing tenders
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, tender_id, tender_title, procuring_entity, official_estimate, submission_deadline,
        procurement_type, division, district, thana, tender_security, document_fee, evaluation_type
    FROM company_tenders 
    WHERE company_id = ? 
    ORDER BY created_at DESC
    ''', (st.session_state.company_id,))
    all_tenders = cursor.fetchall()
    conn.close()
    
    # Search and Filter Section
    st.markdown("#### 🔍 Search & Filter Tenders")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("Search by Tender ID or Title", placeholder="Enter tender ID or title...", key="search_term_input")
    
    with col2:
        filter_type = st.selectbox("Filter by Type", ["All", "works", "goods", "services"], key="filter_type_select")
    
    with col3:
        filter_division = st.selectbox("Filter by Division", ["All"] + DIVISIONS, key="filter_division_select")
    
    # Filter tenders
    filtered_tenders = []
    tender_map = {}
    for tender in all_tenders:
        if search_term:
            if search_term.lower() not in str(tender[1]).lower() and search_term.lower() not in str(tender[2]).lower():
                continue
        if filter_type != "All" and tender[6] != filter_type:
            continue
        if filter_division != "All" and tender[7] != filter_division:
            continue
        filtered_tenders.append(tender)
        tender_map[tender[0]] = {
            'id': tender[0],
            'tender_id': tender[1],
            'tender_title': tender[2],
            'procuring_entity': tender[3],
            'official_estimate': float(tender[4]) if tender[4] else 0,
            'submission_deadline': tender[5],
            'procurement_type': tender[6] or "works",
            'division': tender[7] or "Dhaka",
            'district': tender[8] or "",
            'thana': tender[9] or "",
            'tender_security': float(tender[10]) if tender[10] else 0,
            'document_fee': float(tender[11]) if tender[11] else 0,
            'evaluation_type': tender[12] or "Lot wise"
        }
    
    # Create selection dropdown
    if filtered_tenders:
        tender_display_list = []
        tender_display_to_id = {}
        
        for tender in filtered_tenders:
            try:
                estimate_value = float(tender[4]) if tender[4] else 0
                display_text = f"{tender[1]} - {tender[2][:40]}... (BDT {estimate_value:,.0f})"
            except:
                display_text = f"{tender[1]} - {tender[2][:40]}..."
            
            tender_display_list.append(display_text)
            tender_display_to_id[display_text] = tender[0]
        
        all_options = ["-- Create New Tender --"] + tender_display_list
        
        # Find current selection
        current_index = 0
        if st.session_state.selected_tender_for_analysis:
            for display_text, tid in tender_display_to_id.items():
                if tid == st.session_state.selected_tender_for_analysis.get('id'):
                    current_index = all_options.index(display_text)
                    break
        
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_display = st.selectbox(
                "Select Tender",
                options=all_options,
                index=current_index,
                key="tender_select_display"
            )
        
        with col2:
            if st.button("➕ New Tender", use_container_width=True):
                st.session_state.selected_tender_for_analysis = None
                st.rerun()
        
        # Handle selection change
        if selected_display != "-- Create New Tender --":
            new_selected_id = tender_display_to_id.get(selected_display)
            if new_selected_id and (not st.session_state.selected_tender_for_analysis or st.session_state.selected_tender_for_analysis.get('id') != new_selected_id):
                st.session_state.selected_tender_for_analysis = tender_map[new_selected_id]
                st.rerun()
        else:
            if st.session_state.selected_tender_for_analysis is not None:
                st.session_state.selected_tender_for_analysis = None
                st.rerun()
    
    else:
        st.info("No tenders found matching your criteria. Click 'New Tender' to create one.")
        if st.button("➕ Create New Tender", use_container_width=True):
            st.session_state.selected_tender_for_analysis = None
            st.rerun()
    
    # Set default values from selected tender or empty
    if st.session_state.selected_tender_for_analysis:
        tender_data = st.session_state.selected_tender_for_analysis
        default_tender_id = tender_data.get('tender_id', '')
        default_tender_title = tender_data.get('tender_title', '')
        default_procuring_entity = tender_data.get('procuring_entity', '')
        default_division = tender_data.get('division', 'Dhaka')
        default_district = tender_data.get('district', '')
        default_thana = tender_data.get('thana', '')
        default_official_estimate = tender_data.get('official_estimate', 0)
        default_submission_deadline = tender_data.get('submission_deadline', datetime.now())
        default_tender_security = tender_data.get('tender_security', 0)
        default_document_fee = tender_data.get('document_fee', 0)
        default_procurement_type = tender_data.get('procurement_type', 'works')
        default_evaluation_type = tender_data.get('evaluation_type', 'Lot wise')
        
        st.info(f"📋 Loaded Tender: {default_tender_id} - {default_tender_title[:80]}...")
    else:
        default_tender_id = ""
        default_tender_title = ""
        default_procuring_entity = ""
        default_division = "Dhaka"
        default_district = ""
        default_thana = ""
        default_official_estimate = 0
        default_submission_deadline = datetime.now()
        default_tender_security = 0
        default_document_fee = 0
        default_procurement_type = "works"
        default_evaluation_type = "Lot wise"
    
    # Main Input Form
    with st.form(key="tender_analysis_form"):
        st.markdown("### 📝 Tender Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            tender_id = st.text_input("Tender ID*", value=default_tender_id)
            tender_title = st.text_area("Tender Title*", value=default_tender_title, height=60)
            procuring_entity = st.text_input("Procuring Entity*", value=default_procuring_entity)
        
        with col2:
            division_index = DIVISIONS.index(default_division) if default_division in DIVISIONS else 0
            division = st.selectbox("Division", DIVISIONS, index=division_index)
            
            districts = get_districts(division)
            district_index = districts.index(default_district) if default_district in districts else 0
            district = st.selectbox("District", districts, index=district_index)
            
            upazilas = get_upazilas(district)
            if upazilas:
                thana_index = upazilas.index(default_thana) if default_thana in upazilas else 0
                thana = st.selectbox("Thana/Upazila", upazilas, index=thana_index)
            else:
                thana = st.text_input("Thana/Upazila", value=default_thana)
        
        st.markdown("### 💰 Financial Information")
        col1, col2 = st.columns(2)
        
        with col1:
            official_estimate = st.number_input("Official Estimate (BDT)*", min_value=0, value=int(default_official_estimate), step=1000000, format="%d")
            tender_security = st.number_input("Tender Security (BDT)", min_value=0, value=int(default_tender_security), step=10000, format="%d")
        
        with col2:
            procurement_type_index = ["works", "goods", "services"].index(default_procurement_type) if default_procurement_type in ["works", "goods", "services"] else 0
            procurement_type = st.selectbox("Procurement Type", ["works", "goods", "services"], index=procurement_type_index)
            document_fee = st.number_input("Document Fee (BDT)", min_value=0, value=int(default_document_fee), step=500, format="%d")
        
        st.markdown("### 👥 Competitor Bids")
        
        bid_source = st.radio("Bid Source", ["Auto-generate realistic bids", "Enter manually"], horizontal=True)
        
        competitor_bids = []
        
        if bid_source == "Enter manually":
            st.markdown("#### Enter Competitor Bids")
            
            competitors = db.get_competitor_master_list(st.session_state.company_id)
            competitor_options = {c[1]: c[0] for c in competitors} if competitors else {}
            
            if 'analysis_competitor_bids' not in st.session_state:
                st.session_state.analysis_competitor_bids = []
            
            num_competitors = st.number_input("Number of competitors", min_value=0, max_value=20, value=max(3, len(st.session_state.analysis_competitor_bids)))
            
            for idx, comp_entry in enumerate(st.session_state.analysis_competitor_bids):
                with st.container():
                    st.markdown(f"**Competitor {idx+1}**")
                    col_a, col_b, col_c = st.columns([2.5, 2, 1])
                    with col_a:
                        st.text(f"{comp_entry['name']}")
                    with col_b:
                        new_bid = st.number_input(f"Bid Amount", value=float(comp_entry['bid']), step=1000000.0, format="%.0f", key=f"form_edit_bid_{idx}")
                        comp_entry['bid'] = new_bid
                    with col_c:
                        was_winner = st.checkbox(f"Winner?", value=comp_entry.get('was_winner', False), key=f"form_edit_winner_{idx}")
                        comp_entry['was_winner'] = was_winner
                    st.markdown("---")
            
            with st.expander("➕ Add Competitor", expanded=False):
                if competitor_options:
                    col_a, col_b, col_c = st.columns([2, 2, 1])
                    with col_a:
                        selected_comp = st.selectbox("Select Competitor", [""] + list(competitor_options.keys()), key="form_new_comp")
                    with col_b:
                        new_bid = st.number_input("Bid Amount", min_value=0, step=1000000.0, format="%.0f", key="form_new_comp_bid", value=float(official_estimate * 0.90) if official_estimate > 0 else 0)
                    with col_c:
                        is_winner = st.checkbox("Winner?", key="form_new_comp_winner")
                    
                    if st.button("Add to List"):
                        if selected_comp and new_bid > 0:
                            existing_names = [c['name'] for c in st.session_state.analysis_competitor_bids]
                            if selected_comp in existing_names:
                                st.warning(f"{selected_comp} already added!")
                            else:
                                st.session_state.analysis_competitor_bids.append({
                                    'name': selected_comp,
                                    'bid': new_bid,
                                    'was_winner': is_winner
                                })
                                st.rerun()
                else:
                    st.warning("No competitors in master list. Please add competitors first.")
                    if st.button("Go to Competitor Master"):
                        st.session_state.page = "competitor_master"
                        st.rerun()
            
            competitor_bids = [c['bid'] for c in st.session_state.analysis_competitor_bids]
            
            if st.session_state.analysis_competitor_bids:
                st.markdown("**📊 Current Competitors Summary:**")
                for c in st.session_state.analysis_competitor_bids:
                    winner_text = "🏆 WINNER" if c['was_winner'] else ""
                    st.caption(f"- {c['name']}: BDT {c['bid']:,.0f} {winner_text}")
                
                if st.button("🗑️ Clear All Competitors"):
                    st.session_state.analysis_competitor_bids = []
                    st.rerun()
        
        else:
            num_competitors = st.slider("Number of competitors", min_value=3, max_value=15, value=7)
            
            if 'analysis_competitor_bids' in st.session_state:
                st.session_state.analysis_competitor_bids = []
            
            np.random.seed(hash(str(tender_id) + str(official_estimate)) % 2**32)
            base_percentages = np.random.uniform(0.85, 0.98, num_competitors)
            variations = np.random.uniform(-0.03, 0.03, num_competitors)
            final_percentages = np.clip(base_percentages + variations, 0.80, 1.00)
            competitor_bids = [official_estimate * p for p in final_percentages]
            
            st.info(f"✅ Generated {num_competitors} realistic competitor bids")
            preview_df = pd.DataFrame({
                'Competitor': [f"Bidder {i+1}" for i in range(num_competitors)],
                'Bid Amount': [f"BDT {b:,.0f}" for b in competitor_bids],
                '% of Estimate': [f"{b/official_estimate*100:.1f}%" for b in competitor_bids]
            })
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
        
        st.markdown("### 🎯 Risk Strategy")
        risk_tolerance = st.select_slider("Risk Tolerance", options=['aggressive', 'moderate', 'conservative'], value='moderate')
        
        submitted = st.form_submit_button("🚀 Run Three-Tier Analysis", type="primary", use_container_width=True)
    
    # Process analysis when submitted
    if submitted:
        logger = logging.getLogger(__name__)
        logger.info("Analysis BUTTON CLICKED")
        if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
            st.error("Please fill all required fields (marked with *)")
        elif not competitor_bids:
            st.error("Please add competitor bids (either auto-generate or enter manually)")
        else:
            with st.spinner("Running Three-Tier Analysis..."):
                # Run all three analyses
                from modules.advanced_bid_optimizer import get_three_tier_comparison
                
                comparison = get_three_tier_comparison(
                    official_estimate=official_estimate,
                    competitor_bids=competitor_bids,
                    procurement_type=procurement_type,
                    risk_tolerance=risk_tolerance,
                    company_id=st.session_state.company_id
                )
                
                best_result = None
                best_tier = None
                for tier, result in comparison.items():
                    if best_result is None or result.get('confidence_score', 0) * result['win_probability'] > best_result.get('confidence_score', 0) * best_result['win_probability']:
                        best_result = result
                        best_tier = tier

                
                st.session_state.saved_comparison = comparison
                st.session_state.saved_analysis_record = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'division': division,
                    'district': district,
                    'thana': thana,
                    'construction_type': procurement_type,
                    'official_estimate': official_estimate,
                    'competitor_bids': competitor_bids,
                    'risk_tolerance': risk_tolerance
                }
                st.session_state.saved_best_result = best_result
                st.session_state.saved_best_tier = best_tier
                st.session_state.saved_competitor_bids = competitor_bids
                st.session_state.saved_risk_tolerance = risk_tolerance
                st.session_state.analysis_ready_to_save = True


                analysis_record_for_display = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'division': division,
                    'district': district,
                    'thana': thana,
                    'construction_type': procurement_type,
                    'official_estimate': official_estimate
                }
                
                # Display results
                display_analysis_results_with_report(comparison, analysis_record_for_display, competitor_bids, risk_tolerance)


def display_analysis_results_with_report(comparison, analysis_record, competitor_bids, risk_tolerance):
    """
    Display analysis results in tabbed format with save and PDF generation.
    
    Args:
        comparison: Dict of tier -> result dict
        analysis_record: Dict with tender details
        competitor_bids: List of competitor bid amounts
        risk_tolerance: User's risk tolerance string
    """
    debug_print(f"\n📊 Rendering analysis display | Tiers: {list(comparison.keys())}")
    
    # =============================================================================
    # 🛡️ SESSION STATE PROTECTION: Only set if we have valid NEW data
    # =============================================================================
    # This prevents overwriting session state with None/empty values on rerun
    if analysis_record and comparison:
        debug_print("💾 Updating session state with fresh analysis data")
        
        # Find best result (single calculation)
        best_result = None
        best_tier = None
        for tier, result in comparison.items():
            score = result.get('confidence_score', 0) * result.get('win_probability', 0)
            current_best_score = (best_result.get('confidence_score', 0) * best_result.get('win_probability', 0) 
                                 if best_result else -1)
            if score > current_best_score:
                best_result = result
                best_tier = tier
        
        # Store in session state for save callback
        st.session_state.current_analysis_record = analysis_record
        st.session_state.current_best_result = best_result
        st.session_state.current_best_tier = best_tier
        st.session_state.current_competitor_bids = competitor_bids
        st.session_state.current_risk_tolerance = risk_tolerance
        st.session_state.current_comparison = comparison
        
        debug_print(f"✓ Session state updated | Best tier: {best_tier}")
    
    # =============================================================================
    # 📋 BUILD COMPARISON TABLE
    # =============================================================================
    st.markdown("---")
    st.markdown("## 🆚 Three-Tier Analysis Comparison")
    
    comparison_data = []
    
    # Use comparison from session state if params are empty (rerun scenario)
    active_comparison = comparison if comparison else st.session_state.get('current_comparison', {})
    
    for tier, result in active_comparison.items():
        comparison_data.append({
            'Analysis Type': tier.upper(),
            'Method': result.get('method', 'N/A'),
            'Optimal Bid': f"BDT {result.get('optimal_bid', 0):,.0f}",
            '% of Estimate': f"{result.get('bid_ratio', 0)*100:.1f}%",
            'Win Probability': f"{result.get('win_probability', 0)*100:.0f}%",
            'Confidence': f"{result.get('confidence_score', 0.70)*100:.0f}%",
            'Risk': f"{result.get('risk_color', '⚪')} {result.get('risk_level', 'Unknown')}"
        })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        debug_print(f"✓ Displayed comparison table with {len(comparison_df)} rows")
    else:
        st.warning("⚠️ No comparison data available")
        debug_print("⚠️ No data to display in comparison table")
    
    # =============================================================================
    # 💡 AI RECOMMENDATION SECTION
    # =============================================================================
    st.markdown("---")
    st.markdown("### 💡 AI Recommendation")
    
    best_result = st.session_state.get('current_best_result')
    best_tier = st.session_state.get('current_best_tier')
    
    if best_result and best_tier:
        if best_tier == 'enhanced':
            st.success(f"🎯 **Recommended: Enhanced (ML) Analysis** - Highest confidence ({best_result.get('confidence_score', 0.80)*100:.0f}%)")
        elif best_tier == 'advanced':
            st.info(f"📊 **Recommended: Advanced (PPR 2025) Analysis** - Compliant with government procurement rules")
        else:
            st.warning(f"🔬 **Recommended: Basic Analysis** - Use for quick estimates")
        
        optimal_bid = best_result.get('optimal_bid', 0)
        bid_ratio = best_result.get('bid_ratio', 0)
        st.info(f"**Suggested Bid:** BDT {optimal_bid:,.0f} ({bid_ratio*100:.1f}% of estimate)")
        debug_print(f"✓ Displayed recommendation: {best_tier} @ BDT {optimal_bid:,.0f}")
    else:
        st.warning("⚠️ Run analysis first to see recommendations")
    
    # =============================================================================
    # 💾 SAVE BUTTON SECTION (Callback Pattern)
    # =============================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Check if data is available before enabling save
        has_valid_data = (
            st.session_state.get('current_analysis_record') is not None and
            st.session_state.get('current_best_result') is not None
        )
        
        save_clicked = st.button(
            "💾 Save Analysis to History", 
            key="save_analysis_btn", 
            use_container_width=True, 
            type="primary",
            disabled=not has_valid_data,  # Disable if no data
            on_click=_save_analysis_callback  # ← CALLBACK PATTERN
        )
        
        if not has_valid_data:
            st.caption("🔒 Run analysis first to enable saving")
        elif DEBUG_MODE:
            st.caption("🐛 Debug mode active")
    
    # =============================================================================
    # 🔄 OPTIONAL: Show recently saved status
    # =============================================================================
    if st.session_state.get('last_saved_analysis_id'):
        saved_id = st.session_state.last_saved_analysis_id
        saved_tender = st.session_state.get('last_saved_tender_id', 'Unknown')
        st.success(f"✨ Last saved: Analysis #{saved_id} for Tender {saved_tender}")
    
    debug_print("✅ Display function completed\n")
    
    # Download CSV
    if analysis_record and analysis_record.get('tender_id'):
        export_df = pd.DataFrame(comparison_data)
        csv = export_df.to_csv(index=False)
        st.download_button(
            "📥 Download Comparison Results (CSV)", 
            csv, 
            f"tender_analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "text/csv"
        )
    else:
        st.warning("Analysis data not available for download")

    
    # ==================== FINALIZE BID SUBMISSION ====================
    
    if st.session_state.get('last_saved_analysis_id'):
        st.markdown("---")
        st.markdown("### 📝 Finalize Bid Submission")
        st.warning("⚠️ Once marked as FINAL, this analysis cannot be deleted. This is the bid you submitted to e-GP.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            final_bid_amount = st.number_input(
                "Enter Final Bid Amount Submitted to e-GP",
                value=float(best_result['optimal_bid']),
                step=100000.0,
                format="%.0f",
                help="This is the actual bid amount you submitted to the e-GP system"
            )
            
            if st.button("✅ Mark as Final Submitted Bid", width='stretch', type="primary"):
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Update the saved analysis as FINAL
                cursor.execute('''
                UPDATE tender_analyses 
                SET final_submitted_bid = ?, is_final_submitted = 1, bid_status = 'submitted'
                WHERE id = ?
                ''', (final_bid_amount, st.session_state.last_saved_analysis_id))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Bid of BDT {final_bid_amount:,.0f} marked as FINAL SUBMITTED to e-GP!")
                st.balloons()
                st.session_state.last_saved_analysis_id = None
                st.rerun()    
    
    # ==================== TABBED DETAILED VIEW ====================
    
    st.markdown("---")
    st.markdown("### 🔍 Detailed Analysis View")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tender Info", "🎯 Analysis Results", "📈 PPR Metrics", "📄 Report"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📋 Basic Information")
            st.markdown(f"""
            - **Tender ID:** {analysis_record.get('tender_id', 'N/A')}
            - **Tender Title:** {analysis_record.get('tender_title', 'N/A')}
            - **Procuring Entity:** {analysis_record.get('procuring_entity', 'N/A')}
            - **Construction Type:** {analysis_record.get('construction_type', 'N/A')}
            - **Division:** {analysis_record.get('division', 'N/A')}
            - **District:** {analysis_record.get('district', 'N/A')}
            - **Thana:** {analysis_record.get('thana', 'N/A')}
            """)
        
        with col2:
            st.markdown("#### 📅 Analysis Details")
            st.markdown(f"""
            - **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            - **Analysis Type:** {best_tier.upper()}
            - **Risk Strategy:** {risk_tolerance.upper()}
            - **Number of Competitors:** {len(competitor_bids)}
            - **Bid Status:** {'Submitted' if st.session_state.get('last_saved_analysis_id') else 'Draft'}
            """)
            
            if st.session_state.get('last_saved_analysis_id'):
                st.success(f"✅ Analysis ID: {st.session_state.last_saved_analysis_id} (Saved)")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 Bid Analysis")
            official_est = analysis_record['official_estimate']
            rec_bid = best_result['optimal_bid']
            
            st.markdown(f"""
            - **Official Estimate:** BDT {official_est:,.0f}
            - **Recommended Bid:** BDT {rec_bid:,.0f}
            - **Bid Ratio:** {rec_bid / official_est * 100:.1f}% of estimate
            - **Win Probability:** {best_result['win_probability']*100:.0f}%
            - **Risk Level:** {best_result['risk_color']} {best_result['risk_level']}
            - **Confidence Score:** {best_result.get('confidence_score', 0.75)*100:.0f}%
            """)
            
            # Gauge chart for win probability
            win_prob = best_result['win_probability'] * 100
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=win_prob,
                title={'text': "Win Probability (%)"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkgreen"},
                       'steps': [
                           {'range': [0, 33], 'color': "lightgray"},
                           {'range': [33, 66], 'color': "gray"},
                           {'range': [66, 100], 'color': "lightgreen"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75, 'value': win_prob}}))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Financial Metrics")
            estimated_cost = official_est * 0.85
            expected_profit = rec_bid - estimated_cost
            expected_value = expected_profit * best_result['win_probability']
            st.markdown(f"""
            - **Estimated Cost:** BDT {estimated_cost:,.0f}
            - **Expected Profit:** BDT {expected_profit:,.0f}
            - **Expected Value:** BDT {expected_value:,.0f}
            """)
            
            # Risk meter
            risk_level = best_result['risk_level']
            risk_colors = {'LOW': 'green', 'MEDIUM': 'orange', 'HIGH': 'red', 'MEDIUM-HIGH': 'darkorange', 'MEDIUM-LOW': 'yellowgreen'}
            risk_color = risk_colors.get(risk_level, 'gray')
            
            st.markdown(f"""
            <div style="background: {risk_color}20; padding: 1rem; border-radius: 10px; border-left: 4px solid {risk_color};">
                <b>Risk Assessment:</b> {risk_level}<br>
                <small>Based on bid ratio and market conditions</small>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("#### 📈 PPR 2025 Compliance Metrics")
        
        official_est = analysis_record['official_estimate']
        rec_bid = best_result['optimal_bid']
        
        # NPPI Calculation Details
        st.markdown("##### 📊 NPPI (National Public Procurement Price Index) Calculation")
        st.markdown("**PPR 2025 Clause 49.4 - 49.5:** NPPI is the national average percentage deviation...")
        
        nppi_factor = 0.920
        nppi_price = official_est * nppi_factor
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("NPPI Factor", f"{nppi_factor:.3f}")
        with col2:
            st.metric("NPPI Price", f"BDT {nppi_price:,.0f}")
            st.caption(f"= {official_est:,.0f} × {nppi_factor:.3f}")
        with col3:
            deviation = (nppi_factor - 1) * 100
            st.metric("Market Deviation", f"{deviation:+.1f}%")
        
        st.markdown("---")
        
        # Step 1: Competitor Analysis
        st.markdown("##### Step 1: Competitor Bid Analysis")
        
        if competitor_bids:
            competitor_prices = competitor_bids[:5]
            avg_competitor = np.mean(competitor_prices)
        else:
            competitor_prices = [official_est * 0.88, official_est * 0.90, official_est * 0.92, official_est * 0.94, official_est * 0.95]
            avg_competitor = np.mean(competitor_prices)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Number of Competitors", len(competitor_bids) if competitor_bids else 5)
            st.metric("Average Competitor Bid", f"BDT {avg_competitor:,.0f}")
        with col2:
            st.metric("Lowest Competitor Bid", f"BDT {min(competitor_prices):,.0f}")
            st.metric("Highest Competitor Bid", f"BDT {max(competitor_prices):,.0f}")
        
        # Display competitor table
        comp_table_data = []
        for i, price in enumerate(competitor_prices, 1):
            comp_table_data.append({"Competitor": f"Bidder {i}", "Bid Amount": f"BDT {price:,.0f}", "% of Estimate": f"{price/official_est*100:.1f}%"})
        st.dataframe(pd.DataFrame(comp_table_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Step 2: Weighted Average Calculation (X̄)
        st.markdown("##### Step 2: Weighted Average (X̄) Calculation")
        term1 = 0.5 * avg_competitor
        term2 = 0.2 * official_est
        term3 = 0.3 * nppi_price
        weighted_avg = term1 + term2 + term3
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Term 1 (50%)", f"BDT {term1:,.0f}")
        with col2:
            st.metric("Term 2 (20%)", f"BDT {term2:,.0f}")
        with col3:
            st.metric("Term 3 (30%)", f"BDT {term3:,.0f}")
        
        st.info(f"**X̄ = {term1:,.0f} + {term2:,.0f} + {term3:,.0f} = {weighted_avg:,.0f}**")
        
        st.markdown("---")
        
        # Step 3: Weighted Standard Deviation (Sd)
        st.markdown("##### Step 3: Weighted Standard Deviation (Sd) Calculation")
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
        sum_sq_dev = sum(squared_deviations)
        n = len(competitor_prices)
        variance = sum_sq_dev / n if n > 0 else 0
        weighted_std = np.sqrt(variance)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sum of (X̄ - Xi)²", f"{sum_sq_dev:,.0f}")
        with col2:
            st.metric("Number of Competitors (n)", n)
        with col3:
            st.metric("Variance", f"{variance:,.0f}")
        
        st.info(f"**Sd = √({sum_sq_dev:,.0f} / {n}) = √{variance:.0f} = {weighted_std:,.0f}**")
        
        st.markdown("---")
        
        # Step 4: SLT Threshold
        st.markdown("##### Step 4: SLT Threshold Calculation")
        slt_threshold = weighted_avg - weighted_std
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Weighted Average (X̄)", f"BDT {weighted_avg:,.0f}")
        with col2:
            st.metric("Weighted Std Dev (Sd)", f"BDT {weighted_std:,.0f}")
        
        st.info(f"**SLT Threshold = {weighted_avg:,.0f} - {weighted_std:,.0f} = {slt_threshold:,.0f}**")
        
        st.markdown("---")
        
        # Step 5: Bid Evaluation
        st.markdown("##### Step 5: Bid Evaluation")
        is_slt = rec_bid < slt_threshold
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Recommended Bid", f"BDT {rec_bid:,.0f}")
        with col2:
            st.metric("SLT Threshold", f"BDT {slt_threshold:,.0f}")
        
        if is_slt:
            st.error(f"🚨 **SLT RISK:** Your bid of BDT {rec_bid:,.0f} is BELOW the SLT threshold")
        else:
            st.success(f"✅ **Compliant:** Your bid of BDT {rec_bid:,.0f} is ABOVE the SLT threshold")
    
    with tab4:
        st.markdown("#### 📄 Report Download")
        
        # Check if we have a saved analysis to generate PDF
        if st.session_state.get('last_saved_analysis_id'):
            st.info(f"✅ Analysis ID {st.session_state.last_saved_analysis_id} is ready for PDF report.")
            
            if st.button("📑 Generate PDF Report", use_container_width=True, type="primary"):
                with st.spinner("Generating PDF report..."):
                    try:
                        from modules.pdf_generator import generate_analysis_report
                        
                        user_info = {
                            'full_name': st.session_state.get('full_name', 'N/A'),
                            'company_name': st.session_state.get('company_name', 'N/A'),
                            'role': st.session_state.get('user_role', 'N/A'),
                            'email': st.session_state.get('user_email', 'N/A')
                        }
                        
                        # Get the saved analysis data
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                        SELECT * FROM tender_analyses WHERE id = ?
                        ''', (st.session_state.last_saved_analysis_id,))
                        saved_record = cursor.fetchone()
                        conn.close()
                        
                        if saved_record:
                            # Convert to dict for report generation
                            columns = [description[0] for description in cursor.description] if cursor.description else []
                            record_dict = dict(zip(columns, saved_record)) if columns else {}
                            
                            pdf_buffer = generate_analysis_report(record_dict, user_info)
                            
                            st.download_button(
                                label="💾 Download PDF Report",
                                data=pdf_buffer,
                                file_name=f"Tender_Analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            st.success("✅ PDF Report ready for download!")
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
        else:
            st.info("💾 Please save the analysis first, then generate the PDF report.")

# ==================== SIDEBAR ====================

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🏗️ TenderAI")
        st.markdown("---")
        
        if not st.session_state.logged_in:
            # Public navigation
            menu = {
                "🏠 Home": "home", 
                "💰 Pricing": "pricing", 
                "ℹ️ About": "about", 
                "📞 Contact": "contact", 
                "🔐 Login": "login"
            }
            for label, page in menu.items():
                if st.button(label, key=page, use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
        else:
            # Logged in user info
            st.markdown(f"### 👋 {st.session_state.full_name}")
            st.markdown(f"🏢 {st.session_state.company_name}")
            st.markdown(f"⭐ {st.session_state.user_role}")
            
            # Check premium status
            sub = db.get_user_subscription(st.session_state.user_id)
            is_premium_user = sub.get('plan') in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
            prem_text = "✨ PREMIUM" if is_premium_user else "🔓 FREE"
            st.markdown(f"💳 {prem_text}")
            st.markdown("---")
            
            # Main Menu
            st.markdown("### Main Menu")
            main_menu = {
                "📊 Dashboard": "dashboard", 
                "🎯 Analysis": "new_analysis", 
                "📜 History": "history", 
                "👤 Profile": "profile", 
                "💳 Subscription": "subscription"
            }
            for label, page in main_menu.items():
                if st.button(label, key=page, use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
            
            # Management Menu (Company Admin only)
            if is_admin() or is_company_admin():
                st.markdown("---")
                st.markdown("### 👥 Management")
                if st.button("👥 User Management", key="user_mgmt", use_container_width=True):
                    st.session_state.page = "user_management"
                    st.rerun()
                if st.button("📋 Tender Management", key="tender_mgmt", use_container_width=True):
                    st.session_state.page = "tender_management"
                    st.rerun()
                if is_admin() or is_company_admin():
                    st.markdown("---")
                    st.markdown("### 📊 Evaluation")
                    if st.button("📋 Post Evaluation", key="post_eval", use_container_width=True):
                        st.session_state.page = "post_evaluation"
                        st.rerun()
                    if st.button("🧠 Intelligent Suggestions", key="intelligent", use_container_width=True):
                        st.session_state.page = "intelligent_suggestions"
                        st.rerun()

    
            # Data Management (Premium users only)
            if is_premium_user:
                st.markdown("---")
                st.markdown("### 📚 Data Management")
                if st.button("📊 Historical Data", key="historical_data", use_container_width=True):
                    st.session_state.page = "historical_data"
                    st.rerun()
                if st.button("📜 Analysis History", key="analysis_history", use_container_width=True):
                    st.session_state.page = "analysis_history"
                    st.rerun()
            
            # Intelligence (Premium users only)
            if is_premium_user:
                st.markdown("---")
                st.markdown("### 📊 Intelligence")
                if st.button("👥 Competitor Tracking", key="competitor_tracking", use_container_width=True):
                    st.session_state.page = "competitor_tracking"
                    st.rerun()
                if st.button("👥 Competitor Master", key="competitor_master", use_container_width=True):
                    st.session_state.page = "competitor_master"
                    st.rerun()
            
            # System Admin Menu (Admin only)
            if is_admin():
                st.markdown("---")
                st.markdown("### 👑 System Admin")
                if st.button("👑 Admin Dashboard", key="admin_dash", use_container_width=True):
                    st.session_state.page = "admin_dashboard"
                    st.rerun()
                # Add approval button with pending count badge
                try:
                    pending_count = len(db.get_pending_users(st.session_state.company_id))
                    approval_label = f"👥 User Approvals ({pending_count})" if pending_count > 0 else "👥 User Approvals"
                except:
                    approval_label = "👥 User Approvals"
                if st.button(approval_label, key="user_approval", use_container_width=True):
                    st.session_state.page = "user_approval"
                    st.rerun()

            # Logout
            st.markdown("---")
            if st.button("🚪 Logout", key="logout", use_container_width=True):
                logout_user()
                st.rerun()
print("Step 6: All page functions defined")
# Main function
def main():
    # Hide Streamlit's default navigation
    st.markdown("<style>div[data-testid='stSidebarNav']{display:none;}</style>", unsafe_allow_html=True)
    
    # Initialize session state defaults
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'show_checkout' not in st.session_state:
        st.session_state.show_checkout = False
    
    # Render sidebar
    render_sidebar()
    
    # Checkout page
    if st.session_state.get('show_checkout', False):
        render_checkout()
        return
    
    # Public pages (not logged in)
    if not st.session_state.logged_in:
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
        return
    
    # Logged in pages
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
    elif st.session_state.page == 'tender_management':
        from modules.tender_management import render_tender_management
        render_tender_management()
    elif st.session_state.page == 'post_evaluation':
        from modules.post_evaluation import render_post_evaluation_page
        render_post_evaluation_page()
    elif st.session_state.page == 'intelligent_suggestions':
        from modules.post_evaluation import render_intelligent_suggestions
        render_intelligent_suggestions()


    elif st.session_state.page == 'historical_data':
        from modules.historical_data import render_historical_data_page
        render_historical_data_page()
    elif st.session_state.page == 'analysis_history':
        from modules.analysis_history import show_analysis_history
        show_analysis_history()
    elif st.session_state.page == 'competitor_tracking':
        from modules.competitor_tracking import render_competitor_tracking_page
        render_competitor_tracking_page()
    elif st.session_state.page == 'competitor_master':
        from modules.competitor_master import render_competitor_master_page
        render_competitor_master_page()
    elif st.session_state.page == 'admin_dashboard':
        admin_dashboard_page()
    elif st.session_state.page == 'user_approval':
        from modules.user_approval import render_user_approval_page
        render_user_approval_page()
    else:
        dashboard_page()        

if __name__ == "__main__":
    print("Step 10: Running main()")
    main()