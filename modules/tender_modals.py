"""
Tender Modal Components
Reusable modal dialogs for tender management
"""

import streamlit as st
from datetime import datetime
import pandas as pd

def show_tender_details_modal(tender):
    """Show tender details in a modal-like expander"""
    
    with st.expander(f"📋 Tender Details: {tender['tender_title']}", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Tender Information")
            st.markdown(f"""
            - **Tender ID:** {tender['tender_id']}
            - **Procuring Entity:** {tender['procuring_entity']}
            - **Division:** {tender.get('division', 'N/A')}
            - **District:** {tender.get('district', 'N/A')}
            - **Thana:** {tender.get('thana', 'N/A')}
            - **Procurement Type:** {tender['procurement_type']}
            - **Official Estimate:** BDT {tender['official_estimate']:,.0f}
            - **Submission Deadline:** {tender['submission_deadline']}
            """)
        
        with col2:
            st.markdown("#### 💰 Bid Information")
            our_bid = tender['our_bid_amount']
            bid_display = f"BDT {our_bid:,.0f}" if our_bid and our_bid > 0 else 'Not set'
            st.markdown(f"""
            - **Our Bid:** {bid_display}
            - **Status:** {tender['bid_status'].upper()}
            - **Tender Security:** BDT {tender.get('tender_security', 0):,.0f}
            - **Document Fee:** BDT {tender.get('document_fee', 0):,.0f}
            """)
            
            if our_bid and our_bid > 0 and tender['official_estimate'] > 0:
                bid_ratio = our_bid / tender['official_estimate'] * 100
                st.markdown(f"- **Bid Ratio:** {bid_ratio:.1f}% of estimate")

def show_team_modal(tender_id, team, user_options):
    """Show team management modal"""
    
    with st.expander(f"👥 Team Management", expanded=True):
        if team:
            st.markdown("**Current Team Members:**")
            for member in team:
                st.markdown(f"- {member[1]} - {member[3]}")
        else:
            st.info("No team members assigned")
        
        st.markdown("---")
        st.markdown("**Add Team Member:**")
        col1, col2 = st.columns(2)
        with col1:
            new_member = st.selectbox("Select Member", ["Select"] + list(user_options.keys()), key=f"modal_member_select")
        with col2:
            role = st.selectbox("Role", ["Bid Manager", "Technical Lead", "Financial Analyst", "Legal Advisor", "Support Staff"], key=f"modal_role_select")
        
        if st.button("➕ Add Member", key=f"modal_add_member"):
            if new_member != "Select" and new_member in user_options:
                return {'action': 'add', 'member_id': user_options[new_member], 'role': role}
        return None

def show_edit_bid_modal(tender_id, current_bid):
    """Show edit bid modal"""
    
    with st.expander(f"✏️ Edit Bid Amount", expanded=True):
        new_bid = st.number_input("Bid Amount (BDT)", value=float(current_bid), step=100000.0, format="%.0f", key=f"modal_bid_input")
        reason = st.text_area("Reason for change (optional)", key=f"modal_reason")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Changes", key=f"modal_save_bid"):
                return {'action': 'save', 'new_bid': new_bid, 'reason': reason}
        with col2:
            if st.button("❌ Cancel", key=f"modal_cancel"):
                return {'action': 'cancel'}
        return None