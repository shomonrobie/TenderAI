"""
Post-Evaluation Module
Record actual tender results and generate intelligent suggestions
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from database.unified_db_manager import UnifiedDatabaseManager
from modules.rbac import (
    rbac, can_view_tenders, can_edit_tender, can_view_reports,
    can_export_data, render_role_badge, require_permission,
    is_analyst, is_manager, is_company_admin
)

db = UnifiedDatabaseManager()


@require_permission('can_view_tenders')
def render_post_evaluation_page():
    """Post-evaluation page to record actual tender results"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📋 Post-Evaluation & Award Tracking</h1>
        <p>Record actual tender results and generate intelligent suggestions for future bids</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Get user permissions
    permissions = rbac.get_current_user_permissions()
    user_role = st.session_state.get('user_role', 'viewer')
    can_edit = permissions.get('can_edit_tender', False) or user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    # Show permission info
    if user_role == 'viewer':
        st.info("👁️ **Viewer Mode:** You can view post-evaluation data but cannot edit.")
    elif user_role == 'analyst':
        st.info("📈 **Analyst Mode:** You can view post-evaluation data.")
    elif user_role in ['manager', 'company_admin']:
        st.info("📊 **Manager Mode:** You can view and record post-evaluation data.")
    
    # Get all analyses where final submitted bid exists
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, tender_id, tender_title, procuring_entity, official_estimate, 
           recommended_bid, final_submitted_bid, analysis_type, analysis_date,
           bid_status, actual_winning_bid, actual_winner, our_rank_actual
    FROM tender_analyses 
    WHERE company_id = ? AND is_final_submitted = 1
    ORDER BY analysis_date DESC
    ''', (st.session_state.company_id,))
    
    analyses = cursor.fetchall()
    conn.close()
    
    if not analyses:
        st.info("No final submitted bids found. Complete a Three-Tier Analysis and mark a bid as final first.")
        if permissions.get('can_run_analysis', False):
            if st.button("Go to Bid Optimization"):
                st.session_state.page = "new_analysis"
                st.rerun()
        return
    
    # Selection for post-evaluation
    st.markdown("### Select Tender for Post-Evaluation")
    
    tender_options = {f"{a[1]} - {a[2][:50]}": a[0] for a in analyses}
    selected_tender = st.selectbox("Choose Tender", list(tender_options.keys()))
    
    if selected_tender:
        analysis_id = tender_options[selected_tender]
        selected = next(a for a in analyses if a[0] == analysis_id)
        
        st.markdown("---")
        st.markdown("### 📊 Pre-Evaluation Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Official Estimate", f"BDT {selected[4]:,.0f}")
        with col2:
            st.metric("Recommended Bid", f"BDT {selected[5]:,.0f}")
        with col3:
            st.metric("Final Submitted Bid", f"BDT {selected[6]:,.0f}" if selected[6] else "Not set")
        
        st.markdown("---")
        st.markdown("### 🏆 Post-Evaluation Results")
        
        # Check if user can edit
        if not can_edit:
            st.info("🔒 Post-evaluation data is view-only. Contact your admin to edit.")
            
            # Display existing data if any
            if selected[10] and selected[10] > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Actual Winning Bid", f"BDT {selected[10]:,.0f}")
                    st.metric("Winner", selected[11] if selected[11] else "N/A")
                    st.metric("Our Rank", selected[12] if selected[12] else "N/A")
                with col2:
                    st.metric("Total Bidders", selected[12] if selected[12] else "N/A")
                    st.metric("Bid Status", selected[9] if selected[9] else "N/A")
        else:
            # Editable form
            with st.form("post_evaluation_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    actual_winning_bid = st.number_input(
                        "Actual Winning Bid (BDT)*",
                        min_value=0.0,
                        step=100000.0,
                        format="%.0f",
                        value=float(selected[10]) if selected[10] else 0.0
                    )
                    
                    actual_winner = st.text_input(
                        "Winner Name*",
                        value=selected[11] if selected[11] else ""
                    )
                    
                    our_rank = st.number_input(
                        "Our Rank",
                        min_value=1,
                        max_value=50,
                        value=int(selected[12]) if selected[12] else 1,
                        help="1 = Winner"
                    )
                
                with col2:
                    total_bidders = st.number_input(
                        "Total Number of Bidders",
                        min_value=1,
                        max_value=100,
                        value=1
                    )
                    
                    bid_status = st.selectbox(
                        "Bid Status",
                        ["Won", "Lost"],
                        index=0 if selected[9] == "Won" else 1
                    )
                    
                    lessons_learned = st.text_area(
                        "Lessons Learned / Notes",
                        value="",
                        height=100,
                        placeholder="What worked? What could be improved for future bids?"
                    )
                
                submitted = st.form_submit_button("💾 Save Post-Evaluation", type="primary")
                
                if submitted:
                    if actual_winning_bid <= 0 or not actual_winner:
                        st.error("Please fill all required fields")
                    else:
                        # Calculate accuracy score
                        final_bid = selected[6] if selected[6] else selected[5]
                        accuracy_score = 1 - (abs(final_bid - actual_winning_bid) / actual_winning_bid)
                        accuracy_score = max(0, min(1, accuracy_score))
                        
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                        UPDATE tender_analyses 
                        SET actual_winning_bid = ?, actual_winner = ?, our_rank_actual = ?,
                            total_bidders_actual = ?, bid_status = ?, lessons_learned = ?,
                            bid_accuracy_score = ?, post_evaluation_date = ?
                        WHERE id = ?
                        ''', (actual_winning_bid, actual_winner, our_rank, total_bidders,
                              bid_status, lessons_learned, accuracy_score, datetime.now(), analysis_id))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ Post-evaluation saved successfully!")
                        st.balloons()
                        st.rerun()
        
        # Display accuracy if already exists
        if selected[10] and selected[10] > 0:
            st.markdown("---")
            st.markdown("### 📈 Accuracy Analysis")
            
            final_bid = selected[6] if selected[6] else selected[5]
            difference = final_bid - selected[10]
            diff_percent = (difference / selected[10]) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Bid Difference", f"BDT {difference:,.0f}", 
                         f"{diff_percent:+.1f}%" if difference != 0 else "Perfect!")
            with col2:
                st.metric("Accuracy Score", f"{selected[13]*100:.0f}%" if selected[13] else "N/A")
            with col3:
                if selected[9] == "Won":
                    st.success("✅ WE WON!")
                else:
                    st.error("❌ We Lost")


@require_permission('can_view_reports')
def render_intelligent_suggestions():
    """Generate intelligent suggestions based on historical performance"""
    
    st.markdown("""
    <div class="main-header">
        <h1>🧠 Intelligent Bid Suggestions</h1>
        <p>AI-powered recommendations based on your historical bidding performance</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Get user permissions
    permissions = rbac.get_current_user_permissions()
    user_role = st.session_state.get('user_role', 'viewer')
    can_export = permissions.get('can_export_data', False)
    
    # Get all completed analyses with post-evaluation
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, tender_id, tender_title, analysis_type, recommended_bid, final_submitted_bid,
           actual_winning_bid, actual_winner, bid_status, bid_accuracy_score, official_estimate,
           our_rank_actual, total_bidders_actual, lessons_learned
    FROM tender_analyses 
    WHERE company_id = ? AND is_final_submitted = 1 AND actual_winning_bid IS NOT NULL
    ORDER BY analysis_date DESC
    ''', (st.session_state.company_id,))
    
    historical_data = cursor.fetchall()
    conn.close()
    
    if not historical_data:
        st.info("No completed post-evaluation data available. Complete some post-evaluations first.")
        return
    
    st.markdown("### 📊 Performance Summary")
    
    # Calculate statistics
    total_bids = len(historical_data)
    won_bids = len([h for h in historical_data if h[8] == "Won"])
    win_rate = (won_bids / total_bids) * 100 if total_bids > 0 else 0
    
    # Accuracy by analysis type
    analysis_types = {}
    for h in historical_data:
        atype = h[3]
        if atype not in analysis_types:
            analysis_types[atype] = {'count': 0, 'wins': 0, 'accuracy_sum': 0}
        analysis_types[atype]['count'] += 1
        if h[8] == "Won":
            analysis_types[atype]['wins'] += 1
        if h[9]:
            analysis_types[atype]['accuracy_sum'] += h[9]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Bids", total_bids)
    with col2:
        st.metric("Won", won_bids)
    with col3:
        st.metric("Win Rate", f"{win_rate:.0f}%")
    with col4:
        avg_accuracy = np.mean([h[9] for h in historical_data if h[9]]) * 100 if historical_data else 0
        st.metric("Avg Accuracy", f"{avg_accuracy:.0f}%")
    
    # Analysis type performance
    st.markdown("### 📊 Analysis Type Performance")
    
    perf_data = []
    for atype, stats in analysis_types.items():
        win_rate_type = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
        avg_accuracy = (stats['accuracy_sum'] / stats['count']) * 100 if stats['count'] > 0 else 0
        perf_data.append({
            'Analysis Type': atype.upper(),
            'Bids': stats['count'],
            'Wins': stats['wins'],
            'Win Rate': f"{win_rate_type:.0f}%",
            'Avg Accuracy': f"{avg_accuracy:.0f}%"
        })
    
    perf_df = pd.DataFrame(perf_data)
    st.dataframe(perf_df, use_container_width=True, hide_index=True)
    
    # Export option
    if can_export:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📥 Export Report", use_container_width=True):
                csv = perf_df.to_csv(index=False)
                st.download_button(
                    "💾 Download CSV",
                    csv,
                    f"bid_performance_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
    
    # Intelligent recommendations
    st.markdown("---")
    st.markdown("### 💡 Intelligent Recommendations")
    
    # Find best performing analysis type
    if analysis_types:
        best_type = max(analysis_types.items(), 
                       key=lambda x: (x[1]['wins'] / x[1]['count']) if x[1]['count'] > 0 else 0)
        
        st.info(f"🎯 **Best Performing Analysis Type:** {best_type[0].upper()} with {best_type[1]['wins']} wins out of {best_type[1]['count']} bids")
    
    # Calculate optimal bid adjustment
    successful_bids = [h for h in historical_data if h[8] == "Won"]
    if successful_bids:
        bid_ratios = [(h[5] if h[5] else h[4]) / h[10] for h in successful_bids if h[10] > 0]
        if bid_ratios:
            avg_successful_ratio = np.mean(bid_ratios)
            st.success(f"📈 **Optimal Bid Ratio (based on wins):** {avg_successful_ratio*100:.1f}% of official estimate")
            
            # Compare with recommended vs actual
            diff_ratios = []
            for h in historical_data:
                recommended = h[4]
                actual = h[5] if h[5] else recommended
                if recommended > 0:
                    diff_ratio = (actual - recommended) / recommended
                    diff_ratios.append(diff_ratio)
            
            if diff_ratios:
                avg_diff = np.mean(diff_ratios) * 100
                if avg_diff > 0:
                    st.warning(f"⚠️ **Bid Adjustment Pattern:** On average, your final bids are {avg_diff:.1f}% HIGHER than recommended")
                else:
                    st.info(f"📉 **Bid Adjustment Pattern:** On average, your final bids are {abs(avg_diff):.1f}% LOWER than recommended")
    
    # Lessons learned
    st.markdown("---")
    st.markdown("### 📝 Lessons Learned from Past Tenders")
    
    lessons = [h[13] for h in historical_data if h[13]]
    if lessons:
        for lesson in lessons[:5]:
            st.markdown(f"- {lesson}")
    else:
        st.info("No lessons recorded yet. Add lessons when doing post-evaluation.")
    
    # Visualization (available to all)
    st.markdown("### 📊 Bid Accuracy Trend")
    
    accuracy_data = []
    for h in historical_data:
        if h[9]:
            accuracy_data.append({
                'Tender': h[1][:30],
                'Accuracy': h[9] * 100,
                'Status': h[8]
            })
    
    if accuracy_data:
        acc_df = pd.DataFrame(accuracy_data)
        fig = px.bar(acc_df, x='Tender', y='Accuracy', color='Status',
                    title="Bid Accuracy by Tender",
                    labels={'Accuracy': 'Accuracy Score (%)', 'Tender': 'Tender ID'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)