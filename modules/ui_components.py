# modules/ui_components.py

import streamlit as st
import hashlib
from datetime import datetime
import streamlit.components.v1 as components
from pathlib import Path
import base64
def init_theme():
    """Initialize theme settings"""
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

def toggle_dark_mode():
    """Toggle between dark and light mode"""
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()
def get_theme_css():
    """Return global theme CSS"""
    is_dark = st.session_state.get('dark_mode', False)
    
    if is_dark:
        return """
        <style>
        /* Dark Theme */
        :root {
            --bg-primary: #0a0a1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #1e1e2a;
            --text-primary: #e0e0e0;
            --text-secondary: #94a3b8;
            --border-color: #2a2a35;
            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
        }
        
        /* Force background on all Streamlit containers */
        .stApp, 
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stAppViewContainer"] > .main .block-container,
        section[data-testid="stSidebar"],
        header[data-testid="stHeader"],
        footer[data-testid="stFooter"] {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
            background-color: #0a0a1a !important;
        }
        
        .stMarkdown, h1, h2, h3, h4, h5, h6, p, span, div, label {
            color: var(--text-primary) !important;
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%) !important;
            border-right: 1px solid var(--border-color);
        }
        
        .stTabs [data-baseweb="tab"] {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
            color: white !important;
            border-color: transparent;
        }
        
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select,
        .stTextArea > div > div > textarea {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: var(--accent-primary) !important;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
        }
        
        .stButton > button {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4) !important;
        }
        
        .streamlit-expanderHeader {
            background: rgba(255, 255, 255, 0.03) !important;
            border-radius: 8px !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
        }
        
        .stDataFrame, .dataframe {
            background: var(--bg-card) !important;
            color: var(--text-primary) !important;
        }
        
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
        }
        
        .stAlert {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
        }
        
        .stCheckbox label {
            color: var(--text-secondary) !important;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--accent-primary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-secondary);
        }
        </style>
        """
    else:
        return """
        <style>
        /* Light Theme */
        :root {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
        }
        
        /* Force background on all Streamlit containers */
        .stApp, 
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stAppViewContainer"] > .main .block-container,
        section[data-testid="stSidebar"],
        header[data-testid="stHeader"],
        footer[data-testid="stFooter"] {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f8fafc 100%) !important;
            background-color: #f8fafc !important;
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%) !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: #f1f5f9;
            border-radius: 8px;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
            color: white !important;
        }
        
        .stButton > button {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3) !important;
        }
        .btn-with-tip {
            position: relative;
            display: inline-block;
            width: 100%;
            margin-bottom: 30px;
        }
        
        .btn-with-tip .tip {
            visibility: hidden;
            background: #1e293b;
            color: #e2e8f0;
            text-align: center;
            padding: 6px 12px;
            border-radius: 6px;
            position: absolute;
            z-index: 1;
            bottom: -30px;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.7rem;
            white-space: nowrap;
            border: 1px solid #334155;
        }
        
        .btn-with-tip .tip::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-bottom-color: #1e293b;
        }
        
        .btn-with-tip:hover .tip {
            visibility: visible;
            opacity: 1;
        }
        </style>

                """

def render_app_header():
    """Gradient header with working buttons using components.html"""
    
    if not st.session_state.get('logged_in', False):        
        return
    
    # Logged in header data
    full_name = st.session_state.get('full_name', 'User') or 'User'
    user_role = st.session_state.get('user_role', 'viewer')
    role_display = {
        'system_admin': '👑 System Admin', 'admin': '👑 Admin',
        'company_admin': '🏢 Company Admin', 'manager': '📊 Manager',
        'analyst': '📈 Analyst', 'viewer': '👁️ Viewer'
    }.get(user_role, 'User')
    is_dark = st.session_state.get('dark_mode', False)
    theme_icon = "🌙" if not is_dark else "☀️"
    
    # Logo
    try:
        logo_path = Path("assets/images/tender_ai_logo_50x50.png")
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
                logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 35px; width: auto;">'
        else:
            logo_html = '<span style="font-size: 1.8rem;">🏗️</span>'
    except:
        logo_html = '<span style="font-size: 1.8rem;">🏗️</span>'
    
    # 1. Hide native Streamlit buttons off-screen
    st.markdown("""
    <style>
    .st-key-theme_toggle_btn, .st-key-profile_btn, .st-key-subscription_btn, .st-key-logout_btn {
        position: absolute !important; left: -9999px !important; top: -9999px !important;
        visibility: hidden !important; width: 0 !important; height: 0 !important; overflow: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 2. Create hidden native buttons (these handle the actual logic)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Toggle Theme", key="theme_toggle_btn", help="Toggle between light and dark mode"):
            st.session_state.dark_mode = not st.session_state.get('dark_mode', False)
            st.rerun()
    with col2:
        if st.button("Profile", key="profile_btn", help="View and edit your profile settings"):
            st.session_state.page = "profile"
            st.rerun()
    with col3:
        if st.button("Subscription", key="subscription_btn", help="Manage your subscription plan"):
            st.session_state.page = "subscription"
            st.rerun()
    with col4:
        if st.button("Logout", key="logout_btn", help="Log out of your account"):
            print("=" * 60)
            print("🚪 LOGOUT BUTTON CLICKED")
            print("=" * 60)
            
            # Clear dark mode preference
            st.session_state.dark_mode = False
            
            # 1. Clear app session state
            print("🔍 Clearing app session state...")
            keys_to_pop = list(st.session_state.keys())
            for key in keys_to_pop:
                if key not in ['dark_mode']:
                    st.session_state.pop(key, None)
                    print(f"   Removed: {key}")
            
            # 2. Clear OIDC session using Streamlit's logout
            print("🔍 Clearing OIDC session...")
            try:
                if hasattr(st, 'logout'):
                    print("   Calling st.logout()...")
                    st.logout()
                    print("   ✅ st.logout() called successfully")
                else:
                    print("   ⚠️ st.logout() not available")
                    
                # Also try to clear st.user if it exists
                if hasattr(st, 'user'):
                    print("   st.user exists, clearing...")
                    # st.user is read-only, but we can clear session
            except Exception as e:
                print(f"   ❌ Error in st.logout(): {e}")
            
            # 3. Clear any OIDC-related session state
            print("🔍 Clearing OIDC-related session state...")
            oidc_keys = ['google_user_info', 'show_google_registration', 'google_registration_mode']
            for key in oidc_keys:
                if key in st.session_state:
                    st.session_state.pop(key, None)
                    print(f"   Removed: {key}")
            
            # 4. Clear query params
            print("🔍 Clearing query params...")
            st.query_params.clear()
            print("   ✅ Query params cleared")
            
            # 5. Set logged_in to False and page to login
            st.session_state.logged_in = False
            st.session_state.page = "login"
            
            print("✅ Logout complete")
            print(f"   logged_in: {st.session_state.get('logged_in')}")
            print(f"   page: {st.session_state.get('page')}")
            print("=" * 60)
            
            # 6. Rerun the app
            st.rerun()
    
    # 3. Render custom interactive header using components.html
    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; background: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .header-container {{
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%);
            border-radius: 12px;
            padding: 0.5rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid rgba(102, 126, 234, 0.1);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            box-sizing: border-box;
            position: relative;
            min-height: 60px;
        }}
        .header-left {{ display: flex; align-items: center; gap: 0.75rem; }}
        .header-left h1 {{ margin: 0; font-size: 1.1rem; font-weight: 700; color: white; white-space: nowrap; }}
        .header-buttons {{ display: flex; gap: 0.25rem; position: relative; }}
        
        /* Button styling */
        .header-btn {{
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 0.3rem 0.6rem;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        .header-btn:hover {{ 
            background: rgba(255, 255, 255, 0.2);
        }}
        
        /* ===== FIXED TOOLTIP - BELOW BUTTON ===== */
        .header-btn .tooltip-text {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            top: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.7rem;
            white-space: nowrap;
            z-index: 1000;
            pointer-events: none;
            transition: all 0.25s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            border: 1px solid rgba(102, 126, 234, 0.2);
            font-weight: 400;
            letter-spacing: 0.2px;
        }}
        
        /* Tooltip arrow (pointing up to button) */
        .header-btn .tooltip-text::before {{
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-bottom-color: rgba(0, 0, 0, 0.9);
        }}
        
        /* Show tooltip on hover */
        .header-btn:hover .tooltip-text {{
            visibility: visible;
            opacity: 1;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 768px) {{
            .header-left h1 {{ font-size: 0.8rem; }}
            .header-btn {{ padding: 0.2rem 0.4rem; font-size: 0.65rem; min-width: 30px; }}
            .header-btn .tooltip-text {{ 
                font-size: 0.6rem; 
                padding: 4px 8px;
                top: calc(100% + 6px);
            }}
        }}
    </style>
    </head>
    <body>
    <div class="header-container">
        <div class="header-left">
            {logo_html}
            <h1>TenderAI - Bangladesh's First AI-Powered Tender Intelligence Platform</h1>
        </div>
        <div class="header-buttons">
            <button class="header-btn" id="btn-theme">
                {theme_icon}
                <span class="tooltip-text">Toggle theme (Dark/Light)</span>
            </button>
            <button class="header-btn" id="btn-profile">
                👤
                <span class="tooltip-text">View and edit your profile</span>
            </button>
            <button class="header-btn" id="btn-subscription">
                💳
                <span class="tooltip-text">Manage your subscription plan</span>
            </button>
            <button class="header-btn" id="btn-logout">
                🚪
                <span class="tooltip-text">Log out of your account</span>
            </button>
        </div>
    </div>
    <script>
        function clickStreamlitButton(key) {{
            const btn = window.parent.document.querySelector('.st-key-' + key + ' button');
            if (btn) btn.click();
        }}
        document.getElementById('btn-theme').onclick = function() {{ clickStreamlitButton('theme_toggle_btn'); }};
        document.getElementById('btn-profile').onclick = function() {{ clickStreamlitButton('profile_btn'); }};
        document.getElementById('btn-subscription').onclick = function() {{ clickStreamlitButton('subscription_btn'); }};
        document.getElementById('btn-logout').onclick = function() {{ clickStreamlitButton('logout_btn'); }};
    </script>
    </body>
    </html>
    """, height=70)

def apply_theme():
    """Apply theme with page-aware JavaScript"""
    is_dark = st.session_state.get('dark_mode', False)
    current_page = st.session_state.get('page', 'home')
    st.markdown(get_theme_css(), unsafe_allow_html=True)


def render_footer():
    """Render e-GP style footer with gradient matching login page"""
    try:
        from version import __version__, __version_date__
    except (ImportError, ModuleNotFoundError):
        __version__ = "1.0.0"
        __version_date__ = datetime.now().strftime("%Y")
    except Exception:
        __version__ = "1.0.0"
        __version_date__ = datetime.now().strftime("%Y")
    
    try:
        current_year = datetime.now().strftime("%Y")
    except Exception:
        current_year = "2024"
    
    # Use st.html for cleaner HTML rendering (Streamlit 1.35+)
    footer_html = f"""
    <div style="
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%);
        color: #94a3b8;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 2.5rem;
        text-align: center;
        font-size: 0.82rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div style="
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 10px;
            font-size: 0.78rem;
        ">
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">Home</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">About TenderAI</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">Contact Us</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">RSS Feed</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">Terms and Conditions</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">Service Level</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">Disclaimer and Privacy Policy</a>
            <span style="color: #2d3748;">|</span>
            <a href="#" style="color: #94a3b8; text-decoration: none; transition: color 0.3s;">New Features</a>
        </div>
        
        <div style="font-size:0.7rem; color:#4a5568; margin-bottom:6px;">
            Best viewed in 1024 x 768 and above resolution. 
            Microsoft Edge 109.x or above and Mozilla Firefox 113.x or above and Google Chrome 109.x or above
        </div>
        
        <div style="font-size: 0.7rem; color: #4a5568; margin-top: 8px;">
            <span style="
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: bold;
            ">TenderAI</span> 
            v{__version__} • {__version_date__} • 
            Powered by <span style="
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: bold;
            ">Copyright © {current_year} Bangladesh's First AI-Powered Tender Intelligence Platform</span>
        </div>
    </div>
    """
    
    # Use st.html if available (Streamlit 1.35+)
    try:
        st.html(footer_html)
    except AttributeError:
        # Fallback to st.markdown with unsafe_allow_html
        st.markdown(footer_html, unsafe_allow_html=True)