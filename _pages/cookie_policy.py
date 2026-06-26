# _pages/cookie_policy.py

import streamlit as st

def show():
    """Cookie Policy Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🍪 Cookie Policy
        </h1>
        <p style="color: #64748b; font-size: 1.1rem;">Last Updated: April 2026</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### What Are Cookies?
    
    Cookies are small text files stored on your device when you visit a website. They help us:
    - Remember your preferences
    - Analyze how you use our platform
    - Provide a better user experience
    
    ### Types of Cookies We Use
    
    | Cookie Type | Purpose | Duration |
    |-------------|---------|----------|
    | **Essential** | Required for platform functionality | Session |
    | **Preference** | Remember your settings | 1 year |
    | **Analytics** | Track usage patterns | 30 days |
    | **Security** | Protect against fraud | Session |
    
    ### Third-Party Cookies
    
    We use third-party services that may set cookies:
    - **Google Analytics**: Website analytics
    - **Hotjar**: User experience insights
    - **Facebook Pixel**: Marketing analytics
    - **LinkedIn Insight**: Professional network tracking
    
    ### Managing Cookies
    
    You can control cookies through your browser:
    1. **Chrome**: Settings → Privacy and Security → Cookies
    2. **Firefox**: Options → Privacy & Security → Cookies
    3. **Safari**: Preferences → Privacy → Cookies
    4. **Edge**: Settings → Privacy, Search, and Services → Cookies
    
    ### Your Choices
    
    - **Accept All**: Use all cookies (recommended for best experience)
    - **Essential Only**: Only functional cookies
    - **Reject All**: No cookies (may affect functionality)
    
    ### Contact Us
    
    For cookie-related questions:
    📧 privacy@itenderbd.com
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    from modules.footer import render_footer
    render_footer()        