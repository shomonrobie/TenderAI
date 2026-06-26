"""
Competitor Master Management
Maintain a master list of all competitors for reuse across tenders
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import re
import json
from typing import Dict, List, Optional, Tuple

from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription_manager import check_subscription_access
from modules.tender_selector_helper import render_tender_selector_with_boq


from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, render_protected_button, can_import_tender_data,
)


db = UnifiedDatabaseManager()

def render_competitor_master_page(db=None, subscription_manager=None):
    """Render competitor master management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📋 Competitor Master Database</h1>
        <p>Manage your competitor list and import tender data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Subscription check
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)

    if not has_access:
        st.warning(msg)
        st.info("Upgrade to use Competitor Master.")
        return
    
    # Check user role for import permission
    user_role = st.session_state.get('user_role', 'viewer')
    #can_import_data = user_role in ['system_admin', 'admin', 'company_admin']
    
    # Create tabs
    tabs = st.tabs([
        "📋 Competitor List", 
        "➕ Add New Competitor", 
        "📊 Competitor Analytics"
    ])
    
    with tabs[0]:
        render_competitor_list()
    
    with tabs[1]:
        render_add_competitor_form()
    
    with tabs[2]:
        render_competitor_analytics()
    
def render_competitor_list():
    """Display and manage competitor list"""
    
    st.markdown("### Competitor Directory")
    
    # Search and filter
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("🔍 Search Competitor", placeholder="Enter competitor name...")
    with col2:
        show_inactive = st.checkbox("Show Inactive Competitors")
    
    competitors = db.get_competitor_master_list(st.session_state.company_id, active_only=not show_inactive)
    
    if not competitors:
        st.info("No competitors found. Add your first competitor using the form above.")
        return
    
    # Convert to DataFrame for display
    comp_df = pd.DataFrame(competitors)
    
    # Create display DataFrame with renamed columns
    display_df = comp_df[['competitor_name', 'business_type', 'total_bids', 'total_wins',
                         'avg_bid_ratio', 'preferred_strategy', 'last_seen', 'is_active']].copy()
    display_df.columns = ['Name', 'Business Type', 'Total Bids', 'Total Wins',
                         'Avg Bid Ratio', 'Strategy', 'Last Seen', 'Active']
    
    # Filter by search
    if search:
        display_df = display_df[display_df['Name'].str.contains(search, case=False)]
    
    # Calculate win rate
    display_df['Win Rate'] = display_df.apply(
        lambda x: f"{x['Total Wins']/x['Total Bids']*100:.0f}%" if x['Total Bids'] > 0 else "0%", axis=1
    )
    display_df['Avg Bid Ratio'] = display_df['Avg Bid Ratio'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    
    # Display
    st.dataframe(
        display_df[['Name', 'Business Type', 'Total Bids', 'Win Rate', 'Avg Bid Ratio', 'Strategy', 'Last Seen']], 
        use_container_width=True, 
        hide_index=True
    )
    
    # Competitor details expander
    st.markdown("---")
    st.markdown("### 🔍 Competitor Details")
    
    # Use the original comp_df for selection
    competitor_names = comp_df['competitor_name'].tolist()
    if competitor_names:
        selected_comp = st.selectbox("Select Competitor to View/Edit", competitor_names)
        
        if selected_comp:
            # Get the competitor data directly from the original DataFrame
            comp_data = comp_df[comp_df['competitor_name'] == selected_comp].iloc[0]
            comp_id = comp_data['id']
            
            # Get full details
            full_details = db.get_competitor_by_id(comp_id)
            
            if full_details:
                with st.expander(f"Details for {selected_comp}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Business Type:** {full_details.get('business_type', 'N/A')}")
                        st.markdown(f"**Contact Person:** {full_details.get('contact_person', 'N/A')}")
                        st.markdown(f"**Phone:** {full_details.get('phone', 'N/A')}")
                        st.markdown(f"**Email:** {full_details.get('email', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**Total Bids:** {full_details.get('total_bids', 0)}")
                        st.markdown(f"**Total Wins:** {full_details.get('total_wins', 0)}")
                        win_rate = (full_details.get('total_wins', 0) / full_details.get('total_bids', 1) * 100 
                                   if full_details.get('total_bids', 0) > 0 else 0)
                        st.markdown(f"**Win Rate:** {win_rate:.0f}%")
                        st.markdown(f"**Preferred Strategy:** {full_details.get('preferred_strategy', 'Unknown')}")
                    
                    st.markdown(f"**Notes:** {full_details.get('notes', 'No notes')}")
                    
                    # Edit option
                    if st.button("✏️ Edit Competitor", key=f"edit_{comp_id}"):
                        st.session_state.edit_competitor = full_details
                        st.rerun()
    else:
        st.info("No competitors available to display details.")

def render_add_competitor_form():
    """Form to add new competitor to master list"""
    
    st.markdown("### Add New Competitor")
    st.caption("Add competitors once, then select from dropdown when recording historical tenders")
    
    with st.form("add_competitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            competitor_name = st.text_input("Competitor Name*")
            business_type = st.selectbox("Business Type", ["Construction Company", "Trading Company", "Joint Venture", "Individual", "Other"])
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number")
        
        with col2:
            email = st.text_input("Email Address")
            address = st.text_area("Address", height=68)
            preferred_strategy = st.selectbox("Observed Strategy", ["Aggressive", "Moderate", "Conservative", "Variable", "Unknown"])
            notes = st.text_area("Additional Notes", height=68)
        
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
                }
                
                comp_id = db.add_competitor_to_master(st.session_state.company_id, competitor_data)
                
                if comp_id:
                    st.success(f"✅ Competitor '{competitor_name}' added to master list!")
                    st.balloons()
                else:
                    st.error("Failed to add competitor. Please try again.")

def render_competitor_analytics():
    """Display competitor analytics and insights"""
    
    st.markdown("### Competitor Analytics")
    
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
    top_frequent = comp_df.nlargest(10, 'total_bids')[['competitor_name', 'total_bids', 'Win Rate', 'avg_bid_ratio']].copy()
    top_frequent.columns = ['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']
    top_frequent['Win Rate'] = top_frequent['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
    top_frequent['Avg Bid Ratio'] = top_frequent['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
    st.dataframe(top_frequent, use_container_width=True, hide_index=True)
    
    # Most successful competitors
    st.markdown("#### Most Successful Competitors (Highest Win Rate)")
    top_winners = comp_df[comp_df['total_bids'] >= 2].nlargest(10, 'Win Rate')[['competitor_name', 'total_bids', 'Win Rate', 'avg_bid_ratio']].copy()
    if len(top_winners) > 0:
        top_winners.columns = ['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']
        top_winners['Win Rate'] = top_winners['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
        top_winners['Avg Bid Ratio'] = top_winners['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        st.dataframe(top_winners, use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data for win rate analysis")
    
    # Strategy distribution
    st.markdown("#### Strategy Distribution")
    strategy_counts = comp_df['preferred_strategy'].value_counts()
    if len(strategy_counts) > 0:
        fig = px.pie(values=strategy_counts.values, names=strategy_counts.index, title="Competitor Strategy Breakdown")
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