# modules/top_navigation.py (v4.02)
import streamlit as st

def render_top_navigation():
    """Compact responsive top navigation with horizontal sub-menus"""
    
    try:
        from config.navigation import NAVIGATION_CONFIG
    except ImportError as e:
        st.error(f"❌ Navigation configuration not found: {e}")
        st.info("Please create the config/navigation.py file")
        return
    
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # ==================== CSS ====================
    st.markdown("""
    <style>
    /* Main container */
    .top-nav-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 0.7rem 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    /* Main buttons row */
    .main-nav-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.3rem;
    }
    
    /* Sub-menu container - FULL WIDTH with horizontal flex */
    .sub-nav-container {
        background: rgba(255, 255, 255, 0.08);
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0 0 0;
        border-left: 3px solid #4facfe;
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        gap: 0.3rem !important;
        width: 100% !important;
        box-sizing: border-box !important;
        flex-direction: row !important;  /* Force horizontal */
    }
    
    .sub-nav-label {
        color: #a8d8ff;
        font-size: 0.6rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 0.5rem;
        flex-shrink: 0;
    }
    
    /* Horizontal sub-item buttons - inline */
    .sub-nav-item {
        display: inline-block !important;
        flex: 0 0 auto !important;
    }
    
    .sub-nav-item button {
        font-size: 0.75rem !important;
        padding: 0.15rem 0.6rem !important;
        white-space: nowrap !important;
        min-width: auto !important;
        height: auto !important;
        line-height: 1.4 !important;
        display: inline-block !important;
    }
    
    /* Hide any extra column containers */
    .sub-nav-columns {
        display: none !important;
    }
    
    /* Override Streamlit's column behavior */
    .stColumns {
        display: inline !important;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .top-nav-container {
            padding: 0.4rem 0.5rem;
        }
        .sub-nav-container {
            padding: 0.3rem 0.5rem;
            gap: 0.2rem;
        }
        .sub-nav-label {
            font-size: 0.5rem;
            margin-right: 0.3rem;
        }
        .sub-nav-item button {
            font-size: 0.65rem !important;
            padding: 0.1rem 0.4rem !important;
        }
    }
    
    @media (max-width: 480px) {
        .sub-nav-item button {
            font-size: 0.55rem !important;
            padding: 0.08rem 0.3rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # ==================== GET NAVIGATION CONFIG ====================
    nav_groups = NAVIGATION_CONFIG.get(user_role, NAVIGATION_CONFIG.get('viewer', []))
    
    if not nav_groups:
        st.warning(f"No navigation configuration found for role: {user_role}")
        return

    # ==================== RENDER NAV ====================
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)

    # Row 1: Main navigation buttons (full width)
    cols = st.columns(len(nav_groups))
    for idx, group in enumerate(nav_groups):
        with cols[idx]:
            is_active = current_page == group.page_key
            sub_active = any(item.page_key == current_page for item in group.items)
            button_type = "primary" if (is_active or sub_active) else "secondary"
            
            if st.button(
                f"{group.icon} {group.label}",
                key=f"main_nav_{group.page_key}",
                use_container_width=True,
                type=button_type,
                help=f"Go to {group.label}"
            ):
                st.session_state.page = group.page_key
                st.rerun()

    # Row 2: Sub-menu items (full width, horizontal)
    # Find which group has active sub-items
    active_group = None
    for group in nav_groups:
        is_active = current_page == group.page_key
        sub_active = any(item.page_key == current_page for item in group.items)
        if group.items and (is_active or sub_active):
            active_group = group
            break
    
    # Render sub-menu for the active group - ALL IN ONE ROW
    if active_group:
        # Build the HTML for all sub-items in a single horizontal row
        sub_items_html = []
        for item in active_group.items:
            is_sub_active = current_page == item.page_key
            
            # Handle extension usage count
            display_label = f"{item.icon} {item.label}"
            if item.page_key in ["extension_admin", "extension_usage"]:
                ext_used = st.session_state.get('extension_fills_used', 0)
                ext_limit = st.session_state.get('extension_fills_limit', 5)
                rem = "∞" if ext_limit == -1 else max(0, ext_limit - ext_used)
                display_label = f"{item.icon} {item.label} ({rem})"
            
            # Add to HTML list
            sub_items_html.append({
                'label': display_label,
                'key': item.page_key,
                'active': is_sub_active,
                'help': f"Go to {item.label}"
            })
        
        # Render using a single row of columns
        num_items = len(sub_items_html)
        if num_items > 0:
            # Use columns for horizontal layout - ALL IN ONE ROW
            sub_cols = st.columns(num_items)
            for idx, sub_item in enumerate(sub_items_html):
                with sub_cols[idx]:
                    if st.button(
                        sub_item['label'],
                        key=f"sub_nav_{sub_item['key']}",
                        use_container_width=True,
                        type="primary" if sub_item['active'] else "secondary",
                        help=sub_item['help']
                    ):
                        st.session_state.page = sub_item['key']
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")