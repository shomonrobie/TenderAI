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
        </style>
        """
def get_theme_css_old():
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
        
        .stApp {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
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
        
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f8fafc 100%) !important;
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
        if st.button("Toggle Theme", key="theme_toggle_btn"):
            st.session_state.dark_mode = not st.session_state.get('dark_mode', False)
            st.rerun()
    with col2:
        if st.button("Profile", key="profile_btn"):
            st.session_state.page = "profile"
            st.rerun()
    with col3:
        if st.button("Subscription", key="subscription_btn"):
            st.session_state.page = "subscription"
            st.rerun()
    with col4:
        if st.button("Logout", key="logout_btn"):
            st.session_state.dark_mode = False
            for key in list(st.session_state.keys()):
                if key not in ['dark_mode']:
                    st.session_state.pop(key, None)
            st.session_state.logged_in = False
            st.session_state.page = "home"
            st.rerun()
    
    # 3. Render custom interactive header using components.html
    # This bypasses Streamlit's markdown sanitizer which strips onclick events
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
        }}
        .header-left {{ display: flex; align-items: center; gap: 0.75rem; }}
        .header-left h1 {{ margin: 0; font-size: 1.1rem; font-weight: 700; color: white; white-space: nowrap; }}
        .header-buttons {{ display: flex; gap: 0.25rem; }}
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
            display: flex; align-items: center; justify-content: center;
        }}
        .header-btn:hover {{ background: rgba(255, 255, 255, 0.2); }}
    </style>
    </head>
    <body>
    <div class="header-container">
        <div class="header-left">
            {logo_html}
            <h1>TenderAI - Bangladesh's First AI-Powered Tender Intelligence Platform</h1>
        </div>
        <div class="header-buttons">
            <button class="header-btn" id="btn-theme">{theme_icon}</button>
            <button class="header-btn" id="btn-profile">👤</button>
            <button class="header-btn" id="btn-subscription">💳</button>
            <button class="header-btn" id="btn-logout">🚪</button>
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
            
def render_app_header_bak():
    """Compact header with gradient background"""
    init_theme()
    is_dark = st.session_state.get('dark_mode', False)
    
    if not st.session_state.get('logged_in', False):
        # Guest header
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%); 
                    border-radius: 16px; padding: 2rem 1.5rem; margin-bottom: 2rem; text-align: center;
                    border: 1px solid rgba(102, 126, 234, 0.1); box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h1 style="font-size: 2.5rem; font-weight: 700; margin: 0; 
                       background: linear-gradient(135deg, #667eea, #764ba2);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                🏗️ TenderAI
            </h1>
            <p style="color: #94a3b8; font-size: 1.1rem; margin: 0.5rem 0 0 0;">
                Bangladesh's First AI-Powered Tender Intelligence Platform
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Logged in header
    full_name = st.session_state.get('full_name', 'User') or 'User'
    user_role = st.session_state.get('user_role', 'viewer')
    
    role_display = {
        'system_admin': '👑 System Admin',
        'admin': '👑 Admin',
        'company_admin': '🏢 Company Admin',
        'manager': '📊 Manager',
        'analyst': '📈 Analyst',
        'viewer': '👁️ Viewer'
    }.get(user_role, 'User')
    
    theme_icon = "🌙" if not is_dark else "☀️"
    
    # Wrap everything in a container with gradient background
    with st.container():
        # Apply gradient background to this container via CSS
        st.markdown("""
        <style>
        /* Target the container that wraps the header columns */
        div[data-testid="stVerticalBlock"] > div:has(> div > div > div > div > .header-gradient-container) {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
            border-radius: 16px !important;
            padding: 0.8rem 1.5rem !important;
            margin-bottom: 1.5rem !important;
            border: 1px solid rgba(102, 126, 234, 0.1) !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Style the buttons inside the header */
        div[data-testid="stVerticalBlock"] > div:has(> div > div > div > div > .header-gradient-container) .stButton > button {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 6px !important;
            padding: 0.3rem 0.7rem !important;
            font-size: 0.75rem !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
            min-width: 40px !important;
        }
        
        div[data-testid="stVerticalBlock"] > div:has(> div > div > div > div > .header-gradient-container) .stButton > button:hover {
            background: rgba(255, 255, 255, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        
        /* Make the column containing the user card have proper alignment */
        div[data-testid="stVerticalBlock"] > div:has(> div > div > div > div > .header-gradient-container) .stColumn {
            display: flex;
            align-items: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Add a marker div so CSS can target the container
        st.markdown('<div class="header-gradient-container" style="display: none;"></div>', unsafe_allow_html=True)
        
        # Create the header layout
        col1, col2, col3 = st.columns([2.2, 1.2, 1])
        
        with col1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">🏗️</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #ffffff !important;">
                        Tender<span style="background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI</span>
                    </h1>
                    <p style="margin: 0; font-size: 0.75rem; color: #94a3b8 !important;">AI-Powered Tender Intelligence</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; padding: 4px 12px; 
                        background: rgba(255, 255, 255, 0.08); border-radius: 50px; 
                        border: 1px solid rgba(255, 255, 255, 0.1);">
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; 
                            width: 30px; height: 30px; border-radius: 50%; display: flex; 
                            align-items: center; justify-content: center; font-weight: bold; font-size: 0.9rem;">
                    {full_name[0].upper()}
                </div>
                <div>
                    <div style="color: #ffffff !important; font-weight: 600; font-size: 0.85rem;">{full_name}</div>
                    <div style="color: #94a3b8 !important; font-size: 0.7rem;">{role_display}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            
            with btn_col1:
                if st.button(theme_icon, key="theme_toggle", help="Toggle theme", use_container_width=True):
                    toggle_dark_mode()
            
            with btn_col2:
                if st.button("👤", key="profile_btn", help="Profile", use_container_width=True):
                    st.session_state.page = "profile"
                    st.rerun()
            
            with btn_col3:
                if st.button("💳", key="subscription_btn", help="Subscription", use_container_width=True):
                    st.session_state.page = "subscription"
                    st.rerun()
            
            with btn_col4:
                if st.button("🚪", key="logout_btn", help="Logout", use_container_width=True):
                    st.session_state.dark_mode = False
                    for key in list(st.session_state.keys()):
                        if key not in ['dark_mode']:
                            st.session_state.pop(key, None)
                    st.session_state.logged_in = False
                    st.session_state.page = "home"
                    st.rerun()
    
    st.markdown("---")
    
def apply_theme():
    """Apply theme with page-aware JavaScript"""
    is_dark = st.session_state.get('dark_mode', False)
    current_page = st.session_state.get('page', 'home')
    st.markdown(get_theme_css(), unsafe_allow_html=True)

def render_footer():
    """Render e-GP style footer with gradient matching login page"""
    try:
        from version import __version__, __version_date__
    except ImportError:
        __version__ = "1.0.0"
        __version_date__ = datetime.now().strftime("%Y")
    
    st.markdown(f"""
    <style>
    .footer {{
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
        color: #94a3b8;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 2.5rem;
        text-align: center;
        font-size: 0.82rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}
    .footer .links {{
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 10px;
        font-size: 0.78rem;
    }}
    .footer .links a {{
        color: #94a3b8;
        text-decoration: none;
        transition: color 0.3s;
    }}
    .footer .links a:hover {{
        color: #667eea;
    }}
    .footer .divider {{
        color: #2d3748;
        margin: 0 4px;
    }}
    .footer strong {{
        color: #e0e0e0;
    }}
    .footer .highlight {{
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .footer .version-info {{
        font-size: 0.7rem;
        color: #4a5568;
        margin-top: 8px;
    }}
    .footer .copyright {{
        font-size: 0.7rem;
        color: #4a5568;
        margin-top: 4px;
    }}
    </style>
    <div class="footer">
        <div class="links">
            <a href="#">Home</a>
            <span class="divider">|</span>
            <a href="#">About TenderAI</a>
            <span class="divider">|</span>
            <a href="#">Contact Us</a>
            <span class="divider">|</span>
            <a href="#">RSS Feed</a>
            <span class="divider">|</span>
            <a href="#">Terms and Conditions</a>
            <span class="divider">|</span>
            <a href="#">Service Level</a>
            <span class="divider">|</span>
            <a href="#">Disclaimer and Privacy Policy</a>
            <span class="divider">|</span>
            <a href="#">New Features</a>
        </div>
        <div style="font-size:0.7rem; color:#4a5568; margin-bottom:6px;">
            Best viewed in 1024 x 768 and above resolution. 
            Microsoft Edge 109.x or above and Mozilla Firefox 113.x or above and Google Chrome 109.x or above
        </div>
        <div class="copyright">
            Copyright © 2011 Bangladesh Public Procurement Authority (BPPA). All Rights Reserved.
        </div>
        <div class="version-info">
            <span class="highlight">TenderAI</span> v{__version__} • {__version_date__} • 
            Powered by <span class="highlight">Copyright © 2024 Bangladesh's First AI-Powered Tender Intelligence Platform</span>
        </div>
    
    </div>
    """, unsafe_allow_html=True)


def render_footer_bak():
    """Render footer with gradient matching login page"""
    try:
        from version import __version__, __version_date__
    except ImportError:
        __version__ = "1.0.0"
        __version_date__ = datetime.now().strftime("%Y")
    
    st.markdown(f"""
    <style>
    .footer {{
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
        color: #94a3b8;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 2.5rem;
        text-align: center;
        font-size: 0.88rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}
    .footer strong {{
        color: #e0e0e0;
    }}
    .footer .highlight {{
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    </style>
    <div class="footer">
        🏗️ <strong>TenderAI</strong> v{__version__} • {__version_date__} • 
        <span class="highlight">Bangladesh's First AI-Powered Tender Intelligence Platform</span>
    </div>
    """, unsafe_allow_html=True)