"""
Competitor Profile Tracking System
Tracks competitor behavior patterns over time for better predictions
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.unified_db_manager import UnifiedDatabaseManager
from modules.rbac import (
    rbac, can_view_tenders, can_edit_tender, can_export_data,
    render_role_badge, is_admin, is_company_admin, require_permission
)

db = UnifiedDatabaseManager()


class CompetitorTracker:
    """Track and analyze competitor bidding patterns"""
    
    def __init__(self, company_id):
        self.company_id = company_id
        
    def add_competitor_bid(self, competitor_name: str, tender_id: str, 
                           bid_amount: float, official_estimate: float,
                           was_winner: bool = False, bid_date: str = None):
        """Add a competitor bid record"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if not bid_date:
            bid_date = datetime.now().date()
        
        bid_ratio = bid_amount / official_estimate if official_estimate > 0 else 1.0
        
        try:
            # Add to bid history
            cursor.execute("""
                INSERT INTO competitor_bid_history 
                (company_id, competitor_name, tender_id, bid_amount, official_estimate, 
                 bid_ratio, was_winner, bid_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.company_id, competitor_name, tender_id, bid_amount, 
                  official_estimate, bid_ratio, 1 if was_winner else 0, bid_date))
            
            # Update competitor profile
            self._update_competitor_profile(competitor_name, bid_ratio, was_winner)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding competitor bid: {e}")
            conn.rollback()
            conn.close()
            return False
    
    def update_competitor_profile(self, competitor_name, bid_amount, official_estimate, was_winner=False, tender_id=None):
        """Update or create competitor profile with new bid data"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        bid_ratio = bid_amount / official_estimate if official_estimate > 0 else 0
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_appearances, wins_count, avg_bid_ratio, bid_std_dev
        FROM competitor_profiles 
        WHERE company_id = ? AND competitor_name = ?
        ''', (self.company_id, competitor_name))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing profile
            comp_id, total, wins, avg_ratio, std_dev = existing
            new_total = total + 1
            new_wins = wins + (1 if was_winner else 0)
            
            # Update rolling average
            new_avg_ratio = (avg_ratio * total + bid_ratio) / new_total if new_total > 0 else bid_ratio
            
            # Update standard deviation
            bids = self._get_competitor_bids(competitor_name)
            bids.append(bid_ratio)
            new_std_dev = float(np.std(bids)) if len(bids) > 1 else 0.0
            
            # Determine strategy based on bid ratios
            if new_avg_ratio < 0.88:
                strategy = "Aggressive"
            elif new_avg_ratio < 0.92:
                strategy = "Moderate"
            else:
                strategy = "Conservative"
            
            cursor.execute('''
            UPDATE competitor_profiles 
            SET total_appearances = ?, wins_count = ?, avg_bid_ratio = ?, 
                bid_std_dev = ?, strategy = ?, last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total, new_wins, new_avg_ratio, new_std_dev, strategy, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Create new profile
            strategy = "Aggressive" if bid_ratio < 0.88 else "Moderate" if bid_ratio < 0.92 else "Conservative"
            cursor.execute('''
            INSERT INTO competitor_profiles 
            (company_id, competitor_name, first_seen, last_seen, total_appearances, 
             wins_count, avg_bid_ratio, bid_std_dev, strategy)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ''', (self.company_id, competitor_name, datetime.now().date(), 
                  datetime.now().date(), 1 if was_winner else 0, bid_ratio, 0.0, strategy))
        
        # Save bid history
        if tender_id:
            cursor.execute('''
            INSERT INTO competitor_bid_history 
            (company_id, competitor_name, tender_id, bid_amount, official_estimate, 
             bid_ratio, was_winner, bid_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.company_id, competitor_name, tender_id, bid_amount, 
                  official_estimate, bid_ratio, was_winner, datetime.now().date()))
        
        conn.commit()
        conn.close()
    
    def _get_competitor_bids(self, competitor_name):
        """Get all bid ratios for a competitor"""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT bid_ratio FROM competitor_bid_history 
        WHERE company_id = ? AND competitor_name = ?
        ORDER BY bid_date DESC
        ''', (self.company_id, competitor_name))
        bids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return bids
    
    def get_competitor_insights(self):
        """Get aggregated competitor insights"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT competitor_name, strategy, total_appearances, avg_bid_ratio, 
               wins_count, last_seen
        FROM competitor_profiles 
        WHERE company_id = ?
        ORDER BY total_appearances DESC
        ''', (self.company_id,))
        
        competitors = cursor.fetchall()
        conn.close()
        
        if not competitors:
            return None
        
        insights = {
            'total_competitors': len(competitors),
            'aggressive_count': len([c for c in competitors if c[1] == 'Aggressive']),
            'moderate_count': len([c for c in competitors if c[1] == 'Moderate']),
            'conservative_count': len([c for c in competitors if c[1] == 'Conservative']),
            'competitors': competitors,
            'avg_market_ratio': float(np.mean([c[3] for c in competitors])) if competitors else 0.90
        }
        
        return insights
    
    def predict_competitor_bid(self, competitor_name, official_estimate):
        """Predict what a specific competitor will bid"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT avg_bid_ratio, bid_std_dev, strategy
        FROM competitor_profiles 
        WHERE company_id = ? AND competitor_name = ?
        ''', (self.company_id, competitor_name))
        
        profile = cursor.fetchone()
        conn.close()
        
        if profile:
            avg_ratio, std_dev, strategy = profile
            # Add some randomness based on their historical variance
            random_factor = np.random.normal(0, std_dev * 0.5) if std_dev > 0 else 0
            predicted_ratio = avg_ratio + random_factor
            predicted_ratio = max(0.80, min(0.98, predicted_ratio))
            return official_estimate * predicted_ratio, strategy
        else:
            # Default prediction for unknown competitor
            return official_estimate * 0.90, "Unknown"
    
    def get_competitor_strategy_insights(self):
        """Get detailed competitor strategy insights"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT competitor_name, strategy, avg_bid_ratio, total_appearances, wins_count,
               (wins_count * 1.0 / total_appearances) as win_rate
        FROM competitor_profiles 
        WHERE company_id = ? AND total_appearances >= 2
        ORDER BY total_appearances DESC
        ''', (self.company_id,))
        
        competitors = cursor.fetchall()
        conn.close()
        
        if not competitors:
            return None
        
        insights = {
            'total_tracked': len(competitors),
            'aggressive': [c for c in competitors if c[1] == 'Aggressive'],
            'moderate': [c for c in competitors if c[1] == 'Moderate'],
            'conservative': [c for c in competitors if c[1] == 'Conservative'],
            'high_win_rate': [c for c in competitors if c[5] > 0.5],
            'most_frequent': competitors[:5] if competitors else []
        }
        
        # Calculate market aggression index
        total_bids = sum(c[3] for c in competitors)
        aggressive_bids = sum(c[3] for c in competitors if c[1] == 'Aggressive')
        insights['market_aggression_index'] = aggressive_bids / total_bids if total_bids > 0 else 0.5
        
        return insights
    
    def predict_competitor_behavior(self, competitor_name, official_estimate):
        """Enhanced competitor behavior prediction"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT avg_bid_ratio, bid_std_dev, strategy, total_appearances, wins_count
        FROM competitor_profiles 
        WHERE company_id = ? AND competitor_name = ?
        ''', (self.company_id, competitor_name))
        
        profile = cursor.fetchone()
        conn.close()
        
        if not profile:
            return {
                'predicted_bid': official_estimate * 0.91,
                'strategy': 'Unknown',
                'confidence': 0.40,
                'min_expected': official_estimate * 0.85,
                'max_expected': official_estimate * 0.96
            }
        
        avg_ratio, std_dev, strategy, appearances, wins = profile
        
        # Calculate confidence based on data points
        confidence = min(0.95, 0.50 + (appearances * 0.03))
        
        # Predict with confidence interval
        predicted_ratio = avg_ratio
        min_ratio = max(0.75, avg_ratio - (std_dev * 1.5))
        max_ratio = min(1.00, avg_ratio + (std_dev * 1.5))
        
        return {
            'predicted_bid': official_estimate * predicted_ratio,
            'strategy': strategy,
            'confidence': confidence,
            'appearances': appearances,
            'win_rate': wins / appearances if appearances > 0 else 0,
            'min_expected': official_estimate * min_ratio,
            'max_expected': official_estimate * max_ratio
        }


@require_permission('can_view_tenders')
def render_competitor_tracking_page():
    """Render competitor tracking dashboard with RBAC"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 Competitor Tracking</h1>
        <p>Track competitor behavior patterns for better bid predictions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Check premium access
    subscription = db.get_user_subscription(st.session_state.user_id)
    user_role = st.session_state.get('user_role', 'viewer')
    is_premium = subscription.get('plan') in ['professional', 'enterprise'] or user_role in ['admin', 'system_admin']
    
    if not is_premium:
        st.warning("⚠️ Competitor tracking is available for Professional and Enterprise plans only.")
        st.info("💡 Upgrade your plan to access competitor intelligence features.")
        if st.button("💳 Upgrade Now", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    # Get user permissions
    permissions = rbac.get_current_user_permissions()
    can_edit = permissions.get('can_edit_tender', False) or user_role in ['admin', 'system_admin', 'company_admin']
    can_export = permissions.get('can_export_data', False) or user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Competitor Analytics", "⚙️ Settings"])
    
    with tab1:
        render_competitor_dashboard(can_edit, can_export)
    
    with tab2:
        render_competitor_analytics(can_export)
    
    with tab3:
        render_competitor_settings(can_edit)


def render_competitor_dashboard(can_edit: bool, can_export: bool):
    """Render competitor dashboard"""
    
    tracker = CompetitorTracker(st.session_state.company_id)
    insights = tracker.get_competitor_insights()
    
    if not insights:
        st.info("📭 No competitor data yet. As you save analysis results, competitor profiles will be built automatically.")
        
        # Show how to add competitor data
        with st.expander("ℹ️ How to track competitors", expanded=True):
            st.markdown("""
            **Competitor data is automatically collected when you:**
            1. Run bid optimization for tenders
            2. Add competitor bids during analysis
            3. Record competitor information in tender results
            
            **To manually add competitor data:**
            - Go to **Competitor Master Database** tab
            - Add competitors to master list
            - Record their bids in tender analysis
            """)
            
            if st.button("📋 Go to Competitor Master Database", use_container_width=True):
                st.session_state.page = "competitor_master"
                st.rerun()
        return
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Competitors Tracked", insights['total_competitors'])
    with col2:
        st.metric("Aggressive Bidders", insights['aggressive_count'])
    with col3:
        st.metric("Moderate Bidders", insights['moderate_count'])
    with col4:
        st.metric("Conservative Bidders", insights['conservative_count'])
    
    st.markdown("---")
    
    # Competitor list
    st.markdown("### 📊 Competitor Profiles")
    
    competitors_df = pd.DataFrame(insights['competitors'], 
                                  columns=['Name', 'Strategy', 'Appearances', 'Avg Bid Ratio', 'Wins', 'Last Seen'])
    competitors_df['Avg Bid Ratio'] = competitors_df['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
    competitors_df['Win Rate'] = (competitors_df['Wins'] / competitors_df['Appearances'] * 100).apply(lambda x: f"{x:.0f}%")
    
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
            'Last Seen': st.column_config.DateColumn("Last Seen", width="small")
        }
    )
    
    # Export option
    if can_export:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📥 Export Competitor Data", use_container_width=True):
                csv = competitors_df.to_csv(index=False)
                st.download_button(
                    "💾 Download CSV",
                    csv,
                    f"competitor_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="export_competitor_data"
                )
    
    # Market Intelligence
    st.markdown("---")
    st.markdown("### 📈 Market Intelligence")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Market Bid Ratio", f"{insights['avg_market_ratio']*100:.1f}% of estimate")
    
    with col2:
        if insights['aggressive_count'] > insights['conservative_count']:
            st.warning("⚠️ Market is aggressive - consider more competitive pricing")
        elif insights['conservative_count'] > insights['aggressive_count']:
            st.success("✅ Market is conservative - room for better margins")
        else:
            st.info("📊 Market is balanced - moderate approach recommended")
    
    # Strategy distribution chart
    strategy_data = {
        'Strategy': ['Aggressive', 'Moderate', 'Conservative'],
        'Count': [insights['aggressive_count'], insights['moderate_count'], insights['conservative_count']]
    }
    strategy_df = pd.DataFrame(strategy_data)
    
    if not strategy_df.empty and strategy_df['Count'].sum() > 0:
        st.subheader("Strategy Distribution")
        st.bar_chart(strategy_df.set_index('Strategy'))


def render_competitor_analytics(can_export: bool):
    """Render competitor analytics"""
    
    tracker = CompetitorTracker(st.session_state.company_id)
    strategy_insights = tracker.get_competitor_strategy_insights()
    
    if not strategy_insights:
        st.info("Not enough data for analytics. Need at least 2 bids per competitor.")
        return
    
    st.markdown("### 📊 Competitor Strategy Analysis")
    
    # Strategy breakdown
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Competitors Tracked", strategy_insights['total_tracked'])
    with col2:
        st.metric("Market Aggression Index", f"{strategy_insights['market_aggression_index']*100:.0f}%")
    with col3:
        high_win = len(strategy_insights.get('high_win_rate', []))
        st.metric("High Win Rate Competitors", high_win)
    
    st.markdown("---")
    
    # Most frequent competitors
    if strategy_insights.get('most_frequent'):
        st.markdown("#### Most Active Competitors")
        frequent_df = pd.DataFrame(strategy_insights['most_frequent'],
                                   columns=['Name', 'Strategy', 'Avg Ratio', 'Appearances', 'Wins', 'Win Rate'])
        frequent_df['Avg Ratio'] = frequent_df['Avg Ratio'].apply(lambda x: f"{x*100:.1f}%")
        frequent_df['Win Rate'] = frequent_df['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(frequent_df[['Name', 'Strategy', 'Appearances', 'Win Rate', 'Avg Ratio']], 
                    use_container_width=True, hide_index=True)
    
    # Export analytics
    if can_export:
        st.markdown("---")
        if st.button("📥 Export Analytics Report", use_container_width=True):
            report_data = {
                'total_competitors': strategy_insights['total_tracked'],
                'aggressive_count': len(strategy_insights.get('aggressive', [])),
                'moderate_count': len(strategy_insights.get('moderate', [])),
                'conservative_count': len(strategy_insights.get('conservative', [])),
                'market_aggression_index': strategy_insights['market_aggression_index']
            }
            report_df = pd.DataFrame([report_data])
            csv = report_df.to_csv(index=False)
            st.download_button(
                "💾 Download Analytics CSV",
                csv,
                f"competitor_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )


def render_competitor_settings(can_edit: bool):
    """Render competitor tracking settings"""
    
    st.markdown("### ⚙️ Competitor Tracking Settings")
    
    if not can_edit:
        st.info("🔒 You don't have permission to modify competitor tracking settings.")
        return
    
    st.info("⚙️ Settings panel coming soon. Currently, competitor tracking is automatic based on bid analysis data.")
    
    # Option to clear data (admin only)
    if is_admin():
        st.markdown("---")
        st.warning("⚠️ Danger Zone")
        if st.button("🗑️ Clear All Competitor Data", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear_competitors'):
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM competitor_profiles WHERE company_id = ?", (st.session_state.company_id,))
                cursor.execute("DELETE FROM competitor_bid_history WHERE company_id = ?", (st.session_state.company_id,))
                conn.commit()
                conn.close()
                st.success("✅ All competitor data cleared!")
                st.rerun()
            else:
                st.session_state.confirm_clear_competitors = True
                st.warning("⚠️ Click again to confirm clearing ALL competitor data")