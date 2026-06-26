# modules/landing_counters.py - FIXED VERSION

import streamlit as st
from datetime import datetime, timedelta
import random

class LandingPageCounters:
    """Generate impressive placeholder statistics for landing page"""
    
    def __init__(self):
        # Base values (starting point)
        self.launch_date = datetime(2024, 1, 1)
        self.base_customers = 50
        self.daily_customer_growth = 5  # 5 new customers per day
        self.tenders_per_customer_per_day = 5
        self.reports_per_customer_per_day = 5
        self.man_hours_per_tender = 45  # manual hours without AI
        self.ai_hours_per_tender = 5    # hours with AI
        self.avg_tender_value = 8500000  # BDT 85 Lakh
        
    def get_days_since_launch(self):
        """Calculate days since platform launch"""
        return (datetime.now() - self.launch_date).days
    
    def get_total_customers(self):
        """Calculate total customers (cumulative)"""
        days = self.get_days_since_launch()
        # Exponential growth model for first year, then linear
        if days < 365:
            customers = self.base_customers + (self.daily_customer_growth * days)
        else:
            # After first year, steady growth
            customers = self.base_customers + (self.daily_customer_growth * 365) + (self.daily_customer_growth * 0.5 * (days - 365))
        return int(customers)
    
    def get_today_tenders(self):
        """Get tenders processed today"""
        customers = self.get_total_customers()
        # Assume 80% active rate
        active_customers = int(customers * 0.8)
        # Each active customer creates ~5 tenders per day
        base_tenders = active_customers * self.tenders_per_customer_per_day
        # Add some daily variation
        variation = random.uniform(0.85, 1.15)
        return int(base_tenders * variation)
    
    def get_today_reports(self):
        """Get reports generated today"""
        customers = self.get_total_customers()
        active_customers = int(customers * 0.8)
        base_reports = active_customers * self.reports_per_customer_per_day
        variation = random.uniform(0.9, 1.1)
        return int(base_reports * variation)
    
    def get_man_hours_saved_today(self):
        """Calculate man hours saved today by AI"""
        tenders_today = self.get_today_tenders()
        hours_saved_per_tender = self.man_hours_per_tender - self.ai_hours_per_tender
        return int(tenders_today * hours_saved_per_tender)
    
    def get_cost_savings_today(self):
        """Calculate cost savings today (BDT 500 per hour average)"""
        hours_saved = self.get_man_hours_saved_today()
        hourly_rate = 500  # BDT per hour
        return hours_saved * hourly_rate
    
    def get_auto_fills_today(self):
        """Calculate auto-fills performed today"""
        tenders_today = self.get_today_tenders()
        # Average 15-25 fields per tender form
        fields_per_tender = random.randint(15, 25)
        return int(tenders_today * fields_per_tender * 0.85)  # 85% auto-filled
    
    def get_total_value_processed(self):
        """Calculate total tender value processed today"""
        tenders_today = self.get_today_tenders()
        return int(tenders_today * self.avg_tender_value)
    
    def get_win_rate_improvement(self):
        """Get win rate improvement percentage"""
        return 47  # 47% improvement
    
    def get_avg_confidence_score(self):
        """Get average AI confidence score"""
        return random.randint(86, 94)
    
    def get_all_stats(self):
        """Get all statistics as a dictionary"""
        return {
            'total_customers': self.get_total_customers(),
            'tenders_today': self.get_today_tenders(),
            'reports_today': self.get_today_reports(),
            'man_hours_saved_today': self.get_man_hours_saved_today(),
            'cost_savings_today': self.get_cost_savings_today(),
            'auto_fills_today': self.get_auto_fills_today(),
            'total_value_processed': self.get_total_value_processed(),
            'win_rate_improvement': self.get_win_rate_improvement(),
            'avg_confidence': self.get_avg_confidence_score()
        }
def render_hero_counters():
    """Render main hero counters with gradient cards and hover effects"""
    
    counters = LandingPageCounters()
    stats = counters.get_all_stats()
    
    # Format numbers
    tenders_formatted = f"{stats['tenders_today']:,}"
    hours_formatted = f"{stats['man_hours_saved_today']:,}"
    reports_formatted = f"{stats['reports_today']:,}"
    customers_formatted = f"{stats['total_customers']:,}"
    value_cr = stats['total_value_processed'] / 10000000  # Crore
    savings_m = stats['cost_savings_today'] / 1000000  # Million
    
    st.markdown("""
    <style>
        .hero-container {
            background: linear-gradient(135deg, #0c0e1a 0%, #1a1a3e 30%, #2d1b69 60%, #764ba2 100%);
            border-radius: 28px;
            padding: 3rem 2rem;
            margin: 2rem 0 3rem 0;
            color: white;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(118, 75, 162, 0.3);
        }
        .hero-container::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);
            animation: shimmer 15s ease-in-out infinite;
        }
        @keyframes shimmer {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(180deg); }
        }
        .hero-container .badge {
            display: inline-block;
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            padding: 0.4rem 1.5rem;
            border-radius: 30px;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            z-index: 1;
        }
        .hero-container .live-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            font-size: 0.7rem;
            padding: 0.25rem 1rem;
            border-radius: 20px;
            margin-left: 0.5rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.95); }
        }
        .hero-container .glow-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 1.5s infinite;
        }
        
        /* Counter Cards - Gradient backgrounds */
        .counter-card {
            border-radius: 20px;
            padding: 1.5rem 1rem;
            text-align: center;
            position: relative;
            z-index: 1;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            border: 1px solid rgba(255,255,255,0.08);
            overflow: hidden;
        }
        .counter-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0;
            transition: opacity 0.5s ease;
            border-radius: 20px;
        }
        .counter-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
        }
        .counter-card:hover::before {
            opacity: 1;
        }
        .counter-card .counter-value {
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
            position: relative;
            z-index: 1;
            background: linear-gradient(135deg, #fff 0%, #e0d7ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .counter-card .counter-label {
            font-size: 0.9rem;
            opacity: 0.9;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }
        .counter-card .counter-sub {
            font-size: 0.75rem;
            opacity: 0.6;
            position: relative;
            z-index: 1;
        }
        .counter-card .card-glow {
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            border-radius: 50%;
            opacity: 0;
            transition: opacity 0.6s ease;
            pointer-events: none;
        }
        .counter-card:hover .card-glow {
            opacity: 0.15;
        }
        
        /* Different gradient backgrounds for each card */
        .card-1 { 
            background: linear-gradient(135deg, rgba(33, 150, 243, 0.25), rgba(13, 71, 161, 0.35)); 
            border-color: rgba(33, 150, 243, 0.2);
        }
        .card-1 .card-glow { background: radial-gradient(circle, #2196F3 0%, transparent 70%); }
        .card-1:hover { border-color: rgba(33, 150, 243, 0.5); }
        .card-1:hover::before { background: radial-gradient(circle at center, rgba(33, 150, 243, 0.1), transparent 70%); }
        
        .card-2 { 
            background: linear-gradient(135deg, rgba(76, 175, 80, 0.25), rgba(27, 94, 32, 0.35)); 
            border-color: rgba(76, 175, 80, 0.2);
        }
        .card-2 .card-glow { background: radial-gradient(circle, #4CAF50 0%, transparent 70%); }
        .card-2:hover { border-color: rgba(76, 175, 80, 0.5); }
        .card-2:hover::before { background: radial-gradient(circle at center, rgba(76, 175, 80, 0.1), transparent 70%); }
        
        .card-3 { 
            background: linear-gradient(135deg, rgba(255, 152, 0, 0.25), rgba(230, 81, 0, 0.35)); 
            border-color: rgba(255, 152, 0, 0.2);
        }
        .card-3 .card-glow { background: radial-gradient(circle, #FF9800 0%, transparent 70%); }
        .card-3:hover { border-color: rgba(255, 152, 0, 0.5); }
        .card-3:hover::before { background: radial-gradient(circle at center, rgba(255, 152, 0, 0.1), transparent 70%); }
        
        .card-4 { 
            background: linear-gradient(135deg, rgba(156, 39, 176, 0.25), rgba(74, 20, 140, 0.35)); 
            border-color: rgba(156, 39, 176, 0.2);
        }
        .card-4 .card-glow { background: radial-gradient(circle, #9C27B0 0%, transparent 70%); }
        .card-4:hover { border-color: rgba(156, 39, 176, 0.5); }
        .card-4:hover::before { background: radial-gradient(circle at center, rgba(156, 39, 176, 0.1), transparent 70%); }
        
        /* Floating animation for each card */
        .card-1 { animation: floatCard 3.5s ease-in-out infinite; }
        .card-2 { animation: floatCard 3.5s ease-in-out infinite 0.5s; }
        .card-3 { animation: floatCard 3.5s ease-in-out infinite 1s; }
        .card-4 { animation: floatCard 3.5s ease-in-out infinite 1.5s; }
        
        @keyframes floatCard {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-6px); }
        }
        
        @media (max-width: 768px) {
            .hero-container {
                padding: 2rem 1rem;
            }
            .counter-card {
                padding: 1rem 0.5rem;
            }
            .counter-card .counter-value {
                font-size: 1.8rem;
            }
            .hero-container .badge {
                font-size: 0.7rem;
                padding: 0.3rem 1rem;
            }
            .counter-card .card-1 { animation: none; }
            .counter-card .card-2 { animation: none; }
            .counter-card .card-3 { animation: none; }
            .counter-card .card-4 { animation: none; }
        }
        @media (max-width: 576px) {
            .counter-card .counter-value { font-size: 1.4rem; }
            .counter-card .counter-label { font-size: 0.75rem; }
            .counter-card .counter-sub { font-size: 0.65rem; }
        }
    </style>
    
    <div class="hero-container">
        <div class="badge">
            <span class="glow-dot"></span> LIVE ACTIVITY • Bangladesh Construction Market
        </div>
    """, unsafe_allow_html=True)
    
    # Use columns for counters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="counter-card card-1">
            <div class="card-glow"></div>
            <div class="counter-value">{tenders_formatted}</div>
            <div class="counter-label">📋 Tenders Processed</div>
            <div class="counter-sub">Today • BDT {value_cr:.1f}Cr value</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="counter-card card-2">
            <div class="card-glow"></div>
            <div class="counter-value">{hours_formatted}</div>
            <div class="counter-label">⏱️ Man Hours Saved</div>
            <div class="counter-sub">Today • BDT {savings_m:.0f}M saved</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="counter-card card-3">
            <div class="card-glow"></div>
            <div class="counter-value">{reports_formatted}</div>
            <div class="counter-label">📊 Reports Generated</div>
            <div class="counter-sub">AI-powered analysis</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="counter-card card-4">
            <div class="card-glow"></div>
            <div class="counter-value">{customers_formatted}+</div>
            <div class="counter-label">🏢 Contractors Trust Us</div>
            <div class="counter-sub">+{counters.daily_customer_growth} new this week</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="margin-top: 1.5rem; position: relative; z-index: 1;">
            <span class="live-badge">● LIVE</span>
            <span style="font-size: 0.75rem; margin-left: 0.5rem; opacity: 0.7;">Real-time data • Updated daily</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
def render_hero_counters_bak():
    """Render main hero counters using Streamlit components"""
    
    counters = LandingPageCounters()
    stats = counters.get_all_stats()
    
    # Format numbers
    tenders_formatted = f"{stats['tenders_today']:,}"
    hours_formatted = f"{stats['man_hours_saved_today']:,}"
    reports_formatted = f"{stats['reports_today']:,}"
    customers_formatted = f"{stats['total_customers']:,}"
    value_cr = stats['total_value_processed'] / 10000000  # Crore
    savings_m = stats['cost_savings_today'] / 1000000  # Million
    
    # Main counters row
    st.markdown("""
    <style>
        .counter-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 28px;
            padding: 2rem;
            margin: 2rem 0;
            color: white;
            text-align: center;
        }
        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 0.3rem 1rem;
            border-radius: 30px;
            font-size: 0.8rem;
            margin-bottom: 1.5rem;
        }
        .live-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            font-size: 0.7rem;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            margin-left: 0.5rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        .counter-value {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        .counter-label {
            font-size: 0.85rem;
            opacity: 0.9;
        }
        .counter-sub {
            font-size: 0.7rem;
            opacity: 0.7;
        }
        @media (max-width: 768px) {
            .counter-value {
                font-size: 1.5rem;
            }
        }
    </style>
    
    <div class="counter-container">
        <div class="badge">
            ⚡ LIVE ACTIVITY • Bangladesh Construction Market
        </div>
    """, unsafe_allow_html=True)
    
    # Use columns for counters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="counter-value">{tenders_formatted}</div>
            <div class="counter-label">📋 Tenders Processed</div>
            <div class="counter-sub">Today • BDT {value_cr:.1f}Cr value</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="counter-value">{hours_formatted}</div>
            <div class="counter-label">⏱️ Man Hours Saved</div>
            <div class="counter-sub">Today • BDT {savings_m:.0f}M saved</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="counter-value">{reports_formatted}</div>
            <div class="counter-label">📊 Reports Generated</div>
            <div class="counter-sub">AI-powered analysis</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="counter-value">{customers_formatted}+</div>
            <div class="counter-label">🏢 Contractors Trust Us</div>
            <div class="counter-sub">+{counters.daily_customer_growth} new this week</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="margin-top: 1.5rem;">
            <span class="live-badge">● LIVE</span>
            <span style="font-size: 0.75rem; margin-left: 0.5rem;">Real-time data • Updated daily</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_secondary_metrics():
    """Render secondary metrics with Streamlit columns and uniform height"""
    
    counters = LandingPageCounters()
    stats = counters.get_all_stats()
    
    st.markdown("""
    <style>
        .metric-container {
            background: white;
            border-radius: 20px;
            padding: 1.2rem 0.8rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            transition: all 0.4s ease;
            border: 1px solid rgba(0,0,0,0.04);
            height: 100%;
            min-height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            border-bottom: 3px solid transparent;
        }
        .metric-container:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.08);
        }
        /* Color themes */
        .metric-container.m-1 { border-bottom-color: #2196F3; }
        .metric-container.m-1 .metric-value { color: #2196F3; }
        .metric-container.m-2 { border-bottom-color: #4CAF50; }
        .metric-container.m-2 .metric-value { color: #4CAF50; }
        .metric-container.m-3 { border-bottom-color: #FF9800; }
        .metric-container.m-3 .metric-value { color: #FF9800; }
        .metric-container.m-4 { border-bottom-color: #9C27B0; }
        .metric-container.m-4 .metric-value { color: #9C27B0; }
        .metric-container.m-5 { border-bottom-color: #00BCD4; }
        .metric-container.m-5 .metric-value { color: #00BCD4; }
        
        .metric-value {
            font-size: 1.6rem;
            font-weight: 800;
            line-height: 1.3;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #6c757d;
            font-weight: 500;
            margin-top: 0.1rem;
        }
        .metric-delta {
            font-size: 0.7rem;
            color: #10b981;
            font-weight: 600;
        }
        .metric-help {
            font-size: 0.55rem;
            color: #adb5bd;
            margin-top: 0.2rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-container m-1">
            <div class="metric-value">{stats['auto_fills_today']:,}</div>
            <div class="metric-label">🤖 Auto-Fills Today</div>
            <div class="metric-help">Form fields auto-filled by AI</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-container m-2">
            <div class="metric-value">BDT {stats['cost_savings_today']/1000000:.1f}M</div>
            <div class="metric-label">💰 Daily Savings</div>
            <div class="metric-help">Estimated cost savings from AI</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-container m-3">
            <div class="metric-value">+{stats['win_rate_improvement']}%</div>
            <div class="metric-label">📈 Win Rate <span class="metric-delta">• vs manual</span></div>
            <div class="metric-help">Average win rate improvement</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-container m-4">
            <div class="metric-value">{stats['avg_confidence']}%</div>
            <div class="metric-label">🎯 AI Confidence</div>
            <div class="metric-help">Average AI prediction confidence</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-container m-5">
            <div class="metric-value">+{counters.daily_customer_growth}/day</div>
            <div class="metric-label">⚡ New Contractors</div>
            <div class="metric-help">New companies joining daily</div>
        </div>
        """, unsafe_allow_html=True)


def render_yearly_projection():
    """Render yearly projection metrics"""
    
    counters = LandingPageCounters()
    
    # Calculate yearly projections
    avg_daily_tenders = counters.get_today_tenders()
    avg_daily_hours = counters.get_man_hours_saved_today()
    avg_daily_savings = counters.get_cost_savings_today()
    
    projected_yearly_tenders = avg_daily_tenders * 365
    projected_yearly_hours = avg_daily_hours * 365
    projected_yearly_savings = avg_daily_savings * 365
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                border-radius: 20px; padding: 1.5rem; margin: 1.5rem 0; text-align: center; color: white;">
        <h3 style="margin-bottom: 1rem; font-size: 1.2rem;">📊 Year-End Projections</h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
            <div>
                <div style="font-size: 1.3rem; font-weight: bold;">{projected_yearly_tenders:,}</div>
                <div style="font-size: 0.7rem; opacity: 0.8;">Tenders Processed</div>
            </div>
            <div>
                <div style="font-size: 1.3rem; font-weight: bold;">{projected_yearly_hours:,}</div>
                <div style="font-size: 0.7rem; opacity: 0.8;">Man Hours Saved</div>
            </div>
            <div>
                <div style="font-size: 1.3rem; font-weight: bold;">BDT {projected_yearly_savings/10000000:.0f}Cr</div>
                <div style="font-size: 0.7rem; opacity: 0.8;">Total Savings</div>
            </div>
        </div>
        <div style="margin-top: 0.75rem; font-size: 0.65rem; opacity: 0.7;">
            Based on current growth trajectory
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_all_counters():
    """Render all counter sections together"""
    
    render_hero_counters()
    render_secondary_metrics()
    render_yearly_projection()


# For testing
if __name__ == "__main__":
    render_all_counters()