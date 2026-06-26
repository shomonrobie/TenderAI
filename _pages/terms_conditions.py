# _pages/terms_conditions.py

import streamlit as st
from datetime import datetime

def show():
    """Terms & Conditions Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            📋 Terms & Conditions
        </h1>
        <p style="color: #64748b; font-size: 1.1rem;">Last Updated: April 2026</p>
        <p style="color: #94a3b8;">Welcome to TenderAI. Please read these terms carefully before using our platform.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Table of Contents
    with st.expander("📑 Table of Contents", expanded=False):
        st.markdown("""
        1. [Acceptance of Terms](#acceptance)
        2. [Definitions](#definitions)
        3. [Account Registration](#account)
        4. [User Obligations](#obligations)
        5. [Intellectual Property](#ip)
        6. [Platform Features](#features)
        7. [Subscriptions and Payments](#payments)
        8. [Data Privacy](#privacy)
        9. [Limitation of Liability](#liability)
        10. [Dispute Resolution](#dispute)
        11. [Termination](#termination)
        12. [Governing Law](#law)
        13. [Changes to Terms](#changes)
        14. [Contact Us](#contact)
        """)
    
    st.markdown("---")
    
    # 1. Acceptance of Terms
    st.markdown("""
    <h2 id="acceptance">1. Acceptance of Terms</h2>
    <p>By using TenderAI ("Platform", "Service"), you agree to these Terms & Conditions. If you do not agree, please do not use our platform.</p>
    <p>These terms constitute a legally binding agreement between you ("User", "Customer") and TenderAI (BD) ("Company", "We", "Our", "Us").</p>
    """, unsafe_allow_html=True)
    
    # 2. Definitions
    with st.expander("📚 2. Definitions", expanded=False):
        st.markdown("""
        | Term | Definition |
        |------|------------|
        | **Platform** | TenderAI web application and services |
        | **User** | Any individual or entity using the platform |
        | **Account** | Registered user account on the platform |
        | **Tender** | Government or private procurement opportunity |
        | **Analysis** | AI-powered bid optimization and win probability assessment |
        | **Subscription** | Paid plan for accessing premium features |
        | **Content** | Any data, text, images, or information on the platform |
        | **Services** | All features and functionalities offered by TenderAI |
        """)
    
    # 3. Account Registration
    with st.expander("🔑 3. Account Registration", expanded=False):
        st.markdown("""
        ### Eligibility
        - Must be 18 years or older
        - Must provide accurate and complete information
        - Must maintain the confidentiality of login credentials
        - Must accept responsibility for all activities under your account
        
        ### Account Types
        - **Free Account**: Basic features with limited functionality
        - **Premium Account**: Full features with subscription
        - **Enterprise Account**: Custom solutions for organizations
        
        ### Verification
        - We may require verification of identity
        - We may verify company registration details
        - We reserve the right to refuse service
        """)
    
    # 4. User Obligations
    with st.expander("⚡ 4. User Obligations", expanded=False):
        st.markdown("""
        ### Prohibited Activities
        You agree NOT to:
        - Use the platform for any illegal purpose
        - Upload malicious code or malware
        - Attempt to gain unauthorized access
        - Scrape or crawl the platform without permission
        - Impersonate any person or entity
        - Share sensitive or confidential data inappropriately
        
        ### Acceptable Use
        - Use the platform for legitimate business purposes
        - Maintain the confidentiality of your account
        - Report any security vulnerabilities
        - Comply with all applicable laws and regulations
        - Use the platform ethically and responsibly
        """)
    
    # 5. Intellectual Property
    with st.expander("©️ 5. Intellectual Property", expanded=False):
        st.markdown("""
        ### Our IP
        - **Copyright**: All code, design, and content are owned by TenderAI
        - **Trademarks**: "TenderAI", "BidMatic" are registered trademarks
        - **Patents**: Our AI algorithms are patent-pending
        
        ### Your IP
        - **User Content**: You retain ownership of your tender data
        - **Analysis Results**: Results of your analyses belong to you
        - **License**: You grant us a license to process your data for providing services
        
        ### Restrictions
        - You may not copy, modify, or distribute our IP
        - You may not reverse engineer our platform
        - You may not use our IP without explicit permission
        """)
    
    # 6. Platform Features
    with st.expander("🚀 6. Platform Features", expanded=False):
        st.markdown("""
        ### Core Features
        - **Tender Analysis**: AI-powered bid optimization
        - **Win Probability**: Statistical prediction of win chances
        - **Competitor Analysis**: Market insights and competitor tracking
        - **BOQ Generation**: Automated bill of quantities
        - **Historical Data**: Past tender performance analysis
        - **Team Management**: User and role management
        
        ### AI Disclaimer
        - Our AI provides probabilistic predictions
        - Results are not guarantees of success
        - Final decisions remain your responsibility
        - We recommend using our platform as a decision support tool
        
        ### Service Availability
        - We strive for 99.9% uptime
        - We reserve the right for maintenance windows
        - We will notify users of scheduled maintenance
        """)
    
    # 7. Subscriptions and Payments
    with st.expander("💳 7. Subscriptions and Payments", expanded=False):
        st.markdown("""
        ### Pricing
        - **Free Plan**: $0/month - Basic features
        - **Basic Plan**: $49/month - Advanced features
        - **Professional Plan**: $149/month - Full features
        - **Enterprise Plan**: Custom pricing - Custom solutions
        
        ### Payment Terms
        - **Billing**: Monthly or annual subscription
        - **Payment Methods**: Credit card, bKash, SSLCommerz
        - **Currency**: BDT (Bangladeshi Taka)
        - **Taxes**: Applicable VAT and taxes added
        
        ### Cancellation and Refunds
        - **Cancellation**: Can cancel anytime
        - **Refunds**: Pro-rata refunds for unused time
        - **Free Trial**: 7-day free trial available
        - **Money-Back**: 14-day money-back guarantee (enterprise only)
        """)
    
    # 8. Data Privacy
    with st.expander("🔒 8. Data Privacy", expanded=False):
        st.markdown("""
        ### Our Commitment
        - We comply with GDPR and Bangladeshi data protection laws
        - We implement industry-standard security measures
        - We never sell your data to third parties
        
        ### Data Collection
        - We collect data necessary for providing our services
        - We collect data with your consent
        - We anonymize data for analytics
        
        ### Your Rights
        - Access your data
        - Correct your data
        - Delete your data
        - Object to data processing
        - Data portability
        
        **Please see our [Privacy Policy](#) for detailed information.**
        """)
    
    # 9. Limitation of Liability
    with st.expander("⚖️ 9. Limitation of Liability", expanded=False):
        st.markdown("""
        ### Disclaimer of Warranties
        - Platform is provided "AS IS" and "AS AVAILABLE"
        - No warranty of accuracy or reliability
        - No warranty of fitness for a particular purpose
        
        ### Limitation
        - We are not liable for:
          - Indirect or consequential damages
          - Lost profits or business opportunities
          - Data loss or corruption
          - Third-party claims
        
        ### Maximum Liability
        - Limited to the amount paid by you in the last 12 months
        - Limited to the specific service that caused the damage
        
        ### Force Majeure
        - We are not liable for failures due to:
          - Natural disasters (fires, floods, earthquakes)
          - Acts of government or war
          - Epidemics/pandemics
          - Internet service interruptions
          - Cyber attacks or data breaches
        """)
    
    # 10. Dispute Resolution
    with st.expander("⚖️ 10. Dispute Resolution", expanded=False):
        st.markdown("""
        ### Governing Law
        These terms are governed by the laws of Bangladesh.
        
        ### Dispute Resolution Process
        1. **Informal Resolution**: First, contact us to resolve disputes
        2. **Mediation**: If unresolved, we may propose mediation
        3. **Arbitration**: Binding arbitration in Dhaka, Bangladesh
        4. **Court**: As a final resort, court proceedings
        
        ### Jurisdiction
        - Exclusive jurisdiction of Dhaka courts
        - You agree to submit to the jurisdiction of Bangladesh
        """)
    
    # 11. Termination
    with st.expander("⛔ 11. Termination", expanded=False):
        st.markdown("""
        ### Termination by User
        - You may terminate your account at any time
        - You can delete your account through settings
        - Unused subscription fees may be refunded (pro-rata)
        
        ### Termination by Us
        - We may terminate for violation of terms
        - We may suspend for suspicious activity
        - We may terminate for non-payment
        
        ### Effect of Termination
        - Your data will be deleted after 30 days
        - You will lose access to premium features
        - You must settle any outstanding payments
        """)
    
    # 12. Governing Law
    with st.expander("📜 12. Governing Law", expanded=False):
        st.markdown("""
        ### Applicable Laws
        - These terms are governed by the laws of Bangladesh
        - We comply with:
          - Bangladesh ICT Act 2006
          - Bangladesh Data Protection Act
          - Public Procurement Rules (PPR 2025)
          - GDPR (for EU citizens)
        
        ### Compliance
        - We reserve the right to comply with legal requests
        - We may report illegal activities to authorities
        - We cooperate with regulatory bodies
        """)
    
    # 13. Changes to Terms
    with st.expander("📝 13. Changes to Terms", expanded=False):
        st.markdown("""
        ### Updates
        - We may update these terms periodically
        - We will notify you of significant changes
        - Changes are effective immediately upon posting
        - Continued use constitutes acceptance
        
        ### Review
        - Please review these terms regularly
        - Check the "Last Updated" date
        - Contact us with any questions
        """)
    
    # 14. Contact Us
    st.markdown("""
    <h2 id="contact">14. Contact Us</h2>
    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #667eea;">
        <p><strong>Legal Department:</strong><br>
        📧 <a href="mailto:legal@itenderbd.com">legal@itenderbd.com</a><br>
        📞 +880 1234 567890</p>
        <p><strong>General Enquiries:</strong><br>
        📧 <a href="mailto:info@itenderbd.com">info@itenderbd.com</a></p>
        <p><strong>Company Address:</strong><br>
        TenderAI (BD)<br>
        123, Gulshan Avenue, Dhaka-1212<br>
        Bangladesh</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    from modules.footer import render_footer
    render_footer()        