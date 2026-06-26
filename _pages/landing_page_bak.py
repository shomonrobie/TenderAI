import streamlit as st
from version import get_app_name, get_app_desc

def show_landing_page():
    """Professional landing page with consistent layout"""
    
    st.set_page_config(page_title="TenderAI - AI Bid Optimization", page_icon="🏗️", layout="wide")
    
       
    # Custom CSS - Override global styles
    st.markdown("""
    <style>
    /* Reset global font size for landing page only */
    .main .stMarkdown, .main div, .main p, .main span, .main label {
        font-size: 1rem !important;
        line-height: 1.5 !important;
    }
    
    /* Hero Section */
    .hero-section {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .hero-title {
        font-size: 3rem !important;
        font-weight: 800;
        color: white;
        margin-bottom: 1rem;
    }
    .hero-subtitle {
        font-size: 1.2rem !important;
        color: #cbd5e1;
        margin-bottom: 2rem;
    }
    .badge {
        display: inline-block;
        background: rgba(59,130,246,0.3);
        color: #93c5fd;
        padding: 0.25rem 1rem;
        border-radius: 50px;
        font-size: 0.8rem !important;
        margin-bottom: 1rem;
    }
    
    /* Feature Cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 1rem;
    }
    .feature-icon {
        font-size: 2rem !important;
        margin-bottom: 0.5rem;
    }
    .feature-title {
        font-size: 1.1rem !important;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        font-size: 0.85rem !important;
        color: #666;
    }
    
    /* Report Cards */
    .report-card {
        background: #1e293b;
        border-radius: 15px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        color: white;
        min-height: 320px;        
    }
    .report-card h4 {
        color: #60a5fa;
        margin-bottom: 0.75rem;
        font-size: 1.1rem !important;
    }
    .report-card p, .report-card li {
        color: #cbd5e1;
        font-size: 0.85rem !important;
    }
    
    /* Stats Section */
    .stats-section {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem 0;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem !important;
        font-weight: 800;
        color: #1e3a8a;
    }
    
    /* Pricing Cards */
    .pricing-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        position: relative;
    }
    .pricing-card.popular {
        border: 2px solid #3b82f6;
    }
    .popular-badge {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: #3b82f6;
        color: white;
        padding: 0.2rem 1rem;
        border-radius: 50px;
        font-size: 0.7rem !important;
        font-weight: 600;
        white-space: nowrap;
    }
    .pricing-price {
        font-size: 1.8rem !important;
        font-weight: 800;
        color: #1e3a8a;
        margin: 0.5rem 0;
    }
    
    /* Testimonial Cards */
    .testimonial-card {
        background: white;
        padding: 1.2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .testimonial-card p {
        font-size: 0.85rem !important;
    }
    
    /* FAQ Section */
    .faq-item {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
    }
    .faq-question {
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
        font-size: 1rem !important;
    }
    .faq-answer {
        color: #475569;
        font-size: 0.9rem !important;
        padding-left: 1rem;
        border-left: 3px solid #3b82f6;
    }
    
    .divider {
        margin: 2rem 0;
        height: 1px;
        background: #e2e8f0;
    }
    
    .trust-badge {
        text-align: center;
        font-size: 0.7rem !important;
        color: #666;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-size: 1.8rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ==================== HERO SECTION ====================
    st.markdown(f"""
    <div class="hero-section">
        <div class="badge">🚀 PPR 2025 Compliant • Bangladesh Made</div>
        <div class="hero-title">🏗️ {get_app_name()}</div>
        <div class="hero-subtitle">
            {get_app_desc()}<br>
            Win More Tenders with 85% Accurate Predictions
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # CTA Buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🚀 Start Free Trial", use_container_width=True, type="primary"):
                st.session_state.page = "register"
                st.rerun()
        with col_b:
            if st.button("📊 View Live Demo", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== SEE TENDERAI IN ACTION ====================
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>📊 See TenderAI in Action</h2>", unsafe_allow_html=True)
    
    # Row 1: AI Recommendation + Three-Tier Analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="report-card">
            <h4>🎯 AI Recommendation</h4>
            <p>Based on <strong>3 competitor bids</strong> and <strong>PPR 2025 compliance metrics</strong>, the optimal bid is <strong>BDT 2,745,260</strong> (93.9% of estimate). This bid maintains a <strong>68% win probability</strong> while staying safely above the SLT threshold.</p>
            <hr style="border-color: #334155;">
            <h4>📈 Key Insights</h4>
            <ul>
                <li>Market Position: 6.1% competitive score</li>
                <li>Compliance Margin: +1.8% from SLT threshold</li>
                <li>Expected ROI: 10.4% on investment</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="report-card">
            <h4>🎯 Three-Tier Analysis Comparison</h4>
            <p>Compare Basic, Advanced (PPR 2025), and Enhanced (ML) analysis to find the optimal bidding strategy.</p>
            <hr style="border-color: #334155;">        
            <table style="width:100%; border-collapse: collapse; margin-top: 0.5rem;">
                <tr style="border-bottom: 1px solid #334155;">
                    <th style="text-align: left; padding: 5px;">Tier</th>
                    <th style="text-align: left; padding: 5px;">Optimal Bid</th>
                    <th style="text-align: left; padding: 5px;">Win Prob</th>
                </tr>
                <tr style="background: #334155;">
                    <td style="padding: 5px;"><strong>Advanced (PPR)</strong></td>
                    <td style="padding: 5px;"><strong>BDT 2,745,260</strong></td>
                    <td style="padding: 5px;"><strong>68%</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px;">Enhanced (ML)</td>
                    <td style="padding: 5px;">BDT 2,749,500</td>
                    <td style="padding: 5px;">75%</td>
                </tr>
                <tr>
                    <td style="padding: 5px;">Basic</td>
                    <td style="padding: 5px;">BDT 2,603,250</td>
                    <td style="padding: 5px;">65%</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
    
    # Row 2: Financial Projections + Competitor Intelligence
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="report-card">
            <h4>💰 Financial Projections</h4>
            <p>Financial analysis showing expected costs, profits, and returns on investment based on bid optimization.</p>
            <hr style="border-color: #334155;">
            <p><strong>Estimated Cost:</strong> BDT 2,486,250 (85% of estimate)<br>
            <strong>Expected Profit:</strong> BDT 259,010<br>
            <strong>Expected Value:</strong> BDT 174,832<br>
            <strong>Win Probability:</strong> 68%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="report-card">
            <h4>📊 Competitor Intelligence</h4>
            <p>Track competitor bidding patterns and analyze their strategies to gain competitive advantage.</p>
            <hr style="border-color: #334155;">
            <table style="width:100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 0.5rem;">
                <tr style="border-bottom: 1px solid #334155;">
                    <th>Competitor</th>
                    <th>Bid Amount</th>
                    <th>% of Estimate</th>
                </tr>
                <tr><td>Competitor 1</td><td>BDT 2,698,712</td><td>92.3%</td></tr>
                <tr><td>Competitor 2</td><td>BDT 2,749,863</td><td>94.0%</td></tr>
                <tr><td>Competitor 3</td><td>BDT 2,909,282</td><td>99.5%</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== WHY CHOOSE TENDERAI ====================
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>✨ Why Choose TenderAI?</h2>", unsafe_allow_html=True)
    
    # Row 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI Bid Predictions</div>
            <div class="feature-desc">85% accurate winning bid predictions using advanced machine learning</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">PPR 2025 Compliance</div>
            <div class="feature-desc">Fully compliant with Bangladesh Public Procurement Rules 2025</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Competitor Intelligence</div>
            <div class="feature-desc">Real-time competitor tracking and historical analysis</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Row 2
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <div class="feature-title">Three-Tier Analysis</div>
            <div class="feature-desc">Basic, Advanced (PPR), and Enhanced (ML) analysis options</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">👥</div>
            <div class="feature-title">Team Collaboration</div>
            <div class="feature-desc">Role-based access control for your entire organization</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔒</div>
            <div class="feature-title">Enterprise Security</div>
            <div class="feature-desc">Bank-grade encryption and secure data handling</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== STATS SECTION ====================
    st.markdown("""
    <div class="stats-section">
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
            <div><div class="stat-number">150+</div><div>Companies</div></div>
            <div><div class="stat-number">23%</div><div>Win Rate Increase</div></div>
            <div><div class="stat-number">4.2hrs</div><div>Time Saved</div></div>
            <div><div class="stat-number">85%</div><div>Accuracy</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== PRICING SECTION ====================
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>💰 Simple, Transparent Pricing</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <div class="feature-icon">🆓</div>
            <div class="feature-title">Free</div>
            <div class="pricing-price">৳0<span style="font-size:0.7rem;">/mo</span></div>
            <hr>
            <div align="left">✅ 5 analyses/mo</div>
            <div align="left">✅ Basic reports</div>
            <div align="left">✅ Email support</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Free", key="plan_Free", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="pricing-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Basic</div>
            <div class="pricing-price">৳4,999<span style="font-size:0.7rem;">/mo</span></div>
            <hr>
            <div align="left">✅ 30 analyses/mo</div>
            <div align="left">✅ AI predictions</div>
            <div align="left">✅ Priority support</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Basic", key="plan_Basic", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="pricing-card popular">
            <div class="popular-badge">🔥 Most Popular</div>
            <div class="feature-icon">🚀</div>
            <div class="feature-title">Professional</div>
            <div class="pricing-price">৳14,999<span style="font-size:0.7rem;">/mo</span></div>
            <hr>
            <div align="left">✅ Unlimited analyses</div>
            <div align="left">✅ ML predictions</div>
            <div align="left">✅ Team collaboration</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Professional", key="plan_Professional", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col4:
        st.markdown("""
        <div class="pricing-card">
            <div class="feature-icon">🏢</div>
            <div class="feature-title">Enterprise</div>
            <div class="pricing-price">৳49,999<span style="font-size:0.7rem;">/mo</span></div>
            <hr>
            <div align="left">✅ Everything + API</div>
            <div align="left">✅ Custom AI model</div>
            <div align="left">✅ Dedicated support</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Enterprise", key="plan_Enterprise", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== TESTIMONIALS ====================
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>💬 What Our Users Say</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="testimonial-card">
            <div style="font-size: 1.2rem;">⭐⭐⭐⭐⭐</div>
            <p style="margin: 0.5rem 0; font-style: italic;">"TenderAI helped us increase our win rate by 35% in just 3 months!"</p>
            <strong>Md. Rahman</strong><br>
            <span style="font-size: 0.75rem; color: #666;">CEO, ABC Construction</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="testimonial-card">
            <div style="font-size: 1.2rem;">⭐⭐⭐⭐⭐</div>
            <p style="margin: 0.5rem 0; font-style: italic;">"The AI predictions are remarkably accurate. Saved us from many bad bids."</p>
            <strong>Ms. Khan</strong><br>
            <span style="font-size: 0.75rem; color: #666;">Procurement Manager</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="testimonial-card">
            <div style="font-size: 1.2rem;">⭐⭐⭐⭐⭐</div>
            <p style="margin: 0.5rem 0; font-style: italic;">"PPR 2025 compliance checker is a lifesaver. Highly recommended!"</p>
            <strong>Eng. Islam</strong><br>
            <span style="font-size: 0.75rem; color: #666;">Project Director</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== FAQ SECTION ====================
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>❓ Frequently Asked Questions</h2>", unsafe_allow_html=True)
    
    faqs = [
        ("Is TenderAI compliant with PPR 2025?", "Yes! TenderAI is fully compliant with Bangladesh Public Procurement Rules 2025 and e-GP standards."),
        ("How accurate are the AI predictions?", "Our ML models achieve 85% accuracy in predicting winning bid ranges based on historical data."),
        ("Can I try before buying?", "Absolutely! Start with a 14-day free trial, no credit card required."),
        ("Is my data secure?", "Yes, we use bank-grade encryption and never share your data with third parties.")
    ]
    
    for question, answer in faqs:
        st.markdown(f"""
        <div class="faq-item">
            <div class="faq-question">❓ {question}</div>
            <div class="faq-answer">{answer}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== FINAL CTA ====================
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>Ready to Transform Your Bidding Strategy?</h3>", unsafe_allow_html=True)
        if st.button("Start Your 14-Day Free Trial", use_container_width=True, type="primary"):
            st.session_state.page = "register"
            st.rerun()
        st.caption("No credit card required • Cancel anytime • 14-day free trial")
    
    # Trust Badges
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    badges = ["✓ PPR 2025", "✓ e-GP Ready", "✓ SSL Secure", "✓ 24/7 Support", "✓ Bangladesh Made"]
    for idx, badge in enumerate(badges):
        with [col1, col2, col3, col4, col5][idx]:
            st.markdown(f"<div class='trust-badge'>{badge}</div>", unsafe_allow_html=True)