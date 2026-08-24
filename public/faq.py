# _pages/faq.py

import streamlit as st

def show():
    """FAQ Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            ❓ Frequently Asked Questions
        </h1>
        <p style="color: #64748b;">Find answers to common questions about TenderAI</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("What is TenderAI?", expanded=False):
        st.markdown("""
        TenderAI is Bangladesh's first AI-powered tender intelligence platform. We help businesses:
        - Analyze tender documents
        - Optimize bid pricing
        - Predict win probability
        - Track competitors
        - Generate BOQ automatically
        """)
    
    with st.expander("How does the AI analysis work?", expanded=False):
        st.markdown("""
        Our AI uses machine learning algorithms trained on thousands of historical tenders to:
        - Analyze tender requirements
        - Calculate optimal bid amounts
        - Predict competitor behavior
        - Assess risk factors
        - Provide confidence scores
        """)
    
    with st.expander("Is my data secure?", expanded=False):
        st.markdown("""
        Yes! We take security seriously:
        - SSL/TLS encryption
        - BCrypt password hashing
        - GDPR compliant
        - Regular security audits
        - Data is never sold to third parties
        """)
    
    with st.expander("What are the pricing plans?", expanded=False):
        st.markdown("""
        We offer flexible plans:
        - **Free**: Basic features, 5 analyses/month
        - **Basic**: $49/month, 30 analyses, advanced features
        - **Professional**: $149/month, 100 analyses, full features
        - **Enterprise**: Custom pricing, unlimited features
        """)
    
    with st.expander("Can I cancel anytime?", expanded=False):
        st.markdown("""
        Yes! You can cancel your subscription at any time. We offer:
        - Monthly subscription with no lock-in
        - Pro-rata refunds for unused time
        - 14-day money-back guarantee for enterprise plans
        """)
    
    with st.expander("How do I get started?", expanded=False):
        st.markdown("""
        1. **Create an account** (Free)
        2. **Upload your tender** or connect via e-GP
        3. **Run AI analysis** for instant insights
        4. **Review recommendations** and make data-driven decisions
        5. **Upgrade** to access more features as needed
        """)
    
    with st.expander("Do you offer training?", expanded=False):
        st.markdown("""
        Yes! We provide:
        - **Onboarding sessions** for new users
        - **Video tutorials** in our knowledge base
        - **1-on-1 training** for enterprise plans
        - **Webinars** on best practices
        """)
    
    with st.expander("What support do you offer?", expanded=False):
        st.markdown("""
        - **24/7 Email Support**: support@itenderbd.com
        - **Phone Support**: +880 1234 567890 (Business Hours)
        - **Live Chat**: Available on our platform
        - **Knowledge Base**: Help articles and guides
        """)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    from modules.footer import render_footer
    render_footer()        