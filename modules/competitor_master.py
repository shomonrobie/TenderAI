# modules/competitor_master.py - Refactored with Unique Keys

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple, Any

from database.unified_db_manager import get_db_manager
from modules.subscription_manager import check_subscription_access
from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, render_protected_button, can_import_tender_data,
)


def render_competitor_master_page(db=None, subscription_manager=None):
    """Render competitor master management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 Competitor Intelligence Dashboard</h1>
        <p>Manage competitors and gain intelligence insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ✅ Use cached db manager
    if db is None:
        db = get_db_manager()
    
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
    
    # Create tabs (7 tabs now)
    tabs = st.tabs([
        "📋 Competitor List", 
        "➕ Add Competitor", 
        "📊 Analytics", 
        "🧠 Full Profile",
        "🔍 Tracking", 
        "⚙️ Settings",
        "📈 Bid History"
    ])
    
    with tabs[0]:
        render_competitor_list(db)
    
    with tabs[1]:
        render_add_competitor_form(db)
    
    with tabs[2]:
        render_competitor_analytics(db)
    
    with tabs[3]:
        render_full_profile_tab(db)
    
    with tabs[4]:
        render_tracking_tab(db)
    
    with tabs[5]:
        render_settings_tab(db, can_edit)
    
    with tabs[6]:
        render_bid_history_tab(db)


# ============================================================================
# TAB 0: COMPETITOR LIST
# ============================================================================

def render_competitor_list(db):
    """Display the main competitor dashboard"""
    
    company_id = st.session_state.get('company_id')
    
    # ✅ Use CRUD method
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
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
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
    
    # Competitor List Table
    st.markdown("### 📋 Competitor List")
    
    # Search and Filter - with UNIQUE KEYS
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input(
            "🔍 Search Competitor",
            placeholder="Enter competitor name...",
            key="competitor_list_search"
        )
    with col2:
        filter_type = st.selectbox(
            "Filter",
            ["All", "Active", "Inactive"],
            key="competitor_list_filter"
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Name", "Total Bids", "Win Rate", "Last Seen"],
            key="competitor_list_sort"
        )
    
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
    
    if 'competitor_page' not in st.session_state:
        st.session_state.competitor_page = 1
    
    page = st.session_state.competitor_page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_competitors = filtered_competitors[start_idx:end_idx]
    
    # Display table
    if page_competitors:
        cols = st.columns([3, 2, 2, 2, 1])
        cols[0].write("**Competitor Name**")
        cols[1].write("**Type**")
        cols[2].write("**First Seen**")
        cols[3].write("**Last Seen**")
        cols[4].write("**Details**")
        st.divider()
        
        for comp in page_competitors:
            cols = st.columns([3, 2, 2, 2, 1])
            
            cols[0].write(f"**{comp.get('competitor_name', 'Unknown')}**")
            cols[1].write(comp.get('business_type', 'N/A'))
            
            first_seen = comp.get('first_seen')
            if first_seen and isinstance(first_seen, str):
                try:
                    first_seen = datetime.strptime(first_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    first_seen = 'N/A'
            elif first_seen:
                first_seen = first_seen.strftime('%Y-%m-%d') if hasattr(first_seen, 'strftime') else 'N/A'
            else:
                first_seen = 'N/A'
            cols[2].write(first_seen)
            
            last_seen = comp.get('last_seen')
            if last_seen and isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    last_seen = 'N/A'
            elif last_seen:
                last_seen = last_seen.strftime('%Y-%m-%d') if hasattr(last_seen, 'strftime') else 'N/A'
            else:
                last_seen = 'N/A'
            cols[3].write(last_seen)
            
            comp_id = comp.get('id')
            if cols[4].button("🔍", key=f"view_{comp_id}", help=f"View full intelligence profile for {comp.get('competitor_name')}"):
                st.query_params.competitor_id = comp_id
                st.session_state.page = "competitor_profile"
        
        # Pagination controls
        st.divider()
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if page > 1:
                if st.button("◀ Previous", key="competitor_prev_page"):
                    st.session_state.competitor_page = page - 1
                    st.rerun()
        with col2:
            st.caption(f"Page {page} of {total_pages} | Showing {len(page_competitors)} of {len(filtered_competitors)} competitors")
        with col3:
            if page < total_pages:
                if st.button("Next ▶", key="competitor_next_page"):
                    st.session_state.competitor_page = page + 1
                    st.rerun()
    else:
        st.info("No competitors match your filters")


# ============================================================================
# TAB 1: ADD COMPETITOR
# ============================================================================

def render_add_competitor_form(db):
    """Form to add new competitor to master list"""
    
    st.markdown("### Add New Competitor")
    st.caption("Add competitors once, then select from dropdown when recording historical tenders")
    
    with st.form("add_competitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            competitor_name = st.text_input("Competitor Name*")
            business_type = st.selectbox("Business Type", [
                "Construction Company", "Trading Company", 
                "Joint Venture", "Individual", "Other"
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
        
        st.markdown("---")
        st.markdown("#### 🧠 Intelligence Fields")
        details = st.text_area(
            "Competitor Intelligence Notes",
            placeholder="e.g., Known strengths, weaknesses, past performance, market position...",
            height=100
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
                    'notes': notes + "\n" + details if details else notes,
                    'preferred_strategy': preferred_strategy
                }
                
                # ✅ Use CRUD method
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
# TAB 2: ANALYTICS
# ============================================================================

def render_competitor_analytics(db):
    """Display competitor analytics and insights"""
    
    st.markdown("### 📊 Competitor Analytics")
    
    company_id = st.session_state.get('company_id')
    
    # ✅ Get both master and profile data
    competitors = db.get_competitor_master_list(company_id)
    profiles = db.get_competitor_profiles(company_id)
    
    if not competitors:
        st.info("No competitor data available. Add competitors and record historical tenders.")
        return
    
    comp_df = pd.DataFrame(competitors)
    profile_df = pd.DataFrame(profiles) if profiles else pd.DataFrame()
    
    comp_df['Win Rate'] = comp_df.apply(
        lambda x: x['total_wins'] / x['total_bids'] if x['total_bids'] > 0 else 0, axis=1
    )
    
    # Most frequent competitors
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
    
    # Competitor Type Distribution (from competitor_profiles)
    if not profile_df.empty and 'competitor_type' in profile_df.columns:
        st.markdown("#### Competitor Personality Distribution")
        type_counts = profile_df['competitor_type'].value_counts()
        if len(type_counts) > 0:
            fig = px.bar(
                x=type_counts.index,
                y=type_counts.values,
                title="Personality Types",
                labels={'x': 'Type', 'y': 'Count'},
                color=type_counts.index,
                color_discrete_sequence=px.colors.qualitative.Set2
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
# TAB 3: FULL PROFILE (NEW - consumes competitor_profiles)
# ============================================================================

def render_full_profile_tab(db):
    """Render full competitor profile from competitor_profiles table"""
    
    st.markdown("### 🧠 Competitor Personality & Behavioural Profile")
    st.caption("Deep behavioural intelligence derived from competitor_profiles")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please login to view competitor profiles")
        return
    
    # ✅ Fetch from competitor_profiles
    profiles = db.get_competitor_profiles(company_id)
    
    if not profiles:
        st.info("No detailed profiles available. Profiles are automatically built from bid history.")
        st.info("💡 Tip: Record historical tenders with competitor bids to generate profiles.")
        return
    
    profile_df = pd.DataFrame(profiles)
    
    # KPI Cards
    st.markdown("#### 📊 Profile Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Profiles", len(profile_df))
    with col2:
        aggressive = len(profile_df[profile_df['competitor_type'] == 'Aggressive']) if 'competitor_type' in profile_df.columns else 0
        st.metric("🟢 Aggressive", aggressive)
    with col3:
        conservative = len(profile_df[profile_df['competitor_type'] == 'Conservative']) if 'competitor_type' in profile_df.columns else 0
        st.metric("🔵 Conservative", conservative)
    with col4:
        balanced = len(profile_df[profile_df['competitor_type'] == 'Balanced']) if 'competitor_type' in profile_df.columns else 0
        st.metric("🟡 Balanced", balanced)
    
    st.divider()
    
    # Profile Cards with personality display
    st.markdown("#### 📋 Competitor Profiles")
    
    # Search - with UNIQUE KEY
    search_profile = st.text_input(
        "🔍 Search Competitor",
        placeholder="Enter competitor name...",
        key="profile_search"
    )
    
    filtered_profiles = profiles.copy()
    if search_profile:
        filtered_profiles = [p for p in filtered_profiles if search_profile.lower() in p.get('competitor_name', '').lower()]
    
    # Display as cards
    for idx, profile in enumerate(filtered_profiles[:20]):
        with st.expander(f"🧠 {profile.get('competitor_name', 'Unknown')}", expanded=(idx == 0)):
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Behavioural Profile**")
                comp_type = profile.get('competitor_type', 'Unknown')
                if comp_type == 'Aggressive':
                    st.warning(f"⚡ {comp_type}")
                elif comp_type == 'Conservative':
                    st.info(f"🛡️ {comp_type}")
                elif comp_type == 'Balanced':
                    st.success(f"⚖️ {comp_type}")
                else:
                    st.write(comp_type)
                
                strategy = profile.get('strategy', 'N/A')
                st.write(f"**Strategy:** {strategy}")
                
                first_seen = profile.get('first_seen')
                last_seen = profile.get('last_seen')
                st.write(f"**Active Period:** {first_seen} → {last_seen}")
            
            with col2:
                st.markdown("**Performance Metrics**")
                appearances = profile.get('total_appearances', 0)
                wins = profile.get('wins_count', 0)
                win_rate = (wins / appearances * 100) if appearances > 0 else 0
                st.metric("Appearances", appearances)
                st.metric("Wins", wins)
                st.metric("Win Rate", f"{win_rate:.0f}%")
            
            with col3:
                st.markdown("**Bid Behaviour**")
                avg_ratio = profile.get('avg_bid_ratio', 0)
                std_dev = profile.get('bid_std_dev', 0)
                st.metric("Avg Bid Ratio", f"{avg_ratio*100:.1f}%" if avg_ratio else "N/A")
                st.metric("Consistency (Std Dev)", f"{std_dev:.3f}" if std_dev else "N/A")
                
                # Consistency indicator
                if std_dev and std_dev < 0.05:
                    st.success("✅ Highly Consistent")
                elif std_dev and std_dev < 0.10:
                    st.info("⚖️ Moderately Consistent")
                elif std_dev:
                    st.warning("⚠️ Highly Variable")
            
            # Notes (from competitor_profiles)
            notes = profile.get('notes')
            if notes:
                st.markdown("---")
                st.markdown("**📝 Intelligence Notes**")
                st.info(notes[:500] + "..." if len(notes) > 500 else notes)
    
    # AI Insights section
    st.markdown("---")
    st.markdown("#### 🤖 AI-Generated Insights")
    
    if not profile_df.empty:
        # Find the most aggressive competitor
        if 'avg_bid_ratio' in profile_df.columns:
            most_aggressive = profile_df.loc[profile_df['avg_bid_ratio'].idxmin()] if not profile_df['avg_bid_ratio'].isna().all() else None
            if most_aggressive is not None:
                st.info(f"**Most Aggressive Competitor:** {most_aggressive.get('competitor_name')} "
                       f"(avg bid ratio {most_aggressive.get('avg_bid_ratio', 0)*100:.1f}%)")
        
        # Find the most consistent competitor
        if 'bid_std_dev' in profile_df.columns:
            most_consistent = profile_df.loc[profile_df['bid_std_dev'].idxmin()] if not profile_df['bid_std_dev'].isna().all() else None
            if most_consistent is not None:
                st.success(f"**Most Consistent Competitor:** {most_consistent.get('competitor_name')} "
                          f"(std dev {most_consistent.get('bid_std_dev', 0):.3f})")
        
        # Find the most successful competitor
        profile_df['Win Rate'] = profile_df.apply(
            lambda x: x.get('wins_count', 0) / x.get('total_appearances', 1) if x.get('total_appearances', 0) > 0 else 0,
            axis=1
        )
        if not profile_df['Win Rate'].isna().all():
            most_successful = profile_df.loc[profile_df['Win Rate'].idxmax()] if not profile_df['Win Rate'].isna().all() else None
            if most_successful is not None:
                st.info(f"**Most Successful Competitor:** {most_successful.get('competitor_name')} "
                       f"(win rate {most_successful.get('Win Rate', 0)*100:.0f}%)")
    
    # Export profile data
    st.markdown("---")
    if st.button("📥 Export Full Profiles", key="export_profiles_btn", use_container_width=True):
        csv = profile_df.to_csv(index=False)
        st.download_button(
            "💾 Download Profiles CSV",
            csv,
            f"competitor_profiles_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            key="download_profiles_csv"
        )


# ============================================================================
# TAB 4: TRACKING
# ============================================================================

def render_tracking_tab(db):
    """Render competitor tracking dashboard with historical bid data"""
    
    st.markdown("### 📊 Competitor Tracking")
    st.caption("Track competitor behavior patterns and predict future bids")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please login to view competitor tracking")
        return
    
    # ✅ Use CRUD methods
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
    competitors_df = pd.DataFrame(
        competitors_data,
        columns=['Name', 'Strategy', 'Appearances', 'Avg Bid Ratio', 'Wins', 'Last Seen']
    )
    competitors_df['Avg Bid Ratio'] = competitors_df['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
    competitors_df['Win Rate'] = (
        competitors_df['Wins'] / competitors_df['Appearances'] * 100
    ).apply(lambda x: f"{x:.0f}%")
    
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
# TAB 5: SETTINGS
# ============================================================================

def render_settings_tab(db, can_edit: bool):
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
        if st.button("📥 Export All Competitor Data", key="export_competitor_data_btn", use_container_width=True):
            company_id = st.session_state.get('company_id')
            # ✅ Use CRUD method
            competitors = db.get_competitor_master_list(company_id, active_only=False)
            if competitors:
                df = pd.DataFrame(competitors)
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 Download Full Dataset",
                    csv,
                    f"competitor_full_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_competitor_data"
                )
            else:
                st.warning("No competitor data to export")
    
    with col2:
        if st.button("📊 Export Bid History", key="export_bid_history_btn", use_container_width=True):
            company_id = st.session_state.get('company_id')
            # ✅ Use CRUD method
            history = db.get_competitor_bid_history(company_id, limit=1000)
            if history:
                df = pd.DataFrame(history)
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 Download Bid History",
                    csv,
                    f"competitor_bid_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_bid_history"
                )
            else:
                st.warning("No bid history data to export")
    
    with col3:
        if st.button("🔄 Recalculate Stats", key="recalc_stats_btn", use_container_width=True):
            with st.spinner("Recalculating competitor statistics..."):
                company_id = st.session_state.get('company_id')
                # ✅ Use CRUD method
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
        
        if st.button("🗑️ Clear All Competitor Data", key="clear_competitor_data_btn", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear_competitors'):
                company_id = st.session_state.get('company_id')
                db.execute("DELETE FROM competitor_profiles WHERE company_id = ?", (company_id,))
                db.execute("DELETE FROM competitor_bid_history WHERE company_id = ?", (company_id,))
                db.execute("DELETE FROM competitor_master WHERE company_id = ?", (company_id,))
                st.success("✅ All competitor data cleared!")
                st.session_state.confirm_clear_competitors = False
                st.rerun()
            else:
                st.session_state.confirm_clear_competitors = True
                st.warning("⚠️ Click again to confirm clearing ALL competitor data")


# ============================================================================
# TAB 6: BID HISTORY (NEW - consumes competitor_bid_history)
# ============================================================================

def render_bid_history_tab(db):
    """Render detailed bid history timeline from competitor_bid_history"""
    
    st.markdown("### 📈 Competitor Bid History Timeline")
    st.caption("Historical bid data per competitor over time")
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.warning("Please login to view bid history")
        return
    
    # ✅ Fetch from competitor_bid_history
    history = db.get_competitor_bid_history(company_id, limit=10000)
    
    if not history:
        st.info("No bid history available. Record historical tenders with competitor bids to build history.")
        return
    
    history_df = pd.DataFrame(history)
    
    # Ensure bid_date is datetime
    if 'bid_date' in history_df.columns:
        history_df['bid_date'] = pd.to_datetime(history_df['bid_date'], errors='coerce')
    elif 'created_at' in history_df.columns:
        history_df['bid_date'] = pd.to_datetime(history_df['created_at'], errors='coerce')
    
    # Filters - with UNIQUE KEYS
    st.markdown("#### 🔍 Filter History")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Competitor filter
        competitors = history_df['competitor_name'].unique().tolist() if 'competitor_name' in history_df.columns else []
        selected_competitor = st.selectbox(
            "Select Competitor",
            ["All"] + sorted(competitors),
            key="bid_history_competitor_filter"
        )
    
    with col2:
        # Date range
        min_date = history_df['bid_date'].min().date() if not history_df['bid_date'].isna().all() else datetime.now().date() - timedelta(days=365)
        max_date = history_df['bid_date'].max().date() if not history_df['bid_date'].isna().all() else datetime.now().date()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="bid_history_date_range"
        )
    
    with col3:
        # Sector filter (if available)
        sectors = []
        if 'tender_title' in history_df.columns:
            history_df['sector'] = history_df['tender_title'].apply(
                lambda x: 'Roads' if 'Road' in str(x) else
                          'Bridges' if 'Bridge' in str(x) else
                          'Buildings' if 'Building' in str(x) or 'School' in str(x) or 'Hospital' in str(x) else
                          'Water' if 'Water' in str(x) else
                          'Drainage' if 'Drainage' in str(x) else
                          'General'
            )
            sectors = history_df['sector'].unique().tolist()
        selected_sector = st.selectbox(
            "Sector",
            ["All"] + sorted(sectors) if sectors else ["All"],
            key="bid_history_sector_filter"
        )
    
    with col4:
        # Show winners only?
        show_winners = st.selectbox(
            "Outcome",
            ["All", "Wins Only", "Losses Only"],
            key="bid_history_outcome_filter"
        )
    
    # Apply filters
    filtered_history = history_df.copy()
    
    if selected_competitor != "All" and 'competitor_name' in filtered_history.columns:
        filtered_history = filtered_history[filtered_history['competitor_name'] == selected_competitor]
    
    if len(date_range) == 2 and 'bid_date' in filtered_history.columns:
        filtered_history = filtered_history[
            (filtered_history['bid_date'].dt.date >= date_range[0]) &
            (filtered_history['bid_date'].dt.date <= date_range[1])
        ]
    
    if selected_sector != "All" and 'sector' in filtered_history.columns:
        filtered_history = filtered_history[filtered_history['sector'] == selected_sector]
    
    if show_winners == "Wins Only" and 'was_winner' in filtered_history.columns:
        filtered_history = filtered_history[filtered_history['was_winner'] == True]
    elif show_winners == "Losses Only" and 'was_winner' in filtered_history.columns:
        filtered_history = filtered_history[filtered_history['was_winner'] == False]
    
    # Display metrics
    if not filtered_history.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Encounters", len(filtered_history))
        with col2:
            wins = filtered_history['was_winner'].sum() if 'was_winner' in filtered_history.columns else 0
            st.metric("Wins", wins)
        with col3:
            win_rate = (wins / len(filtered_history) * 100) if len(filtered_history) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.0f}%")
        with col4:
            avg_ratio = filtered_history['bid_ratio'].mean() if 'bid_ratio' in filtered_history.columns else 0
            st.metric("Avg Bid Ratio", f"{avg_ratio*100:.1f}%" if avg_ratio else "N/A")
    
    st.divider()
    
    # Line Chart: Bid Ratio Over Time
    if not filtered_history.empty and 'bid_date' in filtered_history.columns and 'bid_ratio' in filtered_history.columns:
        st.markdown("#### 📈 Bid Ratio Trend (Lower = More Aggressive)")
        
        # Group by month for cleaner trends
        filtered_history['month'] = filtered_history['bid_date'].dt.to_period('M')
        
        # If single competitor selected, show trend with win markers
        if selected_competitor != "All":
            fig = go.Figure()
            
            # Add line trace
            fig.add_trace(go.Scatter(
                x=filtered_history['bid_date'],
                y=filtered_history['bid_ratio'],
                mode='lines+markers',
                name='Bid Ratio',
                line=dict(color='blue'),
                marker=dict(
                    size=8,
                    color=filtered_history['was_winner'].apply(lambda x: 'green' if x else 'red'),
                    symbol='circle',
                    showscale=False
                )
            ))
            
            # Add OCE line (1.0)
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="OCE")
            
            fig.update_layout(
                title=f"Bid Ratio Trend for {selected_competitor}",
                xaxis_title="Date",
                yaxis_title="Bid Ratio (Bid / OCE)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Interpretation
            avg_ratio = filtered_history['bid_ratio'].mean()
            if avg_ratio < 0.88:
                st.warning(f"📊 **Aggressive Bidder** - Average ratio {avg_ratio*100:.1f}%")
            elif avg_ratio < 0.93:
                st.info(f"📊 **Moderate Bidder** - Average ratio {avg_ratio*100:.1f}%")
            else:
                st.success(f"📊 **Conservative Bidder** - Average ratio {avg_ratio*100:.1f}%")
        
        else:
            # Multiple competitors - show average trend
            monthly_avg = filtered_history.groupby('month')['bid_ratio'].mean().reset_index()
            monthly_avg['month'] = monthly_avg['month'].astype(str)
            
            fig = px.line(
                monthly_avg,
                x='month',
                y='bid_ratio',
                title='Market Average Bid Ratio Over Time',
                labels={'month': 'Month', 'bid_ratio': 'Avg Bid Ratio'},
                markers=True
            )
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="OCE")
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed history table
    st.markdown("---")
    st.markdown("#### 📋 Detailed Encounter History")
    
    display_cols = ['competitor_name', 'bid_date', 'bid_amount', 'official_estimate', 'bid_ratio', 'was_winner', 'tender_id']
    if 'sector' in filtered_history.columns:
        display_cols.insert(2, 'sector')
    
    display_df = filtered_history[display_cols].copy() if all(col in filtered_history.columns for col in display_cols) else filtered_history
    
    # Format columns
    if 'bid_date' in display_df.columns:
        display_df['bid_date'] = display_df['bid_date'].dt.strftime('%Y-%m-%d')
    
    if 'was_winner' in display_df.columns:
        display_df['was_winner'] = display_df['was_winner'].apply(lambda x: '✅ Winner' if x else '❌ Lost')
    
    if 'bid_ratio' in display_df.columns:
        display_df['bid_ratio'] = display_df['bid_ratio'].apply(lambda x: f"{x*100:.1f}%")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'competitor_name': 'Competitor',
            'bid_date': 'Date',
            'bid_amount': 'Bid Amount',
            'official_estimate': 'OCE',
            'bid_ratio': 'Bid %',
            'was_winner': 'Outcome',
            'tender_id': 'Tender ID'
        }
    )
    
    # Export
    if st.button("📥 Export Bid History", key="export_bid_history_full_btn", use_container_width=True):
        csv = filtered_history.to_csv(index=False)
        st.download_button(
            "💾 Download History CSV",
            csv,
            f"competitor_bid_history_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            key="download_bid_history_full"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_competitor_by_name(company_id: int, competitor_name: str) -> Optional[Dict]:
    """Get competitor by name - using CRUD"""
    db = get_db_manager()
    return db.get_competitor_by_name(company_id, competitor_name)


def get_competitor_intelligence_summary(company_id: int) -> Dict[str, Any]:
    """Get intelligence summary for a company - using CRUD"""
    db = get_db_manager()
    return db.get_competitor_intelligence_summary(company_id)