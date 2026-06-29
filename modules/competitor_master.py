"""
Competitor Master Management
Maintain a master list of all competitors with intelligence features
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple, Any

from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription_manager import check_subscription_access
from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, render_protected_button, can_import_tender_data,
)

db = UnifiedDatabaseManager()


# ============================================================================
# MAIN RENDER FUNCTION
# ============================================================================

def render_competitor_master_page(db=None, subscription_manager=None):
    """Render competitor master management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 Competitor Intelligence Dashboard</h1>
        <p>Manage competitors and gain intelligence insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Subscription check
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)
    user_role = st.session_state.get('user_role', 'viewer')

    can_edit = user_role in ['system_admin', 'admin', 'company_admin']

    if not has_access:
        st.warning(msg)
        st.info("Upgrade to use Competitor Master.")
        return
    
    # Create tabs
    tabs = st.tabs([
        "📋 Competitor List", 
        "➕ Add Competitor", 
        "📊 Analytics", 
        "🧠 Intelligence", 
        "🔍 Tracking", 
        "⚙️ Settings"
    ])
    
    with tabs[0]:
        render_competitor_list()  # Main dashboard with the UI you showed
    
    with tabs[1]:
        render_add_competitor_form()
    
    with tabs[2]:
        render_competitor_analytics()
    
    with tabs[3]:
        render_intelligence_tab()
    
    with tabs[4]:
        render_tracking_tab()
    
    with tabs[5]:
        render_settings_tab(can_edit)  # ✅ FIXED: Pass can_edit parameter


# ============================================================================
# TAB 1: COMPETITOR LIST
# ============================================================================


def render_competitor_list():
    """Display the main competitor dashboard with the UI shown"""
    
    company_id = st.session_state.get('company_id')
    
    # ============================================================================
    # HEADER SECTION WITH 4 KPI CARDS
    # ============================================================================
    st.markdown("### 📊 Competitor Intelligence Dashboard")
    
    # Get summary stats
    competitors = db.get_competitor_master_list(company_id, active_only=True)
    
    if not competitors:
        st.info("No competitors found. Add your first competitor using the form above.")
        return
    
    comp_df = pd.DataFrame(competitors)
    
    # Calculate KPIs
    total_competitors = len(comp_df)
    active_competitors = len([c for c in competitors if c.get('is_active', True)])
    
    total_bids = comp_df['total_bids'].sum()
    total_wins = comp_df['total_wins'].sum()
    win_rate = (total_wins / total_bids * 100) if total_bids > 0 else 0
    
    avg_ratio = comp_df['avg_bid_ratio'].mean()
    if pd.isna(avg_ratio):
        avg_ratio = 0.0
    
    # Display 4 KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Competitors", total_competitors)
    with col2:
        st.metric("Active Competitors", active_competitors)
    with col3:
        st.metric("Win Rate (All)", f"{win_rate:.1f}%")
    with col4:
        st.metric("Avg Bid Ratio", f"{avg_ratio:.3f}")
    
    st.divider()
    
    # ============================================================================
    # CHARTS SECTION
    # ============================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        # Bid Distribution Histogram
        if len(comp_df) > 0 and comp_df['total_bids'].sum() > 0:
            st.markdown("#### Bid Distribution")
            fig = px.histogram(
                comp_df,
                x='total_bids',
                title='Competitor Bid Distribution',
                labels={'total_bids': 'Number of Bids'},
                nbins=20,
                color_discrete_sequence=['blue']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No bid data available for chart")
    
    with col2:
        # Win Rate by Competitor Bar Chart
        if len(comp_df) > 0 and comp_df['total_bids'].sum() > 0:
            st.markdown("#### Win Rate by Competitor")
            comp_df['Win Rate'] = comp_df.apply(
                lambda x: (x['total_wins'] / x['total_bids'] * 100) if x['total_bids'] > 0 else 0, 
                axis=1
            )
            top_competitors = comp_df.nlargest(10, 'total_bids')
            fig = px.bar(
                top_competitors,
                x='competitor_name',
                y='Win Rate',
                title='Top 10 Competitors by Win Rate',
                labels={'competitor_name': 'Competitor', 'Win Rate': 'Win Rate (%)'},
                color='Win Rate',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No win rate data available for chart")
    
    st.divider()
    
    # ============================================================================
    # COMPETITOR LIST TABLE WITH [🔍] DETAILS BUTTON
    # ============================================================================
    st.markdown("### 📋 Competitor List")
    
    # Search and Filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search Competitor", placeholder="Enter competitor name...")
    with col2:
        filter_type = st.selectbox("Filter", ["All", "Active", "Inactive"])
    with col3:
        sort_by = st.selectbox("Sort by", ["Name", "Total Bids", "Win Rate", "Last Seen"])
    
    # Apply filters
    filtered_competitors = competitors.copy()
    
    if search:
        filtered_competitors = [c for c in filtered_competitors if search.lower() in c.get('competitor_name', '').lower()]
    
    if filter_type == "Active":
        filtered_competitors = [c for c in filtered_competitors if c.get('is_active', True)]
    elif filter_type == "Inactive":
        filtered_competitors = [c for c in filtered_competitors if not c.get('is_active', True)]
    
    # Sort
    if sort_by == "Name":
        filtered_competitors.sort(key=lambda x: x.get('competitor_name', ''))
    elif sort_by == "Total Bids":
        filtered_competitors.sort(key=lambda x: x.get('total_bids', 0), reverse=True)
    elif sort_by == "Win Rate":
        filtered_competitors.sort(
            key=lambda x: (x.get('total_wins', 0) / x.get('total_bids', 1)) if x.get('total_bids', 0) > 0 else 0,
            reverse=True
        )
    elif sort_by == "Last Seen":
        filtered_competitors.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
    
    # Pagination
    page_size = 10
    total_pages = (len(filtered_competitors) - 1) // page_size + 1 if filtered_competitors else 1
    
    # Get current page from session state
    if 'competitor_page' not in st.session_state:
        st.session_state.competitor_page = 1
    
    page = st.session_state.competitor_page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_competitors = filtered_competitors[start_idx:end_idx]
    
    # Display table with [🔍] button
    if page_competitors:
        # Header
        cols = st.columns([3, 2, 2, 2, 1])
        cols[0].write("**Competitor Name**")
        cols[1].write("**Type**")
        cols[2].write("**First Seen**")
        cols[3].write("**Last Seen**")
        cols[4].write("**Details**")
        
        st.divider()
        
        # Rows
        for comp in page_competitors:
            cols = st.columns([3, 2, 2, 2, 1])
            
            # Competitor Name
            cols[0].write(f"**{comp.get('competitor_name', 'Unknown')}**")
            
            # Business Type
            cols[1].write(comp.get('business_type', 'N/A'))
            
            # First Seen (fix date conversion)
            first_seen = comp.get('first_seen')
            if first_seen and isinstance(first_seen, str):
                try:
                    first_seen = datetime.strptime(first_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    first_seen = 'N/A'
            elif first_seen:
                first_seen = first_seen.strftime('%Y-%m-%d')
            else:
                first_seen = 'N/A'
            cols[2].write(first_seen)
            
            # Last Seen (fix date conversion)
            last_seen = comp.get('last_seen')
            if last_seen and isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    last_seen = 'N/A'
            elif last_seen:
                last_seen = last_seen.strftime('%Y-%m-%d')
            else:
                last_seen = 'N/A'
            cols[3].write(last_seen)
            
            # [🔍] Details Button
            comp_id = comp.get('id')
            if cols[4].button(
                "🔍",
                key=f"view_{comp_id}",
                help=f"View full intelligence profile for {comp.get('competitor_name')}"
            ):
                # Navigate to competitor profile page
                st.query_params.competitor_id = comp_id
                st.session_state.page = "competitor_profile"

        
        # Pagination controls
        st.divider()
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if page > 1:
                if st.button("◀ Previous"):
                    st.session_state.competitor_page = page - 1
                    st.rerun()
        
        with col2:
            st.caption(f"Page {page} of {total_pages} | Showing {len(page_competitors)} of {len(filtered_competitors)} competitors")
        
        with col3:
            if page < total_pages:
                if st.button("Next ▶"):
                    st.session_state.competitor_page = page + 1
                    st.rerun()
    else:
        st.info("No competitors match your filters")

# ============================================================================
# TAB 2: ADD COMPETITOR
# ============================================================================

def render_add_competitor_form():
    """Form to add new competitor to master list"""
    
    st.markdown("### Add New Competitor")
    st.caption("Add competitors once, then select from dropdown when recording historical tenders")
    
    with st.form("add_competitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            competitor_name = st.text_input("Competitor Name*")
            business_type = st.selectbox("Business Type", [
                "Construction Company", 
                "Trading Company", 
                "Joint Venture", 
                "Individual", 
                "Other"
            ])
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number")
        
        with col2:
            email = st.text_input("Email Address")
            address = st.text_area("Address", height=68)
            preferred_strategy = st.selectbox(
                "Observed Strategy", 
                ["Aggressive", "Moderate", "Conservative", "Variable", "Unknown"]
            )
            notes = st.text_area("Additional Notes", height=68)
        
        # Intelligence fields
        st.markdown("---")
        st.markdown("#### 🧠 Intelligence Fields")
        details = st.text_area(
            "Competitor Intelligence Notes",
            placeholder="e.g., Known strengths, weaknesses, past performance, market position...",
            height=100,
            help="Store qualitative intelligence about this competitor"
        )
        
        submitted = st.form_submit_button("💾 Add Competitor to Master List", use_container_width=True)
        
        if submitted:
            if not competitor_name:
                st.error("Competitor name is required")
            else:
                competitor_data = {
                    'competitor_name': competitor_name.strip(),
                    'business_type': business_type,
                    'contact_person': contact_person,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'notes': notes,
                    'preferred_strategy': preferred_strategy,
                    'details': details
                }
                
                comp_id = db.add_competitor_to_master(
                    st.session_state.company_id, 
                    competitor_data
                )
                
                if comp_id:
                    st.success(f"✅ Competitor '{competitor_name}' added to master list!")
                    st.balloons()
                else:
                    st.error("Failed to add competitor. Please try again.")


# ============================================================================
# TAB 3: ANALYTICS
# ============================================================================

def render_competitor_analytics():
    """Display competitor analytics and insights"""
    
    st.markdown("### 📊 Competitor Analytics")
    
    competitors = db.get_competitor_master_list(st.session_state.company_id)
    
    if not competitors:
        st.info("No competitor data available. Add competitors and record historical tenders.")
        return
    
    comp_df = pd.DataFrame(competitors)
    
    # Calculate metrics
    comp_df['Win Rate'] = comp_df.apply(
        lambda x: x['total_wins'] / x['total_bids'] if x['total_bids'] > 0 else 0, axis=1
    )
    
    # Top competitors by frequency
    st.markdown("#### Most Frequent Competitors")
    top_frequent = comp_df.nlargest(10, 'total_bids')[
        ['competitor_name', 'total_bids', 'Win Rate', 'avg_bid_ratio']
    ].copy()
    top_frequent.columns = ['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']
    top_frequent['Win Rate'] = top_frequent['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
    top_frequent['Avg Bid Ratio'] = top_frequent['Avg Bid Ratio'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    st.dataframe(top_frequent, use_container_width=True, hide_index=True)
    
    # Most successful competitors
    st.markdown("#### Most Successful Competitors (Highest Win Rate)")
    top_winners = comp_df[comp_df['total_bids'] >= 2].nlargest(10, 'Win Rate')[
        ['competitor_name', 'total_bids', 'Win Rate', 'avg_bid_ratio']
    ].copy()
    if len(top_winners) > 0:
        top_winners.columns = ['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']
        top_winners['Win Rate'] = top_winners['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
        top_winners['Avg Bid Ratio'] = top_winners['Avg Bid Ratio'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
        )
        st.dataframe(top_winners, use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data for win rate analysis")
    
    # Strategy distribution
    st.markdown("#### Strategy Distribution")
    strategy_counts = comp_df['preferred_strategy'].value_counts()
    if len(strategy_counts) > 0:
        fig = px.pie(
            values=strategy_counts.values, 
            names=strategy_counts.index, 
            title="Competitor Strategy Breakdown"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Market aggression index
    avg_aggression = comp_df['avg_bid_ratio'].mean()
    st.markdown(f"#### Market Insights")
    if pd.notna(avg_aggression):
        if avg_aggression < 0.89:
            st.warning(f"📊 **Aggressive Market** - Average bid ratio: {avg_aggression*100:.1f}% (Highly competitive)")
        elif avg_aggression < 0.93:
            st.info(f"📊 **Moderate Market** - Average bid ratio: {avg_aggression*100:.1f}% (Balanced competition)")
        else:
            st.success(f"📊 **Conservative Market** - Average bid ratio: {avg_aggression*100:.1f}% (Room for better margins)")


# ============================================================================
# TAB 4: INTELLIGENCE
# ============================================================================

def render_intelligence_tab():
    """Render the main intelligence dashboard"""
    
    st.markdown("### 🧠 Competitor Intelligence Dashboard")
    st.caption("Deep insights into competitor behavior, performance, and market positioning")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please login to view competitor intelligence")
        return
    
    # Get all competitors with stats
    competitors = db.get_competitor_master_list(company_id, active_only=True)
    
    if not competitors:
        st.info("No competitors found. Add competitors to start tracking intelligence.")
        return
    
    comp_df = pd.DataFrame(competitors)
    
    # ========================================================================
    # Intelligence Overview Cards
    # ========================================================================
    st.markdown("#### 📊 Intelligence Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate intelligence metrics
    total_competitors = len(comp_df)
    total_bids = comp_df['total_bids'].sum()
    total_wins = comp_df['total_wins'].sum()
    
    with col1:
        st.metric("Total Competitors", total_competitors)
    with col2:
        st.metric("Total Bids Tracked", total_bids)
    with col3:
        win_rate = (total_wins / total_bids * 100) if total_bids > 0 else 0
        st.metric("Market Win Rate", f"{win_rate:.0f}%")
    with col4:
        avg_ratio = comp_df['avg_bid_ratio'].mean()
        st.metric("Market Avg Bid Ratio", f"{avg_ratio*100:.1f}%" if pd.notna(avg_ratio) else "N/A")
    
    # Strategy breakdown
    st.markdown("#### 🎯 Strategy Distribution")
    strategies = comp_df['preferred_strategy'].value_counts()
    aggressive_count = strategies.get('Aggressive', 0)
    moderate_count = strategies.get('Moderate', 0)
    conservative_count = strategies.get('Conservative', 0)
    variable_count = strategies.get('Variable', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🟢 Aggressive", aggressive_count)
    with col2:
        st.metric("🟡 Moderate", moderate_count)
    with col3:
        st.metric("🔵 Conservative", conservative_count)
    with col4:
        st.metric("🟣 Variable", variable_count)
    
    # ========================================================================
    # Competitor Intelligence Table
    # ========================================================================
    st.markdown("#### 📋 Competitor Intelligence Report")
    
    # Prepare intelligence data with FIXED date handling
    intel_data = []
    for _, comp in comp_df.iterrows():
        total_bids_comp = comp.get('total_bids', 0)
        total_wins_comp = comp.get('total_wins', 0)
        win_rate_comp = (total_wins_comp / total_bids_comp * 100) if total_bids_comp > 0 else 0
        
        # Determine behavior classification
        avg_ratio = comp.get('avg_bid_ratio', 0.92)
        if avg_ratio < 0.88:
            behavior = "Aggressive Bidder"
        elif avg_ratio < 0.93:
            behavior = "Consistent Bidder"
        else:
            behavior = "Conservative Bidder"
        
        # FIXED: Calculate activity level with proper date handling
        first_seen = comp.get('first_seen')
        last_seen = comp.get('last_seen')
        active_months = None
        
        if first_seen and last_seen:
            # Convert to datetime if they are strings
            if isinstance(first_seen, str):
                try:
                    first_seen = datetime.strptime(first_seen, '%Y-%m-%d')
                except ValueError:
                    first_seen = None
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d')
                except ValueError:
                    last_seen = None
            
            # Calculate difference if both are valid datetime objects
            if first_seen and last_seen:
                active_months = ((last_seen - first_seen).days / 30.44)
        
        intel_data.append({
            'Competitor': comp.get('competitor_name', 'Unknown'),
            'Strategy': comp.get('preferred_strategy', 'Unknown'),
            'Behavior': behavior,
            'Bids': total_bids_comp,
            'Wins': total_wins_comp,
            'Win Rate': win_rate_comp,
            'Avg Bid Ratio': avg_ratio,
            'Active Months': f"{active_months:.0f}" if active_months else "N/A",
            'ID': comp.get('id')
        })
    
    intel_df = pd.DataFrame(intel_data)
    
    # Display with color coding
    st.dataframe(
        intel_df[['Competitor', 'Strategy', 'Behavior', 'Bids', 'Win Rate', 'Avg Bid Ratio', 'Active Months']],
        use_container_width=True,
        hide_index=True,
        column_config={
            'Competitor': 'Competitor Name',
            'Strategy': st.column_config.TextColumn("Strategy", width="small"),
            'Behavior': st.column_config.TextColumn("Behavior Pattern", width="small"),
            'Bids': st.column_config.NumberColumn("Total Bids", width="small"),
            'Win Rate': st.column_config.NumberColumn("Win Rate (%)", width="small", format="%.1f%%"),
            'Avg Bid Ratio': st.column_config.NumberColumn("Avg Bid Ratio", width="small", format="%.2f"),
            'Active Months': st.column_config.TextColumn("Active (Months)", width="small")
        }
    )
    
    # ========================================================================
    # Quick Access to Intelligence Profiles
    # ========================================================================
    st.markdown("#### 🔍 Quick Access to Full Intelligence Profiles")
    
    top_competitors = intel_df.nlargest(5, 'Bids')
    
    if not top_competitors.empty:
        cols = st.columns(min(5, len(top_competitors)))
        for idx, (_, comp) in enumerate(top_competitors.iterrows()):
            if idx < len(cols):
                with cols[idx]:
                    comp_name = comp['Competitor']
                    comp_id = comp['ID']
                    if st.button(
                        f"🧠 {comp_name[:12]}{'...' if len(comp_name) > 12 else ''}",
                        key=f"quick_intel_{comp_id}",
                        help=f"View full intelligence profile for {comp_name}"
                    ):
                        st.query_params.competitor_id = comp_id
                        st.session_state.page = "competitor_profile"

        
        st.caption("Showing top 5 competitors by bid frequency")
    
    # ========================================================================
    # Market Intelligence Insights
    # ========================================================================
    st.markdown("#### 📈 Market Intelligence Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Market Positioning**")
        if avg_ratio:
            if avg_ratio < 0.89:
                st.warning("🟢 Market is **highly competitive** - aggressive pricing is common")
            elif avg_ratio < 0.93:
                st.info("🟡 Market is **moderately competitive** - balanced approach recommended")
            else:
                st.success("🔵 Market is **less competitive** - room for better margins")
    
    with col2:
        st.markdown("**Recommendations**")
        if aggressive_count > conservative_count:
            st.write("• Consider **competitive pricing** to win more tenders")
            st.write("• Focus on **cost optimization** and efficiency")
        elif moderate_count > aggressive_count:
            st.write("• **Balanced strategy** is working well")
            st.write("• Maintain current approach and monitor trends")
        else:
            st.write("• Opportunity for **margin improvement**")
            st.write("• Consider **differentiation** strategies")
    
    # ========================================================================
    # Export Intelligence Data
    # ========================================================================
    if st.button("📥 Export Intelligence Report", use_container_width=True):
        csv = intel_df.to_csv(index=False)
        st.download_button(
            "💾 Download CSV",
            csv,
            f"competitor_intelligence_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            key="export_intelligence"
        )


# ============================================================================
# TAB 5: TRACKING
# ============================================================================
def render_tracking_tab():
    """Render competitor tracking dashboard"""
    
    st.markdown("### 📊 Competitor Tracking")
    st.caption("Track competitor behavior patterns and predict future bids")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please login to view competitor tracking")
        return
    
    # Use the CompetitorTracker class
    from modules.competitor_tracking import CompetitorTracker
    
    tracker = CompetitorTracker(company_id)
    insights = tracker.get_competitor_insights()
    
    if not insights:
        st.info("📭 No competitor data yet. As you save analysis results, competitor profiles will be built automatically.")
        return
    
    # Display tracking metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tracked", insights['total_competitors'])
    with col2:
        st.metric("Aggressive", insights['aggressive_count'])
    with col3:
        st.metric("Moderate", insights['moderate_count'])
    with col4:
        st.metric("Conservative", insights['conservative_count'])
    
    st.markdown("---")
    
    # Competitor list with tracking data
    competitors_data = insights['competitors']
    
    # Convert to DataFrame and handle dates
    competitors_df = pd.DataFrame(
        competitors_data,
        columns=['Name', 'Strategy', 'Appearances', 'Avg Bid Ratio', 'Wins', 'Last Seen']
    )
    competitors_df['Avg Bid Ratio'] = competitors_df['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
    competitors_df['Win Rate'] = (
        competitors_df['Wins'] / competitors_df['Appearances'] * 100
    ).apply(lambda x: f"{x:.0f}%")
    
    # Fix Last Seen date formatting
    def format_date(date_val):
        if date_val:
            if isinstance(date_val, str):
                try:
                    return datetime.strptime(date_val, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    return 'N/A'
            elif hasattr(date_val, 'strftime'):
                return date_val.strftime('%Y-%m-%d')
        return 'N/A'
    
    competitors_df['Last Seen'] = competitors_df['Last Seen'].apply(format_date)
    
    st.markdown("#### 📊 Competitor Profiles")
    st.dataframe(
        competitors_df[['Name', 'Strategy', 'Appearances', 'Win Rate', 'Avg Bid Ratio', 'Last Seen']],
        use_container_width=True,
        hide_index=True,
        column_config={
            'Name': 'Competitor',
            'Strategy': st.column_config.TextColumn("Strategy", width="small"),
            'Appearances': st.column_config.NumberColumn("Bids", width="small"),
            'Win Rate': st.column_config.TextColumn("Win %", width="small"),
            'Avg Bid Ratio': st.column_config.TextColumn("Avg Bid %", width="small"),
            'Last Seen': st.column_config.TextColumn("Last Seen", width="small")
        }
    )
    
    # Market intelligence
    st.markdown("---")
    st.markdown("#### 📈 Market Intelligence")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Market Bid Ratio", f"{insights['avg_market_ratio']*100:.1f}%")
    
    with col2:
        if insights['aggressive_count'] > insights['conservative_count']:
            st.warning("⚠️ Market is aggressive - consider more competitive pricing")
        elif insights['conservative_count'] > insights['aggressive_count']:
            st.success("✅ Market is conservative - room for better margins")
        else:
            st.info("📊 Market is balanced - moderate approach recommended")

# ============================================================================
# TAB 6: SETTINGS
# ============================================================================

def render_settings_tab(can_edit: bool):
    """Render competitor settings"""
    
    st.markdown("### ⚙️ Competitor Settings")
    
    if not can_edit:
        st.info("🔒 You don't have permission to modify competitor settings.")
        return
    
    # Display current settings
    st.markdown("#### Current Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📊 **Data Collection**")
        st.write("• Auto-track competitor bids from tender analyses")
        st.write("• Update profiles on each new bid")
        st.write("• Store up to 5 years of history")
    
    with col2:
        st.info("🎯 **Intelligence Settings**")
        st.write("• Behavioral classification: Active")
        st.write("• Market aggression tracking: Active")
        st.write("• Win rate analysis: Active")
    
    # Export data option
    st.markdown("---")
    st.markdown("#### 📤 Data Management")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Export All Competitor Data", use_container_width=True):
            company_id = st.session_state.get('company_id')
            competitors = db.get_competitor_master_list(company_id, active_only=False)
            if competitors:
                df = pd.DataFrame(competitors)
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 Download Full Dataset",
                    csv,
                    f"competitor_full_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No competitor data to export")
    
    with col2:
        if st.button("📊 Export Bid History", use_container_width=True):
            company_id = st.session_state.get('company_id')
            history = db.query(
                "SELECT * FROM competitor_bid_history WHERE company_id = ?",
                (company_id,)
            )
            if history:
                df = pd.DataFrame(history)
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 Download Bid History",
                    csv,
                    f"competitor_bid_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No bid history data to export")
    
    with col3:
        if st.button("🔄 Recalculate Stats", use_container_width=True):
            with st.spinner("Recalculating competitor statistics..."):
                company_id = st.session_state.get('company_id')
                competitors = db.get_competitor_master_list(company_id, active_only=False)
                for comp in competitors:
                    db.update_competitor_stats_from_bid(
                        company_id,
                        comp['competitor_name'],
                        comp.get('avg_bid_ratio', 0.92),
                        False
                    )
                st.success("✅ Statistics recalculated successfully!")
    
    # Danger zone
    if st.session_state.get('user_role') in ['system_admin', 'admin']:
        st.markdown("---")
        st.warning("⚠️ Danger Zone")
        
        if st.button("🗑️ Clear All Competitor Data", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear_competitors'):
                company_id = st.session_state.get('company_id')
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM competitor_profiles WHERE company_id = ?", (company_id,))
                cursor.execute("DELETE FROM competitor_bid_history WHERE company_id = ?", (company_id,))
                cursor.execute("DELETE FROM competitor_master WHERE company_id = ?", (company_id,))
                conn.commit()
                conn.close()
                st.success("✅ All competitor data cleared!")
                st.session_state.confirm_clear_competitors = False
                st.rerun()
            else:
                st.session_state.confirm_clear_competitors = True
                st.warning("⚠️ Click again to confirm clearing ALL competitor data")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_competitor_by_name(company_id: int, competitor_name: str) -> Optional[Dict]:
    """Get competitor by name"""
    return db.query_one(
        "SELECT * FROM competitor_master WHERE company_id = ? AND competitor_name = ?",
        (company_id, competitor_name)
    )


def get_competitor_intelligence_summary(company_id: int) -> Dict[str, Any]:
    """Get intelligence summary for a company"""
    result = db.query_one("""
        SELECT 
            COUNT(*) as total_competitors,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_competitors,
            SUM(total_bids) as total_bids,
            SUM(total_wins) as total_wins,
            AVG(avg_bid_ratio) as avg_market_ratio
        FROM competitor_master
        WHERE company_id = ?
    """, (company_id,))
    
    if not result:
        return {
            'total_competitors': 0,
            'active_competitors': 0,
            'total_bids': 0,
            'total_wins': 0,
            'avg_market_ratio': 0.0,
            'overall_win_rate': 0.0
        }
    
    total_bids = result.get('total_bids', 0) or 0
    total_wins = result.get('total_wins', 0) or 0
    result['overall_win_rate'] = (total_wins / total_bids * 100) if total_bids > 0 else 0
    
    return result