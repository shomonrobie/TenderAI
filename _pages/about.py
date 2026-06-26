import streamlit as st

from utils.helpers import debug_print

def show_about_page():
    """About us page - Comprehensive company information"""
    debug_print("ℹ️ Rendering about page")
    
    # Add animation CSS
    st.markdown("""
    <style>
        
         /* Reset global font size for landing page only */
        .main .stMarkdown, .main div, .main p, .main span, .main label {
            font-size: 1rem !important;
            line-height: 1.5 !important;
        }
                
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .fade-up {
            animation: fadeInUp 0.8s ease-out;
        }
        
        .slide-left {
            animation: slideInLeft 0.6s ease-out;
        }
        
        .slide-right {
            animation: slideInRight 0.6s ease-out;
        }
        
        .tech-card {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .tech-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .stat-card {
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .bio-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 1.5rem;
            border-radius: 16px;
            margin: 1rem 0;
            transition: transform 0.3s ease;
        }
        
        .bio-card:hover {
            transform: translateX(5px);
        }
    </style>
    """, unsafe_allow_html=True)
    
    
    # =========================================================================
    # COMPANY OVERVIEW (with animation)
    # =========================================================================
    st.markdown("""
    <div class="fade-up" style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); 
                padding: 2rem; border-radius: 16px; margin-bottom: 2rem;">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🏢 Who We Are</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            TenderAI is Bangladesh's first AI-powered tender management platform, 
            created by <strong>Shomon Robie</strong>, an entrepreneur, digital innovator, 
            and Managing Director of <strong>Babui Limited</strong>. With extensive 
            experience in digital marketing, IT, and algorithmic trading through 
            his successful venture <strong>LakshmiFX</strong>, Shomon brings cutting-edge 
            AI and machine learning expertise to the construction procurement space. 
            TenderAI represents the culmination of years of experience in developing 
            high-precision prediction systems, now applied to help Bangladeshi 
            construction companies win more tenders.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # MISSION & VISION (Animated columns)
    # =========================================================================
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="slide-left" style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: 100%;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎯</div>
            <h3 style="color: #1e3a8a; margin-bottom: 1rem;">Our Mission</h3>
            <p style="line-height: 1.6;">
                To democratize access to advanced AI-driven insights for 
                construction companies in Bangladesh, enabling smarter bidding 
                decisions, reducing financial risk, and increasing win rates 
                in public procurement tenders. We're committed to making 
                cutting-edge technology accessible, affordable, and impactful 
                for businesses of all sizes.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="slide-right" style="background: white; padding: 1.5rem; border-radius: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: 100%;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">👁️</div>
            <h3 style="color: #1e3a8a; margin-bottom: 1rem;">Our Vision</h3>
            <p style="line-height: 1.6;">
                To become the undisputed leader in AI-powered tender management 
                across South Asia, transforming how infrastructure projects are 
                planned, bid, and delivered. We envision a future where data-driven 
                decision-making is the standard, not the exception, in public 
                procurement.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # =========================================================================
    # CORE VALUES (Animated)
    # =========================================================================
    st.markdown("### 🌟 Our Core Values")
    
    values_cols = st.columns(4)
    values = [
        ("🔬", "Innovation", "Continuously pushing the boundaries of AI in procurement"),
        ("🤝", "Integrity", "Transparent, ethical, and PPR 2025 compliant solutions"),
        ("🎯", "Excellence", "Delivering 85%+ accurate predictions consistently"),
        ("🌱", "Growth", "Empowering Bangladeshi businesses to thrive"),
    ]
    
    for idx, (icon, title, desc) in enumerate(values):
        with values_cols[idx]:
            st.markdown(f"""
            <div class="fade-up" style="text-align: center; padding: 1rem; transition: transform 0.3s;">
                <div style="font-size: 2rem;">{icon}</div>
                <h4 style="color: #1e3a8a; margin: 0.5rem 0;">{title}</h4>
                <p style="font-size: 0.85rem; color: #666;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # IMPACT METRICS (Animated)
    # =========================================================================
    st.markdown("### 📊 Our Impact")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("🏆", "Win Rate Increase", "+23%", "Average improvement for our users"),
        ("💰", "Savings per Tender", "৳2.4L", "Average cost savings"),
        ("⏱️", "Time Saved", "4.2 hours", "Per analysis on average"),
        ("🏢", "Companies Served", "150+", "Across Bangladesh"),
    ]
    
    for idx, (icon, label, value, caption) in enumerate(metrics):
        with [col1, col2, col3, col4][idx]:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 1rem; border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 2rem;">{icon}</div>
                <div style="font-size: 1.8rem; font-weight: bold;">{value}</div>
                <div style="font-size: 0.85rem; margin: 0.25rem 0;">{label}</div>
                <div style="font-size: 0.7rem; opacity: 0.8;">{caption}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # FOUNDER BIO SECTION (Updated with accurate information)
    # =========================================================================
    st.markdown("### 👨‍💼 About the Founder")
    
    st.markdown("""
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Who is Shomon Robie?</h3>
        <p><strong>Entrepreneur & Digital Founder:</strong> Shomon Robie is the Founder & CEO of <strong>VisitBangladesh.com.bd</strong>, 
        a travel-oriented website focused on promoting tourism and experiences in Bangladesh. With a background in digital 
        marketing and IT spanning many years, Shomon built the travel platform to showcase Bangladesh's rich culture and 
        diverse destinations.</p>
    </div>
    
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Business & Professional Roles</h3>
        <p><strong>Managing Director of Babui:</strong> Records from the Bangladesh Computer Samity list Shomon Robie as the 
        Managing Director of <strong>Babui Limited</strong>, a Dhaka-based company involved in business services and technology activities.</p>
        <p style="margin-top: 0.5rem;"><strong>Babui's Activities:</strong> Under his leadership as Director/CEO, Babui Limited engages in 
        corporate management, information services, and web/computer-related business activities, serving clients across Bangladesh.</p>
    </div>
    
    <div class="bio-card fade-up">
        <h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔹 Technical Contributions</h3>
        <p><strong>Developer of LakshmiFX:</strong> Shomon Robie is credited as the developer of <strong>LakshmiFX</strong>, 
        a MetaTrader 5 automated trading tool (Expert Advisor) used for forex and other financial markets. 
        The detailed manual for LakshmiFX credits him as the developer and outlines the tool's advanced features 
        and trading purposes.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    
    # =========================================================================
    # TECHNOLOGY STACK (Fixed - using st.html for better rendering)
    # =========================================================================
    st.markdown("### 🛠️ Technology Stack")
    # Add CSS to ensure equal height columns
    # Add CSS to ensure equal height columns and consistent styling
    st.markdown("""
    <style>
        /* Reset global font size for about page as like as landing page */
        .main .stMarkdown, .main div, .main p, .main span, .main label {
            font-size: 1rem !important;
            line-height: 1.5 !important;
        }
        
        /* Equal height columns */
        .stColumn {
            display: flex;
        }
        
        .tech-card-full {
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 12px;
            width: 100%;
            min-height: 550px;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .tech-card-full:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .tech-card-full h4 {
            margin-top: 0;
            margin-bottom: 0.75rem;
            color: #1e3a8a;
            font-size: 1.1rem !important;
            font-weight: 600;
        }
        
        /* Consistent styling for both ul and p */
        .tech-card-full ul, 
        .tech-card-full p,
        .tech-card-full li {
            font-size: 0.9rem !important;
            line-height: 1.5 !important;
            color: #475569;
            margin-bottom: 0.75rem;
        }
        
        .tech-card-full ul {
            padding-left: 1.2rem;
            margin: 0 0 1rem 0;
        }
        
        .tech-card-full li {
            margin-bottom: 0.5rem;
        }
        
        .tech-card-full p {
            margin: 0 0 1rem 0;
        }
        
        .tech-card-full ul:last-child,
        .tech-card-full p:last-child {
            margin-bottom: 0;
        }
    </style>
    """, unsafe_allow_html=True)


    col1, col2 = st.columns(2)

    with col1:
        # Use st.html for cleaner HTML rendering (Streamlit 1.36+)
        st.html("""
        <div class="tech-card fade-up" style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; height: 100%;">
            <h4>🤖 Artificial Intelligence & Machine Learning</h4>
            <ul>
                <li>Scikit-learn for statistical modeling</li>
                <li>XGBoost for gradient boosting</li>
                <li>Custom ensemble models for bid prediction</li>
                <li>Time series analysis for market trends</li>
            </ul>
            
            <h4>⚙️ Backend & Infrastructure</h4>
            <ul>
                <li>Python 3.12 with FastAPI</li>
                <li>PostgreSQL for data persistence</li>
                <li>Docker for containerization</li>
                <li>AWS/GCP ready deployment</li>
            </ul>
            
            <h4>🎨 Frontend & Visualization</h4>
            <ul>
                <li>Streamlit for interactive UI</li>
                <li>Plotly for dynamic charts</li>
                <li>ReportLab for PDF generation</li>
                <li>Custom CSS for professional styling</li>
            </ul>
        </div>
        """)

    with col2:
        st.html("""
        <div class="tech-card fade-up" style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; height: 100%;">
            <h4>✅ PPR 2025 Compliant</h4>
            <ul>
                <li>Our algorithms are built specifically for Bangladesh's Public Procurement Rules 2025, ensuring full compliance with government regulations.</li>
            </ul>    
            
            <h4>✅ 85% Prediction Accuracy</h4>
            <ul>
                <li>Trained on thousands of historical tenders, our AI models achieve industry-leading accuracy in bid success predictions.</li>
            </ul>
            
            <h4>✅ Real-time Market Intelligence</h4>
            <ul>
                <li>Stay ahead with live competitor tracking, market trends, and intelligent bid recommendations.</li>
            </ul>
            
            <h4>✅ Enterprise-Grade Security</h4>
            <ul>
                <li>Your data is protected with encryption, secure authentication, and regular security audits.</li>
            </ul>
            
            <h4>✅ Dedicated Support</h4>
            <ul>
                <li>24/7 technical support, training, and consultation to ensure your success.</li>
            </ul>
        </div>
        """)


    
    # =========================================================================
    # TESTIMONIALS
    # =========================================================================
    st.markdown("### 💬 What Our Users Say")
    
    testimonial_cols = st.columns(2)
    
    testimonials = [
        ("⭐⭐⭐⭐⭐", "TenderAI has transformed our bidding process. We've seen a 30% increase in our win rate within just 3 months!", "— Md. Karim, ABC Construction"),
        ("⭐⭐⭐⭐⭐", "The AI recommendations are incredibly accurate. Saved us hours of manual analysis and helped us win 5 major contracts.", "— Shahnaz Begum, BuildTech Ltd."),
    ]
    
    for idx, (rating, text, author) in enumerate(testimonials):
        with testimonial_cols[idx]:
            st.markdown(f"""
            <div class="fade-up" style="background: #f0fdf4; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">{rating}</div>
                <p style="font-style: italic; line-height: 1.5;">"{text}"</p>
                <p style="font-weight: bold; margin-top: 0.5rem;">{author}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # CALL TO ACTION
    # =========================================================================
    st.markdown("""
    <div class="fade-up" style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                padding: 2rem; border-radius: 16px; text-align: center; color: white;">
        <h3 style="color: white; margin-bottom: 1rem;">Ready to Transform Your Bidding Strategy?</h3>
        <p style="margin-bottom: 1.5rem;">Join hundreds of construction companies already using TenderAI</p>
        <div style="display: flex; gap: 1rem; justify-content: center;">
            <a href="#" onclick="parent.postMessage({type: 'streamlit:setPageValue', value: 'register'}, '*')" 
               style="background: #22c55e; color: white; text-decoration: none; padding: 0.75rem 2rem; 
                      border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: bold; display: inline-block;">
                Start Free Trial
            </a>
            <a href="#" onclick="parent.postMessage({type: 'streamlit:setPageValue', value: 'contact'}, '*')" 
               style="background: transparent; color: white; text-decoration: none; border: 1px solid white; 
                      padding: 0.75rem 2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; display: inline-block;">
                Contact Sales
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    from modules.footer import render_footer
    render_footer()
    debug_print("✅ About page render complete")