# _pages/privacy_policy.py

import streamlit as st
from datetime import datetime

def show():
    """Privacy Policy & GDPR Compliance Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🔒 Privacy Policy
        </h1>
        <p style="color: #64748b; font-size: 1.1rem;">Last Updated: April 2026</p>
        <p style="color: #94a3b8;">Your privacy matters to us. We are committed to protecting your personal data.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Table of Contents
    with st.expander("📑 Table of Contents", expanded=False):
        st.markdown("""
        1. [Introduction](#introduction)
        2. [Data We Collect](#data-we-collect)
        3. [How We Use Your Data](#how-we-use-your-data)
        4. [Legal Basis for Processing](#legal-basis)
        5. [Data Sharing and Disclosure](#data-sharing)
        6. [Data Security](#data-security)
        7. [Your Rights (GDPR)](#your-rights)
        8. [Cookies and Tracking](#cookies)
        9. [Data Retention](#data-retention)
        10. [International Data Transfers](#international-transfers)
        11. [Children's Privacy](#children)
        12. [Updates to This Policy](#updates)
        13. [Contact Us](#contact)
        """)
    
    st.markdown("---")
    
    # 1. Introduction
    st.markdown("""
    <h2 id="introduction">1. Introduction</h2>
    <p>Welcome to TenderAI ("we", "our", "us"). We are committed to protecting your privacy and ensuring the security of your personal data. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.</p>
    <p>This policy complies with the <strong>General Data Protection Regulation (GDPR)</strong> (EU) 2016/679 and applicable Bangladeshi data protection laws.</p>
    """, unsafe_allow_html=True)
    
    # 2. Data We Collect
    with st.expander("📊 2. Data We Collect", expanded=False):
        st.markdown("""
        ### Personal Information
        - **Contact Information**: Name, email address, phone number, company name
        - **Account Credentials**: Username, password (encrypted)
        - **Professional Information**: Job title, role, specialization, years of experience
        - **Business Information**: Company registration details, VAT/TIN numbers
        
        ### Usage Data
        - **Platform Activity**: Pages visited, features used, analyses performed
        - **Device Information**: IP address, browser type, operating system
        - **Cookies**: Session data and preferences
        
        ### Tender Data
        - **Tender Submissions**: Tender details, bid amounts, analysis results
        - **Historical Data**: Past tender performance, win/loss records
        - **Competitor Data**: Competitor analysis and market insights
        """)
    
    # 3. How We Use Your Data
    with st.expander("⚙️ 3. How We Use Your Data", expanded=False):
        st.markdown("""
        We use your data for the following purposes:
        
        - **Platform Operation**: To provide, maintain, and improve our services
        - **Tender Analysis**: To perform bid optimization and win probability analysis
        - **Personalization**: To customize your experience and recommendations
        - **Communication**: To send updates, notifications, and support messages
        - **Security**: To detect and prevent fraud, abuse, and security incidents
        - **Compliance**: To fulfill legal and regulatory obligations
        - **Analytics**: To understand usage patterns and improve our platform
        - **Marketing**: To inform you about new features and services (with your consent)
        """)
    
    # 4. Legal Basis for Processing
    with st.expander("⚖️ 4. Legal Basis for Processing (GDPR)", expanded=False):
        st.markdown("""
        Under GDPR, we process your data based on the following legal grounds:
        
        | Basis | Description |
        |-------|-------------|
        | **Contractual Necessity** | Processing necessary for performing our contract with you |
        | **Legitimate Interest** | Processing necessary for our legitimate business interests |
        | **Legal Obligation** | Processing necessary for compliance with legal obligations |
        | **Consent** | Processing based on your explicit consent |
        | **Vital Interest** | Processing necessary to protect your vital interests |
        
        **Legitimate Interests Include:**
        - Improving and optimizing our platform
        - Ensuring platform security and integrity
        - Conducting business analytics and research
        - Preventing fraud and abuse
        """)
    
    # 5. Data Sharing and Disclosure
    with st.expander("🤝 5. Data Sharing and Disclosure", expanded=False):
        st.markdown("""
        We share your data only in the following circumstances:
        
        ### Within Your Organization
        - Sharing data with other users in your company account
        - Sharing analysis results with team members
        
        ### With Service Providers
        - Cloud hosting providers (AWS, Azure)
        - Analytics providers (Google Analytics)
        - Payment processors (SSLCommerz, bKash)
        - Email service providers (SendGrid, Mailchimp)
        
        ### Legal Compliance
        - To comply with applicable laws and regulations
        - To respond to lawful requests from authorities
        - To protect our rights, privacy, safety, or property
        
        ### Business Transfers
        - In case of merger, acquisition, or sale of assets
        - With prior notice and your consent where required
        """)
    
    # 6. Data Security
    with st.expander("🔐 6. Data Security", expanded=False):
        st.markdown("""
        We implement robust security measures to protect your data:
        
        ### Technical Measures
        - **Encryption**: SSL/TLS encryption for data in transit
        - **Hashing**: Passwords encrypted using bcrypt
        - **Firewalls**: Network protection and intrusion detection
        - **Access Controls**: Role-based access and authentication
        - **Audit Logs**: Comprehensive logging of all platform activities
        
        ### Organizational Measures
        - **GDPR Compliance**: Regular data protection audits
        - **Staff Training**: Security awareness and data protection training
        - **Incident Response**: Prepared plan for security incidents
        - **Data Minimization**: Collecting only necessary data
        
        ### Our Commitment
        We regularly review and update our security practices to ensure the highest level of protection for your data.
        """)
    
    # 7. Your Rights (GDPR)
    with st.expander("📋 7. Your Rights Under GDPR", expanded=False):
        st.markdown("""
        You have the following rights regarding your personal data:
        
        | Right | Description | How to Exercise |
        |-------|-------------|-----------------|
        | **Right to Access** | Request a copy of your data | Contact us via email |
        | **Right to Rectification** | Correct inaccurate data | Update your profile |
        | **Right to Erasure** | Request data deletion (forgotten) | Submit a deletion request |
        | **Right to Restrict Processing** | Limit how we use your data | Request processing restriction |
        | **Right to Data Portability** | Receive your data in portable format | Request data export |
        | **Right to Object** | Object to data processing | Opt-out or contact us |
        | **Right to Withdraw Consent** | Withdraw your consent | Manage privacy settings |
        
        ### Data Protection Officer (DPO)
        If you have concerns about how we handle your data, you can contact our Data Protection Officer:
        - **Email**: dpo@itenderbd.com
        - **Phone**: +880 1234 567890
        """)
    
    # 8. Cookies and Tracking
    with st.expander("🍪 8. Cookies and Tracking", expanded=False):
        st.markdown("""
        We use cookies to enhance your experience on our platform:
        
        ### Types of Cookies We Use
        - **Essential Cookies**: Required for platform functionality
        - **Preference Cookies**: Remember your settings and preferences
        - **Analytics Cookies**: Help us understand how you use the platform
        - **Session Cookies**: Maintain your login session
        
        ### Managing Cookies
        You can control cookies through your browser settings:
        - **Chrome**: Settings → Privacy and Security → Cookies
        - **Firefox**: Options → Privacy & Security → Cookies
        - **Safari**: Preferences → Privacy → Cookies
        - **Edge**: Settings → Privacy, Search, and Services → Cookies
        
        ### Third-Party Tracking
        We may use third-party analytics tools (Google Analytics, Hotjar) to improve our services. These tools may use their own cookies.
        """)
    
    # 9. Data Retention
    with st.expander("⏰ 9. Data Retention", expanded=False):
        st.markdown("""
        We retain your data only as long as necessary:
        
        | Data Type | Retention Period |
        |-----------|------------------|
        | Account Information | Active account + 12 months |
        | Tender Analysis | 7 years (for audit trail) |
        | Payment Records | 7 years (legal requirement) |
        | Activity Logs | 2 years |
        | Cookie Data | Session + 30 days |
        | Marketing Data | Until consent withdrawn |
        
        **Deletion Requests**: You can request deletion of your data at any time.
        """)
    
    # 10. International Data Transfers
    with st.expander("🌍 10. International Data Transfers", expanded=False):
        st.markdown("""
        While we primarily operate in Bangladesh, your data may be transferred to:
        
        - **Cloud Service Providers**: Data centers in EU, US, or Asia
        - **Third-Party Services**: Analytics, email, payment processors
        
        ### Transfer Safeguards
        We ensure appropriate safeguards for international data transfers:
        - **Standard Contractual Clauses** (SCCs)
        - **Privacy Shield Framework** (where applicable)
        - **Data Processing Agreements** with all service providers
        
        All transfers comply with GDPR requirements and Bangladeshi data protection laws.
        """)
    
    # 11. Children's Privacy
    with st.expander("👶 11. Children's Privacy", expanded=False):
        st.markdown("""
        Our platform is not intended for individuals under 18 years of age:
        
        - **Age Restriction**: We do not knowingly collect data from minors
        - **Verification**: We may require age verification for certain services
        - **Removal**: If we learn we have collected minor data, we will delete it
        - **Parental Consent**: We do not seek or require parental consent for minors
        
        If you believe we have collected data from a minor, please contact us immediately.
        """)
    
    # 12. Updates to This Policy
    with st.expander("📝 12. Updates to This Policy", expanded=False):
        st.markdown("""
        We may update this Privacy Policy from time to time:
        
        - **Notification**: We will notify you of significant changes
        - **Effective Date**: The date at the top of this policy
        - **Review**: Please review this policy periodically
        - **Consent**: Continued use constitutes acceptance of changes
        
        **Recent Updates:**
        - April 2026: Initial version
        - Updated to comply with GDPR requirements
        - Added DPO contact information
        """)
    
    # 13. Contact Us
    st.markdown("""
    <h2 id="contact">13. Contact Us</h2>
    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #667eea;">
        <p><strong>Data Protection Officer (DPO):</strong><br>
        📧 <a href="mailto:dpo@itenderbd.com">dpo@itenderbd.com</a><br>
        📞 +880 1234 567890</p>
        <p><strong>General Enquiries:</strong><br>
        📧 <a href="mailto:privacy@itenderbd.com">privacy@itenderbd.com</a></p>
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