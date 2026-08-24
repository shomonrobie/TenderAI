# _pages/sitemap.py

import streamlit as st

def show():
    """Sitemap Page"""
    
    st.markdown("""
    <style>
    .sitemap-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem;
    }
    .sitemap-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 2rem;
        margin-top: 2rem;
    }
    .sitemap-section h3 {
        color: #667eea;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid rgba(102, 126, 234, 0.2);
        padding-bottom: 0.5rem;
    }
    .sitemap-section a {
        display: block;
        color: #94a3b8;
        text-decoration: none;
        padding: 0.3rem 0;
        font-size: 0.9rem;
        transition: color 0.3s ease;
        cursor: pointer;
    }
    .sitemap-section a:hover {
        color: #667eea;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🗺️ Sitemap
        </h1>
        <p style="color: #64748b;">Navigate through all pages of TenderAI</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="sitemap-section">
            <h3>🏠 Main Pages</h3>
            <a onclick="navigate('dashboard')">Dashboard</a>
            <a onclick="navigate('about')">About Us</a>
            <a onclick="navigate('features')">Features</a>
            <a onclick="navigate('pricing')">Pricing</a>
            <a onclick="navigate('contact')">Contact Us</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="sitemap-section">
            <h3>📚 Resources</h3>
            <a onclick="navigate('knowledge_base')">Knowledge Base</a>
            <a onclick="navigate('faq')">FAQ</a>
            <a onclick="navigate('blog')">Blog</a>
            <a onclick="navigate('support')">Support</a>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="sitemap-section">
            <h3>⚖️ Legal</h3>
            <a onclick="navigate('terms')">Terms &amp; Conditions</a>
            <a onclick="navigate('privacy')">Privacy Policy</a>
            <a onclick="navigate('cookies')">Cookie Policy</a>
            <a onclick="navigate('gdpr')">GDPR Compliance</a>
            <a onclick="navigate('sitemap')">Sitemap</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="sitemap-section">
            <h3>📞 Support</h3>
            <a onclick="navigate('book_demo')">Book a Demo</a>
            <a onclick="navigate('contact')">Contact Support</a>
            <a href="mailto:support@itenderbd.com">Email Support</a>
            <a href="tel:+8801234567890">Phone Support</a>
        </div>
        """, unsafe_allow_html=True)
    
    # JavaScript for navigation
    st.markdown("""
    <script>
    function navigate(page) {
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        window.location.href = url.toString();
    }
    </script>
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