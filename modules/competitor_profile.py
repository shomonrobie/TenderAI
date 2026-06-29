"""
Competitor Intelligence Profile Module
Detailed view for a single competitor with analytics and insights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Optional

from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription_manager import check_subscription_access

db = UnifiedDatabaseManager()


def render_competitor_profile_page(db=None, subscription_manager=None):
    """
    Render the competitor intelligence profile page
    
    This is called from the main app routing, not as a standalone page
    """
    
    # Subscription check
    company_id = st.session_state.get('company_id')
    user_id = st.session_state.get('user_id')
    has_access, plan, msg = check_subscription_access(company_id, user_id, subscription_manager)

    if not has_access:
        st.warning(msg)
        st.info("Upgrade to access competitor intelligence profiles.")
        return
    
    # Get competitor ID from query params
    competitor_id = st.query_params.get('competitor_id')
    
    if not competitor_id:
        st.error("No competitor selected")
        st.info("Please go back to the Competitor Master page and select a competitor.")
        
        if st.button("⬅ Back to Competitor List"):
            st.session_state.page = "competitor_master"
            st.rerun()
        return
    
    try:
        competitor_id = int(competitor_id)
    except ValueError:
        st.error("Invalid competitor ID")
        return
    
    # Load competitor data
    competitor_data = load_competitor_data(competitor_id, company_id)
    
    if not competitor_data:
        st.error("Competitor not found or you don't have access to this data")
        if st.button("⬅ Back to Competitor List"):
            st.session_state.page = "competitor_master"
            st.rerun()
        return
    
    # Render the profile
    render_competitor_profile(competitor_data)


def load_competitor_data(competitor_id: int, company_id: int) -> Optional[Dict]:
    """
    Load all competitor data for the profile
    
    Args:
        competitor_id: The competitor's ID
        company_id: The company ID for tenant isolation
    
    Returns:
        Dictionary with all competitor data or None
    """
    # Get competitor details
    competitor = db.get_competitor_by_id(competitor_id)
    
    if not competitor or competitor.get('company_id') != company_id:
        return None
    
    # Get bid history
    history = db.get_competitor_bid_history(company_id, competitor['competitor_name'])
    
    # Get competitor profiles (for analytics)
    profiles = db.get_competitor_profiles(company_id)
    profile = next(
        (p for p in profiles if p.get('competitor_name') == competitor['competitor_name']),
        None
    )
    
    # Calculate analytics from history
    analytics = calculate_analytics(history)
    
    # Generate insights
    insights = generate_insights(competitor, history, analytics, profile)
    
    # Prepare chart data
    chart_data = prepare_chart_data(history)
    
    return {
        'competitor': competitor,
        'profile': profile,
        'history': history,
        'analytics': analytics,
        'insights': insights,
        'charts': chart_data
    }


def calculate_analytics(history: list) -> Dict:
    """
    Calculate analytics from bid history
    
    Args:
        history: List of bid history records
    
    Returns:
        Dictionary with analytics metrics
    """
    if not history:
        return {
            'total_bids': 0,
            'total_wins': 0,
            'win_rate': 0,
            'avg_bid': 0,
            'avg_discount': 0,
            'avg_rank': 0,
            'avg_nppi': 0,
            'avg_slt': 0,
            'avg_bid_ratio': 0,
            'std_discount': 0,
            'min_discount': 0,
            'max_discount': 0,
            'median_discount': 0,
            'avg_competition_level': 0
        }
    
    df = pd.DataFrame(history)
    
    total_bids = len(df)
    total_wins = len(df[df.get('was_winner', False) == True])
    
    # Calculate discounts if official_estimate and bid_amount exist
    if 'official_estimate' in df.columns and 'bid_amount' in df.columns:
        df['discount'] = ((df['official_estimate'] - df['bid_amount']) / df['official_estimate']) * 100
        discounts = df['discount'].dropna()
    else:
        discounts = pd.Series([0])
    
    # Calculate bid ratios
    if 'official_estimate' in df.columns and 'bid_amount' in df.columns:
        df['bid_ratio'] = df['bid_amount'] / df['official_estimate']
        ratios = df['bid_ratio'].dropna()
    else:
        ratios = pd.Series([0])
    
    return {
        'total_bids': total_bids,
        'total_wins': total_wins,
        'win_rate': (total_wins / total_bids * 100) if total_bids > 0 else 0,
        'avg_bid': df['bid_amount'].mean() if 'bid_amount' in df.columns else 0,
        'avg_discount': discounts.mean() if len(discounts) > 0 else 0,
        'avg_rank': df['rank'].mean() if 'rank' in df.columns else 0,
        'avg_nppi': 0,  # Placeholder - calculate if NPPI data available
        'avg_slt': 0,   # Placeholder - calculate if SLT data available
        'avg_bid_ratio': ratios.mean() if len(ratios) > 0 else 0,
        'std_discount': discounts.std() if len(discounts) > 0 else 0,
        'min_discount': discounts.min() if len(discounts) > 0 else 0,
        'max_discount': discounts.max() if len(discounts) > 0 else 0,
        'median_discount': discounts.median() if len(discounts) > 0 else 0,
        'avg_competition_level': 0  # Placeholder - calculate if competition data available
    }


def generate_insights(competitor: Dict, history: list, analytics: Dict, profile: Dict) -> Dict:
    """
    Generate deterministic insights for the competitor
    
    Args:
        competitor: Competitor details
        history: Bid history
        analytics: Calculated analytics
        profile: Competitor profile
    
    Returns:
        Dictionary with insights
    """
    insights = {
        'behavioral': [],
        'activity': [],
        'bidding': [],
        'strategy': []
    }
    
    # ============================================================
    # Behavioral Insights (based on analytics)
    # ============================================================
    volatility = analytics.get('std_discount', 0)
    if volatility < 3:
        insights['behavioral'].append("🎯 Highly consistent bidder (very low variance in discounts)")
    elif volatility < 8:
        insights['behavioral'].append("📊 Consistent bidder (moderate variance in discounts)")
    elif volatility < 15:
        insights['behavioral'].append("🔄 Variable bidder (significant variance in discounts)")
    else:
        insights['behavioral'].append("🎲 Aggressive bidder (highly variable discount patterns)")
    
    # Win rate analysis
    win_rate = analytics.get('win_rate', 0)
    if win_rate > 40:
        insights['behavioral'].append(f"🏆 Strong performer: Win rate of {win_rate:.1f}%")
    elif win_rate > 25:
        insights['behavioral'].append(f"📈 Competitive performer: Win rate of {win_rate:.1f}%")
    elif win_rate > 10:
        insights['behavioral'].append(f"📊 Developing performer: Win rate of {win_rate:.1f}%")
    else:
        insights['behavioral'].append(f"📉 Needs improvement: Win rate of {win_rate:.1f}%")
    
    # Discount strategy
    avg_discount = analytics.get('avg_discount', 0)
    if avg_discount > 20:
        insights['behavioral'].append(f"💪 Aggressive pricing: Average discount of {avg_discount:.1f}%")
    elif avg_discount > 10:
        insights['behavioral'].append(f"📊 Balanced pricing: Average discount of {avg_discount:.1f}%")
    elif avg_discount > 5:
        insights['behavioral'].append(f"💰 Conservative pricing: Average discount of {avg_discount:.1f}%")
    else:
        insights['behavioral'].append(f"🛡️ Premium positioning: Average discount of {avg_discount:.1f}%")
    
    # ============================================================
    # Activity Insights
    # ============================================================
    if history:
        # Calculate activity period
        df = pd.DataFrame(history)
        if 'bid_date' in df.columns:
            df['bid_date'] = pd.to_datetime(df['bid_date'])
            first_date = df['bid_date'].min()
            last_date = df['bid_date'].max()
            active_months = ((last_date - first_date).days / 30.44) if first_date and last_date else 0
            
            if active_months < 3:
                insights['activity'].append("🆕 New entrant: Active for less than 3 months")
            elif active_months < 12:
                insights['activity'].append(f"📈 Active competitor: Active for {active_months:.0f} months")
            elif active_months < 24:
                insights['activity'].append(f"🏛️ Established competitor: Active for {active_months:.0f} months")
            else:
                insights['activity'].append(f"🏗️ Veteran competitor: Active for {active_months:.0f} months")
            
            # Recent activity
            days_since_last = (pd.Timestamp.now() - last_date).days if last_date else 999
            if days_since_last < 30:
                insights['activity'].append(f"⚡ Highly active: Last bid {days_since_last} days ago")
            elif days_since_last < 90:
                insights['activity'].append(f"📊 Moderately active: Last bid {days_since_last} days ago")
            elif days_since_last < 180:
                insights['activity'].append(f"⏸️ Less active: Last bid {days_since_last} days ago")
            else:
                insights['activity'].append(f"⚠️ Inactive: Last bid over {days_since_last} days ago")
            
            # Frequency
            bids_per_month = len(df) / active_months if active_months > 0 else 0
            if bids_per_month > 3:
                insights['activity'].append(f"🔥 High frequency: ~{bids_per_month:.1f} bids per month")
            elif bids_per_month > 1:
                insights['activity'].append(f"📊 Moderate frequency: ~{bids_per_month:.1f} bids per month")
            else:
                insights['activity'].append(f"🐢 Low frequency: ~{bids_per_month:.1f} bids per month")
    
    # ============================================================
    # Bidding Insights
    # ============================================================
    if analytics.get('total_bids', 0) > 0:
        # Typical bidding range (20th-80th percentile)
        if 'bid_ratio' in analytics:
            avg_ratio = analytics.get('avg_bid_ratio', 0)
            insights['bidding'].append(f"📊 Typical bid ratio: {avg_ratio*100:.1f}% of OCE")
        
        # Win rate
        insights['bidding'].append(f"🏆 Win rate: {analytics.get('win_rate', 0):.1f}%")
        
        # Total experience
        total_bids = analytics.get('total_bids', 0)
        if total_bids > 50:
            insights['bidding'].append(f"💪 Extensive experience: {total_bids} total bids")
        elif total_bids > 20:
            insights['bidding'].append(f"📈 Significant experience: {total_bids} total bids")
        else:
            insights['bidding'].append(f"📊 Growing experience: {total_bids} total bids")
    
    # ============================================================
    # Strategy Insights (from profile if available)
    # ============================================================
    if profile:
        strategy = profile.get('strategy', 'Unknown')
        insights['strategy'].append(f"📋 Preferred strategy: {strategy}")
        
        # Confidence level based on appearances
        appearances = profile.get('total_appearances', 0)
        if appearances > 20:
            insights['strategy'].append(f"📊 High confidence prediction: {appearances} data points")
        elif appearances > 10:
            insights['strategy'].append(f"📊 Moderate confidence prediction: {appearances} data points")
        else:
            insights['strategy'].append(f"📊 Low confidence prediction: {appearances} data points")
    
    return insights


def prepare_chart_data(history: list) -> Dict:
    """
    Prepare data for charts
    
    Args:
        history: List of bid history records
    
    Returns:
        Dictionary with chart data
    """
    if not history:
        return {}
    
    df = pd.DataFrame(history)
    
    # Ensure bid_date is datetime
    if 'bid_date' in df.columns:
        df['bid_date'] = pd.to_datetime(df['bid_date'])
        df = df.sort_values('bid_date')
    
    # Calculate discount if not present
    if 'discount' not in df.columns and 'official_estimate' in df.columns and 'bid_amount' in df.columns:
        df['discount'] = ((df['official_estimate'] - df['bid_amount']) / df['official_estimate']) * 100
    
    # Prepare chart data
    chart_data = {}
    
    # 1. Discount vs Time
    if 'bid_date' in df.columns and 'discount' in df.columns:
        chart_data['discount_vs_time'] = df[['bid_date', 'discount']].dropna()
    
    # 2. Bid vs OCE
    if 'official_estimate' in df.columns and 'bid_amount' in df.columns:
        chart_data['bid_vs_oce'] = df[['official_estimate', 'bid_amount']].dropna()
    
    # 3. Win Rate Trend (rolling average)
    if 'bid_date' in df.columns and 'was_winner' in df.columns:
        df_sorted = df.sort_values('bid_date')
        df_sorted['win_rate_rolling'] = df_sorted['was_winner'].rolling(window=5, min_periods=1).mean() * 100
        chart_data['win_rate_trend'] = df_sorted[['bid_date', 'win_rate_rolling']].dropna()
    
    # 4. Participation Timeline
    if 'bid_date' in df.columns:
        participation = df.groupby(df['bid_date'].dt.date).size().reset_index(name='count')
        participation.columns = ['bid_date', 'count']
        chart_data['participation_timeline'] = participation
    
    # 5. Bid Distribution
    if 'bid_amount' in df.columns:
        chart_data['bid_distribution'] = df['bid_amount'].dropna()
    
    # 6. Rank Distribution
    if 'rank' in df.columns:
        chart_data['rank_distribution'] = df['rank'].dropna()
    
    return chart_data


def render_competitor_profile(data: Dict):
    """
    Render the competitor profile UI
    
    Args:
        data: Dictionary with all competitor data
    """
    competitor = data['competitor']
    history = data['history']
    analytics = data['analytics']
    insights = data['insights']
    charts = data['charts']
    
    # ============================================================================
    # HEADER
    # ============================================================================
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title(f"🏢 {competitor.get('competitor_name', 'Unknown Competitor')}")
        if competitor.get('business_type'):
            st.caption(f"Business Type: {competitor['business_type']}")
        if competitor.get('notes'):
            st.caption(f"📝 {competitor['notes']}")
    
    with col2:
        first_seen = competitor.get('first_seen')
        if first_seen:
            if isinstance(first_seen, str):
                try:
                    first_seen = datetime.strptime(first_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    first_seen = 'N/A'
            elif hasattr(first_seen, 'strftime'):
                first_seen = first_seen.strftime('%Y-%m-%d')
        else:
            first_seen = 'N/A'
        st.metric("First Seen", first_seen)
    
    with col3:
        last_seen = competitor.get('last_seen')
        if last_seen:
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    last_seen = 'N/A'
            elif hasattr(last_seen, 'strftime'):
                last_seen = last_seen.strftime('%Y-%m-%d')
        else:
            last_seen = 'N/A'
        st.metric("Last Seen", last_seen)
    
    # Back button
    if st.button("⬅ Back to Competitor List", use_container_width=True):
        st.session_state.page = "competitor_master"
        st.rerun()
    
    st.divider()
    
    # ============================================================================
    # SECTION 1: OVERVIEW
    # ============================================================================
    st.header("📊 Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Participations", analytics.get('total_bids', 0))
    with col2:
        st.metric("Total Wins", analytics.get('total_wins', 0))
    with col3:
        st.metric("Win Percentage", f"{analytics.get('win_rate', 0):.1f}%")
    with col4:
        st.metric("Average Bid", f"BDT {analytics.get('avg_bid', 0):,.2f}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Discount from OCE", f"{analytics.get('avg_discount', 0):.1f}%")
    with col2:
        st.metric("Average Rank", f"{analytics.get('avg_rank', 0):.1f}")
    with col3:
        st.metric("Avg Bid Ratio", f"{analytics.get('avg_bid_ratio', 0)*100:.1f}%")
    with col4:
        st.metric("Total Bids", analytics.get('total_bids', 0))
    
    st.divider()
    
    # ============================================================================
    # SECTION 2: TENDER PARTICIPATION HISTORY
    # ============================================================================
    st.header("📜 Tender Participation History")
    
    if history:
        df = pd.DataFrame(history)
        
        # Format dates for display
        if 'bid_date' in df.columns:
            df['bid_date'] = pd.to_datetime(df['bid_date']).dt.strftime('%Y-%m-%d')
        
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search = st.text_input("🔍 Search tenders", placeholder="Search by tender name or ID...")
        with col2:
            show_winner = st.selectbox("Filter", ["All", "Won", "Lost"])
        
        # Apply filters
        if search:
            df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False).any(), axis=1)]
        
        if show_winner == "Won":
            df = df[df['was_winner'] == True]
        elif show_winner == "Lost":
            df = df[df['was_winner'] == False]
        
        # Pagination
        page_size = 10
        total_pages = (len(df) - 1) // page_size + 1 if len(df) > 0 else 1
        page = st.selectbox("Page", range(1, total_pages + 1), index=0) if total_pages > 1 else 1
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Display table
        display_columns = ['tender_id', 'bid_amount', 'official_estimate', 'bid_ratio', 'was_winner', 'rank', 'bid_date']
        available_columns = [col for col in display_columns if col in df.columns]
        
        if available_columns:
            st.dataframe(
                df[available_columns].iloc[start_idx:end_idx],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'tender_id': 'Tender ID',
                    'bid_amount': st.column_config.NumberColumn("Bid Amount", format="BDT %.2f"),
                    'official_estimate': st.column_config.NumberColumn("OCE", format="BDT %.2f"),
                    'bid_ratio': st.column_config.NumberColumn("Bid Ratio", format="%.3f"),
                    'was_winner': 'Winner',
                    'rank': 'Rank',
                    'bid_date': 'Bid Date'
                }
            )
        
        st.caption(f"Showing {len(df.iloc[start_idx:end_idx])} of {len(df)} tenders")
    else:
        st.info("No participation history found for this competitor")
    
    st.divider()
    
    # ============================================================================
    # SECTION 3: COMPETITOR ANALYTICS
    # ============================================================================
    st.header("📈 Competitor Analytics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Discount", f"{analytics.get('avg_discount', 0):.1f}%")
    with col2:
        st.metric("Median Discount", f"{analytics.get('median_discount', 0):.1f}%")
    with col3:
        st.metric("Win Rate", f"{analytics.get('win_rate', 0):.1f}%")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Min Discount", f"{analytics.get('min_discount', 0):.1f}%")
    with col2:
        st.metric("Max Discount", f"{analytics.get('max_discount', 0):.1f}%")
    with col3:
        st.metric("Std Deviation", f"{analytics.get('std_discount', 0):.1f}%")
    
    # ============================================================================
    # BEHAVIORAL OBSERVATIONS
    # ============================================================================
    st.subheader("🧠 Behavioral Observations")
    
    if insights.get('behavioral'):
        for insight in insights['behavioral']:
            st.info(f"• {insight}")
    else:
        st.info("No behavioral insights available")
    
    st.subheader("📊 Activity Insights")
    if insights.get('activity'):
        for insight in insights['activity']:
            st.success(f"• {insight}")
    else:
        st.info("No activity insights available")
    
    st.divider()
    
    # ============================================================================
    # SECTION 4: CHARTS
    # ============================================================================
    st.header("📊 Interactive Charts")
    
    if charts:
        # Chart 1: Discount vs Time
        if 'discount_vs_time' in charts and not charts['discount_vs_time'].empty:
            st.subheader("Discount Trend Over Time")
            fig = px.line(
                charts['discount_vs_time'],
                x='bid_date',
                y='discount',
                title='Discount from OCE Over Time',
                labels={'discount': 'Discount (%)', 'bid_date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Chart 2: Bid vs OCE
        if 'bid_vs_oce' in charts and not charts['bid_vs_oce'].empty:
            st.subheader("Bid vs Official Cost Estimate")
            fig = px.scatter(
                charts['bid_vs_oce'],
                x='official_estimate',
                y='bid_amount',
                title='Bid Amount vs Official Cost Estimate',
                labels={'official_estimate': 'OCE (BDT)', 'bid_amount': 'Bid Amount (BDT)'},
                trendline="ols"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Chart 3: Win Rate Trend
        if 'win_rate_trend' in charts and not charts['win_rate_trend'].empty:
            st.subheader("Win Rate Trend (Rolling Average)")
            fig = px.line(
                charts['win_rate_trend'],
                x='bid_date',
                y='win_rate_rolling',
                title='Win Rate Trend (5-Bid Rolling Average)',
                labels={'win_rate_rolling': 'Win Rate (%)', 'bid_date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Chart 4: Participation Timeline
        if 'participation_timeline' in charts and not charts['participation_timeline'].empty:
            st.subheader("Tender Participation Timeline")
            fig = px.bar(
                charts['participation_timeline'],
                x='bid_date',
                y='count',
                title='Number of Tenders by Date',
                labels={'count': 'Number of Tenders', 'bid_date': 'Date'},
                color='count',
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Charts 5 & 6: Distributions
        col1, col2 = st.columns(2)
        
        with col1:
            if 'bid_distribution' in charts and not charts['bid_distribution'].empty:
                st.subheader("Bid Amount Distribution")
                fig = px.histogram(
                    charts['bid_distribution'],
                    title='Distribution of Bid Amounts',
                    labels={'value': 'Bid Amount (BDT)'},
                    nbins=20,
                    color_discrete_sequence=['blue']
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'rank_distribution' in charts and not charts['rank_distribution'].empty:
                st.subheader("Rank Distribution")
                fig = px.histogram(
                    charts['rank_distribution'],
                    title='Distribution of Ranks Achieved',
                    labels={'value': 'Rank'},
                    nbins=10,
                    color_discrete_sequence=['green']
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("No chart data available for this competitor")
    
    st.divider()
    
    # ============================================================================
    # SECTION 5: AI INSIGHTS
    # ============================================================================
    st.header("🤖 AI Insights")
    st.caption("These insights are generated deterministically from historical data (no LLM required)")
    
    if insights.get('bidding'):
        st.subheader("🎯 Bidding Insights")
        for insight in insights['bidding']:
            st.write(f"• {insight}")
    
    if insights.get('strategy'):
        st.subheader("📊 Strategy Insights")
        for insight in insights['strategy']:
            st.write(f"• {insight}")
    
    st.divider()
    st.caption(f"🔍 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================================
# MAIN ENTRY POINT (for direct page testing)
# ============================================================================

def main():
    """Main entry point for direct page testing"""
    render_competitor_profile_page()


if __name__ == "__main__":
    main()