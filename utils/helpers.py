import logging
from typing import Dict, Optional
import streamlit as st
import re
from datetime import datetime
import traceback
# =============================================================================
# 🔧 DEBUG CONFIGURATION
# =============================================================================
DEBUG_MODE = True
def has_data(data) -> bool:
    """Safe check for None, empty list, dict, or pandas DataFrame"""
    if data is None:
        return False
    if hasattr(data, 'empty'):  # pandas DataFrame
        return not data.empty
    return len(data) > 0  # list, tuple, dict, etc.

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

def setup_logging():
    level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

setup_logging()
logger = logging.getLogger(__name__)
def debug_print(*args, **kwargs):
    print(*args, **kwargs)

# Import BID_AMOUNT_DECIMALS from main or define it here
try:
    from config import BID_AMOUNT_DECIMALS
except ImportError:
    BID_AMOUNT_DECIMALS = 3  # Default to 3 decimals for e-GP compliance

def render_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render a consistent page header with gradient background"""
    icon_str = f"{icon} " if icon else ""
    subtitle_html = f"<p style='color: white; font-size: 1.1rem; margin: 0.5rem 0 0 0; opacity: 0.95;'>{subtitle}</p>" if subtitle else ""
    
    st.markdown(f"""
    <div class="main-header" style="text-align: center;">
        <h1 style="margin: 0; font-size: 2rem;">{icon_str}{title}</h1>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)


def render_feature_card(icon: str, title: str, description: str) -> None:
    """Render a feature card component"""
    st.markdown(f"""
    <div style="background: white; padding: 1.2rem; border-radius: 10px; 
                text-align: center; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0; color: #333;">{title}</h4>
        <p style="margin: 0; color: #666; font-size: 0.9rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_pricing_card(plan_key: str, plan_data: Dict, is_recommended: bool = False) -> None:
    """Render a pricing plan card"""
    border = "2px solid #667eea" if is_recommended else "1px solid #eee"
    shadow = "0 4px 12px rgba(102, 126, 234, 0.15)" if is_recommended else "0 2px 4px rgba(0,0,0,0.05)"
    
    badge = f'''<div style="background: #667eea; color: white; padding: 0.25rem 0.75rem; 
                      border-radius: 20px; font-size: 0.7rem; font-weight: bold; 
                      display: inline-block; margin-bottom: 0.75rem;">POPULAR</div>''' if is_recommended else ''
    
    # Start card
    st.markdown(f"""
    <div style="background: white; padding: 1.3rem; border-radius: 12px; 
                text-align: center; border: {border}; box-shadow: {shadow}; margin: 0.5rem;">
        {badge}
        <h3 style="margin: 0 0 0.5rem 0; color: #1e3c72;">{plan_data.get('name', 'Plan')}</h3>
        <div style="font-size: 2rem; font-weight: bold; margin: 0.5rem 0;">
            BDT {plan_data.get('price', 0):,.0f}
            <span style="font-size: 0.9rem; font-weight: normal;">/month</span>
        </div>
        <div style="margin: 0.5rem 0 1rem 0;">
    """, unsafe_allow_html=True)
    
    # Fixed formatting with 3 decimals for bids
    if plan_data.get('optimal_bid'):
        st.markdown(f"- **Optimal Bid:** BDT {plan_data.get('optimal_bid', 0):,.{BID_AMOUNT_DECIMALS}f}")
    
    # Features list
    for feature in plan_data.get('features', []):
        st.markdown(f"<div style='text-align: left; padding: 0.2rem 0; font-size: 0.85rem; color: #444;'>✅ {feature}</div>", unsafe_allow_html=True)
    
    # Button
    btn_type = "primary" if is_recommended else "secondary"
    if st.button(f"Select {plan_data['name']}", key=f"plan_{plan_key}", use_container_width=True, type=btn_type):
        st.session_state.selected_plan = plan_key
        st.session_state.show_checkout = True
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close card div


def render_demo_credentials() -> None:
    """Render demo account credentials in expandable section"""
    with st.expander("🔑 Click to view demo credentials", expanded=False):
        st.markdown("""
        **Admin Access:**
        - Username: `admin` | Password: `admin123`
        
        **Approved Company Admin:**
        - Username: `john.doe` | Password: `John@123`
        
        **Manager Access:**
        - Username: `jane.smith` | Password: `Jane@123`
        
        **Analyst Access:**
        - Username: `bob.wilson` | Password: `Bob@123`
        
        > 💡 These accounts are for testing only. Do not use in production.
        """)


def navigate_to(page: str, success_msg: Optional[str] = None, error_msg: Optional[str] = None) -> None:
    """
    Standardized navigation helper with optional toast messages.
    
    Args:
        page: Target page key to set in session_state
        success_msg: Optional success message to show before navigating
        error_msg: Optional error message to show before navigating
    """
    if success_msg:
        st.success(success_msg)
    elif error_msg:
        st.error(error_msg)
    
    st.session_state.page = page
    st.rerun()
def navigate_to_2(page: str, success_msg: str = None):
    """Navigate to a page"""
    if success_msg:
        st.success(success_msg)
    st.session_state.page = page
    # ✅ Force rerun after setting page
    st.rerun()



def get_compact_css():
    """Return centralized compact CSS for consistent styling across all pages"""
    return """
    <style>
        /* Global compact styles */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* Smaller headings */
        h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-size: 1.1rem !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Compact buttons */
        .stButton button {
            padding: 0.2rem 0.5rem !important;
            font-size: 0.75rem !important;
            line-height: 1.2 !important;
            min-height: 28px !important;
        }
        
        /* Compact columns */
        div[data-testid="column"] {
            padding: 0.2rem !important;
            margin: 0 !important;
        }
        
        /* Compact text */
        p, div, span, label, .stMarkdown {
            font-size: 0.8rem !important;
            line-height: 1.3 !important;
        }
        
        /* Compact metric boxes */
        div[data-testid="stMetric"] {
            padding: 0.3rem !important;
            margin: 0 !important;
            background: none !important;
        }
        
        div[data-testid="stMetric"] label {
            font-size: 0.7rem !important;
            color: #666 !important;
        }
        
        div[data-testid="stMetric"] div {
            font-size: 1rem !important;
            font-weight: 600 !important;
        }
        
        /* Compact expanders */
        details {
            margin: 0.2rem 0 !important;
        }
        
        summary {
            font-size: 0.8rem !important;
            padding: 0.2rem !important;
        }
        
        /* Compact tabs */
        button[data-baseweb="tab"] {
            font-size: 0.75rem !important;
            padding: 0.2rem 0.8rem !important;
        }
        
        /* Compact dataframe */
        .stDataFrame {
            font-size: 0.75rem !important;
        }
        
        .stDataFrame td, .stDataFrame th {
            padding: 0.2rem 0.3rem !important;
            font-size: 0.75rem !important;
        }
        
        /* Compact horizontal rule */
        hr {
            margin: 0.3rem 0 !important;
        }
        
        /* Compact caption */
        .stCaption, caption {
            font-size: 0.7rem !important;
        }
        
        /* Reduce row height in tables */
        div.row-widget.stButton {
            margin: 0 !important;
            padding: 0 !important;
        }
    </style>
    """

def format_currency_bd(value, decimals=3):
    """
    Format currency according to Bangladesh e-GP standards
    Uses 3 decimal places as per CPTU requirements
    """
    if value is None or value == 0:
        return "BDT 0.000"
    return f"BDT {value:,.{decimals}f}"

def format_percentage(value, decimals=1):
    """Format percentage with proper decimal places"""
    if value is None:
        return "N/A"
    if value <= 1:  # If it's a decimal (0.85)
        value = value * 100
    return f"{value:.{decimals}f}%"

def safe_format(value, format_str="{:,}", default="N/A"):
    """Safely format any value, handling None"""
    if value is None:
        return default
    try:
        return format_str.format(value)
    except:
        return str(value)

def get_bid_status_badge(status):
    """Get emoji badge for bid status"""
    badges = {
        'won': '🏆',
        'lost': '❌',
        'submitted': '📤',
        'draft': '⚪',
        'Won': '🏆',
        'Lost': '❌',
        'Submitted': '📤',
        'Draft': '⚪'
    }
    return badges.get(str(status).lower(), '⚪')

def get_risk_indicator(risk_level):
    """Get risk indicator with emoji"""
    risk_map = {
        'Low': '🟢 Low',
        'Medium': '🟡 Medium',
        'High': '🔴 High',
        'LOW': '🟢 Low',
        'MEDIUM': '🟡 Medium',
        'HIGH': '🔴 High'
    }
    return risk_map.get(str(risk_level).upper(), '⚪ Unknown')

def _generate_and_download_pdf(analysis_id: int, analysis_record: dict) -> None:
    """Helper with bulletproof logging and fallbacks"""
    debug_print("🚀 PDF HELPER START | id={analysis_id}, record_type={type(analysis_record)}, keys={list(analysis_record.keys())[:5] if analysis_record else 'EMPTY'}")
    logger.info(f"🚀 PDF HELPER START | id={analysis_id}, record_type={type(analysis_record)}, keys={list(analysis_record.keys())[:5] if analysis_record else 'EMPTY'}")
    
    with st.spinner("🔄 Generating PDF report..."):
        try:
            from modules.pdf_generator import generate_enhanced_analysis_report
            
            user_info = {
                'full_name': st.session_state.get('full_name', 'N/A'),
                'company_name': st.session_state.get('company_name', 'N/A'),
                'role': st.session_state.get('user_role', 'N/A'),
                'email': st.session_state.get('user_email', 'N/A'),
            }
            logger.debug(f"👤 User: {user_info.get('full_name')}")
            debug_print(f"👤 User Info: {user_info}")

            # ✅ Fetch from DB if ID provided
            if analysis_id:
                logger.debug(f"🗄️ Fetching DB record for id={analysis_id}")
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tender_analyses WHERE id = ?', (analysis_id,))
                saved = cursor.fetchone()
                conn.close()
                
                if saved and cursor.description:
                    cols = [d[0] for d in cursor.description]
                    db_record = dict(zip(cols, saved))
                    report_data = {**analysis_record, **db_record}  # DB overwrites session
                    logger.debug(f"✅ Merged DB + session | final keys: {list(report_data.keys())[:10]}")
                else:
                    report_data = analysis_record
                    logger.warning(f"⚠️ No DB record for id={analysis_id}, using session data only")
            else:
                report_data = analysis_record
                logger.info("ℹ️ No analysis_id provided, using session data only")
            
            # ✅ SAFE TYPE CONVERSIONS (Critical for PDF values)
            logger.debug("🔧 Applying safe type conversions...")
            est = float(report_data.get('official_estimate') or 1)
            bid = float(report_data.get('recommended_bid') or 0)
            slt = float(report_data.get('slt_threshold') or (est * 0.80))
            nppi = float(report_data.get('nppi_factor') or 0.92)
            win_prob = float(report_data.get('success_probability') or 0.6)
            
            # Update report_data with converted values
            report_data.update({
                'official_estimate': est,
                'recommended_bid': bid,
                'slt_threshold': slt,
                'nppi_factor': nppi,
                'success_probability': win_prob
            })
            logger.info(f"💰 Converted values: est={est}, bid={bid}, slt={slt}, nppi={nppi}")
            debug_print(f"💰 Converted values: est={est}, bid={bid}, slt={slt}, nppi={nppi}")
            # ✅ Generate PDF
            logger.debug("📄 Calling generate_enhanced_analysis_report()...")
            pdf_buffer = generate_enhanced_analysis_report(report_data, user_info, include_charts=False)
            
            # ✅ Validate buffer
            if not pdf_buffer:
                logger.error("❌ PDF buffer is None")
                st.error("❌ PDF generation returned None")
                return
            if pdf_buffer.getbuffer().nbytes == 0:
                logger.error("❌ PDF buffer is empty (0 bytes)")
                st.error("❌ PDF generation returned empty buffer")
                return
            
            logger.info(f"✅ PDF generated successfully2 | size={pdf_buffer.getbuffer().nbytes} bytes")
            
            # ✅ STORE in session state (CRITICAL STEP)
            safe_tid = str(report_data.get('tender_id', 'report')).replace('/', '_').replace('\\', '_').replace(' ', '_')
            filename = f"Enhanced_Analysis_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            
            st.session_state._pdf_buffer = pdf_buffer
            st.session_state._pdf_filename = filename
            
            logger.info(f"💾 Stored buffer in session state | filename={filename}")
            st.success("✅ PDF generated! Scroll down to download.")
            
            # ✅ Force immediate rerun to show download button (optional but reliable)
            # st.rerun()  # Uncomment if button doesn't appear without this
            
        except ImportError as e:
            logger.error(f"❌ ImportError in PDF helper: {e}")
            st.warning(f"⚠️ PDF module not available: {e}")
        except Exception as e:
            logger.error(f"❌ PDF helper failed: {type(e).__name__}: {str(e)}", exc_info=True)
            st.error(f"❌ PDF error: {str(e)}")
            if DEBUG_MODE:
                with st.expander("🐛 PDF Helper Traceback"):
                    st.code(traceback.format_exc(), language="python")



import re
def validate_password_strength(password: str) -> tuple[int, str, str]:
    """Validate password strength and return score (0-100), message, and color."""
    score = 0
    feedback = []

    if len(password) >= 8:
        score += 25
    else:
        feedback.append("8+ characters")

    if re.search(r'[A-Z]', password):
        score += 25
    else:
        feedback.append("uppercase letter")

    if re.search(r'[a-z]', password):
        score += 20
    else:
        feedback.append("lowercase letter")

    if re.search(r'\d', password):
        score += 15
    else:
        feedback.append("number")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 15
    else:
        feedback.append("special character")

    # Cap at 100
    score = min(score, 100)

    if score >= 80:
        message = f"Strong password! {' '.join(feedback) if feedback else ''}"
        color = "#10b981"  # green
    elif score >= 60:
        message = f"Medium password. Add: {', '.join(feedback)}"
        color = "#f59e0b"  # orange
    else:
        message = f"Weak password. Add: {', '.join(feedback)}"
        color = "#ef4444"  # red

    return score, message.strip(), color
def render_page_header(title: str, description: str = None):
    """Render page header with consistent styling"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                padding: 1.2rem 1.5rem; 
                border-radius: 12px; 
                margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1e3c72;">{title}</h1>
        {f'<p style="margin: 0.5rem 0 0 0; color: #555;">{description}</p>' if description else ''}
    </div>
    """, unsafe_allow_html=True)

def safe_title(value, default: str = 'N/A') -> str:
    """Safely convert any value to title case"""
    if value is None:
        return default
    try:
        return str(value).strip().title() if str(value).strip() else default
    except Exception:
        return default

def render_tender_info_card(tender_data: dict) -> None:
    """Render a compact tender information summary card"""
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

def safe_date_slice(date_value, length: int = 10) -> str:
    """Safely slice date values (handles Timestamp, str, None)"""
    if date_value is None:
        return 'N/A'
    date_str = str(date_value)
    return date_str[:length] if len(date_str) >= length else date_str

# utils/db_helpers.py
"""Helper functions for database row handling"""

import streamlit as st


def row_to_dict(row, cursor=None):
    """
    Convert any row (sqlite3.Row, dict, tuple) to a real dictionary.
    
    Usage:
        row = cursor.fetchone()
        data = row_to_dict(row, cursor)
        value = data.get('column_name')
    """
    if row is None:
        return {}
    
    # If it's already a dict
    if isinstance(row, dict):
        return row
    
    # If it's a sqlite3.Row (has keys method)
    if hasattr(row, 'keys'):
        return dict(row)
    
    # If it's a tuple, use cursor.description for column names
    if isinstance(row, (tuple, list)) and cursor and hasattr(cursor, 'description'):
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    
    # Last resort - return as is
    return {}


def get_value(row, key, index=None, default=None):
    """
    Safely get value from row (works with dict, Row, or tuple).
    
    Usage:
        # For dict/Row (preferred)
        value = get_value(row, 'column_name')
        
        # For tuple (fallback)
        value = get_value(row, None, index=2)
        
        # Both
        value = get_value(row, 'column_name', index=2)
    """
    if row is None:
        return default
    
    # Try dict access first
    if hasattr(row, 'keys') or isinstance(row, dict):
        if key and key in row:
            return row[key]
        elif hasattr(row, 'get'):
            return row.get(key, default)
    
    # Try tuple/list access
    if isinstance(row, (tuple, list)) and index is not None:
        return row[index] if len(row) > index else default
    
    return default


def rows_to_dicts(rows, cursor=None):
    """Convert multiple rows to list of dictionaries"""
    return [row_to_dict(row, cursor) for row in rows]


def safe_execute_query(db, sql, params=None):
    """
    Execute query and return list of dictionaries.
    This is the recommended way to query the database.
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return rows_to_dicts(rows, cursor)