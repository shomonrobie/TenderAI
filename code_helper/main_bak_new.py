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
    validate_password_strength
)
from config import DEBUG_MODE, BID_AMOUNT_DECIMALS, BID_RATIO_DECIMALS, COST_ESTIMATE_RATIO, PPR_CONFIG, debug_print
#from modules.pdf_generator import generate_babui_detailed_report
from modules.advanced_bid_optimizer import get_three_tier_comparison

# Continue with normal app flow
# debug_print(f"🚀 App render | Page: {st.session_state.page} | Auth: {st.session_state.logged_in}")
from modules.forgot_password import render_forgot_password
from modules.reset_password import render_reset_password
from _pages.admin_dashboard_bak import show as admin_dashboard_page
from _pages.landing_page import show_landing_page
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
from _pages.company_subscription import show_company_subscription
from _pages.company_dashboard import show as show_company_dashboard
from _pages.dashboard import show as dashboard_page
from modules.navigation import render_top_navigation, render_page_header
from modules.ui_components import (
    render_app_header, 
    render_dark_mode_toggle, 
    apply_theme, 
    init_theme,
    render_footer
)
from modules.tender_analysis import render_tender_analysis




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
from database.db_manager import DatabaseManager
from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user
from modules.subscription import render_subscription_page, render_checkout
from modules.user_management import render_user_management

# Initialize database
db = DatabaseManager()


if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

print("=" * 60)
print(f"MAIN.PY STARTING - logged_in={st.session_state.logged_in}")
print(f"URL params at start: {dict(st.query_params)}")

# Try to restore session from URL
if not st.session_state.logged_in:
    print("Attempting to restore from URL...")
    try:
        from modules.auth import restore_session_from_url
        restored = restore_session_from_url()
        print(f"Restore result: {restored}")
        if restored:
            print("Session restored! User is now logged in.")
            # Don't rerun here to avoid loop
    except Exception as e:
        print(f"Restore exception: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Already logged in, skipping restore")

print("=" * 60)

st.markdown(get_compact_css(), unsafe_allow_html=True)
def check_and_run_migrations(db):
    """Check database schema and run migrations if needed"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # =========================================================================
        # MIGRATION 1: Add district column to companies (existing)
        # =========================================================================
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = [col[1] for col in cursor.fetchall()]
        
        if 'district' not in company_columns:
            debug_print("🔧 Running schema migration: city → district")
            cursor.executescript("""
            ALTER TABLE companies ADD COLUMN district TEXT;
            UPDATE companies SET district = city WHERE city IS NOT NULL;
            """)
            conn.commit()
            debug_print("✅ Migration 1 complete: district column added")
        
        # =========================================================================
        # MIGRATION 2: Add individual user support columns to users table
        # =========================================================================
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        # Define new columns for users table
        user_new_columns = {
            'auth_provider': "TEXT DEFAULT 'email'",
            'email_verified': "BOOLEAN DEFAULT 0",
            'email_verified_at': "TIMESTAMP",
            'verification_token': "TEXT",
            'reset_token': "TEXT",
            'reset_token_expires': "TIMESTAMP",
            'specialization': "TEXT",
            'years_experience': "INTEGER"
        }
        
        migration_2_needed = False
        for col_name in user_new_columns.keys():
            if col_name not in user_columns:
                migration_2_needed = True
                break
        
        if migration_2_needed:
            debug_print("🔧 Running schema migration: adding individual user support columns")
            
            for col_name, col_type in user_new_columns.items():
                if col_name not in user_columns:
                    try:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        debug_print(f"  ✅ Added column: {col_name}")
                    except Exception as e:
                        debug_print(f"  ⚠️ Could not add {col_name}: {e}")
            
            conn.commit()
            debug_print("✅ Migration 2 complete: individual user columns added")
        
        # =========================================================================
        # MIGRATION 3: Add is_individual column to companies table
        # =========================================================================
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_individual' not in company_columns:
            debug_print("🔧 Running schema migration: adding is_individual column")
            cursor.execute("ALTER TABLE companies ADD COLUMN is_individual BOOLEAN DEFAULT 0")
            conn.commit()
            debug_print("✅ Migration 3 complete: is_individual column added")
        
        # =========================================================================
        # MIGRATION 4: Create indexes for better performance
        # =========================================================================
        debug_print("🔧 Creating indexes for better performance...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider)",
            "CREATE INDEX IF NOT EXISTS idx_companies_is_individual ON companies(is_individual)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
                debug_print(f"  ✅ Index created: {index.split('ON')[1].strip() if 'ON' in index else index}")
            except Exception as e:
                debug_print(f"  ⚠️ Could not create index: {e}")
        
        conn.commit()
        debug_print("✅ All migrations completed successfully!")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        if DEBUG_MODE:
            st.warning(f"⚠️ Database migration check failed: {e}")

# Call at startup
check_and_run_migrations(db)

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
# 💾 SAVE CALLBACK FUNCTION (Fixed connection handling)
# =============================================================================
def _save_analysis_callback():
    """Callback function for the Save button - preserves analysis state after save"""
    debug_print("\n" + "="*60)
    debug_print("🔽 SAVE CALLBACK TRIGGERED")
    debug_print("="*60)
    
    conn = None
    try:
        # === 1. Validate session state ===
        print("Attempting to save...")

        required_keys = [
            'current_analysis_record', 'current_best_result', 'current_best_tier',
            'current_competitor_bids', 'current_risk_tolerance', 'user_id', 'company_id'
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
        
        debug_print(f"✓ User ID: {user_id}")
        debug_print(f"✓ Company ID: {company_id}")
        debug_print(f"✓ Analysis record: {analysis_record.get('tender_id', 'N/A')}")
        debug_print(f"✓ Best tier: {best_tier}")
        debug_print(f"✓ Optimal bid: {best_result.get('optimal_bid', 'N/A')}")
        debug_print(f"✓ Competitor bids count: {len(competitor_bids)}")
        
        # === 3. Prepare data ===
        official_est = float(analysis_record.get('official_estimate', 0))
        if official_est <= 0:
            st.error("❌ Official estimate must be positive")
            return
            
        optimal_bid = float(best_result['optimal_bid'])
        win_probability = float(best_result['win_probability'])
        confidence_score = float(best_result.get('confidence_score', 0.75))
        risk_level = str(best_result['risk_level'])
        
        estimated_cost = official_est * COST_ESTIMATE_RATIO
        expected_profit = optimal_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        competitor_bids_json = json.dumps(competitor_bids if competitor_bids else [])
        analysis_type_str = f"{best_tier.upper()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # === 4. Database insertion ===
        debug_print("🗄️ Connecting to database...")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # First, check if the table exists and has all columns
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        debug_print(f"✓ Existing columns in tender_analyses: {existing_columns}")
        
        # Build insert query dynamically based on existing columns
        insert_fields = [
            'user_id', 'company_id', 'tender_id', 'tender_title', 'procuring_entity',
            'division', 'official_estimate', 'recommended_bid', 'success_probability',
            'risk_level', 'competitor_count', 'analysis_type', 'analysis_date', 'bid_status'
        ]
        
        insert_values = [
            user_id, company_id,
            str(analysis_record.get('tender_id', '')),
            str(analysis_record.get('tender_title', '')),
            str(analysis_record.get('procuring_entity', '')),
            str(analysis_record.get('division', '')),
            official_est,
            optimal_bid,
            win_probability,
            risk_level,
            int(len(competitor_bids)),
            analysis_type_str,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'draft'
        ]
        
        # Add optional fields if they exist in table
        if 'district' in existing_columns:
            insert_fields.append('district')
            insert_values.append(str(analysis_record.get('district', '')))
        
        if 'thana' in existing_columns:
            insert_fields.append('thana')
            insert_values.append(str(analysis_record.get('thana', '')))
        
        if 'construction_type' in existing_columns:
            insert_fields.append('construction_type')
            insert_values.append(str(analysis_record.get('construction_type', '')))
        
        if 'risk_strategy' in existing_columns:
            insert_fields.append('risk_strategy')
            insert_values.append(str(risk_tolerance))
        
        if 'confidence_score' in existing_columns:
            insert_fields.append('confidence_score')
            insert_values.append(confidence_score)
        
        if 'expected_profit' in existing_columns:
            insert_fields.append('expected_profit')
            insert_values.append(expected_profit)
        
        if 'expected_value' in existing_columns:
            insert_fields.append('expected_value')
            insert_values.append(expected_value)
        
        if 'competitor_bids' in existing_columns:
            insert_fields.append('competitor_bids')
            insert_values.append(competitor_bids_json)
        
        # Build and execute query
        placeholders = ','.join(['?' for _ in range(len(insert_fields))])
        insert_query = f"INSERT INTO tender_analyses ({','.join(insert_fields)}) VALUES ({placeholders})"
        
        debug_print(f"🔍 Insert Query: {insert_query}")
        debug_print(f"🔍 Insert Values: {insert_values}")
        
        cursor.execute(insert_query, insert_values)
        
        analysis_id = cursor.lastrowid
        conn.commit()
        debug_print(f"✓ Committed transaction. Last insert ID: {analysis_id}")
        
        # === 5. Update session state ===
        st.session_state.last_saved_analysis_id = analysis_id
        st.session_state.last_saved_tender_id = analysis_record.get('tender_id', '')
        
        debug_print(f"✅ SAVE SUCCESSFUL! Analysis ID: {analysis_id}")
        debug_print("="*60 + "\n")
        
        st.success(f"✅ {best_tier.upper()} analysis saved! (ID: {analysis_id})")
        st.balloons()
        
    except Exception as e:
        debug_print(f"❌ SAVE ERROR: {type(e).__name__}: {str(e)}")
        logger.error("Save callback failed", exc_info=True)
        if DEBUG_MODE:
            debug_print("\n🔎 FULL TRACEBACK:")
            debug_print(traceback.format_exc())
        st.error(f"💥 Error saving analysis: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
                debug_print("✓ Database connection closed")
            except Exception as e:
                logger.warning(f"Failed to close DB connection: {e}")


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
    INDIVIDUAL_REGISTER = 'individual_register'  # Add this
    INDIVIDUAL_LOGIN = 'individual_login'        # Add this
    
    # ─── Authenticated Core Pages ────────────────────────────────────────────
    DASHBOARD = 'dashboard'
    NEW_ANALYSIS = 'new_analysis'
    RATE_VIEWER = 'rate_viewer'
    HISTORY = 'history'
    PROFILE = 'profile'
    SUBSCRIPTION = 'subscription'
    # Inside PageRoutes class
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
    NEW_ANALYSIS: 'render_tender_analysis',

    # ─── Premium Intelligence Pages ──────────────────────────────────────────
    HISTORICAL_DATA = 'historical_data'
    ANALYSIS_HISTORY = 'analysis_history'
    COMPETITOR_TRACKING = 'competitor_tracking'
    COMPETITOR_MASTER = 'competitor_master'
    BOQ_GENERATOR = "boq_generator"
    BOQ_ADMIN_REPORT = "boq_admin_report"
    BOQ_BID_OPTIMIZER = "boq_bid_optimizer"

    # ─── Admin System Pages ──────────────────────────────────────────────────
    ADMIN_DASHBOARD = 'admin_dashboard'
    USER_APPROVAL = 'user_approval'
    ROLE_MANAGEMENT = 'role_management'
    RATE_MANAGEMENT = 'rate_management'
    IMPORT_WIZARD = 'import_wizard'
    SUBSCRIBER_DASHBOARD = 'subscriber_dashboard'
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
# 📊 DISPLAY FUNCTION (Fixed syntax errors)
# =============================================================================
def display_analysis_results_with_report(
    comparison: Dict[str, Dict], 
    analysis_record: Dict, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """Display analysis results in tabbed format with save functionality"""
    
    debug_print(f"\n📊 Rendering analysis display | Tiers: {list(comparison.keys()) if comparison else 'None'}")
    
    # =============================================================================
    # 🛡️ SESSION STATE PROTECTION
    # =============================================================================
    if analysis_record and comparison:
        debug_print("💾 Updating session state with fresh analysis data")
        
        # Find best result (single calculation)
        best_result = None
        best_tier = None
        for tier, result in comparison.items():
            score = result.get('confidence_score', 0) * result.get('win_probability', 0)
            current_best_score = (
                best_result.get('confidence_score', 0) * best_result.get('win_probability', 0) 
                if best_result else -1
            )
            if score > current_best_score:
                best_result = result
                best_tier = tier
        
        # Store in session state
        st.session_state.current_analysis_record = analysis_record
        st.session_state.current_best_result = best_result
        st.session_state.current_best_tier = best_tier
        st.session_state.current_competitor_bids = competitor_bids
        st.session_state.current_risk_tolerance = risk_tolerance
        st.session_state.current_comparison = comparison
        
        debug_print(f"✓ Session state updated | Best tier: {best_tier}")
    
    # =============================================================================
    # 📋 BUILD COMPARISON TABLE (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    st.markdown("## 🆚 Three-Tier Analysis Comparison")
    
    comparison_data = []
    active_comparison = comparison if comparison else st.session_state.get('current_comparison', {})
    
    for tier, result in active_comparison.items():
        comparison_data.append({
            'Analysis Type': tier.upper(),
            'Method': result.get('method', 'N/A'),
            'Optimal Bid': f"BDT {result.get('optimal_bid', 0):,.3f}",  # ✅ Changed to 3 decimals
            '% of Estimate': f"{result.get('bid_ratio', 0)*100:.1f}%",
            'Win Probability': f"{result.get('win_probability', 0)*100:.0f}%",
            'Confidence': f"{result.get('confidence_score', 0.70)*100:.0f}%",
            'Risk': f"{result.get('risk_color', '⚪')} {result.get('risk_level', 'Unknown')}"
        })

    
    # ✅ Fixed: Complete condition with colon
    if comparison_data:  # ✅ Was: if comparison_
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
        st.info(f"**Suggested Bid:** BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f} ({bid_ratio*100:.1f}% of estimate)")
        debug_print(f"✓ Displayed recommendation: {best_tier} @ BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f}")
    else:
        st.warning("⚠️ Run analysis first to see recommendations")
    
    # =============================================================================
    # 💾 SAVE BUTTON SECTION (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        has_valid_data = (
            st.session_state.get('current_analysis_record') is not None and
            st.session_state.get('current_best_result') is not None
        )
        
        st.button(
            "💾 Save Analysis to History", 
            key="save_analysis_btn", 
            use_container_width=True, 
            type="primary",
            disabled=not has_valid_data,
            on_click=_save_analysis_callback
        )
        debug_print(f"✓ Save button rendered | Enabled: {has_valid_data}")
        # ✅ Fixed: Complete condition with colon
        if not has_valid_data:  # ✅ Was: if not has_valid_
            st.caption("🔒 Run analysis first to enable saving")
        elif DEBUG_MODE:
            st.caption("🐛 Debug mode active")
    
    # =============================================================================
    # 🔄 Show recently saved status
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


# =============================================================================
# 🔄 ADMIN PREMIUM ENFORCEMENT (Your existing function)
# =============================================================================
def ensure_admin_premium():
    """Force admin to have professional plan for testing"""
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            debug_print("🎁 Auto-upgraded admin to professional plan")
            return True
    return False


def _render_unauthenticated_pages() -> None:
    """Render pages for users who are not logged in"""
    
    # Define unauthenticated page handlers
    UNAUTH_PAGE_HANDLERS = {
        'home': home_page,
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': about_page,
        'contact': contact_page,
        'forgot_password': render_forgot_password,
        'reset_password': lambda: render_reset_password(st.query_params.get("token", "")),
    }
    
    # Get current page from session state
    current_page = st.session_state.get('page', 'login')
    
    # Get the handler function
    handler = UNAUTH_PAGE_HANDLERS.get(current_page, login_page)
    
    # Call the handler
    try:
        handler()
    except Exception as e:
        debug_print(f"❌ Unauthenticated page render error: {e}")
        st.error("⚠️ Unable to load this page. Please try again.")



def run_three_tier_analysis(analysis_record, competitor_bids, risk_tolerance):
    """
    Run the three-tier analysis (Basic, Advanced, Enhanced).
    Replace with your actual analysis logic.
    """
    debug_print(f"🔬 Running analysis | Estimate: {analysis_record['official_estimate']}, Competitors: {len(competitor_bids)}")
    
    official_est = analysis_record['official_estimate']
    
    # Risk multipliers
    risk_mult = {'Low': 0.95, 'Medium': 1.0, 'High': 1.05}.get(risk_tolerance, 1.0)
    
    comparison = {}
    
    # Basic Analysis
    comparison['basic'] = {
        'method': 'Statistical Average',
        'optimal_bid': official_est * 0.92 * risk_mult,
        'bid_ratio': 0.92,
        'win_probability': 0.65,
        'confidence_score': 0.70,
        'risk_level': 'Medium',
        'risk_color': '🟡'
    }
    
    # Advanced Analysis (PPR 2025)
    if ADVANCED_OPTIMIZER_AVAILABLE:
        try:
            adv_result = calculate_optimal_bid_ppr2025(official_est, competitor_bids, risk_tolerance)
            comparison['advanced'] = {
                'method': 'PPR 2025 Compliant',
                'optimal_bid': adv_result['optimal_bid'],
                'bid_ratio': adv_result['bid_ratio'],
                'win_probability': adv_result['win_probability'],
                'confidence_score': 0.82,
                'risk_level': 'Low',
                'risk_color': '🟢'
            }
        except Exception as e:
            debug_print(f"⚠️ Advanced analysis failed: {e}")
            comparison['advanced'] = comparison['basic'].copy()
            comparison['advanced']['method'] = 'PPR 2025 (Fallback)'
    else:
        comparison['advanced'] = {
            'method': 'PPR 2025 (Simulated)',
            'optimal_bid': official_est * 0.94 * risk_mult,
            'bid_ratio': 0.94,
            'win_probability': 0.72,
            'confidence_score': 0.82,
            'risk_level': 'Low',
            'risk_color': '🟢'
        }
    
    # Enhanced Analysis (ML)
    comparison['enhanced'] = {
        'method': 'ML Ensemble Model',
        'optimal_bid': official_est * 0.96 * risk_mult,
        'bid_ratio': 0.96,
        'win_probability': 0.78,
        'confidence_score': 0.88,
        'risk_level': 'Low',
        'risk_color': '🟢'
    }
    
    debug_print(f"✓ Analysis complete | Best tier will be calculated in display function")
    return comparison

# =============================================================================
# 🔢 BID PARSING & CALCULATION UTILITIES
# =============================================================================

import re
from typing import List, Optional, Dict, Union


def parse_competitor_bids(input_text: str, official_estimate: Optional[float] = None) -> List[float]:
    """Parse competitor bids with robust validation"""
    if not input_text or not input_text.strip():
        return []
    
    bids = []
    parts = re.split(r'[,;\n|\t]', input_text)  # ✅ re module now imported
    
    for part in parts:
        cleaned = re.sub(r'[^\d\.]', '', part.strip())
        if not cleaned or cleaned == '.':
            continue
        try:
            bid = round(float(cleaned), BID_AMOUNT_DECIMALS)
            if bid <= 0:
                continue
            if official_estimate and official_estimate > 0:
                min_valid = official_estimate * 0.3
                max_valid = official_estimate * 3.0
                if not (min_valid <= bid <= max_valid):
                    debug_print(f"⚠️ Filtered outlier bid: {bid:,.3f}")
                    continue
            bids.append(bid)
        except (ValueError, TypeError) as e:
            debug_print(f"⚠️ Could not parse bid '{part.strip()}': {e}")
            continue
    
    return sorted(bids)



# =============================================================================
# 📐 BID CALCULATION CONSTANTS (Module-level for easy tuning)
# =============================================================================

BID_RATIOS: Dict[str, float] = {
    'aggressive': 0.86,
    'moderate': 0.89, 
    'conservative': 0.93
}

BID_BOUNDS: Dict[str, float] = {
    'min_ratio': 0.80,
    'max_ratio': 0.98,
    'valid_range_factor': 2.0  # Bids must be within [0.5x, 2x] of estimate
}

RISK_THRESHOLDS: Dict[str, float] = {
    'high_max': 0.87,
    'medium_max': 0.92
}

WIN_PROB_VALUES: Dict[str, float] = {
    'high': 0.85,    # When bid <= min competitor
    'medium': 0.60,  # When bid between min and avg
    'low': 0.35      # When bid >= avg competitor
}


def calculate_basic_bid(
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str = 'moderate'
) -> Dict[str, Union[float, str, bool]]:
    """
    Calculate basic bid recommendation using statistical heuristics.
    
    Args:
        official_estimate: Government/procuring entity's official estimate
        competitor_bids: List of known competitor bid amounts
        risk_tolerance: User's risk preference ('aggressive', 'moderate', 'conservative')
        
    Returns:
        Dict with bid recommendation (3 decimals), win probability, risk assessment
    """
    debug_print(f"🔢 Calculating basic bid | Estimate: {official_estimate:,.3f}, Risk: {risk_tolerance}")
    if official_estimate <= 0:
        debug_print("❌ Invalid official_estimate <= 0")
        return {
            'optimal_bid': 0.0,
            'bid_ratio': 0.0,
            'win_probability': 0.0,
            'risk_level': 'UNKNOWN',
            'risk_color': '⚪',
            'avg_competitor': 0.0,
            'min_competitor': 0.0,
            'is_premium': False,
            'method': 'Error: Invalid estimate'
        }
    # Filter valid competitor bids
    min_valid = official_estimate / BID_BOUNDS['valid_range_factor']
    max_valid = official_estimate * BID_BOUNDS['valid_range_factor']
    valid_bids = [b for b in competitor_bids if min_valid <= b <= max_valid]
    
    # Compute competitor statistics
    if valid_bids:
        avg_competitor = float(np.mean(valid_bids))
        min_competitor = float(np.min(valid_bids))
        debug_print(f"✓ Valid competitors: {len(valid_bids)}, Avg: {avg_competitor:,.3f}, Min: {min_competitor:,.3f}")
    else:
        # Fallback estimates when no valid competitor data
        avg_competitor = round(official_estimate * 0.92, 3)
        min_competitor = round(official_estimate * 0.85, 3)
        debug_print("⚠️ No valid competitor bids; using fallback estimates")
    
    # Calculate recommended bid with 3 decimal precision
    ratio = BID_RATIOS.get(risk_tolerance.lower(), BID_RATIOS['moderate'])
    recommended_bid = round(official_estimate * ratio, 3)
    
    # Adjust if bid is uncompetitive vs market
    if recommended_bid > avg_competitor:
        recommended_bid = round(avg_competitor * 0.99, 3)
        debug_print(f"📉 Adjusted bid to be competitive: {recommended_bid:,.3f}")
    
    # Enforce hard bounds (with 3 decimal precision)
    min_bound = round(official_estimate * BID_BOUNDS['min_ratio'], 3)
    max_bound = round(official_estimate * BID_BOUNDS['max_ratio'], 3)
    recommended_bid = round(max(min_bound, min(max_bound, recommended_bid)), 3)
    
    # Calculate win probability based on positioning
    if recommended_bid <= min_competitor:
        win_prob = WIN_PROB_VALUES['high']
    elif recommended_bid >= avg_competitor:
        win_prob = WIN_PROB_VALUES['low']
    else:
        win_prob = WIN_PROB_VALUES['medium']
    
    # Determine risk level based on bid ratio
    if ratio < RISK_THRESHOLDS['high_max']:
        risk_level, risk_color = "HIGH", "🔴"
    elif ratio < RISK_THRESHOLDS['medium_max']:
        risk_level, risk_color = "MEDIUM", "🟡"
    else:
        risk_level, risk_color = "LOW", "🟢"
    
    result = {
        'optimal_bid': recommended_bid,
        # ✅ Safe division with guard
        'bid_ratio': round(recommended_bid / official_estimate, BID_RATIO_DECIMALS) if official_estimate > 0 else 0.0,
        'win_probability': win_prob,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'avg_competitor': avg_competitor,
        'min_competitor': min_competitor,
        'is_premium': False,
        'method': 'Basic Statistical Heuristic'
    }
    
    debug_print(f"✓ Basic bid result: BDT {result['optimal_bid']:,.3f} | Win: {win_prob*100:.1f}% | Risk: {risk_level}")
    return result

# =============================================================================
# 📄 PAGE RENDERING FUNCTIONS
# =============================================================================

def home_page() -> None:
    """Render the public home/landing page"""
    debug_print("🏠 Rendering home page")
    
    # Hero section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 2.5rem 1.5rem; border-radius: 16px; text-align: center; margin-bottom: 1.5rem;">
        <h1 style="color: white; font-size: 2.4rem; margin: 0 0 0.8rem 0;">🏗️ TenderAI</h1>
        <p style="color: white; font-size: 1.15rem; margin: 0; opacity: 0.95;">
            AI-Powered Tender Management & Bid Optimization for Bangladesh Construction
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features grid
    st.markdown("### ✨ Why TenderAI?")
    col1, col2, col3 = st.columns(3)
    features = [
        ("🤖", "AI Predictions", "85% accurate winning bid predictions using machine learning"),
        ("📊", "Market Intelligence", "Real-time competitor tracking & historical analysis"),
        ("👥", "Team Collaboration", "Role-based access control for your organization"),
    ]
    for idx, (icon, title, desc) in enumerate(features):
        with [col1, col2, col3][idx]:
            render_feature_card(icon, title, desc)
    
    # CTA section
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Free 14-Day Trial", use_container_width=True, type="primary"):
            navigate_to("register")
        if st.button("💰 View Pricing Plans", use_container_width=True):
            navigate_to("pricing")
    
    debug_print("✅ Home page render complete")

def login_page() -> None:
    """Updated Login Page with URL-Based Remember Me & Better Integration"""
    debug_print("🔐 Rendering login page")
    
    # Initialize session state variables
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'forgot_password_email' not in st.session_state:
        st.session_state.forgot_password_email = ''
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False

    # Import required modules
    from modules.google_auth import render_google_login_button, handle_google_callback
    from modules.individual_registration import authenticate_individual_user
    from modules.auth import login_user, restore_session_from_url
    
    # ✅ Try to restore session from URL (no cookie complexity)
    if not st.session_state.get('logged_in', False):
        try:
            if restore_session_from_url():
                debug_print("Session restored from URL, redirecting to dashboard")
                navigate_to("dashboard")
                st.rerun()
                return
        except Exception as e:
            debug_print(f"Session restore error: {e}")
    
    # Handle Google OAuth callback
    handle_google_callback()
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    render_page_header("🔐 Login", "Access your TenderAI account")
    
    # Display session persistence tip
    if not st.session_state.get('logged_in', False):
        st.info("💡 **Tip:** Check 'Remember me' to stay logged in across browser sessions for 30 days.")
    
    # Create tabs for different login types
    tab1, tab2 = st.tabs(["🏢 Company Login", "👤 Individual Login"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("company_login_form", clear_on_submit=True):
                username = st.text_input("Username or Email", key="comp_login_username")
                password = st.text_input("Password", type="password", key="comp_login_password")
                remember_me = st.checkbox("Remember me (stay logged in for 30 days)", key="comp_remember_me")
                
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        debug_print(f"[LOGIN] Username: {username}, Remember me: {remember_me}")
                        user, status, message = authenticate_user(username, password)
                        debug_print(f"[LOGIN] Auth result: status={status}, user={user is not None}")
                        
                        if status == "pending_approval":
                            st.warning("⚠️ Your account is pending approval by an administrator.")
                        elif user and status == "approved":
                            debug_print(f"[LOGIN] Calling login_user with remember_me={remember_me}")
                            # ✅ Pass cookies=None since we're using URL params
                            if login_user(user, password, remember_me):
                                full_name = user[3] if len(user) > 3 else username
                                debug_print("[LOGIN] Login successful!")
                                st.success(f"Welcome back, {full_name}! 👋")
                                
                                if remember_me:
                                    st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                                
                                navigate_to("dashboard")
                                st.rerun()
                            else:
                                st.error("❌ Login failed. Please try again.")
                        else:
                            st.error(message or "❌ Invalid credentials. Please try again.")
            
            st.markdown("---")
            if st.button("➕ Register New Company Account", use_container_width=True):
                navigate_to("register")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Individual Email Login
            with st.expander("📧 Login with Email", expanded=True):
                with st.form("individual_login_form", clear_on_submit=True):
                    email = st.text_input("Email Address", key="ind_login_email")
                    password = st.text_input("Password", type="password", key="ind_login_password")
                    remember_me_ind = st.checkbox("Remember me (stay logged in for 30 days)", key="ind_remember_me")
                    
                    submitted_ind = st.form_submit_button("Login", use_container_width=True, type="primary")
                    
                    if submitted_ind:
                        if not email or not password:
                            st.error("Please enter both email and password")
                        else:
                            user = authenticate_individual_user(email, password)
                            if user:
                                from modules.email_verification import send_verification_email
                                if send_verification_email(email, user.get('full_name', 'User'), 'login'):
                                    # Store remember_me preference for 2FA completion
                                    st.session_state.pending_2fa = {
                                        'user': user, 
                                        'email': email,
                                        'remember_me': remember_me_ind
                                    }
                                    st.session_state.show_2fa = True
                                    st.success("Verification code sent to your email!")
                                    st.rerun()
                                else:
                                    st.error("Failed to send verification code")
                            else:
                                st.error("❌ Invalid email or password.")

            st.markdown("---")
            st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
            
            # Google Sign-In
            with st.expander("🔐 Sign in with Google", expanded=False):
                st.caption("For consultants, freelancers, and individual users")
                render_google_login_button()
            
            st.markdown("---")
            
            # Registration & Forgot Password Links
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📝 Register as Individual", use_container_width=True):
                    navigate_to(PageRoutes.INDIVIDUAL_REGISTER)
            with col_b:
                if st.button("🔒 Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state.show_forgot_password = True
                    st.rerun()

    # ====================== 2FA Verification ======================
    if st.session_state.get('show_2fa'):
        st.markdown("---")
        st.markdown("### 🔐 Two-Factor Authentication")
        st.info(f"A verification code has been sent to **{st.session_state.pending_2fa['email']}**")
        
        with st.form("2fa_verification_form"):
            otp = st.text_input("Enter 6-digit verification code", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary", use_container_width=True):
                    from modules.email_verification import verify_otp
                    success, message = verify_otp(st.session_state.pending_2fa['email'], otp)
                    
                    if success:
                        user = st.session_state.pending_2fa['user']
                        remember_me = st.session_state.pending_2fa.get('remember_me', False)
                        
                        # Convert user dict to the expected format for login_user
                        user_tuple = (
                            user.get('id'),
                            user.get('username'),
                            user.get('email'),
                            user.get('full_name'),
                            'individual',
                            1,
                            user.get('company_id'),
                            '',
                            None,
                            1,
                            'individual'
                        )
                        
                        # ✅ Login with remember me option (no cookies parameter)
                        if login_user(user_tuple, None, remember_me):
                            st.session_state.show_2fa = False
                            st.session_state.pending_2fa = None
                            
                            if remember_me:
                                st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                            
                            navigate_to("dashboard", success_msg=f"Welcome back, {user.get('full_name', 'User')}! 👋")
                            st.rerun()
                        else:
                            st.error("Login failed. Please try again.")
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code", use_container_width=True):
                    from modules.email_verification import send_verification_email
                    if send_verification_email(
                        st.session_state.pending_2fa['email'], 
                        st.session_state.pending_2fa['user'].get('full_name', 'User'), 
                        'login'
                    ):
                        st.success("New verification code sent!")
                    else:
                        st.error("Failed to resend code")
    
    # ====================== Forgot Password Modal ======================
    if st.session_state.get('show_forgot_password'):
        st.markdown("---")
        st.markdown("### 🔒 Reset Your Password")
        
        with st.form("forgot_password_form", clear_on_submit=True):
            email_input = st.text_input(
                "Enter your registered email", 
                value=st.session_state.get('forgot_password_email', '')
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                send_clicked = st.form_submit_button("Send Reset Link", 
                                                   use_container_width=True, 
                                                   type="primary")
            
            with col2:
                cancel_clicked = st.form_submit_button("Cancel", 
                                                     use_container_width=True, 
                                                     type="secondary")
            
            if send_clicked:
                if not email_input or "@" not in email_input:
                    st.error("Please enter a valid email address")
                else:
                    user = db.get_user_by_email(email_input)
                    if user:
                        import secrets
                        reset_token = secrets.token_urlsafe(32)
                        
                        if db.store_password_reset_token(email_input, reset_token):
                            reset_link = f"https://itender-bd.streamlit.app/reset-password?token={reset_token}"
                            from modules.email_verification import send_password_reset_email
                            
                            if send_password_reset_email(email_input, reset_link):
                                st.success(f"✅ Password reset link sent to **{email_input}**")
                                st.session_state.show_forgot_password = False
                                st.rerun()
                            else:
                                st.error("Failed to send reset email. Please try again.")
                        else:
                            st.error("System error. Please try again later.")
                    else:
                        st.error("No account found with this email.")
            
            if cancel_clicked:
                st.session_state.show_forgot_password = False
                st.rerun()

def login_page_bak() -> None:
    """Updated Login Page with Better Integration (Forgot Password + Navigation)"""
    debug_print("🔐 Rendering login page")
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'forgot_password_email' not in st.session_state:
        st.session_state.forgot_password_email = ''

    from modules.google_auth import render_google_login_button, handle_google_callback
    from modules.individual_registration import authenticate_individual_user
    
    # Handle Google OAuth callback
    handle_google_callback()
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    render_page_header("🔐 Login", "Access your TenderAI account")
    
    # Create tabs for different login types
    tab1, tab2 = st.tabs(["🏢 Company Login", "👤 Individual Login"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("company_login_form", clear_on_submit=True):
                username = st.text_input("Username or Email", key="comp_login_username")
                password = st.text_input("Password", type="password", key="comp_login_password")
                
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        user, status, message = authenticate_user(username, password)
                        
                        if status == "pending_approval":
                            st.warning("⚠️ Your account is pending approval by an administrator.")
                        elif user and status == "approved":
                            login_user(user, password)
                            full_name = user[3] if len(user) > 3 else username
                            st.success(f"Welcome back, {full_name}! 👋")

                            navigate_to("dashboard")
                        else:
                            st.error(message or "❌ Invalid credentials. Please try again.")
            
            st.markdown("---")
            if st.button("➕ Register New Company Account", use_container_width=True):
                navigate_to("register")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Individual Email Login
            with st.expander("📧 Login with Email", expanded=True):
                with st.form("individual_login_form", clear_on_submit=True):
                    email = st.text_input("Email Address", key="ind_login_email")
                    password = st.text_input("Password", type="password", key="ind_login_password")
                    
                    submitted_ind = st.form_submit_button("Login", use_container_width=True, type="primary")
                    
                    if submitted_ind:
                        if not email or not password:
                            st.error("Please enter both email and password")
                        else:
                            user = authenticate_individual_user(email, password)
                            if user:
                                from modules.email_verification import send_verification_email
                                if send_verification_email(email, user.get('full_name', 'User'), 'login'):
                                    st.session_state.pending_2fa = {'user': user, 'email': email}
                                    st.session_state.show_2fa = True
                                    st.success("Verification code sent to your email!")
                                    st.rerun()
                                else:
                                    st.error("Failed to send verification code")
                            else:
                                st.error("❌ Invalid email or password.")

            st.markdown("---")
            st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
            
            # Google Sign-In
            with st.expander("🔐 Sign in with Google", expanded=False):
                st.caption("For consultants, freelancers, and individual users")
                render_google_login_button()
            
            st.markdown("---")
            
            # Registration & Forgot Password Links
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📝 Register as Individual", use_container_width=True):
                    navigate_to(PageRoutes.INDIVIDUAL_REGISTER)
            with col_b:
                if st.button("🔒 Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state.show_forgot_password = True
                    st.rerun()

    # ====================== 2FA Verification ======================
    if st.session_state.get('show_2fa'):
        st.markdown("---")
        st.markdown("### 🔐 Two-Factor Authentication")
        st.info(f"A verification code has been sent to **{st.session_state.pending_2fa['email']}**")
        
        with st.form("2fa_verification_form"):
            otp = st.text_input("Enter 6-digit verification code", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary", use_container_width=True):
                    from modules.email_verification import verify_otp
                    success, message = verify_otp(st.session_state.pending_2fa['email'], otp)
                    
                    if success:
                        user = st.session_state.pending_2fa['user']
                        # Set session state
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.session_state.username = user.get('username')
                        st.session_state.user_email = user['email']
                        st.session_state.full_name = user['full_name']
                        st.session_state.user_role = 'individual'
                        st.session_state.account_type = 'individual'
                        st.session_state.company_id = user.get('company_id')
                        
                        st.session_state.show_2fa = False
                        st.session_state.pending_2fa = None
                        
                        navigate_to("dashboard", success_msg=f"Welcome back, {user['full_name']}! 👋")
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code", use_container_width=True):
                    from modules.email_verification import send_verification_email
                    if send_verification_email(
                        st.session_state.pending_2fa['email'], 
                        st.session_state.pending_2fa['user'].get('full_name', 'User'), 
                        'login'
                    ):
                        st.success("New verification code sent!")
                    else:
                        st.error("Failed to resend code")
    
    # ====================== Forgot Password Modal ======================
    if st.session_state.get('show_forgot_password'):
        st.markdown("---")
        st.markdown("### 🔒 Reset Your Password")
        
        with st.form("forgot_password_form", clear_on_submit=True):
            email_input = st.text_input(
                "Enter your registered email", 
                value=st.session_state.get('forgot_password_email', '')
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                send_clicked = st.form_submit_button("Send Reset Link", 
                                                   use_container_width=True, 
                                                   type="primary")
            
            with col2:
                cancel_clicked = st.form_submit_button("Cancel", 
                                                     use_container_width=True, 
                                                     type="secondary")
            
            if send_clicked:
                if not email_input or "@" not in email_input:
                    st.error("Please enter a valid email address")
                else:
                    user = db.get_user_by_email(email_input)
                    if user:
                        import secrets
                        reset_token = secrets.token_urlsafe(32)
                        
                        if db.store_password_reset_token(email_input, reset_token):
                            reset_link = f"https://itender-bd.streamlit.app/reset-password?token={reset_token}"
                            from modules.email_verification import send_password_reset_email
                            
                            if send_password_reset_email(email_input, reset_link):
                                st.success(f"✅ Password reset link sent to **{email_input}**")
                                st.session_state.show_forgot_password = False
                                st.rerun()
                            else:
                                st.error("Failed to send reset email. Please try again.")
                        else:
                            st.error("System error. Please try again later.")
                    else:
                        st.error("No account found with this email.")
            
            if cancel_clicked:
                st.session_state.show_forgot_password = False
                st.rerun()


def register_page() -> None:
    """Registration Page - Separate flows for Company vs Individual"""
    debug_print("📝 Rendering registration page")
    
    render_page_header("📝 Create New Account", "Choose the account type that best fits you")
    
    # Tabs for clear separation
    tab1, tab2 = st.tabs(["🏢 Company Registration", "👤 Individual Registration"])
    
    # ====================== COMPANY REGISTRATION ======================
    with tab1:
        st.markdown("### 🏢 Register as a Company")
        st.caption("For construction companies, contractors, and organizations (requires admin approval)")
        
        with st.form("company_register_form", clear_on_submit=True):
            st.markdown("#### Company Information")
            company_name = st.text_input("Company Name *", key="comp_reg_name")
            company_email = st.text_input("Company Email *", key="comp_reg_email")
            company_phone = st.text_input("Company Phone *", key="comp_reg_phone")
            division = st.selectbox("Division / Region *", 
                ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"],
                key="comp_reg_division"
            )
            
            st.markdown("#### Admin Account Details")
            full_name = st.text_input("Full Name (Admin) *", key="comp_reg_fullname")
            email = st.text_input("Admin Email *", key="comp_reg_admin_email")
            username = st.text_input("Username *", key="comp_reg_username")
            
            password = st.text_input("Password *", type="password", key="comp_reg_password")
            confirm_password = st.text_input("Confirm Password *", type="password", key="comp_reg_confpass")
            
            # Password Strength
            if password:
                score, message, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<p style='color:{color}; font-size:0.9em;'>{message}</p>", unsafe_allow_html=True)
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *", key="comp_reg_terms")
            
            submitted = st.form_submit_button("Submit Company Registration", 
                                            use_container_width=True, 
                                            type="primary")
            
            if submitted:
                if not all([company_name, company_email, full_name, email, username, password, division]):
                    st.error("❌ Please fill all required fields.")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match.")
                elif len(password) < 8:
                    st.error("❌ Password must be at least 8 characters.")
                elif score < 60:
                    st.error("❌ Password is too weak.")
                elif not terms:
                    st.error("❌ You must accept the terms.")
                else:
                    try:
                        company_data = {
                            'company_name': company_name.strip(),
                            'email': company_email.strip(),
                            'phone': company_phone.strip(),
                            'division': division
                        }
                        
                        success, result = db.create_company(company_data)
                        
                        if success:
                            company_id = result
                            user_data = {
                                'username': username.strip(),
                                'password': password,
                                'email': email.strip(),
                                'full_name': full_name.strip(),
                                'phone': company_phone.strip(),
                                'role': 'company_admin',
                                'account_type': 'company',
                                'is_approved': False
                            }
                            
                            user_success, user_result = db.create_user(company_id, user_data, None)
                            
                            if user_success:
                                st.success("✅ Company registration submitted successfully!")
                                st.info("Your account is under review. You will receive an email once approved (usually within 24-48 hours).")
                                navigate_to("login")
                            else:
                                st.error(f"❌ User creation failed: {user_result}")
                        else:
                            st.error(f"❌ Company creation failed: {result}")
                    except Exception as e:
                        logger.error("Company registration error", exc_info=True)
                        st.error("❌ An error occurred. Please try again.")
    
        # ====================== INDIVIDUAL REGISTRATION ======================
    with tab2:
        # Use the imported individual registration module
        from modules.individual_registration import render_individual_registration
        render_individual_registration()

    
    # Sidebar / Info Box
    with st.sidebar:
        st.markdown("### 📋 Registration Guidelines")
        st.markdown("""
        **Company Accounts:**
        - Require admin approval
        - Suitable for teams
        - Full platform access after approval
        
        **Individual Accounts:**
        - Faster activation
        - Ideal for freelancers & consultants
        - Auto-approved
        """)
        
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")
    
    debug_print("✅ Registration page render complete")


def pricing_page() -> None:
    """Pricing plans page with interactive selection"""
    debug_print("💰 Rendering pricing page")
    
    # Import and call the subscription module
    from modules.subscription import render_subscription_page
    render_subscription_page()
    
    debug_print("✅ Pricing page render complete")




def about_page_bak() -> None:
    """About us page - Comprehensive company information"""
    debug_print("ℹ️ Rendering about page")
    
    # Add animation CSS
    st.markdown("""
    <style>
        
         /* Reset global font size for landing page only */
        .main .stMarkdown, .main div, .main p, .main span, .main label {
            font-size: 1rem !important;
            line-height: 1.5 !important;
        }
                
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .fade-up {
            animation: fadeInUp 0.8s ease-out;
        }
        
        .slide-left {
            animation: slideInLeft 0.6s ease-out;
        }
        
        .slide-right {
            animation: slideInRight 0.6s ease-out;
        }
        
        .tech-card {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .tech-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .stat-card {
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .bio-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 1.5rem;
            border-radius: 16px;
            margin: 1rem 0;
            transition: transform 0.3s ease;
        }
        
        .bio-card:hover {
            transform: translateX(5px);
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_page_header("ℹ️ About Us", "Revolutionizing Bangladesh construction with AI")
    
    # =========================================================================
    # COMPANY OVERVIEW (with animation)
    # =========================================================================
    st.markdown("""
    <div class="fade-up" style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); 
                padding: 2rem; border-radius: 16px; margin-bottom: 2rem;">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🏢 Who We Are</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            TenderAI is Bangladesh's first AI-powered tender management platform, 
            created by <strong>Shomon Robie</strong>, an entrepreneur, digital innovator, 
            and Managing Director of <strong>Babui Limited</strong>. With extensive 
            experience in digital marketing, IT, and algorithmic trading through 
            his successful venture <strong>LakshmiFX</strong>, Shomon brings cutting-edge 
            AI and machine learning expertise to the construction procurement space. 
            TenderAI represents the culmination of years of experience in developing 
            high-precision prediction systems, now applied to help Bangladeshi 
            construction companies win more tenders.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # MISSION & VISION (Animated columns)
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="slide-left" style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: 100%;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎯</div>
            <h3 style="color: #1e3a8a; margin-bottom: 1rem;">Our Mission</h3>
            <p style="line-height: 1.6;">
                To democratize access to advanced AI-driven insights for 
                construction companies in Bangladesh, enabling smarter bidding 
                decisions, reducing financial risk, and increasing win rates 
                in public procurement tenders. We're committed to making 
                cutting-edge technology accessible, affordable, and impactful 
                for businesses of all sizes.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="slide-right" style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: 100%;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">👁️</div>
            <h3 style="color: #1e3a8a; margin-bottom: 1rem;">Our Vision</h3>
            <p style="line-height: 1.6;">
                To become the undisputed leader in AI-powered tender management 
                across South Asia, transforming how infrastructure projects are 
                planned, bid, and delivered. We envision a future where data-driven 
                decision-making is the standard, not the exception, in public 
                procurement.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # =========================================================================
    # CORE VALUES (Animated)
    # =========================================================================
    st.markdown("### 🌟 Our Core Values")
    
    values_cols = st.columns(4)
    values = [
        ("🔬", "Innovation", "Continuously pushing the boundaries of AI in procurement"),
        ("🤝", "Integrity", "Transparent, ethical, and PPR 2025 compliant solutions"),
        ("🎯", "Excellence", "Delivering 85%+ accurate predictions consistently"),
        ("🌱", "Growth", "Empowering Bangladeshi businesses to thrive"),
    ]
    
    for idx, (icon, title, desc) in enumerate(values):
        with values_cols[idx]:
            st.markdown(f"""
            <div class="fade-up" style="text-align: center; padding: 1rem; transition: transform 0.3s;">
                <div style="font-size: 2rem;">{icon}</div>
                <h4 style="color: #1e3a8a; margin: 0.5rem 0;">{title}</h4>
                <p style="font-size: 0.85rem; color: #666;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # IMPACT METRICS (Animated)
    # =========================================================================
    st.markdown("### 📊 Our Impact")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("🏆", "Win Rate Increase", "+23%", "Average improvement for our users"),
        ("💰", "Savings per Tender", "৳2.4L", "Average cost savings"),
        ("⏱️", "Time Saved", "4.2 hours", "Per analysis on average"),
        ("🏢", "Companies Served", "150+", "Across Bangladesh"),
    ]
    
    for idx, (icon, label, value, caption) in enumerate(metrics):
        with [col1, col2, col3, col4][idx]:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 1rem; border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 2rem;">{icon}</div>
                <div style="font-size: 1.8rem; font-weight: bold;">{value}</div>
                <div style="font-size: 0.85rem; margin: 0.25rem 0;">{label}</div>
                <div style="font-size: 0.7rem; opacity: 0.8;">{caption}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # FOUNDER BIO SECTION (Updated with accurate information)
    # =========================================================================
    st.markdown("### 👨‍💼 About the Founder")
    
    st.markdown("""
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Who is Shomon Robie?</h3>
        <p><strong>Entrepreneur & Digital Founder:</strong> Shomon Robie is the Founder & CEO of <strong>VisitBangladesh.com.bd</strong>, 
        a travel-oriented website focused on promoting tourism and experiences in Bangladesh. With a background in digital 
        marketing and IT spanning many years, Shomon built the travel platform to showcase Bangladesh's rich culture and 
        diverse destinations.</p>
    </div>
    
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Business & Professional Roles</h3>
        <p><strong>Managing Director of Babui:</strong> Records from the Bangladesh Computer Samity list Shomon Robie as the 
        Managing Director of <strong>Babui Limited</strong>, a Dhaka-based company involved in business services and technology activities.</p>
        <p style="margin-top: 0.5rem;"><strong>Babui's Activities:</strong> Under his leadership as Director/CEO, Babui Limited engages in 
        corporate management, information services, and web/computer-related business activities, serving clients across Bangladesh.</p>
    </div>
    
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Technical Contributions</h3>
        <p><strong>Developer of LakshmiFX:</strong> Shomon Robie is credited as the developer of <strong>LakshmiFX</strong>, 
        a MetaTrader 5 automated trading tool (Expert Advisor) used for forex and other financial markets. 
        The detailed manual for LakshmiFX credits him as the developer and outlines the tool's advanced features 
        and trading purposes.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    
    # =========================================================================
    # TECHNOLOGY STACK (Fixed - using st.html for better rendering)
    # =========================================================================
    st.markdown("### 🛠️ Technology Stack")
    # Add CSS to ensure equal height columns
    # Add CSS to ensure equal height columns and consistent styling
    st.markdown("""
    <style>
        /* Reset global font size for about page as like as landing page */
        .main .stMarkdown, .main div, .main p, .main span, .main label {
            font-size: 1rem !important;
            line-height: 1.5 !important;
        }
        
        /* Equal height columns */
        .stColumn {
            display: flex;
        }
        
        .tech-card-full {
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 12px;
            width: 100%;
            min-height: 550px;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .tech-card-full:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .tech-card-full h4 {
            margin-top: 0;
            margin-bottom: 0.75rem;
            color: #1e3a8a;
            font-size: 1.1rem !important;
            font-weight: 600;
        }
        
        /* Consistent styling for both ul and p */
        .tech-card-full ul, 
        .tech-card-full p,
        .tech-card-full li {
            font-size: 0.9rem !important;
            line-height: 1.5 !important;
            color: #475569;
            margin-bottom: 0.75rem;
        }
        
        .tech-card-full ul {
            padding-left: 1.2rem;
            margin: 0 0 1rem 0;
        }
        
        .tech-card-full li {
            margin-bottom: 0.5rem;
        }
        
        .tech-card-full p {
            margin: 0 0 1rem 0;
        }
        
        .tech-card-full ul:last-child,
        .tech-card-full p:last-child {
            margin-bottom: 0;
        }
    </style>
    """, unsafe_allow_html=True)


    col1, col2 = st.columns(2)

    with col1:
        # Use st.html for cleaner HTML rendering (Streamlit 1.36+)
        st.html("""
        <div class="tech-card fade-up" style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; height: 100%;">
            <h4>🤖 Artificial Intelligence & Machine Learning</h4>
            <ul>
                <li>Scikit-learn for statistical modeling</li>
                <li>XGBoost for gradient boosting</li>
                <li>Custom ensemble models for bid prediction</li>
                <li>Time series analysis for market trends</li>
            </ul>
            
            <h4>⚙️ Backend & Infrastructure</h4>
            <ul>
                <li>Python 3.12 with FastAPI</li>
                <li>PostgreSQL for data persistence</li>
                <li>Docker for containerization</li>
                <li>AWS/GCP ready deployment</li>
            </ul>
            
            <h4>🎨 Frontend & Visualization</h4>
            <ul>
                <li>Streamlit for interactive UI</li>
                <li>Plotly for dynamic charts</li>
                <li>ReportLab for PDF generation</li>
                <li>Custom CSS for professional styling</li>
            </ul>
        </div>
        """)

    with col2:
        st.html("""
        <div class="tech-card fade-up" style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; height: 100%;">
            <h4>✅ PPR 2025 Compliant</h4>
            <ul>
                <li>Our algorithms are built specifically for Bangladesh's Public Procurement Rules 2025, ensuring full compliance with government regulations.</li>
            </ul>    
            
            <h4>✅ 85% Prediction Accuracy</h4>
            <ul>
                <li>Trained on thousands of historical tenders, our AI models achieve industry-leading accuracy in bid success predictions.</li>
            </ul>
            
            <h4>✅ Real-time Market Intelligence</h4>
            <ul>
                <li>Stay ahead with live competitor tracking, market trends, and intelligent bid recommendations.</li>
            </ul>
            
            <h4>✅ Enterprise-Grade Security</h4>
            <ul>
                <li>Your data is protected with encryption, secure authentication, and regular security audits.</li>
            </ul>
            
            <h4>✅ Dedicated Support</h4>
            <ul>
                <li>24/7 technical support, training, and consultation to ensure your success.</li>
            </ul>
        </div>
        """)


    
    # =========================================================================
    # TESTIMONIALS
    # =========================================================================
    st.markdown("### 💬 What Our Users Say")
    
    testimonial_cols = st.columns(2)
    
    testimonials = [
        ("⭐⭐⭐⭐⭐", "TenderAI has transformed our bidding process. We've seen a 30% increase in our win rate within just 3 months!", "— Md. Karim, ABC Construction"),
        ("⭐⭐⭐⭐⭐", "The AI recommendations are incredibly accurate. Saved us hours of manual analysis and helped us win 5 major contracts.", "— Shahnaz Begum, BuildTech Ltd."),
    ]
    
    for idx, (rating, text, author) in enumerate(testimonials):
        with testimonial_cols[idx]:
            st.markdown(f"""
            <div class="fade-up" style="background: #f0fdf4; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">{rating}</div>
                <p style="font-style: italic; line-height: 1.5;">"{text}"</p>
                <p style="font-weight: bold; margin-top: 0.5rem;">{author}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # CALL TO ACTION
    # =========================================================================
    st.markdown("""
    <div class="fade-up" style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                padding: 2rem; border-radius: 16px; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem;">Ready to Transform Your Bidding Strategy?</h3>
        <p style="margin-bottom: 1.5rem;">Join hundreds of construction companies already using TenderAI</p>
        <div style="display: flex; gap: 1rem; justify-content: center;">
            <a href="#" onclick="parent.postMessage({type: 'streamlit:setPageValue', value: 'register'}, '*')" 
               style="background: #22c55e; color: white; text-decoration: none; padding: 0.75rem 2rem; 
                      border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: bold; display: inline-block;">
                Start Free Trial
            </a>
            <a href="#" onclick="parent.postMessage({type: 'streamlit:setPageValue', value: 'contact'}, '*')" 
               style="background: transparent; color: white; text-decoration: none; border: 1px solid white; 
                      padding: 0.75rem 2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; display: inline-block;">
                Contact Sales
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    debug_print("✅ About page render complete")



def contact_page() -> None:
    """Contact us page with form"""
    debug_print("📞 Rendering contact page")
    
    render_page_header("📞 Contact Us", "We're here to help")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("contact_form", clear_on_submit=True):
            name = st.text_input("Your Name *", key="contact_name")
            email = st.text_input("Your Email *", key="contact_email")
            subject = st.selectbox("Subject", 
                ["General Inquiry", "Technical Support", "Sales Question", "Partnership", "Other"],
                key="contact_subject"
            )
            message = st.text_area("Message *", height=150, key="contact_message")
            
            submitted = st.form_submit_button("Send Message", use_container_width=True, type="primary")
            
            if submitted:
                if not all([name, email, message]):
                    st.error("❌ Please fill all required fields")
                else:
                    try:
                        db.save_contact_message(name, email, subject, message)
                        st.success("✅ Thank you! We'll get back to you within 24 hours.")
                        # Clear form by rerunning
                        st.rerun()
                    except Exception as e:
                        debug_print(f"❌ Contact form error: {e}")
                        st.error("❌ Failed to send message. Please try again or email support@tenderai.com")
    
    with col2:
        st.markdown("### 📬 Other Ways to Reach Us")
        st.markdown("""
        **Email**  
        📧 support@tenderai.com  
        📧 sales@tenderai.com  
        
        **Phone**  
        📱 +880 1XXX-XXXXXX (Sat-Thu, 9AM-6PM)  
        
        **Office**  
        📍 Dhaka, Bangladesh  
        """)
        
        st.markdown("### ⏱️ Response Times")
        st.markdown("""
        - **Technical Support**: < 4 hours (business days)  
        - **Sales Inquiries**: < 24 hours  
        - **General Questions**: < 48 hours  
        """)
    
    debug_print("✅ Contact page render complete")
    
def dashboard_page() -> None:
    """Main dashboard for authenticated users"""
    
    # No need for separate header - top navigation handles it
    # Just render dashboard content
        # Add card CSS
    st.markdown("""
    <style>
    .metric-card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        border: 1px solid var(--border-color);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    
    # Get stats
    stats = db.get_company_stats(st.session_state.company_id) if st.session_state.company_id else {'total_analyses': 0, 'win_rate': 0, 'total_users': 1}
    
    with col1:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col2:
        win_rate = stats.get('win_rate', 0)
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("👥 Team Members", stats.get('total_users', 1))
    with col4:
        sub = db.get_user_subscription(st.session_state.user_id)
        limit = sub.get('analyses_limit', 5)
        used = sub.get('analyses_used', 0)
        remaining = "∞" if limit == -1 else max(0, limit - used)
        st.metric("📊 Analyses Left", remaining)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Tenders", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    
    with col2:
        if st.button("📊 BOQ Generator", use_container_width=True):
            st.session_state.page = "boq_generator"
            st.rerun()
    
    with col3:
        print("🔍 RENDERING DASHBOARD PAGE - START NEW ANALYSIS BUTTON")
        if st.button("🔍 Start New Analysis", key="dashboard_start_new_analysis_btn", use_container_width=True, type="primary"):
            navigate_to("new_analysis")

    with col4:
        if st.button("🎯 Bid Optimizer", use_container_width=True):
            st.session_state.page = "boq_bid_optimizer"
            st.rerun()
    
    with col5:
        if st.session_state.user_role in ['admin', 'system_admin', 'company_admin']:
            if st.button("👥 Team Management", use_container_width=True):
                st.session_state.page = "user_management"
                st.rerun()
    
    # Recent analyses table
    st.markdown("### 🕐 Recent Analyses")
    
    try:
        recent_df = db.get_user_analyses(
            user_id=st.session_state.user_id,
            company_id=st.session_state.company_id,
            role=st.session_state.user_role,
            limit=5
        )
        
        if recent_df is not None and not recent_df.empty:
            # Display recent analyses
            for _, analysis in recent_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1.5, 1])
                with col1:
                    st.markdown(analysis.get('tender_title', 'Untitled')[:50])
                with col2:
                    st.markdown(f"BDT {analysis.get('recommended_bid', 0):,.0f}")
                with col3:
                    win_prob = analysis.get('success_probability', 0) or 0
                    win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                    st.markdown(f"{win_pct:.1f}%")
                with col4:
                    status = analysis.get('bid_status', 'draft')
                    emoji = {"won": "🏆", "lost": "❌", "submitted": "📤", "draft": "⚪"}.get(status, "⚪")
                    st.markdown(f"{emoji} {status.title()}")
                with col5:
                    if st.button("View", key=f"view_{analysis.get('id')}"):
                        st.session_state.selected_analysis_id = analysis.get('id')
                        st.session_state.page = "history"
                        st.rerun()
                st.markdown("---")
        else:
            st.info("📭 No analyses yet. Start your first analysis!")
    except Exception as e:
        st.info("📭 Start your first analysis to see recent activity here!")

def dashboard_page_bak() -> None:
    """Main dashboard for authenticated users"""
    debug_print("📊 Rendering dashboard page")
    debug_print("".join(traceback.format_stack()[-5:]))  # Show last 5 lines of stack

    #ensure_admin_premium()
    if st.session_state.get('user_role') == 'admin':
        if st.sidebar.button("🔧 Go to Admin Dashboard (Debug)"):
            st.session_state.page = "admin_dashboard"
            st.rerun()

    full_name = st.session_state.get('full_name', 'User')
    company_name = st.session_state.get('company_name', 'N/A')
    plan = str(st.session_state.get('subscription_plan', 'free')).upper()
    sub_status = st.session_state.get('subscription_status')
    status_display = str(sub_status).title() if sub_status is not None else 'Unknown'
    
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0;">Welcome, {full_name}! 👋</h1>
        <p style="margin: 0.3rem 0 0 0; opacity: 0.9;">
            {company_name} • {plan} Plan • {status_display}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    stats = db.get_company_stats(st.session_state.company_id)
    sub = db.get_user_subscription(st.session_state.user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col2:
        win_rate = stats.get('win_rate', 0) * 100
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("👥 Team Members", stats.get('total_users', 1))
    with col4:
        limit = sub.get('analyses_limit', 5)
        used = sub.get('analyses_used', 0)
        remaining = "∞" if limit == -1 else max(0, limit - used)
        st.metric("📊 Analyses Left", remaining)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        print("🔍 RENDERING DASHBOARD PAGE - START NEW ANALYSIS BUTTON")
        if st.button("🔍 Start New Analysis", key="dashboard_start_new_analysis_btn", use_container_width=True, type="primary"):
            navigate_to("new_analysis")
    with col2:
        if st.button("📜 View History", key="dashboard_view_history_btn", use_container_width=True):
            navigate_to("history")
    with col3:
        if st.button("👤 My Profile", key="dashboard_my_profile_btn", use_container_width=True):
            navigate_to("profile")
    
    # Role-specific actions
    if st.session_state.user_role in ['admin', 'company_admin']:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👥 Manage Team", key="dashboard_manage_team_btn", use_container_width=True):
                navigate_to("user_management")
        with col2:
            if st.button("💳 Subscription", key="dashboard_subscription_btn", use_container_width=True):
                navigate_to("subscription")
    
    # Recent Analyses section
    st.markdown("### 🕐 Recent Analyses")
    try:
        recent_df = db.get_user_analyses(
            user_id=st.session_state.user_id,
            company_id=st.session_state.company_id,
            role=st.session_state.user_role,
            limit=5
        )
        
        if recent_df is not None and not recent_df.empty:
            recent_records = recent_df.to_dict('records')
            
            col1, col2, col3, col4, col5, col6 = st.columns([2.5, 2, 1.2, 1, 1.2, 0.8])
            with col1:
                st.markdown("**<span style='font-size:0.75rem;'>Tender Title</span>**", unsafe_allow_html=True)
            with col2:
                st.markdown("**<span style='font-size:0.75rem;'>Bid Amount</span>**", unsafe_allow_html=True)
            with col3:
                st.markdown("**<span style='font-size:0.75rem;'>Win Chance</span>**", unsafe_allow_html=True)
            with col4:
                st.markdown("**<span style='font-size:0.75rem;'>Status</span>**", unsafe_allow_html=True)
            with col5:
                st.markdown("**<span style='font-size:0.75rem;'>Created</span>**", unsafe_allow_html=True)
            with col6:
                st.markdown("**<span style='font-size:0.75rem;'></span>**", unsafe_allow_html=True)
            
            st.markdown("---")
            
            for idx, analysis in enumerate(recent_records):
                cols = st.columns([2.5, 2, 1.2, 1, 1.2, 0.8])
                
                with cols[0]:
                    title = str(analysis.get('tender_title', 'Untitled'))[:50]
                    st.markdown(f"<span style='font-size:0.75rem;' title='{analysis.get('tender_title', '')}'>{title}</span>", unsafe_allow_html=True)
                
                with cols[1]:
                    bid = analysis.get('recommended_bid', 0) or 0
                    st.markdown(f"<span style='font-size:0.75rem;'>BDT {bid:,.3f}</span>", unsafe_allow_html=True)
                
                with cols[2]:
                    win_prob = analysis.get('success_probability', 0) or 0
                    win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                    st.markdown(f"<span style='font-size:0.75rem;'>{win_pct:.1f}%</span>", unsafe_allow_html=True)
                    st.progress(min(win_pct / 100, 1.0), text="")
                
                with cols[3]:
                    status = analysis.get('bid_status', 'draft') or 'draft'
                    status_emoji = {"won": "🏆", "lost": "❌", "submitted": "📤", "draft": "⚪"}.get(status.lower(), "⚪")
                    st.markdown(f"<span style='font-size:0.75rem;'>{status_emoji} {status.title()}</span>", unsafe_allow_html=True)
                
                with cols[4]:
                    created_date = str(analysis.get('analysis_date', ''))[:16] if analysis.get('analysis_date') else "N/A"
                    created_by = analysis.get('created_by', 'System')
                    if not created_by or created_by == 'System':
                        created_by = st.session_state.get('full_name', 'User')[:15]
                    st.markdown(f"<span style='font-size:0.7rem;'>{created_date}<br><span style='color:#666;'>by {created_by}</span></span>", unsafe_allow_html=True)
                
                with cols[5]:
                    analysis_id = analysis.get('id')
                    button_key = f"dashboard_view_{analysis_id}_{idx}"
                    if st.button("📄", key=button_key, help="View details", use_container_width=True):
                        st.session_state.selected_analysis_id = analysis_id
                        st.session_state.page = "history"
                        st.rerun()
                
                st.markdown("---")
            
            if st.button("📊 View All Analyses →", key="dash_view_all", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()
        else:
            st.info("📭 No analyses yet. Run your first analysis in Three-Tier Bid Optimization!")
    except Exception as e:
        st.warning(f"Could not load recent analyses: {str(e)}")
        st.info("📭 Start your first analysis to see recent activity here!")
    
    debug_print("✅ Dashboard page render complete")

def safe_date_slice(date_value, length: int = 10) -> str:
    """Safely slice date values (handles Timestamp, str, None)"""
    if date_value is None:
        return 'N/A'
    date_str = str(date_value)
    return date_str[:length] if len(date_str) >= length else date_str
def history_page() -> None:
    """History page - delegates to analysis_history module"""
    debug_print("📜 Rendering history page from analysis_history module")
    
    # Import and call the module's function
    from modules.analysis_history import show_analysis_history
    show_analysis_history()

def _export_analysis_csv(analysis: Dict) -> None:
    """Export single analysis to CSV (helper for history page)"""
    try:
        import csv
        import io
        
        # Define fields to export
        fields = [
            'tender_id', 'tender_title', 'procuring_entity', 'official_estimate',
            'recommended_bid', 'success_probability', 'risk_level', 'analysis_type',
            'analysis_date', 'bid_status'
        ]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerow({k: analysis.get(k, '') for k in fields})
        
        # Trigger download
        csv_data = output.getvalue()
        output.close()
        
        tender_id = str(analysis.get('tender_id', 'export')).replace('/', '_')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"analysis_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")
        if DEBUG_MODE:
            st.code(traceback.format_exc(), language="python")

def profile_page() -> None:
    """User profile view and edit"""
    debug_print("👤 Rendering profile page")
    
    render_page_header("👤 My Profile", "View and update your account information")
    
    # Fetch fresh user data
    user = db.get_user_by_id(st.session_state.user_id)
    
    if not user:
        st.error("❌ Could not load user profile. Please try logging in again.")
        if st.button("→ Return to Dashboard"):
            navigate_to("dashboard")
        return
    
    # Display user info (read-only for now; add edit form if needed)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Account Details")
        st.info(f"**Full Name:** {user[5] if len(user) > 5 else 'N/A'}")
        st.info(f"**Username:** {user[1] if len(user) > 1 else 'N/A'}")
        st.info(f"**Email:** {user[4] if len(user) > 4 else 'N/A'}")
        st.info(f"**Phone:** {user[7] if len(user) > 7 and user[7] else 'Not provided'}")
    
    with col2:
        st.markdown("### 🏢 Company & Role")
        st.info(f"**Company:** {user[14] if len(user) > 14 else 'N/A'}")
        role_value = user[6] if (user and len(user) > 6 and user[6] is not None) else 'N/A'
        st.info(f"**Role:** {str(role_value).title()}")
        st.info(f"**Account Status:** {'✅ Active' if user[8] else '⏳ Pending'}" if len(user) > 8 else "**Status:** N/A")
        
        # Subscription info
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub:
            st.markdown("---")
            st.markdown("### 💳 Subscription")
            st.info(f"**Plan:** {sub.get('plan', 'free').upper()}")
            sub_status = sub.get('status') if sub else None
            status_display = str(sub_status).title() if sub_status is not None else 'Unknown'
            st.info(f"**Status:** {status_display}")
            if sub.get('analyses_limit', 5) == -1:
                st.info("**Analyses:** Unlimited")
            else:
                used = sub.get('analyses_used', 0)
                limit = sub.get('analyses_limit', 5)
                st.info(f"**Analyses:** {used}/{limit} used this month")
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.info("Profile editing coming soon! Contact support@tenderai.com for updates.")
    with col2:
        if st.button("🔐 Change Password", use_container_width=True):
            st.info("Password change feature coming soon!")
    with col3:
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode']:  # Preserve debug setting
                    del st.session_state[key]
            initialize_session_state()  # Re-init with defaults
            navigate_to("home", success_msg="You have been signed out. 👋")
    
    debug_print("✅ Profile page render complete")


def render_comparison(
    basic_result: Dict, 
    advanced_result: Dict, 
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """
    Render side-by-side comparison between basic and advanced analysis.
    
    Note: This is the 2-tier version. For 3-tier, use display_analysis_results_with_report()
    """
    debug_print("🆚 Rendering comparison: Basic vs Advanced")
    
    st.markdown("### 🆚 Analysis Comparison: Basic vs Advanced")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Basic Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {basic_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {basic_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {basic_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {basic_result['risk_color']} {basic_result['risk_level']}")
        st.caption(f"Method: {basic_result.get('method', 'Statistical')}")
    
    with col2:
        st.markdown("#### 🧠 Advanced ML Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {advanced_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {advanced_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {advanced_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {advanced_result['risk_color']} {advanced_result['risk_level']}")
        st.caption(f"Method: {advanced_result.get('method', 'ML Ensemble')}")
    
    # Difference analysis
    diff = advanced_result['optimal_bid'] - basic_result['optimal_bid']
    diff_percent = (diff / official_estimate) * 100 if official_estimate else 0
    
    st.markdown("---")
    st.markdown("#### 💡 Analysis Insight")
    
    if abs(diff) < official_estimate * 0.005:  # 0.5% threshold
        st.info("📊 Both analyses suggest very similar bid amounts (within 0.5%). The market appears stable and predictable.")
    elif diff > 0:
        st.warning(f"""
        📈 Advanced analysis suggests **increasing bid by BDT {diff:,.3f}** ({diff_percent:+.2f}% of estimate) 
        for optimal outcome. This accounts for:
        - Historical competitor patterns
        - Market condition adjustments
        - Risk-optimized positioning
        """)
    else:
        st.success(f"""
        📉 Advanced analysis suggests **decreasing bid by BDT {abs(diff):,.3f}** ({diff_percent:+.2f}% of estimate) 
        to improve win probability while maintaining profitability. This leverages:
        - Identified competitor weaknesses
        - Optimal risk-reward positioning
        - ML-predicted market response
        """)
    
    # Win probability comparison
    win_diff = advanced_result['win_probability'] - basic_result['win_probability']
    if win_diff > 0.10:
        st.success(f"🎯 Advanced ML analysis shows **+{win_diff*100:.0f}% higher win probability** due to identified competitor patterns and market dynamics.")
    elif win_diff < -0.10:
        st.warning(f"⚠️ Advanced analysis shows **-{abs(win_diff)*100:.0f}% win probability** – this may indicate aggressive competitor clustering or market saturation. Review carefully.")
    
    st.markdown("---")
    st.markdown("#### ✅ Recommendation")
    
    # For admin, default to advanced; for others, respect subscription
    if st.session_state.user_role == 'admin' or st.session_state.subscription_plan in ['professional', 'enterprise']:
        recommended = advanced_result
        rec_label = "Advanced ML Analysis"
        rec_icon = "🧠"
    else:
        recommended = basic_result
        rec_label = "Basic Analysis"
        rec_icon = "📊"
    
    st.info(f"""
    {rec_icon} **Recommended Bid:** BDT {recommended['optimal_bid']:,.3f}  
    Based on {rec_label} • Win probability: {recommended['win_probability']*100:.0f}% • Risk: {recommended['risk_color']} {recommended['risk_level']}
    """)
    
    # Save button hint
    if st.session_state.get('current_analysis_record'):
        st.caption("💡 Click '💾 Save Analysis' below to store this recommendation in your history.")
    
    debug_print("✅ Comparison render complete")



# =============================================================================
# 🎨 UI HELPER COMPONENTS (Extracted for reusability)
# =============================================================================

def render_tender_info_card(tender_data: Dict) -> None:  # ← Correct: tender_data (parameter name)
    """Render a compact tender information summary card"""
    # Now use tender_data consistently inside:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea;">
        <strong>📋 {tender_data.get('tender_title', 'Untitled')[:60]}{'...' if len(tender_data.get('tender_title',''))>60 else ''}</strong><br>
        <small>
            ID: {tender_data.get('tender_id', 'N/A')} • 
            Entity: {tender_data.get('procuring_entity', 'N/A')[:40]}<br>
            Estimate: BDT {tender_data.get('official_estimate', 0):,.3f} • 
            Deadline: {tender_data.get('submission_deadline', 'N/A')}
        </small>
    </div>
    """, unsafe_allow_html=True)

def safe_title(value, default: str = 'N/A') -> str:
    """
    Safely convert any value to title case.
    Handles None, non-strings, and empty values gracefully.
    
    Args:
        value: Any value (str, None, int, etc.)
        default: Fallback string if value is None/empty
    
    Returns:
        Title-cased string or default
    """
    if value is None:
        return default
    try:
        return str(value).strip().title() if str(value).strip() else default
    except Exception:
        return default


def render_competitor_bid_row(idx: int, competitor_Dict, competitor_options: Dict, key_prefix: str) -> tuple:
    """
    Render a single competitor bid input row.
    Returns updated competitor entry dict.
    """
    col_a, col_b, col_c, col_d = st.columns([2.5, 2, 1.5, 0.5])
    
    with col_a:
        if competitor_options:
            name = st.selectbox(
                "Competitor",
                options=[""] + list(competitor_options.keys()),
                index=list(competitor_options.keys()).index(competitor_entry['name']) if competitor_entry['name'] in competitor_options else 0,
                key=f"{key_prefix}_name_{idx}",
                label_visibility="collapsed"
            )
        else:
            name = st.text_input("Competitor", value=competitor_entry['name'], key=f"{key_prefix}_name_{idx}", label_visibility="collapsed")
    
    with col_b:
        bid = st.number_input(
            "Bid (BDT)",
            min_value=0.0,
            value=float(competitor_entry['bid']),
            step=100000.0,  # 1 lakh steps for easier input
            format="%.3f",  # 3 decimal precision
            key=f"{key_prefix}_bid_{idx}",
            label_visibility="collapsed"
        )
    
    with col_c:
        was_winner = st.checkbox(
            "Winner?",
            value=competitor_entry.get('was_winner', False),
            key=f"{key_prefix}_winner_{idx}"
        )
    
    with col_d:
        remove = st.button("🗑️", key=f"{key_prefix}_remove_{idx}", help="Remove this competitor")
    
    return {
        'name': name,
        'bid': round(bid, 3),  # Ensure 3 decimal precision
        'was_winner': was_winner,
        'remove': remove
    }


def render_ppr_metrics_card(label: str, value: str, caption: str, warning: bool = False) -> None:
    """Render a PPR compliance metric with optional warning styling"""
    border_color = "#dc3545" if warning else "#28a745"
    bg_color = "#fff5f5" if warning else "#f0fff4"
    
    st.markdown(f"""
    <div style="background: {bg_color}; padding: 0.75rem; border-radius: 8px; 
                border-left: 3px solid {border_color}; text-align: center;">
        <div style="font-size: 0.8rem; color: #666;">{label}</div>
        <div style="font-size: 1.3rem; font-weight: bold; color: #1e3c72; margin: 0.25rem 0;">{value}</div>
        <div style="font-size: 0.7rem; color: #888;">{caption}</div>
    </div>
    """, unsafe_allow_html=True)


def calculate_ppr_compliance(official_estimate: float, competitor_bids: List[float], recommended_bid: float) -> Dict:
    """
    Calculate PPR 2025 compliance metrics.
    
    Returns dict with all calculated values for display.
    """
    # PPR 2025 constants
    NPPI_FACTOR = 0.920
    WEIGHTS = {'competitor_avg': 0.5, 'official_est': 0.2, 'nppi': 0.3}
    
    # Calculate NPPI price
    nppi_price = round(official_estimate * NPPI_FACTOR, 3)
    
    # Competitor statistics
    if competitor_bids:
        avg_competitor = float(np.mean(competitor_bids))
        competitor_sample = competitor_bids[:5]  # Use first 5 for std dev
    else:
        # Fallback estimates
        avg_competitor = round(official_estimate * 0.91, 3)
        competitor_sample = [
            round(official_estimate * p, 3) 
            for p in [0.88, 0.90, 0.92, 0.94, 0.95]
        ]
    
    # Weighted average (X̄)
    weighted_avg = round(
        WEIGHTS['competitor_avg'] * avg_competitor +
        WEIGHTS['official_est'] * official_estimate +
        WEIGHTS['nppi'] * nppi_price,
        3
    )
    
    # Weighted standard deviation (Sd)
    if len(competitor_sample) > 0:
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_sample]
        variance = sum(squared_deviations) / len(competitor_sample)
        weighted_std = round(np.sqrt(variance), 3)
    else:
        weighted_std = 0.0
    
    # SLT Threshold
    slt_threshold = round(weighted_avg - weighted_std, 3)
    
    # Evaluation
    is_below_slt = recommended_bid < slt_threshold
    compliance_status = "NON-COMPLIANT ⚠️" if is_below_slt else "COMPLIANT ✅"
    
    return {
        'nppi_factor': NPPI_FACTOR,
        'nppi_price': nppi_price,
        'avg_competitor': avg_competitor,
        'weighted_avg': weighted_avg,
        'weighted_std': weighted_std,
        'slt_threshold': slt_threshold,
        'recommended_bid': recommended_bid,
        'is_below_slt': is_below_slt,
        'compliance_status': compliance_status,
        'competitor_sample': competitor_sample,
        'squared_deviations': squared_deviations if 'squared_deviations' in locals() else []
    }


# =============================================================================
# 📊 REFACTORED: Tender Analysis Page (UI Optimized)
# =============================================================================
@st.cache_data(ttl=300)  # Cache for 5 minutes
def _get_company_tenders_cached(company_id: int) -> pd.DataFrame:
    """Cached helper to fetch company tenders as DataFrame"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
            t.division, t.district, t.thana, t.country, t.procurement_type,
            t.official_estimate, t.submission_deadline, t.tender_security,
            t.document_fee, t.evaluation_type,
            -- ✅ Locking columns:
            t.is_locked, t.is_copy, t.original_tender_id, t.is_active,
            t.created_at, t.updated_at
        FROM company_tenders t
        WHERE t.company_id = ? 
        ORDER BY t.created_at DESC
        ''', (company_id,))
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch cached tenders: {e}")
        return pd.DataFrame()


def _process_competitor_bids_input(
    bid_source: str, 
    official_estimate: float, 
    tender_id: str,
    competitor_options: Dict[str, int],
    session_key: str = 'analysis_competitor_bids'
) -> List[float]:
    """
    Handle competitor bid input logic (auto-generate or manual entry).
    Returns list of bid amounts (floats, 3 decimal precision).
    """
    competitor_bids = []
    
    if bid_source == "Enter manually":
        # Manual entry mode
        if session_key not in st.session_state:
            st.session_state[session_key] = []
        
        # Render competitor input rows
        num_competitors = st.number_input(
            "Number of competitors", 
            min_value=0, 
            max_value=20, 
            value=max(3, len(st.session_state[session_key])),
            key=f"{session_key}_count"
        )
        
        # Process existing entries
        updated_entries = []
        for idx, entry in enumerate(st.session_state[session_key]):
            updated = render_competitor_bid_row(idx, entry, competitor_options, session_key)
            if not updated['remove'] and updated['name'] and updated['bid'] > 0:
                updated_entries.append({
                    'name': updated['name'],
                    'bid': updated['bid'],
                    'was_winner': updated['was_winner']
                })
        
        st.session_state[session_key] = updated_entries
        
        # Add new competitor section
        with st.expander("➕ Add New Competitor", expanded=False):
            col_a, col_b, col_c, col_d = st.columns([2, 2, 1.5, 0.5])
            with col_a:
                new_name = st.selectbox(
                    "Select from master list", 
                    options=[""] + list(competitor_options.keys()),
                    key=f"{session_key}_new_name"
                )
            with col_b:
                new_bid = st.number_input(
                    "Bid Amount (BDT)",
                    min_value=0.0,
                    value=round(official_estimate * 0.90, 3) if official_estimate > 0 else 0.0,
                    step=100000.0,
                    format="%.3f",
                    key=f"{session_key}_new_bid"
                )
            with col_c:
                new_winner = st.checkbox("Winner?", key=f"{session_key}_new_winner")
            with col_d:
                add_clicked = st.button("Add", key=f"{session_key}_add_btn")
            
            if add_clicked and new_name and new_bid > 0:
                existing_names = [e['name'] for e in st.session_state[session_key]]
                if new_name not in existing_names:
                    st.session_state[session_key].append({
                        'name': new_name,
                        'bid': round(new_bid, 3),
                        'was_winner': new_winner
                    })
                    st.toast(f"✅ Added {new_name}", icon="🎯")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {new_name} already in list")
        
        # Extract bid amounts
        competitor_bids = [round(e['bid'], 3) for e in st.session_state[session_key]]
        
        # Show summary if bids exist
        if competitor_bids:
            with st.expander("📊 Competitor Summary", expanded=True):
                summary_df = pd.DataFrame([
                    {
                        'Competitor': e['name'],
                        'Bid (BDT)': f"{e['bid']:,.3f}",
                        '% of Estimate': f"{e['bid']/official_estimate*100:.2f}%" if official_estimate > 0 else "N/A",
                        'Winner': '🏆' if e.get('was_winner') else ''
                    }
                    for e in st.session_state[session_key]
                ])
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("🗑️ Clear All", key=f"{session_key}_clear", use_container_width=True):
                        st.session_state[session_key] = []
                        st.rerun()
    
    else:
        # Auto-generate mode
        num_competitors = st.slider(
            "Number of competitors to simulate", 
            min_value=3, 
            max_value=15, 
            value=7,
            key=f"{session_key}_auto_count"
        )
        
        # Clear manual entries when switching to auto
        if session_key in st.session_state:
            st.session_state[session_key] = []
        
        # Generate realistic bids with seeded randomness
        seed_val = hash(f"{tender_id}_{official_estimate}_{num_competitors}") % (2**32)
        np.random.seed(seed_val)
        
        base_ratios = np.random.uniform(0.85, 0.98, num_competitors)
        noise = np.random.uniform(-0.03, 0.03, num_competitors)
        final_ratios = np.clip(base_ratios + noise, 0.80, 1.00)
        
        competitor_bids = [round(official_estimate * r, 3) for r in final_ratios]
        
        # Show preview
        with st.expander("🤖 Auto-Generated Bids Preview", expanded=True):
            preview_df = pd.DataFrame({
                'Simulated Bidder': [f"Bidder {i+1}" for i in range(num_competitors)],
                'Bid Amount (BDT)': [f"{b:,.3f}" for b in competitor_bids],
                '% of Estimate': [f"{b/official_estimate*100:.2f}%" for b in competitor_bids]
            })
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            st.caption("💡 Bids are simulated based on historical patterns. Switch to 'Enter manually' for real competitor data.")
    
    return competitor_bids

def load_tender_into_form(tender_data):
    """Load tender data into session state model"""
    st.session_state.tender_form_data.update({
        'tender_id': str(tender_data.get('tender_id', '')),
        'tender_title': str(tender_data.get('tender_title', '')),
        'procuring_entity': str(tender_data.get('procuring_entity', '')),
        'division': str(tender_data.get('division', 'Dhaka')),
        'district': str(tender_data.get('district', '')),
        'thana': str(tender_data.get('thana', '')),
        'official_estimate': float(tender_data.get('official_estimate', 0) or 0),
        'tender_security': float(tender_data.get('tender_security', 0) or 0),
        'document_fee': float(tender_data.get('document_fee', 0) or 0),
        'procurement_type': str(tender_data.get('procurement_type', 'works'))
    })

def sync_form_to_model():
    """Sync form widget values to the model before rerun"""
    data = st.session_state.tender_form_data
    data['tender_id'] = st.session_state.get('input_tender_id', data['tender_id'])
    data['tender_title'] = st.session_state.get('input_tender_title', data['tender_title'])
    data['procuring_entity'] = st.session_state.get('input_procuring_entity', data['procuring_entity'])
    data['division'] = st.session_state.get('input_division', data['division'])
    data['district'] = st.session_state.get('input_district', data['district'])
    data['thana'] = st.session_state.get('input_thana', st.session_state.get('input_thana_text', data['thana']))
    data['official_estimate'] = st.session_state.get('input_official_estimate', data['official_estimate'])
    data['tender_security'] = st.session_state.get('input_tender_security', data['tender_security'])
    data['document_fee'] = st.session_state.get('input_document_fee', data['document_fee'])
    data['procurement_type'] = st.session_state.get('input_procurement_type', data['procurement_type'])
    data['risk_tolerance'] = st.session_state.get('analysis_risk_tolerance', data['risk_tolerance'])

def model_to_form():
    """Push model values to form widgets"""
    st.session_state.input_tender_id = st.session_state.tender_form_data['tender_id']
    st.session_state.input_tender_title = st.session_state.tender_form_data['tender_title']
    st.session_state.input_procuring_entity = st.session_state.tender_form_data['procuring_entity']
    st.session_state.input_division = st.session_state.tender_form_data['division']
    st.session_state.input_district = st.session_state.tender_form_data['district']
    st.session_state.input_thana = st.session_state.tender_form_data['thana']
    st.session_state.input_official_estimate = st.session_state.tender_form_data['official_estimate']
    st.session_state.input_tender_security = st.session_state.tender_form_data['tender_security']
    st.session_state.input_document_fee = st.session_state.tender_form_data['document_fee']
    st.session_state.input_procurement_type = st.session_state.tender_form_data['procurement_type']
    st.session_state.analysis_risk_tolerance = st.session_state.tender_form_data['risk_tolerance']



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

def render_sidebar_2() -> None:
    """Optimized sidebar with role-based navigation - ONLY for logged-in users"""
    # Only show sidebar if user is logged in
    if not st.session_state.get('logged_in'):
        return
    
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        # Clear extracted data if leaving tender management page
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        
        from version import get_app_name, get_app_desc

        # ========== BRANDING ==========
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ {get_app_name()}</h2>
            <small style="color: #666;">{get_app_desc()}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== USER INFO & BADGE ==========
        if st.session_state.get('logged_in'):
            full_name = st.session_state.get('full_name', 'User')
            company_name = st.session_state.get('company_name', 'N/A')
            user_role = st.session_state.get('user_role', 'User')
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>👋 {full_name}</strong><br>
                <small>🏢 {company_name}<br>
                ⭐ {safe_title(user_role, 'User')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            sub = db.get_user_subscription(st.session_state.user_id) if st.session_state.get('user_id') else {}
            plan = sub.get('plan', 'free')
            is_premium = plan in ['professional', 'enterprise'] or st.session_state.get('user_role') in ['admin', 'system_admin']
            badge_color = "#22c55e" if is_premium else "#6b7280"
            badge_text = "✨ PREMIUM" if is_premium else "🔓 FREE TRIAL"
            
            st.markdown(f"""
            <div style="text-align: center; background: {badge_color}20; 
                        padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                        border: 1px solid {badge_color};">
                <strong style="color: {badge_color};">{badge_text}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # ========== SECTION 1: CORE WORKFLOW ==========
        user_role = st.session_state.get('user_role', 'user')
        
        st.markdown("### 🚀 Core Workflow")
        
        # 1. Tender Management (Everyone)
        _nav_button("📋 Tender Management", "tender_management")
        
        # 2. BOQ Generator (Everyone except viewer)
        if user_role != 'viewer':
            _nav_button("📄 BOQ Generator", "boq_generator")
        
        # 3. BOQ to Bid Optimizer (Everyone except viewer)
        if user_role != 'viewer':
            _nav_button("🎯 BOQ to Bid Optimizer", "boq_bid_optimizer")
        
        st.markdown("---")
        
        # ========== SECTION 2: ANALYSIS & INTELLIGENCE ==========
        st.markdown("### 📊 Analysis & Intelligence")
        
        _nav_button("📈 Dashboard", "dashboard")
        _nav_button("🎯 New Analysis", "new_analysis")
        _nav_button("📜 History", "history")
        
        # Premium features
        if is_premium:
            _nav_button("📊 Historical Data", "historical_data")
            _nav_button("👥 Competitor Tracking", "competitor_tracking")
            _nav_button("🗂️ Competitor Master", "competitor_master")
            _nav_button("📋 Post-Evaluation", "post_evaluation")
            _nav_button("🧠 AI Suggestions", "intelligent_suggestions")
        
        st.markdown("---")
        
        # ========== SECTION 3: COMPANY MANAGEMENT ==========
        if user_role in ['company_admin', 'admin', 'system_admin']:
            st.markdown("### 🏢 Company Management")
            
            _nav_button("🏢 Company Dashboard", "company_dashboard")
            _nav_button("🏗️ e-GP BOQ Workspace", "egp_boq_workspace")
            _nav_button("👥 Team Management", "user_management")
            
            st.markdown("---")
        
        # ========== SECTION 4: RATE MANAGEMENT ==========
        if user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'data_entry']:
            st.markdown("### 🏗️ Rate Management")
            
            _nav_button("📝 Rate Management", "rate_management")
            _nav_button("📊 Rate Viewer", "rate_viewer")
            
            st.markdown("---")
        
        # ========== SECTION 5: ADMINISTRATION ==========
        if user_role in ['admin', 'system_admin']:
            st.markdown("### 👑 Administration")
            
            _nav_button("📊 Admin Dashboard", "admin_dashboard")
            _nav_button("📊 BOQ Report", "boq_admin_report")
            
            # Badge for pending approvals
            pending_count = 0
            try:
                if hasattr(db, 'get_pending_users'):
                    pending_count = len(db.get_pending_users(None))
            except:
                pass
            
            _nav_button("👥 User Approvals", "user_approval", badge=pending_count if pending_count > 0 else None)
            _nav_button("🔐 Role Permissions", "role_management")
            _nav_button("🏢 All Companies", "company_management")
            
            st.markdown("---")
        
        # ========== SECTION 6: SYSTEM TOOLS ==========
        st.markdown("### ⚙️ System Tools")
        
        # Version Management (Admins only)
        if user_role in ['admin', 'system_admin']:
            _nav_button("📦 Version Management", "version_management")
            _nav_button("🔄 Rollback Management", "rollback_management")
        
        _nav_button("💳 Subscription", "subscription")
        _nav_button("👤 Profile", "profile")
        
        st.markdown("---")
        
        # ========== SECTION 7: HELP & SUPPORT ==========
        st.markdown("### 📚 Help & Support")
        
        _nav_button("📖 Tutorial", "tutorial")
        
        st.markdown("---")
        
        # ========== USAGE STATS ==========
        if is_premium and sub:
            limit = sub.get('analyses_limit', -1)
            used = sub.get('analyses_used', 0)
            if limit > 0:
                remaining = max(0, limit - used)
                pct_used = min(100, (used / limit) * 100)
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>📊 Monthly Usage</strong><br>
                    {used}/{limit} analyses used<br>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                        <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <small>{remaining} remaining this month</small>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
        
        # ========== LOGOUT ==========
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
        
        # Debug mode indicator
        if DEBUG_MODE:
            st.markdown("---")
            st.caption("🐛 Debug Mode Active")


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
        
        # Company Management
        "company_dashboard": "company_dashboard",
        "egp_boq_workspace": "egp_boq_workspace",
        "user_management": "user_management",
        
        # Rate Management
        "rate_management": "rate_management",
        "rate_viewer": "rate_viewer",
        
        # Administration
        "admin_dashboard": "admin_dashboard",
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
    """Optimized sidebar with role-based navigation - ONLY for logged-in users"""
    # Only show sidebar if user is logged in
    if not st.session_state.get('logged_in'):
        return
    
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        # Clear extracted data if leaving tender management page
        
         # ========== DARK MODE TOGGLE - CALLED ONCE ==========
        render_dark_mode_toggle()
        st.markdown("---")
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        
        from version import get_app_name, get_app_desc

        # ========== BRANDING ==========
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ {get_app_name()}</h2>
            <small style="color: #666;">{get_app_desc()}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== USER INFO & BADGE ==========
        if st.session_state.get('logged_in'):
            full_name = st.session_state.get('full_name', 'User')
            company_name = st.session_state.get('company_name', 'N/A')
            user_role = st.session_state.get('user_role', 'User')
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>👋 {full_name}</strong><br>
                <small>🏢 {company_name}<br>
                ⭐ {safe_title(user_role, 'User')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            sub = db.get_user_subscription(st.session_state.user_id) if st.session_state.get('user_id') else {}
            plan = sub.get('plan', 'free')
            is_premium = plan in ['professional', 'enterprise'] or st.session_state.get('user_role') in ['admin', 'system_admin']
            badge_color = "#22c55e" if is_premium else "#6b7280"
            badge_text = "✨ PREMIUM" if is_premium else "🔓 FREE TRIAL"
            
            st.markdown(f"""
            <div style="text-align: center; background: {badge_color}20; 
                        padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                        border: 1px solid {badge_color};">
                <strong style="color: {badge_color};">{badge_text}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # ========== LOGOUT BUTTON (MOVED TO TOP FOR VISIBILITY) ==========
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
        
        # ========== SECTION 1: CORE WORKFLOW ==========
        user_role = st.session_state.get('user_role', 'user')
        
        st.markdown("### 🚀 Core Workflow")
        
        # 1. Tender Management (Everyone)
        _nav_button("📋 Tender Management", "tender_management")
        
        # 2. BOQ Generator (Everyone except viewer)
        if user_role != 'viewer':
            _nav_button("📄 BOQ Generator", "boq_generator")
        
        # 3. BOQ to Bid Optimizer (Everyone except viewer)
        if user_role != 'viewer':
            _nav_button("🎯 BOQ to Bid Optimizer", "boq_bid_optimizer")
        
        st.markdown("---")
        
        # ========== SECTION 2: ANALYSIS & INTELLIGENCE ==========
        st.markdown("### 📊 Analysis & Intelligence")
        
        _nav_button("📈 Dashboard", "dashboard")
        _nav_button("🎯 New Analysis", "new_analysis")
        _nav_button("📜 History", "history")
        
        # Premium features
        if is_premium:
            _nav_button("📊 Historical Data", "historical_data")
            _nav_button("👥 Competitor Tracking", "competitor_tracking")
            _nav_button("🗂️ Competitor Master", "competitor_master")
            _nav_button("📋 Post-Evaluation", "post_evaluation")
            _nav_button("🧠 AI Suggestions", "intelligent_suggestions")
        
        st.markdown("---")
        
        # ========== SECTION 3: COMPANY MANAGEMENT ==========
        if user_role in ['company_admin', 'admin', 'system_admin']:
            st.markdown("### 🏢 Company Management")
            
            _nav_button("🏢 Company Dashboard", "company_dashboard")
            _nav_button("🏗️ e-GP BOQ Workspace", "egp_boq_workspace")
            _nav_button("👥 Team Management", "user_management")
            
            st.markdown("---")
        
        # ========== SECTION 4: RATE MANAGEMENT ==========
        if user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'data_entry']:
            st.markdown("### 🏗️ Rate Management")
            
            _nav_button("📝 Rate Management", "rate_management")
            _nav_button("📊 Rate Viewer", "rate_viewer")
            
            st.markdown("---")
        
        # ========== SECTION 5: ADMINISTRATION ==========
        if user_role in ['admin', 'system_admin']:
            st.markdown("### 👑 Administration")
            
            _nav_button("📊 Admin Dashboard", "admin_dashboard")
            _nav_button("📊 BOQ Report", "boq_admin_report")
            
            # Badge for pending approvals
            pending_count = 0
            try:
                if hasattr(db, 'get_pending_users'):
                    pending_count = len(db.get_pending_users(None))
            except:
                pass
            
            _nav_button("👥 User Approvals", "user_approval", badge=pending_count if pending_count > 0 else None)
            _nav_button("🔐 Role Permissions", "role_management")
            _nav_button("🏢 All Companies", "company_management")
            
            st.markdown("---")
        
        # ========== SECTION 6: SYSTEM TOOLS ==========
        st.markdown("### ⚙️ System Tools")
        
        # Version Management (Admins only)
        if user_role in ['admin', 'system_admin']:
            _nav_button("📦 Version Management", "version_management")
            _nav_button("🔄 Rollback Management", "rollback_management")
        
        _nav_button("💳 Subscription", "subscription")
        _nav_button("👤 Profile", "profile")
        
        st.markdown("---")
        
        # ========== SECTION 7: HELP & SUPPORT ==========
        st.markdown("### 📚 Help & Support")
        
        _nav_button("📖 Tutorial", "tutorial")
        
        st.markdown("---")
        
        # ========== USAGE STATS ==========
        if is_premium and sub:
            limit = sub.get('analyses_limit', -1)
            used = sub.get('analyses_used', 0)
            if limit > 0:
                remaining = max(0, limit - used)
                pct_used = min(100, (used / limit) * 100)
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>📊 Monthly Usage</strong><br>
                    {used}/{limit} analyses used<br>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                        <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <small>{remaining} remaining this month</small>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
        
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
        
        # Debug mode indicator
        if DEBUG_MODE:
            st.markdown("---")
            st.caption("🐛 Debug Mode Active")

def render_sidebar_3() -> None:
    """Optimized sidebar with role-based navigation - ONLY for logged-in users"""
    # Only show sidebar if user is logged in
    if not st.session_state.get('logged_in'):
        return
    
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        # Clear extracted data if leaving tender management page
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        from version import get_app_name, get_app_desc

        # ========== BRANDING ==========
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ {get_app_name()}</h2>
            <small style="color: #666;">{get_app_desc()}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== USER INFO & BADGE ==========
        if st.session_state.get('logged_in'):
            # Get user info safely
            full_name = st.session_state.get('full_name', 'User')
            company_name = st.session_state.get('company_name', 'N/A')
            user_role = st.session_state.get('user_role', 'User')
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>👋 {full_name}</strong><br>
                <small>🏢 {company_name}<br>
                ⭐ {safe_title(user_role, 'User')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            sub = db.get_user_subscription(st.session_state.user_id) if st.session_state.get('user_id') else {}
            plan = sub.get('plan', 'free')
            is_premium = plan in ['professional', 'enterprise'] or st.session_state.get('user_role') in ['admin', 'system_admin']
            badge_color = "#22c55e" if is_premium else "#6b7280"
            badge_text = "✨ PREMIUM" if is_premium else "🔓 FREE TRIAL"
            
            st.markdown(f"""
            <div style="text-align: center; background: {badge_color}20; 
                        padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                        border: 1px solid {badge_color};">
                <strong style="color: {badge_color};">{badge_text}</strong>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
        
        # ========== DEFINE MENU STRUCTURES ==========
        # Authenticated main menu
        main_menu = [
            ("📈", "Dashboard", "dashboard"),
            ("🎯", "New Analysis", "new_analysis"),
            ("📜", "History", "history"),
            ("👤", "Profile", "profile"),
        ]
        
        # Company management menu (for company_admin and admin)
        company_management_menu = [
            ("👥", "Team Management", "user_management"),
            ("📋", "Tender Management", "tender_management"),
        ]
        if st.button("📊 BOQ to Bid Optimizer", key="nav_boq_bid", use_container_width=True):
            st.session_state.page = "boq_bid_optimizer"
            st.rerun()

        # Premium intelligence menu
        intelligence_menu = [
            ("📊", "Historical Data", "historical_data"),
            ("👥", "Competitor Tracking", "competitor_tracking"),
            ("🗂️", "Competitor Master", "competitor_master"),
        ]
        
        # Evaluation tools (premium)
        evaluation_menu = [
            ("📋", "Post-Evaluation", "post_evaluation"),
            ("🧠", "AI Suggestions", "intelligent_suggestions"),
        ]
        
        # System Admin menu
        system_admin_menu = [
            ("📊", "Admin Dashboard", "admin_dashboard"),
            ("👥", "User Approvals", "user_approval"),
            ("🔐", "Role Permissions", "role_management"),
            ("🏢", "All Companies", "company_management"),
        ]
        
        # ========== RENDER BASED ON LOGIN STATE ==========
        user_role = st.session_state.get('user_role', 'user')
        
        # 1. Main menu
        st.markdown("### 📊 Main")
        for icon, label, page in main_menu:
            render_nav_button(label, page, icon=icon)
        
        # 2. Subscription management (standalone button)
        if st.button("💳 Subscription", key="nav_subscription", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()
        
        # 3. Company Dashboard (for company_admin and admin)
        if user_role in ['company_admin', 'admin', 'system_admin']:
            if st.button("🏢 Company Dashboard", key="nav_company_dashboard", use_container_width=True):
                st.session_state.page = "company_dashboard"
                st.rerun()
        
        # 4. Company Management (for company_admin and admin)
        if user_role in ['company_admin', 'admin', 'system_admin']:
            st.markdown("---")
            st.markdown("### 👥 Company Management")
            render_nav_button("e-GP BOQ Workspace", "egp_boq_workspace", icon="🏗️")
            for icon, label, page in company_management_menu:
                render_nav_button(label, page, icon=icon)
            
            # Evaluation tools (premium)
            if is_premium:
                st.markdown("#### 📊 Evaluation")
                for icon, label, page in evaluation_menu:
                    render_nav_button(label, page, icon=icon, button_type="secondary")
                
                
        st.markdown("---")
        st.markdown("### 📚 Help")
        if st.button("📖 Tutorial & Documentation", key="nav_tutorial", use_container_width=True):
            st.session_state.page = "tutorial"
            st.rerun()

        # 5. Intelligence features (premium only)
        if is_premium:
            st.markdown("---")
            st.markdown("### 📚 Intelligence")
            for icon, label, page in intelligence_menu:
                render_nav_button(label, page, icon=icon, button_type="secondary")
        
        # 6. System Admin section (only for system_admin)
        if user_role == 'system_admin':
            st.markdown("---")
            st.markdown("### 👑 System Admin")
            
            # Badge for pending approvals
            pending_count = 0
            try:
                if hasattr(db, 'get_pending_users'):
                    pending_count = len(db.get_pending_users(None))
            except:
                pass
            
            for icon, label, page in system_admin_menu:
                badge = str(pending_count) if label == "User Approvals" and pending_count > 0 else None
                render_nav_button(label, page, icon=icon, badge=badge, button_type="secondary")
        
        # 7. Legacy Admin section (for backward compatibility)
        elif user_role == 'admin':
            st.markdown("---")
            st.markdown("### 👑 System Admin")
            
            for icon, label, page in system_admin_menu:
                render_nav_button(label, page, icon=icon, button_type="secondary")
        
        if user_role in ['admin', 'system_admin']:
            st.markdown("---")
            st.markdown("### 📊 BOQ Management")
            
            if st.button("📄 BOQ Generator", key="nav_boq_generator", use_container_width=True):
                st.session_state.page = "boq_generator"
                st.rerun()
            
            if st.button("📊 BOQ Report", key="nav_boq_report", use_container_width=True):
                st.session_state.page = "boq_admin_report"
                st.rerun()

        # ========== LOGOUT & USAGE STATS ==========
        st.markdown("---")
        
        # Usage stats for premium users
        if is_premium and sub:
            limit = sub.get('analyses_limit', -1)
            used = sub.get('analyses_used', 0)
            if limit > 0:
                remaining = max(0, limit - used)
                pct_used = min(100, (used / limit) * 100)
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>Analyses:</strong> {used}/{limit} used<br>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                        <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <small>{remaining} remaining this month</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Logout button
       

        if st.button("🚪 Sign Out", key="nav_logout", use_container_width=True, type="secondary"):
            logout_user()  # This will clear cookies

            for key in list(st.session_state.keys()):
                if key not in ['debug_mode', 'page']:
                    del st.session_state[key]
            initialize_session_state()
            st.toast("👋 You have been signed out", icon="✅")
            st.rerun()
    # Add version info at the bottom of sidebar
    from version import __version__, __version_date__
    st.markdown("---")
    st.caption(f"📌 Version {__version__} | {__version_date__}")
    st.caption("💡 Need help? [Contact Support](mailto:support@tenderai.com)")

    # Debug mode indicator
    if DEBUG_MODE:
        st.markdown("---")
        st.caption("🐛 Debug Mode Active")



# =============================================================================
# 🎬 MAIN APP ROUTER (Refactored + Optimized)
# =============================================================================

def _render_public_pages() -> None:
    """Render pages for non-authenticated users"""
    from modules.individual_registration import render_individual_registration, render_individual_login
    
    page_handlers = {
        'home': lambda: show_landing_page(),  # Use the new landing page
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': lambda: show_about_page(),  # Use the new about page
        'contact': contact_page,
        'individual_register': render_individual_registration,
        'individual_login': render_individual_login,
    }
    
    handler = page_handlers.get(st.session_state.page, home_page)
    handler()

def _render_authenticated_pages_bak() -> None:
    """Render pages for authenticated users with lazy module imports"""
    
    # Get user role
    user_role = st.session_state.get('user_role', 'viewer')
    is_admin = user_role in ['admin', 'system_admin']
    
    PAGE_HANDLERS: Dict[str, Callable] = {
        # Core pages
        PageRoutes.DASHBOARD: dashboard_page,
        PageRoutes.NEW_ANALYSIS: tender_analysis_page,
        PageRoutes.HISTORY: history_page,
        PageRoutes.PROFILE: profile_page,
        PageRoutes.SUBSCRIPTION: lambda: _handle_subscription_redirect(),
        PageRoutes.CHECKOUT: lambda: _import_and_call('subscription', 'render_checkout'),
        
        # Password reset
        PageRoutes.FORGOT_PASSWORD: lambda: _import_and_call('auth', 'render_forgot_password'),
        PageRoutes.RESET_PASSWORD: lambda: _import_and_call('auth', 'render_reset_password'),
        
        # ========== SUBSCRIBER PAGES ==========
        PageRoutes.COMPANY_DASHBOARD: lambda: render_subscriber_dashboard(db) if not is_admin else show_company_dashboard(),
        PageRoutes.TENDER_MANAGEMENT: lambda: _import_and_call('modules.tender_management', 'render_tender_management'),
        PageRoutes.BOQ_GENERATOR: lambda: _import_and_call('modules.boq_generator_ui', 'render_boq_generator'),
        PageRoutes.BOQ_BID_OPTIMIZER: lambda: _import_and_call('modules.boq_bid_bridge', 'render_boq_bid_integration'),
        PageRoutes.BOQ_ADMIN_REPORT: lambda: _import_and_call('modules.boq_admin_report', 'render_boq_admin_report') if is_admin else _access_denied(),
        
        # ========== ADMIN ONLY PAGES ==========
        PageRoutes.ADMIN_DASHBOARD: lambda: _import_and_call('_pages.admin_dashboard', 'show') if is_admin else _access_denied(),
        PageRoutes.USER_MANAGEMENT: lambda: _import_and_call('modules.user_management', 'render_user_management'),
        PageRoutes.USER_APPROVAL: lambda: _import_and_call('modules.user_approval', 'render_user_approval_page') if is_admin else _access_denied(),
        PageRoutes.ROLE_MANAGEMENT: lambda: _import_and_call('modules.user_management', 'render_role_management') if is_admin else _access_denied(),
        PageRoutes.NEW_ANALYSIS: render_tender_analysis,

        
        # ========== ADD THESE MISSING HANDLERS ==========
        PageRoutes.RATE_MANAGEMENT: lambda: render_rate_crud_forms(db),
        PageRoutes.IMPORT_WIZARD: lambda: render_unified_import_wizard(db),
        PageRoutes.RATE_VIEWER: lambda: _import_and_call('modules.rate_viewer', 'render_rate_viewer'),

        # ========== PREMIUM FEATURES (Subscription Check) ==========
        PageRoutes.HISTORICAL_DATA: lambda: _handle_premium_feature(lambda: _import_and_call('modules.historical_data', 'render_historical_data_page')),
        PageRoutes.ANALYSIS_HISTORY: lambda: _handle_premium_feature(lambda: _import_and_call('modules.analysis_history', 'show_analysis_history')),
        PageRoutes.COMPETITOR_TRACKING: lambda: _handle_premium_feature(lambda: _import_and_call('modules.competitor_tracking', 'render_competitor_tracking_page')),
        PageRoutes.COMPETITOR_MASTER: lambda: _handle_premium_feature(lambda: _import_and_call('modules.competitor_master', 'render_competitor_master_page')),
        PageRoutes.POST_EVALUATION: lambda: _handle_premium_feature(lambda: _import_and_call('modules.post_evaluation', 'render_post_evaluation_page')),
        PageRoutes.INTELLIGENT_SUGGESTIONS: lambda: _handle_premium_feature(lambda: _import_and_call('modules.post_evaluation', 'render_intelligent_suggestions')),
        PageRoutes.EGP_BOQ_WORKSPACE: lambda: _import_and_call('modules.egp_boq_workspace', 'render_boq_workspace'),
        PageRoutes.TUTORIAL: lambda: _import_and_call('modules.tutorials', 'render_tutorial'),
    }
    
    # Get handler
    current_page = st.session_state.page
    handler = PAGE_HANDLERS.get(current_page, PAGE_HANDLERS[PageRoutes.DASHBOARD])
    
    try:
        handler()
    except ImportError as e:
        debug_print(f"❌ Module import error for '{current_page}': {e}")
        logger.error(f"Import failed: {current_page}", exc_info=True)
        st.error(f"⚠️ Feature unavailable: {current_page.replace('_', ' ').title()}")
        st.info("This feature may require a higher subscription plan or system configuration.")
    except Exception as e:
        debug_print(f"❌ Render error for '{current_page}': {e}")
        logger.error(f"Page render failed: {current_page}", exc_info=True)
        st.error("⚠️ Unable to load this page. Please try again or contact support.")
        if DEBUG_MODE:
            with st.expander("🐛 Debug Traceback"):
                st.code(traceback.format_exc(), language="python")


def _render_authenticated_pages() -> None:
    """Render pages for authenticated users with top navigation"""
    
    from modules.top_navigation import render_top_navigation
    
    # Render top navigation bar (appears on all authenticated pages)
    render_top_navigation()
    
    # Page handlers (your existing code)
    PAGE_HANDLERS: Dict[str, Callable] = {
        # Core pages
        PageRoutes.DASHBOARD: dashboard_page,
        PageRoutes.NEW_ANALYSIS: tender_analysis_page,
        PageRoutes.HISTORY: history_page,
        PageRoutes.PROFILE: profile_page,
        PageRoutes.ADMIN_DASHBOARD: admin_dashboard_page,
        PageRoutes.SUBSCRIPTION: lambda: render_subscription_page(),
        PageRoutes.USER_MANAGEMENT: lambda: render_user_management(),
         # ========== ADD THESE MISSING HANDLERS ==========
        PageRoutes.RATE_MANAGEMENT: lambda: render_rate_crud_forms(db),
        PageRoutes.IMPORT_WIZARD: lambda: render_unified_import_wizard(db),
        PageRoutes.RATE_VIEWER: lambda: _import_and_call('modules.rate_viewer', 'render_rate_viewer'),

        # Advanced modules (lazy import)
        PageRoutes.TENDER_MANAGEMENT: lambda: _import_and_call('modules.tender_management', 'render_tender_management'),
        PageRoutes.POST_EVALUATION: lambda: _import_and_call('modules.post_evaluation', 'render_post_evaluation_page'),
        PageRoutes.INTELLIGENT_SUGGESTIONS: lambda: _import_and_call('modules.post_evaluation', 'render_intelligent_suggestions'),
        PageRoutes.HISTORICAL_DATA: lambda: _import_and_call('modules.historical_data', 'render_historical_data_page'),
        PageRoutes.ANALYSIS_HISTORY: lambda: _import_and_call('modules.analysis_history', 'show_analysis_history'),
        PageRoutes.COMPETITOR_TRACKING: lambda: _import_and_call('modules.competitor_tracking', 'render_competitor_tracking_page'),
        PageRoutes.COMPETITOR_MASTER: lambda: _import_and_call('modules.competitor_master', 'render_competitor_master_page'),
        PageRoutes.USER_APPROVAL: lambda: _import_and_call('modules.user_approval', 'render_user_approval_page'),
        PageRoutes.ROLE_MANAGEMENT: lambda: _import_and_call('modules.user_management', 'render_role_management'),
        PageRoutes.COMPANY_DASHBOARD: lambda: _import_and_call('_pages.company_dashboard', 'show'),        
        PageRoutes.EGP_BOQ_WORKSPACE: lambda: _import_and_call('modules.egp_boq_workspace', 'render_boq_workspace'),
        PageRoutes.TUTORIAL: lambda: _import_and_call('modules.tutorials', 'render_tutorial'),
        PageRoutes.BOQ_GENERATOR: lambda: _import_and_call('modules.boq_generator_ui', 'render_boq_generator'),
        PageRoutes.BOQ_ADMIN_REPORT: lambda: _import_and_call('modules.boq_admin_report', 'render_boq_admin_report'),
        PageRoutes.BOQ_BID_OPTIMIZER: lambda: _import_and_call('modules.boq_bid_bridge', 'render_boq_bid_integration')
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

def _import_and_call(module_path: str, function_name: str, *args, **kwargs):
    """
    Lazy import helper for module-based page handlers.
    Prevents importing all modules at startup.
    """
    import importlib
    module = importlib.import_module(module_path)
    func = getattr(module, function_name)
    return func(*args, **kwargs)

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

    # =========================================================================
    # RESTORE SESSION FROM URL PARAMETER (Google OAuth)
    # =========================================================================
    query_params = st.query_params
    
    # Check for user data in URL (from Google callback)
    if 'user' in query_params:
        try:
            user_data_b64 = query_params['user']
            user_data_json = base64.urlsafe_b64decode(user_data_b64).decode()
            user_data = json.loads(user_data_json)
            
            # Restore session state
            for key, value in user_data.items():
                st.session_state[key] = value
            
            # Clear the parameter to avoid re-processing
            st.query_params.clear()
            
            # Force rerun to show dashboard
            st.rerun()
            return
        except Exception as e:
            debug_print(f"Error restoring session: {e}")
    
    # =========================================================================
    # HANDLE GOOGLE OAUTH CALLBACK
    # =========================================================================
    from modules.google_auth import handle_google_callback
    
    # Check if this is an OAuth callback
    if 'code' in query_params:
        # Handle the callback - this will process the code and redirect
        handle_google_callback()
        # After handling, clear params and rerun to avoid reprocessing
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
    # RENDER APP HEADER (For all users)
    # =========================================================================
    render_app_header()
    
    # =========================================================================
    # CONDITIONAL SIDEBAR & DARK MODE TOGGLE
    # =========================================================================
    if st.session_state.logged_in:
        # For logged-in users, show dark mode toggle in sidebar        
        
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
    # RENDER FOOTER (For all users)
    # =========================================================================
    from modules.ui_components import render_footer
    render_footer()
    
    # Optional: Global debug panel (development only)
    if DEBUG_MODE and st.session_state.get('user_role') == 'admin':
        _render_global_debug_panel()

def main_bak() -> None:
    """
    Main application entry point with optimized routing.
    Uses PageRoutes constants, lazy imports, and safe error handling.
    """
    import base64
    import json
    
    # =========================================================================
    # RESTORE SESSION FROM URL PARAMETER (Google OAuth)
    # =========================================================================
    query_params = st.query_params
    
    # Check for user data in URL (from Google callback)
    if 'user' in query_params:
        try:
            user_data_b64 = query_params['user']
            user_data_json = base64.urlsafe_b64decode(user_data_b64).decode()
            user_data = json.loads(user_data_json)
            
            # Restore session state
            for key, value in user_data.items():
                st.session_state[key] = value
            
            # Clear the parameter to avoid re-processing
            st.query_params.clear()
            
            # Force rerun to show dashboard
            st.rerun()
            return
        except Exception as e:
            debug_print(f"Error restoring session: {e}")
       
    
    # =========================================================================
    # HANDLE GOOGLE OAUTH CALLBACK
    # =========================================================================
    from modules.google_auth import handle_google_callback
    
    # Check if this is an OAuth callback
    if 'code' in query_params:
        # Handle the callback - this will process the code and redirect
        handle_google_callback()
        # After handling, clear params and rerun to avoid reprocessing
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
    
    # Render sidebar (always visible)
    render_sidebar()
    
    # Handle checkout flow (modal-like experience)
    if st.session_state.get('show_checkout'):
        render_checkout()
        return
    
    # Route to appropriate page handler
    if not st.session_state.logged_in:
        _render_public_pages()
    else:
        _render_authenticated_pages()
    
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
        from subscription import render_subscription_page
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
    from _pages.admin_dashboard_bak import show as show_admin_dashboard
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
    if st.session_state.get('_admin_upgraded', False):
        return
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            st.session_state._admin_upgraded = True

# =============================================================================
# 🎬 APP LAUNCH (Final safety)
# =============================================================================
if __name__ == "__main__":
    # ✅ Ensure imports are available
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    
    debug_print("🎬 Starting TenderAI application...")
    #upgrade_admin_once()  # Ensure admin users are upgraded at startup (one-time check)
    #db.update_role_permissions_for_rates()

    # ✅ Initialize once at startup
    initialize_session_state()
    
    try:
        main()
    except Exception as e:
        logger.critical("Application crashed", exc_info=True)
        st.error("💥 Application error. Please refresh or contact support.")
        if DEBUG_MODE:
            required_routes = [
                'home', 'login', 'register', 'pricing', 'about', 'contact',
                'dashboard', 'new_analysis', 'history', 'profile', 'subscription',
                'user_management', 'tender_management', 'post_evaluation', 'intelligent_suggestions',
                'historical_data', 'analysis_history', 'competitor_tracking', 'competitor_master',
                'admin_dashboard', 'user_approval', 'role_management', 'tutorial'
            ]
            
            missing = [r for r in required_routes if r not in PageRoutes.get_all_routes()]
            if missing:
                debug_print(f"❌ Missing PageRoutes attributes: {missing}")
            else:
                debug_print("✅ All PageRoutes attributes present")
    
    debug_print("✅ App render cycle complete\n")