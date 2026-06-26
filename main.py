"""
TenderAI - Enterprise Tender Management System
Complete Working Version - Fixed & Debug-Enabled
"""
# ====================== FIX WATCHDOG LOG SPAM ======================
import logging

logging.getLogger("watchdog").setLevel(logging.ERROR)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)

# Filter out noisy inotify messages
class NoSpamFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.msg).lower()
        return "inotify_buffer" not in msg and ".git" not in msg

logging.getLogger("watchdog.observers.inotify_buffer").addFilter(NoSpamFilter())
# ====================== END FIX ======================

import streamlit as st


# =============================================================================
# 🎨 PAGE CONFIG & STYLING
# =============================================================================
st.set_page_config(
    page_title="TenderAI - Tender Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)


import numpy as np
import pandas as pd
import plotly.graph_objects as go
import traceback
import logging
import sys
import os
import re
import json
from datetime import datetime
from typing import List, Union, Dict, Callable, Optional
import bcrypt
import reportlab  # For error reporting (e.g., Sentry)
import pdfplumber
#hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
#user_data['password'] = hashed.decode('utf-8')
import importlib  # ✅ Added for lazy imports
from contextlib import contextmanager  # ✅ For resource management
from utils.bid_generators import _generate_competitor_bids
#from modules.pdf_generator import _generate_and_download_pdf
from modules.ppr_viz import render_ppr_compliance_viz
from utils.helpers import (
    render_page_header,
    render_feature_card,
    render_pricing_card,
    render_demo_credentials,
    navigate_to,
    get_compact_css,
    format_currency_bd,
    format_percentage,
    get_bid_status_badge,
    get_risk_indicator,
    validate_password_strength,
    safe_title
)
from config import DEBUG_MODE, BID_AMOUNT_DECIMALS, BID_RATIO_DECIMALS, COST_ESTIMATE_RATIO, PPR_CONFIG, debug_print
#from modules.pdf_generator import generate_babui_detailed_report
from modules.advanced_bid_optimizer import get_three_tier_comparison

# Continue with normal app flow
# debug_print(f"🚀 App render | Page: {st.session_state.page} | Auth: {st.session_state.logged_in}")
from modules.forgot_password import render_forgot_password
from modules.reset_password import render_reset_password
from _pages.admin_dashboard import show as admin_dashboard_page
from _pages.landing_page2 import show_landing_page as landing_page
from _pages.about import show_about_page
import random
from modules.report_generator import generate_unified_report, generate_html_content_only

from modules.auth import restore_session_from_url
from version import get_version, get_full_version, get_copyright, get_app_name, get_app_desc
#from modules.tutorials import render_sidebar_tutorial
from modules.subscriber_dashboard import render_subscriber_dashboard

from modules.subscriber_dashboard import render_subscriber_dashboard
from modules.rate_crud_forms import render_rate_crud_forms
from modules.unified_import_wizard import render_unified_import_wizard
from modules.user_management import render_user_management, render_role_management
from modules.user_approval import render_user_approval_page
from modules.competitor_tracking import render_competitor_tracking_page
from modules.competitor_master import render_competitor_master_page
from modules.historical_data import render_historical_data_page
from modules.analysis_history import show_analysis_history
from modules.post_evaluation import render_post_evaluation_page, render_intelligent_suggestions
from modules.tender_management import render_tender_management
from modules.egp_boq_workspace import render_boq_workspace
from modules.tutorials import render_tutorial
from modules.boq_generator_ui import render_boq_generator
from modules.boq_admin_report import render_boq_admin_report
from modules.boq_bid_bridge import render_boq_bid_integration
from _pages.company_subscription import show as show_company_subscription
from _pages.company_dashboard import show as show_company_dashboard
from _pages.dashboard import show as dashboard_page
#from modules.navigation import render_top_navigation, render_page_header
from modules.ui_components import (
    render_app_header,      
    apply_theme, 
    init_theme,
    render_footer, get_theme_css
)
from modules.company_config import render_company_config
from modules.tender_analysis import render_tender_analysis

from modules.subscription_manager import SubscriptionManager
from modules.rbac import init_rbac

#from _pages.enhanced_company_dashboard import show as show_enhanced_company_dashboard
from _pages.extension_admin import show as show_extension_admin
from _pages.extension_usage import show as show_extension_usage
from modules.company_knowledge_repo import render_company_knowledge_repo
from _pages.company_profile_management import show as show_enhanced_company_dashboard 
if st.query_params.get("health") == "check":
    st.json({"status": "healthy", "timestamp": datetime.now().isoformat()})
    st.stop()
from _pages.login_page import show as login_page
from _pages.registration_page import show as register_page
from _pages.pricing_page import show as pricing_page
from _pages.contact_page import show as contact_page
from _pages.extension_features import show as auto_fill_extension_features
from modules.competitive_bid_simulator import render_competitive_bid_simulator_ui
from modules.company_rate_management import render_company_rate_management
from modules.company_onboarding import render_company_onboarding
from modules.bid_analysis.quick_bid_check import render_quick_bid_check
from modules.bid_analysis.advanced_bid_analysis import render_advanced_bid_analysis
from modules.bid_analysis.ai_bid_advisor import render_ai_bid_advisor
from modules.bid_analysis.competitive_intelligence import render_competitive_intelligence    
#from modules.data_management import render_data_management

# =============================================================================
# 🔧 DEBUG CONFIGURATION
# =============================================================================

def has_data(data) -> bool:
    """Safe check for None, empty list, dict, or pandas DataFrame"""
    if data is None:
        return False
    if hasattr(data, 'empty'):  # pandas DataFrame
        return not data.empty
    return len(data) > 0  # list, tuple, dict, etc.

def setup_logging():
    level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

setup_logging()
logger = logging.getLogger(__name__)



# =============================================================================
# 🗄️ DATABASE & MODULE IMPORTS
# =============================================================================
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager
from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user
from modules.subscription import render_subscription_page, render_checkout
from modules.user_management import render_user_management
from modules.subscription_plans import ensure_default_plans

# Initialize database
db = UnifiedDatabaseManager()
init_rbac()
ensure_default_plans()

# ========== START FLASK API FOR EXTENSION ==========
try:
    from api.flask_api import start_flask_api
    start_flask_api(db, port=5000)
except ImportError as e:
    print(f"⚠️ Flask API not available: {e}")
    print("Extension features will not work. Run: pip install flask flask-cors")
except Exception as e:
    print(f"⚠️ Failed to start Flask API: {e}")
# ===================================================

# # =============================================================================
# # UNIFIED MIGRATION SYSTEM - Run ONCE at startup
# # =============================================================================

# def run_unified_migrations(db):
#     """
#     Run ALL migrations in one place.
#     - Complex migrations (new tables) use the migration system
#     - Simple migrations (columns, indexes) run here (idempotent)
#     """
#     try:
#         # STEP 1: Run complex migrations from migrations folder
#         run_complex_migrations()
        
#         # STEP 2: Run simple schema fixes (always runs, idempotent)
#         run_simple_migrations(db)
        
#         return True
#     except Exception as e:
#         logger.error(f"Migration failed: {e}")
#         if DEBUG_MODE:
#             st.warning(f"⚠️ Migration error: {e}")
#         return False

# def run_complex_migrations():
#     """Run complex migrations (new tables, constraints) using migration system"""
#     try:
#         import sys
#         from pathlib import Path
        
#         # Add migrations directory to path
#         migrations_path = Path(__file__).parent / "migrations"
#         if str(migrations_path) not in sys.path:
#             sys.path.insert(0, str(migrations_path))
        
#         # Import migration manager
#         from migrations.run_migrations import MigrationManager
        
#         print("🔍 Checking for pending complex migrations...")
#         manager = MigrationManager(db.db_path)
#         success = manager.run_all_migrations()
        
#         if success:
#             print("✅ Complex migrations up to date")
#         return success
#     except ImportError as e:
#         print(f"⚠️ Migration module not found (first time run): {e}")
#         return True
#     except Exception as e:
#         print(f"⚠️ Migration check failed: {e}")
#         import traceback
#         traceback.print_exc()
#         return True

# def run_simple_migrations(db):
#     """Run simple schema fixes (add columns, indexes) - ALWAYS runs, idempotent"""
#     try:
#         conn = db.get_connection()
#         cursor = conn.cursor()
        
#         print("🔧 Running simple schema checks...")
        
#         # ========== FIX COMPANIES TABLE ==========
#         cursor.execute("PRAGMA table_info(companies)")
#         company_columns = [col[1] for col in cursor.fetchall()]
        
#         columns_to_add = {
#             'district': 'TEXT',
#             'upazila': 'TEXT', 
#             'post_code': 'TEXT',
#             'is_individual': 'BOOLEAN DEFAULT 0',
#             'status': "TEXT DEFAULT 'active'",
#             'registration_number': 'TEXT',
#             'vat_number': 'TEXT',
#             'website': 'TEXT'
#         }
        
#         for col_name, col_type in columns_to_add.items():
#             if col_name not in company_columns:
#                 try:
#                     cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}")
#                     print(f"  ✅ Added column: {col_name}")
#                 except Exception as e:
#                     print(f"  ⚠️ Could not add {col_name}: {e}")
        
#         # ========== FIX USERS TABLE ==========
#         cursor.execute("PRAGMA table_info(users)")
#         user_columns = [col[1] for col in cursor.fetchall()]
        
#         user_columns_to_add = {
#             'auth_provider': "TEXT DEFAULT 'email'",
#             'email_verified': "BOOLEAN DEFAULT 0",
#             'email_verified_at': "TIMESTAMP",
#             'verification_token': "TEXT",
#             'reset_token': "TEXT",
#             'reset_token_expires': "TIMESTAMP",
#             'specialization': "TEXT",
#             'years_experience': "INTEGER"
#         }
        
#         for col_name, col_type in user_columns_to_add.items():
#             if col_name not in user_columns:
#                 try:
#                     cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
#                     print(f"  ✅ Added column to users: {col_name}")
#                 except Exception as e:
#                     print(f"  ⚠️ Could not add {col_name} to users: {e}")
        
#         # ========== CREATE INDEXES ==========
#         indexes = [
#             "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
#             "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
#             "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token)",
#             "CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider)",
#             "CREATE INDEX IF NOT EXISTS idx_companies_is_individual ON companies(is_individual)",
#         ]
        
#         for index in indexes:
#             try:
#                 cursor.execute(index)
#                 print(f"  ✅ Index ready: {index.split('ON')[1].strip() if 'ON' in index else index}")
#             except Exception as e:
#                 # Table might not exist yet (handled by complex migrations)
#                 pass
        
#         conn.commit()
#         conn.close()
#         print("✅ Simple schema checks complete")
        
#     except Exception as e:
#         logger.error(f"Simple migration failed: {e}")
#         if DEBUG_MODE:
#             st.warning(f"⚠️ Simple migration error: {e}")

# run_unified_migrations(db)

# if 'logged_in' not in st.session_state:
#     st.session_state.logged_in = False

# print("=" * 60)
# print(f"MAIN.PY STARTING - logged_in={st.session_state.logged_in}")
# print(f"URL params at start: {dict(st.query_params)}")

# # Try to restore session from URL
# if not st.session_state.logged_in:
#     print("Attempting to restore from URL...")
#     try:
#         #from modules.auth import restore_session_from_url
#         restored = restore_session_from_url()
#         print(f"Restore result: {restored}")
#         if restored:
#             print("Session restored! User is now logged in.")
#             # Don't rerun here to avoid loop
#     except Exception as e:
#         print(f"Restore exception: {e}")
#         import traceback
#         traceback.print_exc()
# else:
#     print("Already logged in, skipping restore")

# print("=" * 60)

st.markdown(get_compact_css(), unsafe_allow_html=True)
    
# Try to import advanced optimizer
try:
    from modules.advanced_bid_optimizer import calculate_optimal_bid_ppr2025
    ADVANCED_OPTIMIZER_AVAILABLE = True
except ImportError:
    ADVANCED_OPTIMIZER_AVAILABLE = False
    debug_print("⚠️ Advanced optimizer not available - using fallback")

# Custom CSS
st.markdown("""
    <style>
        /* =========================================================================
        REMOVE WHITE GAPS - CRITICAL FIX
        ========================================================================= */
        /* Remove padding from main container */
        .main .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin-top: 0rem !important;
        }
        
        /* Remove spacing from the top of the app */
        section[data-testid="stAppViewContainer"] > .main {
            padding-top: 0rem !important;
        }
        
        /* Hide default Streamlit header */
        header[data-testid="stHeader"] {
            display: none;
        }
        
        /* Remove margin from the first element */
        .stApp > div:first-child {
            margin-top: -1rem !important;
        }
        
        /* Remove default Streamlit padding */
        .stApp {
            padding-top: 0 !important;
        }
        
        /* Remove gap from block container */
        .block-container {
            padding-top: 0 !important;
        }
        
        /* Remove spacing between elements */
        .element-container {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        /* For logged-in users, keep sidebar spacing */
        .logged-in .main .block-container {
            padding-top: 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)


def safe_markdown_vars(**kwargs) -> Dict[str, str]:
    """
    Safely convert session state values to display strings.
    Use this before any st.markdown(unsafe_allow_html=True) call.
    
    Example:
        vars = safe_markdown_vars(
            name=st.session_state.get('full_name'),
            status=st.session_state.get('subscription_status')
        )
        st.markdown(f"<p>{vars['name']} • {vars['status']}</p>", unsafe_allow_html=True)
    """
    result = {}
    for key, value in kwargs.items():
        if value is None:
            result[key] = 'N/A'
        elif isinstance(value, (int, float)):
            result[key] = f"{value:,.2f}" if isinstance(value, float) else str(value)
        else:
            result[key] = str(value).strip() or 'N/A'
    return result


def safe_iterate_df(df, default: List = None) -> List[Dict]:
    """
    Safely convert pandas DataFrame (or other types) to list of dicts for iteration.
    
    Args:
        df: DataFrame, list, dict, or None
        default: Fallback list if input is None/empty
    
    Returns:
        List of dicts ready for `for item in items:` iteration
    """
    if df is None:
        return default or []
    if hasattr(df, 'to_dict'):  # pandas DataFrame
        return df.to_dict('records')
    if isinstance(df, (list, tuple)):
        return list(df)
    if isinstance(df, dict):
        return [df]
    return default or []

# =============================================================================
# 🔑 SESSION STATE INITIALIZATION (Complete)
# =============================================================================
def initialize_session_state():
    """Initialize all required session state keys"""
    debug_print("🔑 Initializing session state...")
    
    session_defaults = {
        # Auth & User
        'logged_in': False,
        'user_id': None,
        'company_id': None,
        'user_role': None,
        'user_email': None,
        'full_name': None,
        'company_name': None,
        'subscription_plan': 'free',
        'subscription_status': 'active',
        
        # Navigation - DON'T override if already set
        'show_checkout': False,
        
        # Analysis Data
        'current_analysis_record': None,
        'current_best_result': None,
        'current_best_tier': None,
        'current_competitor_bids': [],
        'current_risk_tolerance': None,
        'current_comparison': {},
        
        # Save History
        'last_saved_analysis_id': None,
        'last_saved_tender_id': None,
        'save_triggered': False,
        
        # UI State
        'comparison_result': None,
        'analysis_complete': False,
        'debug_mode': DEBUG_MODE,
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Only set default page if not already set by callback
    if 'page' not in st.session_state:
        st.session_state.page = PageRoutes.HOME
    
    debug_print("✅ Session state initialization complete\n")


# =============================================================================
# 🔄 LAZY IMPORT HELPER (With error handling)
# =============================================================================
def _import_and_call(module_path: str, function_name: str, *args, **kwargs):
    """Lazy import with graceful error handling"""
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        return func(*args, **kwargs)
    except ImportError as e:
        debug_print(f"❌ Failed to import {module_path}.{function_name}: {e}")
        logger.error(f"Module import failed: {module_path}", exc_info=True)
        st.error(f"⚠️ Feature unavailable: {function_name.replace('_', ' ').title()}")
        return None
    except AttributeError as e:
        debug_print(f"❌ Function {function_name} not found in {module_path}: {e}")
        st.error(f"⚠️ Configuration error: {function_name}")
        return None


# =============================================================================
# 🗂️ PAGE ROUTE CONSTANTS (Complete - All Routes)
# =============================================================================

class PageRoutes:
    """Centralized page route constants to prevent typos and enable refactoring"""
    
    # ─── Public Pages (No Auth Required) ─────────────────────────────────────
    HOME = 'home'
    LOGIN = 'login'
    REGISTER = 'register'
    PRICING = 'pricing'
    ABOUT = 'about'
    CONTACT = 'contact'
    INDIVIDUAL_REGISTER = 'individual_register'
    INDIVIDUAL_LOGIN = 'individual_login'
    
    # ─── Authenticated Core Pages ────────────────────────────────────────────
    DASHBOARD = 'dashboard'
    NEW_ANALYSIS = 'new_analysis'  # ✅ Fixed - was missing or incorrect
    RATE_VIEWER = 'rate_viewer'
    HISTORY = 'history'
    PROFILE = 'profile'
    SUBSCRIPTION = 'subscription'
    FORGOT_PASSWORD = 'forgot_password'
    RESET_PASSWORD = 'reset_password'
    
    # ─── Management Pages (Company Admin+) ───────────────────────────────────
    USER_MANAGEMENT = 'user_management'
    TENDER_MANAGEMENT = 'tender_management'
    POST_EVALUATION = 'post_evaluation'
    INTELLIGENT_SUGGESTIONS = 'intelligent_suggestions'
    COMPANY_DASHBOARD = 'company_dashboard'
    EGP_BOQ_WORKSPACE = 'egp_boq_workspace'
    TUTORIAL = 'tutorial'        
    COMPANY_RATE_MANAGEMENT ='company_rate_management'
    # ─── Premium Intelligence Pages ──────────────────────────────────────────
    HISTORICAL_DATA = 'historical_data'
    ANALYSIS_HISTORY = 'analysis_history'
    COMPETITOR_TRACKING = 'competitor_tracking'
    COMPETITOR_MASTER = 'competitor_master'
    BOQ_GENERATOR = "boq_generator"
    BOQ_ADMIN_REPORT = "boq_admin_report"
    BOQ_BID_OPTIMIZER = "boq_bid_optimizer"
    BASIC_BID_OPTIMIZER = 'basic_bid_optimizer'    
    COMPETITIVE_BID_SIMULATOR = 'competitive_bid_simulator'
    QUICK_BID = "quick_bid"
    ADVANCED_BID = "advanced_bid"
    COMPETITIVE_INTEL = "competitive_intel"
    AI_ADVISOR = "ai_advisor"
    COMPANY_CONFIG = "company_config"
    TENDER_FORM = 'tender_form'  # ✅ ADD THIS NEW ROUTE

    # ─── Admin System Pages ──────────────────────────────────────────────────
    ADMIN_DASHBOARD = 'admin_dashboard'
    ADMIN_ANALYTICS = 'admin_analytics'
    USER_APPROVAL = 'user_approval'
    ROLE_MANAGEMENT = 'role_management'
    RATE_MANAGEMENT = 'rate_management'
    IMPORT_WIZARD = 'import_wizard'
    SUBSCRIBER_DASHBOARD = 'subscriber_dashboard'
    COMPANY_KNOWLEDGE = 'company_knowledge'
    AUTO_FILL_EXTENSION_ADMIN = 'extension_admin'
    AUTO_FILL_EXTENSION_USAGE = 'extension_usage'
    AUTO_FILL_EXTENSION_DOWNLOAD = 'extension_download'
    AUTO_FILL_EXTENSION_FEATURES = 'auto_fill_extension_features'
    COMPANY_ANALYTICS ='company_analytics'

    COMPANY_ONBOARDING = "company_onboarding"
    #DATA_MANAGEMENT = "data_management"

    # ─── Utility Routes ──────────────────────────────────────────────────────
    CHECKOUT = 'checkout'
    
    @classmethod
    def get_all_routes(cls) -> List[str]:
        """Return list of all route values for validation"""
        return [
            getattr(cls, attr) for attr in dir(cls) 
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        ]
    
    @classmethod
    def is_valid_route(cls, route: str) -> bool:
        """Check if a route string is valid"""
        return route in cls.get_all_routes()


# =============================================================================
# 📄 PAGE RENDERING FUNCTIONS
# =============================================================================

def history_page() -> None:
    """History page - delegates to analysis_history module"""
    debug_print("📜 Rendering history page from analysis_history module")
    
    # Import and call the module's function
    from modules.analysis_history import show_analysis_history
    show_analysis_history()


def profile_page() -> None:
    from modules.profile_module import render_user_profile
    render_user_profile()
    

# =============================================================================
# 🎨 SIDEBAR COMPONENT (Refactored + UI Optimized)
# =============================================================================

def render_nav_button(label: str, page_key: str, icon: str = "", 
                     disabled: bool = False, badge: Optional[str] = None,
                     button_type: str = "secondary") -> bool:
    """Render navigation button with optional text badge"""
    # Build label with badge as plain text (Streamlit-safe)
    full_label = f"{icon} {label}"
    if badge:
        full_label += f" [{badge}]"  # Simple text badge
    
    clicked = st.button(
        full_label,
        key=f"nav_{page_key}",
        use_container_width=True,
        type=button_type,
        disabled=disabled
        # ❌ Removed help parameter that was showing as visible text
    )
    
    if clicked:
        st.session_state.page = page_key
        st.rerun()
    
    return clicked


def _nav_button(label: str, page_key: str, badge: str = None):
    """Helper function to render navigation buttons without duplicate icons"""
    
    # Map page keys to actual route strings
    page_routes = {
        # Core Workflow
        "tender_management": "tender_management",
        "boq_generator": "boq_generator",
        "boq_bid_optimizer": "boq_bid_optimizer",
        
        # Analysis
        "dashboard": "dashboard",
        "new_analysis": "new_analysis",
        "history": "history",
        "historical_data": "historical_data",
        "competitor_tracking": "competitor_tracking",
        "competitor_master": "competitor_master",
        "post_evaluation": "post_evaluation",
        "intelligent_suggestions": "intelligent_suggestions",
         "basic_bid_optimizer": "basic_bid_optimizer",  # ✅ NEW
        "competitive_bid_simulator": "competitive_bid_simulator",
        # Company Management
        "company_dashboard": "company_dashboard",
        "company_analytics":"company_analytics",
        "egp_boq_workspace": "egp_boq_workspace",
        "user_management": "user_management",
        "company_rate_management": 'company_rate_management',        
        # Rate Management
        "rate_management": "rate_management",
        "rate_viewer": "rate_viewer",
        
        # Administration
        "admin_dashboard": "admin_dashboard",
        "admin_analytics":"admin_analytics",
        "boq_admin_report": "boq_admin_report",
        "user_approval": "user_approval",
        "role_management": "role_management",
        "company_management": "company_management",
        

        # System Tools
        "version_management": "version_management",
        "rollback_management": "rollback_management",
        "subscription": "subscription",
        "profile": "profile",
        
        # Help
        "tutorial": "tutorial"
    }
    
    route = page_routes.get(page_key, page_key)
    is_active = st.session_state.get('page') == route
    
    # Create display text with badge if provided
    display_text = label
    if badge:
        display_text = f"{label} <span style='background:#ef4444; color:white; padding:0px 6px; border-radius:10px; font-size:0.7rem; margin-left:5px;'>{badge}</span>"
    
    if is_active:
        # Active button styling
        st.markdown(f"""
        <div style="background: #667eea; border-radius: 8px; margin: 2px 0;">
            <div style="padding: 8px 12px; color: white; font-weight: bold;">
                {display_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Inactive button
        if st.button(display_text, key=f"nav_{route}", use_container_width=True):
            st.session_state.page = route
            st.rerun()

def render_sidebar() -> None:
    """Optimized sidebar with role-based navigation - using access control"""
    if not st.session_state.get('logged_in'):
        return
    
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        # Clear extracted data if leaving tender management page
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        
        from version import get_app_name, get_app_desc
        from modules.subscription import get_current_user_plan_name, is_premium_plan, get_plan
        from modules.access_control import access_control
        from modules.rbac import get_current_user_role

        # ========== BRANDING ==========
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ {get_app_name()}</h2>
            <small style="color: #666;">{get_app_desc()}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== USER INFO & BADGE ==========
        user_role = get_current_user_role()
        plan_name = get_current_user_plan_name()
        is_premium = is_premium_plan(plan_name)
        plan_config = get_plan(plan_name)
        
        full_name = st.session_state.get('full_name', 'User')
        company_name = st.session_state.get('company_name', 'N/A')
        company_id = st.session_state.get('company_id')
        if company_id:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT onboarding_completed FROM company_onboarding_status 
                    WHERE company_id = ?
                """, (company_id,))
                result = cursor.fetchone()
                conn.close()
                
                onboarding_complete = result and result['onboarding_completed'] == 1
                
                if not onboarding_complete:
                    st.warning("⚠️ Onboarding incomplete!")
                    if st.button("🏢 Complete Onboarding", use_container_width=True):
                        st.session_state.page = "company_onboarding"
                        st.rerun()
            except Exception:
                pass
        role_display = {
            'system_admin': '👑 System Admin',
            'admin': '👑 Admin',
            'company_admin': '🏢 Company Admin',
            'manager': '📊 Manager',
            'analyst': '📈 Analyst',
            'viewer': '👁️ Viewer'
        }.get(user_role, '👤 User')
        
        # Premium badge
        badge_color = plan_config.get('color', '#6c757d') if is_premium else "#6b7280"
        badge_text = f"{plan_config.get('badge', '✨')} PREMIUM" if is_premium else "🔓 FREE"
        
        st.markdown(f"""
        <div style="text-align: center; background: {badge_color}20; 
                    padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                    border: 1px solid {badge_color};">
            <strong style="color: {badge_color};">{badge_text}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ========== LOGOUT BUTTON (TOP) ==========
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 👤 Account")
        with col2:
            if st.button("🚪", key="nav_logout_icon", help="Sign Out", use_container_width=True):
                logout_user()
                for key in list(st.session_state.keys()):
                    if key not in ['debug_mode', 'page']:
                        del st.session_state[key]
                initialize_session_state()
                st.toast("👋 You have been signed out", icon="✅")
                st.rerun()
        
        st.markdown("---")
        
        # ========== SIDEBAR MENU ==========
        _render_sidebar_menu()
        
        # ========== USAGE STATS ==========
        
        sub_manager = SubscriptionManager(db)
        sub_manager.render_usage_stats()
        
        # ========== FULL LOGOUT BUTTON (BOTTOM) ==========
        if st.button("🚪 Sign Out", key="nav_logout", use_container_width=True, type="secondary"):
            logout_user()
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode', 'page']:
                    del st.session_state[key]
            initialize_session_state()
            st.toast("👋 You have been signed out", icon="✅")
            st.rerun()
        
        # ========== VERSION INFO ==========
        from version import __version__, __version_date__
        st.markdown("---")
        st.caption(f"📌 Version {__version__} | {__version_date__}")
        st.caption("💡 Need help? [Contact Support](mailto:support@tenderai.com)")
        
        if DEBUG_MODE:
            st.markdown("---")
            st.caption("🐛 Debug Mode Active")

def _render_sidebar_menu():
    """Render sidebar menu with access control"""
    
    from modules.access_control import access_control
    from modules.subscription import is_premium_plan, get_current_user_plan_name
    from modules.rbac import get_current_user_role
    
    user_role = get_current_user_role()
    is_premium = is_premium_plan(get_current_user_plan_name())
    
    # Define menu structure with permissions
    menu_sections = [
        {
            "title": "🚀 Core Workflow",
            "items": [
                {"label": "📋 Tender Management", "page": "tender_management", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📄 BOQ Generator", "page": "boq_generator", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "📊 Analysis & Intelligence",
            "items": [
                {"label": "📈 Dashboard", "page": "dashboard", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📈 Basic Bid Optimizer", "page": "quick_bid", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "🆓"},
                {"label": "🎯 Advanced Bid Optimizer", "page": "advanced_bid", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "⭐", "premium": True},
                {"label": "🔮 Competitive Simulator", "page": "competitive_intel", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "⭐", "premium": True},
                {"label": "📜 History", "page": "history", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📋 Post-Evaluation", "page": "post_evaluation", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "🧠 AI Suggestions", "page": "ai_advisor", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "👥 Competitor Tracking", "page": "competitor_tracking", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "🗂️ Competitor Master", "page": "competitor_master", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "🏢 Company Management",
            "roles": ["company_admin", "admin", "system_admin"],
            "items": [
                {"label": "🏢 Company Dashboard", "page": "company_dashboard", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "📊 Analytics Dashboard", "page": "company_analytics", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "👥 Team Management", "page": "user_management", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "🏗️ e-GP BOQ Workspace", "page": "egp_boq_workspace", "roles": ["company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "🏗️ Rate Management",
            "roles": ["admin", "system_admin", "company_admin", "manager", "analyst", "data_entry"],
            "items": [
                {"label": "📝 Rate Management", "page": "rate_management", "roles": ["admin", "system_admin", "company_admin", "manager", "data_entry"]},
                {"label": "📊 Rate Viewer", "page": "rate_viewer", "roles": ["admin", "system_admin", "company_admin", "manager", "analyst", "data_entry"]},
                {"label": "📥 Import Wizard", "page": "import_wizard", "roles": ["admin", "system_admin", "company_admin", "manager", "data_entry"]},
            ]
        },
        {
            "title": "👑 Administration",
            "roles": ["admin", "system_admin"],
            "items": [
                {"label": "📊 Admin Dashboard", "page": "admin_dashboard", "roles": ["admin", "system_admin"]},
                {"label": "📊 Analytics Dashboard", "page": "admin_analytics", "roles": ["admin", "system_admin"]},
                {"label": "👥 User Approvals", "page": "user_approval", "roles": ["admin", "system_admin"]},
                {"label": "🔐 Role Permissions", "page": "role_management", "roles": ["admin", "system_admin"]},
                {"label": "🏢 All Companies", "page": "company_management", "roles": ["admin", "system_admin"]},
                {"label": "📦 Version Management", "page": "version_management", "roles": ["admin", "system_admin"]},
                {"label": "🔄 Rollback Management", "page": "rollback_management", "roles": ["admin", "system_admin"]},
            ]
        },
        # ========== NEW: COMPANY ONBOARDING ==========
        {
            "title": "🚀 Getting Started",
            "items": [
                {"label": "🏢 Company Onboarding", "page": "company_onboarding", "roles": ["company_admin", "admin", "system_admin"]},
            ]
        },
        
        # ========== NEW: DATA MANAGEMENT ==========
        {
            "title": "⚙️ Data Management",
            "roles": ["company_admin", "admin", "system_admin"],
            "items": [              
                {"label": "🏢 Company Rate Management", "page": "company_rate_management", "roles": ["company_admin", "admin", "system_admin", "manager"]},
            ]
        },
        {
            "title": "⚙️ System Tools",
            "items": [
                {"label": "🤖 Extension Admin", "page": "extension_admin", "roles": ["admin", "system_admin"]},
                {"label": "🤖 Extension Usage", "page": "extension_usage", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "📥 Download Extension", "page": "extension_download", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "💳 Subscription", "page": "subscription", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "👤 Profile", "page": "profile", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "📚 Help & Support",
            "items": [
                {"label": "📖 Tutorial", "page": "tutorial", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        }
    ]
    
    # Render each section
    for section in menu_sections:
        # Check if user has access to any item in this section
        section_items = []
        for item in section.get("items", []):
            # Check role access
            if user_role not in item.get("roles", []):
                continue
            
            # Check premium requirement
            if item.get("premium", False) and not is_premium and user_role not in ['admin', 'system_admin']:
                # Show locked version
                section_items.append({
                    "label": f"🔒 {item['label']}",
                    "page": None,
                    "disabled": True,
                    "help": "Premium feature - Upgrade to access"
                })
            else:
                section_items.append(item)
        
        if section_items:
            # Show section title
            st.markdown(f"### {section['title']}")
            
            # Show items
            for item in section_items:
                if item.get("disabled", False):
                    st.button(
                        item['label'],
                        disabled=True,
                        use_container_width=True,
                        help=item.get("help", "Feature not available"),
                        key=f"nav_{item['label'].replace(' ', '_')}"
                    )
                else:
                    _nav_button(item['label'], item['page'], item.get('badge'))


def _render_sidebar_menu_bak():
    """Render sidebar menu with access control"""
    
    from modules.access_control import access_control
    from modules.subscription import is_premium_plan, get_current_user_plan_name
    from modules.rbac import get_current_user_role
    
    user_role = get_current_user_role()
    is_premium = is_premium_plan(get_current_user_plan_name())
    
    # Define menu structure with permissions
    menu_sections = [
        {
            "title": "🚀 Core Workflow",
            "items": [
                {"label": "📋 Tender Management", "page": "tender_management", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📄 BOQ Generator", "page": "boq_generator", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "📊 Analysis & Intelligence",
            "items": [
                {"label": "📈 Dashboard", "page": "dashboard", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📈 Basic Bid Optimizer", "page": "basic_bid_optimizer", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "🆓"},
                {"label": "🎯 Advanced Bid Optimizer", "page": "new_analysis", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "⭐", "premium": True},
                {"label": "🔮 Competitive Simulator", "page": "competitive_bid_simulator", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"], "badge": "⭐", "premium": True},
                {"label": "📜 History", "page": "history", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "📋 Post-Evaluation", "page": "post_evaluation", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "🧠 AI Suggestions", "page": "intelligent_suggestions", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "👥 Competitor Tracking", "page": "competitor_tracking", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "🗂️ Competitor Master", "page": "competitor_master", "roles": ["analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "🏢 Company Management",
            "roles": ["company_admin", "admin", "system_admin"],
            "items": [
                {"label": "🏢 Company Dashboard", "page": "company_dashboard", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "📊 Analytics Dashboard", "page": "company_analytics", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "👥 Team Management", "page": "user_management", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "🏗️ e-GP BOQ Workspace", "page": "egp_boq_workspace", "roles": ["company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "🏗️ Rate Management",
            "roles": ["admin", "system_admin", "company_admin", "manager", "analyst", "data_entry"],
            "items": [
                {"label": "📝 Rate Management", "page": "rate_management", "roles": ["admin", "system_admin", "company_admin", "manager", "data_entry"]},
                {"label": "📊 Rate Viewer", "page": "rate_viewer", "roles": ["admin", "system_admin", "company_admin", "manager", "analyst", "data_entry"]},
                {"label": "📥 Import Wizard", "page": "import_wizard", "roles": ["admin", "system_admin", "company_admin", "manager", "data_entry"]},
            ]
        },
        {
            "title": "👑 Administration",
            "roles": ["admin", "system_admin"],
            "items": [
                {"label": "📊 Admin Dashboard", "page": "admin_dashboard", "roles": ["admin", "system_admin"]},
                {"label": "📊 Analytics Dashboard", "page": "admin_analytics", "roles": ["admin", "system_admin"]},
                {"label": "👥 User Approvals", "page": "user_approval", "roles": ["admin", "system_admin"]},
                {"label": "🔐 Role Permissions", "page": "role_management", "roles": ["admin", "system_admin"]},
                {"label": "🏢 All Companies", "page": "company_management", "roles": ["admin", "system_admin"]},
                {"label": "📦 Version Management", "page": "version_management", "roles": ["admin", "system_admin"]},
                {"label": "🔄 Rollback Management", "page": "rollback_management", "roles": ["admin", "system_admin"]},
            ]
        },
        # ========== NEW: COMPANY ONBOARDING ==========
        {
            "title": "🚀 Getting Started",
            "items": [
                {"label": "🏢 Company Onboarding", "page": "company_onboarding", "roles": ["company_admin", "admin", "system_admin"]},
            ]
        },
        
        # ========== NEW: DATA MANAGEMENT ==========
        {
            "title": "⚙️ Data Management",
            "roles": ["company_admin", "admin", "system_admin"],
            "items": [              
                {"label": "🏢 Company Rate Management", "page": "company_rate_management", "roles": ["company_admin", "admin", "system_admin", "manager"]},
            ]
        },
        {
            "title": "⚙️ System Tools",
            "items": [
                {"label": "🤖 Extension Admin", "page": "extension_admin", "roles": ["admin", "system_admin"]},
                {"label": "🤖 Extension Usage", "page": "extension_usage", "roles": ["company_admin", "admin", "system_admin"]},
                {"label": "📥 Download Extension", "page": "extension_download", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "💳 Subscription", "page": "subscription", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
                {"label": "👤 Profile", "page": "profile", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        },
        {
            "title": "📚 Help & Support",
            "items": [
                {"label": "📖 Tutorial", "page": "tutorial", "roles": ["viewer", "analyst", "manager", "company_admin", "admin", "system_admin"]},
            ]
        }
    ]
    
    # Render each section
    for section in menu_sections:
        # Check if user has access to any item in this section
        section_items = []
        for item in section.get("items", []):
            # Check role access
            if user_role not in item.get("roles", []):
                continue
            
            # Check premium requirement
            if item.get("premium", False) and not is_premium and user_role not in ['admin', 'system_admin']:
                # Show locked version
                section_items.append({
                    "label": f"🔒 {item['label']}",
                    "page": None,
                    "disabled": True,
                    "help": "Premium feature - Upgrade to access"
                })
            else:
                section_items.append(item)
        
        if section_items:
            # Show section title
            st.markdown(f"### {section['title']}")
            
            # Show items
            for item in section_items:
                if item.get("disabled", False):
                    st.button(
                        item['label'],
                        disabled=True,
                        use_container_width=True,
                        help=item.get("help", "Feature not available"),
                        key=f"nav_{item['label'].replace(' ', '_')}"
                    )
                else:
                    _nav_button(item['label'], item['page'], item.get('badge'))

# =============================================================================
# 🎬 MAIN APP ROUTER (Refactored + Optimized)
# =============================================================================

def _render_public_pages() -> None:
    """Render pages for non-authenticated users"""
    from modules.individual_registration import render_individual_registration, render_individual_login
    from _pages.extension_features import show as extension_features_page
    
    page_handlers = {
        # Main pages
        'home': landing_page,
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': lambda: show_about_page(),
        'contact': contact_page,
        
        # Individual user pages
        'individual_register': render_individual_registration,
        'individual_login': render_individual_login,
        
        # Extension pages (public)
        'extension_features': extension_features_page,  # ← ADD THIS
        
        # Auth pages
        'forgot_password': render_forgot_password,
        'reset_password': lambda: render_reset_password(st.query_params.get("token", "")),
    }
    
    handler = page_handlers.get(st.session_state.page, landing_page)
    
    try:
        handler()
    except Exception as e:
        raise e 
        debug_print(f"❌ Public page render error: {e}")
        st.error("⚠️ Unable to load this page. Please try again.")

def is_onboarding_complete():
    """Check if onboarding is complete"""
    company_id = st.session_state.get('company_id')
    if company_id:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT onboarding_completed FROM company_onboarding_status WHERE company_id = ?
        """, (company_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result['onboarding_completed'] == 1
    return False

def can_manage_company_data():
    """Check if user can manage company data"""
    role = st.session_state.get('user_role', 'viewer')
    return role in ['system_admin', 'admin', 'company_admin', 'manager']


def _render_authenticated_pages() -> None:
    """Render pages for authenticated users with top navigation"""
    
    from modules.top_navigation import render_top_navigation
    
    # Render top navigation bar (appears on all authenticated pages)
    render_top_navigation()
    
    # Page handlers (your existing code)
    PAGE_HANDLERS: Dict[str, Callable] = {
        # Core pages
        PageRoutes.DASHBOARD: dashboard_page,
        PageRoutes.NEW_ANALYSIS: render_tender_analysis,
        PageRoutes.HISTORY: history_page,
        PageRoutes.PROFILE: profile_page,
        PageRoutes.ADMIN_DASHBOARD: admin_dashboard_page,
        PageRoutes.SUBSCRIPTION: lambda: render_subscription_page(),
        PageRoutes.USER_MANAGEMENT: lambda: render_user_management(),
         # ========== ADD THESE MISSING HANDLERS ==========
        PageRoutes.RATE_MANAGEMENT: lambda: render_rate_crud_forms(db),
        PageRoutes.IMPORT_WIZARD: lambda: render_unified_import_wizard(db),
        
        PageRoutes.RATE_VIEWER: lambda: _import_and_call('modules.rate_viewer', 'render_rate_viewer', db),
        PageRoutes.TENDER_FORM: lambda: _import_and_call('modules.tender_form', 'render_tender_form'),

        # Advanced modules (lazy import)
        PageRoutes.TENDER_MANAGEMENT: lambda: _import_and_call('modules.tender_management', 'render_tender_management'),
        PageRoutes.POST_EVALUATION: lambda: _import_and_call('modules.post_evaluation', 'render_post_evaluation_page'),
        PageRoutes.INTELLIGENT_SUGGESTIONS: lambda: _import_and_call('modules.post_evaluation', 'render_intelligent_suggestions'),
        PageRoutes.HISTORICAL_DATA: lambda: _import_and_call('modules.historical_data', 'render_historical_data_page'),
        PageRoutes.ANALYSIS_HISTORY: lambda: _import_and_call('modules.analysis_history', 'show_analysis_history'),
        PageRoutes.COMPETITOR_TRACKING: lambda: _import_and_call('modules.competitor_tracking', 'render_competitor_tracking_page'),
        PageRoutes.COMPETITOR_MASTER: lambda: render_competitor_master_page(db, SubscriptionManager(db)),
        PageRoutes.USER_APPROVAL: lambda: _import_and_call('modules.user_approval', 'render_user_approval_page'),
        PageRoutes.ROLE_MANAGEMENT: lambda: _import_and_call('modules.user_management', 'render_role_management'),
        PageRoutes.COMPANY_DASHBOARD: lambda: _import_and_call('_pages.company_dashboard', 'show'),        
        PageRoutes.EGP_BOQ_WORKSPACE: lambda: _import_and_call('modules.egp_boq_workspace', 'render_boq_workspace'),
        PageRoutes.TUTORIAL: lambda: _import_and_call('modules.tutorials', 'render_tutorial'),
        PageRoutes.BOQ_GENERATOR: lambda: _import_and_call('modules.boq_generator_ui', 'render_boq_generator'),
        PageRoutes.BOQ_ADMIN_REPORT: lambda: _import_and_call('modules.boq_admin_report', 'render_boq_admin_report'),
        PageRoutes.BOQ_BID_OPTIMIZER: lambda: _import_and_call('modules.boq_bid_bridge', 'render_boq_bid_integration'),
        PageRoutes.BASIC_BID_OPTIMIZER: lambda: _import_and_call('modules.basic_bid_optimizer', 'render'),
        PageRoutes.COMPANY_RATE_MANAGEMENT: lambda: render_company_rate_management(db),         
        PageRoutes.COMPANY_KNOWLEDGE: show_enhanced_company_dashboard,
        PageRoutes.AUTO_FILL_EXTENSION_ADMIN: show_extension_admin,
        PageRoutes.AUTO_FILL_EXTENSION_USAGE: show_extension_usage,
        PageRoutes.AUTO_FILL_EXTENSION_DOWNLOAD: lambda: _import_and_call('_pages.extension_download', 'show'),  
        PageRoutes.AUTO_FILL_EXTENSION_FEATURES: lambda: _import_and_call('_pages.extension_features', 'show'), 
        PageRoutes.COMPETITIVE_BID_SIMULATOR: lambda: render_competitive_bid_simulator_ui(db, SubscriptionManager(db)),
        PageRoutes.ADMIN_ANALYTICS: lambda: _import_and_call('_pages.admin_analytics_dashboard', 'show'),
        PageRoutes.COMPANY_ANALYTICS: lambda: _import_and_call('_pages.company_analytics_dashboard', 'show'),
        PageRoutes.COMPANY_ONBOARDING: lambda: render_company_onboarding(db),        
        PageRoutes.QUICK_BID: lambda: render_quick_bid_check(db, SubscriptionManager),
        PageRoutes.ADVANCED_BID: lambda: render_advanced_bid_analysis(db, SubscriptionManager),
        PageRoutes.COMPETITIVE_INTEL: lambda: render_competitive_intelligence(db, SubscriptionManager),
        PageRoutes.AI_ADVISOR: lambda: render_ai_bid_advisor(db, SubscriptionManager),
        PageRoutes.COMPANY_CONFIG: lambda: render_company_config(db),

    }
    
    # Get handler with fallback to dashboard for unknown routes
    handler = PAGE_HANDLERS.get(st.session_state.page, PAGE_HANDLERS[PageRoutes.DASHBOARD])
    
    try:
        handler()
    except ImportError as e:
        debug_print(f"❌ Module import error for '{st.session_state.page}': {e}")
        logger.error(f"Import failed: {st.session_state.page}", exc_info=True)
        st.error(f"⚠️ Feature unavailable: {st.session_state.page.replace('_', ' ').title()}")
        st.info("This feature may require a higher subscription plan or system configuration.")
    except Exception as e:
        debug_print(f"❌ Render error for '{st.session_state.page}': {e}")
        logger.error(f"Page render failed: {st.session_state.page}", exc_info=True)
        st.error("⚠️ Unable to load this page. Please try again or contact support.")
        if DEBUG_MODE:
            with st.expander("🐛 Debug Traceback"):
                st.code(traceback.format_exc(), language="python")

# =============================================================================
# 🎨 HEADER COMPONENT (For Public Pages)
# =============================================================================

def render_header_nav() -> None:
    """Render header navigation menu for non-authenticated users"""
    
    # Custom CSS for header navigation
    st.markdown("""
    <style>
        /* Remove gap below header */
        .header-nav-container {
            margin-bottom: -1rem !important;
        }
        
        .header-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 0 0 10px 10px;
            margin-bottom: 0rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-logo h2 {
            color: white;
            margin: 0;
            font-size: 1.5rem;
        }
        .header-logo p {
            color: rgba(255,255,255,0.8);
            margin: 0;
            font-size: 0.8rem;
        }
        .header-menu {
            display: flex;
            gap: 1rem;
        }
        /* Style Streamlit buttons to look like navigation links */
        .header-menu .stButton > button {
            background: transparent !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 5px !important;
            font-weight: normal !important;
            font-size: 1rem !important;
            width: auto !important;
            margin: 0 !important;
            box-shadow: none !important;
        }
        .header-menu .stButton > button:hover {
            background: rgba(255,255,255,0.2) !important;
            transform: none !important;
        }
        .header-menu .active .stButton > button {
            background: rgba(255,255,255,0.3) !important;
            font-weight: bold !important;
        }
        .btn-login .stButton > button {
            background: transparent !important;
            border: 1px solid white !important;
        }
        .btn-register .stButton > button {
            background: #22c55e !important;
        }
        .btn-register .stButton > button:hover {
            background: #16a34a !important;
        }
        @media (max-width: 768px) {
            .header-nav {
                flex-direction: column;
                gap: 1rem;
                padding: 1rem;
            }
            .header-menu {
                flex-wrap: wrap;
                justify-content: center;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create header using Streamlit columns (this works reliably)
    with st.container():
        # Use columns for layout
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("""
            <div class="header-logo">
                <h2>🏗️ TenderAI</h2>
                <p>Bid Optimization Platform</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Get current page
            current_page = st.session_state.get('page', 'home')
            
            # Create a row of buttons
            menu_cols = st.columns(6)
            
            pages = [
                ("🏠 Home", "home"),
                ("💰 Pricing", "pricing"),
                ("ℹ️ About", "about"),
                ("📞 Contact", "contact"),
                ("🔐 Login", "login"),
                ("➕ Register", "register"),
            ]
            
            for idx, (label, page_key) in enumerate(pages):
                with menu_cols[idx]:
                    # Determine button type
                    if page_key in ['login', 'register']:
                        btn_class = "btn-login" if page_key == 'login' else "btn-register"
                    else:
                        btn_class = ""
                    
                    # Check if this is the active page
                    is_active = current_page == page_key
                    button_type = "primary" if is_active else "secondary"
                    
                    # Create the button
                    if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=button_type):
                        st.session_state.page = page_key
                        st.rerun()


def main() -> None:
    """
    Main application entry point with optimized routing.
    """
    import base64
    import json
    
    # Initialize theme
    init_theme()
    
    # Apply theme CSS
    apply_theme()
    
    from migrations.add_chapter_number_to_pwd_children import run_migration
    run_migration()
    from migrations.add_is_active_to_tender_milestones import run_migration2
    run_migration2()
    ensure_database_schema()
    # =========================================================================
    # FIRST: Check if user is already logged in - redirect immediately
    # =========================================================================
    if st.session_state.get('logged_in', False):
        # Ensure page is set correctly
        user_role = st.session_state.get('user_role', 'viewer')
        current_page = st.session_state.get('page', 'dashboard')
        
        # If on login or oauth2callback page, redirect to proper dashboard
        if current_page in ['login', 'oauth2callback']:
            # Clear any lingering params
            st.query_params.clear()
            
            if user_role in ['admin', 'system_admin']:
                st.session_state.page = "admin_dashboard"
            elif user_role == 'company_admin':
                st.session_state.page = "company_dashboard"
            else:
                st.session_state.page = "dashboard"
            st.rerun()
            return
    
    # =========================================================================
    # HANDLE GOOGLE OAUTH CALLBACK
    # =========================================================================
    query_params = st.query_params
    
    if 'code' in query_params and not st.session_state.get('logged_in', False):
        from modules.google_auth import handle_google_callback
        
        # ✅ Process the callback
        user_data = handle_google_callback()
        
        # If login was successful, redirect to dashboard
        if user_data and user_data.get('logged_in'):
            user_role = st.session_state.get('user_role', 'viewer')
            if user_role in ['admin', 'system_admin']:
                st.session_state.page = "admin_dashboard"
            elif user_role == 'company_admin':
                st.session_state.page = "company_dashboard"
            else:
                st.session_state.page = "dashboard"
            
            st.query_params.clear()
            st.rerun()
            return
        
        # If registration needed, redirect to register
        if user_data and user_data.get('show_registration'):
            st.session_state.page = "register"
            st.query_params.clear()
            st.rerun()
            return
        
        # If we get here, something went wrong
        st.query_params.clear()
        st.rerun()
        return

    debug_print(f"🚀 App render | Page: {st.session_state.page} | Auth: {st.session_state.logged_in}")
    
    
    # Hide Streamlit's default chrome elements
    st.markdown("""
    <style>
        div[data-testid="stSidebarNav"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stApp { max-width: 100%; }
    </style>
    """, unsafe_allow_html=True)
    
    # Ensure session state is initialized (safety net)
    if 'page' not in st.session_state:
        st.session_state.page = PageRoutes.HOME
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # =========================================================================
    # CONDITIONAL HEADER & SIDEBAR RENDERING
    # =========================================================================
    
    # # ONLY render app header for logged-in users
    # if st.session_state.logged_in:
    #     # Pass the dark mode toggle to be rendered inside the header
    #     render_app_header(show_dark_mode_toggle=True)
    
    render_app_header()
    if st.session_state.logged_in:
        # For logged-in users, show sidebar (without dark mode toggle)
        with st.sidebar:
            render_sidebar()
    else:
        # For non-authenticated users, show header navigation
        render_header_nav()
    
    # Handle checkout flow (modal-like experience)
    if st.session_state.get('show_checkout'):
        render_checkout()
        return
    
    # Route to appropriate page handler
    if not st.session_state.logged_in:
        _render_public_pages()
    else:
        _render_authenticated_pages()
    
    # =========================================================================
    # RENDER FOOTER (Only for logged-in users)
    # =========================================================================
    if st.session_state.logged_in:
        from modules.ui_components import render_footer
        render_footer()
    
    # Optional: Global debug panel (development only)
    if DEBUG_MODE and st.session_state.get('user_role') == 'admin':
        _render_global_debug_panel()
        
def _render_global_debug_panel() -> None:
    """Render global debug information for admin users (development only)"""
    with st.expander("🐛 Global Debug Panel", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Session State Keys")
            for key in sorted(st.session_state.keys()):
                val = st.session_state[key]
                display = str(val)[:150] + "..." if len(str(val)) > 150 else str(val)
                st.code(f"{key}: {display}", language="python")
        
        with col2:
            st.markdown("#### Quick Actions")
            if st.button("🗑️ Clear Non-Essential State", use_container_width=True):
                protected = ['logged_in', 'user_id', 'company_id', 'user_role', 'subscription_plan', 'debug_mode', 'page']
                for key in list(st.session_state.keys()):
                    if key not in protected:
                        del st.session_state[key]
                st.success("Session state cleared!")
                st.rerun()
            
            if st.button("🔄 Force Rerun", use_container_width=True):
                st.rerun()
            
            st.markdown("#### System Info")
            st.code(f"""
                Python: {sys.version.split()[0]}
                Streamlit: {st.__version__}
                Debug Mode: {DEBUG_MODE}
                Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            """, language="python")

def _handle_subscription_redirect():
    """Redirect to appropriate subscription page based on user type"""
    account_type = st.session_state.get('account_type', 'company')
    if account_type == 'individual':
        from modules.subscription import render_subscription_page
        render_subscription_page()
    else:
        show_company_subscription()


def _handle_company_dashboard():
    """Handle company dashboard - redirect to subscriber dashboard for non-admins"""
    user_role = st.session_state.get('user_role', 'viewer')
    
    if user_role in ['admin', 'system_admin']:
        # Admins see company dashboard with management features
        show_company_dashboard()
    else:
        # Subscribers see their project dashboard
        render_subscriber_dashboard(db)


def _handle_admin_dashboard():
    """Handle admin dashboard with proper navigation"""
    from _pages.admin_dashboard import show as show_admin_dashboard
    show_admin_dashboard()


def _handle_premium_feature(feature_func):
    """Check subscription before showing premium features"""
    company_id = st.session_state.get('company_id')
    
    if not company_id:
        st.error("Company information not found")
        return
    
    # Check if user has access to premium features
    from modules.subscription_manager import SubscriptionManager
    sub_manager = SubscriptionManager(db)
    sub = sub_manager.get_company_subscription(company_id)
    
    # Professional and Enterprise plans have access
    if sub.get('plan') in ['professional', 'enterprise']:
        feature_func()
    else:
        st.warning("🔒 This is a premium feature")
        st.info(f"Your current plan: **{sub.get('plan_name', 'Free')}**")
        st.markdown("**Upgrade to Professional or Enterprise to access:**")
        st.markdown("- Competitor tracking and analysis")
        st.markdown("- Historical data analysis")
        st.markdown("- Post-bid evaluation")
        st.markdown("- Intelligent suggestions")
        
        if st.button("💳 Upgrade Now", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()

# main.py - Add at the top after imports

def ensure_database_schema():
    """Run database fix on startup if needed"""
    import os
    import sqlite3
    
    db_path = "data/tender_system.db"
    if not os.path.exists(db_path):
        return
    
    try:
        # Check if mobile_number column exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        if 'mobile_number' not in columns:
            # Run the fix script
            import subprocess
            subprocess.run(["python", "migrations/fix_db_final.py"], check=True)
            print("✅ Database schema updated")
    except Exception as e:
        print(f"⚠️ Could not check/update schema: {e}")

# Call this near the start of your app


def _access_denied():
    """Show access denied message"""
    st.error("❌ Access Denied")
    st.info("You don't have permission to access this page.")
    if st.button("← Return to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def debug_competitor_bids_state(location: str):
    """Debug helper to track competitor bids through session state"""
    debug_print(f"\n📍 COMPETITOR DEBUG [{location}]")
    debug_print(f"  analysis_competitor_bids: {len(st.session_state.get('analysis_competitor_bids', []))}")
    debug_print(f"  current_competitor_bids: {len(st.session_state.get('current_competitor_bids', []))}")
    debug_print(f"  auto_competitor_count: {st.session_state.get('auto_competitor_count', 3)}")
    debug_print(f"  analysis_bid_source: {st.session_state.get('analysis_bid_source', 'N/A')}")
    
    # Show actual data if available
    comp_bids = st.session_state.get('analysis_competitor_bids', [])
    if comp_bids:
        debug_print(f"  Sample: {comp_bids[0] if comp_bids else 'None'}")

def upgrade_admin_once():
    """Upgrade admin to professional plan if on free plan"""
    if st.session_state.get('_admin_upgraded', False):
        return
    
    if st.session_state.get('logged_in') and st.session_state.get('user_role') in ['admin', 'system_admin']:
        user_id = st.session_state.user_id
        company_id = st.session_state.get('company_id')
        
        # ✅ Check user subscription
        sub = db.get_user_subscription(user_id)
        
        if sub.get('subscription_tier') == 'free':
            print(f"🔧 Upgrading admin {user_id} to professional...")
            
            # ✅ Try user subscription first
            success = db.update_user_subscription(user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            
            # ✅ If no user subscription, try company subscription
            if not success and company_id:
                success = db.update_company_subscription(company_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            
            if success:
                st.session_state.subscription_plan = 'professional'
                st.session_state._admin_upgraded = True
                print(f"✅ Admin {user_id} upgraded to professional")


# =============================================================================
# 🎬 APP LAUNCH (Final safety)
# =============================================================================
if __name__ == "__main__":
    # ✅ Ensure imports are available
    from database.unified_db_manager import UnifiedDatabaseManager
    db = UnifiedDatabaseManager()
    
    debug_print("🎬 Starting TenderAI application...")
    #upgrade_admin_once()  # Ensure admin users are upgraded at startup (one-time check)
    #db.update_role_permissions_for_rates()
    # Add this function to main.py after db = DatabaseManager() initialization

    
    # ✅ Initialize once at startup
    initialize_session_state()
    
    try:
        main()
    except Exception as e:
        logger.critical("Application crashed", exc_info=True)
        st.error("💥 Application error. Please refresh or contact support.")
        # if DEBUG_MODE:
        #     required_routes = [
        #         'home', 'login', 'register', 'pricing', 'about', 'contact',
        #         'dashboard', 'new_analysis', 'history', 'profile', 'subscription',
        #         'user_management', 'tender_management', 'post_evaluation', 'intelligent_suggestions',
        #         'historical_data', 'analysis_history', 'company_analytics', 'competitor_tracking',
        #         'admin_dashboard', 'admin_analytics', 'user_approval', 'role_management', 'tutorial'
        #     ]
            
        #     missing = [r for r in required_routes if r not in PageRoutes.get_all_routes()]
        #     if missing:
        #         debug_print(f"❌ Missing PageRoutes attributes: {missing}")
        #     else:
        #         debug_print("✅ All PageRoutes attributes present")
    
    debug_print("✅ App render cycle complete\n")