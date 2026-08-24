# _pages/extension_features.py

import streamlit as st

def show():
    """Dedicated page for Chrome Extension Features"""
    print("✅ Extension Features page loaded")
    
    st.markdown("### 🚀 TenderAI Chrome Extension")
    st.markdown("Auto-fill tender forms in seconds...")

    st.markdown("""
    <style>
        .feature-hero {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 3rem 2rem;
            text-align: center;
            margin-bottom: 2rem;
            color: white;
        }
        .feature-hero h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        .feature-hero p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        .feature-section {
            margin: 3rem 0;
        }
        .feature-section h2 {
            font-size: 1.8rem;
            color: #1e3c72;
            margin-bottom: 1.5rem;
            border-left: 4px solid #667eea;
            padding-left: 1rem;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        .feature-card-large {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s;
        }
        .feature-card-large:hover {
            transform: translateY(-5px);
        }
        .feature-icon-large {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        .feature-title-large {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1e3c72;
            margin-bottom: 0.75rem;
        }
        .feature-desc-large {
            color: #666;
            line-height: 1.5;
        }
        .feature-list {
            list-style: none;
            padding: 0;
        }
        .feature-list li {
            padding: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
        }
        .feature-list li:before {
            content: "✅";
            position: absolute;
            left: 0;
            color: #4CAF50;
        }
        .comparison-table {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 2rem 0;
        }
        .comparison-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            border-bottom: 1px solid #eee;
        }
        .comparison-header {
            background: #667eea;
            color: white;
            font-weight: 600;
            padding: 1rem;
            text-align: center;
        }
        .comparison-cell {
            padding: 1rem;
            text-align: center;
        }
        .comparison-cell strong {
            color: #1e3c72;
        }
        .check-mark {
            color: #4CAF50;
            font-size: 1.2rem;
            font-weight: bold;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        .stat-card-large {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            text-align: center;
            padding: 1.5rem;
            border-radius: 16px;
        }
        .stat-number-large {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }
        .compatibility-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
            margin: 2rem 0;
        }
        .compatibility-badge {
            background: #e3f2fd;
            color: #1976d2;
            padding: 0.5rem 1.2rem;
            border-radius: 30px;
            font-weight: 500;
        }
        .cta-section {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 20px;
            padding: 3rem 2rem;
            text-align: center;
            margin: 3rem 0;
            color: white;
        }
        .cta-button-large {
            background: white;
            color: #667eea;
            border: none;
            padding: 1rem 2rem;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 1rem;
            transition: transform 0.2s;
        }
        .cta-button-large:hover {
            transform: scale(1.02);
        }
        .benefit-badge {
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 500;
            margin-left: 0.5rem;
        }
        @media (max-width: 768px) {
            .comparison-row {
                grid-template-columns: 1fr;
            }
            .comparison-header {
                background: #1e3c72;
            }
            .feature-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== HERO SECTION ==========
    st.markdown("""
    <div class="feature-hero">
        <h1>🤖 TenderAI Chrome Extension</h1>
        <p>The Ultimate Auto-Fill Tool for Tender Submissions</p>
        <p style="font-size: 1rem; margin-top: 1rem;">⚡ Fill tender forms in seconds • 🎯 95% accuracy • 🔒 Never auto-submits</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== QUICK STATS ==========
    st.markdown("""
    <div class="stats-grid">
        <div class="stat-card-large">
            <div class="stat-number-large">95%</div>
            <div>Time Saved</div>
            <small style="color: #666;">on data entry</small>
        </div>
        <div class="stat-card-large">
            <div class="stat-number-large">10,000+</div>
            <div>Forms Auto-Filled</div>
            <small style="color: #666;">by our users</small>
        </div>
        <div class="stat-card-large">
            <div class="stat-number-large">40%</div>
            <div>Higher Win Rate</div>
            <small style="color: #666;">on submitted tenders</small>
        </div>
        <div class="stat-card-large">
            <div class="stat-number-large">50+</div>
            <div>Field Types</div>
            <small style="color: #666;">automatically detected</small>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== KEY FEATURES SECTION ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>🌟 Key Features</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card-large">
            <div class="feature-icon-large">🧠</div>
            <div class="feature-title-large">AI-Powered Field Detection</div>
            <div class="feature-desc-large">Our AI understands context, not just keywords. Works with misspelled labels, Bangla text, and dynamic form fields.</div>
            <span class="benefit-badge">Smart</span>
        </div>
        <div class="feature-card-large">
            <div class="feature-icon-large">⚡</div>
            <div class="feature-title-large">One-Click Auto-Fill</div>
            <div class="feature-desc-large">Fill entire tender forms in under 10 seconds. No more copy-pasting from Excel or PDFs.</div>
            <span class="benefit-badge">Fast</span>
        </div>
        <div class="feature-card-large">
            <div class="feature-icon-large">🎯</div>
            <div class="feature-title-large">Confidence Scoring System</div>
            <div class="feature-desc-large">High confidence (90%+) auto-fills automatically. Medium confidence shows suggestions. Low confidence highlights for review.</div>
            <span class="benefit-badge">Accurate</span>
        </div>
        <div class="feature-card-large">
            <div class="feature-icon-large">🔒</div>
            <div class="feature-title-large">Never Auto-Submits</div>
            <div class="feature-desc-large">We only fill forms — you stay in control. Review every field before final submission.</div>
            <span class="benefit-badge">Secure</span>
        </div>
        <div class="feature-card-large">
            <div class="feature-icon-large">👥</div>
            <div class="feature-title-large">Team Sync</div>
            <div class="feature-desc-large">Company data is shared across your entire team. One source of truth for all users.</div>
            <span class="benefit-badge">Collaborative</span>
        </div>
        <div class="feature-card-large">
            <div class="feature-icon-large">📊</div>
            <div class="feature-title-large">Usage Analytics</div>
            <div class="feature-desc-large">Track how many forms you've filled, time saved, and confidence scores. Optimize your workflow.</div>
            <span class="benefit-badge">Insightful</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== WHAT CAN BE AUTO-FILLED ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>📋 What Can Be Auto-Filled</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">🏢</div>
            <div class="feature-title-large">Company Information</div>
            <ul class="feature-list">
                <li>Company / Firm Name</li>
                <li>Trade License Number</li>
                <li>TIN Number (13 digits)</li>
                <li>BIN Number (e-GP)</li>
                <li>VAT Registration Number</li>
                <li>RJSC Registration Number</li>
                <li>Company Address (full)</li>
                <li>Division, District, Upazila</li>
                <li>Post Code</li>
                <li>Phone & Email</li>
                <li>Website</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">👥</div>
            <div class="feature-title-large">Personnel & Key Staff</div>
            <ul class="feature-list">
                <li>Full Name</li>
                <li>Designation / Position</li>
                <li>NID Number</li>
                <li>Phone Number</li>
                <li>Email Address</li>
                <li>Educational Qualification</li>
                <li>Years of Experience</li>
                <li>Professional Certifications</li>
                <li>Key Personnel Status</li>
                <li>CV Attachments</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">🏗️</div>
            <div class="feature-title-large">Equipment & Machinery</div>
            <ul class="feature-list">
                <li>Equipment Name</li>
                <li>Equipment Type</li>
                <li>Model & Capacity</li>
                <li>Ownership Status</li>
                <li>Current Location</li>
                <li>Operational Status</li>
                <li>Quantity Available</li>
                <li>Registration Numbers</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">📋</div>
            <div class="feature-title-large">Experience & Projects</div>
            <ul class="feature-list">
                <li>Project Name</li>
                <li>Client Name</li>
                <li>Contract Value</li>
                <li>Contract Date</li>
                <li>Completion Date</li>
                <li>Nature of Work</li>
                <li>Scope of Work</li>
                <li>Completion Certificate Details</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">💰</div>
            <div class="feature-title-large">Financial Information</div>
            <ul class="feature-list">
                <li>Annual Turnover</li>
                <li>Construction Turnover</li>
                <li>Net Worth</li>
                <li>Working Capital</li>
                <li>Liquid Assets</li>
                <li>Credit Limit</li>
                <li>Bank Guarantee Limit</li>
                <li>Audited Financial Status</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card-large" style="height: 100%;">
            <div class="feature-icon-large">📜</div>
            <div class="feature-title-large">Licenses & Certificates</div>
            <ul class="feature-list">
                <li>Trade License</li>
                <li>Contractor License</li>
                <li>ISO Certificates</li>
                <li>Environment Clearance</li>
                <li>Fire License</li>
                <li>Import/Export License</li>
                <li>Issue & Expiry Dates</li>
                <li>Issuing Authorities</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== COMPARISON TABLE ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>📊 Before vs After</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="comparison-table">
        <div class="comparison-row">
            <div class="comparison-header">Task</div>
            <div class="comparison-header">Without TenderAI</div>
            <div class="comparison-header">With TenderAI ⚡</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Company Information</strong></div>
            <div class="comparison-cell">5-10 minutes per form</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> 5 seconds</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>TIN / VAT / BIN Numbers</strong></div>
            <div class="comparison-cell">Look up from documents</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> Auto-populated</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Key Personnel Details</strong></div>
            <div class="comparison-cell">Copy from CVs</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> Instant fill</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Equipment Schedule</strong></div>
            <div class="comparison-cell">Manual entry of 20+ items</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> Bulk auto-fill</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Experience Records</strong></div>
            <div class="comparison-cell">Type project details each time</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> Select from library</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Financial Data</strong></div>
            <div class="comparison-cell">Refer to audit reports</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> Auto-filled from records</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Error Rate</strong></div>
            <div class="comparison-cell">~15% typos/mistakes</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> ~2% verified data</div>
        </div>
        <div class="comparison-row">
            <div class="comparison-cell"><strong>Total Time per Tender</strong></div>
            <div class="comparison-cell">30-45 minutes</div>
            <div class="comparison-cell"><span class="check-mark">✅</span> 3-5 minutes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== HOW IT WORKS ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>🔄 How It Works</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="text-align: center;">
            <div style="background: #667eea; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; color: white; font-weight: bold; font-size: 1.5rem;">1</div>
            <strong>Install</strong>
            <p style="color: #666; font-size: 0.85rem;">Download from your company dashboard</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center;">
            <div style="background: #667eea; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; color: white; font-weight: bold; font-size: 1.5rem;">2</div>
            <strong>Login</strong>
            <p style="color: #666; font-size: 0.85rem;">Sign in with your TenderAI account</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center;">
            <div style="background: #667eea; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; color: white; font-weight: bold; font-size: 1.5rem;">3</div>
            <strong>Open Form</strong>
            <p style="color: #666; font-size: 0.85rem;">Navigate to any tender application page</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="text-align: center;">
            <div style="background: #667eea; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; color: white; font-weight: bold; font-size: 1.5rem;">4</div>
            <strong>Auto-Fill</strong>
            <p style="color: #666; font-size: 0.85rem;">Watch fields fill automatically</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== COMPATIBILITY ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>🌍 Compatible Platforms</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="compatibility-grid">
        <span class="compatibility-badge">✅ e-GP Bangladesh (eptenders.gov.bd)</span>
        <span class="compatibility-badge">✅ CPTU Portal (cptu.gov.bd)</span>
        <span class="compatibility-badge">✅ LGED Tenders</span>
        <span class="compatibility-badge">✅ PWD Schedule</span>
        <span class="compatibility-badge">✅ DPP Portal</span>
        <span class="compatibility-badge">✅ Any Custom Tender Portal</span>
        <span class="compatibility-badge">✅ HTML Forms</span>
        <span class="compatibility-badge">✅ Dynamic/JavaScript Forms</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== BROWSER SUPPORT ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>🖥️ Browser Support</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem;">🌐</div>
            <strong>Chrome</strong>
            <p style="color: #666;">✅ Full Support</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem;">🟦</div>
            <strong>Microsoft Edge</strong>
            <p style="color: #666;">✅ Full Support</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem;">🟧</div>
            <strong>Opera</strong>
            <p style="color: #666;">✅ Full Support</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem;">🦁</div>
            <strong>Brave</strong>
            <p style="color: #666;">✅ Full Support</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== PRICING PLANS ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>💳 Simple, Transparent Pricing</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: white; border-radius: 16px; padding: 1.5rem; text-align: center; border: 1px solid #e0e0e0;">
            <h3 style="color: #1e3c72;">Free</h3>
            <div style="font-size: 2rem; font-weight: bold;">৳0</div>
            <div style="color: #666; margin-bottom: 1rem;">/month</div>
            <ul class="feature-list" style="text-align: left;">
                <li>5 auto-fills/month</li>
                <li>Basic fields</li>
                <li>Email support</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: white; border-radius: 16px; padding: 1.5rem; text-align: center; border: 2px solid #667eea;">
            <h3 style="color: #1e3c72;">Basic</h3>
            <div style="font-size: 2rem; font-weight: bold;">৳4,999</div>
            <div style="color: #666; margin-bottom: 1rem;">/month</div>
            <ul class="feature-list" style="text-align: left;">
                <li>30 auto-fills/month</li>
                <li>All field types</li>
                <li>Export reports</li>
                <li>Priority support</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: white; border-radius: 16px; padding: 1.5rem; text-align: center; border: 2px solid #667eea;">
            <h3 style="color: #1e3c72;">Professional</h3>
            <div style="font-size: 2rem; font-weight: bold;">৳14,999</div>
            <div style="color: #666; margin-bottom: 1rem;">/month</div>
            <ul class="feature-list" style="text-align: left;">
                <li>100 auto-fills/month</li>
                <li>Team collaboration</li>
                <li>Advanced AI matching</li>
                <li>Dedicated support</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: white; border-radius: 16px; padding: 1.5rem; text-align: center; border: 1px solid #e0e0e0;">
            <h3 style="color: #1e3c72;">Enterprise</h3>
            <div style="font-size: 2rem; font-weight: bold;">Custom</div>
            <div style="color: #666; margin-bottom: 1rem;">/year</div>
            <ul class="feature-list" style="text-align: left;">
                <li>Unlimited auto-fills</li>
                <li>Custom AI model</li>
                <li>API access</li>
                <li>24/7 support</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== TESTIMONIALS ==========
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    st.markdown('<h2>💬 What Users Are Saying</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="color: #FFD700; margin-bottom: 0.5rem;">★★★★★</div>
            <p style="color: #555;">"This extension saved us hours of manual data entry. We now submit tenders 3x faster!"</p>
            <div style="margin-top: 1rem;">
                <strong>— Md. Rahim Uddin</strong><br>
                <small>ABC Construction</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="color: #FFD700; margin-bottom: 0.5rem;">★★★★★</div>
            <p style="color: #555;">"The AI field matching is incredible. It even works with Bangla labels and misspelled fields!"</p>
            <div style="margin-top: 1rem;">
                <strong>— Shahana Akhter</strong><br>
                <small>BuildTech Ltd</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="color: #FFD700; margin-bottom: 0.5rem;">★★★★★</div>
            <p style="color: #555;">"Team sync feature is a game-changer. My whole team uses the same verified company data."</p>
            <div style="margin-top: 1rem;">
                <strong>— Kazi Hasan</strong><br>
                <small>Hasan Enterprise</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== FINAL CTA ==========
    st.markdown("""
    <div class="cta-section">
        <h2 style="font-size: 2rem; margin-bottom: 1rem;">Ready to save hours on every tender?</h2>
        <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">Join hundreds of contractors already using TenderAI</p>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit button for CTA
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.get('logged_in', False):
            if st.button("🚀 Download Extension Now", use_container_width=True, type="primary"):
                st.session_state.page = "extension_download"
                st.rerun()
        else:
            if st.button("🔐 Login to Download", use_container_width=True, type="primary"):
                st.session_state.page = "login"
                st.rerun()

    st.markdown('<p style="text-align: center; margin-top: 1rem; font-size: 0.8rem;">✓ Free for registered users ✓ No credit card required</p>', unsafe_allow_html=True)
