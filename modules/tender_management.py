"""
Complete Tender Management Module - Refactored
State-Driven View Router Pattern with st.dataframe
"""

import streamlit as st
import logging
from typing import Optional, Dict, List, Any, Tuple

from database.unified_db_manager import get_db_manager
from utils.components import render_tender_styles

# Import the refactored tender detail page components
from modules.tender_detail import (
    render_tender_detail_page,
    render_tender_grid_view
)

logger = logging.getLogger(__name__)

db = get_db_manager()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def show():
    """Main entry point for Tender Management - Refactored"""
    
    # Render tender-specific styles
    render_tender_styles()
    
    # Initialize session state for view routing
    if "tender_view" not in st.session_state:
        st.session_state.tender_view = "grid"
    if "tender_selected_id" not in st.session_state:
        st.session_state.tender_selected_id = None
    if "tender_page" not in st.session_state:
        st.session_state.tender_page = 1
    if "tender_search" not in st.session_state:
        st.session_state.tender_search = ""
    if "tender_status_filter" not in st.session_state:
        st.session_state.tender_status_filter = "All"
    if "tender_per_page" not in st.session_state:
        st.session_state.tender_per_page = 10
    
    print(f"🔍 show() called - tender_view: {st.session_state.tender_view}")
    print(f"🔍 tender_selected_id: {st.session_state.tender_selected_id}")
    
    # Check if we're viewing a specific tender
    if st.session_state.tender_view == "detail" and st.session_state.tender_selected_id:
        print(f"🔍 Rendering detail view for tender_id: {st.session_state.tender_selected_id}")
        try:
            render_tender_detail_page(st.session_state.tender_selected_id)
        except Exception as e:
            print(f"❌ Error in tender detail: {e}")
            import traceback
            traceback.print_exc()
            st.error(f"Error loading tender details: {e}")
            st.session_state.tender_view = "grid"
            st.session_state.tender_selected_id = None
            st.rerun()
        # ✅ IMPORTANT: Return here to prevent further rendering
        return
    
    # Render the grid view
    print("🔍 Rendering grid view")
    render_tender_grid_view()


def render_tender_management():
    """Entry point for tender management - maintains compatibility with main.py"""
    return show()


# ✅ Make sure these are exported
__all__ = [
    'show',
    'render_tender_management'
]