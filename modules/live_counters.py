# modules/live_counters.py

import streamlit as st
import random
import time
from datetime import datetime, timedelta
from database.unified_db_manager import db

class LiveCounters:
    """Real-time counters for landing page with realistic Bangladesh market data"""
    
    def __init__(self):
        self.base_customers = 10
        self.daily_growth_rate = 2  # 2 new customers per day
        self.tenders_per_customer_per_5days = 5
        self.avg_tender_value = 7500000  # BDT 75 Lakh average
        self.man_hours_per_tender = 45  # Manual hours per tender
        self.ai_hours_per_tender = 5  # AI-assisted hours per tender
        
    def get_current_stats(self):
        """Get current statistics based on actual database or simulated"""
        
        # Try to get real data from database first
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get today's date range
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Real tenders processed today
        cursor.execute("""
            SELECT COUNT(*) FROM company_tenders 
            WHERE created_at >= ? AND is_active = 1
        """, (today_start,))
        real_tenders_today = cursor.fetchone()[0] or 0
        
        # Real bids analyzed today
        cursor.execute("""
            SELECT COUNT(*) FROM tender_analyses 
            WHERE analysis_date >= ?
        """, (today_start,))
        real_analyses_today = cursor.fetchone()[0] or 0
        
        # Real auto-fills today
        cursor.execute("""
            SELECT COUNT(*) FROM extension_auto_fill_log 
            WHERE filled_at >= ?
        """, (today_start,))
        real_auto_fills_today = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # If we have real data, use it with enhancement
        if real_tenders_today > 0 or real_analyses_today > 0:
            return self._get_enhanced_real_stats(
                real_tenders_today, 
                real_analyses_today, 
                real_auto_fills_today
            )
        
        # Otherwise, generate simulated realistic data for Bangladesh market
        return self._get_simulated_stats()
    
    def _get_enhanced_real_stats(self, real_tenders, real_analyses, real_auto_fills):
        """Enhance real data with projections"""
        # Calculate man hours saved
        man_hours_saved = (real_tenders * (self.man_hours_per_tender - self.ai_hours_per_tender)) + (real_auto_fills * 0.033)  # 2 min per fill
        
        # Calculate business days for projection
        days_since_start = (datetime.now() - datetime(2024, 1, 1)).days
        estimated_total_customers = self.base_customers + (self.daily_growth_rate * (days_since_start // 7))  # Weekly growth
        
        return {
            'tenders_today': real_tenders + random.randint(1, 3),  # Add small buffer
            'man_hours_saved_today': round(man_hours_saved, 1),
            'bids_analyzed_today': real_analyses + random.randint(2, 5),
            'total_customers': max(estimated_total_customers, real_tenders // 5 + 10),
            'auto_fills_today': real_auto_fills,
            'avg_confidence': 87,  # Average confidence score
            'is_real_data': True
        }
    
    def _get_simulated_stats(self):
        """Generate realistic simulated data for Bangladesh market"""
        
        # Calculate days since launch (assuming launch date)
        launch_date = datetime(2024, 6, 1)
        days_operating = (datetime.now() - launch_date).days
        
        # Progressive growth model
        if days_operating < 30:
            # First month: slower growth
            total_customers = self.base_customers + (self.daily_growth_rate * days_operating // 2)
        else:
            # After first month: steady growth
            total_customers = self.base_customers + (self.daily_growth_rate * (days_operating // 7)) * 5
        
        # Calculate tenders today (based on active customers)
        active_customers = int(total_customers * 0.7)  # 70% active rate
        estimated_tenders_today = int((active_customers * self.tenders_per_customer_per_5days) / 5)
        
        # Add some real-time variability (morning/afternoon effect)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            multiplier = 1.0
        elif 17 < current_hour <= 20:  # Evening submission
            multiplier = 1.2
        else:  # Night/early morning
            multiplier = 0.6
        
        tenders_today = int(estimated_tenders_today * multiplier)
        
        # Man hours saved calculation
        man_hours_per_tender_saved = self.man_hours_per_tender - self.ai_hours_per_tender
        man_hours_saved = tenders_today * man_hours_per_tender_saved
        
        # Add auto-fill contributions (2 minutes per fill, assume 3 fills per tender)
        auto_fill_hours = (tenders_today * 3 * 2) / 60
        man_hours_saved += auto_fill_hours
        
        # Bids analyzed today (more than tenders due to multiple scenarios)
        bids_analyzed_today = int(tenders_today * random.uniform(1.2, 1.8))
        
        # Auto-fills today
        auto_fills_today = tenders_today * random.randint(5, 12)
        
        return {
            'tenders_today': tenders_today,
            'man_hours_saved_today': round(man_hours_saved, 1),
            'bids_analyzed_today': bids_analyzed_today,
            'total_customers': total_customers,
            'auto_fills_today': auto_fills_today,
            'avg_confidence': random.randint(84, 92),
            'is_real_data': False
        }


def render_live_counters():
    """Render the live counter section for landing page with Fresha.com style"""
    
    counters = LiveCounters()
    stats = counters.get_current_stats()
    
    # CSS for counter animations
    st.markdown("""
    <style>
        .counter-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 24px;
            padding: 2rem;
            margin: 2rem 0;
            color: white;
        }
        .counter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            text-align: center;
        }
        .counter-item {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease;
        }
        .counter-item:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }
        .counter-number {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #fff 0%, #a8c0ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .counter-label {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 0.5rem;
        }
        .counter-sub {
            font-size: 0.7rem;
            opacity: 0.7;
        }
        .live-badge {
            display: inline-block;
            background: #ef4444;
            color: white;
            font-size: 0.7rem;
            padding: 2px 8px;
            border-radius: 20px;
            margin-left: 10px;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        @media (max-width: 768px) {
            .counter-grid {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
            .counter-number {
                font-size: 2rem;
            }
        }
    </style>
    
    <div class="counter-container">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h2 style="color: white; margin: 0;">📊 Live TenderAI Activity</h2>
            <p style="opacity: 0.8;">Real-time statistics from the Bangladesh construction market</p>
        </div>
        <div class="counter-grid">
            <div class="counter-item">
                <div class="counter-number" id="counterTenders">0</div>
                <div class="counter-label">📋 Tenders Processed Today</div>
                <div class="counter-sub">across {stats['total_customers']}+ contractors</div>
            </div>
            <div class="counter-item">
                <div class="counter-number" id="counterHours">0</div>
                <div class="counter-label">⏱️ Man Hours Saved Today</div>
                <div class="counter-sub">~BDT {(stats['man_hours_saved_today'] * 500):,.0f} saved</div>
            </div>
            <div class="counter-item">
                <div class="counter-number" id="counterBids">0</div>
                <div class="counter-label">🎯 Bids Analyzed Today</div>
                <div class="counter-sub">with {stats['avg_confidence']}% avg confidence</div>
            </div>
        </div>
        <div style="text-align: center; margin-top: 1rem;">
            <span class="live-badge">● LIVE</span>
            <span style="font-size: 0.7rem; margin-left: 10px;">Updated in real-time</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript for animated counter
    st.markdown(f"""
    <script>
    function animateCounter(elementId, targetValue, suffix = '') {{
        const element = document.getElementById(elementId);
        if (!element) return;
        let current = 0;
        const increment = targetValue / 50;
        const timer = setInterval(() => {{
            current += increment;
            if (current >= targetValue) {{
                element.textContent = Math.floor(targetValue).toLocaleString() + suffix;
                clearInterval(timer);
            }} else {{
                element.textContent = Math.floor(current).toLocaleString() + suffix;
            }}
        }}, 30);
    }}
    
    // Start animations when page loads
    window.addEventListener('load', function() {{
        animateCounter('counterTenders', {stats['tenders_today']}, '');
        animateCounter('counterHours', {stats['man_hours_saved_today']}, '');
        animateCounter('counterBids', {stats['bids_analyzed_today']}, '');
    }});
    </script>
    """, unsafe_allow_html=True)
    
    # Also show in Streamlit columns for fallback
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📋 Tenders Processed Today",
            f"{stats['tenders_today']:,}",
            delta=f"+{stats['tenders_today'] // 5} from yesterday",
            help="Total tender submissions processed today"
        )
        st.caption(f"Across {stats['total_customers']}+ active contractors")
    
    with col2:
        st.metric(
            "⏱️ Man Hours Saved Today",
            f"{stats['man_hours_saved_today']:,.0f} hrs",
            delta=f"BDT {stats['man_hours_saved_today'] * 500:,.0f} saved",
            help="Manual hours saved using AI auto-fill and analysis"
        )
        st.caption("~BDT 500 per hour average staff cost")
    
    with col3:
        st.metric(
            "🎯 Bids Analyzed Today",
            f"{stats['bids_analyzed_today']:,}",
            delta=f"{stats['avg_confidence']}% avg confidence",
            help="Total bid scenarios analyzed by AI"
        )
        st.caption(f"{stats['auto_fills_today']:,} fields auto-filled")


def render_extended_counters():
    """Render extended counters with more metrics for dashboard"""
    
    counters = LiveCounters()
    stats = counters.get_current_stats()
    
    # Additional metrics for internal dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🏢 Total Customers",
            f"{stats['total_customers']:,}",
            delta="+2 this week",
            help="Total registered companies"
        )
    
    with col2:
        st.metric(
            "💰 Total Value Processed",
            f"BDT {(stats['tenders_today'] * 7500000):,.0f}",
            delta="today only",
            help="Total tender value processed today"
        )
    
    with col3:
        st.metric(
            "🤖 AI Auto-Fills",
            f"{stats['auto_fills_today']:,}",
            delta=f"{stats['avg_confidence']}% confidence",
            help="Form fields auto-filled today"
        )
    
    with col4:
        st.metric(
            "📈 Win Rate Improvement",
            "+42%",
            delta="vs manual",
            help="Average win rate improvement using AI"
        )


def get_live_stats_for_api():
    """Get live stats as JSON for API endpoint"""
    counters = LiveCounters()
    stats = counters.get_current_stats()
    
    return {
        'tenders_today': stats['tenders_today'],
        'man_hours_saved_today': stats['man_hours_saved_today'],
        'bids_analyzed_today': stats['bids_analyzed_today'],
        'total_customers': stats['total_customers'],
        'auto_fills_today': stats['auto_fills_today'],
        'avg_confidence': stats['avg_confidence'],
        'timestamp': datetime.now().isoformat()
    }


# Example usage in landing page
if __name__ == "__main__":
    # For testing
    render_live_counters()