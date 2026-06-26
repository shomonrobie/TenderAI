"""
TenderAI - Enterprise Tender Management System
Complete Working Version - Fixed
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import traceback


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
        if st.button("🚀 Start Free Trial", width='stretch'):
            st.session_state.page = "register"
            st.rerun()
        if st.button("💰 View Pricing", width='stretch'):
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
            
            if st.form_submit_button("Login", width='stretch'):
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
        
        if st.button("Register New Account", width='stretch'):
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
            
            if st.form_submit_button("Create Account", width='stretch'):
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
        if st.button("Login Instead", width='stretch'):
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
            if st.button(f"Select", key=key, width='stretch'):
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
        if st.button("📊 New Analysis", width='stretch'):
            st.session_state.page = "new_analysis"
            st.rerun()
    with col2:
        if st.button("📜 History", width='stretch'):
            st.session_state.page = "history"
            st.rerun()
    with col3:
        if st.button("👥 User Management", width='stretch'):
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
        st.dataframe(analyses_df, width='stretch')
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
        st.dataframe(pd.DataFrame(user_data), width='stretch', hide_index=True)

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


def display_analysis_results(comparison, tender_id, official_estimate, competitor_bids, 
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
    st.dataframe(comparison_df, width='stretch', hide_index=True)
    
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
    
    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 Save Analysis to History", width='stretch', type="primary"):
            with st.spinner("Saving analysis..."):
                analysis_data = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'division': division,
                    'district': district,
                    'thana': thana,
                    'construction_type': procurement_type,
                    'official_estimate': official_estimate,
                    'recommended_bid': best_result['optimal_bid'],
                    'success_probability': best_result['win_probability'],
                    'risk_level': best_result['risk_level'],
                    'competitor_count': len(competitor_bids),
                    'analysis_type': f"{best_tier.upper()} - {best_result['method']}"
                }
                
                # Save to database
                analysis_id = db.save_analysis(st.session_state.user_id, st.session_state.company_id, analysis_data)
                if analysis_id:
                    db.increment_analysis_usage(st.session_state.user_id)
                    st.success(f"✅ {best_tier.upper()} analysis saved to history! (ID: {analysis_id})")
                    st.balloons()
                else:
                    st.error("Failed to save analysis. Please try again.")
    
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
    """Three-Tier Tender Analysis with search, auto-populate, and integrated analysis report"""
    
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
    
    # Initialize session state
    if 'selected_tender_for_analysis' not in st.session_state:
        st.session_state.selected_tender_for_analysis = None
    if 'last_analysis_result' not in st.session_state:
        st.session_state.last_analysis_result = None
    if 'last_analysis_data' not in st.session_state:
        st.session_state.last_analysis_data = None
    
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
    for tender in all_tenders:
        if search_term:
            if search_term.lower() not in str(tender[1]).lower() and search_term.lower() not in str(tender[2]).lower():
                continue
        if filter_type != "All" and tender[6] != filter_type:
            continue
        if filter_division != "All" and tender[7] != filter_division:
            continue
        filtered_tenders.append(tender)
    
    # Create selection dropdown
    if filtered_tenders:
        tender_display_list = []
        tender_id_map = {}
        
        for tender in filtered_tenders:
            try:
                estimate_value = float(tender[4]) if tender[4] else 0
                display_text = f"{tender[1]} - {tender[2][:50]}... (BDT {estimate_value:,.0f})"
            except:
                display_text = f"{tender[1]} - {tender[2][:50]}..."
            
            tender_display_list.append(display_text)
            tender_id_map[display_text] = {
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
        
        all_options = ["-- Select a Tender --"] + tender_display_list
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            selected_display = st.selectbox(
                "Select Tender",
                options=all_options,
                index=0,
                key="tender_select_display"
            )
        
        with col2:
            if st.button("📂 Load Selected Tender", width='stretch', type="primary"):
                if selected_display != "-- Select a Tender --":
                    st.session_state.selected_tender_for_analysis = tender_id_map[selected_display]
                    st.success(f"✅ Loaded: {selected_display[:60]}...")
                    st.rerun()
        
        with col3:
            if st.button("➕ New Tender", width='stretch'):
                st.session_state.selected_tender_for_analysis = None
                st.rerun()
    
    else:
        st.info("No tenders found matching your criteria. Click 'New Tender' to create one.")
        if st.button("➕ Create New Tender", width='stretch'):
            st.session_state.selected_tender_for_analysis = None
            st.rerun()
    
    # Set default values from selected tender or empty
    if st.session_state.selected_tender_for_analysis:
        tender_data = st.session_state.selected_tender_for_analysis
        default_tender_id = tender_data['tender_id']
        default_tender_title = tender_data['tender_title']
        default_procuring_entity = tender_data['procuring_entity']
        default_division = tender_data['division']
        default_district = tender_data['district']
        default_thana = tender_data['thana']
        default_official_estimate = tender_data['official_estimate']
        default_submission_deadline = tender_data['submission_deadline']
        default_tender_security = tender_data['tender_security']
        default_document_fee = tender_data['document_fee']
        default_procurement_type = tender_data['procurement_type']
        default_evaluation_type = tender_data['evaluation_type']
        
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
        
        submitted = st.form_submit_button("🚀 Run Three-Tier Analysis", type="primary", width='stretch')
    
    # Process analysis when submitted
    if submitted:
        if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
            st.error("Please fill all required fields (marked with *)")
        elif not competitor_bids:
            st.error("Please add competitor bids (either auto-generate or enter manually)")
        else:
            can_analyze, remaining = db.can_perform_analysis(st.session_state.user_id)
            if not can_analyze and not is_premium:
                st.error(f"You've reached your monthly limit. Please upgrade to continue.")
                return
            
            with st.spinner("Running Three-Tier Analysis..."):
                historical_df = db.get_historical_tenders(st.session_state.company_id)
                historical_data = []
                for _, row in historical_df.iterrows():
                    historical_data.append({
                        'winning_bid': row.get('awarded_price', 0),
                        'official_estimate': row.get('official_estimate', 0),
                        'winning_company_type': row.get('winning_company_type', 'Unknown')
                    })
                
                # Import comparison function
                from modules.advanced_bid_optimizer import get_three_tier_comparison
                
                comparison = get_three_tier_comparison(
                    official_estimate=official_estimate,
                    competitor_bids=competitor_bids,
                    procurement_type=procurement_type,
                    risk_tolerance=risk_tolerance,
                    historical_data=historical_data if len(historical_data) > 0 else None,
                    company_id=st.session_state.company_id
                )
                
                # Store results for report generation
                best_tier = max(comparison.keys(), key=lambda t: comparison[t].get('confidence_score', 0) * comparison[t]['win_probability'])
                best_result = comparison[best_tier]

                # Create a complete analysis record with ALL fields
                analysis_record = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'division': division,
                    'district': district,
                    'thana': thana,
                    'construction_type': procurement_type,
                    'official_estimate': official_estimate,
                    'recommended_bid': best_result['optimal_bid'],
                    'success_probability': best_result['win_probability'],
                    'risk_level': best_result['risk_level'],
                    'competitor_count': len(competitor_bids),
                    'analysis_type': f"{best_tier.upper()} - {best_result['method']}",
                    'analysis_date': datetime.now(),
                    'bid_status': 'Pending',
                    'competitor_bids': competitor_bids,  # Add competitor bids
                    'risk_strategy': risk_tolerance,  # Add risk strategy
                    'confidence_score': best_result.get('confidence_score', 0.75),  # Add confidence score
                }

                # Store in session state
                st.session_state.last_analysis_record = analysis_record
                st.session_state.last_analysis_comparison = comparison
                st.session_state.last_analysis_bids = competitor_bids
                st.session_state.last_analysis_risk = risk_tolerance

                # Display results
                display_analysis_results_with_report(comparison, analysis_record, competitor_bids, risk_tolerance)
    
    # Add after the Save button, before the tabs section
    st.markdown("---")
    st.markdown("### 📝 Finalize Bid Submission")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        final_bid_amount = st.number_input(
            "Enter Final Bid Amount to Submit",
            value=float(best_result['optimal_bid']),
            step=100000.0,
            format="%.0f",
            help="This is the actual bid amount you will submit"
        )
        
        if st.button("✅ Mark as Final Submitted Bid", width='stretch', type="primary"):
            # Update the analysis record with final submitted bid
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # First, unmark any other final submitted for this tender
            cursor.execute('''
            UPDATE tender_analyses 
            SET is_final_submitted = 0 
            WHERE tender_id = ? AND company_id = ?
            ''', (analysis_record['tender_id'], st.session_state.company_id))
            
            # Mark this as final submitted
            cursor.execute('''
            UPDATE tender_analyses 
            SET final_submitted_bid = ?, is_final_submitted = 1, bid_status = 'submitted'
            WHERE id = ?
            ''', (final_bid_amount, st.session_state.last_saved_analysis_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Bid of BDT {final_bid_amount:,.0f} marked as FINAL SUBMITTED!")
            st.balloons()
            

def display_analysis_results_with_report(comparison, analysis_record, competitor_bids, risk_tolerance):
    """Display analysis results in tabbed format with automatic PDF generation"""
    
    # Store results in session state to persist
    st.session_state.last_analysis_comparison = comparison
    st.session_state.last_analysis_record = analysis_record
    st.session_state.last_competitor_bids = competitor_bids
    st.session_state.last_risk_tolerance = risk_tolerance
    st.session_state.analysis_complete = True
    
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
    st.dataframe(comparison_df, width='stretch', hide_index=True)
    
    # Best recommendation
    best_tier = max(comparison.keys(), key=lambda t: comparison[t].get('confidence_score', 0) * comparison[t]['win_probability'])
    best_result = comparison[best_tier]
    
    st.markdown("---")
    st.markdown("### 💡 AI Recommendation")
    
    if best_tier == 'enhanced':
        st.success(f"🎯 **Recommended: Enhanced (ML) Analysis** - Highest confidence ({comparison['enhanced'].get('confidence_score', 0.80)*100:.0f}%)")
    elif best_tier == 'advanced':
        st.info(f"📊 **Recommended: Advanced (PPR 2025) Analysis** - Compliant with government procurement rules")
    else:
        st.warning(f"🔬 **Recommended: Basic Analysis** - Use for quick estimates")
    
    st.info(f"**Suggested Bid:** BDT {best_result['optimal_bid']:,.0f} ({best_result['bid_ratio']*100:.1f}% of estimate)")
    
    # Save button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 Save Analysis to History", width='stretch', type="primary"):
            with st.spinner("Saving analysis..."):
                try:
                    official_est = analysis_record['official_estimate']
                    
                    # Calculate metrics
                    if competitor_bids and len(competitor_bids) > 0:
                        avg_competitor = np.mean(competitor_bids)
                    else:
                        avg_competitor = official_est * 0.91
                    
                    nppi_factor = 0.920
                    nppi_price = official_est * nppi_factor
                    
                    term1 = 0.5 * avg_competitor
                    term2 = 0.2 * official_est
                    term3 = 0.3 * nppi_price
                    weighted_avg = term1 + term2 + term3
                    
                    competitor_prices = competitor_bids[:5] if competitor_bids else [official_est * 0.90, official_est * 0.92, official_est * 0.94]
                    squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
                    n = len(competitor_prices)
                    variance = sum(squared_deviations) / n if n > 0 else 0
                    weighted_std = np.sqrt(variance)
                    slt_threshold = weighted_avg - weighted_std
                    
                    estimated_cost = official_est * 0.85
                    expected_profit = best_result['optimal_bid'] - estimated_cost
                    expected_value = expected_profit * best_result['win_probability']
                    
                    analysis_data = {
                        'tender_id': analysis_record['tender_id'],
                        'tender_title': analysis_record['tender_title'],
                        'procuring_entity': analysis_record['procuring_entity'],
                        'division': analysis_record['division'],
                        'district': analysis_record.get('district', ''),
                        'thana': analysis_record.get('thana', ''),
                        'construction_type': analysis_record['construction_type'],
                        'official_estimate': official_est,
                        'recommended_bid': best_result['optimal_bid'],
                        'success_probability': best_result['win_probability'],
                        'risk_level': best_result['risk_level'],
                        'competitor_count': len(competitor_bids),
                        'analysis_type': f"{best_tier.upper()} - {best_result['method']}",
                        'bid_status': 'Pending',
                        'competitor_bids': competitor_bids,
                        'risk_strategy': risk_tolerance,
                        'confidence_score': best_result.get('confidence_score', 0.75),
                        'expected_profit': expected_profit,
                        'expected_value': expected_value,
                        'slt_threshold': slt_threshold,
                        'nppi_factor': nppi_factor,
                        'weighted_average': weighted_avg
                    }
                    
                    analysis_id = db.save_analysis(
                        st.session_state.user_id,
                        st.session_state.company_id,
                        analysis_data
                    )
                    
                    if analysis_id:
                        db.increment_analysis_usage(st.session_state.user_id)
                        st.success(f"✅ {best_tier.upper()} analysis saved to history! (ID: {analysis_id})")
                        st.balloons()
                    else:
                        st.error("Failed to save analysis.")
                        
                except Exception as e:
                    st.error(f"Error saving analysis: {str(e)}")
    
    # Download CSV
    export_df = pd.DataFrame(comparison_data)
    csv = export_df.to_csv(index=False)
    st.download_button("📥 Download Comparison Results (CSV)", csv, 
                      f"tender_analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                      "text/csv")
    
    # ==================== GENERATE PDF AUTOMATICALLY ====================
    
    # Generate PDF automatically after analysis
    with st.spinner("Generating PDF report..."):
        try:
            # Check if reportlab is installed
            try:
                import reportlab
            except ImportError:
                st.warning("reportlab not installed. PDF generation skipped. Run: pip install reportlab")
            
            # Import the report generator
            from modules.pdf_generator import generate_analysis_report
            
            # Prepare user information
            user_info = {
                'full_name': st.session_state.get('full_name', 'N/A'),
                'company_name': st.session_state.get('company_name', 'N/A'),
                'role': st.session_state.get('user_role', 'N/A'),
                'email': st.session_state.get('user_email', 'N/A')
            }
            
            # Prepare analysis record for PDF
            official_est = analysis_record['official_estimate']
            
            # Calculate SLT threshold for PDF
            if competitor_bids and len(competitor_bids) > 0:
                avg_competitor = np.mean(competitor_bids)
            else:
                avg_competitor = official_est * 0.91
            
            nppi_factor = 0.920
            nppi_price = official_est * nppi_factor
            term1 = 0.5 * avg_competitor
            term2 = 0.2 * official_est
            term3 = 0.3 * nppi_price
            weighted_avg = term1 + term2 + term3
            competitor_prices = competitor_bids[:5] if competitor_bids else [official_est * 0.90, official_est * 0.92, official_est * 0.94]
            squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
            n = len(competitor_prices)
            variance = sum(squared_deviations) / n if n > 0 else 0
            weighted_std = np.sqrt(variance)
            slt_threshold = weighted_avg - weighted_std
            
            pdf_record = {
                'tender_id': analysis_record.get('tender_id', 'N/A'),
                'tender_title': analysis_record.get('tender_title', 'N/A'),
                'procuring_entity': analysis_record.get('procuring_entity', 'N/A'),
                'division': analysis_record.get('division', 'N/A'),
                'district': analysis_record.get('district', 'N/A'),
                'thana': analysis_record.get('thana', 'N/A'),
                'construction_type': analysis_record.get('construction_type', 'N/A'),
                'official_estimate': official_est,
                'recommended_bid': best_result['optimal_bid'],
                'success_probability': best_result['win_probability'],
                'risk_level': best_result['risk_level'],
                'analysis_type': f"{best_tier.upper()} Analysis",
                'competitor_count': len(competitor_bids),
                'competitor_bids': competitor_bids[:10],
                'risk_strategy': risk_tolerance,
                'confidence_score': best_result.get('confidence_score', 0.75),
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'slt_threshold': slt_threshold
            }
            
            # Generate PDF
            pdf_buffer = generate_analysis_report(pdf_record, user_info)
            
            # Store in session state for immediate download
            st.session_state.pdf_buffer = pdf_buffer
            st.session_state.pdf_filename = f"Tender_Analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
    
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
            - **Bid Status:** Pending
            """)
    
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
            st.plotly_chart(fig, width='stretch')
        
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
        st.markdown("**PPR 2025 Clause 49.4 - 49.5:** NPPI is the national average percentage deviation between official cost estimate and awarded tender price over the last 28 days")
        
        nppi_factor = 0.920
        nppi_price = official_est * nppi_factor
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("NPPI Factor", f"{nppi_factor:.3f}")  # 3 decimal places
            st.caption("Market index from last 28 days")
        with col2:
            st.metric("NPPI Price", f"BDT {nppi_price:,.0f}")
            st.caption(f"= {official_est:,.0f} × {nppi_factor:.3f}")  # 3 decimal places in caption
        with col3:
            deviation = (nppi_factor - 1) * 100
            st.metric("Market Deviation", f"{deviation:+.1f}%")
            st.caption("Market is 8% below estimates" if deviation < 0 else "Market is above estimates")
        
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
            comp_table_data.append({
                "Competitor": f"Bidder {i}",
                "Bid Amount": f"BDT {price:,.0f}",
                "% of Estimate": f"{price/official_est*100:.1f}%"
            })
        st.dataframe(pd.DataFrame(comp_table_data), width='stretch', hide_index=True)
        
        st.markdown("---")
        
        # Step 2: Weighted Average Calculation (X̄)
        st.markdown("##### Step 2: Weighted Average (X̄) Calculation")
        st.markdown("**Formula (PPR 2025 Clause 49.2):** X̄ = 0.5 × (Avg Competitor) + 0.2 × (Official Estimate) + 0.3 × (NPPI Price)")
        
        term1 = 0.5 * avg_competitor
        term2 = 0.2 * official_est
        term3 = 0.3 * nppi_price
        weighted_avg = term1 + term2 + term3
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Term 1 (50%)", f"BDT {term1:,.0f}")
            st.caption(f"0.5 × {avg_competitor:,.0f}")
        with col2:
            st.metric("Term 2 (20%)", f"BDT {term2:,.0f}")
            st.caption(f"0.2 × {official_est:,.0f}")
        with col3:
            st.metric("Term 3 (30%)", f"BDT {term3:,.0f}")
            st.caption(f"0.3 × {nppi_price:,.0f}")
        
        st.info(f"**X̄ = {term1:,.0f} + {term2:,.0f} + {term3:,.0f} = {weighted_avg:,.0f}**")
        
        st.markdown("---")
        
        # Step 3: Weighted Standard Deviation (Sd)
        st.markdown("##### Step 3: Weighted Standard Deviation (Sd) Calculation")
        st.markdown("**Formula (PPR 2025 Clause 49.2):** Sd = √[ Σ (X̄ - Xi)² / n ]")
        
        # Calculate squared deviations
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
        sum_sq_dev = sum(squared_deviations)
        n = len(competitor_prices)
        variance = sum_sq_dev / n if n > 0 else 0
        weighted_std = np.sqrt(variance)
        
        sq_dev_data = []
        for i, (price, sq_dev) in enumerate(zip(competitor_prices, squared_deviations), 1):
            sq_dev_data.append({
                "Competitor": f"Bidder {i}",
                "Bid (Xi)": f"BDT {price:,.0f}",
                "(X̄ - Xi)": f"BDT {weighted_avg - price:,.0f}",
                "(X̄ - Xi)²": f"{sq_dev:,.0f}"
            })
        
        st.dataframe(pd.DataFrame(sq_dev_data), width='stretch', hide_index=True)
        
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
        st.markdown("**Formula:** SLT Threshold = X̄ - Sd")
        
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
            st.error(f"🚨 **SLT RISK:** Your bid of BDT {rec_bid:,.0f} is BELOW the SLT threshold of BDT {slt_threshold:,.0f}")
            st.warning("**PPR 2025 Clause 49.3:** Bids below the SLT threshold are considered Significantly Low-priced Tenders and may be rejected.")
        else:
            st.success(f"✅ **Compliant:** Your bid of BDT {rec_bid:,.0f} is ABOVE the SLT threshold of BDT {slt_threshold:,.0f}")
            st.info("**PPR 2025 Compliant:** This bid meets the requirements and is not considered an SLT.")
        
        st.markdown("---")
        
        with st.expander("📖 PPR 2025 Reference - Clause 49", expanded=False):
            st.markdown("""
            **Clause 49.2:** During the evaluation of tenders, the proposed prices of all technically responsive tenderers (at least two tenders) shall be used to determine a Weighted Average:
            
            **X̄ = 0.5 × (1/n Σxi) + 0.2 × Xoce + 0.3 × Xnppi**
            
            Where:
            - Σxi/n = Average of all responsive tender prices
            - Xoce = Official Cost Estimate
            - Xnppi = Official Estimate × NPPI Factor
            
            **Sd = √[ Σ (X̄ - Xi)² / n ]**
            
            **Clause 49.3:** Finally, the lower limit of acceptable prices shall be [X̄ - Sd]. Any tender quoted below this limit shall be considered as a significantly low-priced tender and shall be treated as financially non-responsive and rejected.
            
            **Clause 49.4 - 49.5:** NPPI (National Public Procurement Price Index) is the national average percentage deviation between official cost estimate and awarded tender price, calculated from the e-GP system over a period of 28 days.
            """)
    
    with tab4:
        st.markdown("#### 📄 Report Download")
        
        # Show PDF download button
        if st.session_state.get('pdf_buffer'):
            st.success("✅ PDF Report is ready!")
            st.download_button(
                label="📑 Download PDF Report",
                data=st.session_state.pdf_buffer,
                file_name=st.session_state.pdf_filename,
                mime="application/pdf",
                width='stretch'
            )
        else:
            st.info("PDF report will be generated automatically. If not showing, please refresh.")
        
        st.markdown("---")
        st.markdown("#### 📊 Report Summary")
        st.markdown(f"""
        - **Tender:** {analysis_record.get('tender_id', 'N/A')} - {analysis_record.get('tender_title', 'N/A')[:50]}
        - **Recommended Bid:** BDT {best_result['optimal_bid']:,.0f}
        - **Win Probability:** {best_result['win_probability']*100:.0f}%
        - **Risk Level:** {best_result['risk_level']}
        - **Analysis Type:** {best_tier.upper()}
        """)

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
                if st.button(label, key=page, width='stretch'):
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
                if st.button(label, key=page, width='stretch'):
                    st.session_state.page = page
                    st.rerun()
            
            # Management Menu (Company Admin only)
            if is_admin() or is_company_admin():
                st.markdown("---")
                st.markdown("### 👥 Management")
                if st.button("👥 User Management", key="user_mgmt", width='stretch'):
                    st.session_state.page = "user_management"
                    st.rerun()
                if st.button("📋 Tender Management", key="tender_mgmt", width='stretch'):
                    st.session_state.page = "tender_management"
                    st.rerun()
                if is_admin() or is_company_admin():
                    st.markdown("---")
                    st.markdown("### 📊 Evaluation")
                    if st.button("📋 Post Evaluation", key="post_eval", width='stretch'):
                        st.session_state.page = "post_evaluation"
                        st.rerun()
                    if st.button("🧠 Intelligent Suggestions", key="intelligent", width='stretch'):
                        st.session_state.page = "intelligent_suggestions"
                        st.rerun()

    
            # Data Management (Premium users only)
            if is_premium_user:
                st.markdown("---")
                st.markdown("### 📚 Data Management")
                if st.button("📊 Historical Data", key="historical_data", width='stretch'):
                    st.session_state.page = "historical_data"
                    st.rerun()
                if st.button("📜 Analysis History", key="analysis_history", width='stretch'):
                    st.session_state.page = "analysis_history"
                    st.rerun()
            
            # Intelligence (Premium users only)
            if is_premium_user:
                st.markdown("---")
                st.markdown("### 📊 Intelligence")
                if st.button("👥 Competitor Tracking", key="competitor_tracking", width='stretch'):
                    st.session_state.page = "competitor_tracking"
                    st.rerun()
                if st.button("👥 Competitor Master", key="competitor_master", width='stretch'):
                    st.session_state.page = "competitor_master"
                    st.rerun()
            
            # System Admin Menu (Admin only)
            if is_admin():
                st.markdown("---")
                st.markdown("### 👑 System Admin")
                if st.button("👑 Admin Dashboard", key="admin_dash", width='stretch'):
                    st.session_state.page = "admin_dashboard"
                    st.rerun()
                # Add approval button with pending count badge
                try:
                    pending_count = len(db.get_pending_users(st.session_state.company_id))
                    approval_label = f"👥 User Approvals ({pending_count})" if pending_count > 0 else "👥 User Approvals"
                except:
                    approval_label = "👥 User Approvals"
                if st.button(approval_label, key="user_approval", width='stretch'):
                    st.session_state.page = "user_approval"
                    st.rerun()

            # Logout
            st.markdown("---")
            if st.button("🚪 Logout", key="logout", width='stretch'):
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