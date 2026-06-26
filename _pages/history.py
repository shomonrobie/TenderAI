import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def show():
    """Tender analysis history page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📜 Tender Analysis History</h1>
        <p>View all your past tender analyses</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user's analyses
    analyses_df = db.get_user_analyses(
        st.session_state.user_id, 
        st.session_state.company_id, 
        st.session_state.user_role,
        limit=100
    )
    
    if len(analyses_df) == 0:
        st.info("No analyses found. Create your first analysis!")
        if st.button("Create New Analysis"):
            st.session_state.page = "new_analysis"
            st.rerun()
        return
    
    # Filters
    st.markdown("### 🔍 Filter Analyses")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'division' in analyses_df.columns:
            division_filter = st.multiselect("Division", options=analyses_df['division'].unique())
        else:
            division_filter = []
    
    with col2:
        if 'bid_status' in analyses_df.columns:
            status_filter = st.multiselect("Status", options=['Won', 'Lost', 'Pending'])
        else:
            status_filter = []
    
    with col3:
        date_range = st.date_input("Date Range", value=[])
    
    # Apply filters
    filtered_df = analyses_df.copy()
    if division_filter:
        filtered_df = filtered_df[filtered_df['division'].isin(division_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['bid_status'].isin(status_filter)]
    
    # Statistics
    st.markdown("### 📊 Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Analyses", len(filtered_df))
    
    with col2:
        if 'bid_status' in filtered_df.columns:
            won = len(filtered_df[filtered_df['bid_status'] == 'Won'])
            st.metric("Won Tenders", won)
    
    with col3:
        if 'bid_status' in filtered_df.columns:
            win_rate = (won / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.0f}%")
    
    with col4:
        if 'recommended_bid' in filtered_df.columns:
            avg_bid = filtered_df['recommended_bid'].mean()
            st.metric("Avg Recommended Bid", f"BDT {avg_bid:,.0f}")
    
    # Display analyses table
    st.markdown("### 📋 Analyses List")
    
    display_cols = ['tender_id', 'tender_title', 'procuring_entity', 'division', 
                    'official_estimate', 'recommended_bid', 'success_probability', 
                    'risk_level', 'bid_status', 'analysis_date']
    
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    
    if available_cols:
        # Format numeric columns
        display_df = filtered_df[available_cols].copy()
        if 'official_estimate' in display_df.columns:
            display_df['official_estimate'] = display_df['official_estimate'].apply(lambda x: f"BDT {x:,.0f}")
        if 'recommended_bid' in display_df.columns:
            display_df['recommended_bid'] = display_df['recommended_bid'].apply(lambda x: f"BDT {x:,.0f}")
        if 'success_probability' in display_df.columns:
            display_df['success_probability'] = display_df['success_probability'].apply(lambda x: f"{x*100:.0f}%")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Export option
    st.markdown("---")
    if st.button("📥 Export to CSV", use_container_width=True):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"tender_analyses_{st.session_state.username}.csv",
            mime="text/csv"
        )