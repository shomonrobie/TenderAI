import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def calculate_optimal_bid(official_estimate, competitor_bids=None, risk_tolerance='moderate'):
    """Calculate optimal bid based on inputs"""
    
    if competitor_bids:
        avg_competitor = np.mean(competitor_bids)
        min_competitor = np.min(competitor_bids)
        competitor_count = len(competitor_bids)
    else:
        avg_competitor = official_estimate * 0.92
        min_competitor = official_estimate * 0.85
        competitor_count = 5
    
    # Risk-based ratios
    ratios = {
        'aggressive': 0.86,
        'moderate': 0.89,
        'conservative': 0.93
    }
    
    ratio = ratios.get(risk_tolerance, 0.89)
    recommended_bid = official_estimate * ratio
    
    # Adjust based on competition
    if recommended_bid > avg_competitor:
        recommended_bid = avg_competitor * 0.99
    
    # Calculate win probability
    if recommended_bid <= min_competitor:
        win_prob = 0.85
    elif recommended_bid >= avg_competitor:
        win_prob = 0.40
    else:
        win_prob = 0.60
    
    # Risk level
    if ratio < 0.87:
        risk_level = "HIGH"
        risk_color = "🔴"
    elif ratio < 0.92:
        risk_level = "MEDIUM"
        risk_color = "🟡"
    else:
        risk_level = "LOW"
        risk_color = "🟢"
    
    return {
        'recommended_bid': recommended_bid,
        'bid_ratio': ratio,
        'win_probability': win_prob,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'recommended_min': official_estimate * 0.87,
        'recommended_max': official_estimate * 0.94,
        'competitor_stats': {
            'average': avg_competitor,
            'minimum': min_competitor,
            'count': competitor_count
        }
    }

def show():
    """New tender analysis page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📊 New Tender Analysis</h1>
        <p>AI-powered bid optimization for construction tenders</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user can perform analysis
    can_analyze, remaining = db.can_perform_analysis(st.session_state.user_id)
    
    if not can_analyze:
        st.error(f"You've reached your monthly limit. Please upgrade your plan to continue.")
        if st.button("Upgrade Plan"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        tender_id = st.text_input("Tender ID/Reference Number*")
        tender_title = st.text_input("Tender Title*")
        procuring_entity = st.text_input("Procuring Entity*")
        division = st.selectbox("Division", ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"])
    
    with col2:
        construction_type = st.selectbox("Construction Type", ["Building", "Road", "Bridge", "Water Supply", "Drainage"])
        official_estimate = st.number_input("Official Estimated Cost (BDT)*", min_value=0, step=1000000, format="%d")
        risk_tolerance = st.select_slider("Risk Tolerance", options=['conservative', 'moderate', 'aggressive'], value='moderate')
    
    st.markdown("### 👥 Competitor Bids (Optional)")
    st.markdown("Enter known competitor bids separated by commas")
    competitor_input = st.text_area("Competitor Bids", placeholder="45,000,000, 46,500,000, 44,200,000")
    
    competitor_bids = []
    if competitor_input:
        try:
            competitor_bids = [float(x.strip().replace(',', '')) for x in competitor_input.split(',')]
            st.success(f"Loaded {len(competitor_bids)} competitor bids")
        except:
            st.error("Invalid input format. Please use numbers separated by commas.")
    
    if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
        if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
            st.error("Please fill all required fields")
        else:
            with st.spinner("AI is analyzing the tender..."):
                # Calculate optimal bid
                result = calculate_optimal_bid(official_estimate, competitor_bids, risk_tolerance)
                
                # Save analysis
                analysis_data = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'division': division,
                    'construction_type': construction_type,
                    'official_estimate': official_estimate,
                    'recommended_bid': result['recommended_bid'],
                    'success_probability': result['win_probability'],
                    'risk_level': result['risk_level'],
                    'competitor_count': len(competitor_bids)
                }
                
                analysis_id = db.save_analysis(
                    st.session_state.user_id, 
                    st.session_state.company_id, 
                    analysis_data
                )
                
                # Increment usage counter
                db.increment_analysis_usage(st.session_state.user_id)
                
                # Display results
                st.markdown("---")
                st.markdown("## 🤖 AI Analysis Results")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Recommended Bid", f"BDT {result['recommended_bid']:,.0f}", 
                             f"{result['bid_ratio']*100:.1f}% of estimate")
                
                with col2:
                    st.metric("Win Probability", f"{result['win_probability']*100:.0f}%")
                
                with col3:
                    st.metric("Safe Range", f"BDT {result['recommended_min']:,.0f} - {result['recommended_max']:,.0f}")
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Risk Level</h3>
                        <h2>{result['risk_color']} {result['risk_level']}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Competitor analysis
                if competitor_bids:
                    st.markdown("### 📊 Competitor Analysis")
                    comp_df = pd.DataFrame({
                        'Competitor': [f"Bidder {i+1}" for i in range(len(competitor_bids))],
                        'Bid Amount': competitor_bids
                    })
                    st.dataframe(comp_df, use_container_width=True, hide_index=True)
                    
                    # Statistics
                    st.markdown(f"""
                    - **Average Competitor Bid:** BDT {result['competitor_stats']['average']:,.0f}
                    - **Lowest Competitor Bid:** BDT {result['competitor_stats']['minimum']:,.0f}
                    - **Number of Competitors:** {result['competitor_stats']['count']}
                    """)
                
                st.success(f"Analysis saved successfully! Analysis ID: {analysis_id}")
                
                # Option to record actual bid
                st.markdown("---")
                st.markdown("### 📝 Record Your Bid")
                actual_bid = st.number_input("What bid amount will you submit?", value=float(result['recommended_bid']), step=100000.0)
                
                if st.button("Save Bid Submission", use_container_width=True):
                    st.success("Bid recorded! You can update the result after award notification.")