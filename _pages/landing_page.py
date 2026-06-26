# _pages/landing_page.py

import streamlit as st
from version import get_app_name, get_app_desc

def show_landing_page():
    """Unified landing page with English and Bangla content"""
    
    st.set_page_config(page_title="TenderAI (BD) - AI Tender Intelligence Platform", page_icon="🏗️", layout="wide")
    
    # Custom CSS
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
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.2rem !important;
        color: #cbd5e1;
        margin-bottom: 1rem;
    }
    .hero-bangla {
        font-size: 1.5rem !important;
        color: #93c5fd;
        margin-bottom: 1rem;
        font-weight: 600;
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
        transition: transform 0.3s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .feature-icon {
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem;
    }
    .feature-title {
        font-size: 1.1rem !important;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #1e3a8a;
    }
    .feature-desc {
        font-size: 0.85rem !important;
        color: #666;
    }
    
    /* Problem Section */
    .problem-section {
        background: #fef2f2;
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem 0;
        border: 1px solid #fecaca;
    }
    .solution-section {
        background: #f0fdf4;
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem 0;
        border: 1px solid #bbf7d0;
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
        transition: transform 0.3s;
    }
    .pricing-card:hover {
        transform: translateY(-5px);
    }
    .pricing-card.popular {
        border: 2px solid #3b82f6;
        position: relative;
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
        height: 100%;
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
    
    /* ROI Calculator */
    .roi-calculator {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem 0;
        color: white;
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
    
    h1, h2, h3 {
        font-size: 1.8rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ==================== HERO SECTION ====================
    st.markdown(f"""
    <div class="hero-section">
        <div class="badge">🚀 AI-Powered • Bangladesh's First • PPR 2025 Compliant</div>
        <div class="hero-title">🏗️ TenderAI (BD)</div>
        <div class="hero-subtitle">AI Powered Tender Intelligence & Bid Optimization Platform</div>
        <div class="hero-bangla">বাংলাদেশের প্রথম AI-চালিত Tender Intelligence Platform</div>
        <div class="hero-subtitle">টেন্ডার বিশ্লেষণে পুরো দিন নয়, এখন লাগবে মাত্র কয়েক সেকেন্ড</div>
    </div>
    """, unsafe_allow_html=True)
    
    # CTA Buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🎥 ডেমো দেখুন", use_container_width=True, type="primary"):
                st.info("Demo video coming soon!")
        with col_b:
            if st.button("📞 ফ্রি কনসালটেশন বুক করুন", use_container_width=True):
                st.info("Call us: +880 1234 567890")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== WHAT TenderAI (BD) DOES ====================
    st.markdown("""
    <div style="background: #f8fafc; padding: 2rem; border-radius: 20px; margin-bottom: 2rem;">
        <p style="font-size: 1.1rem; text-align: center; margin-bottom: 1rem;">
            <strong>TenderAI (BD)</strong> এমন একটি অত্যাধুনিক AI প্ল্যাটফর্ম যা টেন্ডার ডকুমেন্ট, BOQ এবং বাজার পরিস্থিতি বিশ্লেষণ করে 
            আপনাকে সবচেয়ে প্রতিযোগিতামূলক এবং লাভজনক বিডিং সিদ্ধান্ত নিতে সাহায্য করে।
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem;">
            <div>✅ টেন্ডার বিশ্লেষণের সময় 95% পর্যন্ত কমান</div>
            <div>✅ বিড প্রস্তুতির খরচ কমান</div>
            <div>✅ আরও বেশি টেন্ডারে অংশগ্রহণ করুন</div>
            <div>✅ তথ্যভিত্তিক বিডিং সিদ্ধান্ত নিন</div>
            <div>✅ টেন্ডার জয়ের সম্ভাবনা বৃদ্ধি করুন</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== PROBLEM VS SOLUTION ====================
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="problem-section">
            <h3 style="color: #dc2626; text-align: center;">❌ এখনও কি আপনার টিম ঘণ্টার পর ঘণ্টা BOQ বিশ্লেষণ করে?</h3>
            <div style="margin-top: 1rem;">
                <p>একটি বড় টেন্ডার বিশ্লেষণ করতে সাধারণত:</p>
                <ul>
                    <li>৩-৫ জন কর্মী</li>
                    <li>৪-৮ ঘণ্টা সময়</li>
                    <li>অসংখ্য Excel Sheet</li>
                    <li>শত শত BOQ Item</li>
                    <li>অসংখ্য Manual Calculation</li>
                </ul>
                <p><strong>তারপরও সঠিক বিড মূল্য নির্ধারণ করা কঠিন।</strong></p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="solution-section">
            <h3 style="color: #16a34a; text-align: center;">✨ TenderAI (BD) কী করে?</h3>
            <div style="margin-top: 1rem;">
                <p><strong>এক ক্লিকে:</strong></p>
                <ul>
                    <li>📋 টেন্ডার বিশ্লেষণ</li>
                    <li>📊 BOQ বিশ্লেষণ</li>
                    <li>🎯 Bid Optimization</li>
                    <li>👥 Competitor Simulation</li>
                    <li>⚠️ Risk Assessment</li>
                    <li>💰 Cost Analysis</li>
                    <li>📄 Executive Summary</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== KEY FEATURES ====================
    
    # Feature 1: AI Tender Analysis Engine
    st.markdown("<h2>🤖 AI Tender Analysis Engine</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">কয়েক সেকেন্ডে সম্পূর্ণ টেন্ডার বিশ্লেষণ</div>
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                <li>Eligibility Criteria Analysis</li>
                <li>Tender Requirement Extraction</li>
                <li>Mandatory Document Detection</li>
                <li>Risk Identification</li>
                <li>Technical Evaluation Summary</li>
                <li>Financial Requirement Summary</li>
                <li><strong>Bid / No-Bid Recommendation</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">AI Tender Analysis System Features</div>
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                <li>📄 Automatic Document Parsing</li>
                <li>📊 Key Information Extraction</li>
                <li>⚠️ Risk & Compliance Check</li>
                <li>💡 Smart Recommendations</li>
                <li>📈 Market Comparison</li>
            </ul>
            <p style="margin-top: 0.5rem; font-size: 0.8rem; color: #666;"><strong>SEO:</strong> AI Tender Analysis Software Bangladesh, Tender Analysis System, eGP Tender Analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Feature 2: Smart Bid Optimization Engine
    st.markdown("<h2>🎯 Smart Bid Optimization Engine</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 1rem;'>কত টাকায় বিড করলে জয়ের সম্ভাবনা বেশি?</p>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">⚔️</div>
            <div class="feature-title">Aggressive Bid Strategy</div>
            <div class="feature-desc">সর্বোচ্চ প্রতিযোগিতামূলক বিড</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">⚖️</div>
            <div class="feature-title">Moderate Bid Strategy</div>
            <div class="feature-desc">ঝুঁকি ও লাভের ভারসাম্যপূর্ণ বিড</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🛡️</div>
            <div class="feature-title">Conservative Bid Strategy</div>
            <div class="feature-desc">নিরাপদ ও উচ্চ লাভের বিড</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Weighted Average Recommendation</div>
            <div class="feature-desc">AI-ভিত্তিক সুপারিশকৃত বিড মূল্য</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">👥</div>
            <div class="feature-title">Competitor Simulation</div>
            <div class="feature-desc">বিভিন্ন সংখ্যক প্রতিযোগী ধরে সম্ভাব্য ফলাফল বিশ্লেষণ</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Bid Optimization Results</div>
            <div class="feature-desc">Three-Tier Analysis: Basic, Advanced (PPR 2025), Enhanced (ML)</div>
            <p style="margin-top: 0.5rem; font-size: 0.7rem; color: #666;"><strong>SEO:</strong> Bid Optimization Software, Tender Bid Calculator, Tender Pricing Software Bangladesh</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Feature 3: BOQ Intelligence Platform
    st.markdown("<h2>📊 BOQ Intelligence Platform</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 1rem;'>হাজার হাজার BOQ Item বিশ্লেষণ করুন মুহূর্তেই</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                <li>📄 BOQ Upload (Excel/PDF)</li>
                <li>🤖 Automated Item Analysis</li>
                <li>✅ Quantity Verification</li>
                <li>💰 Rate Comparison</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                <li>📊 Cost Breakdown</li>
                <li>📈 Margin Analysis</li>
                <li>⚠️ Abnormal Item Detection</li>
            </ul>
            <p style="margin-top: 0.5rem; font-size: 0.7rem; color: #666;"><strong>SEO:</strong> BOQ Analysis Software Bangladesh, Construction Cost Analysis Software, Quantity Surveying Software</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Feature 4: Tender Management System
    st.markdown("<h2>📋 Tender Management System</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 1rem;'>সব টেন্ডার এক প্ল্যাটফর্মে</p>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("📌", "Tender Tracking"),
        ("⏰", "Submission Reminder"),
        ("🔄", "Workflow Management"),
        ("👥", "Team Collaboration"),
        ("✅", "Approval Process"),
        ("📁", "Document Repository"),
        ("📊", "Audit Trail")
    ]
    
    for idx, (icon, label) in enumerate(features):
        col = [col1, col2, col3, col4][idx % 4]
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<p style="text-align: center; font-size: 0.8rem; color: #666;"><strong>SEO:</strong> Tender Management Software Bangladesh, eGP Management System, Procurement Software Bangladesh</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Feature 5: Executive Dashboard
    st.markdown("<h2>📊 Executive Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 1rem;'>ব্যবসায়িক সিদ্ধান্ত এখন হবে তথ্যভিত্তিক</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    dashboard_features = [
        ("🏆", "Win Rate Analysis"),
        ("📈", "Tender Performance Analytics"),
        ("💰", "Revenue Forecasting"),
        ("📋", "Project Pipeline Tracking"),
        ("⚠️", "Risk Dashboard"),
        ("💡", "Profitability Insights")
    ]
    
    for idx, (icon, label) in enumerate(dashboard_features):
        col = [col1, col2, col3][idx % 3]
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== WHO IS USING ====================
    st.markdown("<h2>👥 কারা ব্যবহার করছেন?</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    users = [
        "🏗️ Construction Companies",
        "📋 Contractors",
        "📦 Suppliers",
        "🔧 Engineering Firms",
        "🏭 EPC Contractors",
        "📊 Government Project Consultants",
        "🏗️ Infrastructure Developers",
        "📋 Procurement Teams"
    ]
    
    for idx, user in enumerate(users):
        col = [col1, col2, col3, col4][idx % 4]
        with col:
            st.markdown(f"""
            <div style="background: #f8fafc; padding: 0.75rem; border-radius: 10px; text-align: center; margin-bottom: 0.5rem;">
                {user}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== ROI CALCULATOR ====================
    st.markdown("""
    <div class="roi-calculator">
        <h3 style="color: white; text-align: center;">💰 ROI Calculator</h3>
        <p style="text-align: center; margin-bottom: 1rem;">আপনার প্রতিষ্ঠান বছরে কত সাশ্রয় করতে পারে?</p>
        <div style="background: #1e293b; padding: 1rem; border-radius: 10px;">
            <p style="text-align: center;">যদি: ৪ জন কর্মী • প্রতিদিন ৪ ঘণ্টা • মাসে ২০টি টেন্ডার</p>
            <p style="text-align: center; margin-top: 0.5rem;">তাহলে বছরে শত শত মানব-ঘণ্টা সাশ্রয় সম্ভব।</p>
            <p style="text-align: center; font-weight: bold; margin-top: 0.5rem;">TenderAI (BD) আপনার টিমকে কম সময়ে আরও বেশি টেন্ডার বিশ্লেষণের সুযোগ দেয়।</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== PRICING SECTION ====================
    st.markdown("<h2>💰 Simple, Transparent Pricing</h2>", unsafe_allow_html=True)
    
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
            <div align="left">✅ 7-day history</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Free", key="plan_free", use_container_width=True):
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
            <div align="left">✅ Export reports</div>
            <div align="left">✅ Priority support</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Basic", key="plan_basic", use_container_width=True):
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
            <div align="left">✅ Priority support</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Professional", key="plan_pro", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col4:
        st.markdown("""
        <div class="pricing-card">
            <div class="feature-icon">🏢</div>
            <div class="feature-title">Enterprise</div>
            <div class="pricing-price">৳49,999<span style="font-size:0.7rem;">/mo</span></div>
            <hr>
            <div align="left">✅ Everything in Professional</div>
            <div align="left">✅ Custom AI model</div>
            <div align="left">✅ Dedicated support</div>
            <div align="left">✅ SLA guarantee</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Enterprise", key="plan_enterprise", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # ==================== TESTIMONIALS ====================
    st.markdown("<h2>💬 What Our Users Say</h2>", unsafe_allow_html=True)
    
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
    st.markdown("<h2>❓ Frequently Asked Questions</h2>", unsafe_allow_html=True)
    
    faqs = [
        ("TenderAI (BD) কি e-GP এর বিকল্প?", "না। TenderAI (BD) হলো একটি Tender Intelligence Platform যা e-GP ব্যবহারকারীদের টেন্ডার বিশ্লেষণ ও বিডিং সিদ্ধান্ত গ্রহণে সহায়তা করে।"),
        ("কত দ্রুত টেন্ডার বিশ্লেষণ করা যায়?", "সাধারণত কয়েক সেকেন্ডের মধ্যে।"),
        ("এটি কি BOQ বিশ্লেষণ করতে পারে?", "হ্যাঁ। হাজার হাজার BOQ Item স্বয়ংক্রিয়ভাবে বিশ্লেষণ করতে পারে।"),
        ("এটি কি বিড মূল্য সুপারিশ করে?", "হ্যাঁ। Aggressive, Moderate, Conservative এবং Weighted Average Bid Recommendation প্রদান করে।")
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
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 2rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;">
        <h2 style="color: white;">Ready to Win More Tenders?</h2>
        <p style="color: #cbd5e1; margin-bottom: 1rem;">আপনার টেন্ডার বিশ্লেষণকে নিয়ে যান AI-এর পরবর্তী পর্যায়ে</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem; max-width: 800px; margin: 0 auto 1rem auto;">
            <div style="color: white;">✔ দ্রুত বিশ্লেষণ</div>
            <div style="color: white;">✔ কম খরচ</div>
            <div style="color: white;">✔ উন্নত সিদ্ধান্ত</div>
            <div style="color: white;">✔ অধিক দক্ষতা</div>
            <div style="color: white;">✔ জয়ের সম্ভাবনা বৃদ্ধি</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("আজই ডেমো বুক করুন", use_container_width=True, type="primary"):
            st.info("Please call us at +880 1234 567890 or email sales@itenderbd.com")
        st.caption("📞 যোগাযোগ করুন: +880 1234 567890 | 📧 sales@itenderbd.com | 🌐 www.itenderbd.com")
    
    # Trust Badges
    st.markdown("---")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    badges = ["✓ PPR 2025", "✓ e-GP Ready", "✓ SSL Secure", "✓ 24/7 Support", "✓ Bangladesh Made", "✓ AI Powered"]
    for idx, badge in enumerate(badges):
        with [col1, col2, col3, col4, col5, col6][idx]:
            st.markdown(f"<div class='trust-badge'>{badge}</div>", unsafe_allow_html=True)