# _pages/landing_page.py

import streamlit as st
from version import get_app_name, get_app_desc

def show_landing_page():
    """Unified landing page with English and Bangla content"""
    
    st.set_page_config(page_title="TenderAI (BD) - AI Tender Intelligence Platform", page_icon="🏗️", layout="wide")
    
    # Custom CSS - Supabase-inspired with Bangladesh flag colors
    st.markdown("""
    <style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Reset global font size */
    .main .stMarkdown, .main div, .main p, .main span, .main label {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        color: #1a1a1a;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Supabase-inspired Hero Section */
    .hero-section {
        background: linear-gradient(135deg, #006a4e 0%, #00875a 40%, #e2132e 100%);
        padding: 4rem 2rem 3rem;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 3rem;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
        transform: rotate(15deg);
        pointer-events: none;
    }
    .hero-section::after {
        content: '';
        position: absolute;
        bottom: -50%;
        left: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 70%);
        transform: rotate(-15deg);
        pointer-events: none;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        color: white;
        padding: 0.35rem 1.2rem;
        border-radius: 50px;
        font-size: 0.75rem !important;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
        position: relative;
        z-index: 1;
    }
    .hero-title {
        font-size: 3.5rem !important;
        font-weight: 900;
        color: white;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
        position: relative;
        z-index: 1;
    }
    .hero-title span {
        background: linear-gradient(135deg, #ffffff 30%, #ffd700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-subtitle {
        font-size: 1.25rem !important;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.75rem;
        font-weight: 400;
        position: relative;
        z-index: 1;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    .hero-bangla {
        font-size: 1.4rem !important;
        color: rgba(255,255,255,0.85);
        margin-bottom: 0.5rem;
        font-weight: 600;
        position: relative;
        z-index: 1;
        font-family: 'Noto Sans Bengali', 'Inter', sans-serif !important;
    }
    .hero-cta {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
        position: relative;
        z-index: 1;
        margin-top: 1.5rem;
    }
    .btn-primary {
        background: white;
        color: #006a4e;
        padding: 0.8rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.95rem !important;
    }
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    .btn-secondary {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        color: white;
        padding: 0.8rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.2);
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.95rem !important;
    }
    .btn-secondary:hover {
        background: rgba(255,255,255,0.2);
        transform: translateY(-2px);
    }
    
    /* Section titles - Supabase style */
    .section-title {
        font-size: 2.2rem !important;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
        color: #1a1a1a;
    }
    .section-subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem !important;
        margin-bottom: 2.5rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Feature Cards - Supabase style */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    .feature-card {
        background: white;
        padding: 1.75rem;
        border-radius: 16px;
        border: 1px solid #eaeaea;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .feature-card:hover {
        transform: translateY(-4px);
        border-color: #006a4e;
        box-shadow: 0 12px 40px rgba(0,106,78,0.08);
    }
    .feature-card .icon {
        font-size: 2rem !important;
        margin-bottom: 0.75rem;
        display: block;
    }
    .feature-card .title {
        font-size: 1.1rem !important;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    .feature-card .desc {
        font-size: 0.9rem !important;
        color: #666;
        line-height: 1.6;
    }
    .feature-card .tag {
        display: inline-block;
        background: #f0fdf4;
        color: #006a4e;
        font-size: 0.7rem !important;
        font-weight: 600;
        padding: 0.2rem 0.75rem;
        border-radius: 50px;
        margin-top: 0.75rem;
    }
    
    /* Problem/Solution - Bangladesh flag colors */
    .problem-section {
        background: #fef2f2;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #fecaca;
        height: 100%;
    }
    .problem-section h3 {
        color: #e2132e !important;
    }
    .solution-section {
        background: #f0fdf4;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #bbf7d0;
        height: 100%;
    }
    .solution-section h3 {
        color: #006a4e !important;
    }
    
    /* Stats - Clean modern */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin: 2rem 0;
    }
    .stat-item {
        text-align: center;
        padding: 1.5rem;
        background: white;
        border-radius: 16px;
        border: 1px solid #eaeaea;
    }
    .stat-number {
        font-size: 2.5rem !important;
        font-weight: 800;
        color: #006a4e;
        display: block;
    }
    .stat-label {
        font-size: 0.85rem !important;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* Pricing - Supabase inspired */
    .pricing-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin: 2rem 0;
    }
    .pricing-card {
        background: white;
        padding: 2rem 1.5rem;
        border-radius: 16px;
        border: 1px solid #eaeaea;
        text-align: center;
        transition: all 0.25s ease;
        position: relative;
    }
    .pricing-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.06);
    }
    .pricing-card.popular {
        border: 2px solid #006a4e;
        box-shadow: 0 8px 30px rgba(0,106,78,0.12);
    }
    .pricing-card.popular .popular-badge {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: #006a4e;
        color: white;
        padding: 0.2rem 1.2rem;
        border-radius: 50px;
        font-size: 0.7rem !important;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .pricing-card .plan-name {
        font-size: 1rem !important;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.25rem;
    }
    .pricing-card .price {
        font-size: 2.5rem !important;
        font-weight: 800;
        color: #006a4e;
        margin: 0.5rem 0;
    }
    .pricing-card .price span {
        font-size: 1rem !important;
        font-weight: 400;
        color: #666;
    }
    .pricing-card .features {
        text-align: left;
        margin: 1.5rem 0;
        padding: 0;
        list-style: none;
    }
    .pricing-card .features li {
        padding: 0.4rem 0;
        font-size: 0.9rem !important;
        color: #444;
        border-bottom: 1px solid #f5f5f5;
    }
    .pricing-card .features li:last-child {
        border-bottom: none;
    }
    .pricing-card .features li::before {
        content: '✓ ';
        color: #006a4e;
        font-weight: 700;
    }
    
    /* Testimonials */
    .testimonial-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        margin: 2rem 0;
    }
    .testimonial-card {
        background: white;
        padding: 1.75rem;
        border-radius: 16px;
        border: 1px solid #eaeaea;
        transition: all 0.25s ease;
    }
    .testimonial-card:hover {
        border-color: #006a4e;
    }
    .testimonial-card .stars {
        color: #ffd700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .testimonial-card .quote {
        font-style: italic;
        color: #333;
        font-size: 0.95rem !important;
        margin: 0.5rem 0;
    }
    .testimonial-card .author {
        font-weight: 700;
        color: #1a1a1a;
        margin-top: 0.5rem;
    }
    .testimonial-card .role {
        font-size: 0.8rem !important;
        color: #888;
    }
    
    /* FAQ */
    .faq-grid {
        max-width: 700px;
        margin: 0 auto;
    }
    .faq-item {
        background: white;
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #eaeaea;
        margin-bottom: 0.75rem;
        transition: all 0.2s ease;
    }
    .faq-item:hover {
        border-color: #006a4e;
    }
    .faq-question {
        font-weight: 700;
        color: #1a1a1a;
        font-size: 1rem !important;
        margin-bottom: 0.25rem;
    }
    .faq-answer {
        color: #666;
        font-size: 0.9rem !important;
        padding-left: 0;
        border-left: none;
    }
    
    /* CTA Banner */
    .cta-banner {
        background: linear-gradient(135deg, #006a4e 0%, #00875a 50%, #e2132e 100%);
        padding: 3rem 2rem;
        border-radius: 24px;
        text-align: center;
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
    }
    .cta-banner h2 {
        color: white;
        font-size: 2rem !important;
        font-weight: 800;
        position: relative;
        z-index: 1;
    }
    .cta-banner p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem !important;
        margin-bottom: 1.5rem;
        position: relative;
        z-index: 1;
    }
    .cta-banner .btn-white {
        background: white;
        color: #006a4e;
        padding: 0.8rem 2.5rem;
        border-radius: 12px;
        font-weight: 700;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 1rem !important;
        position: relative;
        z-index: 1;
    }
    .cta-banner .btn-white:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    }
    
    /* Trust badges */
    .trust-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .trust-badge {
        text-align: center;
        font-size: 0.75rem !important;
        color: #888;
        font-weight: 500;
        padding: 0.5rem;
        background: #f8f9fa;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .trust-badge:hover {
        background: #f0fdf4;
        color: #006a4e;
    }
    
    /* Dividers */
    .divider {
        margin: 3rem 0;
        height: 1px;
        background: linear-gradient(to right, transparent, #eaeaea, transparent);
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .hero-title { font-size: 2.2rem !important; }
        .stats-grid { grid-template-columns: repeat(2, 1fr); }
        .pricing-grid { grid-template-columns: 1fr; }
        .testimonial-grid { grid-template-columns: 1fr; }
        .trust-grid { grid-template-columns: repeat(3, 1fr); }
        .feature-grid { grid-template-columns: 1fr; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ==================== HERO SECTION ====================
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-badge">🚀 AI-Powered • Bangladesh's First • PPR 2025 Compliant</div>
        <div class="hero-title">🏗️ <span>TenderAI</span> (BD)</div>
        <div class="hero-subtitle">AI Powered Tender Intelligence & Bid Optimization Platform</div>
        <div class="hero-bangla">বাংলাদেশের প্রথম AI-চালিত Tender Intelligence Platform</div>
        <div class="hero-subtitle" style="font-size: 1rem !important; opacity: 0.8;">টেন্ডার বিশ্লেষণে পুরো দিন নয়, এখন লাগবে মাত্র কয়েক সেকেন্ড</div>
        <div class="hero-cta">
            <button class="btn-primary">🎥 ডেমো দেখুন</button>
            <button class="btn-secondary">📞 ফ্রি কনসালটেশন বুক করুন</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== STATS ====================
    st.markdown("""
    <div class="stats-grid">
        <div class="stat-item">
            <span class="stat-number">95%</span>
            <span class="stat-label">Time Saved</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">10K+</span>
            <span class="stat-label">Tenders Analyzed</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">35%</span>
            <span class="stat-label">Win Rate Increase</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">24/7</span>
            <span class="stat-label">AI Support</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== WHAT WE DO ====================
    st.markdown("""
    <h2 class="section-title">What is TenderAI (BD)?</h2>
    <p class="section-subtitle">An advanced AI platform that analyzes tender documents, BOQ, and market conditions to help you make competitive and profitable bidding decisions.</p>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="problem-section">
            <h3 style="color: #e2132e;">❌ The Old Way</h3>
            <ul style="margin-top: 1rem; padding-left: 1.2rem;">
                <li>3-5 team members</li>
                <li>4-8 hours per tender</li>
                <li>Endless Excel sheets</li>
                <li>Hundreds of BOQ items</li>
                <li>Manual calculations</li>
                <li><strong>Still uncertain pricing</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="solution-section">
            <h3 style="color: #006a4e;">✨ The TenderAI Way</h3>
            <ul style="margin-top: 1rem; padding-left: 1.2rem;">
                <li>📋 One-click tender analysis</li>
                <li>📊 Automated BOQ analysis</li>
                <li>🎯 AI-powered bid optimization</li>
                <li>👥 Competitor simulation</li>
                <li>⚠️ Real-time risk assessment</li>
                <li>💰 Data-driven pricing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== FEATURES ====================
    st.markdown("<h2 class='section-title'>Powerful Features</h2>", unsafe_allow_html=True)
    st.markdown("<p class='section-subtitle'>Everything you need to win more tenders with confidence</p>", unsafe_allow_html=True)
    
    features = [
        ("⚡", "AI Tender Analysis", "Analyze complete tenders in seconds with automatic requirement extraction, risk identification, and smart recommendations.", "PPR 2025"),
        ("🎯", "Smart Bid Optimization", "Get aggressive, moderate, conservative, and weighted average bid recommendations to maximize win probability.", "AI-Powered"),
        ("📊", "BOQ Intelligence", "Process thousands of BOQ items instantly with automated quantity verification, rate comparison, and cost analysis.", "Excel/PDF"),
        ("👥", "Competitor Simulation", "Simulate different competitor scenarios and understand how your bid performs under various market conditions.", "Strategic"),
        ("📋", "Tender Management", "Track all tenders in one platform with submission reminders, workflow management, and team collaboration.", "Organization"),
        ("📈", "Executive Dashboard", "Get data-driven insights with win rate analysis, revenue forecasting, risk dashboard, and profitability metrics.", "Analytics"),
    ]
    
    # Display features in 3-column grid
    for i in range(0, len(features), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(features):
                icon, title, desc, tag = features[i + j]
                with cols[j]:
                    st.markdown(f"""
                    <div class="feature-card">
                        <span class="icon">{icon}</span>
                        <div class="title">{title}</div>
                        <div class="desc">{desc}</div>
                        <span class="tag">{tag}</span>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== USERS ====================
    st.markdown("<h2 class='section-title'>Who's Using TenderAI?</h2>", unsafe_allow_html=True)
    st.markdown("<p class='section-subtitle'>Trusted by leading organizations across Bangladesh</p>", unsafe_allow_html=True)
    
    users = [
        "🏗️ Construction Companies", "📋 Contractors", "📦 Suppliers",
        "🔧 Engineering Firms", "🏭 EPC Contractors", "📊 Government Consultants",
        "🏗️ Infrastructure Developers", "📋 Procurement Teams"
    ]
    
    cols = st.columns(4)
    for idx, user in enumerate(users):
        with cols[idx % 4]:
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 12px; text-align: center; margin-bottom: 0.5rem; border: 1px solid #eaeaea; transition: all 0.2s;">
                <span style="font-weight: 500; font-size: 0.9rem;">{user}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== PRICING ====================
    st.markdown("<h2 class='section-title'>Simple, Transparent Pricing</h2>", unsafe_allow_html=True)
    st.markdown("<p class='section-subtitle'>Choose the plan that fits your needs</p>", unsafe_allow_html=True)
    
    pricing = [
        {"name": "Free", "price": "0", "period": "/mo", "features": ["5 analyses/mo", "Basic reports", "Email support", "7-day history"], "popular": False},
        {"name": "Basic", "price": "4,999", "period": "/mo", "features": ["30 analyses/mo", "AI predictions", "Export reports", "Priority support"], "popular": False},
        {"name": "Professional", "price": "14,999", "period": "/mo", "features": ["Unlimited analyses", "ML predictions", "Team collaboration", "Priority support"], "popular": True},
        {"name": "Enterprise", "price": "49,999", "period": "/mo", "features": ["Everything in Pro", "Custom AI model", "Dedicated support", "SLA guarantee"], "popular": False},
    ]
    
    cols = st.columns(4)
    for idx, plan in enumerate(pricing):
        with cols[idx]:
            popular_class = "popular" if plan["popular"] else ""
            popular_badge = '<div class="popular-badge">🔥 Most Popular</div>' if plan["popular"] else ""
            features_html = "".join([f"<li>{f}</li>" for f in plan["features"]])
            st.markdown(f"""
            <div class="pricing-card {popular_class}">
                {popular_badge}
                <div class="plan-name">{plan['name']}</div>
                <div class="price">৳{plan['price']}<span>{plan['period']}</span></div>
                <ul class="features">{features_html}</ul>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Choose {plan['name']}", key=f"plan_{plan['name'].lower()}", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== TESTIMONIALS ====================
    st.markdown("<h2 class='section-title'>What Our Users Say</h2>", unsafe_allow_html=True)
    st.markdown("<p class='section-subtitle'>Real feedback from real customers</p>", unsafe_allow_html=True)
    
    testimonials = [
        ("⭐⭐⭐⭐⭐", '"TenderAI helped us increase our win rate by 35% in just 3 months!"', "Md. Rahman", "CEO, ABC Construction"),
        ("⭐⭐⭐⭐⭐", '"The AI predictions are remarkably accurate. Saved us from many bad bids."', "Ms. Khan", "Procurement Manager"),
        ("⭐⭐⭐⭐⭐", '"PPR 2025 compliance checker is a lifesaver. Highly recommended!"', "Eng. Islam", "Project Director"),
    ]
    
    cols = st.columns(3)
    for idx, (stars, quote, author, role) in enumerate(testimonials):
        with cols[idx]:
            st.markdown(f"""
            <div class="testimonial-card">
                <div class="stars">{stars}</div>
                <div class="quote">{quote}</div>
                <div class="author">{author}</div>
                <div class="role">{role}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== FAQ ====================
    st.markdown("<h2 class='section-title'>Frequently Asked Questions</h2>", unsafe_allow_html=True)
    
    faqs = [
        ("TenderAI (BD) কি e-GP এর বিকল্প?", "না। TenderAI (BD) হলো একটি Tender Intelligence Platform যা e-GP ব্যবহারকারীদের টেন্ডার বিশ্লেষণ ও বিডিং সিদ্ধান্ত গ্রহণে সহায়তা করে।"),
        ("কত দ্রুত টেন্ডার বিশ্লেষণ করা যায়?", "সাধারণত কয়েক সেকেন্ডের মধ্যে সম্পূর্ণ বিশ্লেষণ সম্পন্ন হয়।"),
        ("এটি কি BOQ বিশ্লেষণ করতে পারে?", "হ্যাঁ। হাজার হাজার BOQ Item স্বয়ংক্রিয়ভাবে বিশ্লেষণ করতে পারে।"),
        ("এটি কি বিড মূল্য সুপারিশ করে?", "হ্যাঁ। Aggressive, Moderate, Conservative এবং Weighted Average Bid Recommendation প্রদান করে।"),
    ]
    
    st.markdown('<div class="faq-grid">', unsafe_allow_html=True)
    for question, answer in faqs:
        st.markdown(f"""
        <div class="faq-item">
            <div class="faq-question">{question}</div>
            <div class="faq-answer">{answer}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== FINAL CTA ====================
    st.markdown("""
    <div class="cta-banner">
        <h2>Ready to Win More Tenders?</h2>
        <p>আপনার টেন্ডার বিশ্লেষণকে নিয়ে যান AI-এর পরবর্তী পর্যায়ে</p>
        <button class="btn-white">আজই ডেমো বুক করুন →</button>
        <div style="display: flex; justify-content: center; gap: 1.5rem; margin-top: 1.5rem; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.85); font-size: 0.85rem;">✔ দ্রুত বিশ্লেষণ</span>
            <span style="color: rgba(255,255,255,0.85); font-size: 0.85rem;">✔ কম খরচ</span>
            <span style="color: rgba(255,255,255,0.85); font-size: 0.85rem;">✔ উন্নত সিদ্ধান্ত</span>
            <span style="color: rgba(255,255,255,0.85); font-size: 0.85rem;">✔ জয়ের সম্ভাবনা বৃদ্ধি</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact info
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption("📞 +880 1234 567890 | 📧 sales@itenderbd.com | 🌐 www.itenderbd.com")
    
    # Trust Badges
    st.markdown("""
    <div class="trust-grid">
        <div class="trust-badge">✓ PPR 2025</div>
        <div class="trust-badge">✓ e-GP Ready</div>
        <div class="trust-badge">✓ SSL Secure</div>
        <div class="trust-badge">✓ 24/7 Support</div>
        <div class="trust-badge">✓ Bangladesh Made</div>
        <div class="trust-badge">✓ AI Powered</div>
    </div>
    """, unsafe_allow_html=True)